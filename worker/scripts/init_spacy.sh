#!/bin/bash
# ==========================================
# spaCy Model Initialization for Railway Volume
# ==========================================
#
# This script manages spaCy models on Railway persistent volume.
#
# Benefits:
# - Download models once, persist across deployments
# - Faster startup times (no re-download)
# - Reduced deployment time
# - Railway volume provides persistence
#
# Usage:
#   ./init_spacy.sh
#
# Environment Variables:
#   SPACY_MODEL_PATH - Path to spaCy model on volume (default: /data/spacy_models/de_core_news_sm)
#   SKIP_SPACY_INIT  - Set to 'true' to skip initialization (for testing)
#
# ==========================================

set -e  # Exit on error

# Configuration
MODEL_NAME="de_core_news_sm"
VOLUME_PATH="${SPACY_MODEL_PATH:-/data/spacy_models/$MODEL_NAME}"
SKIP_INIT="${SKIP_SPACY_INIT:-false}"

echo "================================================"
echo "🚀 spaCy Model Initialization for Railway"
echo "================================================"

# Skip initialization if requested
if [ "$SKIP_INIT" = "true" ]; then
    echo "⏭️  Skipping spaCy initialization (SKIP_SPACY_INIT=true)"
    exit 0
fi

echo "📋 Configuration:"
echo "   Model: $MODEL_NAME"
echo "   Volume path: $VOLUME_PATH"
echo "   Skip init: $SKIP_INIT"
echo ""

# Check if model already exists on volume
if [ -d "$VOLUME_PATH" ] && [ -f "$VOLUME_PATH/meta.json" ]; then
    echo "✅ spaCy model found on Railway volume"
    echo "   Path: $VOLUME_PATH"

    # Verify model integrity
    if python3 -c "import spacy; spacy.load('$VOLUME_PATH')" 2>/dev/null; then
        echo "✅ Model integrity verified"
        echo "⚡ Using cached model (fast startup)"
    else
        echo "⚠️  Model corrupted, will re-download..."
        rm -rf "$VOLUME_PATH"
    fi
else
    echo "📥 spaCy model not found on volume"
    echo "   Downloading model (this happens only once)..."

    # Create volume directory structure
    echo "📁 Creating directory: $(dirname "$VOLUME_PATH")"
    mkdir -p "$(dirname "$VOLUME_PATH")" || {
        echo "❌ ERROR: Failed to create directory $(dirname "$VOLUME_PATH")"
        echo "   Check volume permissions and mount point"
        echo "   Volume should be mounted at /data with write permissions"
        exit 1
    }

    # Download spaCy model using pip
    echo "🔽 Downloading $MODEL_NAME via spaCy..."
    python3 -m spacy download "$MODEL_NAME" --quiet

    # Find where spaCy installed the model
    SYSTEM_MODEL_PATH=$(python3 -c "import spacy; import spacy.util; print(spacy.util.get_package_path('$MODEL_NAME'))" 2>/dev/null || echo "")

    if [ -z "$SYSTEM_MODEL_PATH" ] || [ ! -d "$SYSTEM_MODEL_PATH" ]; then
        echo "❌ Failed to locate downloaded model"
        echo "   Trying alternative approach..."

        # Alternative: Find model in pip site-packages
        SYSTEM_MODEL_PATH=$(python3 -c "
import site
import os
for sp in site.getsitepackages():
    model_path = os.path.join(sp, '$MODEL_NAME')
    if os.path.exists(model_path):
        print(model_path)
        break
" 2>/dev/null || echo "")
    fi

    if [ -z "$SYSTEM_MODEL_PATH" ] || [ ! -d "$SYSTEM_MODEL_PATH" ]; then
        echo "❌ ERROR: Could not find downloaded spaCy model"
        echo "   Model download may have failed"
        exit 1
    fi

    echo "📦 Found model at: $SYSTEM_MODEL_PATH"
    echo "📋 Copying model to volume: $VOLUME_PATH"

    # Ensure target directory exists
    mkdir -p "$VOLUME_PATH"

    # Copy model contents to volume (not the directory itself)
    cp -r "$SYSTEM_MODEL_PATH/"* "$VOLUME_PATH/"

    # Verify copy was successful
    if [ -f "$VOLUME_PATH/meta.json" ]; then
        echo "✅ Model successfully installed to Railway volume"

        # Test loading the model
        if python3 -c "import spacy; spacy.load('$VOLUME_PATH')" 2>/dev/null; then
            echo "✅ Model verified and ready to use"
        else
            echo "⚠️  Warning: Model verification failed, but will attempt to use it"
        fi
    else
        echo "❌ ERROR: Model copy failed"
        exit 1
    fi
fi

# Display model information
echo ""
echo "================================================"
echo "📊 Model Information:"
python3 -c "
import spacy
try:
    nlp = spacy.load('$VOLUME_PATH')
    meta = nlp.meta
    print(f'   Name: {meta.get(\"name\", \"unknown\")}')
    print(f'   Version: {meta.get(\"version\", \"unknown\")}')
    print(f'   Language: {meta.get(\"lang\", \"unknown\")}')
    print(f'   Pipeline: {meta.get(\"pipeline\", [])}')
    print(f'   Size: ~15MB')
except Exception as e:
    print(f'   ⚠️  Could not load model info: {e}')
" 2>/dev/null || echo "   ℹ️  Model info not available"

echo "================================================"
echo "✅ spaCy initialization complete"
echo "🟢 Worker ready to start"
echo "================================================"
echo ""
