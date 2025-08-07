#!/bin/sh

# DEPRECATED - This file is no longer used
# The project now uses a dual-instance setup with:
# - ollama-startup-gpu.sh for GPU processing
# - ollama-startup-cpu.sh for CPU preprocessing
#
# Please use docker-compose with ollama-gpu and ollama-cpu services instead.

echo "⚠️ WARNING: This startup script is deprecated!"
echo "📌 Please use the dual-instance setup:"
echo "   - ollama-gpu: GPU instance for main processing"
echo "   - ollama-cpu: CPU instance for preprocessing"
echo ""
echo "See docker-compose.yml for the new configuration."
exit 1