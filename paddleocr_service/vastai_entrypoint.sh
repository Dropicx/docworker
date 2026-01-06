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
# These are picked up by Vast.ai's routing layer
export MODEL_SERVER_URL="${MODEL_SERVER_URL:-http://127.0.0.1:9123}"
export MODEL_HEALTH_ENDPOINT="${MODEL_HEALTH_ENDPOINT:-http://127.0.0.1:9123/health}"
export MODEL_LOG="${MODEL_LOG:-/var/log/portal/ppstructure.log}"

echo "MODEL_SERVER_URL: $MODEL_SERVER_URL"
echo "MODEL_HEALTH_ENDPOINT: $MODEL_HEALTH_ENDPOINT"

# ==================== START SERVICE ====================
echo "Starting PP-StructureV3 service on port 9123..."

# Create log directory
mkdir -p "$(dirname "$MODEL_LOG")" 2>/dev/null || true

# Start uvicorn in background (0.0.0.0 for external access)
cd /app
python -W ignore::UserWarning -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 9123 \
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

# ==================== VAST.AI SERVERLESS ====================
# For Vast.ai Serverless: PyWorker is started by Vast.ai's system via PYWORKER_REPO
# This entrypoint only starts the model server
# Set PYWORKER_REPO=https://github.com/Dropicx/doctranslator
# Set PYWORKER_PATH=paddleocr_service/pyworker

echo ""
echo "Model server running. For Vast.ai Serverless, set PYWORKER_REPO."
echo "=============================================="

# Keep script running
wait $UVICORN_PID
