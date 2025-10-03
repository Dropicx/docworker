#!/bin/sh
set -e

echo "🚀 Starting Frontend with dynamic configuration..."

# Get backend URL from environment variable
# Railway provides this automatically via service references
BACKEND_URL=${BACKEND_INTERNAL_URL:-"http://backend.railway.internal:9122"}

echo "📡 Backend URL: $BACKEND_URL"

# Create nginx configuration with environment variable substitution
cat > /etc/nginx/conf.d/default.conf << EOF
server {
    listen 8080;
    server_name localhost;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private auth;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/javascript
        application/xml+rss
        application/json;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Frontend files
    location / {
        root /usr/share/nginx/html;
        index index.html index.htm;

        # React Router support
        try_files \$uri \$uri/ /index.html;

        # Cache headers for static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # No cache for HTML files
        location ~* \.html$ {
            expires -1;
            add_header Cache-Control "no-cache, no-store, must-revalidate";
        }
    }

    # API proxy to backend (dynamic from environment)
    location /api/ {
        proxy_pass ${BACKEND_URL};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeouts for large files
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;

        # Buffer settings for large uploads
        client_max_body_size 50M;
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # Favicon handling
    location = /favicon.ico {
        log_not_found off;
        access_log off;
    }

    # Robots.txt
    location = /robots.txt {
        log_not_found off;
        access_log off;
        return 200 "User-agent: *\nDisallow: /\n";
    }
}
EOF

echo "✅ Nginx configuration generated"
cat /etc/nginx/conf.d/default.conf

echo "🚀 Starting nginx..."
exec nginx -g "daemon off;"
