#!/bin/sh
set -e

echo "========================================"
echo "🚀 Starting DocTranslator Backend..."
echo "========================================"

# Debug: Show encryption-related environment variables
echo "🔑 Encryption Environment Check:"
if [ -n "$ENCRYPTION_KEY" ]; then
    echo "   ENCRYPTION_KEY: ✅ Set (${#ENCRYPTION_KEY} chars)"
else
    echo "   ENCRYPTION_KEY: ❌ NOT SET"
fi

if [ -n "$ENCRYPTION_KEY_FERNET_LEGACY" ]; then
    echo "   ENCRYPTION_KEY_FERNET_LEGACY: ✅ Set (${#ENCRYPTION_KEY_FERNET_LEGACY} chars)"
else
    echo "   ENCRYPTION_KEY_FERNET_LEGACY: ❌ NOT SET"
fi

if [ -n "$ENCRYPTION_ENABLED" ]; then
    echo "   ENCRYPTION_ENABLED: $ENCRYPTION_ENABLED"
else
    echo "   ENCRYPTION_ENABLED: not set (defaults to true)"
fi

echo "   DATABASE_URL: ${DATABASE_URL:+✅ Set}${DATABASE_URL:-❌ NOT SET}"
echo "========================================"

# Run encryption migration if legacy key is set (idempotent - safe to run every deploy)
if [ -n "$ENCRYPTION_KEY_FERNET_LEGACY" ]; then
    echo "🔐 Running encryption migration (Fernet → AES-256-GCM)..."
    python migrations/upgrade_encryption_to_aes256gcm.py 2>&1 || echo "⚠️ Migration completed or failed - check logs above"
    echo "========================================"
else
    echo "ℹ️  No ENCRYPTION_KEY_FERNET_LEGACY set, skipping migration"
    echo "========================================"
fi

echo "🌐 Starting uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 9122
