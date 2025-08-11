# DocTranslator - Medical Document Translation Service

GDPR-compliant translation service for medical documents with OVH AI integration.

## Features

- 🔒 **GDPR Compliant** - All data processing within EU
- 🏥 **Medical Specialization** - Optimized for medical terminology
- 🌍 **Multi-Language** - DE, EN, FR, ES, IT, PT, NL, PL support
- 📄 **Multiple Formats** - PDF, DOCX, TXT, images (OCR)
- 🚀 **OVH AI Powered** - Using Llama 3.3 70B model
- 🔐 **Secure** - No data retention, encrypted processing

## Quick Start

### Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 9122

# Frontend
cd frontend
npm install
npm run dev
```

### Docker Deployment

```bash
docker-compose up
```

### Railway Deployment

1. Deploy to Railway using the button or CLI
2. Set environment variables in Railway dashboard:
   ```
   OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token-here
   OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1
   USE_OVH_ONLY=true
   ```
3. Railway will automatically build and deploy using `Dockerfile.railway`

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OVH_AI_ENDPOINTS_ACCESS_TOKEN` | OVH API token | Yes |
| `OVH_AI_BASE_URL` | OVH API endpoint | Yes |
| `USE_OVH_ONLY` | Use only OVH (no local Ollama) | Yes |
| `OVH_MAIN_MODEL` | Main AI model | No (default: Meta-Llama-3_3-70B-Instruct) |

## Architecture

```
frontend/          # React + TypeScript + Vite
├── src/          # Source code
└── dist/         # Built files

backend/          # FastAPI + Python
├── app/          # Application code
│   ├── routers/  # API endpoints
│   └── services/ # Business logic
└── tests/        # Test files

railway/          # Deployment configs
└── *.sh         # Startup scripts

docs/             # Documentation
```

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/upload` - Upload document
- `POST /api/process/translate` - Translate document
- `GET /api/health/env-debug` - Debug environment

## Security

- No data persistence after processing
- Automatic cleanup every 30 seconds
- CORS protection
- Rate limiting
- Input validation
- Encrypted transport (HTTPS)

## Development

See [docs/development/README.md](docs/development/README.md) for development guidelines.

## Deployment

See [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) for Railway deployment instructions.

## License

MIT

## Support

For issues, please create an issue on GitHub.