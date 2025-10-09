"""
Database Migration: Add required_context_variables for conditional execution

This migration adds the required_context_variables JSON column to dynamic_pipeline_steps
to support conditional step execution based on available context.

Example: Language Translation step requires 'target_language' to be present,
otherwise it will be skipped gracefully.

Usage:
    python -m app.database.migrations.add_required_context_variables
"""

import logging
from sqlalchemy import text
from app.database.connection import get_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade():
    """Add required_context_variables column"""
    engine = get_engine()

    try:
        with engine.connect() as conn:
            logger.info("🔄 Starting migration: Add required_context_variables...")

            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'dynamic_pipeline_steps'
                AND column_name = 'required_context_variables'
            """))

            if result.fetchone():
                logger.info("✅ Column required_context_variables already exists, skipping migration")
                return True

            # Add the column
            logger.info("📝 Adding required_context_variables JSON column...")
            conn.execute(text("""
                ALTER TABLE dynamic_pipeline_steps
                ADD COLUMN required_context_variables JSON DEFAULT NULL
            """))

            conn.commit()

            # Update Language Translation step to require target_language
            logger.info("🔧 Updating Language Translation step with required_context_variables...")
            conn.execute(text("""
                UPDATE dynamic_pipeline_steps
                SET required_context_variables = '["target_language"]'::json
                WHERE name LIKE '%Language Translation%'
                OR name LIKE '%Sprachübersetzung%'
                OR prompt_template LIKE '%{target_language}%'
            """))

            conn.commit()

            logger.info("✅ Migration successful!")
            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


def downgrade():
    """Remove required_context_variables column"""
    engine = get_engine()

    try:
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE dynamic_pipeline_steps
                DROP COLUMN IF EXISTS required_context_variables
            """))

            conn.commit()

            logger.info("✅ Migration reverted: Removed required_context_variables column")
            return True

    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "down":
        logger.info("🔄 Rolling back migration...")
        success = downgrade()
    else:
        logger.info("🚀 Running migration...")
        success = upgrade()

    sys.exit(0 if success else 1)
