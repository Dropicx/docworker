"""
Database Migration: Add Step Metadata for Dynamic Branching

This migration adds the step_metadata JSON column to the pipeline_step_executions table
to support dynamic branching decisions and generic branching steps.

Features:
- Stores branching decisions (document_class, boolean, enum, generic)
- Enables complete audit trail of all pipeline branching
- Supports querying branching decisions across all executions

Usage:
    python -m app.database.migrations.add_step_metadata_migration
"""

import logging
from sqlalchemy import text
from app.database.connection import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Add step_metadata column to pipeline_step_executions table"""
    try:
        with engine.begin() as conn:
            logger.info("🔄 Starting migration: Add step_metadata for dynamic branching...")

            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'pipeline_step_executions'
                AND column_name = 'step_metadata'
            """))

            if result.fetchone():
                logger.info("✅ Column step_metadata already exists, skipping migration")
                return True

            # Add the column
            logger.info("📝 Adding step_metadata JSON column...")
            conn.execute(text("""
                ALTER TABLE pipeline_step_executions
                ADD COLUMN step_metadata JSON NULL
            """))

            # Backfill existing records with empty JSON for non-branching steps
            logger.info("🔄 Backfilling existing records...")
            conn.execute(text("""
                UPDATE pipeline_step_executions
                SET step_metadata = '{}'::json
                WHERE step_metadata IS NULL
            """))

            # Verify the migration
            logger.info("🔍 Verifying migration...")
            result = conn.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN step_metadata IS NOT NULL THEN 1 END) as with_metadata
                FROM pipeline_step_executions
            """))

            row = result.fetchone()
            logger.info(f"✅ Migration successful!")
            logger.info(f"   Total records: {row[0]}")
            logger.info(f"   Records with metadata: {row[1]}")

            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_migration()
