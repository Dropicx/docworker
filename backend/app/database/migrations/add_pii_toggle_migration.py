"""
Database Migration: Add PII Removal Toggle

This migration adds the pii_removal_enabled column to the ocr_configuration table.

Usage:
    python -m app.database.migrations.add_pii_toggle_migration
"""

import logging
from sqlalchemy import text
from app.database.connection import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Add pii_removal_enabled column to ocr_configuration table"""
    try:
        with engine.begin() as conn:
            logger.info("🔄 Starting migration: Add PII removal toggle...")

            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'ocr_configuration'
                AND column_name = 'pii_removal_enabled'
            """))

            if result.fetchone():
                logger.info("✅ Column pii_removal_enabled already exists, skipping migration")
                return True

            # Add the column
            logger.info("📝 Adding pii_removal_enabled column...")
            conn.execute(text("""
                ALTER TABLE ocr_configuration
                ADD COLUMN pii_removal_enabled BOOLEAN NOT NULL DEFAULT TRUE
            """))

            # Verify the migration
            logger.info("🔍 Verifying migration...")
            result = conn.execute(text("""
                SELECT id, selected_engine, pii_removal_enabled, last_modified
                FROM ocr_configuration
            """))

            rows = result.fetchall()
            logger.info(f"✅ Migration successful! Updated {len(rows)} row(s)")

            for row in rows:
                logger.info(f"   ID {row[0]}: engine={row[1]}, pii_enabled={row[2]}")

            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_migration()
