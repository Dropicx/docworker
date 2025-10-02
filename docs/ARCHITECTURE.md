# System Architecture

## Overview

DocTranslator is a medical document translation service built with a modern, GDPR-compliant architecture using Python FastAPI backend and React TypeScript frontend.

## Technology Stack

### Backend
- **Framework**: FastAPI 0.115.6
- **Server**: Uvicorn 0.34.0 with async support
- **Database**: PostgreSQL (production) / SQLite (development)
- **AI Integration**: OVH AI Endpoints (Llama 3.3 70B, Mistral Nemo)
- **OCR**: Tesseract OCR with pytesseract
- **PDF Processing**: pdf2image, PyPDF2, pdfplumber
- **Image Processing**: Pillow 11.1.0
- **Privacy**: spaCy NER for PII detection (optional)

### Frontend
- **Framework**: React 18.3.1 with TypeScript
- **Build Tool**: Vite 6.0.6
- **Styling**: TailwindCSS 3.4.17
- **Routing**: React Router 6.30.1
- **HTTP Client**: Axios 1.7.9
- **Icons**: Lucide React
- **Markdown**: react-markdown
- **PDF Export**: jsPDF + html2canvas

### Infrastructure
- **Deployment**: Railway.app with Docker
- **AI Processing**: OVH AI Endpoints (EU-based GDPR compliance)
- **Reverse Proxy**: nginx
- **Container**: Multi-stage Docker build

## System Components

### 1. Document Upload Service
**Location**: `frontend/src/components/FileUpload.tsx`

Handles file uploads with:
- Drag-and-drop interface
- Format validation (PDF, DOCX, TXT, images)
- Size validation (max 50MB)
- Progress tracking
- Multiple file support

### 2. Text Extraction Service
**Location**: `backend/app/services/hybrid_text_extractor.py`

Multi-strategy text extraction:
- **PDF**: PyPDF2 → pdfplumber → OCR fallback
- **Images**: Tesseract OCR (German/English)
- **DOCX**: python-docx
- **TXT**: Direct reading

### 3. Processing Pipeline
**Location**: `backend/app/services/unified_processing.py`

9-step configurable pipeline:

1. **TEXT_EXTRACTION** - OCR preprocessing with Qwen Vision
2. **MEDICAL_VALIDATION** - Binary medical classification
3. **CLASSIFICATION** - Document type detection (ARZTBRIEF/BEFUNDBERICHT/LABORWERTE)
4. **PII_PREPROCESSING** - Privacy filtering with spaCy NER
5. **TRANSLATION** - Patient-friendly German translation
6. **FACT_CHECK** - Medical accuracy verification
7. **GRAMMAR_CHECK** - Language correction
8. **LANGUAGE_TRANSLATION** - Multi-language support (EN/FR/ES/IT/PT/NL/PL)
9. **FINAL_CHECK** - Quality assurance
10. **FORMATTING** - Markdown structure optimization

### 4. AI Integration Layer
**Location**: `backend/app/services/ovh_client.py`

OVH AI Endpoints integration:
- **Main Model**: Meta-Llama-3.3-70B-Instruct
- **Preprocessing**: Mistral-Nemo-Instruct-2407
- **Vision**: Qwen2-VL-72B-Instruct (OCR)
- Streaming responses
- Error handling and retries
- Token usage tracking

### 5. Privacy Filter
**Location**: `backend/app/services/privacy_filter_advanced.py`

Three-tier PII detection:
- **Tier 1**: Advanced spaCy NER (when available)
- **Tier 2**: Smart heuristic filter (fallback)
- **Tier 3**: Basic pattern matching

Removes:
- Names, addresses, dates of birth
- Phone numbers, emails
- Insurance numbers
- Gender indicators

Preserves:
- Medical eponyms (Morbus Crohn, Parkinson)
- Anatomical structures (Baker-Zyste)
- Lab values and diagnoses
- Medications and dosages

### 6. Database Layer
**Location**: `backend/app/database/`

Unified prompt management:
- Universal prompts (apply to all document types)
- Document-specific prompts
- Pipeline step configurations
- AI interaction logging
- System settings

See [DATABASE.md](./DATABASE.md) for details.

### 7. Settings Management
**Location**: `frontend/src/components/Settings.tsx`

Admin interface for:
- Universal prompt editing
- Document-specific prompt customization
- Pipeline step enable/disable
- System configuration
- Real-time preview

## Data Flow

```
User Upload
    ↓
Frontend (React)
    ↓ POST /api/upload
Backend (FastAPI)
    ↓
Text Extraction
    ↓
Pipeline Processing (9 steps)
    ↓
OVH AI Endpoints
    ↓
Response Streaming
    ↓
Frontend Display
    ↓
Optional PDF Export
```

## Deployment Architecture

### Railway Deployment

```
Internet
    ↓
Railway Load Balancer
    ↓
nginx (Port 8080)
    ├── / → React Frontend (static)
    └── /api → FastAPI Backend (Port 9122)
           ↓
      OVH AI Endpoints (EU)
           ↓
      PostgreSQL Database
```

### Docker Container

Multi-stage build:
1. **Backend Build**: Install Python dependencies, download OCR data
2. **Frontend Build**: npm install, TypeScript compile, Vite build
3. **Production Image**: Copy artifacts, configure nginx, set up health checks

**Dockerfile**: `Dockerfile.railway`

## Security Features

### Data Protection
- **No Persistence**: Documents deleted after processing
- **Auto-Cleanup**: Temporary files removed every 30 seconds
- **In-Memory Processing**: No disk storage of medical data
- **HTTPS Only**: Encrypted transport layer

### GDPR Compliance
- **EU-Based Processing**: OVH AI Endpoints in EU
- **PII Removal**: Automated privacy filtering
- **No Data Retention**: Zero-storage policy
- **Audit Logging**: AI interaction logs (configurable)

### Application Security
- **CORS Protection**: Configurable allowed origins
- **Rate Limiting**: Request throttling
- **Input Validation**: Pydantic models
- **Error Handling**: No sensitive data in errors

## Performance Optimizations

### Backend
- **Async Processing**: FastAPI async handlers
- **Streaming Responses**: Real-time updates
- **Connection Pooling**: Database connection reuse
- **Lazy Loading**: On-demand model loading

### Frontend
- **Code Splitting**: Lazy route loading
- **Asset Optimization**: Vite build optimization
- **Caching**: Browser caching headers
- **Compression**: nginx gzip compression

### Infrastructure
- **Auto-Scaling**: Railway automatic scaling
- **CDN**: Static asset delivery
- **Health Checks**: Automated monitoring
- **Zero-Downtime Deploys**: Rolling updates

## Monitoring & Logging

### Application Logs
- **Structured Logging**: JSON format
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Context**: Request IDs, session tracking
- **Performance**: Processing time tracking

### Health Endpoints
- `GET /health` - Simple health check
- `GET /api/health` - Backend status
- `GET /api/health/detailed` - Full diagnostics

### Metrics
- Processing success rates
- Average processing times
- Error frequency and types
- Token usage statistics

## Scalability Considerations

### Horizontal Scaling
- Stateless backend design
- Session-based processing
- Database-backed configuration
- Shared nothing architecture

### Performance Limits
- **Max File Size**: 50MB
- **Concurrent Requests**: Railway plan-dependent
- **OVH Rate Limits**: Token-based pricing
- **Database Connections**: Pool size configurable

## Future Enhancements

### Planned Features
- [ ] Batch document processing
- [ ] Advanced caching layer
- [ ] Custom model fine-tuning
- [ ] Multi-tenant support
- [ ] Advanced analytics dashboard

### Optimization Opportunities
- [ ] Redis caching for frequent translations
- [ ] WebSocket for real-time updates
- [ ] Background job processing
- [ ] CDN integration for assets
