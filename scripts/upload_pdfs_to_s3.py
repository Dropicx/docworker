"""
Upload AWMF PDFs from local filesystem to Hetzner Object Storage (S3-compatible).

One-time script to populate the Object Storage bucket with AWMF guideline PDFs.
The bucket serves as source-of-truth for re-ingestion into Dify Knowledge Base.

Usage:
    python scripts/upload_pdfs_to_s3.py

Environment Variables:
    S3_ENDPOINT: Object Storage endpoint (e.g., https://fsn1.your-objectstorage.com)
    S3_ACCESS_KEY: Object Storage access key
    S3_SECRET_KEY: Object Storage secret key
    S3_BUCKET: Bucket name (default: awmf-guidelines)
    PDF_SOURCE_DIR: Local directory with PDFs (default: rag/awmf_pdfs)
"""

import logging
import os
import sys
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuration
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET = os.getenv("S3_BUCKET", "awmf-guidelines")
PDF_SOURCE_DIR = os.getenv("PDF_SOURCE_DIR", "rag/awmf_pdfs")


def get_s3_client():
    """Create S3 client for Hetzner Object Storage."""
    if not all([S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY]):
        logger.error("Missing S3 configuration. Set S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY")
        sys.exit(1)

    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )


def list_existing_objects(s3_client: "boto3.client") -> set[str]:
    """List all existing objects in the bucket to support resume."""
    existing = set()
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=S3_BUCKET):
            for obj in page.get("Contents", []):
                existing.add(obj["Key"])
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchBucket":
            logger.error(f"Bucket '{S3_BUCKET}' does not exist. Create it first via Hetzner Console.")
            sys.exit(1)
        raise
    return existing


def upload_pdfs():
    """Upload all PDFs from local directory to Object Storage."""
    source_dir = Path(PDF_SOURCE_DIR)
    if not source_dir.exists():
        logger.error(f"Source directory not found: {source_dir}")
        sys.exit(1)

    pdf_files = sorted(source_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error(f"No PDF files found in {source_dir}")
        sys.exit(1)

    logger.info(f"Found {len(pdf_files)} PDF files in {source_dir}")

    s3_client = get_s3_client()

    # Get existing objects for resume support
    existing = list_existing_objects(s3_client)
    logger.info(f"Found {len(existing)} existing objects in bucket '{S3_BUCKET}'")

    uploaded = 0
    skipped = 0
    failed = 0

    for pdf_path in pdf_files:
        key = pdf_path.name

        if key in existing:
            skipped += 1
            continue

        try:
            s3_client.upload_file(
                str(pdf_path),
                S3_BUCKET,
                key,
                ExtraArgs={"ContentType": "application/pdf"},
            )
            uploaded += 1
            if uploaded % 100 == 0:
                logger.info(f"Progress: {uploaded} uploaded, {skipped} skipped, {failed} failed")
        except Exception as e:
            logger.error(f"Failed to upload {key}: {e}")
            failed += 1

    logger.info(
        f"Upload complete: {uploaded} uploaded, {skipped} skipped (already existed), {failed} failed"
    )
    logger.info(f"Total objects in bucket: {len(existing) + uploaded}")


if __name__ == "__main__":
    upload_pdfs()
