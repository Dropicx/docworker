#!/bin/bash
# =============================================================================
# SpaCy PII Service Startup Script
# =============================================================================
# Downloads SpaCy models to volume if not present, then starts the service.
# Models are persisted in /data/models (Railway volume mount point).
# =============================================================================

set -e

MODELS_DIR="${SPACY_DATA_DIR:-/data/models}"
DE_MODEL="de_core_news_lg"
EN_MODEL="en_core_web_lg"

echo "=== SpaCy PII Service Startup ==="
echo "Models directory: $MODELS_DIR"

# Create models directory if it doesn't exist
mkdir -p "$MODELS_DIR"

# Function to check if model exists
model_exists() {
    python -c "import spacy; spacy.load('$1')" 2>/dev/null
    return $?
}

# Function to download model to volume
download_model() {
    local model=$1
    echo "Downloading $model..."
    python -m spacy download "$model"
    echo "$model downloaded successfully"
}

# Check and download German model
if model_exists "$DE_MODEL"; then
    echo "German model ($DE_MODEL) already available"
else
    echo "German model not found, downloading..."
    download_model "$DE_MODEL"
fi

# Check and download English model
if model_exists "$EN_MODEL"; then
    echo "English model ($EN_MODEL) already available"
else
    echo "English model not found, downloading..."
    download_model "$EN_MODEL"
fi

echo "=== All models ready, starting service ==="

# Start the FastAPI application
# HOST_BIND: Use "::" for IPv6 (Railway internal networking) or "0.0.0.0" for IPv4 (Hetzner load balancers)
HOST_BIND="${HOST_BIND:-0.0.0.0}"
echo "Starting uvicorn on host: $HOST_BIND port: ${PORT:-9125}"
exec python -m uvicorn app.main:app --host "$HOST_BIND" --port "${PORT:-9125}" --workers 1
