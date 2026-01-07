# ==========================================
# PaddleOCR Fast - Lightweight OCR Dockerfile
# No PPStructureV3 - just fast text extraction
# Build: docker build --build-arg USE_GPU=true/false .
# ==========================================

ARG USE_GPU=false

# ============ GPU BASE ============
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 AS base-true

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install PaddlePaddle GPU
RUN pip install --no-cache-dir paddlepaddle-gpu -i https://www.paddlepaddle.org.cn/packages/stable/cu123/

# ============ CPU BASE ============
FROM python:3.11-slim AS base-false

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

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install PaddlePaddle CPU
RUN pip install --no-cache-dir paddlepaddle -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

# ============ FINAL STAGE ============
FROM base-${USE_GPU} AS final

WORKDIR /app

# Install minimal dependencies for PaddleOCR
RUN pip install --no-cache-dir \
    paddleocr>=3.0.0 \
    fastapi==0.115.6 \
    "uvicorn[standard]==0.34.0" \
    Pillow \
    "numpy<2.0" \
    PyMuPDF \
    pydantic \
    python-multipart \
    opencv-python-headless

# Copy application code
COPY app/ app/

# Create cache directory
RUN mkdir -p /home/appuser/.paddlex && chmod 777 /home/appuser/.paddlex

# Environment variables
ARG USE_GPU
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    USE_GPU=${USE_GPU} \
    PADDLEX_HOME=/home/appuser/.paddlex \
    DISABLE_MODEL_SOURCE_CHECK=True

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9124/health || exit 1

EXPOSE 9124

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9124"]
