#!/usr/bin/env python3
"""
Migration Verification Script

Verifies that the authentication tables migration was successful.
This script can be run after the migration to confirm everything is working.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_migration(database_url: str):
    """Verify that the migration was successful"""
    try:
        # Set the database URL environment variable
        os.environ['DATABASE_URL'] = database_url
        
        logger.info(f"🔍 Verifying authentication tables migration")
        logger.info(f"Database: {database_url.split('@')[1] if '@' in database_url else database_url}")

        # Try to import and use the existing database connection
        try:
            from sqlalchemy import create_engine, text
        except ImportError:
            logger.error("SQLAlchemy not available. Cannot verify migration.")
            return False

        # Create database engine
        engine = create_engine(database_url)
        
        # Tables that should exist after migration
        expected_tables = [
            'users',
            'refresh_tokens', 
            'api_keys',
            'audit_logs'
        ]
        
        # Check if tables exist
        with engine.connect() as connection:
            # Get list of tables
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            
            existing_tables = [row[0] for row in result]
            
            logger.info("📊 Found tables in database:")
            for table in existing_tables:
                logger.info(f"  ✓ {table}")
            
            # Check if all expected tables exist
            missing_tables = []
            for table in expected_tables:
                if table in existing_tables:
                    logger.info(f"✅ {table} table exists")
                else:
                    logger.error(f"❌ {table} table missing")
                    missing_tables.append(table)
            
            # Check if pipeline_jobs has user_id column
            try:
                result = connection.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'pipeline_jobs' 
                    AND column_name = 'user_id'
                """))
                
                user_id_column = result.fetchone()
                if user_id_column:
                    logger.info(f"✅ pipeline_jobs.user_id column exists ({user_id_column[1]}, nullable: {user_id_column[2]})")
                else:
                    logger.error("❌ pipeline_jobs.user_id column missing")
                    missing_tables.append("pipeline_jobs.user_id")
            except Exception as e:
                logger.warning(f"Could not check pipeline_jobs.user_id: {e}")
            
            if missing_tables:
                logger.error(f"❌ Migration incomplete. Missing: {', '.join(missing_tables)}")
                return False
            else:
                logger.info("🎉 All authentication tables and columns are present!")
                logger.info("✅ Migration verification successful!")
                return True

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Get database URL from environment or command line
    database_url = os.environ.get('DATABASE_URL')
    if len(sys.argv) > 1:
        database_url = sys.argv[1]
    
    if not database_url:
        logger.error("No database URL provided. Set DATABASE_URL environment variable or pass as argument.")
        sys.exit(1)

    success = verify_migration(database_url)
    sys.exit(0 if success else 1)
