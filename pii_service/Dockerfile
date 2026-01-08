# =============================================================================
# SpaCy PII Service Dockerfile (Volume-based Model Storage)
# Build: 2025-01-08-v2 - Medical term protection for LOCATION entities
# =============================================================================
# Models are downloaded on first run and stored in a persistent volume.
# This allows fast cold starts when the service wakes from sleep mode.
#
# Railway Setup:
# 1. Add a volume mounted at /data
# 2. Models are cached in /data/models
# =============================================================================

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SPACY_DATA_DIR=/data/models

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies (includes spacy)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and startup script
COPY app/ ./app/
COPY start.sh .
RUN chmod +x start.sh

# Create data directory for volume mount
RUN mkdir -p /data/models

# Expose port
EXPOSE 9125

# Health check (longer start period for model download on first run)
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:9125/health || exit 1

# Run startup script (downloads models if needed, then starts uvicorn)
CMD ["./start.sh"]
