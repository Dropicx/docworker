#!/bin/bash
# Deploy AWMF Weekly Sync to Dify Server (Hetzner)
#
# This script deploys the AWMF sync cron job to the Hetzner VM
# running the Dify RAG service.
#
# Prerequisites:
# - SSH access to the server (root@168.119.244.16)
# - Server has Python 3.10+ installed
#
# Usage:
#   bash scripts/deploy_awmf_sync.sh
#
# After deployment, create /opt/awmf-sync/.env on the server with:
#   DIFY_URL=https://rag.fra-la.de
#   DIFY_DATASET_API_KEY=dataset-Rsit9KtpNE3zSputUXBIZdcv
#   DIFY_DATASET_ID=94f86ec6-4037-458a-b520-1600b4805001
#   S3_ENDPOINT=https://fsn1.your-objectstorage.com
#   S3_ACCESS_KEY=your-access-key
#   S3_SECRET_KEY=your-secret-key
#   S3_BUCKET=awmf-guidelines

set -e

SERVER="root@168.119.244.16"
REMOTE_DIR="/opt/awmf-sync"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "AWMF Weekly Sync - Deployment Script"
echo "=========================================="
echo "Server: $SERVER"
echo "Remote Dir: $REMOTE_DIR"
echo ""

# Check SSH connectivity
echo "[1/6] Testing SSH connection..."
if ! ssh -o ConnectTimeout=10 $SERVER "echo 'SSH OK'" > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to $SERVER"
    echo "Ensure you have SSH access configured."
    exit 1
fi
echo "  ✓ SSH connection OK"

# Create remote directory
echo "[2/6] Creating remote directory..."
ssh $SERVER "mkdir -p $REMOTE_DIR"
echo "  ✓ Directory created"

# Copy Python files
echo "[3/6] Copying sync scripts..."
scp "$SCRIPT_DIR/awmf_weekly_sync.py" "$SERVER:$REMOTE_DIR/"
scp "$SCRIPT_DIR/awmf_document.py" "$SERVER:$REMOTE_DIR/"
scp "$PROJECT_ROOT/rag/awmf_crawler.py" "$SERVER:$REMOTE_DIR/"

# Create scripts module for imports
ssh $SERVER "mkdir -p $REMOTE_DIR/scripts && ln -sf ../awmf_document.py $REMOTE_DIR/scripts/awmf_document.py 2>/dev/null || true"
ssh $SERVER "mkdir -p $REMOTE_DIR/rag && ln -sf ../awmf_crawler.py $REMOTE_DIR/rag/awmf_crawler.py 2>/dev/null || true"

echo "  ✓ Scripts copied"

# Install Python dependencies
echo "[4/6] Installing Python dependencies..."
ssh $SERVER "pip3 install --quiet boto3 httpx playwright aiohttp 2>/dev/null || pip install --quiet boto3 httpx playwright aiohttp"
ssh $SERVER "python3 -m playwright install chromium 2>/dev/null || echo 'Playwright already installed'"
echo "  ✓ Dependencies installed"

# Copy and enable systemd units
echo "[5/6] Installing systemd units..."
scp "$SCRIPT_DIR/awmf-sync.service" "$SERVER:/etc/systemd/system/"
scp "$SCRIPT_DIR/awmf-sync.timer" "$SERVER:/etc/systemd/system/"
ssh $SERVER "systemctl daemon-reload"
ssh $SERVER "systemctl enable awmf-sync.timer"
ssh $SERVER "systemctl start awmf-sync.timer"
echo "  ✓ Systemd timer enabled"

# Check timer status
echo "[6/6] Verifying deployment..."
ssh $SERVER "systemctl list-timers awmf-sync.timer --no-pager"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. Create the environment file on the server:"
echo "   ssh $SERVER 'cat > $REMOTE_DIR/.env << EOF"
echo "DIFY_URL=https://rag.fra-la.de"
echo "DIFY_DATASET_API_KEY=dataset-Rsit9KtpNE3zSputUXBIZdcv"
echo "DIFY_DATASET_ID=94f86ec6-4037-458a-b520-1600b4805001"
echo "S3_ENDPOINT=https://fsn1.your-objectstorage.com"
echo "S3_ACCESS_KEY=your-access-key"
echo "S3_SECRET_KEY=your-secret-key"
echo "S3_BUCKET=awmf-guidelines"
echo "EOF'"
echo ""
echo "2. Test with a dry run:"
echo "   ssh $SERVER 'cd $REMOTE_DIR && source .env && python3 awmf_weekly_sync.py --dry-run'"
echo ""
echo "3. Run a manual sync:"
echo "   ssh $SERVER 'systemctl start awmf-sync.service'"
echo ""
echo "4. Watch logs:"
echo "   ssh $SERVER 'tail -f /var/log/awmf-sync.log'"
echo ""
echo "5. Check timer schedule:"
echo "   ssh $SERVER 'systemctl list-timers awmf-sync.timer'"
