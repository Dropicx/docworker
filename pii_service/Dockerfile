# =============================================================================
# SpaCy PII Service Dockerfile
# =============================================================================
# CPU-optimized image with large SpaCy models for German and English
#
# Build: docker build -t spacy-pii:cpu .
# Run:   docker run -p 9125:9125 -e API_SECRET_KEY=your-key spacy-pii:cpu
# =============================================================================

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download SpaCy models (large models for maximum accuracy)
# This is done at build time so models are cached in the image
RUN python -m spacy download de_core_news_lg && \
    python -m spacy download en_core_web_lg

# Copy application code
COPY app/ ./app/

# Create models directory (for future model caching if needed)
RUN mkdir -p /app/models && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 9125

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:9125/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9125", "--workers", "1"]
