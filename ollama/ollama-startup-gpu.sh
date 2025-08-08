#!/bin/sh

# Ollama GPU Instance - All Local Processing
# This instance handles:
# - Preprocessing with gpt-oss:20b
# - Language translation with gemma3-translator:4b
# All models run on GPU for maximum performance

echo "🚀 Starting Ollama GPU service..."

# Start Ollama service in the background
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama GPU service to be ready..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if ollama list >/dev/null 2>&1; then
        echo "✅ Ollama GPU service is ready!"
        break
    fi
    echo "⏳ Waiting for Ollama... (attempt $((retry_count + 1))/$max_retries)"
    sleep 2
    retry_count=$((retry_count + 1))
done

if [ $retry_count -eq $max_retries ]; then
    echo "❌ Ollama GPU service failed to start after $max_retries attempts"
    exit 1
fi

echo "🔍 Setting up GPU models..."

# Primary model for preprocessing and fallback main processing - USES GPU
MODEL="gpt-oss:20b"
if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
    echo "📥 Pulling primary GPU model: $MODEL"
    if ollama pull "$MODEL"; then
        echo "✅ Successfully pulled: $MODEL (GPU)"
    else
        echo "❌ CRITICAL: Failed to pull mandatory model $MODEL"
        exit 1
    fi
else
    echo "✅ Primary GPU model already exists: $MODEL"
fi

# Gemma3 Translator for language translation (can also run on GPU)
TRANSLATOR_MODEL="zongwei/gemma3-translator:4b"
if ! ollama list 2>/dev/null | grep -q "$TRANSLATOR_MODEL"; then
    echo "📥 Pulling translation model: $TRANSLATOR_MODEL"
    if ollama pull "$TRANSLATOR_MODEL"; then
        echo "✅ Successfully pulled: $TRANSLATOR_MODEL"
    else
        echo "⚠️ Warning: Failed to pull translation model"
    fi
else
    echo "✅ Translation model already exists: $TRANSLATOR_MODEL"
fi

# List available models
echo ""
echo "📋 GPU Instance Models:"
ollama list

echo ""
echo "🎯 Ollama GPU Instance Ready!"
echo "   Preprocessing: gpt-oss:20b (GPU)"
echo "   Translation: zongwei/gemma3-translator:4b (GPU)"
echo "   Main processing: OVH Meta-Llama-3.3-70B (remote)"
echo "   Listening on port 11434"

# Keep service running
wait $OLLAMA_PID