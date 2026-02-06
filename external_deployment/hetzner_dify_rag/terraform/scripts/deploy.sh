#!/bin/bash
set -e

echo "=========================================="
echo "Dify RAG Service Deployment Script"
echo "=========================================="

cd /opt/dify-rag

# 1. Mount volume (if not already mounted by cloud-init)
if ! mountpoint -q /mnt/rag-data; then
    echo "Mounting persistent volume..."
    VOLUME_DEV=$(lsblk -rno NAME,FSTYPE,SIZE | awk '$2 == "ext4" {print "/dev/"$1}' | grep -v sda | head -1)
    if [ -n "$VOLUME_DEV" ]; then
        mount "$VOLUME_DEV" /mnt/rag-data
        echo "Volume mounted at /mnt/rag-data"
    else
        echo "WARNING: Could not find volume device, using local storage"
        mkdir -p /mnt/rag-data
    fi
fi

# Create volume directories
mkdir -p /mnt/rag-data/postgres
mkdir -p /mnt/rag-data/weaviate
mkdir -p /mnt/rag-data/redis
mkdir -p /mnt/rag-data/storage

# Fix storage permissions for Dify API (runs as uid 1001)
chown -R 1001:1001 /mnt/rag-data/storage

# 2. Clone Dify docker repo
if [ ! -d "dify" ]; then
    echo "Cloning Dify repository..."
    git clone https://github.com/langgenius/dify.git dify
else
    echo "Updating Dify repository..."
    cd dify
    git pull origin main
    cd ..
fi

# 3. Copy .env to Dify docker directory
echo "Configuring Dify..."
cp /opt/dify-rag/.env /opt/dify-rag/dify/docker/.env

# 4. Start Docker Compose with override
echo "Starting Dify services..."
cd /opt/dify-rag/dify/docker

docker compose -f docker-compose.yaml -f /opt/dify-rag/docker-compose.override.yml up -d

echo ""
echo "Waiting for Dify to start (this may take 2-3 minutes)..."

for i in $(seq 1 60); do
    # Check API health via docker exec
    if docker exec docker-api-1 curl -sf http://localhost:5001/health > /dev/null 2>&1; then
        echo ""
        echo "Dify is healthy!"
        docker exec docker-api-1 curl -s http://localhost:5001/health | python3 -m json.tool 2>/dev/null || docker exec docker-api-1 curl -s http://localhost:5001/health
        break
    fi
    echo "Waiting... ($i/60)"
    sleep 5
done

# Final check
if ! docker exec docker-api-1 curl -sf http://localhost:5001/health > /dev/null 2>&1; then
    echo "Dify not responding yet. Check logs:"
    echo "  cd /opt/dify-rag/dify/docker && docker compose logs -f"
    exit 1
fi

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo ""
echo "Service managed by systemd:"
echo "  systemctl status dify-rag"
echo "  systemctl restart dify-rag"
echo "  journalctl -u dify-rag -f"
echo ""
echo "Docker commands:"
echo "  View logs:  cd /opt/dify-rag/dify/docker && docker compose logs -f"
echo "  Update:     ./deploy.sh"
echo ""
echo "Next steps:"
echo "  1. Log into https://rag.fra-la.de with init password"
echo "  2. Add Mistral as model provider"
echo "  3. Create Knowledge Base 'AWMF Leitlinien'"
echo "  4. Run bulk PDF upload script"
echo "  5. Create Chat App and get API key"

# Secure log file permissions
chmod 600 /var/log/dify-rag-deploy.log 2>/dev/null || true
