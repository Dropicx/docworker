#!/bin/sh
# PaddleOCR Service Entrypoint
# Fixes volume permissions and starts the service

set -e

# Fix permissions on volume mount (Railway mounts volumes as root)
if [ -d "/home/appuser/.paddleocr" ]; then
    echo "🔧 Fixing volume permissions..."
    chown -R appuser:appuser /home/appuser/.paddleocr
fi

# Switch to appuser and run the application
echo "🚀 Starting PaddleOCR service as appuser..."
exec su appuser -c "python -W ignore::UserWarning -m uvicorn app.main:app --host 0.0.0.0 --port 9123 --log-level info"
