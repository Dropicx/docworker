#!/usr/bin/env python3
"""
Migration: Add account lockout fields to users table

Adds failed_login_attempts and locked_until columns for brute force protection.
"""
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text, inspect
from datetime import datetime, timezone

# Database URL
DATABASE_URL = 'postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway'

def check_column_exists(engine, table_name, column_name):
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def run_migration():
    """Run the migration to add account lockout fields."""
    print('\n' + '='*80)
    print('MIGRATION: Add Account Lockout Fields to Users Table')
    print('='*80)
    print(f'\nTimestamp: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")} UTC')
    print(f'Database: {DATABASE_URL.split("@")[-1]}')

    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            # Check if columns already exist
            failed_attempts_exists = check_column_exists(engine, 'users', 'failed_login_attempts')
            locked_until_exists = check_column_exists(engine, 'users', 'locked_until')

            if failed_attempts_exists and locked_until_exists:
                print('\n✅ Migration already applied - columns exist')
                return True

            print('\n📋 Migration Steps:')
            print('  1. Add failed_login_attempts column (INTEGER, DEFAULT 0)')
            print('  2. Add locked_until column (TIMESTAMP, NULLABLE)')
            print('  3. Create index on locked_until')

            # Begin transaction
            trans = conn.begin()

            try:
                # Add failed_login_attempts column if it doesn't exist
                if not failed_attempts_exists:
                    print('\n➡️  Adding failed_login_attempts column...')
                    conn.execute(text("""
                        ALTER TABLE users
                        ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0
                    """))
                    print('✅ Added failed_login_attempts column')
                else:
                    print('\n✅ failed_login_attempts column already exists')

                # Add locked_until column if it doesn't exist
                if not locked_until_exists:
                    print('\n➡️  Adding locked_until column...')
                    conn.execute(text("""
                        ALTER TABLE users
                        ADD COLUMN locked_until TIMESTAMP
                    """))
                    print('✅ Added locked_until column')
                else:
                    print('\n✅ locked_until column already exists')

                # Create index on locked_until
                print('\n➡️  Creating index on locked_until...')
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_users_locked_until
                        ON users(locked_until)
                    """))
                    print('✅ Created index idx_users_locked_until')
                except Exception as e:
                    if 'already exists' in str(e):
                        print('✅ Index idx_users_locked_until already exists')
                    else:
                        raise

                # Commit transaction
                trans.commit()

                print('\n' + '='*80)
                print('✅ MIGRATION COMPLETED SUCCESSFULLY')
                print('='*80)

                # Verify columns
                print('\n📊 Verification:')
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = 'users'
                    AND column_name IN ('failed_login_attempts', 'locked_until')
                    ORDER BY column_name
                """))

                print(f'\n{"Column":<25} {"Type":<15} {"Nullable":<10} {"Default":<20}')
                print('-' * 80)
                for row in result:
                    print(f'{row[0]:<25} {row[1]:<15} {row[2]:<10} {str(row[3]):<20}')

                # Check index
                result = conn.execute(text("""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = 'users'
                    AND indexname = 'idx_users_locked_until'
                """))

                if result.fetchone():
                    print('\n✅ Index idx_users_locked_until verified')

                return True

            except Exception as e:
                trans.rollback()
                print(f'\n❌ Migration failed: {e}')
                raise

    except Exception as e:
        print(f'\n❌ Error: {e}')
        return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
