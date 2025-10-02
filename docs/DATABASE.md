# Database Architecture

## Overview

DocTranslator uses PostgreSQL in production (Railway) with SQLite fallback for local development. The database manages prompts, pipeline configurations, AI interaction logs, and system settings.

## Database Tables

### 1. universal_prompts
Stores prompts that apply to all document types.

**Columns:**
- `id` - Primary key
- `medical_validation_prompt` - Binary medical classification
- `classification_prompt` - Document type classification
- `preprocessing_prompt` - OCR text preprocessing
- `grammar_check_prompt` - Language correction
- `language_translation_prompt` - Multi-language translation template
- `version` - Prompt version number
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp
- `modified_by` - User/system that modified

### 2. document_specific_prompts
Stores prompts specific to each document type (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE).

**Columns:**
- `id` - Primary key
- `document_type` - ARZTBRIEF | BEFUNDBERICHT | LABORWERTE
- `translation_prompt` - Main translation to patient-friendly language
- `fact_check_prompt` - Medical accuracy verification
- `final_check_prompt` - Quality assurance
- `formatting_prompt` - Markdown structure optimization
- `version` - Prompt version number
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp
- `modified_by` - User/system that modified

### 3. universal_pipeline_steps
Controls which pipeline steps are enabled for ALL document types.

**Columns:**
- `id` - Primary key
- `step_name` - MEDICAL_VALIDATION | CLASSIFICATION | TEXT_EXTRACTION | etc.
- `enabled` - Boolean flag
- `order` - Execution order (1-9)
- `name` - Human-readable name
- `description` - What the step does

### 4. ai_interaction_logs
Comprehensive logging of all AI interactions for analytics and debugging.

**Columns:**
- `id` - Primary key
- `session_id` - Request session identifier
- `step_name` - Pipeline step name
- `model_used` - AI model name
- `input_text` - Input to AI model (truncated if large)
- `output_text` - AI model output (truncated if large)
- `prompt_used` - Full prompt template used
- `processing_time_ms` - Processing duration in milliseconds
- `confidence_score` - AI confidence (if applicable)
- `error_message` - Error details if failed
- `metadata` - JSON field for additional data
- `created_at` - Timestamp

### 5. system_settings
System-wide configuration settings (key-value pairs).

**Columns:**
- `id` - Primary key
- `key` - Setting key (unique)
- `value` - Setting value
- `description` - What the setting controls
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

## Connection Setup

### Environment Variables

**Production (Railway PostgreSQL):**
```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

**Alternative format:**
```bash
POSTGRES_HOST=hostname
POSTGRES_PORT=5432
POSTGRES_DB=doctranslator
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
```

**Local Development:**
```bash
# No configuration needed - SQLite auto-configured
# Database file: backend/doctranslator.db
```

## Database Initialization

### Automatic Initialization
The database tables are created automatically on application startup via `init_db.py`.

### Manual Initialization
```bash
cd backend
python app/database/init_db.py
```

### Seeding Data
```bash
cd backend
python app/database/unified_seed.py
```

This creates:
- 1 universal prompts record
- 3 document-specific prompts records (one per type)
- 9 pipeline step configurations
- System settings

## Migration from Old System

The application has migrated from:
- ❌ File-based JSON prompts → ✅ Database-only prompts
- ❌ Document-specific pipeline configs → ✅ Universal pipeline steps
- ❌ Mixed storage systems → ✅ Single source of truth

All old migration scripts have been removed. The current system is production-ready.

## Analytics Queries

### Processing Success Rates
```sql
SELECT
    step_name,
    COUNT(*) as total,
    SUM(CASE WHEN error_message IS NULL THEN 1 ELSE 0 END) as successful,
    ROUND(100.0 * SUM(CASE WHEN error_message IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM ai_interaction_logs
GROUP BY step_name;
```

### Average Processing Times
```sql
SELECT
    step_name,
    ROUND(AVG(processing_time_ms), 2) as avg_time_ms,
    MIN(processing_time_ms) as min_time_ms,
    MAX(processing_time_ms) as max_time_ms
FROM ai_interaction_logs
WHERE error_message IS NULL
GROUP BY step_name
ORDER BY avg_time_ms DESC;
```

### Recent Errors
```sql
SELECT
    created_at,
    step_name,
    model_used,
    error_message,
    processing_time_ms
FROM ai_interaction_logs
WHERE error_message IS NOT NULL
ORDER BY created_at DESC
LIMIT 20;
```

## Troubleshooting

### Connection Issues
1. Verify `DATABASE_URL` format is correct
2. Check network connectivity to Railway
3. Ensure database user has proper permissions

### Permission Errors
The database user needs:
- CREATE/ALTER permissions for initial setup
- SELECT/INSERT/UPDATE/DELETE for operations

### Debug Logging
Enable SQL query logging:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

This will show all SQL queries in application logs.
