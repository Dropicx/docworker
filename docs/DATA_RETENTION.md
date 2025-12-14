# Data Retention & Privacy Policy

## Overview

DocTranslator implements a **privacy-first approach** with automated data retention policies and PII removal to ensure GDPR compliance.

## Data Storage

### What Gets Stored

When a document is processed, the following data is stored in PostgreSQL:

| Data Type | Stored? | Duration | Privacy Status |
|-----------|---------|----------|----------------|
| Original uploaded file | ✅ Yes | 24 hours | Binary (encrypted at rest) |
| PII-cleaned OCR text | ✅ Yes | 24 hours | **Safe** - Sensitive data removed + encrypted at rest |
| Translated output | ✅ Yes | 24 hours | **Safe** - No PII + encrypted at rest |
| Processing metadata | ✅ Yes | 24 hours | Non-sensitive |
| Client IP address | ✅ Yes | 24 hours | For security logging |

**Note:** All document content (file_content, input_text, output_text) is encrypted at rest using field-level encryption, regardless of user consent status. Consent only determines retention (keep vs delete), not encryption.

### What Gets Removed

**Before AI Processing** (Step 1.5):
- ✅ Names (people, organizations)
- ✅ Addresses (street, city, postal codes)
- ✅ Phone numbers
- ✅ Email addresses
- ✅ Dates of birth
- ✅ Insurance numbers
- ✅ Patient IDs
- ✅ Other PII detected by spaCy NER

**After Retention Period**:
- ✅ All database records (complete job data)
- ✅ File content
- ✅ Processing results
- ✅ All metadata

## Retention Configuration

### Default Settings

- **Database Retention**: 24 hours (development/testing)
- **Temporary Files**: 1 hour
- **In-Memory Cache**: 30 minutes

### Environment Variables

Configure retention periods via environment variables:

```bash
# Database retention in hours (default: 24)
DB_RETENTION_HOURS=24

# For production, reduce to minimum (e.g., 1 hour)
DB_RETENTION_HOURS=1
```

### Recommended Production Settings

```bash
# Minimum retention for production
DB_RETENTION_HOURS=1  # Delete jobs after 1 hour

# For high-security environments
DB_RETENTION_HOURS=0  # Immediate deletion after processing
```

## Cleanup Schedule

### Automatic Cleanup

**Celery Worker** runs scheduled cleanup tasks:

```python
# Runs every hour
@celery_app.task(name='cleanup_old_files')
def cleanup_old_files():
    """
    Cleans up:
    - Temporary files (>1 hour old)
    - In-memory cache (>30 minutes old)
    - Database jobs (>DB_RETENTION_HOURS old)
    """
```

**What Gets Cleaned**:
1. **Temporary Files** (every hour)
   - Files in `/tmp` matching patterns: `medical_*`, `uploaded_*`, `processed_*`
   - Older than 1 hour

2. **In-Memory Store** (every hour)
   - Processing data in worker memory
   - Older than 30 minutes

3. **Database Jobs** (every hour)
   - Complete pipeline jobs (all statuses)
   - Older than `DB_RETENTION_HOURS`

### Manual Cleanup

**Emergency Cleanup** (admin only):

```python
from app.services.cleanup import emergency_cleanup

# Deletes ALL completed jobs immediately
await emergency_cleanup()
```

⚠️ **Warning**: Emergency cleanup removes all completed jobs regardless of age. Use only when necessary.

## Data Flow & Privacy

### Processing Pipeline

```
1. Upload Document
   └─> Store in database (binary)

2. OCR Extraction
   └─> Extract raw text

3. PII Removal ← 🔒 PRIVACY STEP
   └─> Remove sensitive data with spaCy NER
   └─> Result: Privacy-safe text

4. AI Processing
   └─> Use PII-cleaned text only
   └─> No sensitive data sent to AI

5. Store Results
   └─> Save PII-cleaned text + output
   └─> Original sensitive data never stored

6. Automatic Cleanup (after retention period)
   └─> Delete all job data
   └─> Zero data retention achieved
```

### Privacy Guarantees

✅ **Sensitive data NEVER sent to AI services**
- PII removed locally before any external API calls
- Uses spaCy NER (runs on your server)
- No external PII detection services

✅ **Sensitive data NEVER stored in database**
- `original_text` field contains PII-cleaned text
- Safe to use for fact-checking in pipeline steps
- Original raw OCR text never persisted

✅ **Automatic data deletion**
- Configurable retention period
- Scheduled hourly cleanup
- Emergency cleanup available

## GDPR Compliance

### Article 5(1)(e) - Storage Limitation

> Personal data shall be kept in a form which permits identification of data subjects for no longer than is necessary.

**Compliance**: Data deleted after 24 hours (configurable down to 0 hours)

### Article 17 - Right to Erasure

> The data subject shall have the right to obtain from the controller the erasure of personal data.

**Compliance**: Automatic erasure via retention policy + emergency cleanup option

### Article 25 - Data Protection by Design

> The controller shall implement appropriate technical and organisational measures for ensuring that, by default, only personal data which are necessary for each specific purpose of the processing are processed.

**Compliance**: PII removal by default, minimal data storage, EU-based processing

### Article 32 - Security of Processing

> The controller and processor shall implement appropriate technical and organisational measures to ensure a level of security appropriate to the risk.

**Compliance**:
- Encrypted transport (HTTPS/TLS)
- **Encrypted storage at rest** (field-level encryption for all document content)
  - Binary files (file_content) encrypted using Fernet
  - Text content (input_text, output_text) encrypted using Fernet
  - Encryption is transparent to application layer
- Secure file deletion
- Limited retention period
- Access logging

**Encryption Details:**
- All document content is encrypted when stored, regardless of user consent
- Consent determines retention (keep vs delete), encryption is always applied
- Binary fields: binary → base64 → encrypt → store as UTF-8 bytes
- Text fields: text → encrypt → store as encrypted string
- See `backend/docs/ENCRYPTION.md` for technical details

## Monitoring & Auditing

### Cleanup Logs

Monitor cleanup operations in worker logs:

```bash
# Successful cleanup
🧹 Cleanup: 5 files, 3 memory items, 12 database jobs removed

# Job deletion details
🗑️ Found 12 jobs older than 24 hours
   Deleting job abc123 (age: 26.3h, status: COMPLETED)
✅ Deleted 12 old database jobs
```

### Health Check

Verify cleanup system is working:

```bash
# Check last cleanup execution
curl https://your-app.up.railway.app/api/health/detailed

# Response includes cleanup status
{
  "cleanup": {
    "last_run": "2025-01-09T14:30:00Z",
    "jobs_cleaned": 12,
    "status": "healthy"
  }
}
```

## Development vs Production

### Development Mode (Current)

```bash
DB_RETENTION_HOURS=24  # Keep jobs for 24 hours for review
```

**Use Case**: Testing, debugging, reviewing pipeline outputs

### Production Mode (Recommended)

```bash
DB_RETENTION_HOURS=1   # Keep jobs for 1 hour only
```

**Use Case**: Production deployment with minimal data retention

### High-Security Mode

```bash
DB_RETENTION_HOURS=0   # Delete immediately after processing
```

**Use Case**: Maximum privacy, zero data retention

⚠️ **Note**: With `DB_RETENTION_HOURS=0`, users must download results immediately or they'll be lost.

## Privacy Filter Configuration

### Enable/Disable PII Removal

PII removal can be toggled via Settings UI or API:

```python
# Update OCR configuration
PUT /api/pipeline/ocr-config
{
  "pii_removal_enabled": true  # Default: true
}
```

⚠️ **Warning**: Disabling PII removal will store sensitive data in database. Only disable for testing in isolated environments.

### PII Detection

Uses **spaCy German NER model** (`de_core_news_lg`):
- Recognizes German language entities
- Detects: `PER` (person), `LOC` (location), `ORG` (organization), `MISC` (miscellaneous)
- Includes custom patterns for:
  - Phone numbers
  - Email addresses
  - Dates (DD.MM.YYYY format)
  - Postal codes
  - Insurance numbers

See [OPTIMIZED_PII_FILTER.md](./OPTIMIZED_PII_FILTER.md) for technical details.

## Security Best Practices

### For Development

1. ✅ Keep retention at 24 hours for review
2. ✅ Use isolated development database
3. ✅ Never use production data
4. ✅ Enable PII removal (always)

### For Production

1. ✅ Reduce retention to 1 hour or less
2. ✅ Monitor cleanup logs
3. ✅ Use EU-based infrastructure only
4. ✅ Enable HTTPS (automatic on Railway)
5. ✅ Regular security audits

### For High-Security Environments

1. ✅ Set `DB_RETENTION_HOURS=0`
2. ✅ Implement immediate download enforcement
3. ✅ Add audit logging for all access
4. ✅ Use separate database instances
5. ✅ Regular penetration testing

## Troubleshooting

### Jobs Not Being Deleted

**Check cleanup task is running**:
```bash
# Worker logs should show hourly cleanup
docker-compose logs worker | grep "Cleanup"
```

**Verify retention setting**:
```bash
echo $DB_RETENTION_HOURS
```

**Manual cleanup**:
```bash
# Run cleanup manually
docker-compose exec worker python -c "
import asyncio
from app.services.cleanup import cleanup_old_database_jobs
asyncio.run(cleanup_old_database_jobs())
"
```

### Too Aggressive Cleanup

**Increase retention period**:
```bash
DB_RETENTION_HOURS=48  # Increase to 48 hours
```

**Disable automatic cleanup temporarily**:
```python
# Comment out in worker beat schedule
# 'cleanup-old-files': {
#     'task': 'cleanup_old_files',
#     'schedule': crontab(minute=0),  # Every hour
# },
```

## Related Documentation

- **[OPTIMIZED_PII_FILTER.md](./OPTIMIZED_PII_FILTER.md)** - PII detection implementation
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System architecture and data flow
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Production deployment with privacy settings

---

**Version**: 1.0.0
**Last Updated**: January 2025
**Compliance**: GDPR Articles 5, 17, 25, 32
