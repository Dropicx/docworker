# Admin User Setup Guide

This guide explains how to create the initial admin user for the DocTranslator authentication system.

## Prerequisites

1. **Database Migration Completed**: The authentication tables must be created first
2. **PostgreSQL Client**: You need `psql` installed to connect to the database

## Method 1: Using the Standalone Python Script (Recommended)

### Step 1: Install psycopg2 (if needed)

```bash
# Try to install psycopg2-binary
pip3 install --user psycopg2-binary

# Or install system-wide (if you have sudo access)
sudo apt install python3-psycopg2
```

### Step 2: Run the Script

```bash
cd backend
python3 scripts/create_admin_user_standalone.py "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway" "your-email@domain.com" "your-secure-password" "Your Full Name"
```

### Step 3: Verify Success

The script will output:
- ✅ Admin user created successfully!
- Email: your-email@domain.com
- Role: admin
- User ID: [uuid]

## Method 2: Using SQL Directly (Fallback)

If the Python script doesn't work, you can create the admin user directly with SQL:

### Step 1: Connect to Database

```bash
psql 'postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway'
```

### Step 2: Run the SQL Script

```bash
# Exit psql first, then run the SQL file
\q
psql 'postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway' -f backend/scripts/create_admin_user.sql
```

### Step 3: Customize the User (Optional)

If you want to customize the admin user details, edit the SQL file:

```sql
-- Change these values in create_admin_user.sql
\set admin_email 'your-email@domain.com'
\set admin_password 'your-secure-password'
\set admin_name 'Your Full Name'
```

## Method 3: Manual SQL Insert

If both methods above fail, you can insert the user manually:

### Step 1: Connect to Database

```bash
psql 'postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway'
```

### Step 2: Insert Admin User

```sql
-- Generate a UUID for the user ID
SELECT gen_random_uuid();

-- Use the UUID from above in this insert statement
INSERT INTO users (
    id, 
    email, 
    password_hash, 
    full_name, 
    role, 
    is_active, 
    is_verified, 
    created_at, 
    updated_at
) VALUES (
    'REPLACE_WITH_UUID_FROM_ABOVE',  -- Replace with actual UUID
    'your-email@domain.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.8K2a', -- This is 'admin123' hashed
    'Admin User',
    'admin',
    true,
    true,
    NOW(),
    NOW()
);
```

### Step 3: Verify User Created

```sql
SELECT id, email, full_name, role, is_active, is_verified, created_at 
FROM users 
WHERE email = 'your-email@domain.com';
```

## Default Credentials

The default admin user created by the SQL script has these credentials:

- **Email**: `admin@doctranslator.com`
- **Password**: `admin123`
- **Role**: `admin`

**⚠️ Important**: Change the password immediately after first login!

## Password Security

The default password hash in the SQL script is for `admin123`. For production:

1. **Generate a secure password** (at least 12 characters, mixed case, numbers, symbols)
2. **Generate a proper bcrypt hash** for your password
3. **Replace the password_hash** in the SQL insert statement

### Generating a Secure Password Hash

You can use an online bcrypt generator or create a simple Python script:

```python
import bcrypt

password = "your-secure-password"
salt = bcrypt.gensalt(rounds=12)
hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
print(hashed.decode('utf-8'))
```

## Verification

After creating the admin user, verify it works:

### 1. Check User Exists

```sql
SELECT id, email, full_name, role, is_active, is_verified, created_at 
FROM users 
WHERE role = 'admin';
```

### 2. Test Login (After Backend Deployment)

Once the backend is deployed with the authentication system:

```bash
curl -X POST "https://your-app.railway.app/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@domain.com", "password": "your-password"}'
```

You should receive a response with JWT tokens:

```json
{
  "user": {
    "id": "uuid",
    "email": "your-email@domain.com",
    "full_name": "Admin User",
    "role": "admin",
    "is_active": true,
    "is_verified": true
  },
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer"
  }
}
```

## Troubleshooting

### Common Issues

1. **"psql: command not found"**
   - Install PostgreSQL client: `sudo apt install postgresql-client`

2. **"psycopg2 not available"**
   - Install psycopg2: `pip3 install --user psycopg2-binary`
   - Or use the SQL method instead

3. **"relation 'users' does not exist"**
   - Run the database migration first: `psql '...' -f backend/migrations/001_add_authentication_tables.sql`

4. **"duplicate key value violates unique constraint"**
   - User already exists, this is normal
   - Check existing users: `SELECT email, role FROM users;`

### Verification Commands

```bash
# Check if users table exists
psql 'postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway' -c "\dt users"

# Check users table structure
psql 'postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway' -c "\d users"

# List all users
psql 'postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway' -c "SELECT id, email, full_name, role, is_active, created_at FROM users;"
```

## Next Steps

After creating the admin user:

1. **Deploy the Backend** with authentication system
2. **Deploy the Frontend** with login functionality
3. **Test Admin Login** in the web interface
4. **Create Additional Users** through the admin panel
5. **Configure System Settings** as needed

## Security Notes

- **Change Default Password**: Immediately change the default password
- **Use Strong Passwords**: Minimum 12 characters with complexity
- **Limit Admin Access**: Only create admin users for trusted personnel
- **Monitor Access**: Use audit logs to track admin actions
- **Regular Updates**: Keep the system updated with security patches

The admin user has full access to:
- User management (create, edit, delete users)
- System configuration
- Audit logs
- API key management
- All pipeline and settings management
