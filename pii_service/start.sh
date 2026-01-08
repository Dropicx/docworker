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
DE_MODEL_VERSION="3.8.0"
EN_MODEL_VERSION="3.8.0"

echo "=== SpaCy PII Service Startup ==="
echo "Models directory: $MODELS_DIR"

# Create models directory if it doesn't exist
mkdir -p "$MODELS_DIR" 2>/dev/null || true

# Debug: show what's already in the volume
echo "Current contents of $MODELS_DIR:"
ls -la "$MODELS_DIR" 2>/dev/null || echo "(empty or not accessible)"

# Add models directory to Python path so spacy can find them
export PYTHONPATH="$MODELS_DIR:$PYTHONPATH"

# Function to check if model exists in volume
model_exists_in_volume() {
    local model=$1
    local version=$2
    local model_dir="$MODELS_DIR/$model"
    local versioned_dir="$model_dir/${model}-${version}"

    # Check for versioned subdir with config.cfg (pip --target structure)
    if [ -d "$model_dir" ] && [ -f "$model_dir/__init__.py" ] && [ -f "$versioned_dir/config.cfg" ]; then
        echo "Found $model in volume at $model_dir"
        return 0
    fi
    return 1
}

# Function to set up pip environment for downloads (only called when needed)
setup_pip_for_download() {
    # Try to use models directory for pip temp files (avoids "no space" errors with tmpfs on Hetzner)
    # Fall back to /tmp if volume is not writable (Railway with root-owned volume)
    if mkdir -p "$MODELS_DIR/.pip_cache" 2>/dev/null; then
        export TMPDIR="$MODELS_DIR"
        export PIP_CACHE_DIR="$MODELS_DIR/.pip_cache"
        echo "Pip configured: using volume for temp files"
    else
        # Railway: volume is root-owned, use /tmp instead (has enough space for pip)
        export TMPDIR="/tmp"
        export PIP_CACHE_DIR="/tmp/.pip_cache"
        mkdir -p "$PIP_CACHE_DIR"
        echo "Pip configured: using /tmp for temp files (volume not writable)"
    fi
}

# Function to download model to volume
download_model_to_volume() {
    local model=$1
    local version=$2
    echo "Downloading $model to volume..."
    pip install "https://github.com/explosion/spacy-models/releases/download/${model}-${version}/${model}-${version}-py3-none-any.whl" \
        --target="$MODELS_DIR" \
        --no-deps \
        --upgrade
    echo "$model installed to volume successfully"
}

# Check which models need downloading
NEED_DE=false
NEED_EN=false

if model_exists_in_volume "$DE_MODEL" "$DE_MODEL_VERSION"; then
    echo "German model ($DE_MODEL) found - skipping download"
else
    echo "German model ($DE_MODEL) not found - will download"
    NEED_DE=true
fi

if model_exists_in_volume "$EN_MODEL" "$EN_MODEL_VERSION"; then
    echo "English model ($EN_MODEL) found - skipping download"
else
    echo "English model ($EN_MODEL) not found - will download"
    NEED_EN=true
fi

# Only set up pip environment if we need to download
if [ "$NEED_DE" = true ] || [ "$NEED_EN" = true ]; then
    # Check if we can write to the models directory
    if ! touch "$MODELS_DIR/.write_test" 2>/dev/null; then
        echo "ERROR: Cannot write to $MODELS_DIR"
        echo "Models need to be downloaded but volume is not writable."
        echo "This usually happens on Railway with a fresh volume."
        echo "Solution: Ensure the volume is writable or pre-populate with models."
        exit 1
    fi
    rm -f "$MODELS_DIR/.write_test"

    setup_pip_for_download

    if [ "$NEED_DE" = true ]; then
        download_model_to_volume "$DE_MODEL" "$DE_MODEL_VERSION"
    fi

    if [ "$NEED_EN" = true ]; then
        download_model_to_volume "$EN_MODEL" "$EN_MODEL_VERSION"
    fi

    echo "Contents of $MODELS_DIR after downloads:"
    ls -la "$MODELS_DIR" | head -20
fi

echo "=== All models ready, starting service ==="

# Start the FastAPI application
# HOST_BIND: default 0.0.0.0 (IPv4 for Hetzner), set to :: for IPv6 dual-stack (Railway)
PORT="${PORT:-9125}"
HOST="${HOST_BIND:-0.0.0.0}"

echo "Starting uvicorn on $HOST:$PORT"
exec python -m uvicorn app.main:app --host "$HOST" --port "$PORT" --workers 1
