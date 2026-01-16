# System Architecture

## Overview

DocTranslator is a **production-grade, microservices-based** medical document translation service built with cloud-native principles. The system uses:

- **FastAPI** backend for API orchestration
- **React + TypeScript** frontend for user interface
- **Celery** workers for background document processing
- **PostgreSQL** for persistent storage
- **Redis** for task queuing
- **Railway** (Frankfurt, EU) for main application hosting
- **Hetzner** (Germany, EU) for external PII and OCR fallback services
- **OVH AI Endpoints** (EU) for LLM translation
- **Mistral AI** (France, EU) for primary OCR and feedback analysis

All infrastructure is EU-based for GDPR compliance.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RAILWAY PLATFORM (Frankfurt, EU)                     │
│                                                                              │
│   ┌────────────────┐         ┌────────────────┐        ┌────────────────┐   │
│   │   Frontend     │         │    Backend     │        │     Beat       │   │
│   │   (nginx)      │────────▶│   (FastAPI)    │        │  (Scheduler)   │   │
│   │   Port 80      │  /api   │   Port 9122    │        │                │   │
│   │                │         │                │        │                │   │
│   └────────────────┘         └───────┬────────┘        └────────────────┘   │
│                                      │                                       │
│           ┌──────────────────────────┼───────────────────────┐              │
│           │                          │                       │              │
│           ▼                          ▼                       ▼              │
│   ┌────────────────┐       ┌────────────────┐       ┌────────────────┐     │
│   │   PostgreSQL   │       │     Redis      │       │     Worker     │     │
│   │   (Database)   │       │   (Broker)     │◀──────│   (Celery)     │     │
│   │                │       │                │       │                │     │
│   └────────────────┘       └────────────────┘       └────────┬───────┘     │
│                                                               │             │
└───────────────────────────────────────────────────────────────┼─────────────┘
                                                                │
               ┌─────────────────────────────────────────────┼───────────────────────────────────┐
               │                    │                         │                                   │
               ▼                    ▼                         ▼                                   ▼
   ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐     ┌─────────────────────┐
   │    MISTRAL AI       │  │    HETZNER PII      │  │   HETZNER OCR       │     │    OVH AI           │
   │    (France, EU)     │  │    (Germany, EU)    │  │   (Germany, EU)     │     │    (EU)             │
   │                     │  │                     │  │                     │     │                     │
   │  mistral-ocr-latest │  │  ┌───────────────┐  │  │  ┌───────────────┐  │     │  Llama 3.3 70B      │
   │  (Primary OCR)      │  │  │ spaCy NER     │  │  │  │ PaddleOCR     │  │     │  (Translation)      │
   │                     │  │  │ de_core_news  │  │  │  │               │  │     │                     │
   │  mistral-large      │  │  │ en_core_web   │  │  │  │ German OCR    │  │     │  Mistral Nemo       │
   │  (Feedback Analysis)│  │  └───────────────┘  │  │  │ Table detect  │  │     │  (Preprocessing)    │
   │                     │  │  ┌───────────────┐  │  │  └───────────────┘  │     │                     │
   │  Direct API via     │  │  │ Presidio      │  │  │                     │     │  Qwen 2.5 VL 72B    │
   │  mistralai SDK      │  │  │ IBAN, CC,     │  │  │  Load Balancer      │     │  (Vision/OCR)       │
   │                     │  │  │ Phone, Email  │  │  │  2x CPX41 servers   │     │                     │
   └─────────────────────┘  │  └───────────────┘  │  │  Terraform-managed  │     │  EU Infrastructure  │
                            │  ┌───────────────┐  │  │                     │     │                     │
                            │  │ Custom Regex  │  │  └─────────────────────┘     └─────────────────────┘
                            │  │ German IDs    │  │
                            │  │ Tax, SSN, etc │  │
                            │  └───────────────┘  │
                            │                     │
                            │  Load Balancer      │
                            │  2x CPX32 servers   │
                            │  Terraform-managed  │
                            │                     │
                            └─────────────────────┘
```

---

## Service Components

### 1. Frontend Service (nginx + React)

**Location**: `/frontend`
**Port**: 80 (public via Railway)
**Technology**: React 18.3 + TypeScript 5.9 + Vite 6.0 + TailwindCSS 3.4

#### Responsibilities

- Serve React single-page application
- Reverse proxy API requests to backend
- Handle client-side routing
- Provide health check endpoint

#### Key Components

| Component | Purpose |
|-----------|---------|
| `App.tsx` | Main application with state machine flow |
| `FileUpload.tsx` | Drag-and-drop document upload |
| `ProcessingStatus.tsx` | Real-time progress display |
| `TranslationResult.tsx` | Final translation with export (PDF/MD) |
| `LanguageSelector.tsx` | Target language selection |
| `FeedbackWidget.tsx` | User feedback collection |
| `Settings.tsx` | Admin configuration dashboard |

#### nginx Configuration

```nginx
server {
    listen 80;

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend.railway.internal:9122;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### 2. Backend Service (FastAPI)

**Location**: `/backend`
**Port**: 9122 (internal)
**Technology**: FastAPI 0.120+ + Uvicorn + SQLAlchemy 2.0 + Pydantic 2.0

#### Responsibilities

- REST API for document processing
- Pipeline orchestration and job management
- Database access and ORM
- Health monitoring and metrics
- Authentication and authorization

#### Directory Structure

```
backend/app/
├── main.py                  # FastAPI application, lifespan, middleware
├── routers/                 # API endpoints
│   ├── upload.py            # POST /api/upload
│   ├── process.py           # GET /api/process/{id}
│   ├── health.py            # GET /health
│   ├── auth.py              # Authentication
│   ├── users.py             # User management
│   ├── feedback.py          # Feedback collection
│   ├── modular_pipeline.py  # Pipeline configuration
│   ├── admin/config.py      # Admin settings
│   ├── cost_statistics.py   # Cost tracking
│   └── privacy_metrics.py   # PII filter metrics
├── services/                # Business logic
│   ├── modular_pipeline_executor.py  # Pipeline execution
│   ├── privacy_filter_advanced.py    # PII removal (fallback)
│   ├── ovh_client.py                 # OVH AI client
│   ├── ai_cost_tracker.py            # Token/cost logging
│   ├── pii_service_client.py         # Hetzner PII client
│   ├── ocr_engine_manager.py         # OCR selection
│   ├── text_extractor_ocr.py         # OCR extraction
│   ├── file_quality_detector.py      # Image quality analysis
│   ├── file_validator.py             # Upload validation
│   ├── celery_client.py              # Task submission
│   └── cache_service.py              # Redis caching
├── repositories/            # Data access layer
│   ├── base_repository.py
│   ├── pipeline_job_repository.py
│   ├── pipeline_step_repository.py
│   └── system_settings_repository.py
├── database/                # Database layer
│   ├── connection.py        # Session management
│   ├── models.py            # SQLAlchemy models
│   ├── modular_pipeline_models.py
│   ├── auth_models.py
│   └── init_db.py           # Schema initialization
└── core/                    # Core utilities
    ├── config.py            # Pydantic settings
    ├── security.py          # JWT, password hashing
    ├── dependencies.py      # DI providers
    ├── permissions.py       # RBAC
    ├── encryption.py        # Fernet encryption
    ├── circuit_breaker.py   # External service resilience
    └── feature_flags.py     # Runtime toggles
```

#### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload document, return processing_id |
| `/api/process/{id}` | GET | Check processing status |
| `/api/process/{id}/result` | GET | Get final translation |
| `/api/process/languages` | GET | List target languages |
| `/health` | GET | Service health check |
| `/health/detailed` | GET | Detailed health with dependencies |
| `/api/auth/login` | POST | User authentication |
| `/api/settings/pipeline-steps` | GET/PUT | Pipeline configuration |
| `/api/cost/summary` | GET | Token usage and costs |

---

### 3. Worker Service (Celery)

**Location**: `/worker`
**Technology**: Celery 5.4 + Redis (broker)
**Concurrency**: 2-10 workers (configurable)

#### Responsibilities

- Background document processing
- Execute pipeline steps asynchronously
- Manage long-running AI tasks
- Database updates for job status
- Cost and token logging

#### Directory Structure

```
worker/
├── worker.py                # Celery app configuration
├── config.py                # Worker settings
├── tasks/
│   ├── document_processing.py   # Main processing task
│   ├── feedback_analysis.py     # Feedback quality analysis
│   └── scheduled_tasks.py       # Periodic cleanup
└── requirements.txt
```

#### Task Flow

```
1. Backend enqueues task → Redis
2. Worker pulls task from queue
3. Worker loads job from PostgreSQL
4. Worker decrypts file content
5. Worker executes 10-step pipeline:
   └─▶ TEXT_EXTRACTION (OCR)
   └─▶ MEDICAL_VALIDATION
   └─▶ CLASSIFICATION
   └─▶ PII_PREPROCESSING (→ Hetzner PII Service)
   └─▶ TRANSLATION (→ OVH AI)
   └─▶ FACT_CHECK (→ OVH AI)
   └─▶ GRAMMAR_CHECK (→ OVH AI)
   └─▶ LANGUAGE_TRANSLATION (→ OVH AI)
   └─▶ FINAL_CHECK (→ OVH AI)
   └─▶ FORMATTING
6. Worker logs token usage and cost
7. Worker saves result to PostgreSQL
8. Frontend polls and receives result
```

#### Configuration

```python
CELERY_CONFIG = {
    "broker_url": REDIS_URL,
    "result_backend": REDIS_URL,
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "timezone": "Europe/Berlin",
    "worker_concurrency": 2,
    "worker_max_tasks_per_child": 50,
    "task_acks_late": True,
    "worker_prefetch_multiplier": 1,
    "task_soft_time_limit": 600,
    "task_time_limit": 3600,
}
```

---

### 4. Mistral AI Service (France)

**Platform**: Mistral AI (France, EU)
**Protocol**: Native Mistral API
**SDK**: `mistralai` Python package

#### Purpose

Mistral AI provides two critical services:

1. **Primary OCR Engine** - Document text extraction using `mistral-ocr-latest`
2. **Feedback Analysis** - User feedback quality analysis using `mistral-large-latest`

#### Available Models

| Model | Model ID | Purpose |
|-------|----------|---------|
| **Mistral OCR** | `mistral-ocr-latest` | Document text extraction |
| **Mistral Large** | `mistral-large-latest` | Feedback analysis, complex reasoning |

#### Integration

```python
# Mistral client configuration
from mistralai import Mistral

client = Mistral(api_key=settings.MISTRAL_API_KEY)

# OCR extraction
async def extract_with_mistral_ocr(image_data: bytes) -> str:
    response = await client.chat.complete_async(
        model="mistral-ocr-latest",
        messages=[{"role": "user", "content": image_content}]
    )
    return response.choices[0].message.content

# Feedback analysis
async def analyze_feedback(text: str) -> dict:
    response = await client.chat.complete_async(
        model="mistral-large-latest",
        messages=[{"role": "user", "content": analysis_prompt}]
    )
    return parse_analysis(response)
```

#### Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `MISTRAL_API_KEY` | API key from console.mistral.ai | Yes |

**Location**: `backend/app/services/mistral_client.py`

---

### 5. Hetzner PII Service

**Location**: `/pii_service`
**Infrastructure**: 2x CPX32 (4 vCPU, 8GB RAM) + Load Balancer
**Network**: Private (10.1.0.0/16)
**Port**: 9125 (HTTPS via LB)

#### Purpose

GDPR-compliant PII removal using a combination of:

1. **spaCy NER** - Named entity recognition for names, locations, organizations
2. **Microsoft Presidio** - IBAN, credit cards, phone numbers, emails, IP addresses
3. **Custom regex patterns** - German-specific identifiers (Tax ID, Social Security, insurance numbers)

#### Technology Stack

| Component | Purpose |
|-----------|---------|
| spaCy `de_core_news_lg` | German NER model (PER, LOC, ORG) |
| spaCy `en_core_web_lg` | English NER model (PERSON, GPE, ORG) |
| Presidio Analyzer | Enhanced PII detection (IBAN, CC, etc.) |
| FastAPI | REST API framework |
| Uvicorn | ASGI server |

#### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health with model status |
| `/remove-pii` | POST | Remove PII from text |
| `/remove-pii/batch` | POST | Batch PII removal |

#### Request/Response

```json
// POST /remove-pii
{
  "text": "Patient Max Mustermann, geb. 15.03.1980...",
  "language": "de",
  "custom_protection_terms": ["Parkinson", "Aspirin"]
}

// Response
{
  "cleaned_text": "Patient [NAME], geb. [BIRTHDATE]...",
  "processing_time_ms": 45.2,
  "metadata": {
    "entities_detected": 5,
    "pii_types": ["doctor_title_name", "birthdate", "address"]
  }
}
```

#### PII Types Detected

| Category | Types |
|----------|-------|
| **Names** | Doctor titles, honorifics, patient names |
| **Addresses** | Street, PLZ, city |
| **Contact** | Phone, fax, email |
| **IDs** | Tax ID, Social Security, insurance, patient ID |
| **Financial** | IBAN, credit card |
| **Dates** | Birthdates, standalone dates |
| **Other** | IP addresses, URLs |

#### Medical Term Protection

- **300+ medical terms** preserved (anatomy, conditions, procedures)
- **200+ medications** in drug database
- **50+ medical eponyms** (Parkinson, Alzheimer, etc.)
- German declension support (nächtliche → nächtlich)

---

### 6. Hetzner OCR Service (PaddleOCR)

**Location**: `/external_deployment/hetzner_paddleocr`
**Infrastructure**: 2x CPX41 (8 vCPU, 16GB RAM) + Load Balancer
**Network**: Private (10.0.0.0/16)
**Port**: 9123 (public HTTPS via LB), 9124 (internal service)

#### Purpose

OCR fallback service when Mistral OCR is unavailable or for complex documents requiring specialized table detection.

#### Features

- German language OCR optimized
- Table detection and extraction
- Markdown table conversion
- High-resolution image support

#### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health |
| `/extract` | POST | Extract text from image |

---

### 7. PostgreSQL Database

**Platform**: Railway managed
**Version**: PostgreSQL 16

#### Key Tables

| Table | Purpose |
|-------|---------|
| `pipeline_jobs` | Document processing jobs with encrypted file content |
| `dynamic_pipeline_steps` | User-configurable pipeline steps |
| `pipeline_step_executions` | Individual step execution records |
| `ai_interaction_logs` | Token usage and cost tracking |
| `system_settings` | Application configuration |
| `users` | User accounts |
| `user_roles` | Role-based access control |
| `api_keys` | API authentication tokens |
| `audit_logs` | Security and compliance audit trail |
| `feedback_responses` | User feedback with GDPR compliance |
| `ocr_configuration` | OCR engine selection and settings |
| `available_models` | AI model registry with pricing |
| `document_classes` | Custom document type definitions |

See [DATABASE.md](DATABASE.md) for complete schema.

---

### 8. Redis

**Platform**: Railway managed
**Version**: Redis 7

#### Usage

- Celery task broker
- Celery result backend
- Configuration caching (10-minute TTL)
- Session storage (optional)

---

### 9. OVH AI Endpoints

**Platform**: OVH AI Endpoints (EU)
**Protocol**: OpenAI-compatible API

#### Available Models

| Model | Purpose | Usage |
|-------|---------|-------|
| **Llama 3.3 70B** | High-quality translation | Main translation, fact-check |
| **Mistral Nemo** | Fast preprocessing | Validation, classification |
| **Qwen 2.5 VL 72B** | Vision/OCR | Image understanding |

#### Integration

```python
# OVH client configuration
client = AsyncOpenAI(
    api_key=settings.OVH_AI_TOKEN,
    base_url="https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"
)

# Smart model selection
def select_model(prompt_type: str) -> str:
    if prompt_type in ["VALIDATION", "CLASSIFICATION"]:
        return "Mistral-Nemo-Instruct-2407"  # Fast
    return "Meta-Llama-3.3-70B-Instruct"     # Quality
```

---

## Data Flow

### Document Upload Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  User    │───▶│ Frontend │───▶│ Backend  │───▶│ Database │
│          │    │          │    │          │    │          │
│ Upload   │    │ POST     │    │ Validate │    │ Create   │
│ file     │    │ /upload  │    │ + Queue  │    │ Job      │
└──────────┘    └──────────┘    └────┬─────┘    └──────────┘
                                     │
                                     ▼
                               ┌──────────┐
                               │  Redis   │
                               │  Queue   │
                               └──────────┘
```

### Document Processing Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Redis   │───▶│  Worker  │───▶│ Hetzner  │───▶│ OVH AI   │
│  Queue   │    │          │    │ PII Svc  │    │ Endpoints│
│          │    │ Pull job │    │          │    │          │
│          │    │ Execute  │    │ Remove   │    │ Translate│
└──────────┘    │ Pipeline │    │ PII      │    │ Document │
                └────┬─────┘    └──────────┘    └────┬─────┘
                     │                               │
                     ▼                               │
               ┌──────────┐                         │
               │ Database │◀────────────────────────┘
               │          │
               │ Save     │
               │ Result   │
               └──────────┘
```

### OCR Engine Selection

```
Worker calls OCREngineManager.extract_text()
     │
     ▼
Load OCRConfigurationDB
     │
     ├─▶ MISTRAL_OCR → Mistral AI (primary, high accuracy)
     │
     ├─▶ PADDLEOCR → Hetzner service (fallback, tables)
     │
     ├─▶ TESSERACT → Local pytesseract (fast, basic)
     │
     ├─▶ VISION_LLM → OVH Qwen (complex documents)
     │
     └─▶ HYBRID → Intelligent routing based on quality
```

---

## Security Architecture

### Data Protection

| Measure | Implementation |
|---------|----------------|
| **Encryption at rest** | Fernet AES-128 for file content |
| **Encryption in transit** | TLS 1.3 (Railway automatic) |
| **PII removal** | Before any AI processing |
| **Data retention** | 24 hours default (configurable to 0) |
| **No disk storage** | In-memory processing only |

### GDPR Compliance

| Requirement | Implementation |
|-------------|----------------|
| **EU processing** | All services in EU (Railway Frankfurt, Hetzner Germany, OVH EU) |
| **Data minimization** | Only necessary data collected |
| **Purpose limitation** | Data used only for translation |
| **Right to erasure** | Automatic deletion after processing |
| **Audit trail** | Complete logging for compliance |

### Application Security

| Protection | Implementation |
|------------|----------------|
| **Authentication** | JWT tokens (15-min access, 7-day refresh) |
| **Authorization** | Role-based access control (ADMIN, USER, VIEWER) |
| **Password security** | bcrypt (12 rounds) |
| **Rate limiting** | 5 uploads/minute (SlowAPI) |
| **Input validation** | Pydantic models |
| **SQL injection** | SQLAlchemy parameterized queries |
| **XSS** | React automatic escaping |
| **CORS** | Configurable allowed origins |
| **Security headers** | CSP, HSTS, X-Frame-Options |

### Account Security

- Account lockout after 5 failed attempts
- 15-minute lockout duration
- Password complexity requirements
- Token revocation support

---

## Performance

### Backend Optimizations

- **Async everything**: FastAPI async handlers, httpx async client
- **Connection pooling**: PostgreSQL pool (20 connections, 40 overflow)
- **Streaming responses**: Real-time AI output
- **Lazy loading**: On-demand model initialization

### Worker Optimizations

- **Prefetch multiplier**: 1 (one task at a time)
- **Max tasks per child**: 50 (prevents memory leaks)
- **Late acknowledgment**: Tasks acknowledged after completion
- **Configurable concurrency**: 2-10 workers

### Frontend Optimizations

- **Code splitting**: Route-based lazy loading
- **Asset minification**: Vite production build
- **Caching**: nginx cache headers
- **Compression**: gzip enabled

### PII Service Optimizations

- **Dual-path filtering**: Fast regex (10-20ms) or slow NER (100-120ms)
- **Model caching**: spaCy models loaded once at startup
- **Batch support**: Process multiple texts in one request

---

## Resilience

### Circuit Breaker

External service calls (OVH, Hetzner) use circuit breaker pattern:

```python
@circuit_breaker(
    failure_threshold=5,
    recovery_timeout=60,
    fallback=local_fallback
)
async def call_external_service():
    ...
```

### Retry Logic

- **AI calls**: 3 retries with exponential backoff
- **Database**: Connection retry on transient failures
- **Worker tasks**: Configurable retry count

### Fallbacks

| Service | Primary | Fallback |
|---------|---------|----------|
| PII | Hetzner spaCy | Local privacy_filter_advanced |
| OCR | Mistral OCR | PaddleOCR → Tesseract → Vision LLM |
| AI (Translation) | Llama 3.3 | Mistral Nemo (degraded) |
| AI (Feedback) | Mistral Large | Local analysis (degraded) |

### Health Checks

- Backend: `/health` with dependency checks
- Worker: Celery heartbeat
- PII Service: `/health` with model status
- OCR Service: `/health` with PaddleOCR status

---

## Monitoring

### Health Endpoints

```bash
# Backend
curl https://app.railway.app/health
curl https://app.railway.app/health/detailed

# PII Service
curl https://pii.domain.de/health

# OCR Service
curl https://ocr.domain.de/health
```

### Logging

- **Format**: Structured JSON
- **Levels**: DEBUG, INFO, WARNING, ERROR
- **Output**: stdout (Railway captures)
- **Audit**: Separate audit log for compliance

### Metrics

- Processing success/failure rate
- Average processing time per step
- Token usage by model
- Cost per document
- PII detection statistics
- Queue length and wait time

---

## Scalability

### Horizontal Scaling

| Component | Scale Method |
|-----------|--------------|
| Backend | Add Railway instances |
| Worker | Increase concurrency or add instances |
| PII Service | Add Hetzner servers (Terraform) |
| OCR Service | Add Hetzner servers (Terraform) |
| Database | Railway managed replication |
| Redis | Railway managed clustering |

### Vertical Scaling

| Component | Resources |
|-----------|-----------|
| Backend | ~200MB RAM baseline |
| Worker | ~300MB RAM per task |
| PII Service | ~2GB RAM (spaCy models) |
| OCR Service | ~1GB RAM (PaddleOCR) |

### Limits

| Limit | Value |
|-------|-------|
| Max file size | 50MB |
| Worker concurrency | 2-10 |
| Database connections | 20 (pool) |
| Rate limit | 5 uploads/minute |

---

## Infrastructure Management

### Railway

- **Environments**: dev, production
- **Auto-deploy**: Push to main/dev branches
- **Variables**: Per-environment configuration
- **Domains**: Custom domain support

### Hetzner (Terraform)

```hcl
# PII Service
resource "hcloud_server" "pii" {
  count       = 2
  server_type = "cpx32"  # 4 vCPU, 8GB RAM
  location    = "fsn1"   # Falkenstein, Germany
}

# OCR Service
resource "hcloud_server" "ocr" {
  count       = 2
  server_type = "cpx41"  # 8 vCPU, 16GB RAM
  location    = "fsn1"
}
```

Deploy commands:
```bash
cd external_deployment/hetzner_pii/terraform
terraform init
terraform apply
```

---

*Last Updated: January 2026*
