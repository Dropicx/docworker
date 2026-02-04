#!/usr/bin/env python3
"""
Direct Database Migration Runner

Executes the authentication tables migration using the existing database connection.
This approach uses the application's database connection setup.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_migration_direct(database_url: str):
    """Run the migration using direct database connection"""
    try:
        # Set the database URL environment variable
        os.environ["DATABASE_URL"] = database_url

        logger.info(f"🚀 Starting authentication tables migration")
        logger.info(
            f"Database: {database_url.split('@')[1] if '@' in database_url else database_url}"
        )

        # Try to import and use the existing database connection
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.exc import SQLAlchemyError
        except ImportError:
            logger.error("SQLAlchemy not available. Trying alternative approach...")
            return run_migration_alternative(database_url)

        # Create database engine
        engine = create_engine(database_url)

        # Read the migration SQL file
        migration_file = project_root / "migrations" / "001_add_authentication_tables.sql"

        if not migration_file.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return False

        with open(migration_file, "r") as f:
            migration_sql = f.read()

        logger.info("📝 Running migration: 001_add_authentication_tables.sql")

        # Execute the migration
        with engine.connect() as connection:
            # Split SQL into individual statements
            statements = [stmt.strip() for stmt in migration_sql.split(";") if stmt.strip()]

            for i, statement in enumerate(statements, 1):
                if statement:
                    logger.info(f"  Executing statement {i}/{len(statements)}")
                    try:
                        connection.execute(text(statement))
                        connection.commit()
                    except SQLAlchemyError as e:
                        # Check if it's a "table already exists" error (idempotent)
                        if "already exists" in str(e).lower():
                            logger.warning(f"  Table already exists, skipping: {e}")
                            continue
                        else:
                            logger.error(f"  Statement failed: {e}")
                            logger.error(f"  Statement: {statement[:100]}...")
                            raise

        logger.info("✅ Migration completed successfully!")
        logger.info("Authentication tables have been created:")
        logger.info("  - users")
        logger.info("  - refresh_tokens")
        logger.info("  - api_keys")
        logger.info("  - audit_logs")
        logger.info("  - pipeline_jobs (updated with user_id columns)")
        logger.info("🎉 Authentication system is ready for deployment!")

        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_migration_alternative(database_url: str):
    """Alternative migration approach using basic Python libraries"""
    try:
        import urllib.parse
        import urllib.request
        import json

        logger.info("Trying alternative migration approach...")

        # Parse database URL
        parsed = urllib.parse.urlparse(database_url)

        # This is a fallback - we'll create a simple HTTP request
        # For now, let's just log what we would do
        logger.info("Alternative approach would require a REST API endpoint")
        logger.info("For now, please run the migration manually using:")
        logger.info(f"psql '{database_url}' -f migrations/001_add_authentication_tables.sql")

        return False

    except Exception as e:
        logger.error(f"Alternative approach failed: {e}")
        return False


if __name__ == "__main__":
    # Get database URL from environment or command line
    database_url = os.environ.get("DATABASE_URL")
    if len(sys.argv) > 1:
        database_url = sys.argv[1]

    if not database_url:
        logger.error(
            "No database URL provided. Set DATABASE_URL environment variable or pass as argument."
        )
        sys.exit(1)

    success = run_migration_direct(database_url)
    sys.exit(0 if success else 1)
