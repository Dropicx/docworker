# Claude Code Configuration

## Project Overview

**DocTranslator** - GDPR-compliant medical document translation service with OCR support, powered by OVH AI Endpoints (Llama 3.3 70B).

### Tech Stack
- **Backend**: FastAPI 0.115.6 + Python 3.11 (async)
- **Frontend**: React 18.3.1 + TypeScript 5.7.3 + Vite 6.0.6
- **Database**: PostgreSQL (production) / SQLite (local dev)
- **AI**: OVH AI Endpoints - Llama 3.3 70B, Mistral Nemo
- **OCR**: Tesseract with pytesseract
- **Deployment**: Railway with Docker

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

### 9-Step Processing Pipeline
1. TEXT_EXTRACTION - OCR preprocessing
2. MEDICAL_VALIDATION - Medical classification
3. CLASSIFICATION - Document type detection
4. PII_PREPROCESSING - Privacy filtering
5. TRANSLATION - Patient-friendly translation
6. FACT_CHECK - Medical accuracy
7. GRAMMAR_CHECK - Language correction
8. LANGUAGE_TRANSLATION - Multi-language
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
USE_OVH_ONLY=true
```

### Optional
```bash
OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1
OVH_MAIN_MODEL=Meta-Llama-3_3-70B-Instruct
OVH_PREPROCESSING_MODEL=Mistral-Nemo-Instruct-2407
LOG_LEVEL=INFO
DATABASE_URL=postgresql://...  # Auto-configured on Railway
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

### Tables
- `universal_prompts` - Prompts for all document types
- `document_specific_prompts` - Per-document-type prompts
- `universal_pipeline_steps` - Pipeline configuration
- `ai_interaction_logs` - AI request/response logging
- `system_settings` - Key-value configuration

All prompts and configurations are database-driven (no file fallbacks).

## API Endpoints

- `GET /health` - Health check
- `POST /api/upload` - Upload document
- `POST /api/process/translate` - Process document
- `GET /api/settings/universal-prompts` - Get universal prompts
- `PUT /api/settings/universal-prompts` - Update universal prompts
- `GET /api/settings/document-prompts/{type}` - Get document prompts
- `PUT /api/settings/document-prompts/{type}` - Update document prompts
- `GET /api/settings/pipeline-steps` - Get pipeline config
- `PUT /api/settings/pipeline-steps` - Update pipeline config

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
