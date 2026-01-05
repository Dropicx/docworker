#!/bin/sh
# PaddleOCR Service Entrypoint
# Fixes volume permissions and starts the service
# Models are cached on persistent volume at /home/appuser/.paddlex

set -e

MODEL_CACHE="/home/appuser/.paddlex"

# Export environment variables for PaddleX model caching
# These MUST be set before Python starts
export PADDLEX_HOME="$MODEL_CACHE"
export HF_HOME="$MODEL_CACHE/huggingface"
export HF_HUB_CACHE="$MODEL_CACHE/huggingface/hub"
export HUGGINGFACE_HUB_CACHE="$MODEL_CACHE/huggingface/hub"
export TRANSFORMERS_CACHE="$MODEL_CACHE/transformers"
export DISABLE_MODEL_SOURCE_CHECK="True"

echo "📁 Model cache: $PADDLEX_HOME"

# Fix permissions on volume mount (Railway mounts volumes as root)
if [ -d "$MODEL_CACHE" ]; then
    echo "🔧 Fixing volume permissions..."
    chown -R appuser:appuser "$MODEL_CACHE"

    # Check if models are already cached
    if [ -d "$MODEL_CACHE/official_models" ]; then
        MODEL_COUNT=$(ls -1 "$MODEL_CACHE/official_models" 2>/dev/null | wc -l)
        echo "📦 Found $MODEL_COUNT cached models in $MODEL_CACHE/official_models"
        ls -la "$MODEL_CACHE/official_models" 2>/dev/null | head -5
    else
        echo "📥 No cached models found - will download on first startup (~1GB for LITE mode)"
        mkdir -p "$MODEL_CACHE/official_models"
        chown -R appuser:appuser "$MODEL_CACHE"
    fi
else
    echo "⚠️ Volume not mounted at $MODEL_CACHE - models will be downloaded each restart"
    mkdir -p "$MODEL_CACHE/official_models"
    chown -R appuser:appuser "$MODEL_CACHE"
fi

# Switch to appuser and run the application
# Use :: for IPv6 (Railway internal networking) - listens on both IPv4 and IPv6
echo "🚀 Starting PaddleOCR service as appuser..."
exec su appuser -c "PADDLEX_HOME=$PADDLEX_HOME HF_HOME=$HF_HOME DISABLE_MODEL_SOURCE_CHECK=True python -W ignore::UserWarning -m uvicorn app.main:app --host :: --port 9123 --log-level info"
