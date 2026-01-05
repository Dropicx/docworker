# ==========================================
# PaddleOCR Microservice v2.0 Dockerfile
# PP-StructureV3 with Markdown/JSON output
# Optimized for Railway CPU deployment
# ==========================================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PaddleOCR 3.x and PP-StructureV3
# Combined into single layer to reduce image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1 \
    curl \
    poppler-utils \
    libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Create non-root user early (before copying code)
RUN useradd -m -u 1000 appuser

# Copy application code
COPY app/ app/

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh

# Set permissions
RUN chmod +x /entrypoint.sh \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check with extended start period for PP-StructureV3 model loading
HEALTHCHECK --interval=30s --timeout=30s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:9123/health || exit 1

# Expose port
EXPOSE 9123

# Environment variables
# PADDLEX_HOME points to the Railway volume mount for persistent model storage
# This prevents re-downloading ~2GB of models on every container restart
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    PIP_NO_CACHE_DIR=1 \
    PADDLEOCR_DEFAULT_MODE=structured \
    PADDLEX_HOME=/home/appuser/.paddlex \
    HF_HOME=/home/appuser/.paddlex/huggingface \
    DISABLE_MODEL_SOURCE_CHECK=True

# Run the application via entrypoint (fixes permissions, checks model cache)
# PP-StructureV3 models cached on volume after first startup
USER root
ENTRYPOINT ["/entrypoint.sh"]
