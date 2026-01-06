#!/bin/bash
# Vast.ai PP-StructureV3 Entrypoint
# Compatible with Vast.ai serverless deployment
# Runs uvicorn in background, provides MODEL_SERVER_URL for routing

set -e

# ==================== MODEL CACHE SETUP ====================
# Use /workspace for Vast.ai (persistent storage)
MODEL_CACHE="/workspace/paddle_models"

# PaddleX/PaddleOCR model cache locations
export PADDLEX_HOME="$MODEL_CACHE"
export PADDLE_HOME="$MODEL_CACHE"
export PADDLEOCR_HOME="$MODEL_CACHE"

# Override HOME to redirect all dotfile caches to workspace
export HOME="/workspace"

# Standard cache locations
export XDG_CACHE_HOME="/workspace/.cache"
export HF_HOME="$MODEL_CACHE/huggingface"
export HF_HUB_CACHE="$MODEL_CACHE/huggingface/hub"
export HUGGINGFACE_HUB_CACHE="$MODEL_CACHE/huggingface/hub"
export TRANSFORMERS_CACHE="$MODEL_CACHE/transformers"

# Skip model source connectivity check (faster startup)
export DISABLE_MODEL_SOURCE_CHECK="True"
export HF_HUB_OFFLINE="0"

# GPU configuration
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export USE_GPU="true"

# PaddlePaddle flags
export FLAGS_use_cuda="1"
export FLAGS_gpu_memory_limit_mb="20000"

echo "=============================================="
echo "PP-StructureV3 GPU Service - Vast.ai"
echo "=============================================="
echo "Model cache: $PADDLEX_HOME"
echo "CUDA devices: $CUDA_VISIBLE_DEVICES"

# Create all cache directories
mkdir -p "$MODEL_CACHE/official_models" 2>/dev/null || true
mkdir -p "/workspace/.paddlex/official_models" 2>/dev/null || true
mkdir -p "/workspace/.cache" 2>/dev/null || true
ln -sf "$MODEL_CACHE/official_models" "/workspace/.paddlex/official_models" 2>/dev/null || true

# Check for cached models
if [ -d "$MODEL_CACHE/official_models" ]; then
    MODEL_COUNT=$(ls -1 "$MODEL_CACHE/official_models" 2>/dev/null | wc -l || echo "0")
    echo "Found $MODEL_COUNT cached models"
else
    echo "No cached models - will download on first request (~2GB)"
fi

# ==================== VAST.AI SERVERLESS VARIABLES ====================
# Model server runs on 9124 internally, PyWorker exposes 9123 externally
export MODEL_SERVER_URL="${MODEL_SERVER_URL:-http://127.0.0.1:9124}"
export MODEL_HEALTH_ENDPOINT="${MODEL_HEALTH_ENDPOINT:-http://127.0.0.1:9124/health}"
export MODEL_LOG="${MODEL_LOG:-/var/log/portal/ppstructure.log}"

echo "MODEL_SERVER_URL: $MODEL_SERVER_URL"
echo "MODEL_HEALTH_ENDPOINT: $MODEL_HEALTH_ENDPOINT"

# ==================== START SERVICE ====================
echo "Starting PP-StructureV3 service on port 9123..."

# Create log directory
mkdir -p "$(dirname "$MODEL_LOG")" 2>/dev/null || true

# Start uvicorn in background on internal port 9124
# PyWorker will listen on 9123 and proxy to 9124
cd /app
python -W ignore::UserWarning -m uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 9124 \
    --log-level info \
    2>&1 | tee "$MODEL_LOG" &

UVICORN_PID=$!
echo "Uvicorn started with PID: $UVICORN_PID"

# Wait for service to be ready
echo "Waiting for service to be ready..."
for i in $(seq 1 120); do
    if curl -s "$MODEL_HEALTH_ENDPOINT" > /dev/null 2>&1; then
        echo "Service ready after ${i}s"

        # Show health status
        HEALTH=$(curl -s "$MODEL_HEALTH_ENDPOINT")
        echo "Health: $HEALTH"
        break
    fi

    # Check if process is still running
    if ! kill -0 $UVICORN_PID 2>/dev/null; then
        echo "ERROR: Uvicorn process died!"
        cat "$MODEL_LOG" | tail -50
        exit 1
    fi

    echo "Waiting... ($i/120)"
    sleep 1
done

# Check final status
if ! curl -s "$MODEL_HEALTH_ENDPOINT" > /dev/null 2>&1; then
    echo "ERROR: Service failed to start after 120s"
    cat "$MODEL_LOG" | tail -100
    exit 1
fi

echo "=============================================="
echo "PP-StructureV3 Model Server READY"
echo "API: $MODEL_SERVER_URL"
echo "Health: $MODEL_HEALTH_ENDPOINT"
echo "=============================================="

# Debug: Print serverless-related env vars
echo ""
echo "DEBUG: Environment variables check:"
echo "  SERVERLESS='$SERVERLESS'"
echo "  REPORT_ADDR='$REPORT_ADDR'"
echo "  CONTAINER_ID='$CONTAINER_ID'"
echo "  VAST_CONTAINERLABEL='$VAST_CONTAINERLABEL'"
echo ""

# ==================== VAST.AI SERVERLESS PYWORKER ====================
# Check if we're running in Vast.ai Serverless
# Triggers: REPORT_ADDR set, SERVERLESS=true, or CONTAINER_ID set (auto by Vast.ai)
if [ -n "$REPORT_ADDR" ] || [ "$SERVERLESS" = "true" ] || [ -n "$CONTAINER_ID" ]; then
    echo ""
    echo "Vast.ai Serverless mode enabled"

    # Set defaults for required PyWorker environment variables
    # These are normally set by Vast.ai template startup scripts
    # REPORT_ADDR: The autoscaler control server (defaults to https://run.vast.ai)
    # MASTER_TOKEN: Authentication token (defaults to "mtoken" per vast-pyworker)
    # CONTAINER_ID: Auto-set by Vast.ai for all instances
    # WORKER_PORT: The port the model server listens on (needed by vastai-sdk)
    export REPORT_ADDR="${REPORT_ADDR:-https://run.vast.ai}"
    export MASTER_TOKEN="${MASTER_TOKEN:-mtoken}"
    export WORKER_PORT="${WORKER_PORT:-9123}"

    echo "  REPORT_ADDR: $REPORT_ADDR"
    echo "  MASTER_TOKEN: ${MASTER_TOKEN:0:4}****"
    echo "  CONTAINER_ID: ${CONTAINER_ID:-not set (will use fallback)}"
    echo "  WORKER_PORT: $WORKER_PORT"
    echo "  VAST_TCP_PORT_9123: ${VAST_TCP_PORT_9123:-not set}"
    echo "  SERVERLESS: ${SERVERLESS:-not set}"

    # Fallback CONTAINER_ID if not set (use hostname or random)
    if [ -z "$CONTAINER_ID" ]; then
        export CONTAINER_ID="${VAST_CONTAINERLABEL:-$(hostname)}"
        echo "  CONTAINER_ID (fallback): $CONTAINER_ID"
    fi

    echo "Starting PyWorker for autoscaler registration..."

    # Install PyWorker dependencies if needed
    pip install --quiet vastai-sdk aiohttp psutil 2>/dev/null || true

    # Start PyWorker in background
    cd /app
    python pyworker/worker.py 2>&1 &
    PYWORKER_PID=$!
    echo "PyWorker started with PID: $PYWORKER_PID"

    # Wait a moment and check if PyWorker is running
    sleep 5
    if kill -0 $PYWORKER_PID 2>/dev/null; then
        echo "PyWorker running successfully!"
        echo "=============================================="
    else
        echo "WARNING: PyWorker may have failed to start"
        echo "Check logs above for errors"
        echo "=============================================="
    fi
else
    echo ""
    echo "Standalone mode (no REPORT_ADDR or SERVERLESS=true set)"
    echo "PyWorker not started - direct API access only"
    echo "=============================================="
fi

# Keep script running - wait for uvicorn
wait $UVICORN_PID
