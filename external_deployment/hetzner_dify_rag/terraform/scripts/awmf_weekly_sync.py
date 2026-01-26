#!/usr/bin/env python3
"""AWMF Weekly Sync - Automated guideline synchronization."""
import argparse, asyncio, json, logging, os, sys, tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3, httpx
from botocore.config import Config

sys.path.insert(0, "/opt/awmf-sync")
from scripts.awmf_document import AWMFDocument, extract_registry_key
from rag.awmf_crawler import crawl_for_urls

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIFY_URL = os.getenv("DIFY_URL", "")
DIFY_DATASET_API_KEY = os.getenv("DIFY_DATASET_API_KEY", "")
DIFY_DATASET_ID = os.getenv("DIFY_DATASET_ID", "")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET = os.getenv("S3_BUCKET", "awmf-guidelines")
STATE_FILE = Path("/opt/awmf-sync/.awmf_sync_state.json")

@dataclass
class SyncReport:
    added: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    updated: list[tuple[str, str]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    awmf_total: int = 0
    s3_before: int = 0
    s3_after: int = 0
    dify_before: int = 0
    dify_after: int = 0

    def finalize(self): self.end_time = datetime.now(timezone.utc)
    @property
    def duration_seconds(self) -> float: return (self.end_time - self.start_time).total_seconds() if self.end_time else 0
    def to_dict(self) -> dict:
        return {"added": len(self.added), "deleted": len(self.deleted), "updated": len(self.updated),
                "errors": len(self.errors), "duration_seconds": self.duration_seconds,
                "awmf_total": self.awmf_total, "s3_before": self.s3_before, "s3_after": self.s3_after,
                "dify_before": self.dify_before, "dify_after": self.dify_after,
                "added_files": self.added, "deleted_files": self.deleted,
                "updated_files": [{"old": o, "new": n} for o, n in self.updated], "error_details": self.errors}
    def print_report(self):
        print("\n" + "=" * 70)
        print("AWMF Weekly Sync Report")
        print("=" * 70)
        print(f"Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"Duration: {int(self.duration_seconds // 60)}m {int(self.duration_seconds % 60)}s")
        print(f"\nAWMF Registry: {self.awmf_total:,} guidelines")
        print(f"\nChanges: +{len(self.added)} added, -{len(self.deleted)} deleted, ~{len(self.updated)} updated")
        print(f"S3: {self.s3_before:,} -> {self.s3_after:,}")
        print(f"Dify: {self.dify_before:,} -> {self.dify_after:,}")
        print(f"Errors: {len(self.errors)}")
        print("=" * 70)

class AWMFWeeklySync:
    def __init__(self, s3_endpoint, s3_bucket, s3_access_key, s3_secret_key, dify_url, dify_dataset_api_key, dify_dataset_id, dry_run=False):
        self.s3_bucket, self.dify_url, self.dify_api_key, self.dify_dataset_id, self.dry_run = s3_bucket, dify_url.rstrip("/"), dify_dataset_api_key, dify_dataset_id, dry_run
        self.s3_client = boto3.client("s3", endpoint_url=s3_endpoint, aws_access_key_id=s3_access_key, aws_secret_access_key=s3_secret_key, config=Config(signature_version="s3v4"))
        self.awmf_pdfs, self.s3_pdfs, self.dify_docs = {}, set(), {}
        self._state = self._load_state()

    def _load_state(self):
        if STATE_FILE.exists():
            with open(STATE_FILE) as f: return json.load(f)
        return {"last_sync": None, "last_sync_report": None, "awmf_snapshot": {}, "sync_history": []}

    def _save_state(self, report):
        self._state["last_sync"] = datetime.now(timezone.utc).isoformat()
        self._state["last_sync_report"] = report.to_dict()
        self._state["awmf_snapshot"] = {f: {"url": d.url, "registry_number": d.registry_number, "version_date": d.version_date} for f, d in self.awmf_pdfs.items()}
        self._state["sync_history"] = [{"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "added": len(report.added), "deleted": len(report.deleted), "updated": len(report.updated)}] + self._state["sync_history"][:51]
        with open(STATE_FILE, "w") as f: json.dump(self._state, f, indent=2)

    async def crawl_awmf(self):
        logger.info("Crawling AWMF registry...")
        self.awmf_pdfs = await crawl_for_urls()
        logger.info(f"Found {len(self.awmf_pdfs)} PDFs")
        return self.awmf_pdfs

    def list_s3_pdfs(self):
        logger.info(f"Listing S3: {self.s3_bucket}")
        keys = set()
        for page in self.s3_client.get_paginator("list_objects_v2").paginate(Bucket=self.s3_bucket):
            for obj in page.get("Contents", []):
                if obj["Key"].lower().endswith(".pdf"): keys.add(obj["Key"])
        self.s3_pdfs = keys
        logger.info(f"Found {len(keys)} PDFs in S3")
        return keys

    async def list_dify_documents(self):
        logger.info("Listing Dify KB...")
        documents, page = {}, 1
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                resp = await client.get(f"{self.dify_url}/v1/datasets/{self.dify_dataset_id}/documents", params={"limit": 100, "page": page}, headers={"Authorization": f"Bearer {self.dify_api_key}"})
                if resp.status_code != 200: break
                data = resp.json()
                for doc in data.get("data", []): documents[doc["name"]] = doc["id"]
                if not data.get("has_more", False): break
                page += 1
        self.dify_docs = documents
        logger.info(f"Found {len(documents)} docs in Dify")
        return documents

    def calculate_deltas(self):
        awmf_filenames = set(self.awmf_pdfs.keys())
        to_add, to_delete = list(awmf_filenames - self.s3_pdfs), list(self.s3_pdfs - awmf_filenames)
        to_update = []
        to_add_by_base = {extract_registry_key(f): f for f in to_add}
        to_delete_by_base = {extract_registry_key(f): f for f in to_delete}
        for base_key in set(to_add_by_base.keys()) & set(to_delete_by_base.keys()):
            old_f, new_f = to_delete_by_base[base_key], to_add_by_base[base_key]
            to_update.append((old_f, new_f, self.awmf_pdfs[new_f]))
            to_add.remove(new_f)
            to_delete.remove(old_f)
        logger.info(f"Delta: +{len(to_add)}, -{len(to_delete)}, ~{len(to_update)}")
        return to_add, to_delete, to_update

    async def _download_pdf(self, url):
        async with httpx.AsyncClient(timeout=120.0) as c:
            r = await c.get(url); r.raise_for_status(); return r.content

    async def _upload_to_dify(self, filename, pdf_bytes):
        async with httpx.AsyncClient(timeout=180.0) as client:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
                tmp.write(pdf_bytes); tmp.flush()
                with open(tmp.name, "rb") as f:
                    resp = await client.post(f"{self.dify_url}/v1/datasets/{self.dify_dataset_id}/document/create_by_file",
                        headers={"Authorization": f"Bearer {self.dify_api_key}"},
                        files={"file": (filename, f, "application/pdf")},
                        data={"data": json.dumps({"indexing_technique": "high_quality", "process_rule": {"mode": "custom", "rules": {"pre_processing_rules": [{"id": "remove_extra_spaces", "enabled": True}, {"id": "remove_urls_emails", "enabled": False}], "segmentation": {"separator": "\n\n", "max_tokens": 1000, "chunk_overlap": 200}}}})})
                    if resp.status_code != 200: raise Exception(f"Dify upload failed: {resp.status_code}")
                    return resp.json()

    async def _delete_from_dify(self, doc_id):
        async with httpx.AsyncClient(timeout=60.0) as c:
            return (await c.delete(f"{self.dify_url}/v1/datasets/{self.dify_dataset_id}/documents/{doc_id}", headers={"Authorization": f"Bearer {self.dify_api_key}"})).status_code == 200

    async def sync_new_pdfs(self, to_add, report):
        for i, fn in enumerate(to_add):
            doc = self.awmf_pdfs[fn]
            logger.info(f"[{i+1}/{len(to_add)}] Adding: {fn}")
            if self.dry_run: report.added.append(fn); continue
            try:
                pdf = await self._download_pdf(doc.url)
                self.s3_client.put_object(Bucket=self.s3_bucket, Key=fn, Body=pdf, ContentType="application/pdf")
                await self._upload_to_dify(fn, pdf)
                report.added.append(fn)
                await asyncio.sleep(10.0)
            except Exception as e:
                logger.error(f"Failed: {fn}: {e}")
                report.errors.append({"filename": fn, "op": "add", "error": str(e)})

    async def sync_deleted_pdfs(self, to_delete, report):
        for i, fn in enumerate(to_delete):
            logger.info(f"[{i+1}/{len(to_delete)}] Deleting: {fn}")
            if self.dry_run: report.deleted.append(fn); continue
            try:
                if fn in self.dify_docs: await self._delete_from_dify(self.dify_docs[fn])
                self.s3_client.delete_object(Bucket=self.s3_bucket, Key=fn)
                report.deleted.append(fn)
                await asyncio.sleep(1.0)
            except Exception as e:
                logger.error(f"Failed: {fn}: {e}")
                report.errors.append({"filename": fn, "op": "delete", "error": str(e)})

    async def sync_updated_pdfs(self, to_update, report):
        for i, (old_fn, new_fn, new_doc) in enumerate(to_update):
            logger.info(f"[{i+1}/{len(to_update)}] Updating: {old_fn} -> {new_fn}")
            if self.dry_run: report.updated.append((old_fn, new_fn)); continue
            try:
                if old_fn in self.dify_docs: await self._delete_from_dify(self.dify_docs[old_fn])
                self.s3_client.delete_object(Bucket=self.s3_bucket, Key=old_fn)
                pdf = await self._download_pdf(new_doc.url)
                self.s3_client.put_object(Bucket=self.s3_bucket, Key=new_fn, Body=pdf, ContentType="application/pdf")
                await self._upload_to_dify(new_fn, pdf)
                report.updated.append((old_fn, new_fn))
                await asyncio.sleep(10.0)
            except Exception as e:
                logger.error(f"Failed: {old_fn}: {e}")
                report.errors.append({"filename": old_fn, "op": "update", "error": str(e)})

    async def run_full_sync(self):
        report = SyncReport()
        if self.dry_run: logger.info("DRY RUN MODE")
        await self.crawl_awmf(); report.awmf_total = len(self.awmf_pdfs)
        self.list_s3_pdfs(); report.s3_before = len(self.s3_pdfs)
        await self.list_dify_documents(); report.dify_before = len(self.dify_docs)
        to_add, to_delete, to_update = self.calculate_deltas()
        await self.sync_new_pdfs(to_add, report)
        await self.sync_deleted_pdfs(to_delete, report)
        await self.sync_updated_pdfs(to_update, report)
        report.s3_after = report.s3_before + len(report.added) - len(report.deleted)
        report.dify_after = report.dify_before + len(report.added) - len(report.deleted)
        report.finalize()
        if not self.dry_run: self._save_state(report)
        return report

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--crawl-only", action="store_true")
    args = parser.parse_args()
    if not all([DIFY_URL, DIFY_DATASET_API_KEY, DIFY_DATASET_ID]): logger.error("Missing Dify config"); sys.exit(1)
    if not all([S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY]): logger.error("Missing S3 config"); sys.exit(1)
    if args.crawl_only:
        docs = await crawl_for_urls()
        print(f"\nFound {len(docs)} PDFs"); sys.exit(0)
    syncer = AWMFWeeklySync(S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, DIFY_URL, DIFY_DATASET_API_KEY, DIFY_DATASET_ID, args.dry_run)
    report = await syncer.run_full_sync()
    report.print_report()
    if report.errors: sys.exit(1)

if __name__ == "__main__": asyncio.run(main())
