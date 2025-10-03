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
# Use :: for IPv6 (Railway internal networking) - listens on both IPv4 and IPv6
echo "🚀 Starting PaddleOCR service as appuser..."
exec su appuser -c "python -W ignore::UserWarning -m uvicorn app.main:app --host :: --port 9123 --log-level info"
