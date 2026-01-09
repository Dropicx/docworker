"""
Database Migration: Add AI Analysis Columns to User Feedback

This migration adds the AI-powered quality analysis columns to the user_feedback table.
These columns support the Self-Improving Feedback Analysis feature.

Columns added:
- ai_analysis_status: Analysis status (PENDING, PROCESSING, COMPLETED, FAILED, SKIPPED)
- ai_analysis_text: Full AI analysis text
- ai_analysis_summary: Structured JSON summary
- ai_analysis_started_at: When analysis started
- ai_analysis_completed_at: When analysis completed
- ai_analysis_error: Error message if analysis failed

Usage:
    python -m app.database.migrations.add_feedback_ai_analysis_columns
"""

import logging
from sqlalchemy import text
from app.database.connection import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Add AI analysis columns to user_feedback table"""
    try:
        with engine.begin() as conn:
            logger.info("Starting migration: Add AI analysis columns to user_feedback...")

            # Check if columns already exist
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'user_feedback'
                AND column_name = 'ai_analysis_status'
            """))

            if result.fetchone():
                logger.info("AI analysis columns already exist, skipping migration")
                return True

            # Add ai_analysis_status column (VARCHAR for enum)
            logger.info("Adding ai_analysis_status column...")
            conn.execute(text("""
                ALTER TABLE user_feedback
                ADD COLUMN ai_analysis_status VARCHAR(20) DEFAULT NULL
            """))

            # Add ai_analysis_text column
            logger.info("Adding ai_analysis_text column...")
            conn.execute(text("""
                ALTER TABLE user_feedback
                ADD COLUMN ai_analysis_text TEXT DEFAULT NULL
            """))

            # Add ai_analysis_summary column (JSONB for PostgreSQL)
            logger.info("Adding ai_analysis_summary column...")
            conn.execute(text("""
                ALTER TABLE user_feedback
                ADD COLUMN ai_analysis_summary JSONB DEFAULT NULL
            """))

            # Add ai_analysis_started_at column
            logger.info("Adding ai_analysis_started_at column...")
            conn.execute(text("""
                ALTER TABLE user_feedback
                ADD COLUMN ai_analysis_started_at TIMESTAMP DEFAULT NULL
            """))

            # Add ai_analysis_completed_at column
            logger.info("Adding ai_analysis_completed_at column...")
            conn.execute(text("""
                ALTER TABLE user_feedback
                ADD COLUMN ai_analysis_completed_at TIMESTAMP DEFAULT NULL
            """))

            # Add ai_analysis_error column
            logger.info("Adding ai_analysis_error column...")
            conn.execute(text("""
                ALTER TABLE user_feedback
                ADD COLUMN ai_analysis_error TEXT DEFAULT NULL
            """))

            # Verify the migration
            logger.info("Verifying migration...")
            result = conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'user_feedback'
                AND column_name LIKE 'ai_analysis%'
                ORDER BY column_name
            """))

            columns = result.fetchall()
            logger.info(f"Migration successful! Added {len(columns)} columns:")
            for col in columns:
                logger.info(f"   {col[0]}: {col[1]}")

            return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    run_migration()
