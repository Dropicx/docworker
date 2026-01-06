#!/bin/bash
# =============================================================================
# PP-StructureV3 OCR Server - Vast.ai Setup Script
# =============================================================================
# Run this script on your vast.ai instance to set up the OCR service.
# Usage: ./setup.sh [DOCKER_IMAGE]
# =============================================================================

set -e

# Configuration
DOCKER_IMAGE="${1:-ppstructure:gpu}"
CONTAINER_NAME="ppstructure"
PORT=9124
ENV_FILE="/workspace/.env"
API_KEY_FILE="/workspace/API_KEY.txt"

echo "=========================================="
echo "PP-StructureV3 OCR Server Setup"
echo "=========================================="
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if NVIDIA GPU is available
if ! nvidia-smi &> /dev/null; then
    echo "Warning: NVIDIA GPU not detected. Service will run but may be slow."
fi

# Generate API key if not exists
if [ -f "$API_KEY_FILE" ]; then
    API_KEY=$(cat "$API_KEY_FILE" | tr -d '[:space:]')
    echo "Using existing API key from $API_KEY_FILE"
else
    API_KEY=$(tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 64)
    echo "$API_KEY" > "$API_KEY_FILE"
    chmod 600 "$API_KEY_FILE"
    echo "Generated new API key"
fi

# Create .env file
cat > "$ENV_FILE" << EOF
API_SECRET_KEY=${API_KEY}
USE_GPU=true
PYTHONUNBUFFERED=1
PADDLEOCR_DEFAULT_MODE=structured
EOF
chmod 600 "$ENV_FILE"
echo "Created environment file at $ENV_FILE"

# Stop existing container if running
if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
    echo "Stopping existing container..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

# Pull latest image
echo ""
echo "Pulling Docker image: $DOCKER_IMAGE"
docker pull "$DOCKER_IMAGE" || echo "Using local image"

# Run container with GPU support
echo ""
echo "Starting container with GPU support..."
docker run -d \
    --name $CONTAINER_NAME \
    --gpus all \
    -p ${PORT}:${PORT} \
    --env-file "$ENV_FILE" \
    -v paddle_models:/home/appuser/.paddlex \
    --restart unless-stopped \
    "$DOCKER_IMAGE"

# Wait for service to be healthy
echo ""
echo "Waiting for PP-StructureV3 to start..."
echo "(First startup downloads ~1-2GB of models, please be patient)"
echo ""

for i in {1..60}; do
    if curl -sf "http://localhost:${PORT}/health" > /dev/null 2>&1; then
        echo ""
        echo "Service is healthy!"
        break
    fi
    echo "  Waiting... ($i/60)"
    sleep 10
done

# Check final status
if ! curl -sf "http://localhost:${PORT}/health" > /dev/null 2>&1; then
    echo ""
    echo "Warning: Service not responding yet."
    echo "Check logs: docker logs -f $CONTAINER_NAME"
    exit 1
fi

# Get public IP
PUBLIC_IP=$(curl -sf ifconfig.me 2>/dev/null || curl -sf icanhazip.com 2>/dev/null || echo "<your-ip>")

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Service URL: http://${PUBLIC_IP}:${PORT}"
echo "Health URL:  http://${PUBLIC_IP}:${PORT}/health"
echo ""
echo "API Key: ${API_KEY}"
echo ""
echo "Add these to your backend environment:"
echo ""
echo "  EXTERNAL_OCR_URL=http://${PUBLIC_IP}:${PORT}"
echo "  EXTERNAL_API_KEY=${API_KEY}"
echo "  USE_EXTERNAL_OCR=true"
echo ""
echo "Useful commands:"
echo "  View logs:    docker logs -f $CONTAINER_NAME"
echo "  Restart:      docker restart $CONTAINER_NAME"
echo "  Stop:         docker stop $CONTAINER_NAME"
echo "  Update:       docker pull $DOCKER_IMAGE && ./setup.sh $DOCKER_IMAGE"
echo ""
