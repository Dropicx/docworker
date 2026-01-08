#!/bin/bash
set -e

echo "=========================================="
echo "SpaCy PII Service Deployment Script"
echo "=========================================="

cd /opt/pii

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

# Copy pii_service files to /opt/pii
echo "Copying PII service files..."
cp -r doctranslator/pii_service/* /opt/pii/

# Build Docker image (CPU mode with SpaCy models)
echo "Building Docker image with SpaCy models..."
echo "This will take 10-15 minutes on first build (downloading ~1.1GB models)..."
docker build -t spacy-pii:cpu .

# Stop old container if running
docker-compose down 2>/dev/null || true

# Start service
echo "Starting service..."
docker-compose up -d

echo ""
echo "Waiting for PII service to start (loading SpaCy models takes ~60 seconds)..."

for i in $(seq 1 40); do
    if curl -sf http://localhost:9125/health > /dev/null 2>&1; then
        echo ""
        echo "Service is healthy!"
        curl -s http://localhost:9125/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:9125/health
        break
    fi
    echo "Waiting... ($i/40)"
    sleep 5
done

# Final check
if ! curl -sf http://localhost:9125/health > /dev/null 2>&1; then
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
echo "  systemctl status pii"
echo "  systemctl restart pii"
echo "  journalctl -u pii -f"
echo ""
echo "Docker commands:"
echo "  View logs:  docker-compose logs -f"
echo "  Update:     ./deploy.sh"
echo ""
echo "API key is in /opt/pii/.env (never logged)"

# Secure log file permissions
chmod 600 /var/log/pii-deploy.log 2>/dev/null || true
