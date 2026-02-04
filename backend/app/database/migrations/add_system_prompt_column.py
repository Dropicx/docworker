"""
Migration: Add system_prompt column to dynamic_pipeline_steps

Adds a system_prompt TEXT column for prompt injection defense via
system/user role separation. The system_prompt holds instruction text
while prompt_template holds the user-facing content with {input_text}.

Steps without a system_prompt set continue to work as before (single
user message).
"""

import logging
import sys

from sqlalchemy import text

from app.database.connection import get_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Add system_prompt column to dynamic_pipeline_steps table."""
    engine = get_engine()

    with engine.connect() as conn:
        # Check if column already exists
        try:
            result = conn.execute(
                text("SELECT system_prompt FROM dynamic_pipeline_steps LIMIT 1")
            )
            result.fetchone()
            logger.info("Column 'system_prompt' already exists — skipping migration.")
            return
        except Exception:
            conn.rollback()

        # Add the column
        logger.info("Adding 'system_prompt' column to 'dynamic_pipeline_steps'...")
        conn.execute(
            text("ALTER TABLE dynamic_pipeline_steps ADD COLUMN system_prompt TEXT")
        )
        conn.commit()
        logger.info("Migration completed: system_prompt column added.")


if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
