#!/bin/bash
# Debug startup script to diagnose 500 error

echo "=== Starting DocTranslator on Railway (DEBUG MODE) ==="
echo "Timestamp: $(date)"
echo "Environment check:"
echo "- USE_OVH_ONLY: ${USE_OVH_ONLY:-not set}"
echo "- OVH_API_ENDPOINT: ${OVH_API_ENDPOINT:-not set}"
echo "- OVH_API_KEY: ${OVH_API_KEY:+[SET]}"
echo "- PORT: ${PORT:-8080}"
echo "- RAILWAY_ENVIRONMENT: ${RAILWAY_ENVIRONMENT:-not set}"

# Railway provides PORT environment variable that MUST be used
RAILWAY_PORT=${PORT:-8080}

# Check what files exist
echo ""
echo "=== File System Check ==="
echo "Current directory: $(pwd)"
echo "Directory contents:"
ls -la /app/

echo ""
echo "Checking for frontend dist:"
if [ -d "/app/frontend/dist" ]; then
    echo "✓ Frontend dist directory exists"
    echo "Contents:"
    ls -la /app/frontend/dist/ | head -20
elif [ -d "/app/frontend/build" ]; then
    echo "⚠ Found 'build' directory instead of 'dist'"
    echo "Contents:"
    ls -la /app/frontend/build/ | head -20
else
    echo "✗ Frontend dist directory NOT FOUND!"
    echo "Checking /app/frontend:"
    ls -la /app/frontend/ 2>/dev/null || echo "Frontend directory doesn't exist"
fi

echo ""
echo "Checking for backend:"
if [ -d "/app/backend" ]; then
    echo "✓ Backend directory exists"
else
    echo "✗ Backend directory NOT FOUND!"
fi

# Ensure required directories exist
mkdir -p /app/logs /tmp/medical-translator /etc/nginx/conf.d

# Set environment
export PYTHONPATH="/app/backend:${PYTHONPATH}"
export USE_OVH_ONLY="true"
export PYTHONUNBUFFERED=1

# Function to create nginx config with debugging
create_nginx_config() {
    echo "[$(date)] Creating nginx configuration for port $RAILWAY_PORT..."
    
    # Check if frontend files exist and set the correct path
    if [ -d "/app/frontend/dist" ] && [ -f "/app/frontend/dist/index.html" ]; then
        FRONTEND_ROOT="/app/frontend/dist"
        echo "Using frontend root: $FRONTEND_ROOT (Vite dist)"
    elif [ -d "/app/frontend/build" ] && [ -f "/app/frontend/build/index.html" ]; then
        FRONTEND_ROOT="/app/frontend/build"
        echo "Using frontend root: $FRONTEND_ROOT (legacy build)"
    elif [ -d "/app/frontend" ] && [ -f "/app/frontend/index.html" ]; then
        FRONTEND_ROOT="/app/frontend"
        echo "Using frontend root: $FRONTEND_ROOT (no subdirectory)"
    else
        FRONTEND_ROOT="/app/frontend/dist"
        echo "WARNING: Frontend files not found, using default path: $FRONTEND_ROOT"
        # Create a minimal index.html for debugging
        mkdir -p $FRONTEND_ROOT
        cat > $FRONTEND_ROOT/index.html <<HTML
<!DOCTYPE html>
<html>
<head><title>DocTranslator Debug</title></head>
<body>
<h1>DocTranslator - Debug Mode</h1>
<p>Frontend build not found. This is a debug page.</p>
<p>Timestamp: $(date)</p>
<p>Port: $RAILWAY_PORT</p>
<h2>Directory Structure:</h2>
<pre>$(ls -la /app/)</pre>
</body>
</html>
HTML
    fi
    
    cat > /etc/nginx/conf.d/default.conf <<EOF
server {
    listen ${RAILWAY_PORT};
    server_name _;
    
    # Debug headers
    add_header X-Debug-Mode "true";
    add_header X-Frontend-Root "${FRONTEND_ROOT}";
    
    # Enable error logging
    error_log /app/logs/nginx-error.log debug;
    access_log /app/logs/nginx-access.log;
    
    # Simple health check
    location /health {
        access_log off;
        return 200 "healthy";
        add_header Content-Type text/plain;
    }
    
    # Debug endpoint
    location /debug {
        return 200 "Frontend root: ${FRONTEND_ROOT}\nFiles exist: \$(ls ${FRONTEND_ROOT} 2>/dev/null | wc -l) files\nPort: ${RAILWAY_PORT}";
        add_header Content-Type text/plain;
    }
    
    # Frontend with detailed error handling
    location / {
        root ${FRONTEND_ROOT};
        try_files \$uri \$uri/ /index.html =404;
        
        # If file not found, show debug info
        error_page 404 /404.html;
    }
    
    # Custom 404 page
    location = /404.html {
        internal;
        return 404 "File not found. Frontend root: ${FRONTEND_ROOT}";
        add_header Content-Type text/plain;
    }
    
    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:9122;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
        
        proxy_intercept_errors on;
        error_page 502 503 504 = @backend_down;
    }
    
    location @backend_down {
        return 503 "Backend service is starting, please wait...";
        add_header Content-Type text/plain;
        add_header Retry-After 30;
    }
}
EOF
}

# Try to start backend (but don't fail if it doesn't work)
echo ""
echo "[$(date)] Starting backend service..."
cd /app/backend 2>/dev/null && {
    python -m uvicorn app.main:app \
        --host 127.0.0.1 \
        --port 9122 \
        --workers 1 \
        --log-level info \
        --access-log \
        > /app/logs/backend.log 2>&1 &
    echo "Backend started with PID: $!"
} || {
    echo "Backend directory not found, skipping backend start"
}

# Create nginx config
create_nginx_config

# Show nginx error log in background for debugging
tail -f /app/logs/nginx-error.log 2>/dev/null &

# Start nginx
echo ""
echo "[$(date)] Starting nginx on port $RAILWAY_PORT..."
echo "You can check:"
echo "  - https://doctranslator-production.up.railway.app/ (main site)"
echo "  - https://doctranslator-production.up.railway.app/health (health check)"
echo "  - https://doctranslator-production.up.railway.app/debug (debug info)"
echo ""

# Start nginx in foreground
exec nginx -g "daemon off;"