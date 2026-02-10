#!/usr/bin/env python3
"""
Data Migration: Upgrade Encryption from Fernet (AES-128-CBC) to AES-256-GCM

Migrates existing encrypted data from legacy Fernet (AES-128-CBC + HMAC-SHA256)
to AES-256-GCM for GDPR "Stand der Technik" (state of the art) compliance.

Safety Features:
- Idempotent: Can run multiple times safely (skips already-migrated data)
- Batched: Processes records in batches to avoid memory issues
- Progress tracking: Shows progress for large datasets
- Dry run mode: Test without making changes
- Rollback on error: Uses transactions for safety

Prerequisites:
- ENCRYPTION_KEY must be set with a new 256-bit key for AES-256-GCM
- ENCRYPTION_KEY_FERNET_LEGACY must be set with the old Fernet key
- Database must be accessible

Tables/Fields migrated:
- users: email, full_name
- pipeline_jobs: file_content (binary), original_text, translated_text,
                 language_translated_text, ocr_markdown, guidelines_text
- pipeline_step_executions: input_text, output_text
- user_feedback: ai_analysis_text

Usage:
    # Dry run (no changes)
    python upgrade_encryption_to_aes256gcm.py --dry-run

    # Real migration
    python upgrade_encryption_to_aes256gcm.py

    # Custom batch size
    python upgrade_encryption_to_aes256gcm.py --batch-size 50

    # Migrate specific table only
    python upgrade_encryption_to_aes256gcm.py --table users
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text, bindparam
from sqlalchemy.types import LargeBinary

from app.core.encryption import encryptor, FieldEncryptor

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/doctranslator",
)


def is_fernet_encrypted(value: str | bytes | memoryview | None) -> bool:
    """Check if a value is encrypted with legacy Fernet."""
    if value is None:
        return False
    # Handle memoryview from SQLAlchemy bytea columns
    if isinstance(value, memoryview):
        value = bytes(value)
    # Handle bytes from bytea columns - convert to string first
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return False
    # Debug: check what the encryptor sees
    try:
        import base64
        decoded = base64.urlsafe_b64decode(value)
        first_byte = decoded[0] if decoded else None
        fb_hex = f"0x{first_byte:02X}" if first_byte is not None else "None"
        print(f"    [DEBUG] is_fernet check: first_byte={fb_hex}, expected=0x80")
    except Exception as e:
        print(f"    [DEBUG] is_fernet check: base64 decode failed: {e}")
    return encryptor.is_legacy_fernet(value)


def is_aes256gcm_encrypted(value: str | bytes | memoryview | None) -> bool:
    """Check if a value is already encrypted with AES-256-GCM."""
    if value is None:
        return False
    # Handle memoryview from SQLAlchemy bytea columns
    if isinstance(value, memoryview):
        value = bytes(value)
    # Handle bytes from bytea columns - convert to string first
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return False
    return encryptor.is_aes256gcm(value)


def migrate_text_field(value: str | None, dry_run: bool = False) -> tuple[str | None, str]:
    """
    Migrate a text field from Fernet to AES-256-GCM.

    Args:
        value: Encrypted field value
        dry_run: If True, don't actually encrypt

    Returns:
        Tuple of (new_value, status) where status is one of:
        - "migrated": Successfully migrated
        - "skipped_already_migrated": Already AES-256-GCM
        - "skipped_null": Null value
        - "skipped_plaintext": Appears to be plaintext (not encrypted)
        - "error": Migration failed
    """
    if value is None:
        return None, "skipped_null"

    if is_aes256gcm_encrypted(value):
        return value, "skipped_already_migrated"

    if not is_fernet_encrypted(value):
        return value, "skipped_plaintext"

    if dry_run:
        return value, "migrated"

    try:
        # Decrypt with Fernet, re-encrypt with AES-256-GCM
        decrypted = encryptor.decrypt_field(value)
        encrypted = encryptor.encrypt_field(decrypted)
        return encrypted, "migrated"
    except Exception as e:
        print(f"    Error migrating field: {e}")
        return value, "error"


def migrate_binary_field(value: str | bytes | None, dry_run: bool = False) -> tuple[str | bytes | None, str]:
    """
    Migrate a binary field from Fernet to AES-256-GCM.

    Binary fields are stored as base64-encoded encrypted strings in bytea columns.
    SQLAlchemy returns bytea columns as bytes, so we need to handle both.

    Args:
        value: Encrypted binary field value (str or bytes from bytea column)
        dry_run: If True, don't actually encrypt

    Returns:
        Tuple of (new_value, status)
    """
    if value is None:
        print("    [DEBUG] Binary field is None")
        return None, "skipped_null"

    # Convert bytes/memoryview to string for processing (bytea columns return memoryview in SQLAlchemy)
    original_value = value
    print(f"    [DEBUG] Binary field type: {type(value).__name__}, length: {len(value)}")

    # Handle memoryview (SQLAlchemy returns bytea as memoryview)
    if isinstance(value, memoryview):
        value = bytes(value)
        print(f"    [DEBUG] Converted memoryview to bytes")

    if isinstance(value, bytes):
        print(f"    [DEBUG] First 20 bytes hex: {value[:20].hex()}")
        print(f"    [DEBUG] First 20 bytes repr: {value[:20]!r}")
        try:
            value = value.decode("utf-8")
            print(f"    [DEBUG] Decoded to string, first 30 chars: {value[:30]}")
        except UnicodeDecodeError as e:
            print(f"    Warning: Could not decode bytea field as UTF-8: {e}")
            return original_value, "skipped_plaintext"

    is_aes = is_aes256gcm_encrypted(value)
    is_fernet = is_fernet_encrypted(value)
    print(f"    [DEBUG] is_aes256gcm: {is_aes}, is_fernet: {is_fernet}")

    if is_aes:
        print("    [DEBUG] Skipping - already AES-256-GCM")
        return original_value, "skipped_already_migrated"

    if not is_fernet:
        print(f"    [DEBUG] Skipping - not detected as Fernet. Value starts with: {value[:30]}")
        return original_value, "skipped_plaintext"

    if dry_run:
        return original_value, "migrated"

    try:
        # Decrypt binary with Fernet, re-encrypt with AES-256-GCM
        decrypted_bytes = encryptor.decrypt_binary_field(value)
        encrypted = encryptor.encrypt_binary_field(decrypted_bytes)
        # Return as bytes for bytea column if original was bytes
        if isinstance(original_value, bytes) and encrypted:
            return encrypted.encode("utf-8"), "migrated"
        return encrypted, "migrated"
    except Exception as e:
        print(f"    Error migrating binary field: {e}")
        import traceback
        traceback.print_exc()
        return original_value, "error"


def migrate_users_table(conn, batch_size: int, dry_run: bool) -> dict:
    """Migrate users table (email, full_name)."""
    stats = {"migrated": 0, "skipped": 0, "errors": 0}

    print("\n📋 Migrating users table...")

    # Get total count
    result = conn.execute(text("SELECT COUNT(*) FROM users"))
    total = result.scalar() or 0
    print(f"   Found {total} users")

    if total == 0:
        return stats

    # Fetch all users
    result = conn.execute(text("SELECT id, email, full_name FROM users ORDER BY id"))
    users = result.fetchall()

    for i in range(0, len(users), batch_size):
        batch = users[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(users) + batch_size - 1) // batch_size
        print(f"   Batch {batch_num}/{total_batches}...", end=" ")

        batch_migrated = 0
        batch_skipped = 0
        batch_errors = 0

        for user_id, email, full_name in batch:
            new_email, email_status = migrate_text_field(email, dry_run)
            new_full_name, name_status = migrate_text_field(full_name, dry_run)

            # Track stats for email
            if email_status == "migrated":
                batch_migrated += 1
            elif email_status == "error":
                batch_errors += 1
            else:
                batch_skipped += 1

            # Update if anything was migrated
            if not dry_run and (email_status == "migrated" or name_status == "migrated"):
                conn.execute(
                    text(
                        """
                        UPDATE users
                        SET email = :email, full_name = :full_name
                        WHERE id = :id
                    """
                    ),
                    {"email": new_email, "full_name": new_full_name, "id": user_id},
                )

        stats["migrated"] += batch_migrated
        stats["skipped"] += batch_skipped
        stats["errors"] += batch_errors
        print(f"Migrated: {batch_migrated}, Skipped: {batch_skipped}, Errors: {batch_errors}")

    return stats


def migrate_pipeline_jobs_table(conn, batch_size: int, dry_run: bool) -> dict:
    """Migrate pipeline_jobs table (file_content, various text fields)."""
    stats = {"migrated": 0, "skipped": 0, "errors": 0}

    print("\n📋 Migrating pipeline_jobs table...")

    text_fields = [
        "original_text",
        "translated_text",
        "language_translated_text",
        "ocr_markdown",
        "guidelines_text",
    ]

    # Get total count
    result = conn.execute(text("SELECT COUNT(*) FROM pipeline_jobs"))
    total = result.scalar() or 0
    print(f"   Found {total} pipeline jobs")

    if total == 0:
        return stats

    # Fetch all jobs
    fields_select = ", ".join(["id", "file_content"] + text_fields)
    result = conn.execute(text(f"SELECT {fields_select} FROM pipeline_jobs ORDER BY id"))
    jobs = result.fetchall()

    for i in range(0, len(jobs), batch_size):
        batch = jobs[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(jobs) + batch_size - 1) // batch_size
        print(f"   Batch {batch_num}/{total_batches}...", end=" ")

        batch_migrated = 0
        batch_skipped = 0
        batch_errors = 0

        for row in batch:
            job_id = row[0]
            file_content = row[1]
            other_fields = {name: row[idx + 2] for idx, name in enumerate(text_fields)}

            # Migrate file_content (binary field)
            new_file_content, fc_status = migrate_binary_field(file_content, dry_run)
            if fc_status == "migrated":
                batch_migrated += 1
            elif fc_status == "error":
                batch_errors += 1

            # Migrate text fields
            new_values = {"file_content": new_file_content}
            any_migrated = fc_status == "migrated"

            for field_name, field_value in other_fields.items():
                new_value, status = migrate_text_field(field_value, dry_run)
                new_values[field_name] = new_value
                if status == "migrated":
                    any_migrated = True

            # Update if anything was migrated
            if not dry_run and any_migrated:
                # Build SET clause with proper type binding for bytea column
                set_parts = []
                for k in new_values.keys():
                    if k == "file_content":
                        set_parts.append(f"{k} = :file_content")
                    else:
                        set_parts.append(f"{k} = :{k}")
                set_clause = ", ".join(set_parts)

                # Use bindparam with LargeBinary type for bytea column
                stmt = text(f"UPDATE pipeline_jobs SET {set_clause} WHERE id = :id")
                if "file_content" in new_values and new_values["file_content"] is not None:
                    # Ensure file_content is bytes for bytea column
                    fc_value = new_values["file_content"]
                    if isinstance(fc_value, str):
                        fc_value = fc_value.encode("utf-8")
                    stmt = stmt.bindparams(bindparam("file_content", value=fc_value, type_=LargeBinary))
                    new_values_copy = {k: v for k, v in new_values.items() if k != "file_content"}
                    conn.execute(stmt, {**new_values_copy, "id": job_id})
                else:
                    conn.execute(stmt, {**new_values, "id": job_id})

        stats["migrated"] += batch_migrated
        stats["skipped"] += batch_skipped
        stats["errors"] += batch_errors
        print(f"Migrated: {batch_migrated}, Skipped: {batch_skipped}, Errors: {batch_errors}")

    return stats


def migrate_pipeline_step_executions_table(conn, batch_size: int, dry_run: bool) -> dict:
    """Migrate pipeline_step_executions table (input_text, output_text)."""
    stats = {"migrated": 0, "skipped": 0, "errors": 0}

    print("\n📋 Migrating pipeline_step_executions table...")

    # Get total count
    result = conn.execute(text("SELECT COUNT(*) FROM pipeline_step_executions"))
    total = result.scalar() or 0
    print(f"   Found {total} step executions")

    if total == 0:
        return stats

    # Fetch all executions
    result = conn.execute(
        text("SELECT id, input_text, output_text FROM pipeline_step_executions ORDER BY id")
    )
    executions = result.fetchall()

    for i in range(0, len(executions), batch_size):
        batch = executions[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(executions) + batch_size - 1) // batch_size
        print(f"   Batch {batch_num}/{total_batches}...", end=" ")

        batch_migrated = 0
        batch_skipped = 0
        batch_errors = 0

        for exec_id, input_text, output_text in batch:
            new_input, input_status = migrate_text_field(input_text, dry_run)
            new_output, output_status = migrate_text_field(output_text, dry_run)

            if input_status == "migrated" or output_status == "migrated":
                batch_migrated += 1
            elif input_status == "error" or output_status == "error":
                batch_errors += 1
            else:
                batch_skipped += 1

            if not dry_run and (input_status == "migrated" or output_status == "migrated"):
                conn.execute(
                    text(
                        """
                        UPDATE pipeline_step_executions
                        SET input_text = :input_text, output_text = :output_text
                        WHERE id = :id
                    """
                    ),
                    {"input_text": new_input, "output_text": new_output, "id": exec_id},
                )

        stats["migrated"] += batch_migrated
        stats["skipped"] += batch_skipped
        stats["errors"] += batch_errors
        print(f"Migrated: {batch_migrated}, Skipped: {batch_skipped}, Errors: {batch_errors}")

    return stats


def migrate_user_feedback_table(conn, batch_size: int, dry_run: bool) -> dict:
    """Migrate user_feedback table (ai_analysis_text)."""
    stats = {"migrated": 0, "skipped": 0, "errors": 0}

    print("\n📋 Migrating user_feedback table...")

    # Get total count
    result = conn.execute(text("SELECT COUNT(*) FROM user_feedback"))
    total = result.scalar() or 0
    print(f"   Found {total} feedback entries")

    if total == 0:
        return stats

    # Fetch all feedback
    result = conn.execute(text("SELECT id, ai_analysis_text FROM user_feedback ORDER BY id"))
    feedbacks = result.fetchall()

    for i in range(0, len(feedbacks), batch_size):
        batch = feedbacks[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(feedbacks) + batch_size - 1) // batch_size
        print(f"   Batch {batch_num}/{total_batches}...", end=" ")

        batch_migrated = 0
        batch_skipped = 0
        batch_errors = 0

        for feedback_id, ai_analysis_text in batch:
            new_value, status = migrate_text_field(ai_analysis_text, dry_run)

            if status == "migrated":
                batch_migrated += 1
            elif status == "error":
                batch_errors += 1
            else:
                batch_skipped += 1

            if not dry_run and status == "migrated":
                conn.execute(
                    text(
                        """
                        UPDATE user_feedback
                        SET ai_analysis_text = :ai_analysis_text
                        WHERE id = :id
                    """
                    ),
                    {"ai_analysis_text": new_value, "id": feedback_id},
                )

        stats["migrated"] += batch_migrated
        stats["skipped"] += batch_skipped
        stats["errors"] += batch_errors
        print(f"Migrated: {batch_migrated}, Skipped: {batch_skipped}, Errors: {batch_errors}")

    return stats


def run_migration(dry_run: bool = False, batch_size: int = 100, table: str | None = None) -> bool:
    """
    Run the encryption upgrade migration.

    Args:
        dry_run: If True, show what would be done without making changes
        batch_size: Number of records to process per batch
        table: If specified, only migrate this table

    Returns:
        True if successful, False otherwise
    """
    print("\n" + "=" * 80)
    print("ENCRYPTION UPGRADE: Fernet (AES-128-CBC) → AES-256-GCM")
    print("=" * 80)
    print(f"\nTimestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'local'}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE MIGRATION'}")
    print(f"Batch Size: {batch_size}")
    if table:
        print(f"Table: {table}")

    # Check encryption is enabled
    if not encryptor.is_enabled():
        print("\n❌ ERROR: Encryption is disabled (ENCRYPTION_ENABLED=false)")
        print("   Enable encryption before running this migration")
        return False

    # Check new AES-256-GCM key is set
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        print("\n❌ ERROR: ENCRYPTION_KEY environment variable not set")
        print("   Generate a new key with: python -c 'from app.core.encryption import FieldEncryptor; print(FieldEncryptor.generate_key())'")
        return False

    # Check legacy Fernet key is set (needed for decryption)
    fernet_legacy_key = os.getenv("ENCRYPTION_KEY_FERNET_LEGACY")
    if not fernet_legacy_key:
        print("\n⚠️  WARNING: ENCRYPTION_KEY_FERNET_LEGACY not set")
        print("   Set this to your old Fernet key to decrypt legacy data")
        print("   Migration will attempt to use ENCRYPTION_KEY as Fernet key (fallback)")

    print(f"\n✅ Encryption enabled: {encryptor.is_enabled()}")
    print(f"✅ AES-256-GCM key set: {'*' * 20}...")
    if fernet_legacy_key:
        print(f"✅ Legacy Fernet key set: {'*' * 20}...")

    engine = create_engine(DATABASE_URL)

    try:
        with engine.begin() as conn:
            total_stats = {"migrated": 0, "skipped": 0, "errors": 0}

            # Migrate tables
            tables_to_migrate = {
                "users": migrate_users_table,
                "pipeline_jobs": migrate_pipeline_jobs_table,
                "pipeline_step_executions": migrate_pipeline_step_executions_table,
                "user_feedback": migrate_user_feedback_table,
            }

            if table:
                if table not in tables_to_migrate:
                    print(f"\n❌ ERROR: Unknown table '{table}'")
                    print(f"   Available tables: {', '.join(tables_to_migrate.keys())}")
                    return False
                tables_to_migrate = {table: tables_to_migrate[table]}

            for table_name, migrate_func in tables_to_migrate.items():
                try:
                    stats = migrate_func(conn, batch_size, dry_run)
                    total_stats["migrated"] += stats["migrated"]
                    total_stats["skipped"] += stats["skipped"]
                    total_stats["errors"] += stats["errors"]
                except Exception as e:
                    print(f"\n❌ ERROR migrating {table_name}: {e}")
                    total_stats["errors"] += 1

            # Summary
            print("\n" + "=" * 80)
            if dry_run:
                print("DRY RUN COMPLETED")
            else:
                print("MIGRATION COMPLETED")
            print("=" * 80)

            print(f"\n📊 Summary:")
            print(f"   Migrated: {total_stats['migrated']}")
            print(f"   Skipped: {total_stats['skipped']}")
            print(f"   Errors: {total_stats['errors']}")

            if total_stats["errors"] > 0:
                print(f"\n⚠️  WARNING: {total_stats['errors']} errors occurred")
                return False

            if dry_run:
                print("\n💡 Run without --dry-run to apply changes")

            return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Parse arguments and run migration."""
    parser = argparse.ArgumentParser(
        description="Upgrade encryption from Fernet (AES-128-CBC) to AES-256-GCM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of records to process per batch (default: 100)",
    )
    parser.add_argument(
        "--table",
        type=str,
        choices=["users", "pipeline_jobs", "pipeline_step_executions", "user_feedback"],
        help="Only migrate a specific table",
    )

    args = parser.parse_args()

    success = run_migration(
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        table=args.table,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
