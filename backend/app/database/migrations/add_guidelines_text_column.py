"""
Database Migration: Add guidelines_text Column to Pipeline Jobs

This migration adds the guidelines_text column to the pipeline_jobs table
for caching AWMF guidelines with GDPR-compliant consent flow.

The guidelines follow the same GDPR pattern as other medical content:
- When user gives consent (feedback with consent=true) → guidelines preserved
- When user declines or leaves without feedback → guidelines cleared

Usage:
    python -m app.database.migrations.add_guidelines_text_column
"""

import logging
from sqlalchemy import text
from app.database.connection import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Add guidelines_text column to pipeline_jobs table"""
    try:
        with engine.begin() as conn:
            logger.info("Starting migration: Add guidelines_text column to pipeline_jobs...")

            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'pipeline_jobs'
                AND column_name = 'guidelines_text'
            """))

            if result.fetchone():
                logger.info("guidelines_text column already exists, skipping migration")
                return True

            # Add guidelines_text column
            logger.info("Adding guidelines_text column...")
            conn.execute(text("""
                ALTER TABLE pipeline_jobs
                ADD COLUMN guidelines_text TEXT DEFAULT NULL
            """))

            # Verify the migration
            logger.info("Verifying migration...")
            result = conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'pipeline_jobs'
                AND column_name = 'guidelines_text'
            """))

            column = result.fetchone()
            if column:
                logger.info(f"Migration successful! Added column: {column[0]} ({column[1]})")
            else:
                logger.error("Migration verification failed - column not found")
                return False

            return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    run_migration()
