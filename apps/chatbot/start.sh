#!/bin/sh
set -e

echo "Starting Frag die Leitlinie frontend..."

# Extract DNS server from resolv.conf for Railway internal networking
RAW_DNS=$(grep nameserver /etc/resolv.conf | head -1 | awk '{print $2}')

# Wrap IPv6 addresses in brackets for nginx resolver
if echo "$RAW_DNS" | grep -q ':'; then
    export DNS_SERVER="[${RAW_DNS}]"
else
    export DNS_SERVER="$RAW_DNS"
fi
echo "DNS Server: ${DNS_SERVER}"

# Default environment variables
export PORT=${PORT:-8080}
export BACKEND_URL=${BACKEND_URL:-"backend.railway.internal"}
export BACKEND_PORT=${BACKEND_PORT:-9122}

echo "Configuration:"
echo "  PORT: ${PORT}"
echo "  BACKEND_URL: ${BACKEND_URL}"
echo "  BACKEND_PORT: ${BACKEND_PORT}"

# Substitute environment variables in nginx config
envsubst '${PORT} ${DNS_SERVER} ${BACKEND_URL} ${BACKEND_PORT}' \
    < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

echo "Nginx configuration generated successfully"

# Test nginx configuration
nginx -t

echo "Starting nginx..."
exec nginx -g 'daemon off;'
