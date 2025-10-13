# DocTranslator 🏥

> GDPR-compliant medical document translation service powered by AI

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![React](https://img.shields.io/badge/react-18.3-blue.svg)
![FastAPI](https://img.shields.io/badge/fastapi-0.115-green.svg)
![Code Quality](https://img.shields.io/badge/code%20quality-A-brightgreen.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)
![Coverage](https://img.shields.io/badge/coverage-60%25-yellow.svg)

DocTranslator transforms complex medical documents into patient-friendly language while maintaining complete data privacy and GDPR compliance. Built with FastAPI and React, powered by OVH AI Endpoints.

## ✨ Features

- 🔒 **GDPR Compliant** - All data processing within EU, zero data retention
- 🏥 **Medical Specialization** - Optimized for medical terminology and documents
- 🌍 **Multi-Language Support** - DE, EN, FR, ES, IT, PT, NL, PL
- 📄 **Multiple Formats** - PDF, DOCX, TXT, JPG, PNG (up to 50MB)
- 🔍 **Full OCR Support** - Tesseract OCR for scanned documents
- 🚀 **AI-Powered** - Llama 3.3 70B and Mistral Nemo via OVH AI Endpoints
- 🛡️ **Privacy Filter** - Automatic PII removal with spaCy NER
- ⚡ **Fast Processing** - Optimized 9-step pipeline
- 🎨 **Modern UI** - React + TypeScript + TailwindCSS
- 📊 **Admin Dashboard** - Configurable prompts and pipeline steps

## 🚀 Quick Start

### Using Railway (Recommended)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)

1. Click "Deploy on Railway"
2. Connect your GitHub repository
3. Create two environments:
   - `dev` → linked to `dev` branch
   - `production` → linked to `main` branch
4. Add PostgreSQL to both environments
5. Set environment variables (both environments):
   ```bash
   OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token-here
   USE_OVH_ONLY=true
   ```
6. Railway auto-deploys on push to respective branches

See [DEPLOYMENT.md](./docs/DEPLOYMENT.md) for detailed instructions.

### Using Docker

```bash
# Clone repository
git clone <your-repo-url>
cd doctranslator

# Set environment variables
cp .env.example .env
# Edit .env with your OVH credentials

# Run with Docker Compose
docker-compose up -d

# Access application
open http://localhost:8080
```

### Local Development

**Prerequisites:** Railway dev environment with PostgreSQL ([Setup Guide](./docs/RAILWAY_DEV_SETUP.md))

**Backend:**
```bash
cd backend
cp .env.example .env.development  # Configure with Railway DATABASE_URL
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
export $(cat .env.development | xargs)
python -m uvicorn app.main:app --reload --port 9122
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

See [DEVELOPMENT.md](./docs/DEVELOPMENT.md) for complete local setup guide.

## 📚 Documentation

- **Getting Started**
  - [Development Setup](./docs/DEVELOPMENT.md) - Local development quick start
  - [Railway Dev Setup](./docs/RAILWAY_DEV_SETUP.md) - Railway + PostgreSQL setup
  - [Contributing Guidelines](./CONTRIBUTING.md) - Code style and workflow
  - [Type Checking Guide](./docs/TYPE_CHECKING.md) - MyPy setup and type annotation guidelines
- **Architecture & API**
  - [Architecture](./docs/ARCHITECTURE.md) - System design and components
  - [API Reference](./docs/API.md) - Complete API documentation
  - [Database](./docs/DATABASE.md) - Database schema and queries
- **Configuration**
  - [Configuration Guide](./docs/CONFIGURATION.md) - Environment variables and settings
  - [Feature Flags](./docs/FEATURE_FLAGS.md) - Feature flag system and management
- **Deployment & Operations**
  - [Deployment Guide](./docs/DEPLOYMENT.md) - Production deployment
  - [Privacy Filter](./docs/PRIVACY_FILTER.md) - PII detection system

## 🏗️ Architecture

```
┌─────────────┐
│   React UI  │ (TypeScript + TailwindCSS)
└──────┬──────┘
       │ HTTP/SSE
┌──────▼──────┐
│  FastAPI    │ (Python 3.11 + async)
│  Backend    │
└──────┬──────┘
       │
       ├─────────────┐
       │             │
┌──────▼──────┐ ┌───▼────────┐
│ OVH AI      │ │ PostgreSQL │
│ Endpoints   │ │ Database   │
└─────────────┘ └────────────┘
```

## 🔧 Technology Stack

**Backend:**
- FastAPI 0.115.6 - Modern async web framework
- Uvicorn 0.34.0 - ASGI server
- PostgreSQL - Production database
- Tesseract OCR - Text extraction
- spaCy NER - Privacy filtering
- OVH AI Endpoints - AI processing

**Frontend:**
- React 18.3.1 - UI framework
- TypeScript 5.7.3 - Type safety
- Vite 6.0.6 - Build tool
- TailwindCSS 3.4.17 - Styling
- Axios 1.7.9 - HTTP client

**Infrastructure:**
- Railway - Cloud platform
- Docker - Containerization
- nginx - Reverse proxy

## 🔐 Security & Privacy

- ✅ **No Data Retention** - Documents deleted after processing
- ✅ **EU-Based Processing** - OVH AI Endpoints in EU
- ✅ **PII Removal** - Automated privacy filtering
- ✅ **HTTPS Only** - Encrypted transport
- ✅ **CORS Protection** - Configurable origins
- ✅ **Input Validation** - Pydantic models

## 🏥 Medical Document Support

| Document Type | Description | Examples |
|---------------|-------------|----------|
| **ARZTBRIEF** | Doctor's letters | Discharge summaries, referrals |
| **BEFUNDBERICHT** | Medical reports | Radiology, pathology findings |
| **LABORWERTE** | Lab results | Blood tests, clinical chemistry |

## 🌍 Language Support

| Input | Output Translations |
|-------|---------------------|
| German (DE) | English, French, Spanish, Italian, Portuguese, Dutch, Polish |

## 📊 Processing Pipeline

1. **TEXT_EXTRACTION** - OCR preprocessing with Qwen Vision
2. **MEDICAL_VALIDATION** - Binary medical classification
3. **CLASSIFICATION** - Document type detection
4. **PII_PREPROCESSING** - Privacy filtering
5. **TRANSLATION** - Patient-friendly German
6. **FACT_CHECK** - Medical accuracy verification
7. **GRAMMAR_CHECK** - Language correction
8. **LANGUAGE_TRANSLATION** - Multi-language support
9. **FINAL_CHECK** - Quality assurance
10. **FORMATTING** - Markdown output

All steps are configurable via admin dashboard.

## 🛠️ Configuration

### Environment Variables

```bash
# Required
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token
OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1
USE_OVH_ONLY=true

# Optional
OVH_MAIN_MODEL=Meta-Llama-3_3-70B-Instruct
OVH_PREPROCESSING_MODEL=Mistral-Nemo-Instruct-2407
LOG_LEVEL=INFO
DATABASE_URL=postgresql://...  # Auto-configured on Railway
```

See [DEPLOYMENT.md](./docs/DEPLOYMENT.md) for complete reference.

## 📈 Performance

- **Processing Time**: 3-5 seconds average
- **Max File Size**: 50MB
- **Concurrent Requests**: Railway plan-dependent
- **Uptime**: 99.9% on Railway

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

## 🎯 Code Quality

DocTranslator maintains high code quality standards through automated tooling and CI/CD pipelines.

### Backend Quality Tools

- **Ruff** - Fast Python linter and formatter (1,451 issues auto-fixed)
- **MyPy** - Static type checking for Python
- **Bandit** - Security vulnerability scanning
- **pytest** - Unit and integration testing (60%+ coverage)
- **pip-audit** - Dependency vulnerability scanning

### Frontend Quality Tools

- **ESLint** - JavaScript/TypeScript linting
- **Prettier** - Code formatting
- **TypeScript** - Static type checking

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

Hooks automatically run on every commit:
- Ruff linting and formatting
- MyPy type checking
- Bandit security scanning
- JSON/YAML validation
- Secret detection (gitleaks)
- Trailing whitespace removal
- Conventional commit message validation

### CI/CD Pipeline

Every push and pull request triggers automated quality checks:

- ✅ **Backend Quality** - Ruff, MyPy, Bandit
- ✅ **Backend Tests** - pytest with PostgreSQL service
- ✅ **Frontend Quality** - ESLint, Prettier, TypeScript
- ✅ **Frontend Build** - Production build verification
- ✅ **Security Audit** - pip-audit and npm audit
- ✅ **Quality Gate** - All checks must pass for PR merge

See [CONTRIBUTING.md](./CONTRIBUTING.md) for code style guidelines.

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines.

**Quick Start:**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following our code style guidelines
4. Run quality checks: `pre-commit run --all-files`
5. Commit with conventional commits format
6. Push to your branch and open a Pull Request

All PRs must pass automated quality checks before merge.

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OVH Cloud](https://www.ovhcloud.com/) - AI Endpoints infrastructure
- [Railway](https://railway.app/) - Deployment platform
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - OCR engine
- [spaCy](https://spacy.io/) - NLP and NER
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [React](https://react.dev/) - Frontend framework

## 📞 Support

- 📖 [Documentation](./docs/README.md)
- 🐛 [Issues](https://github.com/your-repo/issues)
- 💬 [Discussions](https://github.com/your-repo/discussions)

## 🗺️ Roadmap

- [ ] Batch document processing
- [ ] Advanced analytics dashboard
- [ ] Multi-tenant support
- [ ] Custom model fine-tuning
- [ ] API authentication
- [ ] WebSocket real-time updates
- [ ] Mobile app

---

**Built with ❤️ for healthcare professionals and patients**
