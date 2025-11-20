"""
Database Migration: Add Quality Gate Fields

This migration adds quality gate configuration fields to the ocr_configuration table:
- min_ocr_confidence_threshold: Minimum confidence score for accepting documents (0.0-1.0)
- enable_markdown_tables: Toggle for markdown table formatting

Usage:
    python -m app.database.migrations.add_quality_gate_migration
"""

import logging

from sqlalchemy import text

from app.database.connection import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Add quality gate fields to ocr_configuration table"""
    try:
        with engine.begin() as conn:
            logger.info("🔄 Starting migration: Add quality gate configuration...")

            # Check if min_ocr_confidence_threshold column already exists
            result = conn.execute(
                text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'ocr_configuration'
                AND column_name = 'min_ocr_confidence_threshold'
            """)
            )

            if result.fetchone():
                logger.info(
                    "✅ Column min_ocr_confidence_threshold already exists, skipping migration"
                )
                return True

            # Add min_ocr_confidence_threshold column
            logger.info("📝 Adding min_ocr_confidence_threshold column...")
            conn.execute(
                text("""
                ALTER TABLE ocr_configuration
                ADD COLUMN min_ocr_confidence_threshold FLOAT NOT NULL DEFAULT 0.5
            """)
            )

            # Add enable_markdown_tables column
            logger.info("📝 Adding enable_markdown_tables column...")
            conn.execute(
                text("""
                ALTER TABLE ocr_configuration
                ADD COLUMN enable_markdown_tables BOOLEAN NOT NULL DEFAULT TRUE
            """)
            )

            # Verify the migration
            logger.info("🔍 Verifying migration...")
            result = conn.execute(
                text("""
                SELECT id, selected_engine, min_ocr_confidence_threshold,
                       enable_markdown_tables, last_modified
                FROM ocr_configuration
            """)
            )

            rows = result.fetchall()
            logger.info(f"✅ Migration successful! Updated {len(rows)} row(s)")

            for row in rows:
                logger.info(
                    f"   ID {row[0]}: engine={row[1]}, threshold={row[2]}, "
                    f"markdown={row[3]}"
                )

            logger.info(
                "\n🎯 Quality Gate Configuration:\n"
                f"   - Min Confidence Threshold: 0.5 (50%)\n"
                f"   - Markdown Tables: Enabled\n"
                f"\n💡 Tip: Adjust threshold via admin UI or database:\n"
                f"   UPDATE ocr_configuration SET min_ocr_confidence_threshold = 0.7;"
            )

            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    run_migration()
