# Data Encryption at Rest - Technical Documentation

## Overview

DocTranslator implements **field-level encryption at rest** for all personally identifiable information (PII) stored in the database. This ensures compliance with GDPR Article 32 requirements for medical data protection.

**Encrypted Fields:**
- User `email` (PII)
- User `full_name` (PII)
- System settings marked with `is_encrypted=True`
- `PipelineJobDB.file_content` (Binary PDF/image files)
- `PipelineStepExecutionDB.input_text` (OCR extracted text)
- `PipelineStepExecutionDB.output_text` (AI processed text)

**Encryption Method:** AES-128-CBC via Fernet (Python cryptography library)

**Key Features:**
- ✅ Transparent encryption (zero service layer code changes)
- ✅ Searchable encrypted fields via SHA-256 hashes
- ✅ Key rotation support with zero-downtime
- ✅ Performance optimized (<1ms overhead per operation)
- ✅ Enable/disable toggle for development

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer (Unaware)                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ user_service.create_user(email="test@example.com")   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │ Plaintext
┌─────────────────────────▼───────────────────────────────────┐
│            Repository Layer (Encryption Mixin)               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. Generate searchable hash (SHA-256)                │  │
│  │ 2. Encrypt email → base64(Fernet.encrypt(...))       │  │
│  │ 3. Store: email=encrypted, email_searchable=hash     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │ Ciphertext
┌─────────────────────────▼───────────────────────────────────┐
│                      Database (PostgreSQL)                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ email: "gAAAAABk..." (encrypted, 150+ chars)         │  │
│  │ email_searchable: "82888cec35..." (SHA-256 hash)     │  │
│  │ encryption_version: 1 (key version tracking)         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

**1. FieldEncryptor** (`app/core/encryption.py`)
- Singleton encryption service
- Fernet symmetric encryption with base64 encoding
- Searchable hash generation (SHA-256)
- Key rotation support

**2. EncryptedRepositoryMixin** (`app/repositories/base_repository.py`)
- Transparent encryption/decryption
- Auto-generates searchable hashes
- Overrides CRUD methods (create, update, get_by_id, etc.)

**3. UserRepository** (`app/repositories/user_repository.py`)
- Inherits EncryptedRepositoryMixin (order matters!)
- `encrypted_fields = ['email', 'full_name']`
- Uses email_searchable for efficient lookups

**4. PipelineJobRepository** (`app/repositories/pipeline_job_repository.py`)
- Inherits EncryptedRepositoryMixin
- `encrypted_fields = ['file_content']`
- Handles binary field encryption (converts binary → base64 → encrypt → store as UTF-8 bytes)

**5. PipelineStepExecutionRepository** (`app/repositories/pipeline_step_execution_repository.py`)
- Inherits EncryptedRepositoryMixin
- `encrypted_fields = ['input_text', 'output_text']`
- Handles text field encryption

---

## How It Works

### Encryption Flow (Write)

```python
# Service layer code (unchanged)
user_service.create_user(email="patient@hospital.de", full_name="Max Müller")

# Repository intercepts (EncryptedRepositoryMixin.create)
1. Generate hashes:
   email_searchable = SHA256("patient@hospital.de")
   → "82888cec35d445b5d7fd90845b996f05ec7fe94a65f9aa685a9b05c259f2fbd7"

2. Encrypt fields:
   email_encrypted = Fernet.encrypt("patient@hospital.de")
   → "gAAAAABkAhgEaY5itnRfx0SlLdMvxxYpSrr-S..."

3. Store in database:
   INSERT INTO users (
     email,
     email_searchable,
     full_name,
     full_name_searchable
   ) VALUES (
     'gAAAAABkAhgE...',  -- encrypted
     '82888cec35...',     -- hash
     'gAAAAABkAhgF...',  -- encrypted
     'a7f4d8e2bc...'      -- hash
   )
```

### Decryption Flow (Read) - Text Fields

```python
# Service layer code (unchanged)
user = user_repo.get_by_email("patient@hospital.de")

# Repository intercepts (UserRepository.get_by_email)
1. Generate hash for lookup:
   email_hash = SHA256("patient@hospital.de")

2. Query using hash (no decryption needed):
   SELECT * FROM users
   WHERE email_searchable = '82888cec35...'

3. Decrypt result:
   email_decrypted = Fernet.decrypt("gAAAAABkAhgE...")
   → "patient@hospital.de"

4. Return to service:
   user.email = "patient@hospital.de"  # Plaintext
```

### Decryption Flow (Read) - Binary Fields

```python
# Service layer code (unchanged)
job = job_repo.get_by_processing_id("processing-123")

# Repository intercepts (PipelineJobRepository.get_by_processing_id)
1. Query database:
   SELECT * FROM pipeline_jobs WHERE processing_id = 'processing-123'

2. Detect binary field and decrypt:
   encrypted_str = db_job.file_content.decode("utf-8")
   base64_str = Fernet.decrypt(encrypted_str)
   binary_data = base64.b64decode(base64_str)
   → b'%PDF-1.4...'

3. Return to service:
   job.file_content = b'%PDF-1.4...'  # Plaintext binary
```

### Why Searchable Hashes?

**Problem:** Can't query encrypted data without decrypting every row
```sql
-- This doesn't work with encryption:
SELECT * FROM users WHERE email = 'patient@hospital.de'
```

**Solution:** Store SHA-256 hash alongside encrypted value
```sql
-- This works efficiently:
SELECT * FROM users WHERE email_searchable = SHA256('patient@hospital.de')
```

**Security:**
- SHA-256 is one-way (can't reverse to get original)
- Same input = same hash (enables search)
- Different from encryption (can't decrypt a hash)
- Indexed for fast lookups

---

## Key Management

### Production Setup

**1. Generate Encryption Key**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Output: WR_RE1Ortnd5jq_92lrZkuI0YswP9FTuQCn_AZ9qf4c=
```

**2. Store in Railway**
1. Go to Railway project → Variables
2. Add variable:
   ```
   ENCRYPTION_KEY=WR_RE1Ortnd5jq_92lrZkuI0YswP9FTuQCn_AZ9qf4c=
   ```
3. **CRITICAL:** Store backup in 3 secure locations:
   - Railway environment variables (primary)
   - Password manager (1Password, Bitwarden)
   - Encrypted backup file (KeePass, encrypted USB)

**3. Enable Encryption** (default: enabled)
```bash
# Optional: Explicitly enable (default is true)
ENCRYPTION_ENABLED=true
```

### Key Rotation

**Zero-downtime key rotation** using dual-key decryption:

**Step 1: Deploy with dual keys**
```bash
# Add new key while keeping old one
ENCRYPTION_KEY_CURRENT=<new_key>
ENCRYPTION_KEY_PREVIOUS=<old_key>
```

**Step 2: Re-encrypt data**
```bash
python migrations/rotate_encryption_key.py
```

**Step 3: Remove old key**
```bash
# After all data is re-encrypted
ENCRYPTION_KEY=<new_key>
# Remove ENCRYPTION_KEY_PREVIOUS
```

**When to rotate:**
- Every 12 months (recommended)
- After suspected key exposure
- Before major audits
- Compliance requirements

---

## Database Schema

### Users Table

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,

  -- Encrypted PII
  email VARCHAR(255) NOT NULL,  -- ENCRYPTED (150+ chars ciphertext)
  full_name VARCHAR(255) NOT NULL,  -- ENCRYPTED

  -- Searchable hashes (indexed)
  email_searchable VARCHAR(64),  -- SHA-256 hash
  full_name_searchable VARCHAR(64),  -- SHA-256 hash

  -- Encryption metadata
  encryption_version INTEGER NOT NULL DEFAULT 1,

  -- Non-encrypted fields
  password_hash VARCHAR(255) NOT NULL,  -- Already hashed (bcrypt)
  role VARCHAR(20) NOT NULL,
  -- ... other fields
);

-- Indexes for efficient encrypted field lookup
CREATE INDEX idx_users_email_searchable ON users(email_searchable);
CREATE INDEX idx_users_full_name_searchable ON users(full_name_searchable);
```

### Pipeline Jobs Table

```sql
CREATE TABLE pipeline_jobs (
  id INTEGER PRIMARY KEY,

  -- Encrypted document content
  file_content BYTEA NOT NULL,  -- ENCRYPTED (binary PDF/image files)
  -- Note: Encrypted content stored as UTF-8 bytes of base64-encoded Fernet token

  -- Non-encrypted fields
  job_id VARCHAR(255) NOT NULL UNIQUE,
  processing_id VARCHAR(255) NOT NULL,
  filename VARCHAR(255) NOT NULL,
  file_type VARCHAR(50) NOT NULL,
  file_size INTEGER NOT NULL,
  -- ... other fields
);

-- Note: No searchable hash needed for file_content (not queried by content)
```

### Pipeline Step Executions Table

```sql
CREATE TABLE pipeline_step_executions (
  id INTEGER PRIMARY KEY,

  -- Encrypted text content
  input_text TEXT,  -- ENCRYPTED (OCR extracted text)
  output_text TEXT,  -- ENCRYPTED (AI processed text)

  -- Non-encrypted fields
  job_id VARCHAR(255) NOT NULL,
  step_id INTEGER NOT NULL,
  step_name VARCHAR(255) NOT NULL,
  -- ... other fields
);

-- Note: No searchable hash needed for text fields (not queried by content)
```

### System Settings Table

```sql
CREATE TABLE system_settings (
  id INTEGER PRIMARY KEY,
  key VARCHAR(255) UNIQUE NOT NULL,

  value TEXT NOT NULL,  -- ENCRYPTED if is_encrypted=true
  is_encrypted BOOLEAN NOT NULL DEFAULT FALSE,

  -- ... other fields
);
```

---

## Operational Procedures

### Initial Deployment (New System)

```bash
# 1. Generate and store encryption key
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 2. Set environment variables
export ENCRYPTION_KEY="$ENCRYPTION_KEY"

# 3. Deploy code
git push railway main

# 4. Verify encryption is working
# Create test user and verify database shows ciphertext
```

### Migrating Existing System

```bash
# 1. Generate and set encryption key
export ENCRYPTION_KEY="<your_key_here>"

# 2. Run schema migration (adds columns)
python migrations/add_encryption_search_fields.py

# 3. Run data migration (encrypts existing data)
# Dry run first
python migrations/encrypt_existing_user_data.py --dry-run

# Real migration
python migrations/encrypt_existing_user_data.py

# 4. Verify
# Check that users.email contains ciphertext
# Check that email_searchable contains hash
```

### Disabling Encryption (Development Only)

```bash
# NEVER do this in production!
export ENCRYPTION_ENABLED=false

# Data will be stored as plaintext
# Useful for local development/debugging
```

---

## Troubleshooting

### Issue: "ENCRYPTION_KEY environment variable is not set"

**Cause:** Encryption key not configured

**Solution:**
```bash
# Set the encryption key
export ENCRYPTION_KEY="<your_key_here>"

# Or add to .env file (development only)
echo "ENCRYPTION_KEY=<your_key_here>" >> .env
```

---

### Issue: "Encryption failed: Invalid key"

**Cause:** Invalid Fernet key format

**Solution:**
```bash
# Generate a NEW valid key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Use the output as ENCRYPTION_KEY
```

---

### Issue: "Failed to decrypt field"

**Possible Causes:**
1. Wrong encryption key
2. Data encrypted with different key
3. Corrupted ciphertext

**Debug Steps:**
```python
# Check if value is encrypted
from app.core.encryption import encryptor
value = "<database_value>"
print(f"Is encrypted: {encryptor.is_encrypted(value)}")

# Try decryption
try:
    decrypted = encryptor.decrypt_field(value)
    print(f"Decrypted: {decrypted}")
except Exception as e:
    print(f"Decryption failed: {e}")
```

**Solutions:**
- Verify ENCRYPTION_KEY matches the key used to encrypt
- Check encryption_version in database
- Use key rotation if data was encrypted with old key

---

### Issue: get_by_email() not finding users

**Cause:** Searchable hash not generated for existing data

**Solution:**
```bash
# Re-run data migration to generate hashes
python migrations/encrypt_existing_user_data.py
```

---

### Issue: Performance degradation

**Symptoms:** Slow user lookups

**Debug:**
```sql
-- Check if indexes exist
SELECT indexname FROM pg_indexes
WHERE tablename = 'users'
AND indexname IN ('idx_users_email_searchable', 'idx_users_full_name_searchable');

-- Check query plan
EXPLAIN ANALYZE
SELECT * FROM users
WHERE email_searchable = '<hash>';
```

**Solutions:**
- Ensure indexes exist on searchable columns
- Run `ANALYZE users;` to update statistics
- Check encryption overhead (should be <1ms)

---

## Security Considerations

### What is Protected

✅ **Email addresses** - Encrypted in database, decrypted in application
✅ **Full names** - Encrypted in database, decrypted in application
✅ **Sensitive system settings** - Optional encryption per setting
✅ **Document file content** - Binary PDF/image files encrypted at rest
✅ **OCR extracted text** - Input text from document processing encrypted
✅ **AI processed text** - Output text from AI processing encrypted
✅ **Data at rest** - Protected if database is compromised

### What is NOT Protected

❌ **Password hashes** - Already hashed with bcrypt (not encrypted)
❌ **Data in transit** - Use HTTPS/TLS (separate concern)
❌ **Data in memory** - Plaintext in application memory
❌ **Application logs** - Don't log PII
❌ **Database backups** - Encrypted data remains encrypted

### Threat Model

**Protected Against:**
- Database dump theft (data is encrypted)
- Database backup exposure (ciphertext only)
- SQL injection (reads ciphertext)
- Unauthorized database access (needs encryption key)

**NOT Protected Against:**
- Application compromise (has encryption key)
- Memory dumps (plaintext in RAM)
- Authenticated SQL injection (can read decrypted)
- Key exposure (encryption becomes useless)

### Best Practices

1. **Key Security:**
   - Never commit keys to Git
   - Use Railway encrypted environment variables
   - Store backups in password manager
   - Rotate keys annually

2. **Access Control:**
   - Limit who can access Railway environment
   - Use principle of least privilege
   - Audit key access regularly

3. **Monitoring:**
   - Log encryption failures
   - Monitor for unusual decryption patterns
   - Alert on key rotation events

4. **Backup Strategy:**
   - Backup encryption keys separately
   - Test key recovery procedures
   - Document key rotation process

---

## Performance Impact

### Benchmarks (from integration tests)

| Operation | Without Encryption | With Encryption | Overhead |
|-----------|-------------------|-----------------|----------|
| Create single user | ~2ms | ~2.5ms | +0.5ms |
| Create 50 users | ~180ms | ~190ms | +10ms |
| Retrieve single user | ~1ms | ~1.5ms | +0.5ms |
| Retrieve 50 users | ~15ms | ~18ms | +3ms |
| Email lookup (hash) | ~1ms | ~1ms | 0ms |

**Key Findings:**
- ✅ <1ms overhead per operation
- ✅ Searchable hashes enable O(1) lookups (no decryption)
- ✅ Batch operations scale linearly
- ✅ 50 users < 1s (test threshold)

### Optimization Tips

1. **Use searchable hashes for queries** (already implemented)
2. **Batch operations when possible** (reduces overhead)
3. **Cache decrypted results** (if security allows)
4. **Index searchable columns** (already implemented)

---

## Testing

### Unit Tests
```bash
# Test encryption module
pytest tests/unit/test_encryption.py -v

# Results: 44/44 passing, 92% coverage
```

### Integration Tests
```bash
# Test repository encryption
pytest tests/repositories/test_encrypted_repository.py -v

# Results: 19/19 passing
# - SystemSettingsRepository: 7 tests
# - UserRepository: 6 tests
# - EncryptedRepositoryMixin: 3 tests
# - Performance: 2 tests
# - Encryption control: 1 test
```

---

## Compliance

### GDPR Article 32

**Requirement:** "Appropriate technical and organizational measures to ensure a level of security appropriate to the risk"

**Implementation:**
- ✅ Encryption of personal data (email, full_name)
- ✅ Pseudonymization via searchable hashes
- ✅ Ability to restore access (key backup)
- ✅ Regular testing of security measures (automated tests)

### HIPAA (if applicable)

**Requirement:** "Encryption and Decryption" (164.312(a)(2)(iv))

**Implementation:**
- ✅ Encryption at rest for ePHI
- ✅ Addressable implementation specification
- ✅ Documented key management procedures

---

## Migration History

| Date | Migration | Description |
|------|-----------|-------------|
| 2025-10-29 | `add_encryption_search_fields.py` | Added searchable hash columns |
| 2025-10-29 | `encrypt_existing_user_data.py` | Encrypted existing user PII |

---

## Contacts

**Encryption System Owner:** Backend Team
**Key Custodian:** DevOps Team
**Security Incidents:** security@yourcompany.com

---

## Appendix: Code Examples

### Adding Encryption to New Repository

```python
from app.repositories.base_repository import BaseRepository, EncryptedRepositoryMixin
from app.database.models import SomeModel

class SomeRepository(EncryptedRepositoryMixin, BaseRepository[SomeModel]):
    """
    IMPORTANT: EncryptedRepositoryMixin must come FIRST in inheritance!
    """

    encrypted_fields = ['field1', 'field2']  # Define fields to encrypt

    def __init__(self, db: Session):
        super().__init__(db, SomeModel)
```

### Creating Searchable Field Lookup

```python
def get_by_field(self, field_value: str):
    """Lookup using searchable hash"""
    from app.core.encryption import encryptor

    field_hash = encryptor.generate_searchable_hash(field_value)
    entity = self.db.query(self.model).filter(
        self.model.field_searchable == field_hash
    ).first()

    return self._decrypt_entity(entity)
```

---

**Last Updated:** 2025-10-29
**Version:** 1.0
**Status:** Production Ready
