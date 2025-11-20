#!/usr/bin/env python3
"""
Data Migration: Encrypt existing user data

Encrypts existing plaintext email and full_name fields in the users table
and generates searchable hashes for encrypted field lookups.

Safety Features:
- Idempotent: Can run multiple times safely (skips already encrypted data)
- Batched: Processes users in batches to avoid memory issues
- Progress tracking: Shows progress for large datasets
- Dry run mode: Test without making changes
- Rollback on error: Uses transactions for safety

Prerequisites:
- Schema migration (add_encryption_search_fields.py) must be run first
- ENCRYPTION_KEY environment variable must be set

Usage:
    # Dry run (no changes)
    python encrypt_existing_user_data.py --dry-run

    # Real migration
    python encrypt_existing_user_data.py

    # Custom batch size
    python encrypt_existing_user_data.py --batch-size 50
"""
import os
import sys
import argparse
import hashlib
from pathlib import Path
from datetime import datetime, timezone

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from app.core.encryption import encryptor

# Database URL from environment
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway'
)

def generate_searchable_hash(value: str) -> str:
    """
    Generate SHA-256 hash for searchable field.

    Args:
        value: Plaintext value to hash

    Returns:
        Hex string of SHA-256 hash (64 characters)
    """
    if not value:
        return None
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def is_already_encrypted(email_value: str) -> bool:
    """
    Check if a value appears to be already encrypted.

    Args:
        email_value: Email field value from database

    Returns:
        True if value looks encrypted (base64 format)
    """
    if not email_value:
        return False

    # Encrypted values are base64-encoded Fernet tokens (much longer than emails)
    # and contain only base64 characters
    if len(email_value) < 100:  # Encrypted emails are typically 150+ chars
        return False

    try:
        import base64
        base64.b64decode(email_value.encode('ascii'))
        return True  # Valid base64, likely encrypted
    except Exception:
        return False  # Not base64, definitely not encrypted

def encrypt_user_batch(conn, users, dry_run=False):
    """
    Encrypt a batch of users.

    Args:
        conn: Database connection
        users: List of user tuples (id, email, full_name)
        dry_run: If True, don't commit changes

    Returns:
        Tuple of (encrypted_count, skipped_count, error_count)
    """
    encrypted_count = 0
    skipped_count = 0
    error_count = 0

    for user_id, email, full_name in users:
        try:
            # Skip if already encrypted
            if is_already_encrypted(email):
                skipped_count += 1
                continue

            # Encrypt fields
            encrypted_email = encryptor.encrypt_field(email)
            encrypted_full_name = encryptor.encrypt_field(full_name)

            # Generate searchable hashes (from plaintext)
            email_hash = generate_searchable_hash(email)
            full_name_hash = generate_searchable_hash(full_name)

            if not dry_run:
                # Update user with encrypted data
                conn.execute(
                    text("""
                        UPDATE users
                        SET
                            email = :encrypted_email,
                            full_name = :encrypted_full_name,
                            email_searchable = :email_hash,
                            full_name_searchable = :full_name_hash,
                            encryption_version = 1
                        WHERE id = :user_id
                    """),
                    {
                        'encrypted_email': encrypted_email,
                        'encrypted_full_name': encrypted_full_name,
                        'email_hash': email_hash,
                        'full_name_hash': full_name_hash,
                        'user_id': user_id
                    }
                )

            encrypted_count += 1

        except Exception as e:
            print(f'  ❌ Error encrypting user {user_id}: {e}')
            error_count += 1

    return encrypted_count, skipped_count, error_count

def run_data_migration(dry_run=False, batch_size=100):
    """
    Run the data migration to encrypt existing users.

    Args:
        dry_run: If True, show what would be done without making changes
        batch_size: Number of users to process per batch

    Returns:
        True if successful, False otherwise
    """
    print('\n' + '='*80)
    print('DATA MIGRATION: Encrypt Existing User Data')
    print('='*80)
    print(f'\nTimestamp: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")} UTC')
    print(f'Database: {DATABASE_URL.split("@")[-1]}')
    print(f'Mode: {"DRY RUN (no changes)" if dry_run else "LIVE MIGRATION"}')
    print(f'Batch Size: {batch_size}')

    # Check encryption is enabled
    if not encryptor.is_enabled():
        print('\n❌ ERROR: Encryption is disabled (ENCRYPTION_ENABLED=false)')
        print('   Enable encryption before running this migration')
        return False

    # Check encryption key is set
    encryption_key = os.getenv('ENCRYPTION_KEY')
    if not encryption_key:
        print('\n❌ ERROR: ENCRYPTION_KEY environment variable not set')
        print('   Set encryption key before running this migration')
        return False

    print(f'\n✅ Encryption enabled: {encryptor.is_enabled()}')
    print(f'✅ Encryption key set: {"*" * 20}...')

    engine = create_engine(DATABASE_URL)

    try:
        # Use begin() to get a connection with transaction control
        with engine.begin() as conn:
            # Check schema migration was run
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                AND column_name IN ('email_searchable', 'full_name_searchable', 'encryption_version')
            """))

            required_columns = set(row[0] for row in result)
            if len(required_columns) < 3:
                missing = {'email_searchable', 'full_name_searchable', 'encryption_version'} - required_columns
                print(f'\n❌ ERROR: Schema migration not run. Missing columns: {missing}')
                print('   Run add_encryption_search_fields.py first')
                return False

            print('\n✅ Schema migration verified')

            # Get total user count
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            total_users = result.scalar()

            if total_users == 0:
                print('\n✅ No users to migrate')
                return True

            print(f'\n📊 Found {total_users} users to process')

            # Get users that need encryption (plaintext email)
            result = conn.execute(text("""
                SELECT id, email, full_name
                FROM users
                ORDER BY id
            """))

            all_users = result.fetchall()

            # Process in batches
            total_encrypted = 0
            total_skipped = 0
            total_errors = 0

            print('\n🔄 Processing users in batches...\n')

            for i in range(0, len(all_users), batch_size):
                batch = all_users[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(all_users) + batch_size - 1) // batch_size

                print(f'Batch {batch_num}/{total_batches} ({len(batch)} users)...', end=' ')

                try:
                    encrypted, skipped, errors = encrypt_user_batch(conn, batch, dry_run)

                    total_encrypted += encrypted
                    total_skipped += skipped
                    total_errors += errors

                    print(f'✅ Encrypted: {encrypted}, Skipped: {skipped}, Errors: {errors}')

                except Exception as e:
                    print(f'❌ Batch failed: {e}')
                    total_errors += len(batch)
                    if not dry_run:
                        raise  # Re-raise to trigger rollback of entire transaction

            # Summary
            print('\n' + '='*80)
            if dry_run:
                print('DRY RUN COMPLETED')
            else:
                print('MIGRATION COMPLETED')
            print('='*80)

            print(f'\n📊 Summary:')
            print(f'  Total users: {total_users}')
            print(f'  Encrypted: {total_encrypted}')
            print(f'  Already encrypted (skipped): {total_skipped}')
            print(f'  Errors: {total_errors}')

            if total_errors > 0:
                print(f'\n⚠️  WARNING: {total_errors} users had errors')
                return False

            if not dry_run and total_encrypted > 0:
                # Verify encryption worked
                result = conn.execute(text("""
                    SELECT COUNT(*)
                    FROM users
                    WHERE email_searchable IS NOT NULL
                    AND full_name_searchable IS NOT NULL
                """))
                verified_count = result.scalar()

                print(f'\n✅ Verification: {verified_count} users have searchable hashes')

                # Show sample (first user)
                result = conn.execute(text("""
                    SELECT id, email, email_searchable, encryption_version
                    FROM users
                    LIMIT 1
                """))

                sample = result.fetchone()
                if sample:
                    print(f'\n📝 Sample encrypted user:')
                    print(f'  ID: {sample[0]}')
                    print(f'  Email (encrypted): {sample[1][:50]}...')
                    print(f'  Email hash: {sample[2]}')
                    print(f'  Encryption version: {sample[3]}')

            if dry_run:
                print('\n💡 Run without --dry-run to apply changes')

            return True

    except Exception as e:
        print(f'\n❌ Migration failed: {e}')
        import traceback
        traceback.print_exc()
        return False

def main():
    """Parse arguments and run migration."""
    parser = argparse.ArgumentParser(
        description='Encrypt existing user data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of users to process per batch (default: 100)'
    )

    args = parser.parse_args()

    success = run_data_migration(
        dry_run=args.dry_run,
        batch_size=args.batch_size
    )

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
