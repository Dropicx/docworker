#!/usr/bin/env python3
"""
Database Migration Runner

This script runs the authentication tables migration.
It can be used for both local development and production deployment.

Usage:
    python scripts/run_migration.py [--dry-run]
"""

import argparse
import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.database.connection import get_session
from sqlalchemy import text

def run_migration(dry_run=False):
    """Run the authentication tables migration."""
    try:
        # Read migration file
        migration_file = backend_dir / "migrations" / "001_add_authentication_tables.sql"
        
        if not migration_file.exists():
            print(f"Error: Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        if dry_run:
            print("DRY RUN: Would execute the following SQL:")
            print("-" * 60)
            print(migration_sql)
            print("-" * 60)
            return True
        
        # Get database session
        db = next(get_session())
        
        try:
            # Execute migration
            print("Running authentication tables migration...")
            db.execute(text(migration_sql))
            db.commit()
            
            print("✅ Migration completed successfully!")
            print("Created tables:")
            print("  - users (user accounts with RBAC)")
            print("  - refresh_tokens (JWT refresh token storage)")
            print("  - api_keys (API key management)")
            print("  - audit_logs (comprehensive audit trail)")
            print("  - Added user_id columns to pipeline_jobs")
            
            return True
            
        except Exception as e:
            db.rollback()
            print(f"❌ Migration failed: {e}")
            return False
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        return False

def check_migration_status():
    """Check if migration has already been applied."""
    try:
        db = next(get_session())
        
        try:
            # Check if users table exists
            result = db.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                )
            """))
            
            users_exists = result.scalar()
            
            if users_exists:
                print("✅ Authentication tables already exist")
                return True
            else:
                print("❌ Authentication tables not found - migration needed")
                return False
                
        except Exception as e:
            print(f"❌ Error checking migration status: {e}")
            return False
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run authentication tables migration")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running the migration"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if migration has already been applied"
    )
    
    args = parser.parse_args()
    
    print("DocTranslator Database Migration")
    print("=" * 40)
    print()
    
    if args.check:
        success = check_migration_status()
        sys.exit(0 if success else 1)
    
    if args.dry_run:
        print("Running in dry-run mode...")
        success = run_migration(dry_run=True)
    else:
        print("Running migration...")
        success = run_migration(dry_run=False)
    
    if success:
        print()
        print("Next steps:")
        print("1. Create initial admin user: python scripts/create_admin_user.py")
        print("2. Test authentication: curl -X POST /api/auth/login")
        print("3. Verify public upload still works")
        sys.exit(0)
    else:
        print()
        print("Migration failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
