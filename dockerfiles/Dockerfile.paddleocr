# ==========================================
# PaddleOCR Microservice Dockerfile
# Optimized for Railway CPU deployment
# ==========================================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PaddleOCR
RUN apt-get update && apt-get install -y \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download PaddleOCR models at build time (faster startup)
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)" || true

# Copy application code
COPY app/ app/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:9123/health || exit 1

# Expose port
EXPOSE 9123

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9123"]
