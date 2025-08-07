#!/bin/sh

# Ollama CPU Instance - Preprocessing
# This instance runs gpt-oss:20b on CPU for preprocessing

echo "🚀 Starting Ollama CPU service (preprocessing)..."

# Force CPU-only mode
export CUDA_VISIBLE_DEVICES=""
export OLLAMA_NUM_GPU=0

# Start Ollama service in the background
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama CPU service to be ready..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if ollama list >/dev/null 2>&1; then
        echo "✅ Ollama CPU service is ready!"
        break
    fi
    echo "⏳ Waiting for Ollama... (attempt $((retry_count + 1))/$max_retries)"
    sleep 2
    retry_count=$((retry_count + 1))
done

if [ $retry_count -eq $max_retries ]; then
    echo "❌ Ollama CPU service failed to start after $max_retries attempts"
    exit 1
fi

echo "🔍 Setting up CPU models for preprocessing..."

# Same model but for CPU preprocessing
MODEL="gpt-oss:20b"
if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
    echo "📥 Pulling preprocessing model: $MODEL (CPU-only)"
    # Pull with CPU-only configuration
    OLLAMA_NUM_GPU=0 ollama pull "$MODEL"
    if [ $? -eq 0 ]; then
        echo "✅ Successfully pulled: $MODEL (configured for CPU)"
    else
        echo "❌ CRITICAL: Failed to pull preprocessing model $MODEL"
        exit 1
    fi
else
    echo "✅ Preprocessing model already exists: $MODEL"
    # Ensure it's loaded with CPU configuration
    echo "🔄 Loading $MODEL with CPU-only configuration..."
    OLLAMA_NUM_GPU=0 ollama run $MODEL "test" 2>/dev/null
fi

# List available models
echo ""
echo "📋 CPU Instance Models:"
ollama list

echo ""
echo "🎯 Ollama CPU Instance Ready!"
echo "   Preprocessing model: gpt-oss:20b (CPU/RAM)"
echo "   Listening on port 11434"
echo "   External port: 7870"

# Keep service running
wait $OLLAMA_PID