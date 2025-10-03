# System Architecture

## Overview

DocTranslator is a **microservices-based** medical document translation service built with modern cloud-native principles. The system uses FastAPI backend, React TypeScript frontend, Celery worker for background processing, and Railway deployment with IPv6 internal networking.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     Railway Platform (IPv6)                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────┐         ┌────────────────┐                  │
│  │   Frontend     │         │    Backend     │                  │
│  │   (nginx)      │────────▶│   (FastAPI)    │                  │
│  │   Port 8080    │  /api   │   Port 9122    │                  │
│  │                │         │   Listen: ::   │                  │
│  └────────────────┘         └───────┬────────┘                  │
│                                     │                            │
│           ┌─────────────────────────┼────────────────┐           │
│           │                         │                │           │
│           ▼                         ▼                ▼           │
│  ┌────────────────┐       ┌────────────────┐  ┌──────────────┐ │
│  │  PaddleOCR     │       │   PostgreSQL   │  │    Redis     │ │
│  │  (FastAPI)     │       │   (Database)   │  │   (Broker)   │ │
│  │  Port 9123     │       │                │  │              │ │
│  │  Listen: ::    │       └────────────────┘  └──────┬───────┘ │
│  └────────────────┘                                   │         │
│                                                        │         │
│                                              ┌─────────▼───────┐ │
│                                              │     Worker      │ │
│                                              │    (Celery)     │ │
│                                              │                 │ │
│                                              └─────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                   ┌────────────────────────┐
                   │  OVH AI Endpoints      │
                   │  (Llama 3.3 70B)       │
                   │  (EU Infrastructure)   │
                   └────────────────────────┘
```

## Technology Stack

### Backend Services
- **FastAPI** 0.115.6 - Modern async Python web framework
- **Uvicorn** 0.34.0 - ASGI server with async support
- **Celery** 5.4.0 - Distributed task queue for background processing
- **Redis** 5.0.0 - Message broker and result backend
- **PostgreSQL** - Production database with SQLAlchemy ORM
- **httpx** 0.28.1 - Async HTTP client for microservice communication

### OCR & Document Processing
- **Tesseract OCR** - Fast local OCR engine (C++ native)
- **PaddleOCR** - GPU/CPU-capable OCR microservice
- **pytesseract** 0.3.13 - Python wrapper for Tesseract
- **pdf2image** 1.17.0 - PDF to image conversion using poppler
- **PyPDF2** 3.0.1 - Direct PDF text extraction
- **pdfplumber** 0.11.5 - Advanced PDF table/text parsing
- **Pillow** 11.1.0 - Image processing and manipulation

### AI & NLP
- **OVH AI Endpoints** - Managed LLM hosting (EU-based)
  - Meta-Llama-3.3-70B-Instruct (main processing)
  - Mistral-Nemo-Instruct-2407 (preprocessing)
  - Qwen2-VL-72B-Instruct (vision/OCR)
- **OpenAI Python SDK** 1.59.2 - Compatible API client
- **spaCy** 3.8.3 - NLP library for PII detection
  - en_core_web_sm (English model)
  - de_core_news_sm (German model)

### Frontend
- **React** 18.3.1 - Component-based UI library
- **TypeScript** 5.7.3 - Type-safe JavaScript
- **Vite** 6.0.6 - Fast build tool and dev server
- **TailwindCSS** 3.4.17 - Utility-first CSS framework
- **React Router** 6.30.1 - Client-side routing
- **Axios** 1.7.9 - Promise-based HTTP client
- **react-markdown** - Markdown rendering
- **Lucide React** - Icon library

### Infrastructure
- **Railway** - Cloud platform with IPv6 networking
- **Docker** - Containerization with multi-stage builds
- **nginx** - Reverse proxy and static file serving
- **PostgreSQL** - Relational database
- **Redis** - In-memory data store and message broker

## Service Components

### 1. Frontend Service (nginx + React)

**Port**: 8080 (public)
**Technology**: React 18 + TypeScript + nginx

#### Responsibilities
- Serve static React application
- Reverse proxy API requests to backend
- Handle client-side routing
- Provide health check endpoint

#### nginx Configuration
```nginx
server {
    listen 8080;

    # Serve React app
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to backend (IPv6 internal)
    location /api/ {
        proxy_pass http://doctranslator-backend.railway.internal:9122;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Key Features**:
- Gzip compression for assets
- Cache headers for static files
- React Router support
- Health check endpoint

**Location**: `/frontend`

---

### 2. Backend Service (FastAPI)

**Port**: 9122 (internal)
**Listen Address**: `::` (IPv6 dual-stack)
**Technology**: FastAPI + Uvicorn

#### Responsibilities
- REST API endpoints for document processing
- OCR engine management and selection
- Pipeline orchestration
- Database management
- Health monitoring

#### Key Endpoints
- `POST /api/upload` - Upload and queue document
- `GET /api/processing/{id}` - Check processing status
- `GET /api/pipeline/ocr-engines` - List available OCR engines
- `GET /api/health` - Service health check

#### Internal Architecture
```
backend/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── routers/                   # API endpoints
│   │   ├── upload.py              # Document upload
│   │   ├── processing.py          # Status queries
│   │   ├── health.py              # Health checks
│   │   └── settings.py            # Configuration
│   ├── services/                  # Business logic
│   │   ├── ocr_engine_manager.py  # OCR selection
│   │   ├── hybrid_text_extractor.py # Text extraction
│   │   ├── ovh_client.py          # AI integration
│   │   └── privacy_filter_advanced.py # PII removal
│   └── database/                  # Database layer
│       ├── connection.py          # DB session management
│       ├── modular_pipeline_models.py # SQLAlchemy models
│       └── init_db.py             # Schema initialization
```

#### IPv6 Configuration
Backend listens on `::` (IPv6 any address) to accept connections from:
- Frontend nginx (internal proxy)
- PaddleOCR service (health checks)
- Worker (database access)

```python
# Command in Dockerfile
uvicorn app.main:app --host :: --port 9122
```

**Location**: `/backend`

---

### 3. Worker Service (Celery)

**Technology**: Celery 5.4.0 + Redis
**Listen**: N/A (client-only, connects to Redis)

#### Responsibilities
- Background document processing
- Execute pipeline steps asynchronously
- Manage long-running AI tasks
- Database updates for job status

#### Architecture
```
worker/
├── worker.py                      # Celery app configuration
└── tasks/
    ├── document_processing.py     # Main processing task
    └── scheduled_tasks.py         # Periodic cleanup tasks
```

#### Task Flow
```
1. Backend enqueues task to Redis
2. Worker pulls task from Redis queue
3. Worker loads job from PostgreSQL
4. Worker executes pipeline:
   - OCR text extraction
   - AI processing steps
   - PII filtering
   - Translation
5. Worker saves results to PostgreSQL
6. Worker updates job status
```

#### Configuration
- **Concurrency**: 2 workers (configurable)
- **Max tasks per child**: 50 (prevents memory leaks)
- **Task acknowledgment**: Late (after completion)
- **Prefetch multiplier**: 1 (one task at a time)
- **Broker**: Redis
- **Result backend**: Redis

#### Communication
Worker is purely a client - it **does not listen on any port**:
- Connects **TO** Redis for task queue
- Connects **TO** PostgreSQL for data
- Connects **TO** PaddleOCR service for OCR
- Connects **TO** OVH AI Endpoints for LLM processing

**Location**: `/worker`

---

### 4. PaddleOCR Service (FastAPI)

**Port**: 9123 (internal)
**Listen Address**: `::` (IPv6 dual-stack)
**Technology**: FastAPI + PaddleOCR

#### Responsibilities
- OCR text extraction from images
- Standalone microservice for scalability
- Alternative to Tesseract for complex documents

#### Endpoints
- `GET /health` - Service health and availability
- `POST /extract` - Extract text from uploaded image
- `GET /` - Service information

#### Internal Architecture
```
paddleocr_service/
├── app/
│   └── main.py                    # FastAPI app with PaddleOCR
├── entrypoint.sh                  # Startup script
└── requirements.txt               # Dependencies
```

#### OCR Configuration
```python
paddle_ocr = PaddleOCR(
    use_angle_cls=True,   # Text angle classification
    lang='german',        # German language support
    use_gpu=False,        # CPU mode (Railway default)
    show_log=False        # Reduce console noise
)
```

#### IPv6 Configuration
**Critical**: PaddleOCR must listen on `::` for Railway internal networking:

```bash
# entrypoint.sh
uvicorn app.main:app --host :: --port 9123
```

**Why IPv6 is required**:
- Railway internal networking uses IPv6
- Listening on `0.0.0.0` (IPv4 only) causes "Connection refused"
- `::` listens on both IPv4 and IPv6

#### Health Check Response
```json
{
  "status": "healthy",
  "service": "PaddleOCR Microservice",
  "paddleocr_available": true,
  "version": "1.0.0"
}
```

**Location**: `/paddleocr_service`

---

### 5. Redis Service

**Port**: 6379 (internal)
**Technology**: Redis (managed by Railway)

#### Responsibilities
- Celery task queue (broker)
- Celery result backend
- Worker coordination

#### Usage
```
Backend → Redis (enqueue task)
Worker → Redis (pull task)
Worker → Redis (push result)
Backend → Redis (check status)
```

#### Configuration
Railway auto-provides:
- `REDIS_URL` environment variable
- Automatic backups
- High availability

---

### 6. PostgreSQL Database

**Port**: 5432 (internal)
**Technology**: PostgreSQL (managed by Railway)

#### Responsibilities
- Pipeline configuration storage
- Job tracking and audit logging
- System settings
- Prompt templates

#### Schema
```sql
-- Pipeline Jobs
CREATE TABLE pipeline_jobs (
    job_id UUID PRIMARY KEY,
    processing_id UUID UNIQUE,
    filename VARCHAR(255),
    file_type VARCHAR(50),
    file_size INTEGER,
    file_content BYTEA,              -- Binary file storage
    status VARCHAR(50),
    progress_percent INTEGER,
    pipeline_config JSONB,           -- Snapshot of pipeline at job time
    ocr_config JSONB,                -- Snapshot of OCR config
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- OCR Configuration
CREATE TABLE ocr_configuration (
    id SERIAL PRIMARY KEY,
    selected_engine VARCHAR(50),     -- TESSERACT, PADDLEOCR, VISION_LLM, HYBRID
    tesseract_config JSONB,
    paddleocr_config JSONB,
    vision_llm_config JSONB,
    hybrid_config JSONB
);

-- Pipeline Steps
CREATE TABLE universal_pipeline_steps (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    order INTEGER,
    enabled BOOLEAN,
    prompt_template TEXT,
    selected_model_id VARCHAR(100),
    document_class_id INTEGER,
    is_branching_step BOOLEAN,
    branching_field VARCHAR(100)
);
```

See [DATABASE.md](./DATABASE.md) for complete schema.

---

## Data Flow

### Document Upload Flow

```
1. User uploads file in React UI
   ↓
2. POST /api/upload (Frontend → Backend)
   ↓
3. Backend validates file
   ↓
4. Backend creates PipelineJobDB record
   - Stores file_content as BYTEA
   - Captures pipeline_config snapshot
   - Captures ocr_config snapshot
   ↓
5. Backend enqueues task to Redis
   - Task: process_medical_document.delay(processing_id)
   ↓
6. Backend returns processing_id to frontend
   ↓
7. Frontend polls GET /api/processing/{id}
```

### Worker Processing Flow

```
1. Worker pulls task from Redis queue
   ↓
2. Worker loads PipelineJobDB from PostgreSQL
   - Reads file_content (BYTEA)
   - Reads pipeline_config snapshot
   - Reads ocr_config snapshot
   ↓
3. Worker executes OCR
   - OCREngineManager selects engine
   - Calls PaddleOCR service if selected
   - Falls back to Tesseract or Vision LLM
   ↓
4. Worker executes pipeline steps (from snapshot)
   - TEXT_EXTRACTION
   - MEDICAL_VALIDATION
   - CLASSIFICATION
   - PII_PREPROCESSING (spaCy NER)
   - TRANSLATION (OVH AI Endpoints)
   - FACT_CHECK
   - GRAMMAR_CHECK
   - LANGUAGE_TRANSLATION
   - FINAL_CHECK
   - FORMATTING
   ↓
5. Worker updates PipelineJobDB
   - progress_percent (0-100)
   - status (PROCESSING → COMPLETED)
   - result_data (JSONB)
   ↓
6. Worker pushes result to Redis
   ↓
7. Frontend receives result via polling
```

### OCR Engine Selection Flow

```
1. Worker calls OCREngineManager.extract_text()
   ↓
2. Load OCRConfigurationDB from database
   - selected_engine: TESSERACT | PADDLEOCR | VISION_LLM | HYBRID
   ↓
3. If HYBRID (intelligent routing):
   ├─▶ Analyze document quality
   ├─▶ If clean → Tesseract (fast)
   ├─▶ If complex → PaddleOCR (accurate)
   └─▶ If very complex → Vision LLM (AI-powered)

4. If PADDLEOCR selected:
   ├─▶ Check PaddleOCR service health
   ├─▶ POST to http://paddleocr-service.railway.internal:9123/extract
   ├─▶ If fails → Fallback to hybrid
   └─▶ Return extracted text + confidence

5. If TESSERACT selected:
   ├─▶ Convert PDF/image to format
   ├─▶ Call pytesseract.image_to_string()
   └─▶ Return extracted text + confidence

6. If VISION_LLM selected:
   ├─▶ Encode image as base64
   ├─▶ Call OVH AI Endpoints (Qwen2-VL-72B)
   └─▶ Return extracted text + confidence
```

## Inter-Service Communication

### Frontend ↔ Backend
- **Protocol**: HTTP/HTTPS
- **URL**: `http://doctranslator-backend.railway.internal:9122` (internal)
- **Public**: `https://your-app.up.railway.app/api` (via nginx proxy)
- **Format**: JSON REST API

### Backend ↔ Worker
- **Protocol**: Redis (broker-mediated)
- **No direct TCP**: Worker pulls from Redis queue
- **Communication**: Backend → Redis → Worker → Redis → Backend

### Worker ↔ PaddleOCR
- **Protocol**: HTTP (Railway IPv6 internal)
- **URL**: `http://paddleocr-service.railway.internal:9123`
- **Format**: JSON REST API
- **Fallback**: If unavailable, use Tesseract or Vision LLM

### Backend/Worker ↔ PostgreSQL
- **Protocol**: PostgreSQL wire protocol (TCP)
- **URL**: Auto-configured via `DATABASE_URL`
- **ORM**: SQLAlchemy 2.0.43

### Backend/Worker ↔ Redis
- **Protocol**: Redis wire protocol (TCP)
- **URL**: Auto-configured via `REDIS_URL`
- **Client**: Redis-py 5.0.0

### Backend/Worker ↔ OVH AI
- **Protocol**: HTTPS (OpenAI-compatible API)
- **URL**: `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1`
- **Authentication**: Bearer token
- **Client**: OpenAI Python SDK

## Railway IPv6 Networking

### Why IPv6 is Critical

Railway uses **IPv6 for internal service-to-service communication**. Services must listen on `::` (IPv6 any address) to accept internal connections.

### Correct Configuration

**Backend Dockerfile**:
```dockerfile
CMD sh -c "uvicorn app.main:app --host :: --port 9122"
```

**PaddleOCR entrypoint.sh**:
```bash
exec su appuser -c "uvicorn app.main:app --host :: --port 9123"
```

### Common Mistake

**Wrong** (IPv4 only):
```bash
uvicorn app.main:app --host 0.0.0.0 --port 9123
```

**Result**: Connection refused (errno 111)

**Right** (IPv4 + IPv6):
```bash
uvicorn app.main:app --host :: --port 9123
```

**Result**: Accepts connections from Railway internal network

### Internal Domain Pattern

Railway services communicate via:
```
http://<service-name>.railway.internal:<port>
```

Examples:
- `http://doctranslator-backend.railway.internal:9122`
- `http://paddleocr-service.railway.internal:9123`

### Service Discovery

Railway automatically:
- Creates DNS entries for services
- Routes internal traffic via IPv6
- Provides `RAILWAY_PRIVATE_DOMAIN` variable
- Manages service-to-service TLS (optional)

## Security Architecture

### Data Protection
- **Zero Persistence**: Documents deleted after processing
- **In-Memory Processing**: No disk storage of medical data
- **Auto-Cleanup**: Temporary files removed every 30 seconds
- **Binary Storage**: File content stored as PostgreSQL BYTEA (for audit/retry)

### GDPR Compliance
- **EU-Based Processing**: OVH AI Endpoints in EU
- **PII Removal**: spaCy NER-based automated filtering
- **No Data Retention**: Jobs auto-deleted after completion (configurable)
- **Audit Logging**: AI interactions logged (optional, configurable)

### Application Security
- **HTTPS Only**: Railway automatic TLS
- **CORS Protection**: Configurable allowed origins
- **Rate Limiting**: 5 uploads/minute (SlowAPI)
- **Input Validation**: Pydantic models
- **SQL Injection**: SQLAlchemy parameterized queries
- **XSS Protection**: React automatic escaping
- **Secure Headers**: X-Frame-Options, CSP, X-Content-Type-Options

### Authentication & Authorization
- **Current**: No authentication (internal use)
- **Future**: JWT tokens for API access

## Performance Optimizations

### Backend
- **Async Everything**: FastAPI async handlers, httpx async client
- **Connection Pooling**: PostgreSQL connection pool (SQLAlchemy)
- **Streaming Responses**: Real-time updates from AI
- **Lazy Loading**: On-demand spaCy model loading

### Frontend
- **Code Splitting**: React.lazy() for route-based chunks
- **Asset Optimization**: Vite build minification
- **Caching**: nginx cache headers for static assets
- **Compression**: gzip enabled in nginx

### Worker
- **Prefetch Multiplier**: 1 (process one task at a time)
- **Max Tasks Per Child**: 50 (prevents memory leaks)
- **Concurrency**: 2 workers (configurable per Railway plan)
- **Late Acknowledgment**: Tasks acknowledged after completion

### PaddleOCR
- **CPU Optimization**: PaddleOCR CPU mode
- **Model Caching**: Models downloaded once, cached in volume
- **Batch Processing**: Single image per request (future: batch support)

### Database
- **Indexes**: Primary keys, foreign keys, status columns
- **JSONB**: Efficient storage for pipeline config
- **BYTEA**: Binary file storage (faster than filesystem)

## Monitoring & Observability

### Health Endpoints

**Service Health**:
```bash
# Frontend
curl https://your-app.up.railway.app/health

# Backend
curl https://your-app.up.railway.app/api/health

# Backend Detailed
curl https://your-app.up.railway.app/api/health/detailed

# PaddleOCR (internal)
curl http://paddleocr-service.railway.internal:9123/health
```

### Logging

**Structured Logging**:
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Output: stdout (Railway captures)

**Log Categories**:
- `app.main` - Application startup/shutdown
- `app.routers` - API request/response
- `app.services` - Business logic execution
- `worker.tasks` - Background task processing
- `paddleocr_service` - OCR service logs

### Metrics Tracked

- Processing success rate (completed vs failed)
- Average processing time (per document, per step)
- OCR engine usage distribution
- Error frequency by type
- Worker queue length
- Redis connection status
- Database query performance

### Error Handling

**Backend**:
```python
try:
    result = await process_document()
except ValueError as e:
    logger.error(f"Validation error: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

**Worker**:
```python
@celery_app.task(bind=True, max_retries=3)
def process_document(self, processing_id):
    try:
        # Processing logic
    except SoftTimeLimitExceeded:
        logger.error("Task timeout")
        self.retry(countdown=60)
    except Exception as e:
        logger.exception(f"Task failed: {e}")
        # Update job status to FAILED
```

## Scalability Considerations

### Horizontal Scaling

**Stateless Design**:
- Backend: Stateless API (no sessions)
- Worker: Pull-based (add more workers)
- Database: Connection pooling

**Scalable Components**:
- Backend: Add more Railway instances
- Worker: Increase concurrency or add services
- PaddleOCR: Add more instances with load balancer
- Redis: Railway managed clustering
- PostgreSQL: Railway managed replication

### Vertical Scaling

**Railway Plans**:
- Starter: 512MB RAM, 1 vCPU
- Pro: 8GB RAM, 8 vCPU
- Team: 32GB RAM, 16 vCPU

**Resource Usage**:
- Backend: ~200MB RAM baseline
- Worker: ~300MB RAM per task
- PaddleOCR: ~500MB RAM (model cache)
- Frontend: ~50MB RAM (nginx)

### Performance Limits

- **Max File Size**: 50MB
- **Concurrent Uploads**: Railway plan-dependent
- **Worker Concurrency**: 2 (configurable)
- **OVH Rate Limits**: Token-based pricing
- **Database Connections**: Pool size 20 (default)

## Future Enhancements

### Planned Features
- [ ] WebSocket for real-time updates (replace polling)
- [ ] Batch document processing
- [ ] Redis caching for frequent translations
- [ ] Advanced analytics dashboard
- [ ] Multi-tenant support
- [ ] Custom model fine-tuning
- [ ] S3/object storage for file persistence

### Optimization Opportunities
- [ ] PaddleOCR GPU support (Railway Pro plan)
- [ ] Result caching (deduplicate similar documents)
- [ ] CDN integration for frontend assets
- [ ] Database read replicas
- [ ] API gateway for rate limiting
- [ ] Distributed tracing (OpenTelemetry)

---

**Architecture Version**: 2.0.0 (Microservices)
**Last Updated**: January 2025
**Platform**: Railway with IPv6 Internal Networking
