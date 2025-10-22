# Phase 3 Implementation Plan: Security & Compliance

**Phase:** 3 of 7
**Status:** Ready to Start
**Duration Estimate:** 3-4 weeks
**Priority:** CRITICAL - Required for Production
**Issues:** #17 (Security & Authentication), #31 (GDPR Compliance)

---

## 📋 Executive Summary

Phase 3 focuses on implementing production-grade security measures and ensuring full GDPR compliance. These are **critical requirements** for production deployment and EU operations.

**Key Objectives:**
1. Implement robust authentication and authorization system
2. Enhance API security with rate limiting and request validation
3. Ensure full GDPR compliance with data protection measures
4. Implement comprehensive audit logging
5. Create legal documentation (Privacy Policy, Terms of Service, DPA)

**Success Criteria:**
- ✅ All API endpoints protected with authentication
- ✅ Role-based access control (RBAC) implemented
- ✅ GDPR compliance checklist 100% complete
- ✅ Audit logging operational
- ✅ Legal documentation published
- ✅ Security tests passing

---

## 🎯 Implementation Strategy

### Sequencing Decision: #17 FIRST, then #31

**Rationale:**
1. **Foundation First**: Authentication system (#17) is required for GDPR compliance (#31)
2. **User Management**: Need user accounts before implementing data access/deletion rights
3. **Audit Logging**: Security infrastructure enables GDPR audit requirements
4. **Dependencies**: #31 requires user authentication, roles, and permissions from #17

**Timeline:**
- **Week 1-2**: Issue #17 - Security & Authentication
- **Week 3-4**: Issue #31 - GDPR Compliance
- **Overlap**: Start GDPR planning during Week 2

---

## 🔐 Issue #17: Security & Authentication

### Phase 1: Core Authentication (Week 1, Days 1-3)

#### 1.1 Database Schema
**Files:** `backend/app/database/models/`

Create new models:
```python
# user.py
class User(Base):
    - id (UUID, primary key)
    - email (unique, indexed)
    - password_hash (bcrypt)
    - full_name
    - is_active, is_verified
    - role (enum: USER, ADMIN)
    - created_at, updated_at
    - last_login_at

# api_key.py
class APIKey(Base):
    - id (UUID, primary key)
    - user_id (foreign key)
    - key_hash (HMAC)
    - name (description)
    - is_active
    - expires_at
    - last_used_at
    - created_at

# refresh_token.py
class RefreshToken(Base):
    - id (UUID, primary key)
    - user_id (foreign key)
    - token_hash
    - expires_at
    - is_revoked
    - created_at
```

**Migration Script:**
```bash
# Create migration
alembic revision --autogenerate -m "Add authentication tables"
alembic upgrade head
```

**Seed Data:**
```python
# Create admin user
admin@doctranslator.com (ADMIN role)
# Create test user
user@doctranslator.com (USER role)
```

#### 1.2 Security Core
**File:** `backend/app/core/security.py`

Implement:
```python
- password_hash(password: str) -> str
  → bcrypt with cost factor 12

- verify_password(plain: str, hashed: str) -> bool
  → constant-time comparison

- create_access_token(data: dict, expires_delta: timedelta) -> str
  → JWT with HS256, 15 min expiry

- create_refresh_token(user_id: UUID) -> str
  → JWT with 7 day expiry, store hash in DB

- decode_token(token: str) -> dict
  → validate signature, expiry, claims

- generate_api_key() -> tuple[str, str]
  → cryptographically secure random key
  → return (plain_key, key_hash)

- verify_api_key(key: str, key_hash: str) -> bool
  → constant-time HMAC comparison
```

**Dependencies:**
```txt
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
python-multipart==0.0.9
```

#### 1.3 Authentication Module
**File:** `backend/app/core/auth.py`

Implement:
```python
class AuthService:
    - register_user(email, password, full_name) -> User
      → validate email format
      → check if user exists
      → hash password
      → create user record
      → send verification email (future)

    - authenticate_user(email, password) -> User | None
      → fetch user by email
      → verify password
      → update last_login_at
      → return user or None

    - create_tokens(user: User) -> dict
      → create access_token
      → create refresh_token
      → store refresh_token in DB
      → return both tokens

    - refresh_access_token(refresh_token: str) -> str
      → validate refresh token
      → check if revoked
      → create new access token

    - revoke_refresh_token(token: str) -> None
      → mark token as revoked in DB

    - get_current_user(token: str) -> User
      → decode JWT
      → fetch user from DB
      → verify user is active
      → return user
```

#### 1.4 Auth Router
**File:** `backend/app/routers/auth.py`

Endpoints:
```python
POST   /api/auth/register
       → Body: {email, password, full_name}
       → Returns: {user, access_token, refresh_token}

POST   /api/auth/login
       → Body: {email, password}
       → Returns: {user, access_token, refresh_token}

POST   /api/auth/refresh
       → Body: {refresh_token}
       → Returns: {access_token}

POST   /api/auth/logout
       → Body: {refresh_token}
       → Returns: {message}

GET    /api/auth/me
       → Auth: Required
       → Returns: {user}

POST   /api/auth/change-password
       → Auth: Required
       → Body: {old_password, new_password}
       → Returns: {message}
```

**Testing:**
```bash
pytest backend/tests/routers/test_auth.py
- test_register_user_success
- test_register_duplicate_email
- test_login_success
- test_login_invalid_credentials
- test_refresh_token_success
- test_logout_success
- test_get_current_user
- test_change_password
```

---

### Phase 2: Authorization & RBAC (Week 1, Days 4-5)

#### 2.1 Role-Based Access Control
**File:** `backend/app/core/permissions.py`

```python
class Role(str, Enum):
    USER = "user"    # Can upload, translate, view own docs
    ADMIN = "admin"  # Can manage settings, view all docs

class Permission(str, Enum):
    # Document permissions
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_READ_OWN = "document:read:own"
    DOCUMENT_READ_ALL = "document:read:all"
    DOCUMENT_DELETE_OWN = "document:delete:own"
    DOCUMENT_DELETE_ALL = "document:delete:all"

    # Settings permissions
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"

    # Admin permissions
    USER_MANAGE = "user:manage"
    AUDIT_VIEW = "audit:view"

ROLE_PERMISSIONS = {
    Role.USER: [
        Permission.DOCUMENT_CREATE,
        Permission.DOCUMENT_READ_OWN,
        Permission.DOCUMENT_DELETE_OWN,
        Permission.SETTINGS_READ,
    ],
    Role.ADMIN: [
        # All USER permissions plus:
        Permission.DOCUMENT_READ_ALL,
        Permission.DOCUMENT_DELETE_ALL,
        Permission.SETTINGS_WRITE,
        Permission.USER_MANAGE,
        Permission.AUDIT_VIEW,
    ],
}

def require_permission(permission: Permission):
    """Decorator for permission checks"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not has_permission(current_user, permission):
                raise HTTPException(403, "Insufficient permissions")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

#### 2.2 API Key Management
**File:** `backend/app/routers/api_keys.py`

```python
POST   /api/keys/create
       → Auth: Required
       → Body: {name, expires_in_days}
       → Returns: {key, id, name, expires_at}
       → NOTE: Plain key shown only once

GET    /api/keys
       → Auth: Required
       → Returns: [{id, name, is_active, expires_at, last_used_at}]
       → NOTE: Does not return key values

DELETE /api/keys/{key_id}
       → Auth: Required
       → Returns: {message}

PATCH  /api/keys/{key_id}/rotate
       → Auth: Required
       → Returns: {new_key}
```

#### 2.3 Protect Existing Endpoints
**Files to Modify:**

```python
# backend/app/routers/upload.py
@router.post("/upload")
@require_permission(Permission.DOCUMENT_CREATE)
async def upload_document(
    file: UploadFile,
    current_user: User = Depends(get_current_user)
):
    # Associate document with user_id
    # ...

# backend/app/routers/settings.py
@router.get("/settings/universal-prompts")
@require_permission(Permission.SETTINGS_READ)
async def get_universal_prompts(
    current_user: User = Depends(get_current_user)
):
    # ...

@router.put("/settings/universal-prompts")
@require_permission(Permission.SETTINGS_WRITE)
async def update_universal_prompts(
    current_user: User = Depends(get_current_user)
):
    # Only ADMIN can modify
    # ...
```

---

### Phase 3: API Security (Week 2, Days 1-2)

#### 3.1 Rate Limiting
**File:** `backend/app/middleware/rate_limiter.py`

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Rate limits
RATE_LIMITS = {
    "auth": "5/minute",     # Login attempts
    "upload": "10/hour",    # File uploads
    "process": "20/hour",   # Document processing
    "api": "100/hour",      # General API
}
```

**Middleware:**
```python
# backend/app/main.py
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**Apply to routes:**
```python
@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    # ...
```

**Dependencies:**
```txt
slowapi==0.1.9
redis==5.0.1  # For distributed rate limiting
```

#### 3.2 Security Headers
**File:** `backend/app/middleware/security_headers.py`

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https://oai.endpoints.kepler.ai.cloud.ovh.net"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    return response
```

#### 3.3 CORS Configuration
**File:** `backend/app/main.py`

```python
# Update CORS settings
ALLOWED_ORIGINS = [
    "https://doctranslator.com",
    "https://www.doctranslator.com",
    "https://dev.doctranslator.com",
]

if settings.ENVIRONMENT == "development":
    ALLOWED_ORIGINS.append("http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    max_age=3600,
)
```

#### 3.4 Request Validation
**File:** `backend/app/middleware/request_validator.py`

```python
MAX_REQUEST_SIZE = 50 * 1024 * 1024  # 50MB

@app.middleware("http")
async def validate_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE:
        raise HTTPException(413, "Request too large")

    return await call_next(request)

# File type validation
ALLOWED_MIME_TYPES = [
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
]

def validate_file_type(file: UploadFile) -> bool:
    """Validate using magic numbers, not just extension"""
    import magic
    mime = magic.from_buffer(file.file.read(2048), mime=True)
    file.file.seek(0)
    return mime in ALLOWED_MIME_TYPES
```

---

### Phase 4: Frontend Integration (Week 2, Days 3-5)

#### 4.1 Auth Context
**File:** `frontend/src/contexts/AuthContext.tsx`

```typescript
interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'user' | 'admin';
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}

export const AuthProvider: React.FC<{children: React.ReactNode}> = ({children}) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing session on mount
    const initAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const user = await api.auth.getCurrentUser();
          setUser(user);
        } catch (error) {
          // Token expired, try refresh
          await refreshToken();
        }
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  // Implement login, logout, register, refreshToken
  // ...
}
```

#### 4.2 API Client Updates
**File:** `frontend/src/services/api.ts`

```typescript
// Add auth interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add refresh token interceptor
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const { access_token } = await api.auth.refreshToken(refreshToken);
          localStorage.setItem('access_token', access_token);
          // Retry original request
          return api.request(error.config);
        } catch (refreshError) {
          // Refresh failed, logout
          localStorage.clear();
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);
```

#### 4.3 Auth Pages
**Files to Create:**

```typescript
// frontend/src/pages/Login.tsx
- Email/password form
- Remember me checkbox
- Forgot password link
- Register link
- Submit → login → redirect to dashboard

// frontend/src/pages/Register.tsx
- Full name, email, password, confirm password
- Terms acceptance checkbox
- Submit → register → auto-login → dashboard

// frontend/src/pages/ForgotPassword.tsx
- Email input
- Submit → send reset email
- Success message

// frontend/src/components/ProtectedRoute.tsx
- Check authentication
- Redirect to /login if not authenticated
- Show loading spinner during check
```

#### 4.4 Settings UI Updates
**File:** `frontend/src/pages/Settings.tsx`

```typescript
// Check admin role before showing settings
const { user } = useAuth();

if (user?.role !== 'admin') {
  return <div>Access denied. Admin privileges required.</div>;
}

// Show settings UI
```

---

## ⚖️ Issue #31: GDPR Compliance

### Phase 5: Data Protection (Week 3, Days 1-2)

#### 5.1 Audit Logging
**File:** `backend/app/services/audit_logger.py`

```python
class AuditAction(str, Enum):
    ACCESS = "access"
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    EXPORT = "export"

class AuditLogger:
    async def log(
        self,
        user_id: UUID,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        ip_address: str,
        user_agent: str,
        details: dict = None
    ):
        """Create tamper-proof audit log entry"""
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            timestamp=datetime.utcnow()
        )
        await audit_log_repo.create(entry)
```

**Database Model:**
```python
# backend/app/database/models/audit_log.py
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=False)
    ip_address = Column(INET)
    user_agent = Column(Text)
    details = Column(JSONB)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
```

**Integration:**
```python
# Add audit logging to all protected endpoints
@router.post("/upload")
async def upload_document(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    request: Request
):
    # Process upload
    doc_id = await process_upload(file, current_user.id)

    # Audit log
    await audit_logger.log(
        user_id=current_user.id,
        action=AuditAction.CREATE,
        resource_type="document",
        resource_id=doc_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )

    return {"document_id": doc_id}
```

#### 5.2 Field-Level Encryption
**File:** `backend/app/database/encryption.py`

```python
from cryptography.fernet import Fernet

class FieldEncryption:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        """Encrypt sensitive field"""
        if not value:
            return value
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        """Decrypt sensitive field"""
        if not encrypted:
            return encrypted
        return self.fernet.decrypt(encrypted.encode()).decode()

# Usage in models
class User(Base):
    __tablename__ = "users"

    email = Column(String)  # Not encrypted (needed for login)

    @hybrid_property
    def phone_number(self):
        if self._phone_number:
            return encryption.decrypt(self._phone_number)
        return None

    @phone_number.setter
    def phone_number(self, value):
        if value:
            self._phone_number = encryption.encrypt(value)
        else:
            self._phone_number = None
```

**Environment Variables:**
```bash
# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to .env
ENCRYPTION_KEY=your-generated-key-here
```

---

### Phase 6: GDPR Endpoints (Week 3, Days 3-4)

#### 6.1 Data Export
**File:** `backend/app/routers/gdpr.py`

```python
@router.get("/gdpr/export")
async def export_user_data(
    current_user: User = Depends(get_current_user)
):
    """Export all user data in machine-readable format"""

    # Collect all user data
    data = {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "created_at": current_user.created_at.isoformat(),
        },
        "documents": await get_user_documents(current_user.id),
        "ai_interactions": await get_user_ai_logs(current_user.id),
        "audit_logs": await get_user_audit_logs(current_user.id),
        "consents": await get_user_consents(current_user.id),
    }

    # Create ZIP file
    zip_buffer = create_gdpr_export_zip(data)

    # Audit log
    await audit_logger.log(
        user_id=current_user.id,
        action=AuditAction.EXPORT,
        resource_type="user_data",
        resource_id=str(current_user.id),
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=gdpr_export_{current_user.id}.zip"
        }
    )
```

#### 6.2 Data Deletion
**File:** `backend/app/services/data_deletion.py`

```python
class DataDeletionService:
    async def request_deletion(self, user_id: UUID) -> str:
        """Schedule user data deletion"""

        # Create deletion request
        request = DataDeletionRequest(
            user_id=user_id,
            requested_at=datetime.utcnow(),
            scheduled_for=datetime.utcnow() + timedelta(days=30),  # Grace period
            status="SCHEDULED"
        )
        await deletion_repo.create(request)

        # Notify user
        await send_deletion_confirmation_email(user_id)

        return request.id

    async def execute_deletion(self, request_id: str):
        """Execute scheduled deletion"""

        request = await deletion_repo.get(request_id)
        if request.status != "SCHEDULED":
            return

        # Delete all user data (cascade)
        user_id = request.user_id

        # 1. Delete documents
        await document_repo.delete_by_user(user_id)

        # 2. Delete AI logs
        await ai_log_repo.delete_by_user(user_id)

        # 3. Delete API keys
        await api_key_repo.delete_by_user(user_id)

        # 4. Keep audit logs (legal requirement)
        # Anonymize instead of delete
        await audit_log_repo.anonymize_user(user_id)

        # 5. Delete user account
        await user_repo.delete(user_id)

        # Update request status
        request.status = "COMPLETED"
        request.completed_at = datetime.utcnow()
        await deletion_repo.update(request)

    async def cancel_deletion(self, user_id: UUID):
        """Cancel pending deletion"""
        await deletion_repo.cancel_pending(user_id)
```

#### 6.3 Consent Management
**File:** `backend/app/services/consent_manager.py`

```python
class ConsentType(str, Enum):
    TERMS = "terms"
    PRIVACY = "privacy"
    COOKIES = "cookies"
    ANALYTICS = "analytics"
    MARKETING = "marketing"

class ConsentManager:
    async def record_consent(
        self,
        user_id: UUID,
        consent_type: ConsentType,
        consent_given: bool,
        version: str,
        ip_address: str,
        user_agent: str
    ):
        """Record user consent"""
        consent = ConsentRecord(
            user_id=user_id,
            consent_type=consent_type,
            consent_given=consent_given,
            consent_date=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
            version=version
        )
        await consent_repo.create(consent)

    async def get_consents(self, user_id: UUID) -> dict:
        """Get all user consents"""
        consents = await consent_repo.get_by_user(user_id)
        return {
            c.consent_type: {
                "given": c.consent_given,
                "date": c.consent_date,
                "version": c.version
            }
            for c in consents
        }

    async def has_consent(self, user_id: UUID, consent_type: ConsentType) -> bool:
        """Check if user has given consent"""
        consent = await consent_repo.get_latest(user_id, consent_type)
        return consent and consent.consent_given
```

---

### Phase 7: Legal Documentation (Week 3, Day 5)

#### 7.1 Privacy Policy
**File:** `docs/legal/PRIVACY_POLICY.md`

Contents:
```markdown
# Privacy Policy - DocTranslator

Last Updated: [DATE]

## 1. Introduction
DocTranslator ("we", "our", "us") respects your privacy...

## 2. Data Controller
- Company: [Legal Entity Name]
- Email: privacy@doctranslator.com
- Address: [Legal Address]

## 3. Data We Collect
### Personal Data
- Email address (for account creation)
- Name (optional)
- IP address (for security)
- Browser information (for compatibility)

### Medical Documents
- Uploaded documents (processed and deleted after 7 days)
- Translated output
- Processing metadata

### Usage Data
- API interaction logs (90 days retention)
- Error logs (90 days retention)
- Audit logs (3 years retention for legal compliance)

## 4. Legal Basis for Processing
- **Contract Performance**: Account creation, document processing
- **Legitimate Interest**: Security, fraud prevention, service improvement
- **Legal Obligation**: Audit logs, financial records

## 5. Data Retention
- Documents: 7 days after processing
- AI interaction logs: 90 days
- Audit logs: 3 years
- User accounts: Until user requests deletion

## 6. Your Rights
Under GDPR, you have the right to:
- Access your personal data
- Correct inaccurate data
- Request deletion of your data
- Export your data
- Object to processing
- Withdraw consent

## 7. Data Security
- Encryption in transit (TLS 1.3)
- Encryption at rest (AES-256)
- Regular security audits
- Access controls and authentication

## 8. Third-Party Processors
| Provider | Purpose | Location | DPA Signed |
|----------|---------|----------|------------|
| OVH | AI Processing | EU | Yes |
| Railway | Hosting | EU | Yes |
| PostgreSQL | Database | EU | N/A |

## 9. Data Transfers
All data is processed within the EU. No international transfers.

## 10. Cookies
We use essential cookies only:
- Session management
- Authentication
- Security

## 11. Children's Privacy
Not intended for users under 16. No knowingly collected data from children.

## 12. Changes to Policy
We will notify users of material changes via email.

## 13. Contact Us
Privacy questions: privacy@doctranslator.com
Data Protection Officer: dpo@doctranslator.com

## 14. Supervisory Authority
[EU Member State Data Protection Authority]
```

#### 7.2 Terms of Service
**File:** `docs/legal/TERMS_OF_SERVICE.md`

Key sections:
```markdown
# Terms of Service

## 1. Acceptance of Terms
## 2. Service Description
## 3. User Accounts
## 4. Medical Disclaimer
## 5. User Obligations
## 6. Intellectual Property
## 7. Limitation of Liability
## 8. Termination
## 9. Governing Law
## 10. Dispute Resolution
```

#### 7.3 Data Processing Agreement
**File:** `docs/legal/DPA_TEMPLATE.md`

For B2B customers (GDPR Article 28 compliant)

---

### Phase 8: Cookie Consent (Week 4, Day 1)

#### 8.1 Cookie Banner
**File:** `frontend/src/components/CookieConsent.tsx`

```typescript
export const CookieConsent: React.FC = () => {
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem('cookie_consent');
    if (!consent) {
      setShowBanner(true);
    }
  }, []);

  const handleAccept = async () => {
    // Record consent
    await api.gdpr.recordConsent({
      consent_type: 'cookies',
      consent_given: true,
      version: '1.0'
    });

    localStorage.setItem('cookie_consent', 'accepted');
    setShowBanner(false);
  };

  const handleDecline = () => {
    localStorage.setItem('cookie_consent', 'declined');
    setShowBanner(false);
  };

  if (!showBanner) return null;

  return (
    <div className="cookie-banner">
      <p>We use essential cookies for authentication and security.</p>
      <button onClick={handleAccept}>Accept</button>
      <button onClick={handleDecline}>Decline</button>
    </div>
  );
};
```

---

### Phase 9: Data Retention & Cleanup (Week 4, Day 2)

#### 9.1 Retention Policy
**File:** `backend/app/services/data_retention.py`

```python
RETENTION_POLICIES = {
    "documents": timedelta(days=7),
    "ai_logs": timedelta(days=90),
    "audit_logs": timedelta(days=1095),  # 3 years
    "user_accounts": None,  # Until deletion requested
}

class DataRetentionService:
    async def cleanup_expired_data(self):
        """Run daily cleanup job"""

        # 1. Delete old documents
        cutoff = datetime.utcnow() - RETENTION_POLICIES["documents"]
        await document_repo.delete_older_than(cutoff)

        # 2. Delete old AI logs
        cutoff = datetime.utcnow() - RETENTION_POLICIES["ai_logs"]
        await ai_log_repo.delete_older_than(cutoff)

        # 3. Delete old audit logs
        cutoff = datetime.utcnow() - RETENTION_POLICIES["audit_logs"]
        await audit_log_repo.delete_older_than(cutoff)

        # 4. Execute scheduled deletions
        pending = await deletion_repo.get_pending_deletions()
        for request in pending:
            if request.scheduled_for <= datetime.utcnow():
                await data_deletion_service.execute_deletion(request.id)
```

**Celery Task:**
```python
# backend/worker/tasks/maintenance.py
@celery_app.task
def daily_data_cleanup():
    """Run daily at 2 AM"""
    asyncio.run(data_retention_service.cleanup_expired_data())

# Schedule in celery beat
celery_app.conf.beat_schedule = {
    'daily-cleanup': {
        'task': 'tasks.maintenance.daily_data_cleanup',
        'schedule': crontab(hour=2, minute=0),
    },
}
```

---

### Phase 10: Testing & Documentation (Week 4, Days 3-5)

#### 10.1 Security Tests
**File:** `backend/tests/security/test_auth.py`

```python
# Authentication tests
- test_register_weak_password
- test_login_brute_force_protection
- test_jwt_expiration
- test_jwt_tampering_detection
- test_refresh_token_rotation
- test_password_reset_flow

# Authorization tests
- test_user_cannot_access_admin_endpoints
- test_api_key_authentication
- test_permission_checks

# Security tests
- test_rate_limiting
- test_request_size_validation
- test_file_type_validation
- test_sql_injection_prevention
- test_xss_prevention
```

#### 10.2 GDPR Tests
**File:** `backend/tests/gdpr/test_compliance.py`

```python
- test_data_export_completeness
- test_data_deletion_cascade
- test_audit_logging
- test_consent_recording
- test_retention_policy_enforcement
- test_anonymization
```

#### 10.3 Documentation
**Files to Create/Update:**

```markdown
# docs/SECURITY.md
- Authentication guide
- Authorization guide
- API key management
- Security best practices

# docs/GDPR_COMPLIANCE.md
- Compliance checklist
- Data flows
- Retention policies
- User rights implementation

# docs/API.md (update)
- Add auth endpoints
- Add GDPR endpoints
- Update authentication requirements
```

---

## 📊 Success Metrics

### Security (#17)
- [ ] 100% of API endpoints require authentication
- [ ] RBAC implemented with USER and ADMIN roles
- [ ] Rate limiting active on all endpoints
- [ ] Security headers configured
- [ ] API key management functional
- [ ] All tests passing (50+ security tests)

### GDPR (#31)
- [ ] Data export API working
- [ ] Data deletion with 30-day grace period
- [ ] Audit logging on all data access
- [ ] Consent management implemented
- [ ] Cookie consent banner
- [ ] Retention policies enforced
- [ ] Legal documentation published
- [ ] All tests passing (30+ GDPR tests)

---

## ⚠️ Risk Assessment

### High Risk
1. **Data Breach**: Implement encryption, audit logging, access controls
2. **Authentication Bypass**: Comprehensive security testing required
3. **GDPR Non-Compliance**: Legal review of documentation needed

### Medium Risk
1. **Performance Impact**: Rate limiting may affect legitimate users
2. **Migration Complexity**: Adding auth to existing system requires careful rollout
3. **User Friction**: Registration flow must be smooth

### Low Risk
1. **Documentation Gaps**: Can be addressed incrementally
2. **Frontend UI/UX**: Can iterate based on user feedback

---

## 🚀 Deployment Strategy

### Week 4, Day 5: Pre-Production Checklist
```bash
# 1. Database migrations
alembic upgrade head

# 2. Create admin user
python scripts/create_admin_user.py

# 3. Security audit
make security-audit

# 4. GDPR compliance check
make gdpr-check

# 5. Run all tests
make test-all

# 6. Deploy to staging
railway up --environment staging

# 7. Manual testing
- Test authentication flow
- Test RBAC permissions
- Test data export
- Test data deletion
- Test audit logging

# 8. Production deployment
railway up --environment production

# 9. Post-deployment
- Monitor error rates
- Check audit logs
- Verify rate limiting
- User acceptance testing
```

---

## 📝 Documentation Deliverables

1. **Technical Documentation**
   - Security architecture diagram
   - Authentication flow diagram
   - GDPR data flow diagram
   - API documentation updates

2. **Legal Documentation**
   - Privacy Policy (published)
   - Terms of Service (published)
   - DPA Template (for B2B)
   - Cookie Policy

3. **User Documentation**
   - Account management guide
   - Data rights guide
   - API key usage guide

4. **Internal Documentation**
   - Security procedures
   - Incident response plan
   - GDPR compliance checklist
   - Audit log analysis guide

---

## 🎯 Post-Phase 3 Readiness

After completing Phase 3, the application will be:

✅ **Production-Ready Security**
- Enterprise-grade authentication
- Role-based access control
- Comprehensive API security

✅ **GDPR Compliant**
- Full user data rights
- Audit trail for compliance
- Legal documentation complete

✅ **Ready for Phase 4**
- Foundation for performance optimization
- Monitoring hooks in place
- Scalability groundwork complete

---

**Next Steps After Phase 3:**
1. Move to Phase 4 (Performance & Scalability)
2. Conduct external security audit (recommended)
3. Legal review of documentation
4. User acceptance testing
5. Production deployment

---

**Plan Status:** READY FOR IMPLEMENTATION
**Estimated Start Date:** [To be determined]
**Estimated Completion:** 3-4 weeks from start

🤖 Generated with [Claude Code](https://claude.com/claude-code)
