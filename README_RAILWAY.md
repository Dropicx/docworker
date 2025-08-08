# DocTranslator - Railway Deployment Branch

This branch (`railwaywithovhapi`) is configured for deployment on Railway.app with OVH AI Endpoints.

## 🚀 Key Features

- **No Local Infrastructure Required**: All AI processing via OVH cloud
- **No GPU Needed**: Runs on standard Railway containers
- **Auto-scaling**: Railway handles scaling automatically
- **Automatic HTTPS**: SSL/TLS provided by Railway
- **Simple Deployment**: One-click deploy from GitHub

## 🏗️ Architecture

```
User → Railway (HTTPS) → Nginx → Backend (FastAPI) → OVH AI Endpoints
                          ↓
                       Frontend (React)
```

## 📦 What's Different in This Branch

### Removed
- ❌ Traefik (Railway handles routing)
- ❌ Ollama (Using OVH API instead)
- ❌ GPU requirements
- ❌ Complex docker-compose setup

### Added
- ✅ Railway-specific Dockerfile
- ✅ Nginx + Supervisor configuration
- ✅ OVH API integration
- ✅ Simplified deployment

## 🚢 Deployment

See [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) for detailed instructions.

### Quick Start

1. **Fork/Clone this repository**
2. **Get OVH API Token** from [OVH AI Endpoints](https://endpoints.ai.cloud.ovh.net/)
3. **Deploy to Railway**:
   - Connect GitHub repo (use `railwaywithovhapi` branch)
   - Add environment variables (especially `OVH_AI_ENDPOINTS_ACCESS_TOKEN`)
   - Deploy!

## 🔧 Configuration

All configuration is done through environment variables in Railway dashboard:

```env
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token-here
OVH_MAIN_MODEL=Meta-Llama-3_3-70B-Instruct
OVH_PREPROCESSING_MODEL=Mistral-Nemo-Instruct-2407
OVH_TRANSLATION_MODEL=Meta-Llama-3_3-70B-Instruct
USE_OVH_ONLY=true
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## 📊 Models Used

- **Preprocessing**: Mistral-Nemo-Instruct-2407 (removes personal data)
- **Main Processing**: Meta-Llama-3.3-70B-Instruct (medical translation)
- **Language Translation**: Meta-Llama-3.3-70B-Instruct (multi-language)

## 🛠️ Local Development

For local development, use the main branch with docker-compose. This branch is optimized specifically for Railway deployment.

## 📝 Notes

- No medical data is stored permanently
- All processing happens in memory
- Temporary files are automatically cleaned up
- GDPR/DSGVO compliant

## 🆘 Support

- [Railway Documentation](https://docs.railway.app)
- [OVH AI Endpoints Docs](https://endpoints.ai.cloud.ovh.net/docs)
- [Project Issues](https://github.com/your-repo/issues)