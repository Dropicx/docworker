#!/bin/bash
set -e

echo "=========================================="
echo "PP-StructureV3 Deployment Script"
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
docker build --build-arg USE_GPU=false -t ppstructure:cpu .

# Stop old container if running
docker-compose down 2>/dev/null || true

# Start service
echo "Starting service..."
docker-compose up -d

echo ""
echo "Waiting for PP-StructureV3 to start..."
echo "(First startup downloads ~2GB of models)"

for i in $(seq 1 30); do
    if curl -sf http://localhost:9124/health > /dev/null 2>&1; then
        echo ""
        echo "Service is healthy!"
        curl -s http://localhost:9124/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:9124/health
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 10
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
echo "Add these to your backend environment:"
echo ""
SERVER_IP=$(curl -s ifconfig.me)
API_KEY=$(cat /opt/paddleocr/API_KEY.txt | tr -d '[:space:]')
echo "  EXTERNAL_OCR_URL=http://${SERVER_IP}:9124"
echo "  EXTERNAL_API_KEY=${API_KEY}"
echo "  USE_EXTERNAL_OCR=true"
echo ""
echo "Useful commands:"
echo "  View logs:  docker-compose logs -f"
echo "  Restart:    docker-compose restart"
echo "  Stop:       docker-compose down"
echo "  Update:     ./deploy.sh"
