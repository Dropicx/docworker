# Database Architecture

## Overview

DocTranslator uses **PostgreSQL 16** in production (Railway managed) with SQLite fallback for local development. The database manages:

- Document processing jobs with encrypted file storage
- User accounts and authentication
- Pipeline configuration and execution tracking
- AI interaction logs and cost tracking
- System settings and feature flags
- Audit logs for GDPR compliance

---

## Entity Relationship Diagram

```
┌─────────────────┐       ┌──────────────────────┐
│     users       │       │   pipeline_jobs      │
├─────────────────┤       ├──────────────────────┤
│ id (PK)         │       │ job_id (PK)          │
│ email           │       │ processing_id        │
│ password_hash   │──────▶│ user_id (FK)         │
│ role            │       │ file_content (enc)   │
│ is_active       │       │ status               │
└────────┬────────┘       │ target_language      │
         │                └──────────┬───────────┘
         │                           │
┌────────▼────────┐       ┌──────────▼───────────┐
│   user_roles    │       │ pipeline_step_exec   │
├─────────────────┤       ├──────────────────────┤
│ id (PK)         │       │ id (PK)              │
│ user_id (FK)    │       │ job_id (FK)          │
│ role_name       │       │ step_name            │
└─────────────────┘       │ status               │
                          │ result               │
┌─────────────────┐       │ tokens_used          │
│   api_keys      │       └──────────────────────┘
├─────────────────┤
│ id (PK)         │       ┌──────────────────────┐
│ user_id (FK)    │       │ ai_interaction_logs  │
│ key_hash        │       ├──────────────────────┤
│ expires_at      │       │ id (PK)              │
└─────────────────┘       │ job_id (FK)          │
                          │ step_name            │
┌─────────────────┐       │ model_used           │
│  audit_logs     │       │ tokens (input/output)│
├─────────────────┤       │ cost_usd             │
│ id (PK)         │       └──────────────────────┘
│ user_id (FK)    │
│ action          │       ┌──────────────────────┐
│ resource        │       │ dynamic_pipeline_steps│
│ timestamp       │       ├──────────────────────┤
└─────────────────┘       │ id (PK)              │
                          │ name                 │
┌─────────────────┐       │ prompt_template      │
│feedback_responses│      │ model_id (FK)        │
├─────────────────┤       │ order                │
│ id (PK)         │       │ enabled              │
│ job_id (FK)     │       └──────────────────────┘
│ rating          │
│ comment         │       ┌──────────────────────┐
│ consent_given   │       │  available_models    │
└─────────────────┘       ├──────────────────────┤
                          │ id (PK)              │
┌─────────────────┐       │ model_name           │
│ system_settings │       │ provider             │
├─────────────────┤       │ input_price_per_1m   │
│ id (PK)         │       │ output_price_per_1m  │
│ key             │       │ is_active            │
│ value           │       └──────────────────────┘
│ category        │
│ is_encrypted    │       ┌──────────────────────┐
└─────────────────┘       │  ocr_configuration   │
                          ├──────────────────────┤
                          │ id (PK)              │
                          │ selected_engine      │
                          │ tesseract_config     │
                          │ paddleocr_config     │
                          └──────────────────────┘
```

---

## Core Tables

### pipeline_jobs

**Purpose**: Document processing jobs with encrypted file content storage.

```sql
CREATE TABLE pipeline_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    processing_id UUID UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id),

    -- File information
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size INTEGER NOT NULL,
    file_content BYTEA,              -- Encrypted binary storage

    -- Processing configuration (snapshot at job time)
    target_language VARCHAR(10) DEFAULT 'de',
    document_class VARCHAR(50),
    pipeline_config JSONB,           -- Pipeline snapshot
    ocr_config JSONB,                -- OCR settings snapshot

    -- Status tracking
    status VARCHAR(50) DEFAULT 'PENDING',
    progress_percent INTEGER DEFAULT 0,
    current_step VARCHAR(100),
    error_message TEXT,

    -- Results
    result_data JSONB,               -- Final translation result
    original_text TEXT,
    simplified_text TEXT,
    translated_text TEXT,

    -- Cost tracking
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10, 6) DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,

    -- Indexes
    INDEX idx_jobs_status (status),
    INDEX idx_jobs_user (user_id),
    INDEX idx_jobs_created (created_at)
);
```

**Status Values**: `PENDING`, `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `TIMEOUT`, `TERMINATED`

### pipeline_step_executions

**Purpose**: Individual step execution records for each job.

```sql
CREATE TABLE pipeline_step_executions (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES pipeline_jobs(job_id) ON DELETE CASCADE,

    -- Step information
    step_id INTEGER REFERENCES dynamic_pipeline_steps(id),
    step_name VARCHAR(100) NOT NULL,
    step_order INTEGER NOT NULL,

    -- Execution status
    status VARCHAR(50) DEFAULT 'PENDING',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,

    -- Results
    input_text TEXT,
    output_text TEXT,
    error_message TEXT,

    -- AI metrics (if AI step)
    model_used VARCHAR(100),
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd DECIMAL(10, 6),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_exec_job (job_id),
    INDEX idx_exec_status (status)
);
```

### ai_interaction_logs

**Purpose**: Token usage and cost tracking for all AI API calls.

```sql
CREATE TABLE ai_interaction_logs (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES pipeline_jobs(job_id),

    -- Request context
    step_name VARCHAR(100) NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    prompt_type VARCHAR(100),

    -- Token counts (NO text content stored - privacy)
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,

    -- Cost (calculated from dynamic pricing)
    input_cost_usd DECIMAL(10, 8),
    output_cost_usd DECIMAL(10, 8),
    total_cost_usd DECIMAL(10, 8),

    -- Performance
    latency_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_code VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_logs_job (job_id),
    INDEX idx_logs_model (model_used),
    INDEX idx_logs_created (created_at)
);
```

**Note**: No prompt or response text is stored - only metadata for cost tracking.

---

## Authentication Tables

### users

**Purpose**: User accounts with password authentication.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    -- Account status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,

    -- Security
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    last_login TIMESTAMP,
    last_password_change TIMESTAMP,

    -- Profile
    display_name VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_users_email (email)
);
```

### user_roles

**Purpose**: Role-based access control.

```sql
CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_name VARCHAR(50) NOT NULL,  -- ADMIN, USER, VIEWER
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by UUID REFERENCES users(id),

    UNIQUE(user_id, role_name)
);
```

**Roles**:
- `ADMIN` - Full access, user management, settings
- `USER` - Document upload and processing
- `VIEWER` - Read-only access

### api_keys

**Purpose**: API key authentication for programmatic access.

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Key (hashed)
    key_prefix VARCHAR(10) NOT NULL,  -- First 8 chars for identification
    key_hash VARCHAR(255) NOT NULL,

    -- Metadata
    name VARCHAR(100),
    description TEXT,

    -- Permissions
    scopes JSONB DEFAULT '["read", "write"]',

    -- Expiration
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    revoked_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_apikeys_user (user_id),
    INDEX idx_apikeys_prefix (key_prefix)
);
```

### refresh_tokens

**Purpose**: JWT refresh token tracking for revocation.

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,

    -- Client info
    user_agent TEXT,
    ip_address VARCHAR(45),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_refresh_user (user_id),
    INDEX idx_refresh_hash (token_hash)
);
```

---

## Configuration Tables

### dynamic_pipeline_steps

**Purpose**: User-configurable pipeline step definitions.

```sql
CREATE TABLE dynamic_pipeline_steps (
    id SERIAL PRIMARY KEY,

    -- Step identity
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    description TEXT,

    -- Execution
    order_index INTEGER NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,

    -- AI configuration
    model_id VARCHAR(100) REFERENCES available_models(model_name),
    prompt_template TEXT,

    -- Branching logic
    is_branching_step BOOLEAN DEFAULT FALSE,
    branching_field VARCHAR(100),
    terminates_on_false BOOLEAN DEFAULT FALSE,

    -- Document class specific
    document_class_id INTEGER REFERENCES document_classes(id),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_steps_order (order_index)
);
```

### available_models

**Purpose**: AI model registry with dynamic pricing.

```sql
CREATE TABLE available_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) UNIQUE NOT NULL,
    provider VARCHAR(50) NOT NULL,     -- 'ovh', 'openai', etc.
    display_name VARCHAR(200),

    -- Pricing (per 1 million tokens)
    input_price_per_1m DECIMAL(10, 6) NOT NULL,
    output_price_per_1m DECIMAL(10, 6) NOT NULL,

    -- Capabilities
    max_tokens INTEGER DEFAULT 4096,
    supports_vision BOOLEAN DEFAULT FALSE,
    supports_streaming BOOLEAN DEFAULT TRUE,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Default Models**:
```sql
INSERT INTO available_models (model_name, provider, input_price_per_1m, output_price_per_1m)
VALUES
    ('Meta-Llama-3.3-70B-Instruct', 'ovh', 3.00, 3.00),
    ('Mistral-Nemo-Instruct-2407', 'ovh', 0.30, 0.30),
    ('Qwen2.5-VL-72B-Instruct', 'ovh', 4.00, 4.00);
```

### document_classes

**Purpose**: Custom document type definitions.

```sql
CREATE TABLE document_classes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,  -- ARZTBRIEF, BEFUNDBERICHT, LABORWERTE
    display_name VARCHAR(200),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### ocr_configuration

**Purpose**: OCR engine selection and settings.

```sql
CREATE TABLE ocr_configuration (
    id SERIAL PRIMARY KEY,
    selected_engine VARCHAR(50) NOT NULL,  -- TESSERACT, PADDLEOCR, VISION_LLM, HYBRID

    -- Engine-specific configs (JSONB)
    tesseract_config JSONB DEFAULT '{"languages": ["deu", "eng"]}',
    paddleocr_config JSONB DEFAULT '{"service_url": null}',
    vision_llm_config JSONB DEFAULT '{"model": "Qwen2.5-VL-72B-Instruct"}',
    hybrid_config JSONB DEFAULT '{"quality_threshold": 0.6}',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### system_settings

**Purpose**: Application-wide configuration (key-value).

```sql
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    category VARCHAR(100),
    description TEXT,

    -- Encryption for sensitive values
    is_encrypted BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Common Settings**:
```sql
INSERT INTO system_settings (key, value, category) VALUES
    ('data_retention_hours', '24', 'privacy'),
    ('max_file_size_mb', '50', 'upload'),
    ('rate_limit_per_minute', '5', 'security'),
    ('pii_removal_enabled', 'true', 'privacy'),
    ('external_pii_url', 'https://pii.domain.de', 'external'),
    ('encryption_key', '...', 'security');  -- is_encrypted=true
```

---

## Audit & Compliance Tables

### audit_logs

**Purpose**: Security and compliance audit trail.

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),

    -- Action details
    action VARCHAR(100) NOT NULL,      -- LOGIN, LOGOUT, CREATE, UPDATE, DELETE
    resource_type VARCHAR(100),        -- user, job, setting
    resource_id VARCHAR(255),

    -- Request context
    ip_address VARCHAR(45),
    user_agent TEXT,

    -- Details
    details JSONB,
    success BOOLEAN DEFAULT TRUE,

    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_audit_user (user_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_created (created_at)
);
```

### feedback_responses

**Purpose**: User feedback with GDPR consent.

```sql
CREATE TABLE feedback_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES pipeline_jobs(job_id),
    user_id UUID REFERENCES users(id),

    -- Feedback
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,

    -- GDPR
    consent_given BOOLEAN NOT NULL DEFAULT FALSE,
    consent_timestamp TIMESTAMP,

    -- Analysis (AI-powered)
    analysis_result JSONB,
    analyzed_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_feedback_job (job_id)
);
```

---

## Connection Configuration

### Production (Railway PostgreSQL)

Railway auto-provides `DATABASE_URL`:

```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

### Local Development

SQLite auto-configured (no setup needed):

```bash
# Default: backend/doctranslator.db
# Override:
DATABASE_URL=sqlite:///./dev.db
```

### Connection Pool Settings

```python
# In core/config.py
SQLALCHEMY_POOL_SIZE = 20
SQLALCHEMY_POOL_OVERFLOW = 40
SQLALCHEMY_POOL_TIMEOUT = 30
SQLALCHEMY_POOL_RECYCLE = 1800  # 30 minutes
```

---

## Database Operations

### Initialize Database

```bash
cd backend
python app/database/init_db.py
```

### Seed Data

```bash
python app/database/unified_seed.py
```

### Migrations (Alembic)

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Analytics Queries

### Processing Success Rate

```sql
SELECT
    DATE(created_at) as date,
    COUNT(*) as total_jobs,
    SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
    ROUND(100.0 * SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM pipeline_jobs
GROUP BY DATE(created_at)
ORDER BY date DESC
LIMIT 30;
```

### Token Usage by Model

```sql
SELECT
    model_used,
    COUNT(*) as calls,
    SUM(total_tokens) as total_tokens,
    SUM(total_cost_usd) as total_cost,
    AVG(latency_ms) as avg_latency_ms
FROM ai_interaction_logs
WHERE created_at > CURRENT_DATE - INTERVAL '30 days'
GROUP BY model_used
ORDER BY total_cost DESC;
```

### Average Processing Time per Step

```sql
SELECT
    step_name,
    COUNT(*) as executions,
    AVG(duration_ms) as avg_duration_ms,
    MIN(duration_ms) as min_duration_ms,
    MAX(duration_ms) as max_duration_ms
FROM pipeline_step_executions
WHERE status = 'COMPLETED'
GROUP BY step_name
ORDER BY avg_duration_ms DESC;
```

### Recent Errors

```sql
SELECT
    pj.processing_id,
    pj.filename,
    pse.step_name,
    pse.error_message,
    pse.created_at
FROM pipeline_step_executions pse
JOIN pipeline_jobs pj ON pse.job_id = pj.job_id
WHERE pse.status = 'FAILED'
ORDER BY pse.created_at DESC
LIMIT 20;
```

### Cost Summary by Day

```sql
SELECT
    DATE(created_at) as date,
    SUM(total_cost_usd) as daily_cost,
    SUM(total_tokens) as daily_tokens,
    COUNT(DISTINCT job_id) as jobs_processed
FROM ai_interaction_logs
WHERE created_at > CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

---

## Data Retention

Jobs and related data are automatically cleaned up:

```sql
-- Cleanup job (runs via Celery Beat)
DELETE FROM pipeline_jobs
WHERE created_at < NOW() - INTERVAL '24 hours'
  AND status IN ('COMPLETED', 'FAILED', 'CANCELLED');
```

Configure retention:
```sql
UPDATE system_settings
SET value = '48'  -- hours
WHERE key = 'data_retention_hours';
```

---

## Encryption

File content is encrypted at rest using Fernet:

```python
from cryptography.fernet import Fernet

# Encryption key stored in system_settings (is_encrypted=true)
key = get_setting('encryption_key')
fernet = Fernet(key)

# Encrypt
encrypted = fernet.encrypt(file_content)

# Decrypt
decrypted = fernet.decrypt(encrypted)
```

---

## Troubleshooting

### Connection Issues

```bash
# Test connection
railway run psql -c "SELECT 1"

# Check pool status
railway logs -s backend | grep "pool"
```

### Performance Issues

```sql
-- Check slow queries
SELECT
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query,
    state
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

### Index Usage

```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

---

*Last Updated: January 2026*
