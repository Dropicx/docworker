"""
Database Migration Runner

Executes all pending migrations on a target database.
Migrations are idempotent and safe to run multiple times.

Usage:
    python run_migrations.py <database_url>

Example:
    python run_migrations.py postgresql://user:pass@host:port/db
"""

import sys
import os
import logging
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_migration_on_database(database_url: str, migration_name: str, migration_func):
    """Execute a single migration on the specified database"""
    try:
        # Temporarily override DATABASE_URL for this migration
        original_db_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = database_url

        logger.info(f"📝 Running migration: {migration_name}")
        result = migration_func()

        # Restore original DATABASE_URL
        if original_db_url:
            os.environ['DATABASE_URL'] = original_db_url
        elif 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']

        return result
    except Exception as e:
        logger.error(f"❌ Migration {migration_name} failed: {e}")
        return False


def run_all_migrations(database_url: str):
    """Run all migrations on the specified database"""
    logger.info(f"🚀 Starting migrations on database")
    logger.info(f"   Database: {database_url.split('@')[1] if '@' in database_url else database_url}")

    # Set DATABASE_URL environment variable
    os.environ['DATABASE_URL'] = database_url

    # Import migration modules
    from app.database.migrations.add_pii_toggle_migration import run_migration as pii_toggle_migration
    from app.database.migrations.add_step_metadata_migration import run_migration as step_metadata_migration
    from app.database.migrations.add_stop_conditions import upgrade as stop_conditions_migration
    from app.database.migrations.add_post_branching_column import migrate_up as post_branching_migration

    migrations = [
        ("add_pii_toggle", pii_toggle_migration),
        ("add_step_metadata", step_metadata_migration),
        ("add_stop_conditions", stop_conditions_migration),
        ("add_post_branching", post_branching_migration),
    ]

    results = []
    for migration_name, migration_func in migrations:
        success = run_migration_on_database(database_url, migration_name, migration_func)
        results.append((migration_name, success))

    # Print summary
    logger.info("\n" + "="*60)
    logger.info("📊 Migration Summary")
    logger.info("="*60)

    all_successful = True
    for migration_name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"   {status}: {migration_name}")
        if not success:
            all_successful = False

    logger.info("="*60)

    if all_successful:
        logger.info("🎉 All migrations completed successfully!")
        return True
    else:
        logger.error("⚠️ Some migrations failed. Please review the logs above.")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("❌ Usage: python run_migrations.py <database_url>")
        logger.info("\nExample:")
        logger.info("  python run_migrations.py postgresql://user:pass@host:port/database")
        sys.exit(1)

    database_url = sys.argv[1]

    try:
        success = run_all_migrations(database_url)
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
