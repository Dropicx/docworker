# PII Removal Toggle - Implementation Guide

## 🎯 Overview

The PII (Personally Identifiable Information) removal toggle allows users to enable or disable automatic privacy filtering after OCR text extraction. This feature provides flexibility while maintaining GDPR compliance when enabled.

## 🏗️ Architecture

### Flow Diagram
```
Frontend UI Toggle
      ↓
API: PUT /api/pipeline/ocr-config
      ↓
Database: ocr_configuration.pii_removal_enabled
      ↓
Worker: Checks setting before PII removal
      ↓
OptimizedPrivacyFilter (if enabled)
```

## 📊 Database Schema

### Table: `ocr_configuration`

```sql
CREATE TABLE ocr_configuration (
    id INTEGER PRIMARY KEY,
    selected_engine VARCHAR NOT NULL DEFAULT 'PADDLEOCR',
    paddleocr_config JSON,
    vision_llm_config JSON,
    hybrid_config JSON,
    pii_removal_enabled BOOLEAN NOT NULL DEFAULT TRUE,  -- NEW
    last_modified TIMESTAMP DEFAULT NOW(),
    modified_by VARCHAR
);
```

### Default Value
- **Default**: `TRUE` (PII removal enabled by default for GDPR compliance)
- **Type**: Boolean (NOT NULL)

## 🔧 Implementation Details

### 1. Frontend (React + TypeScript)

**File**: `frontend/src/components/settings/PipelineBuilder.tsx`

```typescript
// State management
const [piiRemovalEnabled, setPiiRemovalEnabled] = useState<boolean>(true);

// Load from API
const loadOCRConfig = async () => {
  const config = await pipelineApi.getOCRConfig();
  setPiiRemovalEnabled(config.pii_removal_enabled ?? true);
};

// Save to API
const saveOCRConfig = async () => {
  await pipelineApi.updateOCRConfig({
    selected_engine: selectedEngine,
    pii_removal_enabled: piiRemovalEnabled,
    // ... other config
  });
};

// UI Component
<label className="relative inline-flex items-center cursor-pointer">
  <input
    type="checkbox"
    checked={piiRemovalEnabled}
    onChange={(e) => setPiiRemovalEnabled(e.target.checked)}
  />
  <span>{piiRemovalEnabled ? 'Aktiviert' : 'Deaktiviert'}</span>
</label>
```

**Location**: OCR Engine Configuration section, below engine selection cards

### 2. Backend API (FastAPI)

**File**: `backend/app/routers/modular_pipeline.py`

**Request Model**:
```python
class OCRConfigRequest(BaseModel):
    selected_engine: OCREngineEnum
    paddleocr_config: Optional[Dict[str, Any]] = None
    vision_llm_config: Optional[Dict[str, Any]] = None
    hybrid_config: Optional[Dict[str, Any]] = None
    pii_removal_enabled: Optional[bool] = True  # NEW
```

**Response Model**:
```python
class OCRConfigResponse(BaseModel):
    id: int
    selected_engine: str
    paddleocr_config: Optional[Dict[str, Any]]
    vision_llm_config: Optional[Dict[str, Any]]
    hybrid_config: Optional[Dict[str, Any]]
    pii_removal_enabled: bool  # NEW
    last_modified: datetime
```

**Endpoints**:
- `GET /api/pipeline/ocr-config` - Returns current config including PII toggle
- `PUT /api/pipeline/ocr-config` - Updates config including PII toggle

### 3. Database Model (SQLAlchemy)

**File**: `backend/app/database/modular_pipeline_models.py`

```python
class OCRConfigurationDB(Base):
    __tablename__ = "ocr_configuration"

    id = Column(Integer, primary_key=True, index=True)
    selected_engine = Column(SQLEnum(OCREngineEnum), default=OCREngineEnum.PADDLEOCR, nullable=False)

    # Engine-specific settings
    paddleocr_config = Column(JSON, nullable=True)
    vision_llm_config = Column(JSON, nullable=True)
    hybrid_config = Column(JSON, nullable=True)

    # Privacy settings
    pii_removal_enabled = Column(Boolean, default=True, nullable=False)  # NEW

    # Metadata
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(String(255), nullable=True)
```

### 4. Worker (Celery Task)

**File**: `worker/tasks/document_processing.py`

```python
# Import OCR configuration model
from app.database.modular_pipeline_models import OCRConfigurationDB

# Check PII toggle before filtering
ocr_config = db.query(OCRConfigurationDB).first()
pii_enabled = ocr_config.pii_removal_enabled if ocr_config else True

if pii_enabled:
    logger.info("🔒 Starting local PII removal...")
    from app.services.optimized_privacy_filter import OptimizedPrivacyFilter

    pii_filter = OptimizedPrivacyFilter()
    extracted_text = pii_filter.remove_pii(extracted_text)

    logger.info(f"✅ PII removal completed")
else:
    logger.info("⏭️  PII removal disabled - skipping privacy filter")
```

**Why Worker Checks the Setting**:
- **Reduced Backend Load**: Worker makes decision independently
- **Database-Driven**: Worker queries fresh config from database
- **Flexible**: Easy to add more worker-side privacy options later
- **Performance**: Avoids passing config through multiple service layers

## 🔄 Database Migration

### Option 1: SQL Script (Recommended for Railway)

**File**: `backend/app/database/migrations/add_pii_removal_toggle.sql`

```bash
# Connect to Railway database
psql postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway

# Run migration
\i backend/app/database/migrations/add_pii_removal_toggle.sql
```

### Option 2: Python Migration Script

```bash
cd backend
python -m app.database.migrations.add_pii_toggle_migration
```

### Migration Steps:
1. Adds `pii_removal_enabled` column with default `TRUE`
2. Updates existing rows to ensure default value
3. Verifies migration success

## 🧪 Testing

### 1. Test Frontend Toggle

1. Navigate to Settings → Pipeline Builder
2. Scroll to "OCR-Engine Konfiguration"
3. Toggle "PII-Entfernung nach OCR" switch
4. Click "Speichern"
5. Refresh page and verify toggle state persists

### 2. Test Worker Behavior

**With PII Enabled** (default):
```
🔒 Starting local PII removal...
✅ PII removal completed in 87.3ms
   Original: 1234 chars → Cleaned: 1198 chars
```

**With PII Disabled**:
```
⏭️  PII removal disabled - skipping privacy filter
```

### 3. Test API Endpoints

```bash
# Get current config
curl -X GET http://localhost:9122/api/pipeline/ocr-config \
  -H "Authorization: Bearer <token>"

# Update config
curl -X PUT http://localhost:9122/api/pipeline/ocr-config \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "selected_engine": "PADDLEOCR",
    "pii_removal_enabled": false
  }'
```

## 📝 User Documentation

### German UI Text

**Section Title**: "PII-Entfernung nach OCR"

**Description**: "Entfernt automatisch personenbezogene Daten (Namen, Adressen, etc.) nach der Texterkennung - lokal und datenschutzkonform"

**Toggle States**:
- ✅ Aktiviert (Enabled) - Default
- ❌ Deaktiviert (Disabled)

### When to Disable

Users might want to disable PII removal when:
- Processing internal documents where privacy is not a concern
- Testing OCR accuracy without modifications
- Processing documents that don't contain PII
- Using custom PII filtering in later pipeline steps

**⚠️ Warning**: Disabling PII removal means raw OCR text (including names, addresses, etc.) will be sent to AI services. Only disable if you understand the privacy implications.

## 🔒 Security Considerations

1. **Default Enabled**: PII removal is ON by default for GDPR compliance
2. **Local Processing**: PII filtering happens locally on worker before any external API calls
3. **Database-Driven**: Setting stored securely in database, not in frontend code
4. **Audit Trail**: Changes logged with timestamp and modified_by field

## 🚀 Deployment Checklist

- [x] Database model updated with `pii_removal_enabled` column
- [x] API request/response models include new field
- [x] Frontend UI toggle implemented and styled
- [x] Worker checks setting before PII removal
- [x] Database seed updated with default value
- [x] Migration script created and tested
- [ ] Run database migration on Railway
- [ ] Deploy backend with updated models
- [ ] Deploy worker with updated logic
- [ ] Deploy frontend with new toggle UI
- [ ] Test end-to-end functionality

## 🐛 Troubleshooting

### Toggle doesn't save
- Check browser console for API errors
- Verify authentication token is valid
- Check backend logs for database errors

### PII still being removed when disabled
- Check worker logs to verify setting is being read
- Ensure database migration was successful
- Restart worker service after config change

### Database column missing
- Run migration script
- Check database schema: `\d ocr_configuration`
- Verify migration executed successfully

## 📚 Related Documentation

- [OPTIMIZED_PII_FILTER.md](./OPTIMIZED_PII_FILTER.md) - Technical details of PII removal system
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Overall system architecture
- [DATABASE.md](./DATABASE.md) - Database schema reference
- [API.md](./API.md) - API endpoint documentation
