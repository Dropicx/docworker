#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "🔧 Docker Environment Fix Script"
echo "================================================"
echo ""

# Stop only doctranslator project containers
echo "1️⃣  Stopping doctranslator containers..."
docker compose down 2>/dev/null || true
# Only stop containers from this project (with medical-translator prefix or ollama)
docker stop medical-translator-backend medical-translator-frontend ollama 2>/dev/null || true
echo "✅ Doctranslator containers stopped"
echo ""

# Remove only doctranslator project containers and volumes
echo "2️⃣  Cleaning up doctranslator Docker resources..."
# Remove specific containers
docker rm -f ollama medical-translator-backend medical-translator-frontend 2>/dev/null || true
# Remove only volumes from this project
docker volume rm doctranslator_ollama_data 2>/dev/null || true
# Remove only dangling images related to this project
docker images | grep -E "(medical-translator|doctranslator)" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true
echo "✅ Doctranslator cleanup completed"
echo ""

# Create docker-compose.gpu.yml with proper permissions
echo "3️⃣  Creating GPU configuration file..."
cat > docker-compose.gpu.yml << 'EOF'
# GPU-enabled configuration for Ollama
version: '3.8'

services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
EOF

if [ -f docker-compose.gpu.yml ]; then
    echo "✅ GPU configuration file created"
else
    echo "❌ Failed to create GPU configuration file"
fi
echo ""

# Update docker-compose.yml to remove any problematic configurations
echo "4️⃣  Updating docker-compose.yml..."
# Check if we need to update the ollama service configuration
if grep -q "nvidia-container-runtime" docker-compose.yml 2>/dev/null; then
    echo "   Removing old nvidia runtime configuration..."
    sed -i '/runtime: nvidia/d' docker-compose.yml
    sed -i '/nvidia-container-runtime/d' docker-compose.yml
fi
echo "✅ docker-compose.yml updated"
echo ""

# Rebuild images to ensure clean state
echo "5️⃣  Rebuilding Docker images..."
echo "   This may take a few minutes..."
docker compose build --no-cache
echo "✅ Images rebuilt"
echo ""

# Start services with GPU support
echo "6️⃣  Starting services..."
if [ -f docker-compose.gpu.yml ]; then
    echo "   Starting with GPU support..."
    docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
else
    echo "   Starting without GPU override..."
    docker compose up -d
fi
echo ""

# Wait for services to be ready
echo "7️⃣  Waiting for services to be ready..."
sleep 10

# Check service status
echo "8️⃣  Checking service status..."
docker compose ps
echo ""

# Test Ollama
echo "9️⃣  Testing Ollama service..."
if docker exec ollama ollama list 2>/dev/null; then
    echo "✅ Ollama is running"
else
    echo "⚠️  Ollama might still be starting up..."
fi
echo ""

# Test backend
echo "🔟  Testing backend service..."
if curl -s http://localhost:9122/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "⚠️  Backend is not responding yet"
fi
echo ""

# Test frontend
echo "1️⃣1️⃣  Testing frontend service..."
if curl -s http://localhost:9121 > /dev/null 2>&1; then
    echo "✅ Frontend is accessible"
else
    echo "⚠️  Frontend is not responding yet"
fi
echo ""

echo "================================================"
echo "✨ Docker environment fix complete!"
echo "================================================"
echo ""
echo "Services should now be running at:"
echo "  - Frontend: http://localhost:9121"
echo "  - Backend:  http://localhost:9122"
echo "  - Ollama:   http://localhost:11434"
echo ""
echo "To check logs, run:"
echo "  docker compose logs -f [service-name]"
echo ""
echo "If services are still starting, wait a minute and run:"
echo "  docker compose ps"