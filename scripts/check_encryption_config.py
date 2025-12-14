"""
Check if encryption is configured and enabled in the database environment.
"""

import os

print("=" * 80)
print("Encryption Configuration Check")
print("=" * 80)
print()

# Check environment variables
encryption_key = os.getenv("ENCRYPTION_KEY")
encryption_enabled = os.getenv("ENCRYPTION_ENABLED", "true")

print("Environment Variables:")
print(f"  ENCRYPTION_KEY: {'✅ Set' if encryption_key else '❌ NOT SET'}")
if encryption_key:
    print(f"    Length: {len(encryption_key)} chars")
    print(f"    Preview: {encryption_key[:20]}...")
print(f"  ENCRYPTION_ENABLED: {encryption_enabled}")
print()

if not encryption_key:
    print("❌ ENCRYPTION_KEY is not set!")
    print("   Encryption will fail. Set it in Railway environment variables.")
    print()
    print("   Generate a key with:")
    print("   python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
elif encryption_enabled.lower() != "true":
    print("⚠️  ENCRYPTION_ENABLED is not 'true'")
    print("   Encryption is disabled. Set ENCRYPTION_ENABLED=true to enable.")
else:
    print("✅ Encryption appears to be configured correctly")
    print()
    print("However, the database check showed content is NOT encrypted.")
    print("This could mean:")
    print("  1. The code fix hasn't been deployed yet")
    print("  2. There's a bug in the encryption logic")
    print("  3. The job was created before encryption was enabled")

