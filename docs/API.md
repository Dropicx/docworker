# API Reference

## Base URL

**Production**: `https://your-app.up.railway.app`
**Local Development**: `http://localhost:9122`

All API endpoints are prefixed with `/api` except health checks.

## Authentication

Currently no authentication required. All endpoints are public.

## Endpoints

### Health Checks

#### GET /health
Simple health check for load balancers and monitoring.

**Response:**
```
OK
```

#### GET /api/health
Backend health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-02T10:30:00Z",
  "environment": "production",
  "ovh_configured": true
}
```

#### GET /api/health/detailed
Detailed system diagnostics.

**Response:**
```json
{
  "status": "healthy",
  "ovh_available": true,
  "database_connected": true,
  "models": ["Meta-Llama-3_3-70B-Instruct", "Mistral-Nemo-Instruct-2407"],
  "pipeline_steps": 9
}
```

### Document Processing

#### POST /api/upload
Upload and process a document.

**Request:**
- Content-Type: `multipart/form-data`
- Body:
  - `file`: Document file (PDF, DOCX, TXT, JPG, PNG)
  - Max size: 50MB

**Example (curl):**
```bash
curl -X POST \
  http://localhost:9122/api/upload \
  -F "file=@document.pdf"
```

**Example (JavaScript):**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('/api/upload', {
  method: 'POST',
  body: formData
});

const data = await response.json();
```

**Response (200 OK):**
```json
{
  "file_id": "abc123",
  "filename": "document.pdf",
  "file_path": "/tmp/uploads/abc123.pdf",
  "content_type": "application/pdf",
  "size": 102400,
  "message": "File uploaded successfully"
}
```

**Error Responses:**

400 Bad Request - Invalid file type:
```json
{
  "detail": "Unsupported file type. Allowed: pdf, txt, jpg, jpeg, png"
}
```

413 Request Entity Too Large - File too large:
```json
{
  "detail": "File size exceeds 50MB limit"
}
```

#### POST /api/process/translate
Process uploaded document through translation pipeline.

**Request:**
```json
{
  "file_path": "/tmp/uploads/abc123.pdf",
  "document_type": "ARZTBRIEF",  // Optional, auto-detected if not provided
  "target_language": "en",        // Optional: en, fr, es, it, pt, nl, pl
  "pipeline_config": {            // Optional: customize pipeline steps
    "TEXT_EXTRACTION": true,
    "MEDICAL_VALIDATION": true,
    "CLASSIFICATION": true,
    "PII_PREPROCESSING": true,
    "TRANSLATION": true,
    "FACT_CHECK": true,
    "GRAMMAR_CHECK": true,
    "LANGUAGE_TRANSLATION": false,
    "FINAL_CHECK": true,
    "FORMATTING": true
  }
}
```

**Example (curl):**
```bash
curl -X POST \
  http://localhost:9122/api/process/translate \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/tmp/uploads/abc123.pdf",
    "target_language": "en"
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "original_text": "Sehr geehrte Damen und Herren...",
  "simplified_text": "Ihr Arzt hat folgende Befunde festgestellt...",
  "document_type": "ARZTBRIEF",
  "is_medical": true,
  "confidence_score": 0.95,
  "processing_steps": {
    "TEXT_EXTRACTION": "completed",
    "MEDICAL_VALIDATION": "completed",
    "CLASSIFICATION": "completed",
    "TRANSLATION": "completed"
  },
  "processing_time_ms": 3425,
  "translated_text": "Your doctor has determined the following findings..."  // If target_language set
}
```

**Streaming Response:**

If using SSE (Server-Sent Events):
```
data: {"step": "TEXT_EXTRACTION", "status": "processing"}
data: {"step": "TEXT_EXTRACTION", "status": "completed", "result": "..."}
data: {"step": "TRANSLATION", "status": "processing"}
data: {"step": "TRANSLATION", "status": "completed", "result": "..."}
data: {"step": "COMPLETE", "final_result": {...}}
```

**Error Responses:**

400 Bad Request - Missing file_path:
```json
{
  "detail": "file_path is required"
}
```

404 Not Found - File not found:
```json
{
  "detail": "File not found: /tmp/uploads/abc123.pdf"
}
```

500 Internal Server Error - Processing failed:
```json
{
  "detail": "Translation failed: AI model timeout"
}
```

### Settings Management

#### GET /api/settings/universal-prompts
Get universal prompts (apply to all document types).

**Response:**
```json
{
  "medical_validation_prompt": "Du bist ein medizinischer Experte...",
  "classification_prompt": "Klassifiziere das Dokument...",
  "preprocessing_prompt": "Bereinige den OCR-Text...",
  "grammar_check_prompt": "Prüfe die Grammatik...",
  "language_translation_prompt": "Übersetze nach {target_language}...",
  "version": 2,
  "updated_at": "2025-01-02T10:00:00Z"
}
```

#### PUT /api/settings/universal-prompts
Update universal prompts.

**Request:**
```json
{
  "medical_validation_prompt": "New prompt text...",
  "classification_prompt": "Updated classification...",
  // ... other prompts
}
```

**Response:**
```json
{
  "success": true,
  "version": 3,
  "message": "Universal prompts updated successfully"
}
```

#### GET /api/settings/document-prompts/{document_type}
Get document-specific prompts.

**Parameters:**
- `document_type`: ARZTBRIEF | BEFUNDBERICHT | LABORWERTE

**Response:**
```json
{
  "document_type": "ARZTBRIEF",
  "translation_prompt": "Übersetze den Arztbrief...",
  "fact_check_prompt": "Prüfe medizinische Fakten...",
  "final_check_prompt": "Abschlussprüfung...",
  "formatting_prompt": "Formatiere als Markdown...",
  "version": 2,
  "updated_at": "2025-01-02T10:00:00Z"
}
```

#### PUT /api/settings/document-prompts/{document_type}
Update document-specific prompts.

**Request:**
```json
{
  "translation_prompt": "New translation prompt...",
  "fact_check_prompt": "Updated fact check...",
  // ... other prompts
}
```

**Response:**
```json
{
  "success": true,
  "version": 3,
  "message": "Document prompts updated successfully"
}
```

#### GET /api/settings/pipeline-steps
Get pipeline step configurations.

**Response:**
```json
{
  "steps": [
    {
      "step_name": "TEXT_EXTRACTION",
      "enabled": true,
      "order": 1,
      "name": "OCR Text Extraction",
      "description": "Extract and clean text from images"
    },
    {
      "step_name": "MEDICAL_VALIDATION",
      "enabled": true,
      "order": 2,
      "name": "Medical Validation",
      "description": "Verify document is medical"
    }
    // ... 7 more steps
  ]
}
```

#### PUT /api/settings/pipeline-steps
Update pipeline step configurations.

**Request:**
```json
{
  "steps": [
    {
      "step_name": "TEXT_EXTRACTION",
      "enabled": true,
      "order": 1
    },
    {
      "step_name": "MEDICAL_VALIDATION",
      "enabled": false,
      "order": 2
    }
    // ... other steps
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Pipeline steps updated successfully",
  "updated_count": 9
}
```

## Document Types

| Type | Description | Examples |
|------|-------------|----------|
| `ARZTBRIEF` | Doctor's letter, discharge summary | Entlassungsbrief, Überweisungsbrief |
| `BEFUNDBERICHT` | Medical report, findings | Radiologie, Pathologie, Befund |
| `LABORWERTE` | Lab results, blood tests | Blutbild, Laboruntersuchung |

## Supported Languages

| Code | Language | Support |
|------|----------|---------|
| `de` | German | Native (input) |
| `en` | English | Translation target |
| `fr` | French | Translation target |
| `es` | Spanish | Translation target |
| `it` | Italian | Translation target |
| `pt` | Portuguese | Translation target |
| `nl` | Dutch | Translation target |
| `pl` | Polish | Translation target |

## Supported File Formats

| Extension | Type | OCR Support |
|-----------|------|-------------|
| `.pdf` | PDF | Yes (if scanned) |
| `.txt` | Plain text | No |
| `.docx` | Word document | No |
| `.jpg`, `.jpeg` | Image | Yes |
| `.png` | Image | Yes |

## Rate Limiting

Currently no rate limiting implemented. Recommended for production:
- 100 requests/minute per IP
- 10 MB/s upload bandwidth
- 5 concurrent processing requests

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 404 | Resource not found |
| 413 | Payload too large (>50MB) |
| 415 | Unsupported media type |
| 422 | Validation error |
| 500 | Internal server error |
| 503 | Service unavailable (AI API down) |

## CORS

Default CORS configuration allows all origins in development.

Production should configure:
```python
origins = [
    "https://your-domain.com",
    "https://app.your-domain.com"
]
```

## Response Headers

All responses include:
```
Content-Type: application/json
X-Request-ID: <unique-request-id>
```

## Request Examples

### Complete Workflow (JavaScript)

```javascript
// 1. Upload file
const formData = new FormData();
formData.append('file', file);

const uploadResponse = await fetch('/api/upload', {
  method: 'POST',
  body: formData
});
const { file_path } = await uploadResponse.json();

// 2. Process document
const processResponse = await fetch('/api/process/translate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    file_path,
    target_language: 'en'
  })
});
const result = await processResponse.json();

console.log(result.simplified_text);
console.log(result.translated_text);
```

### Get and Update Settings (Python)

```python
import requests

# Get universal prompts
response = requests.get('http://localhost:9122/api/settings/universal-prompts')
prompts = response.json()

# Update a prompt
prompts['medical_validation_prompt'] = 'New prompt text...'
response = requests.put(
    'http://localhost:9122/api/settings/universal-prompts',
    json=prompts
)
print(response.json())
```

## Webhook Support

Not currently implemented. Future consideration for:
- Processing completion notifications
- Error alerts
- Usage statistics
