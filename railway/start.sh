#!/bin/bash
set -e

echo "=== Starting DocTranslator on Railway ==="
echo "Environment variables:"
echo "USE_OVH_ONLY: ${USE_OVH_ONLY:-not set}"
echo "OVH_API_ENDPOINT: ${OVH_API_ENDPOINT:-not set}"
echo "OVH_API_KEY: ${OVH_API_KEY:0:10}..." # Show only first 10 chars for security
echo "PORT: ${PORT:-8080}"

# Railway provides PORT environment variable that MUST be used
RAILWAY_PORT=${PORT:-8080}
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

# Create nginx config with Railway's PORT
cat > /etc/nginx/conf.d/railway-port.conf <<EOF
server {
    listen ${RAILWAY_PORT};
    server_name _;
    
    # Frontend static files
    location / {
        root /app/frontend/build;
        try_files \$uri \$uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)\$ {
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:9122;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts for long-running AI processing
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:9122/api/health/simple;
        proxy_intercept_errors on;
        error_page 502 503 504 =200 /health-nginx;
        access_log off;
    }
    
    # Nginx health check fallback
    location /health-nginx {
        return 200 'nginx-ok-backend-starting';
        add_header Content-Type text/plain;
        access_log off;
    }
}
EOF

echo "Starting nginx on port ${RAILWAY_PORT}..."
exec nginx -g "daemon off;"