"""
Database Migration: Add Guidelines Analysis Toggle

This migration adds the guidelines_analysis_enabled column to the ocr_configuration table.

Usage:
    python -m app.database.migrations.add_guidelines_toggle
"""

import logging
from sqlalchemy import text
from app.database.connection import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Add guidelines_analysis_enabled column to ocr_configuration table"""
    try:
        with engine.begin() as conn:
            logger.info("🔄 Starting migration: Add guidelines analysis toggle...")

            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'ocr_configuration'
                AND column_name = 'guidelines_analysis_enabled'
            """))

            if result.fetchone():
                logger.info("✅ Column guidelines_analysis_enabled already exists, skipping migration")
                return True

            # Add the column
            logger.info("📝 Adding guidelines_analysis_enabled column...")
            conn.execute(text("""
                ALTER TABLE ocr_configuration
                ADD COLUMN guidelines_analysis_enabled BOOLEAN NOT NULL DEFAULT TRUE
            """))

            # Verify the migration
            logger.info("🔍 Verifying migration...")
            result = conn.execute(text("""
                SELECT id, selected_engine, guidelines_analysis_enabled, last_modified
                FROM ocr_configuration
            """))

            rows = result.fetchall()
            logger.info(f"✅ Migration successful! Updated {len(rows)} row(s)")

            for row in rows:
                logger.info(f"   ID {row[0]}: engine={row[1]}, guidelines_enabled={row[2]}")

            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_migration()
