#!/bin/sh

# Ollama Model Pre-loader Script
# This script ensures all required models are available for the doctranslator application

echo "🚀 Starting Ollama service with model pre-loading..."

# Start Ollama service in the background
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama service to be ready..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if ollama list >/dev/null 2>&1; then
        echo "✅ Ollama service is ready!"
        break
    fi
    echo "⏳ Waiting for Ollama... (attempt $((retry_count + 1))/$max_retries)"
    sleep 2
    retry_count=$((retry_count + 1))
done

if [ $retry_count -eq $max_retries ]; then
    echo "❌ Ollama service failed to start after $max_retries attempts"
    exit 1
fi

# Array of models required by the application (in priority order)
echo "🔍 Checking required models..."

# Primary model - MANDATORY for document analysis and translation
MODEL="gpt-oss:20b"
if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
    echo "📥 Pulling MANDATORY primary model: $MODEL"
    if ollama pull "$MODEL"; then
        echo "✅ Successfully pulled: $MODEL"
    else
        echo "❌ CRITICAL: Failed to pull mandatory model $MODEL"
        echo "   This model is required for document analysis and translation!"
        echo "   Please ensure the model is available and try again."
        exit 1
    fi
else
    echo "✅ Primary model already exists: $MODEL"
fi

# Gemma3 model for fast preprocessing with German support - IMPORTANT
PREPROCESS_MODEL="gemma3:4b"
if ! ollama list 2>/dev/null | grep -q "$PREPROCESS_MODEL"; then
    echo "📥 Pulling preprocessing model: $PREPROCESS_MODEL"
    if ollama pull "$PREPROCESS_MODEL"; then
        echo "✅ Successfully pulled: $PREPROCESS_MODEL"
    else
        echo "⚠️ Warning: Failed to pull Gemma3 model for fast preprocessing"
        echo "   Preprocessing will fall back to primary model (slower)."
    fi
else
    echo "✅ Preprocessing model already exists: $PREPROCESS_MODEL"
fi

# Gemma3 Translator model for language translation - IMPORTANT
TRANSLATOR_MODEL="zongwei/gemma3-translator:4b"
if ! ollama list 2>/dev/null | grep -q "$TRANSLATOR_MODEL"; then
    echo "📥 Pulling translation model: $TRANSLATOR_MODEL"
    if ollama pull "$TRANSLATOR_MODEL"; then
        echo "✅ Successfully pulled: $TRANSLATOR_MODEL"
    else
        echo "⚠️ Warning: Failed to pull Gemma3 Translator model"
        echo "   Language translation features may be limited."
    fi
else
    echo "✅ Translation model already exists: $TRANSLATOR_MODEL"
fi

# Secondary/fallback models - optional
for MODEL in "mistral-nemo:latest" "llama3.1" "mistral:7b"; do
    if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
        echo "📥 Pulling secondary model: $MODEL"
        ollama pull "$MODEL" || echo "⚠️ Failed to pull: $MODEL (optional)"
    else
        echo "✅ Model already exists: $MODEL"
    fi
done

# List all available models
echo ""
echo "📋 Available models:"
ollama list

echo ""
echo "🎯 Ollama is ready to serve requests!"
echo "   Primary model (MANDATORY): gpt-oss:20b"
echo "   Preprocessing model: gemma3:4b (fast, German support)"
echo "   Translation model: zongwei/gemma3-translator:4b"
echo "   Secondary models: mistral-nemo:latest, llama3.1, etc."
echo "   Listening on port 11434"

# Keep the Ollama service running in foreground
wait $OLLAMA_PID