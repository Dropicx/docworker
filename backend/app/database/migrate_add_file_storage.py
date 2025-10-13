"""
Migration: Add file storage fields to pipeline_jobs table

This migration adds columns for storing uploaded documents directly in the database:
- filename: Original filename
- file_type: Document type (pdf, jpg, png)
- file_size: File size in bytes
- file_content: Binary file data (BLOB)
- client_ip: Client IP for security logging
- uploaded_at: Upload timestamp
"""

import logging

from sqlalchemy import create_engine, text

from app.core.config import settings

logger = logging.getLogger(__name__)

def migrate_add_file_storage():
    """Add file storage columns to pipeline_jobs table"""
    try:
        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()

            try:
                # Add filename column
                conn.execute(text("""
                    ALTER TABLE pipeline_jobs
                    ADD COLUMN IF NOT EXISTS filename VARCHAR(255) NOT NULL DEFAULT 'unknown.pdf'
                """))

                # Add file_type column
                conn.execute(text("""
                    ALTER TABLE pipeline_jobs
                    ADD COLUMN IF NOT EXISTS file_type VARCHAR(50) NOT NULL DEFAULT 'pdf'
                """))

                # Add file_size column
                conn.execute(text("""
                    ALTER TABLE pipeline_jobs
                    ADD COLUMN IF NOT EXISTS file_size INTEGER NOT NULL DEFAULT 0
                """))

                # Add file_content column (BYTEA for PostgreSQL, BLOB for SQLite)
                conn.execute(text("""
                    ALTER TABLE pipeline_jobs
                    ADD COLUMN IF NOT EXISTS file_content BYTEA
                """))

                # Add client_ip column
                conn.execute(text("""
                    ALTER TABLE pipeline_jobs
                    ADD COLUMN IF NOT EXISTS client_ip VARCHAR(100)
                """))

                # Add uploaded_at column
                conn.execute(text("""
                    ALTER TABLE pipeline_jobs
                    ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                """))

                # Commit transaction
                trans.commit()

                logger.info("✅ Migration successful: Added file storage columns to pipeline_jobs")
                print("✅ Migration successful: Added file storage columns to pipeline_jobs")
                return True

            except Exception as e:
                # Rollback on error
                trans.rollback()
                logger.error(f"❌ Migration failed: {e}")
                print(f"❌ Migration failed: {e}")
                return False

    except Exception as e:
        logger.error(f"❌ Migration error: {e}")
        print(f"❌ Migration error: {e}")
        return False

if __name__ == "__main__":
    import sys

    print("Running migration: Add file storage to pipeline_jobs")
    success = migrate_add_file_storage()

    if success:
        print("✅ Migration completed successfully")
        sys.exit(0)
    else:
        print("❌ Migration failed")
        sys.exit(1)
