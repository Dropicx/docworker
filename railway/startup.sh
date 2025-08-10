#!/bin/bash
set -e

echo "🚀 Starting DocTranslator services on Railway..."
echo "================================================"

# Debug: Print environment variables (masking sensitive values)
echo "📊 Environment Variables Check:"
echo "   USE_OVH_ONLY: ${USE_OVH_ONLY:-not set}"
echo "   OVH_AI_BASE_URL: ${OVH_AI_BASE_URL:-not set}"
echo "   OVH_MAIN_MODEL: ${OVH_MAIN_MODEL:-not set}"

# Check if OVH token is set (don't print the actual value)
if [ -n "$OVH_AI_ENDPOINTS_ACCESS_TOKEN" ]; then
    echo "   OVH_AI_ENDPOINTS_ACCESS_TOKEN: ✅ Set (${#OVH_AI_ENDPOINTS_ACCESS_TOKEN} chars)"
else
    echo "   OVH_AI_ENDPOINTS_ACCESS_TOKEN: ❌ NOT SET - API will fail!"
fi

echo "   ENVIRONMENT: ${ENVIRONMENT:-not set}"
echo "   PORT: ${PORT:-not set}"
echo "   RAILWAY_ENVIRONMENT: ${RAILWAY_ENVIRONMENT:-not set}"
echo "================================================"

# Create necessary directories
mkdir -p /app/logs /tmp/medical-translator

# Wait for backend to be ready
echo "Starting backend service..."
cd /app/backend
uvicorn app.main:app --host 127.0.0.1 --port 9122 --workers 1 &
BACKEND_PID=$!

# Wait for backend to be healthy
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:9122/api/health/simple > /dev/null; then
        echo "Backend is ready!"
        break
    fi
    echo "Waiting for backend... ($i/30)"
    sleep 2
done

# Start nginx
echo "Starting nginx..."
nginx -g "daemon off;" &
NGINX_PID=$!

# Keep the script running and forward signals
trap "kill $BACKEND_PID $NGINX_PID" EXIT

# Wait for both processes
wait $BACKEND_PID $NGINX_PID