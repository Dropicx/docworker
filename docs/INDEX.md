# DocTranslator Documentation

**GDPR-compliant medical document translation service** that transforms complex German medical documents into patient-friendly language in multiple languages.

---

## System Overview

DocTranslator is a production-grade medical document translation platform that:

1. **Accepts** medical documents (PDF, images, DOCX) in German
2. **Extracts** text using OCR (PaddleOCR/Tesseract)
3. **Removes** personally identifiable information (GDPR compliance)
4. **Translates** medical jargon into patient-friendly language
5. **Validates** medical accuracy through AI fact-checking
6. **Converts** to target language (EN, FR, ES, IT, PT, NL, PL)
7. **Delivers** clean, formatted Markdown output

### Infrastructure Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          RAILWAY (Frankfurt, EU)                         │
│                                                                          │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│   │ Frontend │   │ Backend  │   │  Worker  │   │   Beat   │            │
│   │ (React)  │   │ (FastAPI)│   │ (Celery) │   │(Scheduler)│           │
│   │ Port 80  │   │ Port 9122│   │          │   │          │            │
│   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘            │
│        │              │              │              │                   │
│        └──────────────┴──────────────┴──────────────┘                   │
│                              │                                          │
│                    ┌─────────┴─────────┐                               │
│                    │                   │                               │
│              ┌─────┴─────┐      ┌──────┴──────┐                        │
│              │PostgreSQL │      │    Redis    │                        │
│              │ (Database)│      │(Task Queue) │                        │
│              └───────────┘      └─────────────┘                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
     ┌─────────────────────────────┼─────────────────────────────┐
     │                    │                    │                 │
     ▼                    ▼                    ▼                 ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ MISTRAL AI     │ │ HETZNER PII    │ │ HETZNER OCR    │ │ OVH AI         │
│ (France, EU)   │ │ (Germany, EU)  │ │ (Germany, EU)  │ │ (EU)           │
│                │ │                │ │                │ │                │
│ mistral-ocr    │ │ spaCy NER +    │ │ PaddleOCR      │ │ Llama 3.3 70B  │
│ (Primary OCR)  │ │ Presidio +     │ │ (OCR Fallback) │ │ (Translation)  │
│                │ │ Custom Regex   │ │                │ │                │
│ mistral-large  │ │                │ │                │ │ Mistral Nemo   │
│ (Feedback AI)  │ │ 2x CPX32 HA    │ │ 2x CPX41 HA    │ │ (Preprocessing)│
│                │ │                │ │                │ │                │
│ Direct API     │ │                │ │                │ │ Qwen 2.5 VL 72B│
└────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘
```

---

## Quick Navigation

### Core Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Complete system architecture, components, data flow |
| [API.md](API.md) | REST API endpoint reference |
| [DATABASE.md](DATABASE.md) | Database schema and models |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment (Railway + Hetzner) |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Local development setup |

### Privacy & Security

| Document | Description |
|----------|-------------|
| [PRIVACY_FILTER.md](PRIVACY_FILTER.md) | PII removal system (GDPR compliance) |
| [DATA_RETENTION.md](DATA_RETENTION.md) | Data retention and privacy policy |
| [AUTHENTICATION_IMPLEMENTATION_SUMMARY.md](AUTHENTICATION_IMPLEMENTATION_SUMMARY.md) | Authentication system |

### Operations & Configuration

| Document | Description |
|----------|-------------|
| [CONFIGURATION.md](CONFIGURATION.md) | Environment variables reference |
| [WORKER_SCALING.md](WORKER_SCALING.md) | Celery worker scaling guide |
| [FEATURE_FLAGS.md](FEATURE_FLAGS.md) | Runtime feature toggles |
| [MONITORING_TROUBLESHOOTING.md](MONITORING_TROUBLESHOOTING.md) | Debugging and monitoring |

### User Guides

| Document | Description |
|----------|-------------|
| [PIPELINE_USER_GUIDE.md](PIPELINE_USER_GUIDE.md) | Creating and managing pipelines |
| [PIPELINE_VARIABLES.md](PIPELINE_VARIABLES.md) | Pipeline variable reference |
| [TESTING.md](TESTING.md) | Testing guide |

---

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Backend** | FastAPI | 0.120+ | Async REST API |
| **Frontend** | React + TypeScript | 18.3 / 5.9 | User interface |
| **Database** | PostgreSQL | 16 | Persistent storage |
| **ORM** | SQLAlchemy | 2.0 | Database abstraction |
| **Task Queue** | Celery + Redis | 5.4 / 7 | Background processing |
| **AI Provider (Translation)** | OVH AI Endpoints | - | LLM translation |
| **AI Provider (OCR/Feedback)** | Mistral AI (France) | - | OCR + analytics |
| **Main LLM** | Llama 3.3 70B | - | High-quality translation |
| **Fast LLM** | Mistral Nemo (OVH) | - | Quick preprocessing |
| **Vision LLM** | Qwen 2.5 VL 72B | - | OCR/image understanding |
| **Primary OCR** | Mistral OCR | - | `mistral-ocr-latest` |
| **Feedback Analysis** | Mistral Large | - | `mistral-large-latest` |
| **PII Detection** | spaCy + Presidio | 3.8 / 2.2 | GDPR compliance |
| **OCR Fallback** | PaddleOCR / Tesseract | - | Text extraction |
| **Deployment** | Railway + Hetzner | - | Multi-cloud hosting |

---

## Processing Pipeline

DocTranslator uses a 10-step modular pipeline:

| Step | Name | Description |
|------|------|-------------|
| 1 | `TEXT_EXTRACTION` | OCR/PDF text extraction |
| 2 | `MEDICAL_VALIDATION` | Verify document is medical |
| 3 | `CLASSIFICATION` | Detect document type |
| 4 | `PII_PREPROCESSING` | Remove personal information |
| 5 | `TRANSLATION` | Translate to patient-friendly German |
| 6 | `FACT_CHECK` | Verify medical accuracy |
| 7 | `GRAMMAR_CHECK` | Language correction |
| 8 | `LANGUAGE_TRANSLATION` | Convert to target language |
| 9 | `FINAL_CHECK` | Quality assurance |
| 10 | `FORMATTING` | Markdown output |

### Document Types

- **ARZTBRIEF** - Doctor's letters, discharge summaries
- **BEFUNDBERICHT** - Medical reports, diagnostic findings
- **LABORWERTE** - Laboratory results, blood tests

### Supported Languages

- **Input**: German (DE)
- **Output**: English (EN), French (FR), Spanish (ES), Italian (IT), Portuguese (PT), Dutch (NL), Polish (PL)

---

## GDPR Compliance

DocTranslator is designed with privacy-first principles:

| Feature | Implementation |
|---------|----------------|
| **PII Removal** | spaCy NER + Presidio + custom patterns |
| **Data Retention** | 24 hours (configurable to 0) |
| **EU Processing** | All infrastructure in EU |
| **Encryption** | At-rest (Fernet) + in-transit (TLS) |
| **Audit Trail** | Complete logging for compliance |
| **Cookie-Free** | No tracking cookies |

### PII Types Detected

- Names (German/English NER)
- Addresses (street, postal code, city)
- Phone numbers, fax, email
- Birthdates
- German Tax ID, Social Security
- Insurance numbers, Patient IDs
- Case/file reference numbers

### Medical Terms Protected

- 300+ anatomical/clinical terms
- 200+ medications
- 50+ medical eponyms (Parkinson, Alzheimer, etc.)
- Lab values, units, abbreviations

See [PRIVACY_FILTER.md](PRIVACY_FILTER.md) for complete details.

---

## External AI Services

### Mistral AI (France)

**Purpose**: Primary OCR engine and feedback analysis

**Services Used**:
- **Mistral OCR** (`mistral-ocr-latest`) - High-accuracy document text extraction
- **Mistral Large** (`mistral-large-latest`) - Feedback quality analysis

**Integration**:
- Direct API via `mistralai` Python SDK
- EU data processing (France)
- Requires `MISTRAL_API_KEY` from [console.mistral.ai](https://console.mistral.ai)

**Location**: `backend/app/services/mistral_client.py`, `backend/app/services/ocr_engine_manager.py`

---

## External Services (Hetzner)

### PII Service

**Purpose**: GDPR-compliant PII removal using spaCy + Presidio

**Infrastructure**:
- 2x CPX32 servers (4 vCPU, 8GB RAM)
- Load balancer with managed SSL
- Private network (10.1.0.0/16)

**Technologies**:
- spaCy `de_core_news_lg` + `en_core_web_lg`
- Microsoft Presidio analyzers
- Custom regex patterns for German identifiers

**Location**: `pii_service/` directory

### OCR Service

**Purpose**: PaddleOCR fallback when Mistral OCR is unavailable or for complex documents

**Infrastructure**:
- 2x CPX41 servers (8 vCPU, 16GB RAM)
- Load balancer with managed SSL
- Private network (10.0.0.0/16)

**Location**: `external_deployment/hetzner_paddleocr/`

---

## Cost Tracking

DocTranslator tracks AI token usage automatically:

- Per-call logging (input/output tokens)
- Dynamic pricing from database
- Cost breakdown by model and pipeline step
- No text content stored (lean database)

**Typical cost**: ~$0.005 per document (~half a cent)

---

## Getting Started

### For Users

1. Upload a medical document (PDF, JPG, PNG, DOCX)
2. Select target language
3. Wait for processing (typically 30-60 seconds)
4. Download translated document

### For Developers

```bash
# Clone repository
git clone https://github.com/Dropicx/doctranslator.git
cd doctranslator

# Start with Docker
docker-compose up -d

# Or manual setup
cd backend && pip install -r requirements.txt
cd frontend && npm install
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed setup.

### For Operators

- **Railway**: Main application (dev + production environments)
- **Hetzner**: External services (PII, OCR) via Terraform

See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment.

---

## Archive

Historical and implementation-specific documentation is in `docs/archive/`:

- Phase planning documents
- Implementation checklists
- Redis diagnostics
- Legacy privacy filter docs

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | Jan 2026 | Hetzner PII service, enhanced privacy filter, Presidio integration |
| 1.5 | Oct 2025 | Authentication system, cost tracking, feature flags |
| 1.0 | Aug 2025 | Initial release |

---

## Support

- **GitHub Issues**: [github.com/Dropicx/doctranslator/issues](https://github.com/Dropicx/doctranslator/issues)
- **Health Check**: `GET /health` endpoint
- **Documentation**: This `/docs` folder

---

*Last Updated: January 2026*
