#!/usr/bin/env python3
"""
Simple Authentication Migration Runner

Runs the authentication tables migration using basic Python libraries.
This script doesn't require the full application dependencies.
"""

import os
import sys
import logging
from urllib.parse import urlparse

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_migration():
    """Run the authentication tables migration"""
    try:
        # Try to import psycopg2 (PostgreSQL adapter)
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    except ImportError:
        logger.error("psycopg2 not available. Trying alternative...")
        try:
            # Try psycopg2-binary
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        except ImportError:
            logger.error("No PostgreSQL adapter found. Please install psycopg2 or psycopg2-binary")
            return False

    # Get database URL from environment or command line
    database_url = os.environ.get("DATABASE_URL")
    if len(sys.argv) > 1:
        database_url = sys.argv[1]

    if not database_url:
        logger.error(
            "No database URL provided. Set DATABASE_URL environment variable or pass as argument."
        )
        return False

    logger.info(f"🚀 Starting authentication tables migration")
    logger.info(f"Database: {database_url.split('@')[1] if '@' in database_url else database_url}")

    try:
        # Parse database URL
        parsed_url = urlparse(database_url)

        # Connect to database
        conn = psycopg2.connect(
            host=parsed_url.hostname,
            port=parsed_url.port,
            database=parsed_url.path[1:],  # Remove leading slash
            user=parsed_url.username,
            password=parsed_url.password,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        logger.info("📝 Running migration: 001_add_authentication_tables.sql")

        # Read and execute the migration SQL
        migration_file = os.path.join(
            os.path.dirname(__file__), "..", "migrations", "001_add_authentication_tables.sql"
        )

        if not os.path.exists(migration_file):
            logger.error(f"Migration file not found: {migration_file}")
            return False

        with open(migration_file, "r") as f:
            migration_sql = f.read()

        # Split SQL into individual statements and execute them
        statements = [stmt.strip() for stmt in migration_sql.split(";") if stmt.strip()]

        for i, statement in enumerate(statements, 1):
            if statement:
                logger.info(f"  Executing statement {i}/{len(statements)}")
                try:
                    cursor.execute(statement)
                except Exception as e:
                    # Check if it's a "table already exists" error (idempotent)
                    if "already exists" in str(e).lower():
                        logger.warning(f"  Table already exists, skipping: {e}")
                        continue
                    else:
                        logger.error(f"  Statement failed: {e}")
                        logger.error(f"  Statement: {statement[:100]}...")
                        raise

        cursor.close()
        conn.close()

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


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
