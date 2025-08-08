#!/bin/bash
set -e

echo "=== Starting DocTranslator on Railway ==="
echo "Environment variables:"
echo "USE_OVH_ONLY: ${USE_OVH_ONLY:-not set}"
echo "OVH_API_ENDPOINT: ${OVH_API_ENDPOINT:-not set}"
echo "OVH_API_KEY: ${OVH_API_KEY:0:10}..." # Show only first 10 chars for security
echo "PORT: ${PORT:-8080}"
echo "PYTHONPATH: ${PYTHONPATH}"

# Ensure required directories exist
mkdir -p /app/logs /tmp/medical-translator

# Set Python path
export PYTHONPATH="/app/backend:${PYTHONPATH}"
export USE_OVH_ONLY="true"

# Start backend in background with explicit logging
echo "Starting backend service..."
cd /app/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 9122 --log-level info > /app/logs/backend.log 2>&1 &
BACKEND_PID=$!

# Give backend time to start
echo "Waiting for backend to initialize..."
sleep 10

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "ERROR: Backend failed to start!"
    echo "Backend logs:"
    cat /app/logs/backend.log
    exit 1
fi

# Test backend health
echo "Testing backend health endpoint..."
for i in {1..30}; do
    if curl -f -s http://127.0.0.1:9122/api/health/simple; then
        echo "Backend is healthy!"
        break
    else
        echo "Backend not ready yet... attempt $i/30"
        if [ $i -eq 10 ]; then
            echo "Backend logs so far:"
            tail -20 /app/logs/backend.log
        fi
    fi
    sleep 2
done

# Start nginx in foreground
echo "Starting nginx..."
exec nginx -g "daemon off;"