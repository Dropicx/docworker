"""
Test encryption directly to verify it works.
"""

import base64
import sys

# Simple test without app dependencies
def test_encryption():
    """Test if we can encrypt/decrypt binary data."""
    
    # Sample binary data (simulating PDF)
    test_binary = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj"
    
    print("Original binary:")
    print(f"  Length: {len(test_binary)} bytes")
    print(f"  Preview: {test_binary[:50]}")
    print()
    
    # Simulate what encrypt_binary_field does:
    # 1. Convert binary to base64
    base64_str = base64.b64encode(test_binary).decode("ascii")
    print("After base64 encoding:")
    print(f"  Length: {len(base64_str)} chars")
    print(f"  Preview: {base64_str[:50]}...")
    print()
    
    # 2. Encrypt (we can't do this without the key, but we can show the pattern)
    print("After encryption (would be):")
    print("  - Fernet encrypts the base64 string")
    print("  - Returns base64-encoded Fernet token (string)")
    print("  - Length: ~150+ chars for even small inputs")
    print()
    
    # 3. Convert to bytes for storage
    print("For LargeBinary column storage:")
    print("  - Encrypted string.encode('utf-8') → bytes")
    print("  - These bytes are stored in LargeBinary column")
    print()
    
    print("What we should see in database:")
    print("  - If encrypted: UTF-8 bytes of base64-encoded Fernet token")
    print("  - If NOT encrypted: Original PDF binary bytes")
    print()
    
    print("Current database shows:")
    print("  - Preview starts with: \\x255044462d...")
    print("  - This is hex-escaped PDF binary (\\x25 = '%', \\x50 = 'P', etc.)")
    print("  - This means: NOT ENCRYPTED")
    print()
    
    print("Expected if encrypted:")
    print("  - Preview would start with: gAAAAAB... (Fernet token)")
    print("  - Much longer than original (150+ chars even for small files)")
    print("  - Only base64 characters (A-Z, a-z, 0-9, +, /, =)")

if __name__ == "__main__":
    test_encryption()

