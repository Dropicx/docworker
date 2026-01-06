# PP-StructureV3 on Vast.ai

Deploy PP-StructureV3 OCR service on vast.ai with GPU acceleration and a static public IP.

## Prerequisites

- Docker installed locally
- Docker Hub account
- Vast.ai account with credits

## Quick Start

### 1. Build and Push Docker Image

```bash
# Set your Docker Hub username
export DOCKERHUB_USER=your-username

# Build, tag, and push
make all
```

Or manually:

```bash
cd ../../paddleocr_service
docker build --build-arg USE_GPU=true -t ppstructure:gpu .
docker tag ppstructure:gpu your-username/ppstructure:gpu
docker login
docker push your-username/ppstructure:gpu
```

### 2. Create Vast.ai Template

1. Go to [vast.ai Templates](https://cloud.vast.ai/templates/)
2. Create new template with:
   - **Image:** `your-username/ppstructure:gpu`
   - **Docker Options:** `--gpus all`
   - **Port:** `9124`
   - **Environment:** `USE_GPU=true`

See [template-config.md](template-config.md) for detailed settings.

### 3. Rent Instance

1. Go to [vast.ai](https://cloud.vast.ai/)
2. Filter instances:
   - GPU: RTX 3060+ (4GB+ VRAM)
   - CUDA: 12.x
   - Direct IP: Available (for static public IP)
3. Select your template
4. Rent instance

### 4. Set Up Service

SSH into your instance and run setup:

```bash
# Clone repo
git clone https://github.com/Dropicx/doctranslator.git
cd doctranslator/external_deployment/vastai

# Run setup (generates API key, starts container)
./setup.sh your-username/ppstructure:gpu
```

Or run the container directly:

```bash
# Generate API key
API_KEY=$(tr -dc A-Za-z0-9 < /dev/urandom | head -c 64)
echo $API_KEY

# Run container
docker run -d --name ppstructure --gpus all -p 9124:9124 \
  -e USE_GPU=true \
  -e API_SECRET_KEY=$API_KEY \
  -v paddle_models:/home/appuser/.paddlex \
  your-username/ppstructure:gpu
```

### 5. Configure Backend

Add to your Railway/backend environment:

```
EXTERNAL_OCR_URL=http://<vast-ip>:9124
EXTERNAL_API_KEY=<your-api-key>
USE_EXTERNAL_OCR=true
```

## Instance Commands

```bash
# Check health (from local machine)
make health IP=<vast-ip>

# SSH into instance
make ssh IP=<vast-ip>

# View logs
make logs IP=<vast-ip>
```

## Troubleshooting

### Service not responding
```bash
# Check container status
docker ps -a

# View logs
docker logs -f ppstructure

# Restart container
docker restart ppstructure
```

### Model download taking too long
First startup downloads ~1-2GB of models. This can take 5-15 minutes. Check logs for progress:
```bash
docker logs -f ppstructure
```

### GPU not detected
```bash
# Verify GPU is available
nvidia-smi

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

### API authentication errors
Verify API key matches:
```bash
# On vast.ai instance
cat /workspace/API_KEY.txt

# Test with curl
curl -H "X-API-Key: <key>" http://localhost:9124/health
```

## Cost Estimation

| GPU | VRAM | Approx. Cost/hr |
|-----|------|-----------------|
| RTX 3060 | 12GB | ~$0.10 |
| RTX 3080 | 10GB | ~$0.15 |
| RTX 4090 | 24GB | ~$0.40 |

PP-StructureV3 uses ~2-3GB VRAM, so budget GPUs work fine.

## Files

- `setup.sh` - Instance setup script
- `template-config.md` - Vast.ai template reference
- `Makefile` - Build/push/management commands

## Updating the Service

```bash
# On local machine: rebuild and push
make all

# On vast.ai instance: pull and restart
docker pull your-username/ppstructure:gpu
docker stop ppstructure && docker rm ppstructure
./setup.sh your-username/ppstructure:gpu
```
