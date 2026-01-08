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

# Debug: show what's already in the volume
echo "Current contents of $MODELS_DIR:"
ls -la "$MODELS_DIR" 2>/dev/null || echo "(empty or not accessible)"

# Add models directory to Python path so spacy can find them
export PYTHONPATH="$MODELS_DIR:$PYTHONPATH"

# Use models directory for pip temp files (avoids "no space" errors with tmpfs)
# Note: mkdir may fail on Railway if volume is root-owned but models already exist - that's OK
export TMPDIR="$MODELS_DIR"
export PIP_CACHE_DIR="$MODELS_DIR/.pip_cache"
mkdir -p "$PIP_CACHE_DIR" 2>/dev/null || true

# Function to check if model exists in volume
model_exists_in_volume() {
    local model=$1
    local version=$2
    local model_dir="$MODELS_DIR/$model"

    # SpaCy models installed with pip --target create this structure:
    # /data/models/de_core_news_lg/
    #   ├── __init__.py
    #   ├── de_core_news_lg-3.8.0/   ← config.cfg is in versioned subdir
    #   └── meta.json
    #
    # Check for __init__.py (package marker) AND versioned subdir with config.cfg
    local versioned_dir="$model_dir/${model}-${version}"

    if [ -d "$model_dir" ] && [ -f "$model_dir/__init__.py" ]; then
        if [ -f "$versioned_dir/config.cfg" ]; then
            echo "Found $model in volume at $model_dir (config in $versioned_dir)"
            return 0
        else
            echo "WARNING: Package exists but missing config.cfg in $versioned_dir"
            ls -la "$model_dir" 2>/dev/null || true
        fi
    fi

    echo "Model $model not found in volume (checked $model_dir)"
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

    # Debug: show what was created
    echo "Contents of $MODELS_DIR after install:"
    ls -la "$MODELS_DIR" | head -20
}

# Check and download German model
if model_exists_in_volume "$DE_MODEL" "$DE_MODEL_VERSION"; then
    echo "German model ($DE_MODEL) found in volume - skipping download"
else
    echo "German model not found in volume, downloading..."
    download_model_to_volume "$DE_MODEL" "$DE_MODEL_VERSION"
fi

# Check and download English model
if model_exists_in_volume "$EN_MODEL" "$EN_MODEL_VERSION"; then
    echo "English model ($EN_MODEL) found in volume - skipping download"
else
    echo "English model not found in volume, downloading..."
    download_model_to_volume "$EN_MODEL" "$EN_MODEL_VERSION"
fi

echo "=== All models ready, starting service ==="

# Start the FastAPI application
# HOST_BIND: default 0.0.0.0 (IPv4 for Hetzner), set to :: for IPv6 dual-stack (Railway)
PORT="${PORT:-9125}"
HOST="${HOST_BIND:-0.0.0.0}"

echo "Starting uvicorn on $HOST:$PORT"
exec python -m uvicorn app.main:app --host "$HOST" --port "$PORT" --workers 1
