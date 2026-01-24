"""
Migration: Add ui_stage column to dynamic_pipeline_steps

Maps each pipeline step to a frontend UI progress card stage.
Valid values: ocr, validation, classification, translation, quality, formatting

Usage:
    python -m app.database.migrations.add_ui_stage_column
"""

import sys
import logging
from sqlalchemy import text

sys.path.insert(0, '/Users/litmac/Documents/doctranslator/backend')

from app.database.connection import get_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Step name -> ui_stage mapping for existing rows
STEP_STAGE_MAP = {
    "Medical Content Validation": "validation",
    "Document Classification": "classification",
    "Patient-Friendly Translation": "translation",
    "Vereinfachung Arztbrief": "translation",
    "Vereinfachung Befundbericht": "translation",
    "Vereinfachung Laborwerte": "translation",
    "Medical Fact Check": "quality",
    "Grammar and Spelling Check": "quality",
    "Language Translation": "quality",
    "Final Quality Check": "quality",
    "Finaler Check auf Richtigkeit": "quality",
    "Text Formatting": "formatting",
}


def migrate_up():
    """Add ui_stage column and populate existing rows."""

    engine = get_engine()

    add_column_sql = """
    ALTER TABLE dynamic_pipeline_steps
    ADD COLUMN IF NOT EXISTS ui_stage VARCHAR(30) NOT NULL DEFAULT 'translation';
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(add_column_sql))

            # Update existing rows based on step names
            for step_name, stage in STEP_STAGE_MAP.items():
                conn.execute(
                    text(
                        "UPDATE dynamic_pipeline_steps SET ui_stage = :stage WHERE name = :name"
                    ),
                    {"stage": stage, "name": step_name},
                )

            conn.commit()
            logger.info("Migration complete: Added ui_stage column")
            logger.info("   - Column: ui_stage VARCHAR(30) DEFAULT 'translation'")
            logger.info(f"   - Updated {len(STEP_STAGE_MAP)} existing rows")
            return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def migrate_down():
    """Remove ui_stage column (rollback)."""

    engine = get_engine()

    rollback_sql = """
    ALTER TABLE dynamic_pipeline_steps
    DROP COLUMN IF EXISTS ui_stage;
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(rollback_sql))
            conn.commit()
            logger.info("Rollback complete: Removed ui_stage column")
            return True

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return False


def verify_migration():
    """Verify the migration was successful."""

    engine = get_engine()

    verify_sql = """
    SELECT column_name, data_type, column_default, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'dynamic_pipeline_steps'
    AND column_name = 'ui_stage';
    """

    try:
        with engine.connect() as conn:
            result = conn.execute(text(verify_sql))
            row = result.fetchone()

            if row:
                logger.info("Migration verified:")
                logger.info(f"   Column: {row[0]}")
                logger.info(f"   Type: {row[1]}")
                logger.info(f"   Default: {row[2]}")
                logger.info(f"   Nullable: {row[3]}")
                return True
            else:
                logger.error("Verification failed: Column not found")
                return False

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "down":
        logger.info("Rolling back migration...")
        success = migrate_down()
    elif len(sys.argv) > 1 and sys.argv[1] == "verify":
        logger.info("Verifying migration...")
        success = verify_migration()
    else:
        logger.info("Running migration...")
        success = migrate_up()

        if success:
            logger.info("Verifying migration...")
            verify_migration()

    sys.exit(0 if success else 1)
