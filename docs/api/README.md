# API Reference - DocTranslator

## Table of Contents
1. [Overview](#overview)
2. [Base URL & Authentication](#base-url--authentication)
3. [Rate Limiting](#rate-limiting)
4. [Endpoints](#endpoints)
5. [Data Models](#data-models)
6. [Error Handling](#error-handling)
7. [Examples](#examples)
8. [WebSocket Support](#websocket-support)

## Overview

The DocTranslator API provides programmatic access to medical document translation services. The API follows RESTful principles and returns JSON responses.

### Key Features
- RESTful API design
- JSON request/response format
- Comprehensive error handling
- Rate limiting for fair usage
- Health monitoring endpoints
- Async processing support

## Base URL & Authentication

### Base URL
```
Production: https://medical.your-domain.de/api
Development: http://localhost:9122/api
```

### Authentication
Currently, the API doesn't require authentication tokens. Future versions may implement API key authentication.

### Headers
Required headers for all requests:
```http
Content-Type: application/json
Accept: application/json
```

## Rate Limiting

Rate limits are enforced per IP address:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/upload` | 5 requests | 1 minute |
| `/process/{id}` | 3 requests | 1 minute |
| `/process/active` | 30 requests | 1 minute |
| `/upload/{id}` (DELETE) | 10 requests | 1 minute |

Exceeded limits return `429 Too Many Requests`.

## Endpoints

### 1. Upload Document

**POST** `/api/upload`

Uploads a medical document for translation.

#### Request
```http
POST /api/upload
Content-Type: multipart/form-data

file: [binary data]
```

#### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | File | Yes | Medical document (PDF, JPG, PNG) |

#### Response
```json
{
  "processing_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "arztbrief.pdf",
  "file_type": "PDF",
  "file_size": 245632,
  "status": "pending",
  "message": "File successfully uploaded and ready for processing"
}
```

#### Status Codes
- `200 OK`: Upload successful
- `400 Bad Request`: Invalid file or validation failed
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

### 2. Start Processing

**POST** `/api/process/{processing_id}`

Initiates translation processing for an uploaded document.

#### Request
```http
POST /api/process/550e8400-e29b-41d4-a716-446655440000
```

#### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| processing_id | UUID | Yes | ID from upload response |

#### Response
```json
{
  "message": "Processing started",
  "processing_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing"
}
```

#### Status Codes
- `200 OK`: Processing started
- `404 Not Found`: Processing ID not found
- `409 Conflict`: Already processing or completed
- `429 Too Many Requests`: Rate limit exceeded

---

### 3. Get Processing Status

**GET** `/api/process/{processing_id}/status`

Retrieves the current processing status.

#### Request
```http
GET /api/process/550e8400-e29b-41d4-a716-446655440000/status
```

#### Response
```json
{
  "processing_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "translating",
  "progress_percent": 60,
  "current_step": "Translating text to simple language...",
  "message": null,
  "error": null
}
```

#### Status Values
- `pending`: Waiting to start
- `processing`: Initial processing
- `extracting_text`: Extracting text from document
- `translating`: Translating to simple language
- `completed`: Successfully completed
- `error`: Processing failed

---

### 4. Get Translation Result

**GET** `/api/process/{processing_id}/result`

Retrieves the completed translation result.

#### Request
```http
GET /api/process/550e8400-e29b-41d4-a716-446655440000/result
```

#### Response
```json
{
  "processing_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_text": "Original medical text...",
  "translated_text": "📋 **SUMMARY**\nSimple explanation...",
  "document_type_detected": "arztbrief",
  "confidence_score": 0.92,
  "processing_time_seconds": 34.5
}
```

#### Status Codes
- `200 OK`: Result retrieved successfully
- `404 Not Found`: Processing ID not found
- `409 Conflict`: Processing not yet completed

---

### 5. Cancel Processing

**DELETE** `/api/upload/{processing_id}`

Cancels ongoing processing and deletes associated data.

#### Request
```http
DELETE /api/upload/550e8400-e29b-41d4-a716-446655440000
```

#### Response
```json
{
  "message": "Processing successfully cancelled",
  "processing_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### 6. Health Check

**GET** `/api/health`

Comprehensive system health check.

#### Request
```http
GET /api/health
```

#### Response
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "services": {
    "api": {
      "status": "healthy",
      "response_time_ms": 5
    },
    "ollama": {
      "status": "healthy",
      "connected": true,
      "models_available": 3
    },
    "storage": {
      "status": "healthy",
      "temp_files": 2,
      "disk_usage_percent": 45.2
    }
  },
  "metrics": {
    "active_processes": 3,
    "cpu_percent": 23.5,
    "memory_percent": 67.8,
    "uptime_seconds": 86400
  }
}
```

---

### 7. Get Upload Limits

**GET** `/api/upload/limits`

Returns current upload limits and restrictions.

#### Response
```json
{
  "max_file_size_mb": 10,
  "allowed_formats": ["PDF", "JPG", "JPEG", "PNG"],
  "rate_limit": "5 uploads per minute",
  "max_pages_pdf": 50,
  "min_image_size": "100x100 pixels",
  "max_image_size": "8000x8000 pixels",
  "processing_timeout_minutes": 30
}
```

---

### 8. List Available Models

**GET** `/api/process/models`

Lists available AI models for translation.

#### Response
```json
{
  "connected": true,
  "models": [
    "mistral-nemo:latest",
    "llama3.2:latest",
    "meditron:7b"
  ],
  "recommended": "mistral-nemo:latest",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

### 9. Get Active Processes

**GET** `/api/process/active`

Lists all active processing jobs (admin/debug endpoint).

#### Response
```json
{
  "active_count": 2,
  "processes": [
    {
      "processing_id": "550e8400...",
      "status": "translating",
      "progress_percent": 60,
      "current_step": "Translating text...",
      "created_at": "2025-01-15T10:29:00Z",
      "filename": "document.pdf"
    }
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## Data Models

### UploadResponse
```typescript
interface UploadResponse {
  processing_id: string;      // UUID
  filename: string;
  file_type: "PDF" | "IMAGE";
  file_size: number;          // bytes
  status: ProcessingStatus;
  message: string;
}
```

### ProcessingProgress
```typescript
interface ProcessingProgress {
  processing_id: string;
  status: ProcessingStatus;
  progress_percent: number;   // 0-100
  current_step: string;
  message?: string;
  error?: string;
}
```

### TranslationResult
```typescript
interface TranslationResult {
  processing_id: string;
  original_text: string;
  translated_text: string;
  document_type_detected: DocumentType;
  confidence_score: number;   // 0.0-1.0
  processing_time_seconds: number;
}
```

### ProcessingStatus
```typescript
enum ProcessingStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  EXTRACTING_TEXT = "extracting_text",
  TRANSLATING = "translating",
  COMPLETED = "completed",
  ERROR = "error"
}
```

### DocumentType
```typescript
enum DocumentType {
  ARZTBRIEF = "arztbrief",       // Doctor's letter
  LABORBEFUND = "laborbefund",   // Lab results
  RADIOLOGIE = "radiologie",     // Radiology report
  PATHOLOGIE = "pathologie",     // Pathology report
  ALLGEMEIN = "allgemein"        // General medical document
}
```

## Error Handling

### Error Response Format
```json
{
  "detail": "Error message describing what went wrong",
  "status_code": 400,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Common Error Codes

| Code | Description | Common Causes |
|------|-------------|---------------|
| 400 | Bad Request | Invalid file format, file too large |
| 404 | Not Found | Processing ID doesn't exist |
| 409 | Conflict | Processing already started/completed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server or AI model error |
| 503 | Service Unavailable | Ollama service down |

## Examples

### Complete Upload and Translation Flow

#### 1. Upload Document
```bash
curl -X POST \
  https://medical.your-domain.de/api/upload \
  -H "Accept: application/json" \
  -F "file=@arztbrief.pdf"
```

Response:
```json
{
  "processing_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "arztbrief.pdf",
  "file_type": "PDF",
  "file_size": 245632,
  "status": "pending"
}
```

#### 2. Start Processing
```bash
curl -X POST \
  https://medical.your-domain.de/api/process/550e8400-e29b-41d4-a716-446655440000
```

#### 3. Check Status (Poll)
```bash
curl -X GET \
  https://medical.your-domain.de/api/process/550e8400-e29b-41d4-a716-446655440000/status
```

#### 4. Get Result
```bash
curl -X GET \
  https://medical.your-domain.de/api/process/550e8400-e29b-41d4-a716-446655440000/result
```

### Python Example

```python
import requests
import time

# Configuration
API_BASE = "https://medical.your-domain.de/api"

def translate_document(file_path):
    # 1. Upload
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"{API_BASE}/upload",
            files={'file': f}
        )
    upload_data = response.json()
    processing_id = upload_data['processing_id']
    
    # 2. Start processing
    requests.post(f"{API_BASE}/process/{processing_id}")
    
    # 3. Poll for completion
    while True:
        status = requests.get(
            f"{API_BASE}/process/{processing_id}/status"
        ).json()
        
        if status['status'] == 'completed':
            break
        elif status['status'] == 'error':
            raise Exception(f"Processing failed: {status.get('error')}")
        
        print(f"Progress: {status['progress_percent']}% - {status['current_step']}")
        time.sleep(2)
    
    # 4. Get result
    result = requests.get(
        f"{API_BASE}/process/{processing_id}/result"
    ).json()
    
    return result

# Usage
try:
    result = translate_document("medical_document.pdf")
    print("Translation:", result['translated_text'])
    print(f"Confidence: {result['confidence_score']:.2%}")
except Exception as e:
    print(f"Error: {e}")
```

### JavaScript/TypeScript Example

```typescript
class MedicalTranslatorAPI {
  private baseUrl = 'https://medical.your-domain.de/api';

  async translateDocument(file: File): Promise<TranslationResult> {
    // 1. Upload document
    const formData = new FormData();
    formData.append('file', file);
    
    const uploadResponse = await fetch(`${this.baseUrl}/upload`, {
      method: 'POST',
      body: formData
    });
    const uploadData = await uploadResponse.json();
    
    // 2. Start processing
    await fetch(`${this.baseUrl}/process/${uploadData.processing_id}`, {
      method: 'POST'
    });
    
    // 3. Poll for completion
    while (true) {
      const statusResponse = await fetch(
        `${this.baseUrl}/process/${uploadData.processing_id}/status`
      );
      const status = await statusResponse.json();
      
      if (status.status === 'completed') {
        break;
      } else if (status.status === 'error') {
        throw new Error(`Processing failed: ${status.error}`);
      }
      
      // Wait 2 seconds before next poll
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    
    // 4. Get result
    const resultResponse = await fetch(
      `${this.baseUrl}/process/${uploadData.processing_id}/result`
    );
    return await resultResponse.json();
  }
}
```

## WebSocket Support

*Note: WebSocket support for real-time updates is planned for future versions.*

### Planned WebSocket Events
- `processing.started`: Processing initiated
- `processing.progress`: Progress updates
- `processing.completed`: Translation ready
- `processing.error`: Error occurred

## Best Practices

### 1. Error Handling
Always implement proper error handling for network failures and API errors.

### 2. Polling Strategy
When polling for status:
- Start with 1-second intervals
- Increase to 2-5 seconds after 10 seconds
- Maximum poll duration: 5 minutes

### 3. File Validation
Validate files client-side before upload:
- Check file size (<10MB)
- Verify file format
- Ensure file is readable

### 4. Rate Limiting
Implement client-side rate limiting to avoid 429 errors:
- Track request timestamps
- Queue requests if needed
- Show user-friendly messages

### 5. Timeout Handling
Set appropriate timeouts:
- Upload: 60 seconds
- Processing: 5 minutes
- Status checks: 10 seconds

---

*API Reference Version: 1.0.0 | Last Updated: January 2025*