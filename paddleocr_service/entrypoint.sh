#!/bin/sh
# PaddleOCR Service Entrypoint
# Fixes volume permissions and starts the service
# Models are cached on persistent volume at /home/appuser/.paddleocr

set -e

MODEL_CACHE="/home/appuser/.paddleocr"

# Fix permissions on volume mount (Railway mounts volumes as root)
if [ -d "$MODEL_CACHE" ]; then
    echo "🔧 Fixing volume permissions..."
    chown -R appuser:appuser "$MODEL_CACHE"

    # Check if models are already cached
    if [ -d "$MODEL_CACHE/official_models" ]; then
        MODEL_COUNT=$(ls -1 "$MODEL_CACHE/official_models" 2>/dev/null | wc -l)
        echo "📦 Found $MODEL_COUNT cached models in $MODEL_CACHE/official_models"
    else
        echo "📥 No cached models found - will download on first startup (~2GB)"
    fi
else
    echo "⚠️ Volume not mounted at $MODEL_CACHE - models will be downloaded each restart"
fi

# Switch to appuser and run the application
# Use :: for IPv6 (Railway internal networking) - listens on both IPv4 and IPv6
echo "🚀 Starting PaddleOCR service as appuser..."
exec su appuser -c "python -W ignore::UserWarning -m uvicorn app.main:app --host :: --port 9123 --log-level info"
