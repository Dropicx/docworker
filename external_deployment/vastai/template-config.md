# Vast.ai Template Configuration

Reference for creating a vast.ai template for PP-StructureV3 OCR service.

## Template Settings

### Basic Info
- **Template Name:** PP-StructureV3 OCR
- **Description:** Medical document OCR with structured table extraction

### Docker Configuration
| Setting | Value |
|---------|-------|
| Image | `<your-dockerhub>/ppstructure:gpu` |
| Docker Options | `--gpus all` |

### Ports
| Port | Protocol | Description |
|------|----------|-------------|
| 9124 | HTTP | OCR API endpoint |

### Environment Variables
```
USE_GPU=true
PYTHONUNBUFFERED=1
PADDLEOCR_DEFAULT_MODE=structured
```

Note: `API_SECRET_KEY` should be set at instance creation or via setup.sh

### On-Start Command
```bash
cd /app && python -m uvicorn app.main:app --host 0.0.0.0 --port 9124
```

### Resource Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| GPU VRAM | 4 GB | 8+ GB |
| RAM | 8 GB | 16 GB |
| Disk | 20 GB | 30 GB |
| CUDA | 12.x | 12.4+ |

### Networking
- **Direct IP:** Enable for static public IP
- **SSH:** Enable for debugging access

## Creating the Template

1. Go to https://cloud.vast.ai/templates/
2. Click "Create Template"
3. Fill in settings from above
4. Save template

## Renting an Instance

1. Go to https://cloud.vast.ai/
2. Filter by:
   - GPU: RTX 3060 or better (4GB+ VRAM)
   - CUDA: 12.x
   - Direct IP: Available
3. Select your template
4. Rent instance
5. Wait for instance to start
6. SSH in and verify: `curl http://localhost:9124/health`

## GPU Recommendations

| GPU | VRAM | Performance | Cost/hr |
|-----|------|-------------|---------|
| RTX 3060 | 12GB | Good | ~$0.10 |
| RTX 3080 | 10GB | Great | ~$0.15 |
| RTX 4090 | 24GB | Excellent | ~$0.40 |
| A10 | 24GB | Excellent | ~$0.30 |

PP-StructureV3 uses ~2-3GB VRAM during inference, so any 4GB+ GPU works.
