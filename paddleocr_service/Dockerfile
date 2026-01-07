# ==========================================
# PaddleOCR CPU-Only Dockerfile
# Lightweight OCR for Hetzner/CPU deployment
# ==========================================

FROM python:3.11-slim

# Install system dependencies
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

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install PaddlePaddle CPU from official index
RUN pip install --no-cache-dir paddlepaddle -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

# Install other dependencies
RUN pip install --no-cache-dir \
    fastapi==0.115.6 \
    "uvicorn[standard]==0.34.0" \
    Pillow \
    "numpy<2.0" \
    PyMuPDF \
    pydantic \
    python-multipart \
    opencv-python-headless \
    psutil

# Install paddleocr without its paddlepaddle dependency (already installed CPU version)
RUN pip install --no-cache-dir --no-deps paddleocr>=3.0.0 \
    && pip install --no-cache-dir shapely pyclipper lmdb tqdm rapidfuzz

WORKDIR /app

# Copy application code
COPY app/ app/

# Create cache directory
RUN mkdir -p /home/appuser/.paddlex && chmod 777 /home/appuser/.paddlex

# Environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    USE_GPU=false \
    PADDLEX_HOME=/home/appuser/.paddlex \
    DISABLE_MODEL_SOURCE_CHECK=True

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9124/health || exit 1

EXPOSE 9124

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9124"]
