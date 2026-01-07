#!/usr/bin/env python3
"""
Standalone Dev Database Decryption

Minimal dependencies - only needs cryptography and psycopg2.
"""

import base64
import json
import os
import sys

# Install dependencies if needed:
# pip3 install cryptography psycopg2-binary

from cryptography.fernet import Fernet, InvalidToken
import psycopg2


ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "WR_RE1Ortnd5jq_92lrZkuI0YswP9FTuQCn_AZ9qf4c=")
DATABASE_URL = "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"


def get_cipher():
    """Get Fernet cipher from key."""
    return Fernet(ENCRYPTION_KEY.encode())


def decrypt_field(ciphertext):
    """Decrypt a single field."""
    if not ciphertext:
        return None

    try:
        # Decode from our base64 wrapper
        encrypted_bytes = base64.b64decode(ciphertext.encode("ascii"))
        # Decrypt with Fernet
        cipher = get_cipher()
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        print(f"      Decrypt error: {e}")
        return None


def decrypt_binary_field(encrypted_string):
    """Decrypt a binary field."""
    if not encrypted_string:
        return None

    try:
        # Step 1: Decrypt to get base64 string
        base64_string = decrypt_field(encrypted_string)
        if not base64_string:
            return None
        # Step 2: Decode base64 to get original binary
        return base64.b64decode(base64_string.encode("ascii"))
    except Exception as e:
        print(f"      Binary decrypt error: {e}")
        return None


def is_encrypted(value):
    """Check if value looks encrypted."""
    if not value or not isinstance(value, str):
        return False
    return value.startswith('gAAAAA') or value.startswith('Z0FBQUFB')


def main():
    print("=" * 60)
    print("🔓 Dev Database Decryption (Standalone)")
    print("=" * 60)

    # Connect to database
    print(f"\n🔗 Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    total_decrypted = 0

    try:
        # 1. Decrypt users table
        print("\n📧 Decrypting users table...")
        cur.execute("SELECT id, email, full_name FROM users")
        rows = cur.fetchall()

        for row in rows:
            user_id, email, full_name = row
            needs_update = False
            new_email = email
            new_full_name = full_name

            if is_encrypted(email):
                new_email = decrypt_field(email)
                needs_update = True

            if is_encrypted(full_name):
                new_full_name = decrypt_field(full_name)
                needs_update = True

            if needs_update and new_email:
                cur.execute(
                    "UPDATE users SET email = %s, full_name = %s WHERE id = %s",
                    (new_email, new_full_name, user_id)
                )
                total_decrypted += 1
                print(f"   ✓ Decrypted user {user_id}: {new_email[:30] if new_email else 'N/A'}...")

        # 2. Decrypt pipeline_jobs table
        print("\n📄 Decrypting pipeline_jobs table...")
        cur.execute("SELECT id, result_data FROM pipeline_jobs")
        rows = cur.fetchall()

        for row in rows:
            job_id, result_data = row

            if result_data and is_encrypted(result_data):
                decrypted_json_str = decrypt_field(result_data)
                if decrypted_json_str:
                    cur.execute(
                        "UPDATE pipeline_jobs SET result_data = %s WHERE id = %s",
                        (decrypted_json_str, job_id)
                    )
                    total_decrypted += 1
                    print(f"   ✓ Decrypted job {job_id} result_data")

        # Note: file_content is LargeBinary, handled differently - skip for now
        # as it's stored as binary, not encrypted string in most cases

        # 3. Decrypt pipeline_step_executions table
        print("\n📝 Decrypting pipeline_step_executions table...")
        cur.execute("SELECT id, input_text, output_text FROM pipeline_step_executions")
        rows = cur.fetchall()

        for row in rows:
            exec_id, input_text, output_text = row
            needs_update = False
            new_input = input_text
            new_output = output_text

            if is_encrypted(input_text):
                new_input = decrypt_field(input_text)
                needs_update = True

            if is_encrypted(output_text):
                new_output = decrypt_field(output_text)
                needs_update = True

            if needs_update:
                cur.execute(
                    "UPDATE pipeline_step_executions SET input_text = %s, output_text = %s WHERE id = %s",
                    (new_input, new_output, exec_id)
                )
                total_decrypted += 1
                print(f"   ✓ Decrypted execution {exec_id}")

        # 4. Decrypt system_settings table
        print("\n⚙️ Decrypting system_settings table...")
        cur.execute("SELECT id, key, value FROM system_settings")
        rows = cur.fetchall()

        for row in rows:
            setting_id, key, value = row

            if is_encrypted(value):
                new_value = decrypt_field(value)
                if new_value:
                    cur.execute(
                        "UPDATE system_settings SET value = %s WHERE id = %s",
                        (new_value, setting_id)
                    )
                    total_decrypted += 1
                    print(f"   ✓ Decrypted setting '{key}'")

        # Commit all changes
        conn.commit()

        print("\n" + "=" * 60)
        print(f"✅ Migration complete! Decrypted {total_decrypted} records.")
        print("=" * 60)
        print("\nYou can now set ENCRYPTION_ENABLED=false in your dev environment.")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
