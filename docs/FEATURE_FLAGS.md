# Feature Flags

Comprehensive guide to DocTranslator's feature flag system for runtime feature control.

## Overview

Feature flags enable toggling functionality at runtime without code deployment, supporting:

- **Gradual Rollout** - Enable features incrementally
- **A/B Testing** - Test features with subset of users
- **Emergency Disable** - Quickly disable problematic features
- **Environment-Specific** - Different features per environment

---

## Priority System

Feature flags use a **four-tier priority system** (highest to lowest):

### 1. Environment Variables (Highest Priority)

```bash
# Format: FEATURE_FLAG_{NAME}=true/false
FEATURE_FLAG_VISION_LLM_FALLBACK_ENABLED=false
FEATURE_FLAG_MULTI_FILE_PROCESSING_ENABLED=true
```

**Use When:**
- Emergency disable needed
- Environment-specific overrides (dev vs prod)
- Container/Railway configuration

### 2. Database Configuration

Managed via Admin API endpoints:

```bash
curl -X PUT http://localhost:9122/api/admin/config/feature-flags/vision_llm_fallback_enabled \
  -H "X-Access-Code: your-code" \
  -d '{"enabled": false}'
```

**Use When:**
- Runtime feature toggles without restart
- Gradual rollout percentages
- Quick disable during incidents

### 3. Config Defaults

From `app/core/config.py` Settings:

```python
class Settings(BaseSettings):
    enable_ocr: bool = Field(default=True)
    enable_privacy_filter: bool = Field(default=True)
    enable_multi_file: bool = Field(default=True)
```

**Use When:**
- Default configuration management
- Linking to other settings
- Environment-based defaults

### 4. Hardcoded Defaults (Lowest Priority)

From `app/services/feature_flags.py`:

```python
DEFAULTS = {
    Feature.VISION_LLM_FALLBACK: True,
    Feature.MULTI_FILE_PROCESSING: True,
    Feature.PARALLEL_STEP_EXECUTION: False,  # Experimental
}
```

**Use When:**
- Production-ready defaults
- Safeguards for new features
- Documentation of intended state

---

## Available Feature Flags

### OCR and Text Extraction

#### `vision_llm_fallback_enabled`
- **Default:** `True`
- **Description:** Allow fallback to Vision LLM when local OCR fails
- **Impact:** Enables higher accuracy OCR via AI when Tesseract fails
- **Performance:** Slower but more accurate
- **Cost:** Uses AI tokens

```bash
FEATURE_FLAG_VISION_LLM_FALLBACK_ENABLED=true
```

#### `multi_file_processing_enabled`
- **Default:** `True`
- **Description:** Enable multi-file document processing
- **Impact:** Users can upload and process multiple files at once
- **Performance:** Increased memory usage
- **Cost:** No additional cost

```bash
FEATURE_FLAG_MULTI_FILE_PROCESSING_ENABLED=true
```

### Privacy and Security

#### `advanced_privacy_filter_enabled`
- **Default:** `True`
- **Description:** Use advanced privacy filtering with pattern matching
- **Impact:** Better PII detection and removal
- **Performance:** Slightly slower processing
- **Compliance:** Required for GDPR compliance

```bash
FEATURE_FLAG_ADVANCED_PRIVACY_FILTER_ENABLED=true
```

#### `pii_removal_enabled`
- **Default:** `True`
- **Description:** Enable PII removal in preprocessing step
- **Impact:** Removes personal information before translation
- **Performance:** Minimal impact
- **Compliance:** Required for GDPR compliance

```bash
FEATURE_FLAG_PII_REMOVAL_ENABLED=true
```

### Performance and Monitoring

#### `cost_tracking_enabled`
- **Default:** `True`
- **Description:** Track AI token usage and costs
- **Impact:** Detailed cost analytics available
- **Performance:** Minimal impact
- **Database:** Logs to ai_cost_tracking table

```bash
FEATURE_FLAG_COST_TRACKING_ENABLED=true
```

#### `ai_logging_enabled`
- **Default:** `True`
- **Description:** Log all AI requests and responses
- **Impact:** Full audit trail of AI interactions
- **Performance:** Increased database writes
- **Database:** Logs to ai_interaction_logs table

```bash
FEATURE_FLAG_AI_LOGGING_ENABLED=true
```

#### `parallel_step_execution_enabled`
- **Default:** `False` (Experimental)
- **Description:** Execute independent pipeline steps in parallel
- **Impact:** Faster processing for multi-step pipelines
- **Performance:** Higher CPU and memory usage
- **Status:** Under testing, not production-ready

```bash
FEATURE_FLAG_PARALLEL_STEP_EXECUTION_ENABLED=false
```

### Pipeline Features

#### `dynamic_branching_enabled`
- **Default:** `True`
- **Description:** Enable dynamic pipeline branching based on document type
- **Impact:** Different pipeline paths per document type
- **Performance:** No impact
- **Required:** For document classification system

```bash
FEATURE_FLAG_DYNAMIC_BRANCHING_ENABLED=true
```

#### `stop_conditions_enabled`
- **Default:** `True`
- **Description:** Enable pipeline stop conditions
- **Impact:** Pipeline can stop early based on conditions
- **Performance:** Potential performance improvement (early stops)
- **Use Cases:** Skip translation for non-medical documents

```bash
FEATURE_FLAG_STOP_CONDITIONS_ENABLED=true
```

#### `retry_on_failure_enabled`
- **Default:** `True`
- **Description:** Automatically retry failed pipeline steps
- **Impact:** More resilient processing
- **Performance:** Increased processing time on failures
- **Retries:** Configurable max retries per step

```bash
FEATURE_FLAG_RETRY_ON_FAILURE_ENABLED=true
```

### Experimental Features

#### `hybrid_ocr_strategy_enabled`
- **Default:** `False` (Experimental)
- **Description:** Use hybrid OCR strategy (Tesseract + Vision LLM)
- **Impact:** Best accuracy combining multiple OCR engines
- **Performance:** Slower, uses multiple services
- **Cost:** Higher AI token usage
- **Status:** Experimental, under development

```bash
FEATURE_FLAG_HYBRID_OCR_STRATEGY_ENABLED=false
```

#### `auto_quality_detection_enabled`
- **Default:** `False` (Experimental)
- **Description:** Automatically detect document quality and choose processing strategy
- **Impact:** Optimized processing based on document quality
- **Performance:** Additional quality check step
- **Status:** Experimental, under development

```bash
FEATURE_FLAG_AUTO_QUALITY_DETECTION_ENABLED=false
```

---

## Usage in Code

### Basic Usage

```python
from app.services.feature_flags import FeatureFlags, Feature
from app.core.config import settings
from sqlalchemy.orm import Session

def process_document(db: Session):
    flags = FeatureFlags(session=db, settings=settings)

    if flags.is_enabled(Feature.VISION_LLM_FALLBACK):
        return process_with_vision()
    else:
        return process_with_tesseract()
```

### Dependency Injection (FastAPI)

```python
from fastapi import Depends
from app.database.connection import get_session
from app.core.config import get_settings

@router.post("/process")
async def process(
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings)
):
    flags = FeatureFlags(session=db, settings=settings)

    if flags.is_enabled(Feature.MULTI_FILE_PROCESSING):
        return await process_multiple_files()
    else:
        return {"error": "Multi-file processing disabled"}
```

### Check Multiple Flags

```python
flags = FeatureFlags(session=db, settings=settings)

# Get all enabled features
enabled = flags.get_enabled_features()
print(f"Enabled features: {enabled}")

# Check specific features
if flags.is_enabled(Feature.COST_TRACKING) and flags.is_enabled(Feature.AI_LOGGING):
    log_ai_usage_with_costs()
```

### Require Feature

```python
flags = FeatureFlags(session=db, settings=settings)

try:
    # Raises RuntimeError if disabled
    flags.require_feature(Feature.ADVANCED_PRIVACY_FILTER)
    # Continue with feature
    apply_advanced_privacy_filter()
except RuntimeError as e:
    logger.error(f"Feature required but disabled: {e}")
    return fallback_privacy_filter()
```

---

## Management via API

### Authentication

All endpoints require `X-Access-Code` header:

```bash
X-Access-Code: your-settings-access-code
```

Set via environment variable:
```bash
SETTINGS_ACCESS_CODE=your-secure-code
```

### Get All Feature Flags

```bash
GET /api/admin/config/feature-flags
```

**Response:**
```json
{
  "flags": {
    "vision_llm_fallback_enabled": true,
    "multi_file_processing_enabled": true,
    "parallel_step_execution_enabled": false,
    ...
  },
  "total_count": 12,
  "enabled_count": 10
}
```

### Update Feature Flag

```bash
PUT /api/admin/config/feature-flags/{flag_name}
```

**Request Body:**
```json
{
  "enabled": false,
  "description": "Temporarily disabled for testing",
  "rollout_percentage": 50
}
```

**Example:**
```bash
curl -X PUT http://localhost:9122/api/admin/config/feature-flags/vision_llm_fallback_enabled \
  -H "X-Access-Code: admin123" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false,
    "description": "Disabled during maintenance",
    "rollout_percentage": 0
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Feature flag 'vision_llm_fallback_enabled' updated successfully",
  "flag": {
    "name": "vision_llm_fallback_enabled",
    "enabled": false,
    "description": "Disabled during maintenance",
    "rollout_percentage": 0
  }
}
```

---

## Best Practices

### 1. Emergency Disable

For quick disables during incidents, use environment variables:

```bash
# In Railway/Docker
FEATURE_FLAG_VISION_LLM_FALLBACK_ENABLED=false

# Or update via API
curl -X PUT .../feature-flags/vision_llm_fallback_enabled \
  -d '{"enabled": false, "description": "Incident: High error rate"}'
```

### 2. Gradual Rollout

Use rollout_percentage for gradual feature releases:

```bash
# Start with 10% of users
curl -X PUT .../feature-flags/new_feature_enabled \
  -d '{"enabled": true, "rollout_percentage": 10}'

# Increase to 50%
curl -X PUT .../feature-flags/new_feature_enabled \
  -d '{"enabled": true, "rollout_percentage": 50}'

# Full rollout
curl -X PUT .../feature-flags/new_feature_enabled \
  -d '{"enabled": true, "rollout_percentage": 100}'
```

### 3. Environment-Specific Configuration

```bash
# Development - Enable all experimental features
FEATURE_FLAG_HYBRID_OCR_STRATEGY_ENABLED=true
FEATURE_FLAG_AUTO_QUALITY_DETECTION_ENABLED=true
FEATURE_FLAG_PARALLEL_STEP_EXECUTION_ENABLED=true

# Production - Stable features only
FEATURE_FLAG_HYBRID_OCR_STRATEGY_ENABLED=false
FEATURE_FLAG_AUTO_QUALITY_DETECTION_ENABLED=false
FEATURE_FLAG_PARALLEL_STEP_EXECUTION_ENABLED=false
```

### 4. Documentation

Always document flag changes:

```bash
curl -X PUT .../feature-flags/cost_tracking_enabled \
  -d '{
    "enabled": false,
    "description": "Disabled 2025-01-13: Database performance issue. Re-enable after migration."
  }'
```

### 5. Monitoring

Monitor feature flag usage:

```python
flags = FeatureFlags(session=db, settings=settings)

# Log feature flag status on startup
enabled = flags.get_enabled_features()
logger.info(f"Feature flags enabled: {', '.join(enabled)}")

# Log when features are used
if flags.is_enabled(Feature.VISION_LLM_FALLBACK):
    logger.info("Using Vision LLM fallback (feature flag enabled)")
```

---

## Database Schema

### feature_flags Table

```sql
CREATE TABLE feature_flags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    description TEXT,
    rollout_percentage INTEGER DEFAULT 0 CHECK (rollout_percentage >= 0 AND rollout_percentage <= 100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_feature_flags_name ON feature_flags(name);
```

### Example Queries

```sql
-- Get all enabled flags
SELECT name, description, rollout_percentage
FROM feature_flags
WHERE enabled = true;

-- Update flag
UPDATE feature_flags
SET enabled = false,
    description = 'Disabled for testing',
    updated_at = NOW()
WHERE name = 'vision_llm_fallback_enabled';

-- Check flag status
SELECT enabled FROM feature_flags
WHERE name = 'cost_tracking_enabled';
```

---

## Troubleshooting

### Flag Not Taking Effect

**Check Priority Order:**

1. Check environment variable:
```bash
echo $FEATURE_FLAG_VISION_LLM_FALLBACK_ENABLED
```

2. Check database:
```sql
SELECT * FROM feature_flags WHERE name = 'vision_llm_fallback_enabled';
```

3. Check config defaults in `app/core/config.py`

4. Check hardcoded defaults in `app/services/feature_flags.py`

### Database Not Updating

**Verify Table Exists:**
```bash
python app/database/migrations/add_feature_flags.py
```

**Check Permissions:**
```sql
GRANT SELECT, INSERT, UPDATE ON feature_flags TO your_user;
```

### API Authentication Failing

**Verify Access Code:**
```bash
# Check environment
echo $SETTINGS_ACCESS_CODE

# Test endpoint
curl -X GET http://localhost:9122/api/admin/config/feature-flags \
  -H "X-Access-Code: your-code" \
  -v
```

---

## Migration Guide

### From Hardcoded to Feature Flags

**Before:**
```python
# Hardcoded feature check
if USE_VISION_LLM:
    process_with_vision()
```

**After:**
```python
from app.services.feature_flags import FeatureFlags, Feature

flags = FeatureFlags(session=db, settings=settings)
if flags.is_enabled(Feature.VISION_LLM_FALLBACK):
    process_with_vision()
```

### Adding New Feature Flags

1. **Define in Feature enum:**
```python
# app/services/feature_flags.py
class Feature(str, Enum):
    NEW_FEATURE = "new_feature_enabled"
```

2. **Add default:**
```python
DEFAULTS = {
    Feature.NEW_FEATURE: False,  # Disabled by default
}
```

3. **Seed in database:**
```sql
INSERT INTO feature_flags (name, enabled, description)
VALUES ('new_feature_enabled', FALSE, 'Description of new feature');
```

4. **Use in code:**
```python
if flags.is_enabled(Feature.NEW_FEATURE):
    use_new_feature()
```

---

## Reference

### Files

- `app/services/feature_flags.py` - Feature flag service and enum
- `app/database/migrations/add_feature_flags.py` - Database migration
- `app/routers/admin/config.py` - Admin API endpoints
- `.env.example` - Environment variable examples

### Related Documentation

- [Configuration Management](CONFIGURATION.md)
- [Architecture](ARCHITECTURE.md)
- [Development Guide](DEVELOPMENT.md)

### API Endpoints

- `GET /api/admin/config/feature-flags` - Get all flags
- `PUT /api/admin/config/feature-flags/{name}` - Update flag
- `GET /api/admin/config/validation` - Validate configuration

---

## Support

For issues or questions:

- Check logs for feature flag status
- Use validation endpoint to verify configuration
- Review priority order if flags not working
- Check database for flag status
- Consult configuration documentation

