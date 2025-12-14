"""
Check Encryption Status in Database

Connects to database and verifies if document content is encrypted.
"""

import base64
import sys

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
except ImportError:
    print("❌ SQLAlchemy not installed. Install with: pip install sqlalchemy psycopg2-binary")
    sys.exit(1)


def check_if_encrypted_heuristic(value) -> bool:
    """
    Heuristically check if a value appears to be encrypted.
    
    Fernet tokens are base64-encoded and start with specific patterns.
    """
    if value is None:
        return False
    
    # If it's bytes, decode to string first
    if isinstance(value, bytes):
        try:
            value_str = value.decode("utf-8")
        except UnicodeDecodeError:
            # If it can't be decoded as UTF-8, it's likely not encrypted
            # (encrypted values are stored as UTF-8 bytes of base64 strings)
            return False
    else:
        value_str = str(value)
    
    # Check if it looks like a base64-encoded Fernet token
    # Fernet tokens are base64-encoded and typically start with 'gAAAAA' or similar
    # They're also quite long (150+ characters for even short inputs)
    
    if not value_str or len(value_str) < 50:
        return False
    
    # Check if it's valid base64
    try:
        decoded = base64.b64decode(value_str)
        # Fernet tokens have a specific structure
        # They start with version byte 0x80
        if len(decoded) > 0 and decoded[0] == 0x80:
            return True
    except Exception:
        pass
    
    # Additional check: encrypted strings are typically much longer than plaintext
    # and contain only base64 characters
    if len(value_str) > 100 and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in value_str):
        # Could be encrypted, but not definitive
        return True
    
    return False


def main():
    """Check encryption status of latest pipeline job."""
    # Database connection string
    db_url = "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"
    
    print("=" * 80)
    print("Checking Encryption Status in Database")
    print("=" * 80)
    print()
    
    # Create database connection
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Get latest pipeline job using raw SQL
        result = session.execute(
            text("""
                SELECT id, job_id, processing_id, filename, created_at, status,
                       LENGTH(file_content) as file_content_length,
                       file_content IS NULL as file_content_is_null
                FROM pipeline_jobs
                ORDER BY created_at DESC
                LIMIT 1
            """)
        )
        job_row = result.fetchone()
        
        if not job_row:
            print("❌ No pipeline jobs found in database")
            return
        
        print(f"📋 Latest Pipeline Job:")
        print(f"   ID: {job_row[0]}")
        print(f"   Job ID: {job_row[1]}")
        print(f"   Processing ID: {job_row[2]}")
        print(f"   Filename: {job_row[3]}")
        print(f"   Created: {job_row[4]}")
        print(f"   Status: {job_row[5]}")
        print()
        
        # Get file_content sample
        if job_row[6] is None or job_row[7]:
            print("   ⚠️  file_content is NULL (cleared)")
            file_encrypted = None
        else:
            file_length = job_row[6]
            print(f"   file_content length: {file_length} bytes")
            
            # Get first 200 bytes to check
            result = session.execute(
                text("""
                    SELECT SUBSTRING(file_content::text, 1, 200) as preview
                    FROM pipeline_jobs
                    WHERE id = :job_id
                """),
                {"job_id": job_row[0]}
            )
            preview_row = result.fetchone()
            
            if preview_row and preview_row[0]:
                preview = preview_row[0]
                is_encrypted = check_if_encrypted_heuristic(preview)
                
                if is_encrypted:
                    print("   ✅ ENCRYPTED (appears to be Fernet token)")
                    print(f"   Preview: {preview[:100]}...")
                    file_encrypted = True
                else:
                    print("   ❌ NOT ENCRYPTED (appears to be plaintext)")
                    # Check if it looks like PDF
                    if preview.startswith("%PDF") or preview.startswith("\\x255044462d"):
                        print("   ⚠️  This looks like plaintext PDF binary data!")
                    print(f"   Preview: {preview[:100]}...")
                    file_encrypted = False
            else:
                print("   ⚠️  Could not retrieve preview")
                file_encrypted = None
        
        print()
        
        # Get step executions
        result = session.execute(
            text("""
                SELECT id, step_name, step_order,
                       LENGTH(input_text) as input_length,
                       input_text IS NULL as input_is_null,
                       LENGTH(output_text) as output_length,
                       output_text IS NULL as output_is_null,
                       SUBSTRING(input_text, 1, 100) as input_preview,
                       SUBSTRING(output_text, 1, 100) as output_preview
                FROM pipeline_step_executions
                WHERE job_id = :job_id
                ORDER BY step_order
            """),
            {"job_id": job_row[1]}
        )
        step_rows = result.fetchall()
        
        print(f"🔍 Checking {len(step_rows)} step execution(s)...")
        print()
        
        text_encrypted_list = []
        
        for i, step_row in enumerate(step_rows, 1):
            print(f"   Step {i}: {step_row[2]} (order: {step_row[3]})")
            
            # Check input_text
            if step_row[4] or step_row[5]:  # input_is_null
                print("      input_text: NULL")
                input_encrypted = None
            else:
                input_length = step_row[4]  # input_length
                input_preview = step_row[8] if step_row[8] else ""
                is_encrypted_input = check_if_encrypted_heuristic(input_preview)
                
                print(f"      input_text: {input_length} chars - ", end="")
                if is_encrypted_input:
                    print("✅ ENCRYPTED")
                    print(f"         Preview: {input_preview[:80]}...")
                    input_encrypted = True
                else:
                    print("❌ NOT ENCRYPTED")
                    print(f"         Preview: {input_preview[:80]}...")
                    input_encrypted = False
            
            # Check output_text
            if step_row[6] or step_row[7]:  # output_is_null
                print("      output_text: NULL")
                output_encrypted = None
            else:
                output_length = step_row[6]  # output_length
                output_preview = step_row[9] if step_row[9] else ""
                is_encrypted_output = check_if_encrypted_heuristic(output_preview)
                
                print(f"      output_text: {output_length} chars - ", end="")
                if is_encrypted_output:
                    print("✅ ENCRYPTED")
                    print(f"         Preview: {output_preview[:80]}...")
                    output_encrypted = True
                else:
                    print("❌ NOT ENCRYPTED")
                    print(f"         Preview: {output_preview[:80]}...")
                    output_encrypted = False
            
            text_encrypted_list.append((input_encrypted, output_encrypted))
            print()
        
        # Summary
        print("=" * 80)
        print("Summary")
        print("=" * 80)
        
        all_text_encrypted = all(
            (enc is None or enc is True) for enc_pair in text_encrypted_list for enc in enc_pair
        )
        
        if file_encrypted and all_text_encrypted:
            print("✅ All content appears to be ENCRYPTED")
        elif file_encrypted is True and not all_text_encrypted:
            print("⚠️  file_content is encrypted, but some text fields are NOT encrypted")
        elif file_encrypted is False and all_text_encrypted:
            print("⚠️  Text fields are encrypted, but file_content is NOT encrypted")
        elif file_encrypted is False:
            print("❌ Content does NOT appear to be encrypted")
            print()
            print("   This means the encryption implementation may not be working correctly,")
            print("   or encryption was disabled when this data was stored.")
        else:
            print("⚠️  Could not determine encryption status for all fields")
        
        print()
        print("Note: This is a heuristic check based on data patterns.")
        print("      Actual encryption status depends on ENCRYPTION_ENABLED and")
        print("      whether the repository was used when storing the data.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
