"""
Upload AWMF PDFs from Hetzner Object Storage to Dify Knowledge Base.

Downloads PDFs from the S3-compatible Object Storage bucket and uploads them
to Dify's Knowledge Base via API for RAG indexing.

Usage:
    python scripts/dify_upload_pdfs.py

Environment Variables:
    DIFY_URL: Dify API URL (e.g., https://rag.fra-la.de)
    DIFY_DATASET_API_KEY: Dify dataset API key
    DIFY_DATASET_ID: Target knowledge base ID
    S3_ENDPOINT: Object Storage endpoint
    S3_ACCESS_KEY: Object Storage access key
    S3_SECRET_KEY: Object Storage secret key
    S3_BUCKET: Bucket name (default: awmf-guidelines)
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

import boto3
import httpx
from botocore.config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuration
DIFY_URL = os.getenv("DIFY_URL", "")
DIFY_DATASET_API_KEY = os.getenv("DIFY_DATASET_API_KEY", "")
DIFY_DATASET_ID = os.getenv("DIFY_DATASET_ID", "")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET = os.getenv("S3_BUCKET", "awmf-guidelines")

STATE_FILE = Path("scripts/.dify_upload_state.json")


class DifyPDFUploader:
    """Upload AWMF PDFs from Object Storage to Dify knowledge base."""

    def __init__(
        self,
        dify_url: str,
        dataset_api_key: str,
        dataset_id: str,
        s3_endpoint: str,
        s3_bucket: str,
        s3_access_key: str,
        s3_secret_key: str,
    ):
        self.dify_url = dify_url.rstrip("/")
        self.dataset_api_key = dataset_api_key
        self.dataset_id = dataset_id
        self.s3_bucket = s3_bucket

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=s3_endpoint,
            aws_access_key_id=s3_access_key,
            aws_secret_access_key=s3_secret_key,
            config=Config(signature_version="s3v4"),
        )

        self._state = self._load_state()

    def _load_state(self) -> dict:
        """Load upload state for resume support."""
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
        return {"uploaded": [], "failed": [], "last_key": ""}

    def _save_state(self):
        """Persist upload state."""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(self._state, f, indent=2)

    def list_s3_pdfs(self) -> list[str]:
        """List all PDF keys in the S3 bucket."""
        keys = []
        paginator = self.s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.s3_bucket):
            for obj in page.get("Contents", []):
                if obj["Key"].lower().endswith(".pdf"):
                    keys.append(obj["Key"])
        return sorted(keys)

    async def upload_single(self, pdf_key: str) -> dict:
        """Download PDF from S3 and upload to Dify Knowledge Base."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            # Download from S3
            self.s3_client.download_file(self.s3_bucket, pdf_key, tmp.name)

            # Upload to Dify via multipart form
            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(tmp.name, "rb") as pdf_file:
                    files = {"file": (pdf_key, pdf_file, "application/pdf")}
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
                        f"{self.dify_url}/v1/datasets/{self.dataset_id}/document/create_by_file",
                        headers={"Authorization": f"Bearer {self.dataset_api_key}"},
                        files=files,
                        data=data,
                    )

                    if response.status_code == 200:
                        return response.json()
                    else:
                        raise Exception(
                            f"Dify upload failed ({response.status_code}): {response.text[:200]}"
                        )

    async def upload_all(self, delay: float = 1.0):
        """List PDFs from S3, download each, upload to Dify with resume."""
        pdf_keys = self.list_s3_pdfs()
        logger.info(f"Found {len(pdf_keys)} PDFs in S3 bucket '{self.s3_bucket}'")

        # Filter already uploaded
        already_uploaded = set(self._state.get("uploaded", []))
        pending = [k for k in pdf_keys if k not in already_uploaded]
        logger.info(f"Pending: {len(pending)} (already uploaded: {len(already_uploaded)})")

        uploaded = 0
        failed = 0

        for i, key in enumerate(pending):
            try:
                logger.info(f"[{i + 1}/{len(pending)}] Uploading: {key}")
                result = await self.upload_single(key)
                self._state["uploaded"].append(key)
                self._state["last_key"] = key
                uploaded += 1

                if uploaded % 10 == 0:
                    self._save_state()
                    logger.info(f"Progress saved: {uploaded} uploaded, {failed} failed")

            except Exception as e:
                logger.error(f"Failed to upload {key}: {e}")
                self._state["failed"].append({"key": key, "error": str(e)})
                failed += 1

            # Rate limiting
            await asyncio.sleep(delay)

        # Final save
        self._save_state()
        logger.info(f"Upload complete: {uploaded} uploaded, {failed} failed")
        logger.info(f"Total in knowledge base: {len(self._state['uploaded'])}")

        if failed > 0:
            logger.warning(f"Failed uploads saved to {STATE_FILE} for retry")


async def main():
    """Run the PDF upload process."""
    if not all([DIFY_URL, DIFY_DATASET_API_KEY, DIFY_DATASET_ID]):
        logger.error("Missing Dify configuration. Set DIFY_URL, DIFY_DATASET_API_KEY, DIFY_DATASET_ID")
        sys.exit(1)

    if not all([S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY]):
        logger.error("Missing S3 configuration. Set S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY")
        sys.exit(1)

    uploader = DifyPDFUploader(
        dify_url=DIFY_URL,
        dataset_api_key=DIFY_DATASET_API_KEY,
        dataset_id=DIFY_DATASET_ID,
        s3_endpoint=S3_ENDPOINT,
        s3_bucket=S3_BUCKET,
        s3_access_key=S3_ACCESS_KEY,
        s3_secret_key=S3_SECRET_KEY,
    )

    await uploader.upload_all(delay=1.0)


if __name__ == "__main__":
    asyncio.run(main())
