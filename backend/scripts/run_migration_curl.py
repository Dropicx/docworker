#!/usr/bin/env python3
"""
Curl-based Database Migration Runner

Executes the authentication tables migration using curl to connect to PostgreSQL.
This approach doesn't require Python database drivers.
"""

import os
import sys
import subprocess
import tempfile
import logging
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration_with_curl(database_url: str):
    """Run the migration using curl to execute SQL"""
    try:
        # Parse database URL
        parsed_url = urlparse(database_url)
        
        # Extract connection details
        host = parsed_url.hostname
        port = parsed_url.port or 5432
        database = parsed_url.path[1:]  # Remove leading slash
        user = parsed_url.username
        password = parsed_url.password
        
        logger.info(f"🚀 Starting authentication tables migration")
        logger.info(f"Database: {host}:{port}/{database}")
        logger.info(f"User: {user}")

        # Read the migration SQL file
        migration_file = os.path.join(os.path.dirname(__file__), '..', 'migrations', '001_add_authentication_tables.sql')
        
        if not os.path.exists(migration_file):
            logger.error(f"Migration file not found: {migration_file}")
            return False

        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        # Create a temporary SQL file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
            temp_file.write(migration_sql)
            temp_file_path = temp_file.name

        try:
            # Use psql via curl (if available) or direct psql command
            # First try to find psql
            psql_paths = ['/usr/bin/psql', '/usr/local/bin/psql', 'psql']
            psql_cmd = None
            
            for path in psql_paths:
                try:
                    result = subprocess.run([path, '--version'], capture_output=True, text=True)
                    if result.returncode == 0:
                        psql_cmd = path
                        break
                except FileNotFoundError:
                    continue
            
            if not psql_cmd:
                logger.error("psql command not found. Please install PostgreSQL client tools.")
                return False

            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = password

            # Execute the migration
            logger.info("📝 Running migration: 001_add_authentication_tables.sql")
            
            cmd = [
                psql_cmd,
                '-h', host,
                '-p', str(port),
                '-U', user,
                '-d', database,
                '-f', temp_file_path,
                '-v', 'ON_ERROR_STOP=1'
            ]
            
            logger.info(f"Executing: {' '.join(cmd[:6])}...")
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                logger.info("✅ Migration completed successfully!")
                logger.info("Authentication tables have been created:")
                logger.info("  - users")
                logger.info("  - refresh_tokens")
                logger.info("  - api_keys")
                logger.info("  - audit_logs")
                logger.info("  - pipeline_jobs (updated with user_id columns)")
                logger.info("🎉 Authentication system is ready for deployment!")
                
                if result.stdout:
                    logger.info("Migration output:")
                    logger.info(result.stdout)
                
                return True
            else:
                logger.error(f"❌ Migration failed with return code {result.returncode}")
                logger.error("Error output:")
                logger.error(result.stderr)
                return False

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
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

    success = run_migration_with_curl(database_url)
    sys.exit(0 if success else 1)
