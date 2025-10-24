# Database Migration Guide

## Overview

This guide explains how to run the authentication system database migration for DocTranslator. The migration creates the necessary tables for user authentication, API key management, and audit logging.

## Prerequisites

You need one of the following PostgreSQL client tools installed:

1. **psql** (PostgreSQL command-line client) - Recommended
2. **pgAdmin** (PostgreSQL GUI client)
3. **Any PostgreSQL client** that can execute SQL files

## Migration Steps

### Step 1: Run the Migration

Execute the following command to run the migration:

```bash
# Using psql (recommended)
psql 'postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway' -f backend/migrations/001_add_authentication_tables.sql

# Alternative: Set PGPASSWORD and use shorter command
export PGPASSWORD='KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp'
psql -h turntable.proxy.rlwy.net -p 58299 -U postgres -d railway -f backend/migrations/001_add_authentication_tables.sql
```

### Step 2: Verify the Migration

After running the migration, verify it was successful:

```bash
# Run the verification script
cd backend
python3 scripts/verify_migration.py "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"
```

### Step 3: Create Initial Admin User

Once the migration is complete, create the initial admin user:

```bash
# Set environment variables
export JWT_SECRET_KEY="your-jwt-secret-key-here"
export INITIAL_ADMIN_EMAIL="your-email@domain.com"
export INITIAL_ADMIN_PASSWORD="your-secure-password"

# Create admin user
cd backend
python3 scripts/create_admin_user.py
```

## What the Migration Creates

### New Tables

1. **users** - User accounts with authentication data
   - `id` (UUID, Primary Key)
   - `email` (Unique, Indexed)
   - `password_hash` (bcrypt hashed)
   - `full_name`
   - `role` (USER or ADMIN)
   - `is_active`, `is_verified` (boolean flags)
   - `created_at`, `updated_at`, `last_login_at` (timestamps)

2. **refresh_tokens** - JWT refresh token storage
   - `id` (UUID, Primary Key)
   - `user_id` (Foreign Key to users)
   - `token_hash` (HMAC hashed)
   - `expires_at`
   - `is_revoked` (boolean)
   - `created_at`, `last_used_at` (timestamps)

3. **api_keys** - API key management
   - `id` (UUID, Primary Key)
   - `user_id` (Foreign Key to users)
   - `name` (user-defined name)
   - `key_hash` (HMAC hashed)
   - `expires_at`
   - `is_active` (boolean)
   - `last_used_at`, `created_at` (timestamps)

4. **audit_logs** - Security event logging
   - `id` (UUID, Primary Key)
   - `user_id` (Foreign Key to users, nullable)
   - `action` (action type)
   - `resource_type`, `resource_id`
   - `ip_address`, `user_agent`
   - `details` (JSON context)
   - `created_at` (timestamp)

### Modified Tables

1. **pipeline_jobs** - Added user tracking
   - `user_id` (UUID, Foreign Key to users, nullable)
   - `created_by_admin_id` (UUID, Foreign Key to users, nullable)

### Indexes Created

- `idx_users_email` - Fast email lookups
- `idx_refresh_tokens_user_id` - Fast token lookups by user
- `idx_refresh_tokens_expires_at` - Cleanup expired tokens
- `idx_api_keys_user_id` - Fast API key lookups by user
- `idx_api_keys_expires_at` - Cleanup expired keys
- `idx_audit_logs_user_id` - Fast audit log lookups by user
- `idx_audit_logs_action` - Fast audit log filtering by action
- `idx_audit_logs_created_at` - Fast audit log time-based queries
- `idx_pipeline_jobs_user_id` - Fast pipeline job lookups by user

## Troubleshooting

### Common Issues

1. **"psql: command not found"**
   - Install PostgreSQL client tools
   - On Ubuntu/Debian: `sudo apt install postgresql-client`
   - On macOS: `brew install postgresql`

2. **"permission denied"**
   - Check database credentials
   - Ensure the user has CREATE TABLE permissions

3. **"table already exists"**
   - This is normal if running the migration multiple times
   - The migration is idempotent and safe to run multiple times

4. **"connection refused"**
   - Check database URL
   - Ensure database server is running
   - Check firewall settings

### Verification Commands

Check if tables exist:
```sql
\dt
```

Check specific table structure:
```sql
\d users
\d refresh_tokens
\d api_keys
\d audit_logs
```

Check pipeline_jobs has user_id column:
```sql
\d pipeline_jobs
```

## Next Steps

After successful migration:

1. **Set Environment Variables** in your deployment platform:
   ```bash
   JWT_SECRET_KEY=your-secure-jwt-secret
   INITIAL_ADMIN_EMAIL=admin@yourdomain.com
   INITIAL_ADMIN_PASSWORD=your-secure-password
   ALLOW_PUBLIC_UPLOAD=true
   REQUIRE_AUTH_FOR_RESULTS=false
   ```

2. **Deploy the Updated Backend** with authentication system

3. **Deploy the Updated Frontend** with login functionality

4. **Test the System**:
   - Verify public document upload still works
   - Test admin login
   - Test user creation
   - Test protected endpoints

## Rollback (If Needed)

If you need to rollback the migration:

```sql
-- Drop the new tables
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Remove added columns from pipeline_jobs
ALTER TABLE pipeline_jobs DROP COLUMN IF EXISTS user_id;
ALTER TABLE pipeline_jobs DROP COLUMN IF EXISTS created_by_admin_id;
```

**Warning**: This will permanently delete all user data and authentication information.

## Support

If you encounter issues:

1. Check the migration logs for specific error messages
2. Verify database connectivity
3. Ensure proper permissions
4. Check the troubleshooting section above

The migration is designed to be safe and idempotent, so it can be run multiple times without issues.
