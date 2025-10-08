"""
Migration: Add post_branching column to dynamic_pipeline_steps

This migration adds support for post-branching pipeline steps that run
after document-specific processing is complete.

Usage:
    python -m app.database.migrations.add_post_branching_column
"""

import sys
import logging
from sqlalchemy import text

# Add parent directory to path for imports
sys.path.insert(0, '/Users/litmac/Documents/doctranslator/backend')

from app.database.connection import get_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_up():
    """Add post_branching column to dynamic_pipeline_steps table."""

    engine = get_engine()

    migration_sql = """
    -- Add post_branching column with default FALSE
    ALTER TABLE dynamic_pipeline_steps
    ADD COLUMN IF NOT EXISTS post_branching BOOLEAN NOT NULL DEFAULT FALSE;

    -- Create index for performance
    CREATE INDEX IF NOT EXISTS ix_dynamic_pipeline_steps_post_branching
    ON dynamic_pipeline_steps(post_branching);

    -- Add comment for documentation
    COMMENT ON COLUMN dynamic_pipeline_steps.post_branching IS
    'When TRUE, this universal step runs after document-specific processing. When FALSE (default), it runs before branching.';
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(migration_sql))
            conn.commit()
            logger.info("✅ Migration complete: Added post_branching column")
            logger.info("   - Column: post_branching BOOLEAN DEFAULT FALSE")
            logger.info("   - Index: ix_dynamic_pipeline_steps_post_branching")
            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


def migrate_down():
    """Remove post_branching column (rollback)."""

    engine = get_engine()

    rollback_sql = """
    -- Drop index
    DROP INDEX IF EXISTS ix_dynamic_pipeline_steps_post_branching;

    -- Drop column
    ALTER TABLE dynamic_pipeline_steps
    DROP COLUMN IF EXISTS post_branching;
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(rollback_sql))
            conn.commit()
            logger.info("✅ Rollback complete: Removed post_branching column")
            return True

    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        return False


def verify_migration():
    """Verify the migration was successful."""

    engine = get_engine()

    verify_sql = """
    SELECT column_name, data_type, column_default, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'dynamic_pipeline_steps'
    AND column_name = 'post_branching';
    """

    try:
        with engine.connect() as conn:
            result = conn.execute(text(verify_sql))
            row = result.fetchone()

            if row:
                logger.info("✅ Migration verified:")
                logger.info(f"   Column: {row[0]}")
                logger.info(f"   Type: {row[1]}")
                logger.info(f"   Default: {row[2]}")
                logger.info(f"   Nullable: {row[3]}")
                return True
            else:
                logger.error("❌ Verification failed: Column not found")
                return False

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "down":
        logger.info("🔄 Rolling back migration...")
        success = migrate_down()
    elif len(sys.argv) > 1 and sys.argv[1] == "verify":
        logger.info("🔍 Verifying migration...")
        success = verify_migration()
    else:
        logger.info("🚀 Running migration...")
        success = migrate_up()

        if success:
            logger.info("🔍 Verifying migration...")
            verify_migration()

    sys.exit(0 if success else 1)
