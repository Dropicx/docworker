# ==========================================
# PaddleOCR Microservice Dockerfile
# Optimized for Railway CPU deployment
# ==========================================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PaddleOCR
# Combined into single layer to reduce image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1 \
    curl \
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

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9123/health || exit 1

# Expose port
EXPOSE 9123

# Environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    PIP_NO_CACHE_DIR=1

# Run the application
# Models will be downloaded on first startup (faster build, slower first request)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9123"]
