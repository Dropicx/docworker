# ==========================================
# PP-StructureV3 Universal Dockerfile
# Supports both CPU and GPU via build arg
# Build: docker build --build-arg USE_GPU=true/false .
# ==========================================

ARG USE_GPU=false

# ============ GPU BASE ============
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 AS base-true

ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.11 and system dependencies
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
    poppler-utils \
    libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install PaddlePaddle GPU (CUDA 12.3)
RUN pip install --no-cache-dir nvidia-cuda-cccl-cu12 && \
    pip install --no-cache-dir --no-deps paddlepaddle-gpu -i https://www.paddlepaddle.org.cn/packages/stable/cu123/ && \
    pip install --no-cache-dir httpx numpy Pillow decorator opt-einsum protobuf networkx typing_extensions \
        nvidia-cuda-runtime-cu12 nvidia-cuda-cupti-cu12 nvidia-cudnn-cu12 nvidia-cublas-cu12 \
        nvidia-cufft-cu12 nvidia-curand-cu12 nvidia-cusolver-cu12 nvidia-cusparse-cu12 \
        nvidia-nccl-cu12 nvidia-nvtx-cu12 nvidia-cuda-nvrtc-cu12

# ============ CPU BASE ============
FROM python:3.11-slim AS base-false

# Install system dependencies
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

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install PaddlePaddle CPU FIRST (before paddleocr to prevent GPU version)
# Pin to CPU version explicitly
RUN pip install --no-cache-dir paddlepaddle==3.0.0b2 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

# ============ FINAL STAGE ============
FROM base-${USE_GPU} AS final

WORKDIR /app

# Install PaddleOCR with doc-parser for PP-StructureV3
# Use --no-deps first to avoid pulling paddlepaddle again, then install deps
RUN pip install --no-cache-dir --no-deps "paddleocr>=3.3.0" && \
    pip install --no-cache-dir \
    paddlex \
    docx2pdf \
    fastapi==0.115.6 \
    "uvicorn[standard]==0.34.0" \
    Pillow==11.0.0 \
    "numpy<2.0" \
    PyMuPDF==1.24.14 \
    pydantic==2.10.3 \
    python-multipart==0.0.9 \
    psutil>=5.9.0 \
    opencv-python-headless \
    shapely \
    pyclipper \
    imgaug \
    lmdb \
    tqdm \
    visualdl \
    rapidfuzz \
    cython \
    lxml \
    premailer \
    openpyxl \
    attrdict3 \
    PyYAML

# Copy application code
COPY app/ app/

# Create cache directory for models
RUN mkdir -p /home/appuser/.paddlex && chmod 777 /home/appuser/.paddlex

# Environment variables
ARG USE_GPU
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    USE_GPU=${USE_GPU} \
    PADDLEOCR_DEFAULT_MODE=structured \
    PADDLEX_HOME=/home/appuser/.paddlex \
    HF_HOME=/home/appuser/.paddlex/huggingface \
    DISABLE_MODEL_SOURCE_CHECK=True

# Health check (long start period for model download on first run)
HEALTHCHECK --interval=30s --timeout=60s --start-period=300s --retries=5 \
    CMD curl -f http://localhost:9124/health || exit 1

# Expose port
EXPOSE 9124

# Run uvicorn directly (no entrypoint script needed)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9124"]
