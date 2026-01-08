#!/bin/bash
# =============================================================================
# SpaCy PII Service Startup Script
# =============================================================================
# Downloads SpaCy models to volume if not present, then starts the service.
# Models are persisted in /data/models (Railway volume mount point).
#
# FIX: Use pip install with --target to store models on volume, not site-packages
# =============================================================================

set -e

MODELS_DIR="${SPACY_DATA_DIR:-/data/models}"
DE_MODEL="de_core_news_lg"
EN_MODEL="en_core_web_lg"
DE_MODEL_VERSION="3.8.0"
EN_MODEL_VERSION="3.8.0"

echo "=== SpaCy PII Service Startup ==="
echo "Models directory: $MODELS_DIR"

# Create models directory if it doesn't exist
mkdir -p "$MODELS_DIR"

# Add models directory to Python path so spacy can find them
export PYTHONPATH="$MODELS_DIR:$PYTHONPATH"

# Function to check if model exists in volume
model_exists_in_volume() {
    local model=$1
    # Check if the model directory exists in our volume
    if [ -d "$MODELS_DIR/${model//-/_}" ]; then
        # Verify it's loadable
        python -c "import sys; sys.path.insert(0, '$MODELS_DIR'); import spacy; spacy.load('$MODELS_DIR/${model//-/_}')" 2>/dev/null
        return $?
    fi
    return 1
}

# Function to download model to volume
download_model_to_volume() {
    local model=$1
    local version=$2
    echo "Downloading $model to volume..."
    # Download model wheel and install to volume directory
    pip install "https://github.com/explosion/spacy-models/releases/download/${model}-${version}/${model}-${version}-py3-none-any.whl" \
        --target="$MODELS_DIR" \
        --no-deps \
        --upgrade
    echo "$model installed to volume successfully"
}

# Check and download German model
if model_exists_in_volume "$DE_MODEL"; then
    echo "German model ($DE_MODEL) found in volume - skipping download"
else
    echo "German model not found in volume, downloading..."
    download_model_to_volume "$DE_MODEL" "$DE_MODEL_VERSION"
fi

# Check and download English model
if model_exists_in_volume "$EN_MODEL"; then
    echo "English model ($EN_MODEL) found in volume - skipping download"
else
    echo "English model not found in volume, downloading..."
    download_model_to_volume "$EN_MODEL" "$EN_MODEL_VERSION"
fi

echo "=== All models ready, starting service ==="

# Start the FastAPI application
# Use 0.0.0.0 for IPv4 - Railway's proxy handles external routing
PORT="${PORT:-9125}"

echo "Starting uvicorn on 0.0.0.0:$PORT"
exec python -m uvicorn app.main:app --host "0.0.0.0" --port "$PORT" --workers 1
