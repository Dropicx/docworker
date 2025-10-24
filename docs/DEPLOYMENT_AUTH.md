# Authentication System Deployment Guide

This guide covers the deployment of the new enterprise-grade authentication system for DocTranslator.

## Overview

The authentication system provides:
- JWT-based authentication with refresh tokens
- Role-based access control (USER, ADMIN)
- API key management for programmatic access
- Comprehensive audit logging
- Public document upload (no auth required)
- Protected admin functions

## Pre-Deployment Setup

### 1. Generate Security Secrets

```bash
cd backend
python scripts/generate_secrets.py --type all
```

This will generate:
- JWT secret key
- Admin password
- API key example
- All required environment variables

### 2. Set Railway Environment Variables

```bash
# JWT Authentication
railway variables set JWT_SECRET_KEY=<generated-jwt-key>

# Initial Admin User
railway variables set INITIAL_ADMIN_EMAIL=your-email@domain.com
railway variables set INITIAL_ADMIN_PASSWORD=<generated-password>
railway variables set INITIAL_ADMIN_NAME="Your Name"

# Security Settings
railway variables set BCRYPT_ROUNDS=12
railway variables set PASSWORD_MIN_LENGTH=8
railway variables set API_KEY_LENGTH=32
railway variables set API_KEY_DEFAULT_EXPIRY_DAYS=90

# Audit Logging
railway variables set ENABLE_AUDIT_LOGGING=true
railway variables set AUDIT_ADMIN_ACTIONS_ONLY=true

# Public Access
railway variables set ALLOW_PUBLIC_UPLOAD=true
railway variables set REQUIRE_AUTH_FOR_RESULTS=false

# CORS Configuration
railway variables set CORS_ALLOW_CREDENTIALS=true
railway variables set CORS_MAX_AGE=3600
railway variables set ALLOWED_ORIGINS=["*"]
railway variables set TRUSTED_HOSTS=["*"]
```

### 3. Database Migration

The authentication system requires new database tables. Run the migration:

```bash
# In Railway console or local development
alembic upgrade head
```

## Deployment Steps

### 1. Deploy Backend

Deploy the updated backend with the new authentication system:

```bash
# Deploy to Railway
railway up
```

### 2. Create Initial Admin User

After deployment, create the initial admin user:

```bash
# In Railway console
python scripts/create_admin_user.py
```

### 3. Verify Deployment

Test the authentication system:

```bash
# Test admin login
curl -X POST "https://your-app.railway.app/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@domain.com",
    "password": "your-admin-password"
  }'

# Test public upload (should work without auth)
curl -X POST "https://your-app.railway.app/api/upload" \
  -F "file=@test-document.pdf"
```

## Post-Deployment Configuration

### 1. Create Additional Users

Use the admin interface or CLI to create additional users:

```bash
# Create a regular user
python scripts/manage_users.py create user@example.com "User Name" USER

# Create another admin
python scripts/manage_users.py create admin2@example.com "Admin 2" ADMIN
```

### 2. Generate API Keys

Create API keys for programmatic access:

```bash
# Create API key for a user
python scripts/manage_api_keys.py create user@example.com "My API Key" --expires-days 90
```

### 3. Configure CORS for Production

Update CORS settings for your production domain:

```bash
railway variables set ALLOWED_ORIGINS=["https://yourdomain.com"]
railway variables set TRUSTED_HOSTS=["yourdomain.com"]
```

## Access Model

### Public Access (No Authentication Required)
- Document upload (`POST /api/upload`)
- Document processing status (`GET /api/processing/{id}`)
- Document results retrieval
- Multi-file processing
- Health checks

### User Role (Authentication Required)
- All public access features
- Pipeline configuration management
- Prompt management
- OCR settings
- Own API key management
- Own activity logs

### Admin Role (Full Access)
- All user permissions
- User management (create, edit, delete users)
- Role assignment
- All audit logs
- All API key management
- System configuration

## API Usage Examples

### Authentication

```bash
# Login
curl -X POST "https://your-app.railway.app/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use access token
curl -X GET "https://your-app.railway.app/api/auth/me" \
  -H "Authorization: Bearer <access-token>"

# Refresh token
curl -X POST "https://your-app.railway.app/api/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh-token>"}'
```

### API Key Usage

```bash
# Use API key for authentication
curl -X GET "https://your-app.railway.app/api/auth/me" \
  -H "Authorization: Bearer <api-key>"
```

### User Management (Admin Only)

```bash
# Create user
curl -X POST "https://your-app.railway.app/api/users" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "secure-password",
    "full_name": "New User",
    "role": "user"
  }'

# List users
curl -X GET "https://your-app.railway.app/api/users" \
  -H "Authorization: Bearer <admin-token>"
```

## Monitoring and Maintenance

### 1. Audit Logs

Monitor security events through audit logs:

```bash
# View recent audit logs
curl -X GET "https://your-app.railway.app/api/audit/logs" \
  -H "Authorization: Bearer <admin-token>"

# Export audit logs
curl -X GET "https://your-app.railway.app/api/audit/export/csv" \
  -H "Authorization: Bearer <admin-token>"
```

### 2. API Key Management

```bash
# List all API keys
python scripts/manage_api_keys.py list-all

# Clean up expired keys
python scripts/manage_api_keys.py cleanup
```

### 3. User Management

```bash
# List all users
python scripts/manage_users.py list

# Deactivate user
python scripts/manage_users.py deactivate user@example.com
```

## Security Considerations

### 1. Password Policy
- Minimum 8 characters
- Must contain uppercase, lowercase, digit, and special character
- Bcrypt hashing with cost factor 12

### 2. Token Security
- Access tokens expire in 15 minutes
- Refresh tokens expire in 7 days
- Tokens are revoked on logout

### 3. API Key Security
- HMAC-SHA256 hashing for storage
- Configurable expiration
- Usage tracking

### 4. Audit Logging
- All admin and user actions logged
- Public uploads not logged (privacy)
- IP address and user agent tracking
- Configurable retention period

## Troubleshooting

### Common Issues

1. **JWT_SECRET_KEY not set**
   - Error: "JWT secret key is required"
   - Solution: Set JWT_SECRET_KEY environment variable

2. **Admin user creation fails**
   - Error: "User with email already exists"
   - Solution: Check if admin user already exists, or use different email

3. **Database migration fails**
   - Error: Migration conflicts
   - Solution: Check database state, may need manual migration

4. **CORS errors**
   - Error: CORS policy blocks requests
   - Solution: Update ALLOWED_ORIGINS for your domain

### Logs and Debugging

```bash
# View application logs
railway logs

# Check specific service logs
railway logs --service backend

# Test authentication locally
python scripts/create_admin_user.py
```

## Rollback Plan

If issues occur:

1. **Revert to previous deployment**
   ```bash
   railway rollback
   ```

2. **Database rollback** (if needed)
   ```bash
   alembic downgrade -1
   ```

3. **Verify public access still works**
   - Document upload should work without authentication
   - Status checks should work without authentication

## Support

For issues with the authentication system:

1. Check audit logs for security events
2. Verify environment variables are set correctly
3. Test with the provided CLI tools
4. Review the API documentation

The authentication system is designed to be robust and maintain backward compatibility with public document processing while adding enterprise-grade security for administrative functions.
