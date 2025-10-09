# DocTranslator Documentation

Medical document translation service with AI-powered processing and OCR support.

## 📖 Overview

**DocTranslator** translates complex medical documents into patient-friendly language while maintaining GDPR compliance and data privacy. Built with FastAPI backend, React frontend, and microservices architecture deployed on Railway.

### Key Features

- 🏥 **Medical Document Translation** - Translates German medical documents into simple, understandable language
- 🔒 **GDPR Compliant** - Zero data retention, EU-based processing, automated PII removal
- 📄 **Multi-Format Support** - PDF, images (JPG, PNG) with OCR
- 🤖 **Multiple OCR Engines** - Tesseract, PaddleOCR microservice, Vision LLM, intelligent hybrid routing
- ⚡ **Background Processing** - Celery worker with Redis queue for async document processing
- 🌐 **Multi-Language Output** - German, English, French, Spanish, Italian, Portuguese, Dutch, Polish
- 📊 **Configurable Pipeline** - Database-driven 9-step processing pipeline
- 🎨 **Modern UI** - React + TypeScript + TailwindCSS responsive interface

## 🏗️ Architecture

DocTranslator uses a **microservices architecture** deployed on Railway:

```
┌─────────────────────────────────────────────────────┐
│                  Railway Platform                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────┐   ┌──────────┐   ┌───────────────┐  │
│  │ Frontend │   │ Backend  │   │ Worker        │  │
│  │ (React)  │──▶│ (FastAPI)│──▶│ (Celery)      │  │
│  │ nginx    │   │ Port 9122│   │ Redis Queue   │  │
│  └──────────┘   └────┬─────┘   └───────┬───────┘  │
│                      │                  │          │
│                      ▼                  ▼          │
│              ┌──────────────┐   ┌─────────────┐   │
│              │ PaddleOCR    │   │ PostgreSQL  │   │
│              │ (FastAPI)    │   │ Database    │   │
│              │ Port 9123    │   └─────────────┘   │
│              └──────────────┘                      │
│                      │                             │
│                      ▼                             │
│              ┌──────────────┐                      │
│              │ Redis        │                      │
│              │ (Broker)     │                      │
│              └──────────────┘                      │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
          ┌──────────────────────┐
          │ OVH AI Endpoints     │
          │ (Llama 3.3 70B)      │
          │ (EU Infrastructure)  │
          └──────────────────────┘
```

### Services

1. **Frontend** - React 18 + TypeScript + Vite (nginx on port 8080)
2. **Backend** - FastAPI async API (port 9122, IPv6 `::`)
3. **Worker** - Celery background processor (connects to Redis)
4. **PaddleOCR Service** - Standalone OCR microservice (port 9123, IPv6 `::`)
5. **Redis** - Task queue broker and result backend
6. **PostgreSQL** - Pipeline configuration and audit logging

## 📚 Documentation

### Core Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Detailed system architecture, components, and data flow
- **[API.md](./API.md)** - REST API endpoint reference
- **[DATABASE.md](./DATABASE.md)** - Database schema and migrations

### Deployment & Development

- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Production deployment guide for Railway
- **[RAILWAY_DEPLOYMENT_GUIDE.md](./RAILWAY_DEPLOYMENT_GUIDE.md)** - Detailed Railway setup
- **[DEVELOPMENT.md](./DEVELOPMENT.md)** - Local development setup and workflow

### Pipeline Configuration

- **[PIPELINE_VARIABLES.md](./PIPELINE_VARIABLES.md)** - ⭐ **NEW** - Variables and context system for pipeline steps
  - Access original OCR text in any step
  - Use document type for conditional logic
  - Multi-language handling with context variables

### Privacy & Security

- **[OPTIMIZED_PII_FILTER.md](./OPTIMIZED_PII_FILTER.md)** - Advanced PII detection with spaCy NER
- **[PII_REMOVAL_TOGGLE.md](./PII_REMOVAL_TOGGLE.md)** - Configurable PII removal feature
- **[PRIVACY_FILTER.md](./PRIVACY_FILTER.md)** - Basic privacy filter overview

### AI & Cost Management

- **[TOKEN_TRACKING.md](./TOKEN_TRACKING.md)** - AI token usage tracking and cost management

### Quick Start

1. **Deploy to Railway** → See [RAILWAY_DEPLOYMENT_GUIDE.md](./RAILWAY_DEPLOYMENT_GUIDE.md)
2. **Local Development** → See [DEVELOPMENT.md](./DEVELOPMENT.md)
3. **Configure Pipeline** → See [PIPELINE_VARIABLES.md](./PIPELINE_VARIABLES.md)
4. **API Integration** → See [API.md](./API.md)

### Archive

Historical documentation moved to **[archive/](./archive/)** for reference.

## 🚀 Technology Stack

### Backend
- **FastAPI** 0.115.6 - Modern async Python web framework
- **Celery** 5.4.0 - Distributed task queue
- **Redis** 5.0.0 - Message broker and result backend
- **PostgreSQL** - Production database
- **SQLAlchemy** 2.0.43 - ORM and database toolkit
- **httpx** 0.28.1 - Async HTTP client

### OCR & Document Processing
- **Tesseract** - Fast local OCR (Tier 1)
- **PaddleOCR** - CPU-based OCR microservice (Tier 2)
- **pytesseract** 0.3.13 - Python Tesseract wrapper
- **pdf2image** 1.17.0 - PDF to image conversion
- **PyPDF2** 3.0.1 - PDF text extraction
- **pdfplumber** 0.11.5 - Advanced PDF parsing
- **Pillow** 11.1.0 - Image processing

### AI & NLP
- **OVH AI Endpoints** - Llama 3.3 70B, Mistral Nemo, Qwen 2.5 VL
- **OpenAI SDK** 1.59.2 - Compatible API client
- **spaCy** 3.8.3 - NLP for PII detection

### Frontend
- **React** 18.3.1 - UI framework
- **TypeScript** 5.7.3 - Type-safe JavaScript
- **Vite** 6.0.6 - Build tool and dev server
- **TailwindCSS** 3.4.17 - Utility-first CSS
- **React Router** 6.30.1 - Client-side routing
- **Axios** 1.7.9 - HTTP client

### Infrastructure
- **Railway** - Cloud platform with IPv6 networking
- **Docker** - Containerization
- **nginx** - Reverse proxy and static file serving

## 🔐 Security & Privacy

### GDPR Compliance
- ✅ **Zero Data Retention** - Documents processed in-memory only
- ✅ **EU-Based Processing** - OVH AI Endpoints hosted in EU
- ✅ **Automated PII Removal** - spaCy NER-based privacy filter
- ✅ **No Third-Party Tracking** - No analytics or external scripts
- ✅ **Audit Logging** - Optional AI interaction logging (configurable)

### Application Security
- ✅ **HTTPS Only** - Encrypted transport (Railway automatic)
- ✅ **Input Validation** - Pydantic models and file type checking
- ✅ **Rate Limiting** - Request throttling (5 uploads/minute)
- ✅ **CORS Protection** - Configurable allowed origins
- ✅ **Secure Headers** - X-Frame-Options, CSP, X-Content-Type-Options

## 📊 Processing Pipeline

DocTranslator uses a **database-configurable 9-step pipeline**:

1. **TEXT_EXTRACTION** - OCR preprocessing with Vision LLM
2. **MEDICAL_VALIDATION** - Binary medical classification
3. **CLASSIFICATION** - Document type detection (ARZTBRIEF/BEFUNDBERICHT/LABORWERTE)
4. **PII_PREPROCESSING** - Privacy filtering with spaCy NER
5. **TRANSLATION** - Patient-friendly German translation
6. **FACT_CHECK** - Medical accuracy verification
7. **GRAMMAR_CHECK** - Language correction
8. **LANGUAGE_TRANSLATION** - Multi-language support
9. **FINAL_CHECK** - Quality assurance
10. **FORMATTING** - Markdown structure optimization

All steps can be enabled/disabled and customized via Settings UI.

## 🔧 OCR Engine Selection

Four OCR strategies with automatic fallback:

### TESSERACT (Fast Local)
- Speed: <5s per page
- Best for: Clean, simple documents
- Language: German + English
- Cost: Free

### PADDLEOCR (Microservice)
- Speed: ~2-5s per page
- Best for: Complex documents, handwritten text
- Language: German + multilingual
- Cost: Free (CPU-based)
- Architecture: Standalone FastAPI service

### VISION_LLM (AI-Powered)
- Speed: ~2 minutes per page
- Best for: Highly complex or degraded documents
- Model: Qwen 2.5 VL 72B
- Cost: OVH AI Endpoints pricing

### HYBRID (Intelligent Routing)
- Analyzes document quality
- Automatically selects optimal OCR
- Tesseract → PaddleOCR → Vision LLM fallback chain
- Best for: Production use

## 🌐 Multi-Language Support

**Input**: German medical documents

**Output**: 8 languages
- 🇩🇪 German (simplified)
- 🇬🇧 English
- 🇫🇷 French
- 🇪🇸 Spanish
- 🇮🇹 Italian
- 🇵🇹 Portuguese
- 🇳🇱 Dutch
- 🇵🇱 Polish

## 📝 Supported Document Types

### Medical Documents
- **ARZTBRIEF** - Doctor's letters, discharge summaries
- **BEFUNDBERICHT** - Medical reports, diagnostic findings
- **LABORWERTE** - Laboratory results, blood tests

### File Formats
- PDF (up to 50 pages)
- Images: JPG, JPEG, PNG
- Max file size: 50MB

## 🔍 API Endpoints

### Document Processing
- `POST /api/upload` - Upload document
- `GET /api/processing/{id}` - Check processing status
- `POST /api/process/translate` - Process uploaded document

### Configuration
- `GET /api/pipeline/ocr-engines` - List available OCR engines
- `GET /api/pipeline/steps` - Get pipeline configuration
- `PUT /api/pipeline/steps` - Update pipeline steps
- `GET /api/settings/universal-prompts` - Get universal prompts
- `PUT /api/settings/universal-prompts` - Update prompts

### Health & Monitoring
- `GET /health` - Service health check
- `GET /api/health` - Backend health status
- `GET /api/health/detailed` - Detailed diagnostics

See [API.md](./API.md) for complete endpoint documentation.

## 🚢 Deployment

### Railway (Production) - Recommended

```bash
# 1. Connect GitHub repository to Railway
# 2. Add PostgreSQL database service
# 3. Add Redis service
# 4. Deploy Backend, Worker, and PaddleOCR services
# 5. Set environment variables

# Required:
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token
DATABASE_URL=postgresql://...  # Auto-configured
REDIS_URL=redis://...          # Auto-configured

# Backend service:
PADDLEOCR_SERVICE_URL=http://paddleocr-service.railway.internal:9123

# PaddleOCR service:
PORT=9123
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for step-by-step guide.

### Docker Compose (Local)

```bash
docker-compose up -d
```

### Local Development

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 9122

# Frontend
cd frontend
npm install && npm run dev

# Worker
cd worker
celery -A worker.worker.celery_app worker --loglevel=info
```

See [DEVELOPMENT.md](./DEVELOPMENT.md) for detailed setup.

## 📈 Monitoring

### Health Checks

```bash
# Service health
curl https://your-app.up.railway.app/health

# Backend diagnostics
curl https://your-app.up.railway.app/api/health/detailed

# PaddleOCR service (internal)
curl http://paddleocr-service.railway.internal:9123/health
```

### Metrics Tracked
- Processing success rates
- Average processing times
- OCR engine usage statistics
- Error frequency and types
- Worker queue length
- Redis connection status

## 🐛 Troubleshooting

### Common Issues

**PaddleOCR not available**
- Check service is running: Railway dashboard → PaddleOCR service
- Verify internal URL: `http://paddleocr-service.railway.internal:9123`
- Check IPv6 networking: Service must listen on `::` not `0.0.0.0`
- Review logs: Look for `✅ PaddleOCR initialized successfully`

**Worker not processing**
- Check Redis connection: `REDIS_URL` environment variable
- Verify worker is running: Railway dashboard → Worker service
- Check logs: Look for `✅ Celery worker initialized`
- Test manually: Upload document and check processing status

**Database errors**
- Verify PostgreSQL service running
- Check `DATABASE_URL` connection string
- Run migrations: `python app/database/init_db.py`

See [DEPLOYMENT.md#troubleshooting](./DEPLOYMENT.md#troubleshooting) for more solutions.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Follow [DEVELOPMENT.md](./DEVELOPMENT.md) for setup
4. Make changes and test thoroughly
5. Submit pull request

## 📄 License

[License information to be added]

## 📞 Support

- **Documentation**: This `/docs` folder
- **Issues**: GitHub Issues
- **Railway**: [Railway Discord](https://discord.gg/railway)
- **OVH AI**: [Documentation](https://endpoints.ai.cloud.ovh.net/docs)

---

**Version**: 2.0.0 (Microservices Architecture)
**Last Updated**: January 2025
**Deployment**: Railway with IPv6 Internal Networking
