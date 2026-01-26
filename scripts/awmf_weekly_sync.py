#!/usr/bin/env python3
"""
AWMF Weekly Sync - Automated guideline synchronization.

Synchronizes AWMF medical guidelines between the AWMF registry,
Hetzner Object Storage (S3), and Dify Knowledge Base.

Operations:
- Crawls AWMF registry for current PDF links
- Compares against S3 and Dify contents
- Uploads NEW PDFs to S3 → Dify
- Deletes REMOVED PDFs from S3 and Dify
- Handles UPDATED PDFs (same registry number, new version)

Usage:
    python scripts/awmf_weekly_sync.py                 # Full sync
    python scripts/awmf_weekly_sync.py --dry-run      # Preview changes only
    python scripts/awmf_weekly_sync.py --crawl-only   # Only crawl, don't sync

Environment Variables:
    DIFY_URL: Dify API URL (e.g., https://rag.fra-la.de)
    DIFY_DATASET_API_KEY: Dify dataset API key
    DIFY_DATASET_ID: Target knowledge base ID
    S3_ENDPOINT: Object Storage endpoint
    S3_ACCESS_KEY: Object Storage access key
    S3_SECRET_KEY: Object Storage secret key
    S3_BUCKET: Bucket name (default: awmf-guidelines)
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import httpx
from botocore.config import Config

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.awmf_document import AWMFDocument, extract_registry_key
from rag.awmf_crawler import crawl_for_urls

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration from environment
DIFY_URL = os.getenv("DIFY_URL", "")
DIFY_DATASET_API_KEY = os.getenv("DIFY_DATASET_API_KEY", "")
DIFY_DATASET_ID = os.getenv("DIFY_DATASET_ID", "")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET = os.getenv("S3_BUCKET", "awmf-guidelines")

STATE_FILE = Path(__file__).parent / ".awmf_sync_state.json"


@dataclass
class SyncReport:
    """Report of sync operations performed."""

    added: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    updated: list[tuple[str, str]] = field(default_factory=list)  # (old, new)
    errors: list[dict[str, Any]] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    awmf_total: int = 0
    s3_before: int = 0
    s3_after: int = 0
    dify_before: int = 0
    dify_after: int = 0

    def finalize(self):
        """Mark sync as complete."""
        self.end_time = datetime.now(timezone.utc)

    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "added": len(self.added),
            "deleted": len(self.deleted),
            "updated": len(self.updated),
            "errors": len(self.errors),
            "duration_seconds": self.duration_seconds,
            "awmf_total": self.awmf_total,
            "s3_before": self.s3_before,
            "s3_after": self.s3_after,
            "dify_before": self.dify_before,
            "dify_after": self.dify_after,
            "added_files": self.added,
            "deleted_files": self.deleted,
            "updated_files": [{"old": o, "new": n} for o, n in self.updated],
            "error_details": self.errors,
        }

    def print_report(self):
        """Print formatted sync report."""
        print("\n" + "=" * 70)
        print("AWMF Weekly Sync Report")
        print("=" * 70)
        print(f"Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"Duration: {int(self.duration_seconds // 60)} minutes {int(self.duration_seconds % 60)} seconds")
        print()
        print("AWMF Registry:")
        print(f"  Total guidelines found: {self.awmf_total:,}")
        print()
        print("Changes:")
        print(f"  ✅ Added:   {len(self.added)} new guidelines")
        print(f"  ❌ Deleted: {len(self.deleted)} removed guidelines")
        print(f"  🔄 Updated: {len(self.updated)} version updates")
        print()
        print("Object Storage (S3):")
        print(f"  Total files: {self.s3_before:,} → {self.s3_after:,}")
        print()
        print("Dify Knowledge Base:")
        print(f"  Total documents: {self.dify_before:,} → {self.dify_after:,}")
        print()
        print(f"Errors: {len(self.errors)}")

        if self.added:
            print("\nAdded:")
            for f in self.added[:10]:
                print(f"  - {f}")
            if len(self.added) > 10:
                print(f"  ... and {len(self.added) - 10} more")

        if self.deleted:
            print("\nDeleted:")
            for f in self.deleted[:10]:
                print(f"  - {f}")
            if len(self.deleted) > 10:
                print(f"  ... and {len(self.deleted) - 10} more")

        if self.updated:
            print("\nUpdated:")
            for old, new in self.updated[:10]:
                print(f"  - {extract_registry_key(old)}: {old.split('_')[-1]} → {new.split('_')[-1]}")
            if len(self.updated) > 10:
                print(f"  ... and {len(self.updated) - 10} more")

        if self.errors:
            print("\nErrors:")
            for err in self.errors[:5]:
                print(f"  - {err.get('filename', 'unknown')}: {err.get('error', 'unknown error')}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more")

        print("=" * 70)


class AWMFWeeklySync:
    """Weekly sync of AWMF guidelines to S3 and Dify Knowledge Base."""

    def __init__(
        self,
        s3_endpoint: str,
        s3_bucket: str,
        s3_access_key: str,
        s3_secret_key: str,
        dify_url: str,
        dify_dataset_api_key: str,
        dify_dataset_id: str,
        dry_run: bool = False,
    ):
        self.s3_bucket = s3_bucket
        self.dify_url = dify_url.rstrip("/")
        self.dify_api_key = dify_dataset_api_key
        self.dify_dataset_id = dify_dataset_id
        self.dry_run = dry_run

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=s3_endpoint,
            aws_access_key_id=s3_access_key,
            aws_secret_access_key=s3_secret_key,
            config=Config(signature_version="s3v4"),
        )

        self.awmf_pdfs: dict[str, AWMFDocument] = {}
        self.s3_pdfs: set[str] = set()
        self.dify_docs: dict[str, str] = {}  # filename -> document_id

        self._state = self._load_state()

    def _load_state(self) -> dict:
        """Load sync state for audit history."""
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
        return {
            "last_sync": None,
            "last_sync_report": None,
            "awmf_snapshot": {},
            "sync_history": [],
        }

    def _save_state(self, report: SyncReport):
        """Persist sync state."""
        self._state["last_sync"] = datetime.now(timezone.utc).isoformat()
        self._state["last_sync_report"] = report.to_dict()

        # Store AWMF snapshot
        self._state["awmf_snapshot"] = {
            filename: {
                "url": doc.url,
                "registry_number": doc.registry_number,
                "version_date": doc.version_date,
            }
            for filename, doc in self.awmf_pdfs.items()
        }

        # Add to history (keep last 52 weeks)
        self._state["sync_history"].insert(0, {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "added": len(report.added),
            "deleted": len(report.deleted),
            "updated": len(report.updated),
        })
        self._state["sync_history"] = self._state["sync_history"][:52]

        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(self._state, f, indent=2)

    async def crawl_awmf(self) -> dict[str, AWMFDocument]:
        """
        Crawl AWMF registry and return mapping of filename -> metadata.

        Uses rag/awmf_crawler.py logic but returns structured data
        instead of downloading files.
        """
        logger.info("Crawling AWMF registry...")
        self.awmf_pdfs = await crawl_for_urls()
        logger.info(f"Found {len(self.awmf_pdfs)} PDFs in AWMF registry")
        return self.awmf_pdfs

    def list_s3_pdfs(self) -> set[str]:
        """List all PDF filenames in the S3 bucket."""
        logger.info(f"Listing S3 bucket: {self.s3_bucket}")
        keys = set()
        paginator = self.s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.s3_bucket):
            for obj in page.get("Contents", []):
                if obj["Key"].lower().endswith(".pdf"):
                    keys.add(obj["Key"])
        self.s3_pdfs = keys
        logger.info(f"Found {len(keys)} PDFs in S3")
        return keys

    async def list_dify_documents(self) -> dict[str, str]:
        """
        List all documents in Dify Knowledge Base.

        Returns:
            {filename: document_id, ...}
        """
        logger.info("Listing Dify Knowledge Base documents...")
        documents = {}
        page = 1

        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                response = await client.get(
                    f"{self.dify_url}/v1/datasets/{self.dify_dataset_id}/documents",
                    params={"limit": 100, "page": page},
                    headers={"Authorization": f"Bearer {self.dify_api_key}"}
                )

                if response.status_code != 200:
                    logger.error(f"Dify list error: {response.status_code} - {response.text[:200]}")
                    break

                data = response.json()
                for doc in data.get("data", []):
                    documents[doc["name"]] = doc["id"]

                if not data.get("has_more", False):
                    break
                page += 1

        self.dify_docs = documents
        logger.info(f"Found {len(documents)} documents in Dify")
        return documents

    def calculate_deltas(self) -> tuple[list[str], list[str], list[tuple[str, str, AWMFDocument]]]:
        """
        Calculate what needs to be added, deleted, or updated.

        Returns:
            (to_add, to_delete, to_update)
            where to_update is list of (old_filename, new_filename, new_doc)
        """
        awmf_filenames = set(self.awmf_pdfs.keys())

        # Simple diff
        to_add = list(awmf_filenames - self.s3_pdfs)
        to_delete = list(self.s3_pdfs - awmf_filenames)

        # Detect updates (same registry+variant, different date)
        to_update: list[tuple[str, str, AWMFDocument]] = []

        # Build index of base keys for matching
        to_add_by_base = {extract_registry_key(f): f for f in to_add}
        to_delete_by_base = {extract_registry_key(f): f for f in to_delete}

        for base_key in set(to_add_by_base.keys()) & set(to_delete_by_base.keys()):
            # Same base key in both add and delete = version update
            old_filename = to_delete_by_base[base_key]
            new_filename = to_add_by_base[base_key]
            new_doc = self.awmf_pdfs[new_filename]

            to_update.append((old_filename, new_filename, new_doc))

            # Remove from add/delete lists
            to_add.remove(new_filename)
            to_delete.remove(old_filename)

        logger.info(f"Delta: +{len(to_add)} new, -{len(to_delete)} removed, ~{len(to_update)} updated")
        return to_add, to_delete, to_update

    async def _download_pdf(self, url: str) -> bytes:
        """Download PDF from AWMF URL."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def _upload_to_dify(self, filename: str, pdf_bytes: bytes) -> dict:
        """Upload PDF to Dify Knowledge Base."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
                tmp.write(pdf_bytes)
                tmp.flush()

                with open(tmp.name, "rb") as pdf_file:
                    files = {"file": (filename, pdf_file, "application/pdf")}
                    data = {
                        "data": json.dumps({
                            "indexing_technique": "high_quality",
                            "process_rule": {
                                "mode": "custom",
                                "rules": {
                                    "pre_processing_rules": [
                                        {"id": "remove_extra_spaces", "enabled": True},
                                        {"id": "remove_urls_emails", "enabled": False},
                                    ],
                                    "segmentation": {
                                        "separator": "\n\n",
                                        "max_tokens": 1000,
                                        "chunk_overlap": 200,
                                    },
                                },
                            },
                        })
                    }

                    response = await client.post(
                        f"{self.dify_url}/v1/datasets/{self.dify_dataset_id}/document/create_by_file",
                        headers={"Authorization": f"Bearer {self.dify_api_key}"},
                        files=files,
                        data=data,
                    )

                    if response.status_code != 200:
                        raise Exception(f"Dify upload failed ({response.status_code}): {response.text[:200]}")

                    return response.json()

    async def _delete_from_dify(self, document_id: str) -> bool:
        """Delete a document from Dify Knowledge Base."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.delete(
                f"{self.dify_url}/v1/datasets/{self.dify_dataset_id}/documents/{document_id}",
                headers={"Authorization": f"Bearer {self.dify_api_key}"}
            )
            return response.status_code == 200

    async def sync_new_pdfs(self, to_add: list[str], report: SyncReport):
        """
        Download new PDFs from AWMF, upload to S3, then to Dify.

        Rate limited: 10s delay between Dify uploads (Titan embeddings).
        """
        logger.info(f"Adding {len(to_add)} new PDFs...")

        for i, filename in enumerate(to_add):
            doc = self.awmf_pdfs[filename]
            logger.info(f"[{i+1}/{len(to_add)}] Adding: {filename}")

            if self.dry_run:
                report.added.append(filename)
                continue

            try:
                # Download from AWMF
                pdf_bytes = await self._download_pdf(doc.url)

                # Upload to S3
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=filename,
                    Body=pdf_bytes,
                    ContentType="application/pdf"
                )

                # Upload to Dify
                await self._upload_to_dify(filename, pdf_bytes)
                report.added.append(filename)

                await asyncio.sleep(10.0)  # Rate limit for embeddings

            except Exception as e:
                logger.error(f"Failed to add {filename}: {e}")
                report.errors.append({"filename": filename, "operation": "add", "error": str(e)})

    async def sync_deleted_pdfs(self, to_delete: list[str], report: SyncReport):
        """
        Remove PDFs that no longer exist on AWMF.

        Flow: Find Dify document ID → Delete from Dify → Delete from S3
        """
        logger.info(f"Deleting {len(to_delete)} removed PDFs...")

        for i, filename in enumerate(to_delete):
            logger.info(f"[{i+1}/{len(to_delete)}] Deleting: {filename}")

            if self.dry_run:
                report.deleted.append(filename)
                continue

            try:
                # Delete from Dify first (need document_id)
                doc_id = self.dify_docs.get(filename)
                if doc_id:
                    await self._delete_from_dify(doc_id)

                # Delete from S3
                self.s3_client.delete_object(Bucket=self.s3_bucket, Key=filename)
                report.deleted.append(filename)

                await asyncio.sleep(1.0)  # Small delay

            except Exception as e:
                logger.error(f"Failed to delete {filename}: {e}")
                report.errors.append({"filename": filename, "operation": "delete", "error": str(e)})

    async def sync_updated_pdfs(
        self,
        to_update: list[tuple[str, str, AWMFDocument]],
        report: SyncReport
    ):
        """
        Handle guideline version updates.

        Flow: Delete old version → Upload new version
        """
        logger.info(f"Updating {len(to_update)} PDFs...")

        for i, (old_filename, new_filename, new_doc) in enumerate(to_update):
            logger.info(f"[{i+1}/{len(to_update)}] Updating: {old_filename} → {new_filename}")

            if self.dry_run:
                report.updated.append((old_filename, new_filename))
                continue

            try:
                # Delete old from Dify
                old_doc_id = self.dify_docs.get(old_filename)
                if old_doc_id:
                    await self._delete_from_dify(old_doc_id)

                # Delete old from S3
                self.s3_client.delete_object(Bucket=self.s3_bucket, Key=old_filename)

                # Download new version
                pdf_bytes = await self._download_pdf(new_doc.url)

                # Upload new to S3
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=new_filename,
                    Body=pdf_bytes,
                    ContentType="application/pdf"
                )

                # Upload new to Dify
                await self._upload_to_dify(new_filename, pdf_bytes)
                report.updated.append((old_filename, new_filename))

                await asyncio.sleep(10.0)  # Rate limit for embeddings

            except Exception as e:
                logger.error(f"Failed to update {old_filename}: {e}")
                report.errors.append({
                    "filename": old_filename,
                    "new_filename": new_filename,
                    "operation": "update",
                    "error": str(e)
                })

    async def run_full_sync(self) -> SyncReport:
        """Execute complete sync workflow."""
        report = SyncReport()

        if self.dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")

        # 1. Crawl AWMF for current PDFs
        await self.crawl_awmf()
        report.awmf_total = len(self.awmf_pdfs)

        # 2. Get current S3 contents
        self.list_s3_pdfs()
        report.s3_before = len(self.s3_pdfs)

        # 3. Get current Dify documents
        await self.list_dify_documents()
        report.dify_before = len(self.dify_docs)

        # 4. Calculate deltas
        to_add, to_delete, to_update = self.calculate_deltas()

        # 5. Execute sync operations
        await self.sync_new_pdfs(to_add, report)
        await self.sync_deleted_pdfs(to_delete, report)
        await self.sync_updated_pdfs(to_update, report)

        # 6. Update counts (in dry-run these are projected)
        report.s3_after = report.s3_before + len(report.added) - len(report.deleted)
        report.dify_after = report.dify_before + len(report.added) - len(report.deleted)

        # 7. Finalize and save
        report.finalize()

        if not self.dry_run:
            self._save_state(report)

        return report


async def main():
    parser = argparse.ArgumentParser(description="AWMF Weekly Guidelines Sync")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without making them")
    parser.add_argument("--crawl-only", action="store_true", help="Only crawl AWMF, don't sync")
    args = parser.parse_args()

    # Validate configuration
    if not all([DIFY_URL, DIFY_DATASET_API_KEY, DIFY_DATASET_ID]):
        logger.error("Missing Dify configuration. Set DIFY_URL, DIFY_DATASET_API_KEY, DIFY_DATASET_ID")
        sys.exit(1)

    if not all([S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY]):
        logger.error("Missing S3 configuration. Set S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY")
        sys.exit(1)

    if args.crawl_only:
        # Just crawl and print results
        documents = await crawl_for_urls()
        print(f"\nFound {len(documents)} PDFs in AWMF registry")
        print("\nSample entries:")
        for i, (filename, doc) in enumerate(list(documents.items())[:10]):
            print(f"  {doc.registry_number}{doc.variant} | {doc.classification} | {doc.version_date} | {filename[:60]}...")
        sys.exit(0)

    syncer = AWMFWeeklySync(
        s3_endpoint=S3_ENDPOINT,
        s3_bucket=S3_BUCKET,
        s3_access_key=S3_ACCESS_KEY,
        s3_secret_key=S3_SECRET_KEY,
        dify_url=DIFY_URL,
        dify_dataset_api_key=DIFY_DATASET_API_KEY,
        dify_dataset_id=DIFY_DATASET_ID,
        dry_run=args.dry_run,
    )

    report = await syncer.run_full_sync()
    report.print_report()

    # Exit with error code if there were failures
    if report.errors:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
