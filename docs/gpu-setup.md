# GPU Setup and Automatic Configuration

## Overview

The Doctranslator application now includes intelligent GPU detection and configuration scripts that automatically handle NVIDIA GPU setup and fallback to CPU mode when necessary.

## Components

### 1. NVIDIA Check Script (`scripts/check-nvidia.sh`)
This script performs comprehensive GPU verification:
- Detects NVIDIA GPU hardware
- Verifies driver installation
- Loads kernel modules
- Tests nvidia-smi functionality
- Validates Docker GPU support
- Creates appropriate docker-compose override files

### 2. Intelligent Startup Script (`start.sh`)
A wrapper around docker-compose that:
- Runs GPU verification before starting services
- Automatically selects GPU or CPU configuration
- Provides convenient commands for service management
- Shows GPU status and monitoring information

## Usage

### Quick Start
```bash
# Start all services with automatic GPU detection
./start.sh

# Or explicitly:
./start.sh up
```

### Available Commands
```bash
./start.sh up          # Start all services
./start.sh down        # Stop all services
./start.sh restart     # Restart services
./start.sh logs        # View logs
./start.sh ps          # Show status
./start.sh gpu-status  # Check GPU configuration
./start.sh models      # List Ollama models
./start.sh help        # Show all commands
```

### Manual GPU Check
```bash
# Run GPU verification only
bash scripts/check-nvidia.sh
```

## How It Works

### Automatic GPU Detection Flow

1. **Hardware Detection**: Checks for NVIDIA GPU using `lspci`
2. **Driver Verification**: Ensures NVIDIA drivers are installed
3. **Module Loading**: Loads required kernel modules:
   - nvidia
   - nvidia_uvm
   - nvidia_modeset
   - nvidia_drm
4. **nvidia-smi Test**: Validates driver functionality
5. **Docker GPU Test**: Confirms Docker can access GPU
6. **Configuration Selection**:
   - If all checks pass → GPU mode enabled
   - If any check fails → CPU mode fallback

### Configuration Files

The scripts automatically create override files:

#### GPU Mode (`docker-compose.gpu.yml`)
```yaml
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

#### CPU Mode (`docker-compose.cpu.yml`)
```yaml
services:
  ollama:
    environment:
      - OLLAMA_NUM_GPU=0  # Force CPU-only
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

## Troubleshooting

### Common Issues and Solutions

#### 1. NVIDIA Driver Not Installed
```bash
# Install recommended driver
sudo ubuntu-drivers autoinstall
sudo reboot
```

#### 2. Kernel Modules Not Loading
```bash
# Rebuild DKMS modules
sudo dkms status
sudo dkms build nvidia/550.163.01
sudo dkms install nvidia/550.163.01
sudo update-initramfs -u
sudo reboot
```

#### 3. Docker Can't Access GPU
```bash
# Install NVIDIA Container Toolkit
sudo apt install nvidia-container-toolkit
sudo systemctl restart docker
```

#### 4. Secure Boot Issues
```bash
# Check Secure Boot status
mokutil --sb-state

# If enabled, either:
# - Disable in BIOS, or
# - Sign kernel modules (complex)
```

### Manual Module Loading
If modules don't load automatically:
```bash
sudo modprobe nvidia
sudo modprobe nvidia_uvm
sudo modprobe nvidia_modeset
sudo modprobe nvidia_drm
```

## Performance Comparison

### GPU Mode (RTX 4000)
- Model loading: ~5-10 seconds
- Inference speed: ~50-100 tokens/second
- Multiple models in memory: Yes
- Power usage: Higher

### CPU Mode
- Model loading: ~30-60 seconds
- Inference speed: ~5-20 tokens/second
- Multiple models in memory: Limited
- Power usage: Lower

## Monitoring

### GPU Monitoring
```bash
# Real-time GPU usage
watch nvidia-smi

# Docker container GPU usage
docker stats ollama

# Ollama logs
./start.sh logs -f ollama
```

### Check Current Mode
```bash
# Show current configuration
./start.sh gpu-status

# View effective docker-compose config
./start.sh config
```

## Requirements

### For GPU Mode
- NVIDIA GPU (any CUDA-capable card)
- NVIDIA Driver (version 450+)
- NVIDIA Container Toolkit
- Docker with GPU support
- Sufficient GPU memory (4GB+ recommended)

### For CPU Mode
- x86_64 processor with AVX support
- 8GB+ RAM recommended
- No special requirements

## Best Practices

1. **Always use start.sh**: It handles configuration automatically
2. **Check GPU status**: Run `./start.sh gpu-status` to verify mode
3. **Monitor resources**: Use `nvidia-smi` in GPU mode
4. **Update drivers**: Keep NVIDIA drivers current for best performance
5. **Restart after driver updates**: Always reboot after driver changes

## Advanced Configuration

### Force CPU Mode
```bash
# Set environment variable
export OLLAMA_NUM_GPU=0
./start.sh up
```

### Custom GPU Selection
Edit `docker-compose.gpu.yml`:
```yaml
devices:
  - driver: nvidia
    device_ids: ['0']  # Use first GPU only
    capabilities: [gpu]
```

### Memory Limits
Adjust in `docker-compose.cpu.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '8'      # More CPUs
      memory: 16G    # More RAM
```

## Support

### Logs and Debugging
```bash
# Check GPU verification
bash scripts/check-nvidia.sh

# View startup logs
./start.sh logs ollama

# System logs
journalctl -xe | grep nvidia
dmesg | grep nvidia
```

### Getting Help
```bash
# Show available commands
./start.sh help

# Check system status
./start.sh ps
./start.sh gpu-status
```