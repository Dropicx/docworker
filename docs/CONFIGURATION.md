# Configuration Management

Comprehensive guide to DocTranslator's centralized configuration system.

## Overview

DocTranslator uses a **three-tier configuration system** with type-safe validation:

1. **Environment Variables** (highest priority)
2. **.env File** (medium priority)
3. **Default Values** (from `app/core/config.py`)

All configuration is centralized in `app/core/config.py` using Pydantic Settings for type safety and validation.

---

## Quick Start

### 1. Copy Environment Template

```bash
cd backend
cp .env.example .env
```

### 2. Configure Required Settings

Edit `.env` and set:

```bash
# Required
DATABASE_URL=postgresql://user:password@localhost:5432/doctranslator
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token-here

# Recommended to change
SETTINGS_ACCESS_CODE=your-secure-code
SECRET_KEY=your-random-secret-key
```

### 3. Run Application

```bash
python -m uvicorn app.main:app --reload
```

Configuration is automatically loaded and validated on startup.

---

## Configuration Structure

### Application Settings

```python
APP_NAME=DocTranslator           # Application name
ENVIRONMENT=development          # development, staging, production
DEBUG=false                      # Enable debug mode
PORT=9122                        # Server port
```

### Database Settings (REQUIRED)

```python
DATABASE_URL=postgresql://user:password@host:port/database
DB_POOL_SIZE=20                  # Connection pool size
DB_MAX_OVERFLOW=40               # Maximum overflow connections
DB_POOL_TIMEOUT=30               # Pool timeout in seconds
```

### OVH AI Endpoints (REQUIRED)

```python
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token
OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1
OVH_MAIN_MODEL=Meta-Llama-3_3-70B-Instruct
OVH_PREPROCESSING_MODEL=Mistral-Nemo-Instruct-2407
OVH_TRANSLATION_MODEL=Meta-Llama-3_3-70B-Instruct
OVH_VISION_MODEL=Qwen2.5-VL-72B-Instruct
OVH_VISION_BASE_URL=https://qwen-2-5-vl-72b-instruct.endpoints.kepler.ai.cloud.ovh.net
USE_OVH_ONLY=true
```

### Security Settings

```python
SECRET_KEY=your-secret-key        # Session encryption key
SETTINGS_ACCESS_CODE=admin123     # Admin API access code (CHANGE!)
ALLOWED_ORIGINS=*                 # CORS allowed origins
TRUSTED_HOSTS=*                   # Trusted host headers
```

### Feature Flags

```python
ENABLE_OCR=true
ENABLE_PRIVACY_FILTER=true
ENABLE_MULTI_FILE=true
```

See [Feature Flags](#feature-flags-system) section below for complete list.

---

## Feature Flags System

### Overview

Feature flags enable runtime control of functionality without redeployment.

**Four-Tier Priority System:**

1. **Environment Variables** (highest)
   - `FEATURE_FLAG_{NAME}=true/false`
   - Example: `FEATURE_FLAG_VISION_LLM_FALLBACK_ENABLED=false`

2. **Database Configuration**
   - Managed via Admin API endpoints
   - Can be updated at runtime

3. **Config Defaults**
   - From `app/core/config.py` Settings
   - Maps some flags to config attributes

4. **Hardcoded Defaults** (lowest)
   - Defined in `app/services/feature_flags.py`
   - Production-ready defaults

### Available Feature Flags

#### OCR and Text Extraction

```python
FEATURE_FLAG_VISION_LLM_FALLBACK_ENABLED=true
FEATURE_FLAG_MULTI_FILE_PROCESSING_ENABLED=true
```

#### Privacy and Security

```python
FEATURE_FLAG_ADVANCED_PRIVACY_FILTER_ENABLED=true
FEATURE_FLAG_PII_REMOVAL_ENABLED=true
```

#### Performance and Monitoring

```python
FEATURE_FLAG_COST_TRACKING_ENABLED=true
FEATURE_FLAG_AI_LOGGING_ENABLED=true
FEATURE_FLAG_PARALLEL_STEP_EXECUTION_ENABLED=false  # Experimental
```

#### Pipeline Features

```python
FEATURE_FLAG_DYNAMIC_BRANCHING_ENABLED=true
FEATURE_FLAG_STOP_CONDITIONS_ENABLED=true
FEATURE_FLAG_RETRY_ON_FAILURE_ENABLED=true
```

#### Experimental Features

```python
FEATURE_FLAG_HYBRID_OCR_STRATEGY_ENABLED=false
FEATURE_FLAG_AUTO_QUALITY_DETECTION_ENABLED=false
```

### Using Feature Flags in Code

```python
from app.services.feature_flags import FeatureFlags, Feature
from app.core.config import settings
from app.database.connection import get_session

# In a function/route
def my_function(db: Session = Depends(get_session)):
    flags = FeatureFlags(session=db, settings=settings)

    if flags.is_enabled(Feature.VISION_LLM_FALLBACK):
        # Use Vision LLM fallback
        result = await process_with_vision()
    else:
        # Use standard processing
        result = await process_standard()
```

### Managing Feature Flags via API

#### Get All Feature Flags Status

```bash
curl -X GET http://localhost:9122/api/admin/config/feature-flags \
  -H "X-Access-Code: your-access-code"
```

#### Update Feature Flag

```bash
curl -X PUT http://localhost:9122/api/admin/config/feature-flags/vision_llm_fallback_enabled \
  -H "X-Access-Code: your-access-code" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false,
    "description": "Temporarily disable Vision LLM fallback",
    "rollout_percentage": 50
  }'
```

---

## Admin Configuration API

All admin endpoints require authentication via `X-Access-Code` header.

### Get Configuration Summary

```bash
GET /api/admin/config
X-Access-Code: your-access-code
```

Response:
```json
{
  "app_name": "DocTranslator",
  "environment": "production",
  "debug": false,
  "max_file_size_mb": 50,
  "database_connected": true,
  "ovh_configured": true,
  "redis_configured": true
}
```

### Validate Configuration

```bash
GET /api/admin/config/validation
X-Access-Code: your-access-code
```

Response:
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    "CORS allows all origins (*) in production - security risk"
  ]
}
```

### Hot Reload Configuration

```bash
POST /api/admin/config/reload
X-Access-Code: your-access-code
```

**Safe Settings for Hot Reload:**
- log_level
- max_file_size_mb
- ai_timeout_seconds
- rate_limit_per_minute

**Critical Settings Requiring Restart:**
- database_url
- ovh_ai_endpoints_access_token
- redis_url
- secret_key

---

## Configuration Validation

### Automatic Validation on Startup

Configuration is validated when the application starts:

```python
# In app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate configuration
    try:
        settings.validate_on_startup()
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
```

### Validation Rules

**Required Settings:**
- `DATABASE_URL` - PostgreSQL connection string
- `OVH_AI_ENDPOINTS_ACCESS_TOKEN` - OVH API token

**Format Validation:**
- `DATABASE_URL` must start with `postgresql://` or `postgres://`
- `LOG_LEVEL` must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `ENVIRONMENT` must be one of: development, staging, production
- `MAX_FILE_SIZE_MB` must be between 1 and 100

### Manual Validation

```python
from app.core.config import settings

# Validate and log configuration
settings.validate_on_startup()
```

---

## Environment-Specific Configuration

### Development

```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
ALLOWED_ORIGINS=*
```

### Staging

```bash
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://staging.doctranslator.com
```

### Production

```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
ALLOWED_ORIGINS=https://doctranslator.com
TRUSTED_HOSTS=doctranslator.com
SETTINGS_ACCESS_CODE=strong-random-code
SECRET_KEY=strong-random-secret
```

---

## Railway Deployment

### Auto-Configured Settings

Railway automatically sets:

```bash
DATABASE_URL=postgresql://...    # From PostgreSQL service
RAILWAY_ENVIRONMENT=production   # Environment name
RAILWAY_PROJECT_ID=your-id       # Project identifier
```

### Required Manual Configuration

Set these in Railway project variables:

```bash
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token
SETTINGS_ACCESS_CODE=your-secure-code
SECRET_KEY=your-random-secret
ALLOWED_ORIGINS=https://yourdomain.com
```

### Railway-Specific Best Practices

1. **Never hardcode secrets** - Use Railway variables
2. **Set specific CORS origins** - Don't use `*` in production
3. **Change default access codes** - Generate secure random values
4. **Monitor configuration** - Use validation endpoint regularly

---

## Security Best Practices

### 1. Secret Key Generation

```bash
# Generate secure random secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Access Code Security

- **Never use default** `admin123` in production
- Generate random access code
- Rotate periodically
- Store securely in Railway variables

### 3. CORS Configuration

```bash
# Development - Allow all
ALLOWED_ORIGINS=*

# Production - Specific domains only
ALLOWED_ORIGINS=https://doctranslator.com,https://app.doctranslator.com
```

### 4. Trusted Hosts

```bash
# Development - Allow all
TRUSTED_HOSTS=*

# Production - Specific hosts
TRUSTED_HOSTS=doctranslator.com,*.doctranslator.com
```

### 5. Secrets Management

- Use environment variables for secrets
- Never commit `.env` files
- Use `.env.example` as template (no real values)
- Rotate secrets regularly
- Use Railway secrets for sensitive data

---

## Troubleshooting

### Configuration Not Loading

**Symptom:** Settings not being read from `.env`

**Solutions:**
1. Ensure `.env` file is in `backend/` directory
2. Check file permissions: `chmod 600 .env`
3. Verify no syntax errors in `.env`
4. Check application logs for validation errors

### Validation Errors on Startup

**Symptom:** Application fails to start with configuration errors

**Solutions:**
1. Check required settings are set:
   ```bash
   echo $DATABASE_URL
   echo $OVH_AI_ENDPOINTS_ACCESS_TOKEN
   ```
2. Validate DATABASE_URL format
3. Check logs for specific validation failures
4. Run validation endpoint manually

### Feature Flags Not Working

**Symptom:** Feature flag changes not taking effect

**Priority Check:**
1. Check environment variables (highest priority)
2. Check database via admin API
3. Check config defaults
4. Check hardcoded defaults

**Debug:**
```python
from app.services.feature_flags import FeatureFlags, Feature
flags = FeatureFlags(session=db, settings=settings)
print(flags.is_enabled(Feature.VISION_LLM_FALLBACK))  # Check current state
```

---

## Reference

### Configuration Files

- `backend/app/core/config.py` - Settings class definition
- `backend/.env.example` - Environment template
- `backend/.env` - Your configuration (not in git)

### Feature Flag Files

- `backend/app/services/feature_flags.py` - Feature flag service
- `backend/app/database/migrations/add_feature_flags.py` - Database migration

### API Endpoints

- `GET /api/admin/config` - Get configuration
- `GET /api/admin/config/validation` - Validate configuration
- `GET /api/admin/config/feature-flags` - Get feature flags
- `PUT /api/admin/config/feature-flags/{name}` - Update feature flag
- `POST /api/admin/config/reload` - Hot reload configuration

### Related Documentation

- [Feature Flags](FEATURE_FLAGS.md) - Detailed feature flag guide
- [Development](DEVELOPMENT.md) - Development setup
- [Architecture](ARCHITECTURE.md) - System architecture
- [Deployment](DEPLOYMENT.md) - Production deployment

---

## Examples

### Basic Configuration

```python
# app/core/config.py
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = Field(default="DocTranslator")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    database_url: str = Field(...)  # Required

    class Config:
        env_file = ".env"
        case_sensitive = False

# Usage
from app.core.config import settings

print(f"Running {settings.app_name} in {settings.environment}")
```

### Using Settings in FastAPI

```python
from fastapi import Depends
from app.core.config import Settings, get_settings

@router.get("/info")
async def get_info(settings: Settings = Depends(get_settings)):
    return {
        "app": settings.app_name,
        "environment": settings.environment,
        "max_file_size": settings.max_file_size_mb
    }
```

### Feature Flag Integration

```python
from app.services.feature_flags import FeatureFlags, Feature
from app.core.config import settings

async def process_document(db: Session):
    flags = FeatureFlags(session=db, settings=settings)

    # Check feature before using
    if flags.is_enabled(Feature.VISION_LLM_FALLBACK):
        logger.info("Using Vision LLM fallback")
        return await process_with_vision()

    return await process_standard()
```

---

## Support

For issues or questions:

- Check validation endpoint: `GET /api/admin/config/validation`
- Review logs for configuration errors
- Consult `.env.example` for proper format
- See Railway documentation for deployment issues
- Check GitHub issues for known problems
