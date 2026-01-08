#!/bin/bash
set -e

echo "=========================================="
echo "PaddleOCR 3.x Deployment Script"
echo "=========================================="

cd /opt/paddleocr

# Read config
REPO=$(cat .repo 2>/dev/null || echo "Dropicx/doctranslator")
BRANCH=$(cat .branch 2>/dev/null || echo "dev")

# Read GitHub token if available
GITHUB_TOKEN=""
if [ -f ".github_token" ] && [ -s ".github_token" ]; then
    GITHUB_TOKEN=$(cat .github_token | tr -d '[:space:]')
fi

# Build repo URL (with or without token)
if [ -n "$GITHUB_TOKEN" ]; then
    REPO_URL="https://${GITHUB_TOKEN}@github.com/${REPO}.git"
    echo "Using authenticated GitHub access"
else
    REPO_URL="https://github.com/${REPO}.git"
    echo "Using public GitHub access"
fi

# Clone or update repo
if [ ! -d "doctranslator" ]; then
    echo "Cloning repository..."
    git clone -b $BRANCH "$REPO_URL" doctranslator
else
    echo "Updating repository..."
    cd doctranslator
    git remote set-url origin "$REPO_URL"
    git pull origin $BRANCH
    cd ..
fi

# Copy paddleocr_service files to /opt/paddleocr
echo "Copying service files..."
cp -r doctranslator/paddleocr_service/* /opt/paddleocr/

# Build Docker image (CPU mode)
echo "Building Docker image (CPU mode)..."
echo "This will take 5-10 minutes on first build..."
docker build -t paddleocr:cpu .

# Stop old container if running
docker-compose down 2>/dev/null || true

# Start service
echo "Starting service..."
docker-compose up -d

echo ""
echo "Waiting for PaddleOCR to start..."

for i in $(seq 1 20); do
    if curl -sf http://localhost:9124/health > /dev/null 2>&1; then
        echo ""
        echo "Service is healthy!"
        curl -s http://localhost:9124/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:9124/health
        break
    fi
    echo "Waiting... ($i/20)"
    sleep 5
done

# Final check
if ! curl -sf http://localhost:9124/health > /dev/null 2>&1; then
    echo "Service not responding yet. Check logs:"
    echo "  docker-compose logs -f"
    exit 1
fi

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo ""
echo "Service managed by systemd:"
echo "  systemctl status paddleocr"
echo "  systemctl restart paddleocr"
echo "  journalctl -u paddleocr -f"
echo ""
echo "Docker commands:"
echo "  View logs:  docker-compose logs -f"
echo "  Update:     ./deploy.sh"
echo ""
echo "API key is in /opt/paddleocr/.env (never logged)"

# Secure log file permissions
chmod 600 /var/log/paddleocr-deploy.log 2>/dev/null || true
