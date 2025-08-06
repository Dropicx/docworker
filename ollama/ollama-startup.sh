#!/bin/bash

# Ollama Model Pre-loader Script
# This script ensures all required models are available for the doctranslator application

echo "🚀 Starting Ollama model initialization..."

# Array of models required by the application (in priority order)
MODELS=(
    "mistral-nemo:latest"
    "llama3.2:latest"
    "llama3.1"
    "mistral:7b"
    "deepseek-r1:7b"
    "gemma3:27b"
)

# Function to check if a model exists
check_model() {
    local model=$1
    ollama list 2>/dev/null | grep -q "$model"
    return $?
}

# Function to pull a model
pull_model() {
    local model=$1
    echo "📥 Pulling model: $model"
    if ollama pull "$model"; then
        echo "✅ Successfully pulled: $model"
        return 0
    else
        echo "⚠️ Failed to pull: $model"
        return 1
    fi
}

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama service to be ready..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if ollama list &>/dev/null; then
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

# Check and pull models
echo "🔍 Checking required models..."
pulled_count=0
failed_count=0

for model in "${MODELS[@]}"; do
    if check_model "$model"; then
        echo "✅ Model already exists: $model"
    else
        echo "⚠️ Model not found: $model"
        if pull_model "$model"; then
            pulled_count=$((pulled_count + 1))
        else
            failed_count=$((failed_count + 1))
            # Only fail critically for the primary model
            if [ "$model" = "mistral-nemo:latest" ]; then
                echo "❌ Critical: Failed to pull primary model!"
                exit 1
            fi
        fi
    fi
done

# Summary
echo ""
echo "📊 Model initialization complete!"
echo "   - Models checked: ${#MODELS[@]}"
echo "   - Models pulled: $pulled_count"
echo "   - Failed pulls: $failed_count"

# List all available models
echo ""
echo "📋 Available models:"
ollama list

# Keep the container running
echo ""
echo "🎯 Ollama is ready to serve requests!"
echo "   Primary model: mistral-nemo:latest"
echo "   Listening on port 11434"

# Start Ollama server (this will keep the container running)
exec ollama serve