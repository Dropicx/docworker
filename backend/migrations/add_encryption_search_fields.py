#!/usr/bin/env python3
"""
Migration: Add encryption search fields to users table

Adds searchable hash columns for encrypted fields to enable searching
while maintaining encryption. Also adds encryption_version for key rotation.

Schema Changes:
- email_searchable (VARCHAR 64): SHA-256 hash of email for search
- full_name_searchable (VARCHAR 64): SHA-256 hash of full_name for search
- encryption_version (INTEGER): Track encryption key version (default 1)

Indexes:
- idx_users_email_searchable: For email lookups
- idx_users_full_name_searchable: For name searches
"""
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text, inspect
from datetime import datetime, timezone

# Database URL from environment (fallback for development)
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway'
)

def check_column_exists(engine, table_name, column_name):
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def check_index_exists(engine, index_name):
    """Check if an index exists."""
    inspector = inspect(engine)
    indexes = inspector.get_indexes('users')
    return any(idx['name'] == index_name for idx in indexes)

def run_migration():
    """Run the migration to add encryption search fields."""
    print('\n' + '='*80)
    print('MIGRATION: Add Encryption Search Fields to Users Table')
    print('='*80)
    print(f'\nTimestamp: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")} UTC')
    print(f'Database: {DATABASE_URL.split("@")[-1]}')

    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            # Check if columns already exist
            email_searchable_exists = check_column_exists(engine, 'users', 'email_searchable')
            full_name_searchable_exists = check_column_exists(engine, 'users', 'full_name_searchable')
            encryption_version_exists = check_column_exists(engine, 'users', 'encryption_version')

            if email_searchable_exists and full_name_searchable_exists and encryption_version_exists:
                print('\n✅ Migration already applied - all columns exist')
                return True

            print('\n📋 Migration Steps:')
            print('  1. Add email_searchable column (VARCHAR 64, NULLABLE)')
            print('  2. Add full_name_searchable column (VARCHAR 64, NULLABLE)')
            print('  3. Add encryption_version column (INTEGER, DEFAULT 1)')
            print('  4. Create index on email_searchable')
            print('  5. Create index on full_name_searchable')

            # Begin transaction
            trans = conn.begin()

            try:
                # Add email_searchable column if it doesn't exist
                if not email_searchable_exists:
                    print('\n➡️  Adding email_searchable column...')
                    conn.execute(text("""
                        ALTER TABLE users
                        ADD COLUMN email_searchable VARCHAR(64)
                    """))
                    print('✅ Added email_searchable column')
                else:
                    print('\n✅ email_searchable column already exists')

                # Add full_name_searchable column if it doesn't exist
                if not full_name_searchable_exists:
                    print('\n➡️  Adding full_name_searchable column...')
                    conn.execute(text("""
                        ALTER TABLE users
                        ADD COLUMN full_name_searchable VARCHAR(64)
                    """))
                    print('✅ Added full_name_searchable column')
                else:
                    print('\n✅ full_name_searchable column already exists')

                # Add encryption_version column if it doesn't exist
                if not encryption_version_exists:
                    print('\n➡️  Adding encryption_version column...')
                    conn.execute(text("""
                        ALTER TABLE users
                        ADD COLUMN encryption_version INTEGER NOT NULL DEFAULT 1
                    """))
                    print('✅ Added encryption_version column')
                else:
                    print('\n✅ encryption_version column already exists')

                # Create index on email_searchable
                print('\n➡️  Creating index on email_searchable...')
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_users_email_searchable
                        ON users(email_searchable)
                    """))
                    print('✅ Created index idx_users_email_searchable')
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        print('✅ Index idx_users_email_searchable already exists')
                    else:
                        raise

                # Create index on full_name_searchable
                print('\n➡️  Creating index on full_name_searchable...')
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_users_full_name_searchable
                        ON users(full_name_searchable)
                    """))
                    print('✅ Created index idx_users_full_name_searchable')
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        print('✅ Index idx_users_full_name_searchable already exists')
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
                    AND column_name IN ('email_searchable', 'full_name_searchable', 'encryption_version')
                    ORDER BY column_name
                """))

                print(f'\n{"Column":<30} {"Type":<20} {"Nullable":<10} {"Default":<20}')
                print('-' * 80)
                for row in result:
                    print(f'{row[0]:<30} {row[1]:<20} {row[2]:<10} {str(row[3]):<20}')

                # Check indexes
                result = conn.execute(text("""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = 'users'
                    AND indexname IN ('idx_users_email_searchable', 'idx_users_full_name_searchable')
                    ORDER BY indexname
                """))

                print('\n📑 Indexes:')
                for row in result:
                    print(f'  ✅ {row[0]}')

                print('\n💡 Next Steps:')
                print('  1. Run data migration to encrypt existing data')
                print('  2. Update get_by_email() to use email_searchable')
                print('  3. Deploy with ENCRYPTION_KEY set')

                return True

            except Exception as e:
                trans.rollback()
                print(f'\n❌ Migration failed: {e}')
                raise

    except Exception as e:
        print(f'\n❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
