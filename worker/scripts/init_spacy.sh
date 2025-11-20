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
#   SPACY_MODEL_PATH - Path to spaCy model on volume (default: /data/spacy_models/de_core_news_md)
#   SKIP_SPACY_INIT  - Set to 'true' to skip initialization (for testing)
#
# ==========================================

set -e  # Exit on error

# Configuration
# UPGRADE: Changed from de_core_news_sm to de_core_news_md for +15% accuracy (Issue #35)
# Model sizes: sm=15MB, md=43MB, lg=542MB
MODEL_NAME="de_core_news_md"
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
MODEL_NEEDS_DOWNLOAD=false

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
        MODEL_NEEDS_DOWNLOAD=true
    fi
else
    echo "📥 spaCy model not found on volume"
    echo "   Downloading model (this happens only once)..."
    MODEL_NEEDS_DOWNLOAD=true
fi

if [ "$MODEL_NEEDS_DOWNLOAD" = "true" ]; then

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

    # spaCy models have a versioned subdirectory (e.g., de_core_news_sm-3.8.0)
    # We need to find this subdirectory and copy its contents to the root of VOLUME_PATH
    VERSIONED_SUBDIR=$(find "$SYSTEM_MODEL_PATH" -maxdepth 1 -type d -name "${MODEL_NAME}-*" | head -1)

    if [ -n "$VERSIONED_SUBDIR" ]; then
        echo "📦 Found versioned model directory: $VERSIONED_SUBDIR"
        echo "📋 Copying model contents to volume: $VOLUME_PATH"

        # Ensure target directory exists
        mkdir -p "$VOLUME_PATH"

        # Copy versioned model contents directly to volume root
        echo "🔄 Copying files..."
        cp -rv "$VERSIONED_SUBDIR/"* "$VOLUME_PATH/" 2>&1 | head -20
    else
        echo "⚠️  No versioned subdirectory found, copying all contents..."
        echo "📋 Copying model to volume: $VOLUME_PATH"

        # Ensure target directory exists
        mkdir -p "$VOLUME_PATH"

        # Copy model contents to volume with verbose output
        echo "🔄 Copying files..."
        cp -rv "$SYSTEM_MODEL_PATH/"* "$VOLUME_PATH/" 2>&1 | head -20
    fi

    # Set proper permissions on copied files
    echo "🔐 Setting permissions..."
    chmod -R 755 "$VOLUME_PATH"

    # List what was copied for debugging
    echo "📂 Files in volume:"
    ls -la "$VOLUME_PATH" | head -10

    # Verify critical files exist
    CRITICAL_FILES=("meta.json" "config.cfg" "vocab" "ner")
    MISSING_FILES=()

    for file in "${CRITICAL_FILES[@]}"; do
        if [ ! -e "$VOLUME_PATH/$file" ]; then
            MISSING_FILES+=("$file")
        fi
    done

    if [ ${#MISSING_FILES[@]} -gt 0 ]; then
        echo "❌ ERROR: Missing critical files: ${MISSING_FILES[*]}"
        echo "   Copy may have failed. Volume contents:"
        ls -la "$VOLUME_PATH"
        exit 1
    fi

    echo "✅ Model successfully installed to Railway volume"

    # Test loading the model with error details
    if python3 -c "import spacy; spacy.load('$VOLUME_PATH')" 2>&1; then
        echo "✅ Model verified and ready to use"
    else
        echo "⚠️  Warning: Model verification failed"
        echo "   Trying to get more details..."
        python3 -c "import spacy; print(spacy.load('$VOLUME_PATH'))" 2>&1 || true
    fi
fi  # End of MODEL_NEEDS_DOWNLOAD block

# Display model information only if model exists
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
    print(f'   Size: ~43MB (md model for enhanced accuracy)')
except Exception as e:
    print(f'   ⚠️  Could not load model info: {e}')
" 2>/dev/null || echo "   ℹ️  Model info not available"

echo "================================================"
echo "✅ spaCy initialization complete"
echo "🟢 Worker ready to start"
echo "================================================"
echo ""
