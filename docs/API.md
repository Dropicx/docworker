# API Reference

## Base URL

| Environment | URL |
|-------------|-----|
| **Production** | `https://your-app.railway.app` |
| **Development** | `https://dev-app.railway.app` |
| **Local** | `http://localhost:9122` |

All API endpoints are prefixed with `/api` except health checks.

---

## Authentication

### JWT Authentication

Most endpoints require JWT authentication. Obtain tokens via the login endpoint.

**Headers:**
```
Authorization: Bearer <access_token>
```

### API Key Authentication

For programmatic access, API keys can be used:

```
X-API-Key: <api_key>
```

---

## Endpoints Overview

### Core Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Simple health check |
| `/api/health` | GET | No | Backend health status |
| `/api/health/detailed` | GET | No | Detailed diagnostics |
| `/api/upload` | POST | Yes | Upload document |
| `/api/process/{id}` | GET | Yes | Get processing status |
| `/api/process/{id}/result` | GET | Yes | Get final result |
| `/api/process/languages` | GET | No | List target languages |

### Authentication Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/login` | POST | No | User login |
| `/api/auth/refresh` | POST | No | Refresh access token |
| `/api/auth/logout` | POST | Yes | Logout (revoke token) |

### Settings Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/settings/pipeline-steps` | GET | Yes | Get pipeline configuration |
| `/api/settings/pipeline-steps` | PUT | Admin | Update pipeline steps |
| `/api/settings/ocr-config` | GET | Yes | Get OCR configuration |
| `/api/settings/ocr-config` | PUT | Admin | Update OCR settings |

### Admin Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/users` | GET | Admin | List users |
| `/api/users` | POST | Admin | Create user |
| `/api/cost/summary` | GET | Admin | Cost statistics |
| `/api/feedback` | GET | Admin | View feedback |

---

## Health Checks

### GET /health

Simple health check for load balancers.

**Response:** `200 OK`
```
OK
```

### GET /api/health

Backend health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-16T10:30:00Z",
  "environment": "production",
  "ovh_configured": true
}
```

### GET /api/health/detailed

Detailed system diagnostics.

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "ovh_api": "healthy",
    "pii_service": "healthy",
    "ocr_service": "healthy"
  },
  "models": [
    "Meta-Llama-3.3-70B-Instruct",
    "Mistral-Nemo-Instruct-2407",
    "Qwen2.5-VL-72B-Instruct"
  ],
  "pipeline_steps": 10,
  "worker_available": true
}
```

---

## Authentication

### POST /api/auth/login

Authenticate user and obtain tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOi...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "role": "USER"
  }
}
```

**Errors:**
- `401 Unauthorized` - Invalid credentials
- `423 Locked` - Account locked (too many attempts)

### POST /api/auth/refresh

Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOi..."
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### POST /api/auth/logout

Revoke refresh token.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

---

## Document Processing

### POST /api/upload

Upload a document for processing.

**Request:**
- Content-Type: `multipart/form-data`
- Body:
  - `file`: Document file (required)
  - `target_language`: Target language code (optional, default: "de")

**Supported Formats:** PDF, DOCX, TXT, JPG, JPEG, PNG
**Max Size:** 50MB

**Example (curl):**
```bash
curl -X POST https://app.railway.app/api/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf" \
  -F "target_language=en"
```

**Response:**
```json
{
  "processing_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "file_type": "application/pdf",
  "file_size": 102400,
  "target_language": "en",
  "status": "QUEUED",
  "message": "Document queued for processing"
}
```

**Errors:**
- `400 Bad Request` - Invalid file type or missing file
- `413 Payload Too Large` - File exceeds 50MB
- `503 Service Unavailable` - Worker not available

### GET /api/process/{processing_id}

Get processing status.

**Response (Processing):**
```json
{
  "processing_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING",
  "progress_percent": 45,
  "current_step": "TRANSLATION",
  "steps_completed": ["TEXT_EXTRACTION", "MEDICAL_VALIDATION", "CLASSIFICATION", "PII_PREPROCESSING"],
  "steps_remaining": ["TRANSLATION", "FACT_CHECK", "GRAMMAR_CHECK", "LANGUAGE_TRANSLATION", "FINAL_CHECK", "FORMATTING"],
  "created_at": "2026-01-16T10:30:00Z",
  "updated_at": "2026-01-16T10:30:45Z"
}
```

**Response (Completed):**
```json
{
  "processing_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "progress_percent": 100,
  "current_step": null,
  "result_available": true,
  "created_at": "2026-01-16T10:30:00Z",
  "completed_at": "2026-01-16T10:31:30Z"
}
```

**Status Values:**
- `QUEUED` - Waiting in queue
- `PROCESSING` - Being processed
- `COMPLETED` - Successfully completed
- `FAILED` - Processing failed
- `CANCELLED` - Cancelled by user
- `TIMEOUT` - Processing timed out

### GET /api/process/{processing_id}/result

Get final processing result.

**Response:**
```json
{
  "processing_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_text": "Sehr geehrte Kolleginnen und Kollegen...",
  "simplified_text": "# Patienteninformation\n\nIhr Arzt hat folgende Befunde festgestellt...",
  "translated_text": "# Patient Information\n\nYour doctor has determined...",
  "document_type": "ARZTBRIEF",
  "is_medical": true,
  "target_language": "en",
  "confidence_score": 0.95,
  "processing_time_ms": 45230,
  "cost": {
    "total_tokens": 15420,
    "total_cost_usd": 0.0047
  },
  "metadata": {
    "ocr_engine": "PADDLEOCR",
    "pii_removed": true,
    "pii_types_detected": ["name", "birthdate", "address"]
  }
}
```

### DELETE /api/process/{processing_id}

Cancel a processing job.

**Response:**
```json
{
  "processing_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "CANCELLED",
  "message": "Processing cancelled successfully"
}
```

### GET /api/process/languages

List supported target languages.

**Response:**
```json
{
  "languages": [
    {"code": "de", "name": "German", "native_name": "Deutsch"},
    {"code": "en", "name": "English", "native_name": "English"},
    {"code": "fr", "name": "French", "native_name": "Français"},
    {"code": "es", "name": "Spanish", "native_name": "Español"},
    {"code": "it", "name": "Italian", "native_name": "Italiano"},
    {"code": "pt", "name": "Portuguese", "native_name": "Português"},
    {"code": "nl", "name": "Dutch", "native_name": "Nederlands"},
    {"code": "pl", "name": "Polish", "native_name": "Polski"}
  ],
  "default": "de"
}
```

---

## Pipeline Configuration

### GET /api/settings/pipeline-steps

Get pipeline step configurations.

**Response:**
```json
{
  "steps": [
    {
      "id": 1,
      "name": "TEXT_EXTRACTION",
      "display_name": "OCR Text Extraction",
      "description": "Extract text from document using OCR",
      "order": 1,
      "enabled": true,
      "model_id": null,
      "is_branching_step": false
    },
    {
      "id": 2,
      "name": "MEDICAL_VALIDATION",
      "display_name": "Medical Validation",
      "description": "Verify document is medical content",
      "order": 2,
      "enabled": true,
      "model_id": "Mistral-Nemo-Instruct-2407",
      "is_branching_step": true,
      "terminates_on_false": true
    }
    // ... more steps
  ]
}
```

### PUT /api/settings/pipeline-steps

Update pipeline step configurations. **Admin only.**

**Request:**
```json
{
  "steps": [
    {
      "id": 1,
      "enabled": true,
      "order": 1
    },
    {
      "id": 2,
      "enabled": false,
      "order": 2
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "updated_count": 2,
  "message": "Pipeline steps updated successfully"
}
```

### GET /api/settings/ocr-config

Get OCR engine configuration.

**Response:**
```json
{
  "selected_engine": "HYBRID",
  "engines": {
    "MISTRAL_OCR": {
      "enabled": true,
      "model": "mistral-ocr-latest",
      "healthy": true,
      "priority": 1
    },
    "PADDLEOCR": {
      "enabled": true,
      "service_url": "https://ocr.domain.de",
      "healthy": true,
      "priority": 2
    },
    "TESSERACT": {
      "enabled": true,
      "languages": ["deu", "eng"],
      "confidence_threshold": 0.5,
      "priority": 3
    },
    "VISION_LLM": {
      "enabled": true,
      "model": "Qwen2.5-VL-72B-Instruct",
      "priority": 4
    }
  },
  "hybrid_config": {
    "quality_threshold": 0.6,
    "prefer_paddleocr_for_tables": true,
    "min_ocr_confidence_threshold": 0.5
  }
}
```

---

## Cost & Statistics

### GET /api/cost/summary

Get token usage and cost statistics. **Admin only.**

**Query Parameters:**
- `start_date`: Start date (ISO 8601)
- `end_date`: End date (ISO 8601)
- `group_by`: `model` | `step` | `day`

**Response:**
```json
{
  "period": {
    "start": "2026-01-01T00:00:00Z",
    "end": "2026-01-16T23:59:59Z"
  },
  "totals": {
    "total_requests": 1250,
    "total_tokens": 5420000,
    "total_cost_usd": 15.83,
    "average_cost_per_document": 0.013
  },
  "by_model": [
    {
      "model": "Meta-Llama-3.3-70B-Instruct",
      "requests": 4500,
      "tokens": 4200000,
      "cost_usd": 12.60
    },
    {
      "model": "Mistral-Nemo-Instruct-2407",
      "requests": 2500,
      "tokens": 1220000,
      "cost_usd": 3.23
    }
  ]
}
```

---

## Feature Flags

Runtime feature toggles for controlling application behavior.

### GET /api/settings/feature-flags

Get all feature flags. **Admin only.**

**Response:**
```json
{
  "flags": [
    {
      "id": "uuid",
      "name": "enable_ocr",
      "description": "Enable OCR text extraction",
      "enabled": true,
      "enabled_for_roles": ["ADMIN", "USER"],
      "created_at": "2026-01-01T00:00:00Z"
    },
    {
      "id": "uuid",
      "name": "enable_privacy_filter",
      "description": "Enable PII removal before AI processing",
      "enabled": true,
      "enabled_for_roles": ["ADMIN", "USER", "VIEWER"]
    },
    {
      "id": "uuid",
      "name": "enable_multi_file",
      "description": "Enable batch processing multiple documents",
      "enabled": true,
      "enabled_for_roles": ["ADMIN"]
    },
    {
      "id": "uuid",
      "name": "enable_feedback_analysis",
      "description": "Enable AI analysis of user feedback",
      "enabled": true,
      "enabled_for_roles": ["ADMIN"]
    }
  ]
}
```

### PUT /api/settings/feature-flags/{flag_name}

Update a feature flag. **Admin only.**

**Request:**
```json
{
  "enabled": true,
  "enabled_for_roles": ["ADMIN", "USER"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Feature flag updated successfully"
}
```

---

## Quality Gate

Quality assurance system for OCR and processing results.

### GET /api/settings/quality-gate

Get quality gate configuration. **Admin only.**

**Response:**
```json
{
  "min_ocr_confidence_threshold": 0.5,
  "min_medical_validation_confidence": 0.7,
  "enable_fact_check": true,
  "enable_grammar_check": true,
  "max_retry_attempts": 3,
  "quality_metrics": {
    "ocr_accuracy_target": 0.95,
    "translation_quality_target": 0.90
  }
}
```

### PUT /api/settings/quality-gate

Update quality gate settings. **Admin only.**

**Request:**
```json
{
  "min_ocr_confidence_threshold": 0.6,
  "enable_fact_check": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Quality gate settings updated"
}
```

---

## Feedback Analysis

AI-powered analysis of user feedback using Mistral Large.

### GET /api/feedback/analysis

Get feedback analysis results. **Admin only.**

**Query Parameters:**
- `start_date`: Start date (ISO 8601)
- `end_date`: End date (ISO 8601)
- `status`: `pending` | `completed` | `failed`

**Response:**
```json
{
  "total_feedback": 150,
  "analyzed": 142,
  "pending_analysis": 8,
  "analysis_summary": {
    "average_rating": 4.2,
    "sentiment_breakdown": {
      "positive": 85,
      "neutral": 45,
      "negative": 20
    },
    "common_themes": [
      "translation_accuracy",
      "simplification_quality",
      "processing_speed"
    ],
    "improvement_suggestions": [
      "Better handling of medical abbreviations",
      "Faster processing for large documents"
    ]
  },
  "recent_analyses": [
    {
      "feedback_id": "uuid",
      "rating": 4,
      "ai_analysis": {
        "sentiment": "positive",
        "themes": ["accuracy", "clarity"],
        "actionable_insights": "User appreciates simplified explanations"
      },
      "analyzed_at": "2026-01-16T10:30:00Z",
      "model_used": "mistral-large-latest"
    }
  ]
}
```

### POST /api/feedback/{id}/analyze

Trigger AI analysis for a specific feedback. **Admin only.**

**Response:**
```json
{
  "feedback_id": "uuid",
  "status": "analysis_queued",
  "message": "Feedback queued for AI analysis"
}
```

---

## Audit Logging

Security and compliance audit trail.

### GET /api/audit/logs

Get audit logs. **Admin only.**

**Query Parameters:**
- `start_date`: Start date (ISO 8601)
- `end_date`: End date (ISO 8601)
- `action`: Filter by action type
- `user_id`: Filter by user
- `page`: Page number
- `per_page`: Items per page

**Response:**
```json
{
  "logs": [
    {
      "id": "uuid",
      "timestamp": "2026-01-16T10:30:00Z",
      "user_id": "uuid",
      "user_email": "admin@example.com",
      "action": "PIPELINE_CONFIG_UPDATE",
      "resource_type": "pipeline_step",
      "resource_id": "step-123",
      "details": {
        "changes": {
          "enabled": {"old": false, "new": true}
        }
      },
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0..."
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 1250,
    "pages": 25
  }
}
```

**Action Types:**
- `USER_LOGIN` - User authentication
- `USER_LOGOUT` - User logout
- `USER_CREATE` - New user created
- `USER_UPDATE` - User modified
- `PIPELINE_CONFIG_UPDATE` - Pipeline configuration changed
- `OCR_CONFIG_UPDATE` - OCR settings changed
- `FEATURE_FLAG_UPDATE` - Feature flag modified
- `API_KEY_CREATE` - API key generated
- `API_KEY_REVOKE` - API key revoked
- `FEEDBACK_DELETE` - Feedback removed (GDPR)

---

## User Management

### GET /api/users

List users. **Admin only.**

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20)
- `role`: Filter by role

**Response:**
```json
{
  "users": [
    {
      "id": "uuid",
      "email": "admin@example.com",
      "role": "ADMIN",
      "created_at": "2026-01-01T00:00:00Z",
      "last_login": "2026-01-16T10:00:00Z",
      "is_active": true
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 5,
    "pages": 1
  }
}
```

### POST /api/users

Create new user. **Admin only.**

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure-password",
  "role": "USER"
}
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "role": "USER",
  "created_at": "2026-01-16T10:30:00Z"
}
```

---

## Feedback

### POST /api/feedback

Submit user feedback.

**Request:**
```json
{
  "processing_id": "550e8400-e29b-41d4-a716-446655440000",
  "rating": 4,
  "comment": "Translation was accurate but could be simpler",
  "consent_given": true
}
```

**Response:**
```json
{
  "id": "uuid",
  "message": "Feedback submitted successfully"
}
```

### DELETE /api/feedback/{id}

Delete feedback (GDPR). **Requires consent owner or Admin.**

**Response:**
```json
{
  "message": "Feedback deleted successfully"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error description",
  "error_code": "ERROR_CODE",
  "timestamp": "2026-01-16T10:30:00Z",
  "request_id": "req_abc123"
}
```

### Error Codes

| HTTP Code | Error Code | Description |
|-----------|------------|-------------|
| 400 | `INVALID_REQUEST` | Invalid request parameters |
| 400 | `INVALID_FILE_TYPE` | Unsupported file format |
| 401 | `UNAUTHORIZED` | Missing or invalid token |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource not found |
| 413 | `FILE_TOO_LARGE` | File exceeds 50MB limit |
| 422 | `VALIDATION_ERROR` | Request validation failed |
| 423 | `ACCOUNT_LOCKED` | Too many failed attempts |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |
| 503 | `SERVICE_UNAVAILABLE` | External service down |

---

## Rate Limiting

| Endpoint | Limit |
|----------|-------|
| `/api/upload` | 5 requests/minute |
| `/api/auth/login` | 10 requests/minute |
| General | 100 requests/minute |

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705401600
```

---

## CORS

Production CORS configuration:

```python
origins = [
    "https://your-domain.com",
    "https://app.your-domain.com"
]
```

Development allows all origins.

---

## SDKs & Examples

### Python

```python
import httpx

class DocTranslatorClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    async def upload(self, file_path: str, target_language: str = "en"):
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                response = await client.post(
                    f"{self.base_url}/api/upload",
                    files={"file": f},
                    data={"target_language": target_language},
                    headers=self.headers
                )
            return response.json()

    async def get_result(self, processing_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/process/{processing_id}/result",
                headers=self.headers
            )
            return response.json()
```

### JavaScript/TypeScript

```typescript
async function translateDocument(file: File, targetLanguage: string = 'en') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('target_language', targetLanguage);

  const uploadResponse = await fetch('/api/upload', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  });

  const { processing_id } = await uploadResponse.json();

  // Poll for result
  while (true) {
    const statusResponse = await fetch(`/api/process/${processing_id}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const status = await statusResponse.json();

    if (status.status === 'COMPLETED') {
      const resultResponse = await fetch(`/api/process/${processing_id}/result`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return await resultResponse.json();
    }

    if (status.status === 'FAILED') {
      throw new Error('Processing failed');
    }

    await new Promise(r => setTimeout(r, 2000)); // Wait 2 seconds
  }
}
```

---

*Last Updated: January 2026*
