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

# Primary model - critical
MODEL="mistral-nemo:latest"
if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
    echo "📥 Pulling primary model: $MODEL"
    if ollama pull "$MODEL"; then
        echo "✅ Successfully pulled: $MODEL"
    else
        echo "⚠️ Failed to pull primary model, trying fallback..."
    fi
else
    echo "✅ Primary model already exists: $MODEL"
fi

# Fallback models - optional
for MODEL in "llama3.2:latest" "llama3.1" "mistral:7b"; do
    if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
        echo "📥 Pulling fallback model: $MODEL"
        ollama pull "$MODEL" || echo "⚠️ Failed to pull: $MODEL (non-critical)"
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
echo "   Primary model: mistral-nemo:latest"
echo "   Listening on port 11434"

# Keep the Ollama service running in foreground
wait $OLLAMA_PID