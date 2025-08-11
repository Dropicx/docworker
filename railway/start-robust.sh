#!/bin/bash
# Robust startup script that won't exit on failure

echo "=== Starting DocTranslator on Railway ==="
echo "Timestamp: $(date)"
echo "Environment check:"
echo "- USE_OVH_ONLY: ${USE_OVH_ONLY:-not set}"
echo "- OVH_AI_BASE_URL: ${OVH_AI_BASE_URL:-not set}"
echo "- OVH_AI_ENDPOINTS_ACCESS_TOKEN: ${OVH_AI_ENDPOINTS_ACCESS_TOKEN:+[SET]}"
echo "- PORT: ${PORT:-8080}"
echo "- RAILWAY_ENVIRONMENT: ${RAILWAY_ENVIRONMENT:-not set}"

# Check OCR capabilities
echo ""
echo "=== OCR Capability Check ==="
if command -v tesseract &> /dev/null; then
    echo "✅ Tesseract OCR is installed:"
    tesseract --version 2>&1 | head -n 1
    echo "   Available languages:"
    tesseract --list-langs 2>&1 | grep -E "deu|eng" | head -5
else
    echo "❌ Tesseract OCR is NOT installed"
fi

if command -v pdftoppm &> /dev/null; then
    echo "✅ Poppler-utils (PDF to image) is installed"
else
    echo "❌ Poppler-utils is NOT installed (PDF OCR will not work)"
fi
echo "==="

# Railway provides PORT environment variable that MUST be used
RAILWAY_PORT=${PORT:-8080}

# Ensure required directories exist
mkdir -p /app/logs /tmp/medical-translator /etc/nginx/conf.d

# Set environment
export PYTHONPATH="/app/backend:${PYTHONPATH}"
export USE_OVH_ONLY="true"
export PYTHONUNBUFFERED=1

# Function to start backend with retries
start_backend() {
    echo "[$(date)] Starting backend service..."
    
    # Log environment variables for debugging
    echo "[$(date)] Environment check for backend:"
    echo "  OVH_AI_ENDPOINTS_ACCESS_TOKEN: ${OVH_AI_ENDPOINTS_ACCESS_TOKEN:+[SET]}"
    echo "  OVH_AI_BASE_URL: ${OVH_AI_BASE_URL:-not set}"
    echo "  USE_OVH_ONLY: ${USE_OVH_ONLY:-not set}"
    echo "  PYTHONPATH: ${PYTHONPATH:-not set}"
    
    cd /app/backend
    
    # Export environment variables explicitly
    export OVH_AI_ENDPOINTS_ACCESS_TOKEN="${OVH_AI_ENDPOINTS_ACCESS_TOKEN}"
    export OVH_AI_BASE_URL="${OVH_AI_BASE_URL}"
    export USE_OVH_ONLY="true"
    export PYTHONPATH="/app/backend:${PYTHONPATH}"
    
    # Try to start backend - log to stdout for Railway
    # Increased limits for large file uploads (50MB)
    # Removed --access-log to disable HTTP request logging for cleaner output
    python -m uvicorn app.main:app \
        --host 127.0.0.1 \
        --port 9122 \
        --workers 1 \
        --log-level info \
        --limit-max-requests 1000 \
        --h11-max-incomplete-event-size 52428800 \
        2>&1 | tee /app/logs/backend.log &
    
    BACKEND_PID=$!
    echo "[$(date)] Backend started with PID: $BACKEND_PID"
    
    # Wait and check if it's still running
    sleep 5
    
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo "[$(date)] Backend is running"
        # Test if backend responds
        sleep 2
        if curl -s http://127.0.0.1:9122/api/health/simple > /dev/null 2>&1; then
            echo "[$(date)] Backend health check passed!"
        else
            echo "[$(date)] Backend is running but health check failed"
            echo "[$(date)] Backend logs:"
            tail -20 /app/logs/backend.log 2>/dev/null || echo "No logs available"
        fi
        return 0
    else
        echo "[$(date)] Backend failed to start. Logs:"
        cat /app/logs/backend.log 2>/dev/null || echo "No logs available"
        return 1
    fi
}

# Function to create nginx config
create_nginx_config() {
    echo "[$(date)] Creating nginx configuration for port $RAILWAY_PORT..."
    
    cat > /etc/nginx/conf.d/default.conf <<EOF
server {
    listen ${RAILWAY_PORT};
    server_name _;
    
    # Increase client max body size for large image uploads (50MB)
    client_max_body_size 50M;
    client_body_buffer_size 10M;
    
    # Simple health check that always works
    location /health {
        access_log off;
        return 200 "healthy";
        add_header Content-Type text/plain;
    }
    
    # Frontend (Vite outputs to 'dist')
    location / {
        root /app/frontend/dist;
        try_files \$uri \$uri/ /index.html;
    }
    
    # Backend API with error handling
    location /api/ {
        proxy_pass http://127.0.0.1:9122/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Long timeouts for AI processing
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
        
        # If backend is down, return service unavailable
        proxy_intercept_errors on;
        error_page 502 503 504 = @backend_down;
    }
    
    # Special handling for health endpoints
    location = /api/health/env-debug {
        proxy_pass http://127.0.0.1:9122/api/health/env-debug;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        
        # Return debug info even if backend is down
        proxy_intercept_errors on;
        error_page 502 503 504 = @health_fallback;
    }
    
    location @health_fallback {
        default_type application/json;
        return 200 '{"status":"backend_down","message":"Backend is not responding","env":{"USE_OVH_ONLY":"${USE_OVH_ONLY}","OVH_AI_BASE_URL":"${OVH_AI_BASE_URL}","OVH_TOKEN_SET":"${OVH_AI_ENDPOINTS_ACCESS_TOKEN:+true}"}}';
    }
    
    location @backend_down {
        return 503 "Backend service is starting, please wait...";
        add_header Content-Type text/plain;
        add_header Retry-After 30;
    }
}
EOF
}

# Main startup sequence
echo "[$(date)] Initializing services..."

# Try to start backend with retries
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "[$(date)] Backend startup attempt $((RETRY_COUNT + 1))/$MAX_RETRIES"
    
    if start_backend; then
        echo "[$(date)] Backend started successfully"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "[$(date)] Retrying in 10 seconds..."
            sleep 10
        fi
    fi
done

# Create nginx config regardless of backend status
create_nginx_config

# Start nginx (this will keep the container running)
echo "[$(date)] Starting nginx on port $RAILWAY_PORT..."
echo "[$(date)] Application URL: https://doctranslator-production.up.railway.app"

# Start nginx in foreground - this keeps container alive
exec nginx -g "daemon off;"