# Claude Code Configuration

## Project Overview

**DocTranslator** - GDPR-compliant medical document translation service with OCR support, powered by OVH AI Endpoints (Llama 3.3 70B).

### Tech Stack
- **Backend**: FastAPI 0.120+ + Python 3.11 (async)
- **Frontend**: React 18.3.1 + TypeScript 5.7.3 + Vite 6.0.6
- **Database**: PostgreSQL (production) / SQLite (local dev)
- **AI (Translation)**: OVH AI Endpoints - Llama 3.3 70B, Mistral Nemo, Qwen 2.5 VL
- **AI (OCR/Feedback)**: Mistral AI (France) - mistral-ocr-latest, mistral-large-latest
- **OCR**: Mistral OCR (primary), PaddleOCR (Hetzner fallback), Tesseract
- **PII**: Hetzner service (spaCy + Presidio)
- **Deployment**: Railway + Hetzner + OVH + Mistral AI

### Project Structure
```
doctranslator/
├── backend/
│   ├── app/
│   │   ├── routers/        # API endpoints
│   │   ├── services/       # Business logic
│   │   ├── database/       # DB models, connection
│   │   └── main.py         # FastAPI app
│   ├── requirements.txt
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API clients
│   │   ├── types/          # TypeScript types
│   │   └── App.tsx
│   └── package.json
├── docs/                   # All documentation
│   ├── ARCHITECTURE.md
│   ├── DATABASE.md
│   ├── DEPLOYMENT.md
│   └── API.md
├── railway/                # Deployment scripts
└── README.md              # GitHub README
```

## 🚨 File Management Rules

**ABSOLUTE RULES:**
1. **NEVER save working files, text/mds and tests to the root folder**
2. **ALWAYS organize files in appropriate subdirectories**

### Correct File Locations
- `/backend/app/routers/` - API endpoints
- `/backend/app/services/` - Business logic
- `/backend/tests/` - Backend tests
- `/frontend/src/components/` - React components
- `/frontend/src/services/` - Frontend services
- `/docs/` - ALL documentation (no root .md files except README.md and CLAUDE.md)
- `/scripts/` - Utility scripts

## Development Commands

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 9122
```

### Frontend
```bash
cd frontend
npm install
npm run dev          # Development server
npm run build        # Production build
npm run preview      # Preview build
```

### Database
```bash
cd backend
python app/database/init_db.py        # Initialize tables
python app/database/unified_seed.py   # Seed data
```

### Docker
```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

## Key Features

### 10-Step Processing Pipeline
1. TEXT_EXTRACTION - OCR via Mistral OCR (primary) or PaddleOCR
2. MEDICAL_VALIDATION - Medical content classification
3. CLASSIFICATION - Document type detection
4. PII_PREPROCESSING - Privacy filtering via Hetzner PII service
5. TRANSLATION - Patient-friendly translation (Llama 3.3 70B)
6. FACT_CHECK - Medical accuracy verification
7. GRAMMAR_CHECK - Language correction
8. LANGUAGE_TRANSLATION - Multi-language output
9. FINAL_CHECK - Quality assurance
10. FORMATTING - Markdown output

### Document Types
- **ARZTBRIEF** - Doctor's letters, discharge summaries
- **BEFUNDBERICHT** - Medical reports, findings
- **LABORWERTE** - Lab results, blood tests

### Supported Languages
- Input: German (DE)
- Output: EN, FR, ES, IT, PT, NL, PL

## Environment Variables

### Required
```bash
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token-here
MISTRAL_API_KEY=your-mistral-api-key
USE_OVH_ONLY=true
```

### Optional
```bash
OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1
OVH_MAIN_MODEL=Meta-Llama-3_3-70B-Instruct
OVH_PREPROCESSING_MODEL=Mistral-Nemo-Instruct-2407
OVH_VISION_MODEL=Qwen2.5-VL-72B-Instruct
LOG_LEVEL=INFO
DATABASE_URL=postgresql://...  # Auto-configured on Railway
EXTERNAL_PII_URL=https://pii.your-domain.de
PADDLEOCR_SERVICE_URL=https://ocr.your-domain.de
```

## Code Style & Best Practices

- **Modular Design**: Keep files under 500 lines
- **Environment Safety**: Never hardcode secrets, use environment variables
- **Type Safety**: Use Pydantic models (backend), TypeScript interfaces (frontend)
- **Clean Architecture**: Separate routers, services, models
- **Async First**: Use async/await for I/O operations
- **Error Handling**: Proper try/catch with meaningful error messages
- **Documentation**: Keep docs updated in /docs folder

## Database Architecture

### Core Tables
- `pipeline_jobs` - Document processing jobs (encrypted file content)
- `dynamic_pipeline_steps` - User-configurable pipeline steps
- `pipeline_step_executions` - Individual step execution records
- `ai_interaction_logs` - Token usage and cost tracking
- `system_settings` - Key-value configuration
- `users` - User accounts with roles
- `api_keys` - API authentication tokens
- `audit_logs` - Security and compliance audit trail
- `feature_flags` - Runtime feature toggles
- `ocr_configuration` - OCR engine selection and settings
- `available_models` - AI model registry with pricing
- `document_classes` - Custom document type definitions
- `user_feedback` - Feedback with GDPR compliance

All configurations are database-driven (no file fallbacks).

## API Endpoints

### Core
- `GET /health` - Health check
- `GET /health/detailed` - Detailed health with dependencies
- `POST /api/upload` - Upload document
- `GET /api/process/{id}` - Check processing status
- `GET /api/process/{id}/result` - Get final translation

### Configuration
- `GET /api/settings/pipeline-steps` - Get pipeline config
- `PUT /api/settings/pipeline-steps` - Update pipeline config
- `GET /api/settings/ocr-configuration` - Get OCR settings
- `PUT /api/settings/ocr-configuration` - Update OCR settings

### Analytics
- `GET /api/cost/summary` - Token usage and costs
- `GET /api/feedback/stats` - Feedback statistics

### Authentication
- `POST /api/auth/login` - User authentication
- `POST /api/auth/refresh` - Refresh token

See [docs/API.md](docs/API.md) for complete reference.

## Deployment

### Railway (Production)
1. Connect GitHub repository
2. Set environment variables
3. Add PostgreSQL service
4. Deploy automatically via `Dockerfile.railway`

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed guide.

## Testing

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test

# E2E
npm run test:e2e
```

## Documentation

All documentation is in `/docs/`:
- **ARCHITECTURE.md** - System design and components
- **DATABASE.md** - Database schema and queries
- **DEPLOYMENT.md** - Production deployment guide
- **API.md** - Complete API reference
- **PRIVACY_FILTER.md** - PII detection system
- **DATABASE_SETUP.md** - Database setup guide

---

# Important Instruction Reminders

Do what has been asked; nothing more, nothing less.

NEVER create files unless they're absolutely necessary for achieving your goal.

ALWAYS prefer editing an existing file to creating a new one.

NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

Never save working files, text/mds and tests to the root folder.
