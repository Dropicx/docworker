#!/bin/bash
set -e

echo "🚀 Starting DocTranslator Backend..."

# Run encryption migration if legacy key is set (idempotent - safe to run every deploy)
if [ -n "$ENCRYPTION_KEY_FERNET_LEGACY" ]; then
    echo "🔐 Running encryption migration (AES-256-GCM)..."
    python migrations/upgrade_encryption_to_aes256gcm.py || echo "⚠️ Migration completed or no data to migrate"
else
    echo "ℹ️ No ENCRYPTION_KEY_FERNET_LEGACY set, skipping migration"
fi

echo "🌐 Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 9122
