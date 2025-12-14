"""
Migration: Encrypt Existing Document Content

Encrypts existing plaintext document content in the database:
- pipeline_jobs.file_content (binary)
- pipeline_step_executions.input_text (text)
- pipeline_step_executions.output_text (text)

This migration processes data in batches to avoid memory issues.
Supports dry-run mode for testing before actual migration.

Usage:
    # Dry run (test mode)
    python migrations/encrypt_existing_document_content.py --dry-run

    # Actual migration
    python migrations/encrypt_existing_document_content.py

    # With batch size override
    python migrations/encrypt_existing_document_content.py --batch-size 50
"""

import argparse
import logging
import sys
from datetime import datetime
from typing import Any

# Add backend to path
sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/home/catchmelit/Projects/doctranslator/backend")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.encryption import encryptor
from app.database.modular_pipeline_models import (
    PipelineJobDB,
    PipelineStepExecutionDB,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def check_encryption_enabled() -> bool:
    """Check if encryption is enabled."""
    if not encryptor.is_enabled():
        logger.error("Encryption is disabled. Enable it before running migration.")
        return False
    return True


def encrypt_pipeline_jobs(
    session: Any, batch_size: int = 100, dry_run: bool = False
) -> tuple[int, int]:
    """
    Encrypt file_content for all pipeline jobs.

    Args:
        session: Database session
        batch_size: Number of records to process per batch
        dry_run: If True, don't actually encrypt (just count)

    Returns:
        Tuple of (total_count, encrypted_count)
    """
    logger.info("=" * 80)
    logger.info("Encrypting pipeline_jobs.file_content")
    logger.info("=" * 80)

    try:
        # Count total jobs with file_content
        total_count = (
            session.query(PipelineJobDB)
            .filter(PipelineJobDB.file_content.isnot(None))
            .count()
        )

        logger.info(f"Found {total_count} jobs with file_content to encrypt")

        if total_count == 0:
            logger.info("No jobs to encrypt. Migration complete.")
            return 0, 0

        if dry_run:
            logger.info("DRY RUN: Would encrypt {total_count} jobs")
            return total_count, 0

        encrypted_count = 0
        offset = 0

        while offset < total_count:
            # Get batch of jobs
            jobs = (
                session.query(PipelineJobDB)
                .filter(PipelineJobDB.file_content.isnot(None))
                .offset(offset)
                .limit(batch_size)
                .all()
            )

            if not jobs:
                break

            logger.info(
                f"Processing batch: {offset + 1} to {min(offset + batch_size, total_count)} of {total_count}"
            )

            for job in jobs:
                try:
                    # Check if already encrypted (heuristic check)
                    file_content_bytes = job.file_content
                    if file_content_bytes is None:
                        continue

                    # Check if already encrypted
                    # Encrypted content is stored as UTF-8 bytes of base64-encoded Fernet token
                    if isinstance(file_content_bytes, bytes):
                        try:
                            file_content_str = file_content_bytes.decode("utf-8", errors="ignore")
                            if encryptor.is_encrypted(file_content_str):
                                logger.debug(
                                    f"Job {job.id} file_content appears already encrypted, skipping"
                                )
                                continue
                        except Exception:
                            pass  # Not decodable as UTF-8, might be binary - proceed with encryption

                        # Encrypt binary content (returns base64-encoded string)
                        encrypted_content_str = encryptor.encrypt_binary_field(file_content_bytes)

                        if encrypted_content_str:
                            # Store encrypted string as UTF-8 bytes (LargeBinary column accepts bytes)
                            job.file_content = encrypted_content_str.encode("utf-8")
                            encrypted_count += 1
                            logger.debug(f"Encrypted file_content for job {job.id}")
                        else:
                            logger.warning(f"Failed to encrypt file_content for job {job.id}")
                    else:
                        # Already a string (shouldn't happen for binary, but handle it)
                        logger.warning(
                            f"Job {job.id} file_content is not bytes, skipping encryption"
                        )

                except Exception as e:
                    logger.error(f"Error encrypting job {job.id}: {e}")
                    session.rollback()
                    continue

            # Commit batch
            try:
                session.commit()
                logger.info(f"Committed batch: {encrypted_count} jobs encrypted so far")
            except Exception as e:
                logger.error(f"Error committing batch: {e}")
                session.rollback()
                raise

            offset += batch_size

        logger.info(f"✅ Encrypted {encrypted_count} of {total_count} pipeline jobs")
        return total_count, encrypted_count

    except Exception as e:
        logger.error(f"Error in encrypt_pipeline_jobs: {e}")
        session.rollback()
        raise


def encrypt_step_executions(
    session: Any, batch_size: int = 100, dry_run: bool = False
) -> tuple[int, int]:
    """
    Encrypt input_text and output_text for all step executions.

    Args:
        session: Database session
        batch_size: Number of records to process per batch
        dry_run: If True, don't actually encrypt (just count)

    Returns:
        Tuple of (total_count, encrypted_count)
    """
    logger.info("=" * 80)
    logger.info("Encrypting pipeline_step_executions.input_text and output_text")
    logger.info("=" * 80)

    try:
        # Count total step executions with text content
        total_count = (
            session.query(PipelineStepExecutionDB)
            .filter(
                (PipelineStepExecutionDB.input_text.isnot(None))
                | (PipelineStepExecutionDB.output_text.isnot(None))
            )
            .count()
        )

        logger.info(f"Found {total_count} step executions with text content to encrypt")

        if total_count == 0:
            logger.info("No step executions to encrypt. Migration complete.")
            return 0, 0

        if dry_run:
            logger.info("DRY RUN: Would encrypt {total_count} step executions")
            return total_count, 0

        encrypted_count = 0
        offset = 0

        while offset < total_count:
            # Get batch of step executions
            executions = (
                session.query(PipelineStepExecutionDB)
                .filter(
                    (PipelineStepExecutionDB.input_text.isnot(None))
                    | (PipelineStepExecutionDB.output_text.isnot(None))
                )
                .offset(offset)
                .limit(batch_size)
                .all()
            )

            if not executions:
                break

            logger.info(
                f"Processing batch: {offset + 1} to {min(offset + batch_size, total_count)} of {total_count}"
            )

            for execution in executions:
                try:
                    # Encrypt input_text if present
                    if execution.input_text and not encryptor.is_encrypted(
                        execution.input_text
                    ):
                        execution.input_text = encryptor.encrypt_field(execution.input_text)
                        encrypted_count += 1
                        logger.debug(f"Encrypted input_text for execution {execution.id}")

                    # Encrypt output_text if present
                    if execution.output_text and not encryptor.is_encrypted(
                        execution.output_text
                    ):
                        execution.output_text = encryptor.encrypt_field(execution.output_text)
                        encrypted_count += 1
                        logger.debug(f"Encrypted output_text for execution {execution.id}")

                except Exception as e:
                    logger.error(f"Error encrypting execution {execution.id}: {e}")
                    session.rollback()
                    continue

            # Commit batch
            try:
                session.commit()
                logger.info(f"Committed batch: {encrypted_count} fields encrypted so far")
            except Exception as e:
                logger.error(f"Error committing batch: {e}")
                session.rollback()
                raise

            offset += batch_size

        logger.info(
            f"✅ Encrypted text fields in {encrypted_count} step executions (out of {total_count} total)"
        )
        return total_count, encrypted_count

    except Exception as e:
        logger.error(f"Error in encrypt_step_executions: {e}")
        session.rollback()
        raise


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Encrypt existing document content")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - don't actually encrypt, just count",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of records to process per batch (default: 100)",
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("Document Content Encryption Migration")
    logger.info("=" * 80)
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE MIGRATION'}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("")

    # Check encryption is enabled
    if not check_encryption_enabled():
        sys.exit(1)

    # Create database session
    try:
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            # Encrypt pipeline jobs
            jobs_total, jobs_encrypted = encrypt_pipeline_jobs(
                session, batch_size=args.batch_size, dry_run=args.dry_run
            )

            # Encrypt step executions
            executions_total, executions_encrypted = encrypt_step_executions(
                session, batch_size=args.batch_size, dry_run=args.dry_run
            )

            # Summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("Migration Summary")
            logger.info("=" * 80)
            logger.info(f"Pipeline Jobs: {jobs_encrypted}/{jobs_total} encrypted")
            logger.info(
                f"Step Executions: {executions_encrypted} fields encrypted (out of {executions_total} executions)"
            )

            if args.dry_run:
                logger.info("")
                logger.info("DRY RUN complete. Run without --dry-run to perform actual migration.")
            else:
                logger.info("")
                logger.info("✅ Migration complete!")

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

