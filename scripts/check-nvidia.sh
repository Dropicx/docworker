#!/bin/bash

# NVIDIA GPU Verification Script for Doctranslator
# This script checks if NVIDIA drivers and Docker GPU support are properly configured

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "==========================================="
echo "🔍 NVIDIA GPU Configuration Check"
echo "==========================================="

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Track if we should use GPU
USE_GPU=true
ERRORS_FOUND=false

# 1. Check if NVIDIA GPU exists
echo ""
echo "1️⃣  Checking for NVIDIA GPU..."
if lspci | grep -i nvidia > /dev/null 2>&1; then
    GPU_INFO=$(lspci | grep -i "VGA.*NVIDIA" | head -1)
    print_success "NVIDIA GPU detected: ${GPU_INFO#*: }"
else
    print_warning "No NVIDIA GPU detected - will run in CPU mode"
    USE_GPU=false
fi

# 2. Check NVIDIA driver installation
if [ "$USE_GPU" = true ]; then
    echo ""
    echo "2️⃣  Checking NVIDIA driver..."
    
    # Check if driver packages are installed
    if dpkg -l | grep -q "nvidia-driver-[0-9]"; then
        DRIVER_VERSION=$(dpkg -l | grep "nvidia-driver-[0-9]" | awk '{print $3}' | head -1)
        print_success "NVIDIA driver installed: version $DRIVER_VERSION"
    else
        print_error "NVIDIA driver not installed"
        print_warning "Install with: sudo ubuntu-drivers autoinstall"
        USE_GPU=false
        ERRORS_FOUND=true
    fi
fi

# 3. Check and load NVIDIA kernel modules
if [ "$USE_GPU" = true ]; then
    echo ""
    echo "3️⃣  Checking NVIDIA kernel modules..."
    
    MODULES_LOADED=true
    for module in nvidia nvidia_uvm nvidia_modeset nvidia_drm; do
        if ! lsmod | grep -q "^$module"; then
            echo "   Loading module: $module..."
            if sudo modprobe $module 2>/dev/null; then
                print_success "Module $module loaded"
            else
                print_warning "Could not load module $module"
                MODULES_LOADED=false
            fi
        else
            print_success "Module $module already loaded"
        fi
    done
    
    if [ "$MODULES_LOADED" = false ]; then
        print_error "Some kernel modules failed to load"
        print_warning "You may need to reboot or rebuild DKMS modules"
        USE_GPU=false
        ERRORS_FOUND=true
    fi
fi

# 4. Check nvidia-smi
if [ "$USE_GPU" = true ]; then
    echo ""
    echo "4️⃣  Testing nvidia-smi..."
    
    if nvidia-smi > /dev/null 2>&1; then
        GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
        GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader | head -1)
        print_success "nvidia-smi working - GPU: $GPU_NAME ($GPU_MEMORY)"
    else
        print_error "nvidia-smi failed"
        print_warning "Driver may not be properly loaded"
        USE_GPU=false
        ERRORS_FOUND=true
    fi
fi

# 5. Check Docker NVIDIA runtime
if [ "$USE_GPU" = true ]; then
    echo ""
    echo "5️⃣  Checking Docker NVIDIA support..."
    
    # Check if nvidia-container-toolkit is installed
    if which nvidia-container-cli > /dev/null 2>&1; then
        print_success "NVIDIA Container Toolkit installed"
    else
        print_error "NVIDIA Container Toolkit not installed"
        print_warning "Install with: sudo apt install nvidia-container-toolkit"
        USE_GPU=false
        ERRORS_FOUND=true
    fi
    
    # Test Docker GPU support
    if [ "$USE_GPU" = true ]; then
        echo "   Testing Docker GPU access..."
        if docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi > /dev/null 2>&1; then
            print_success "Docker can access GPU"
        else
            print_error "Docker cannot access GPU"
            print_warning "Try: sudo systemctl restart docker"
            USE_GPU=false
            ERRORS_FOUND=true
        fi
    fi
fi

# 6. Final decision and docker-compose modification
echo ""
echo "==========================================="
echo "📊 Configuration Summary"
echo "==========================================="

# Get the script's parent directory (project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
COMPOSE_GPU_FILE="$PROJECT_ROOT/docker-compose.gpu.yml"
COMPOSE_CPU_FILE="$PROJECT_ROOT/docker-compose.cpu.yml"

if [ "$USE_GPU" = true ]; then
    print_success "✨ GPU support is ENABLED"
    echo ""
    echo "Your Ollama container will use GPU acceleration."
    echo "This will significantly improve model inference speed."
    
    # Create GPU-enabled override file
    cat > "$COMPOSE_GPU_FILE" << 'EOF'
# GPU-enabled configuration for Ollama
version: '3.8'

services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
EOF
    
    export COMPOSE_CONFIG="gpu"
    
else
    print_warning "💻 Running in CPU-ONLY mode"
    echo ""
    if [ "$ERRORS_FOUND" = true ]; then
        echo "Some issues were found with GPU configuration."
        echo "The application will still work but inference will be slower."
        echo ""
        echo "To enable GPU support, fix the issues above and run again."
    else
        echo "No NVIDIA GPU detected. Running on CPU."
    fi
    
    # Create CPU-only override file
    cat > "$COMPOSE_CPU_FILE" << 'EOF'
# CPU-only configuration for Ollama
version: '3.8'

services:
  ollama:
    environment:
      - OLLAMA_KEEP_ALIVE=24h
      - OLLAMA_NUM_GPU=0  # Force CPU-only mode
    # GPU configuration explicitly disabled
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
EOF
    
    export COMPOSE_CONFIG="cpu"
fi

echo ""
echo "==========================================="
echo "Configuration mode: $COMPOSE_CONFIG"
echo "==========================================="

# Exit with appropriate code
if [ "$ERRORS_FOUND" = true ]; then
    exit 1
else
    exit 0
fi