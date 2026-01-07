#!/usr/bin/env python3
"""
Decrypt Dev Database Migration

This script decrypts all encrypted fields in the database so that
ENCRYPTION_ENABLED can be set to false for development.

IMPORTANT: Run this with ENCRYPTION_ENABLED=true and ENCRYPTION_KEY set!
After running, you can set ENCRYPTION_ENABLED=false.

Usage:
    cd backend
    python migrations/decrypt_dev_database.py
"""

import base64
import json
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import encryption BEFORE disabling it
os.environ.setdefault("ENCRYPTION_ENABLED", "true")
from app.core.encryption import encryptor


def get_database_url():
    """Get database URL from environment or use default."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"
    )


def decrypt_users(session):
    """Decrypt email and full_name in users table."""
    print("\n📧 Decrypting users table...")

    result = session.execute(text("SELECT id, email, full_name FROM users"))
    rows = result.fetchall()

    decrypted_count = 0
    for row in rows:
        user_id, email, full_name = row

        try:
            # Check if encrypted (starts with gAAAAA or looks like Fernet token)
            new_email = email
            new_full_name = full_name
            needs_update = False

            if email and (email.startswith('gAAAAA') or email.startswith('Z0FBQUFB')):
                new_email = encryptor.decrypt_field(email)
                needs_update = True

            if full_name and (full_name.startswith('gAAAAA') or full_name.startswith('Z0FBQUFB')):
                new_full_name = encryptor.decrypt_field(full_name)
                needs_update = True

            if needs_update:
                session.execute(
                    text("UPDATE users SET email = :email, full_name = :full_name WHERE id = :id"),
                    {"email": new_email, "full_name": new_full_name, "id": user_id}
                )
                decrypted_count += 1
                print(f"   ✓ Decrypted user {user_id}")

        except Exception as e:
            print(f"   ⚠ Failed to decrypt user {user_id}: {e}")

    print(f"   Decrypted {decrypted_count} users")
    return decrypted_count


def decrypt_pipeline_jobs(session):
    """Decrypt file_content and result_data in pipeline_jobs table."""
    print("\n📄 Decrypting pipeline_jobs table...")

    result = session.execute(text("SELECT id, file_content, result_data FROM pipeline_jobs"))
    rows = result.fetchall()

    decrypted_count = 0
    for row in rows:
        job_id, file_content, result_data = row

        try:
            needs_update = False
            new_file_content = file_content
            new_result_data = result_data

            # Decrypt file_content (binary field stored as encrypted string)
            if file_content:
                # file_content in DB is bytes, but if encrypted it's stored differently
                if isinstance(file_content, memoryview):
                    file_content = bytes(file_content)
                if isinstance(file_content, bytes):
                    try:
                        # Try to decode as string to check if it's encrypted
                        content_str = file_content.decode('utf-8', errors='ignore')
                        if content_str.startswith('gAAAAA') or content_str.startswith('Z0FBQUFB'):
                            # It's encrypted - decrypt it
                            decrypted_bytes = encryptor.decrypt_binary_field(content_str)
                            new_file_content = decrypted_bytes
                            needs_update = True
                    except:
                        pass  # Not encrypted or not decryptable

            # Decrypt result_data (JSON field stored as encrypted string)
            if result_data:
                result_str = result_data if isinstance(result_data, str) else str(result_data)
                if result_str.startswith('gAAAAA') or result_str.startswith('Z0FBQUFB'):
                    decrypted_dict = encryptor.decrypt_json_field(result_str)
                    new_result_data = json.dumps(decrypted_dict) if decrypted_dict else None
                    needs_update = True

            if needs_update:
                session.execute(
                    text("UPDATE pipeline_jobs SET file_content = :file_content, result_data = :result_data WHERE id = :id"),
                    {"file_content": new_file_content, "result_data": new_result_data, "id": job_id}
                )
                decrypted_count += 1
                print(f"   ✓ Decrypted job {job_id}")

        except Exception as e:
            print(f"   ⚠ Failed to decrypt job {job_id}: {e}")

    print(f"   Decrypted {decrypted_count} pipeline jobs")
    return decrypted_count


def decrypt_pipeline_step_executions(session):
    """Decrypt input_text and output_text in pipeline_step_executions table."""
    print("\n📝 Decrypting pipeline_step_executions table...")

    result = session.execute(text("SELECT id, input_text, output_text FROM pipeline_step_executions"))
    rows = result.fetchall()

    decrypted_count = 0
    for row in rows:
        exec_id, input_text, output_text = row

        try:
            needs_update = False
            new_input_text = input_text
            new_output_text = output_text

            if input_text and (input_text.startswith('gAAAAA') or input_text.startswith('Z0FBQUFB')):
                new_input_text = encryptor.decrypt_field(input_text)
                needs_update = True

            if output_text and (output_text.startswith('gAAAAA') or output_text.startswith('Z0FBQUFB')):
                new_output_text = encryptor.decrypt_field(output_text)
                needs_update = True

            if needs_update:
                session.execute(
                    text("UPDATE pipeline_step_executions SET input_text = :input_text, output_text = :output_text WHERE id = :id"),
                    {"input_text": new_input_text, "output_text": new_output_text, "id": exec_id}
                )
                decrypted_count += 1
                print(f"   ✓ Decrypted execution {exec_id}")

        except Exception as e:
            print(f"   ⚠ Failed to decrypt execution {exec_id}: {e}")

    print(f"   Decrypted {decrypted_count} step executions")
    return decrypted_count


def decrypt_system_settings(session):
    """Decrypt value in system_settings table."""
    print("\n⚙️ Decrypting system_settings table...")

    result = session.execute(text("SELECT id, key, value FROM system_settings"))
    rows = result.fetchall()

    decrypted_count = 0
    for row in rows:
        setting_id, key, value = row

        try:
            if value and (value.startswith('gAAAAA') or value.startswith('Z0FBQUFB')):
                new_value = encryptor.decrypt_field(value)
                session.execute(
                    text("UPDATE system_settings SET value = :value WHERE id = :id"),
                    {"value": new_value, "id": setting_id}
                )
                decrypted_count += 1
                print(f"   ✓ Decrypted setting '{key}'")

        except Exception as e:
            print(f"   ⚠ Failed to decrypt setting {key}: {e}")

    print(f"   Decrypted {decrypted_count} settings")
    return decrypted_count


def main():
    print("=" * 60)
    print("🔓 Dev Database Decryption Migration")
    print("=" * 60)

    # Check encryption is enabled
    if not encryptor.is_enabled():
        print("\n❌ ERROR: ENCRYPTION_ENABLED is false!")
        print("   This script must run with encryption ENABLED to decrypt data.")
        print("   Set ENCRYPTION_ENABLED=true and ENCRYPTION_KEY before running.")
        sys.exit(1)

    print("\n✅ Encryption is enabled - proceeding with decryption")

    # Connect to database
    db_url = get_database_url()
    print(f"\n🔗 Connecting to database...")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        total_decrypted = 0

        # Decrypt each table
        total_decrypted += decrypt_users(session)
        total_decrypted += decrypt_pipeline_jobs(session)
        total_decrypted += decrypt_pipeline_step_executions(session)
        total_decrypted += decrypt_system_settings(session)

        # Commit all changes
        session.commit()

        print("\n" + "=" * 60)
        print(f"✅ Migration complete! Decrypted {total_decrypted} total records.")
        print("=" * 60)
        print("\nYou can now set ENCRYPTION_ENABLED=false in your dev environment.")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
