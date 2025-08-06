# Architecture Documentation - DocTranslator

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Security Architecture](#security-architecture)
6. [Technology Stack](#technology-stack)
7. [Deployment Architecture](#deployment-architecture)
8. [Performance Considerations](#performance-considerations)
9. [Scalability](#scalability)

## System Overview

DocTranslator is a microservices-based application designed for translating medical documents from complex medical terminology to patient-friendly language. The system prioritizes privacy, security, and performance while maintaining GDPR compliance.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │    Traefik     │ (Reverse Proxy / Load Balancer)
         │   (Port 443)   │
         └────────┬───────┘
                  │
        ┌─────────┴──────────┐
        ▼                    ▼
┌──────────────┐    ┌──────────────┐
│   Frontend   │    │   Backend    │
│    (React)   │◄───│  (FastAPI)   │
│  Port: 9121  │    │  Port: 9122  │
└──────────────┘    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │    Ollama    │
                    │  (AI Engine)  │
                    │  Port: 11434 │
                    └──────────────┘
```

### Core Components

1. **Frontend Service**: React-based SPA for user interaction
2. **Backend Service**: FastAPI application handling business logic
3. **Ollama Service**: Local AI inference engine
4. **Traefik**: Reverse proxy and SSL termination

## Architecture Principles

### 1. Privacy by Design
- No persistent storage of user data
- All processing in-memory
- Automatic cleanup of temporary files
- No external API calls for core functionality

### 2. Microservices Architecture
- Loosely coupled services
- Independent deployment capability
- Service-specific scaling
- Clear service boundaries

### 3. Security First
- HTTPS everywhere
- Input validation at multiple layers
- Rate limiting and DDoS protection
- Content Security Policy (CSP) headers

### 4. Performance Optimization
- Async processing for long-running tasks
- Efficient file handling
- Caching strategies where appropriate
- Resource pooling

## Component Architecture

### Frontend Component

```
src/
├── App.tsx                    # Main application component
├── components/
│   ├── FileUpload.tsx        # Document upload handling
│   ├── ProcessingStatus.tsx  # Real-time status updates
│   └── TranslationResult.tsx # Result display
├── services/
│   └── api.ts               # API client service
└── types/
    └── api.ts               # TypeScript type definitions
```

**Key Features:**
- Single Page Application (SPA)
- Responsive design with Tailwind CSS
- Real-time progress updates
- Error boundary implementation
- Progressive enhancement

### Backend Component

```
app/
├── main.py                   # FastAPI application entry
├── routers/
│   ├── upload.py            # Upload endpoints
│   ├── process.py           # Processing endpoints
│   └── health.py            # Health check endpoints
├── services/
│   ├── ollama_client.py     # Ollama integration
│   ├── text_extractor.py    # OCR and text extraction
│   ├── file_validator.py    # File validation logic
│   └── cleanup.py           # Cleanup service
└── models/
    └── document.py          # Data models
```

**Key Features:**
- Async request handling
- Background task processing
- Rate limiting per endpoint
- Comprehensive error handling
- Health monitoring

### AI Engine (Ollama)

**Integration Points:**
- REST API communication
- Model management
- Streaming response support
- Fallback model selection

**Supported Models:**
- mistral-nemo:latest (primary)
- llama3.2:latest
- meditron:7b (medical-specific)

## Data Flow

### Document Processing Flow

```
1. User Upload
   │
   ├─► File Validation
   │   ├─► Size Check (<10MB)
   │   ├─► Format Check (PDF/Image)
   │   └─► Content Validation
   │
2. Text Extraction
   │
   ├─► PDF Processing (PyPDF2)
   │   └─► Text Extraction
   │
   ├─► Image Processing (Pillow)
   │   └─► OCR (Tesseract)
   │
3. Document Analysis
   │
   ├─► Document Type Detection
   │   ├─► Arztbrief
   │   ├─► Lab Results
   │   ├─► Radiology
   │   └─► Pathology
   │
4. AI Translation
   │
   ├─► Prompt Generation
   ├─► Ollama Processing
   ├─► Quality Scoring
   └─► Response Formatting
   │
5. Result Delivery
   │
   ├─► Structured Output
   ├─► Confidence Score
   └─► Cleanup Trigger
```

### State Management

```
Document States:
┌─────────┐
│ PENDING │ ──► File uploaded, awaiting processing
└────┬────┘
     │
     ▼
┌─────────────┐
│ PROCESSING  │ ──► Initial processing started
└────┬────────┘
     │
     ▼
┌──────────────────┐
│ EXTRACTING_TEXT  │ ──► OCR/Text extraction phase
└────┬─────────────┘
     │
     ▼
┌──────────────┐
│ TRANSLATING  │ ──► AI translation in progress
└────┬─────────┘
     │
     ├─────────────┐
     ▼             ▼
┌───────────┐ ┌───────┐
│ COMPLETED │ │ ERROR │
└───────────┘ └───────┘
```

## Security Architecture

### Defense in Depth

```
Layer 1: Network Security
├─► HTTPS/TLS 1.3
├─► Traefik reverse proxy
└─► Network isolation (Docker)

Layer 2: Application Security
├─► Input validation
├─► Rate limiting
├─► CORS configuration
└─► Security headers

Layer 3: Data Security
├─► No persistent storage
├─► Memory-only processing
├─► Automatic cleanup
└─► Encrypted transmission

Layer 4: Infrastructure Security
├─► Container isolation
├─► Read-only file systems
├─► Limited container capabilities
└─► Security scanning
```

### Security Headers

```python
# Implemented security headers
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
Content-Security-Policy: default-src 'self'
```

### Input Validation

1. **File Upload Validation**
   - File size limits (10MB)
   - MIME type verification
   - Magic number validation
   - Filename sanitization

2. **API Input Validation**
   - UUID format for IDs
   - Request body validation
   - Parameter type checking
   - SQL injection prevention

## Technology Stack

### Frontend Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI framework |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 3.x | Styling |
| Vite | 5.x | Build tool |
| Axios | 1.x | HTTP client |
| Lucide React | - | Icons |

### Backend Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| FastAPI | 0.100+ | Web framework |
| Uvicorn | 0.23+ | ASGI server |
| Pydantic | 2.x | Data validation |
| httpx | 0.24+ | HTTP client |
| Pillow | 10.x | Image processing |
| PyPDF2 | 3.x | PDF processing |
| python-multipart | 0.0.6 | File uploads |
| slowapi | 0.1.8 | Rate limiting |

### Infrastructure Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| Docker | 24.x | Containerization |
| Docker Compose | 2.x | Orchestration |
| Nginx | 1.25 | Web server (frontend) |
| Traefik | 2.x | Reverse proxy |
| Ollama | Latest | AI inference |
| Tesseract | 5.x | OCR engine |

## Deployment Architecture

### Container Architecture

```yaml
Services:
├── frontend
│   ├── Base: node:20-alpine (build)
│   ├── Runtime: nginx:alpine
│   ├── Port: 9121
│   └── Networks: [proxy, medical-translator]
│
├── backend
│   ├── Base: python:3.11-slim
│   ├── Port: 9122
│   ├── Networks: [medical-translator, ollama]
│   └── Volumes: [/tmp, /logs]
│
└── ollama (external)
    ├── Port: 11434
    └── Networks: [ollama]
```

### Network Architecture

```
Networks:
├── proxy (external)
│   └── Traefik ↔ Frontend
│
├── medical-translator (internal)
│   ├── Frontend ↔ Backend
│   └── Isolated from internet
│
└── ollama (external)
    └── Backend ↔ Ollama
```

### Health Checks

```yaml
Backend Health Check:
- Endpoint: /api/health/simple
- Interval: 30s
- Timeout: 10s
- Retries: 3
- Start Period: 40s
```

## Performance Considerations

### Optimization Strategies

1. **Frontend Optimization**
   - Code splitting
   - Lazy loading
   - Image optimization
   - Bundle size optimization
   - CDN usage for static assets

2. **Backend Optimization**
   - Async processing
   - Connection pooling
   - Memory management
   - Background tasks
   - Response caching

3. **AI Model Optimization**
   - Model caching
   - Batch processing capability
   - Temperature tuning (0.3)
   - Response streaming
   - Fallback models

### Performance Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Page Load Time | <2s | ~1.5s |
| API Response Time | <200ms | ~150ms |
| Document Processing | <60s | ~30-45s |
| Memory Usage | <500MB | ~350MB |
| CPU Usage (idle) | <5% | ~2% |

## Scalability

### Horizontal Scaling

```
Load Balancer (Traefik)
         │
    ┌────┴────┬────────┬────────┐
    ▼         ▼        ▼        ▼
Frontend  Frontend  Frontend  Frontend
    │         │        │        │
    └────┬────┴────────┴────────┘
         │
    ┌────┴────┬────────┬────────┐
    ▼         ▼        ▼        ▼
Backend   Backend   Backend   Backend
    │         │        │        │
    └────┬────┴────────┴────────┘
         │
         ▼
   Ollama Cluster
```

### Scaling Strategies

1. **Frontend Scaling**
   - Multiple Nginx instances
   - CDN for static assets
   - Browser caching

2. **Backend Scaling**
   - Multiple FastAPI workers
   - Load balancing
   - Session affinity not required

3. **AI Engine Scaling**
   - Multiple Ollama instances
   - Model replication
   - Queue-based processing

### Bottlenecks & Solutions

| Bottleneck | Impact | Solution |
|------------|--------|----------|
| OCR Processing | High CPU | Dedicated OCR service |
| AI Inference | High memory | GPU acceleration |
| File Uploads | Network I/O | Chunked uploads |
| Concurrent Users | Resource contention | Horizontal scaling |

## Monitoring & Observability

### Key Metrics

1. **Application Metrics**
   - Request rate
   - Error rate
   - Response time
   - Active processes

2. **System Metrics**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network traffic

3. **Business Metrics**
   - Documents processed
   - Processing success rate
   - Average processing time
   - User satisfaction

### Logging Strategy

```
Log Levels:
├── ERROR: System errors, failures
├── WARNING: Degraded performance, retries
├── INFO: Normal operations, milestones
└── DEBUG: Detailed debugging (dev only)

Log Locations:
├── Frontend: Browser console
├── Backend: /app/logs/
├── Nginx: /var/log/nginx/
└── Docker: docker logs <container>
```

---

*Architecture Documentation Version: 1.0.0 | Last Updated: January 2025*