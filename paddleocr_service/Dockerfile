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
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    PIP_NO_CACHE_DIR=1 \
    PADDLEOCR_DEFAULT_MODE=structured

# Run the application
# PP-StructureV3 models downloaded on first startup (~1-2 min)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9123"]
