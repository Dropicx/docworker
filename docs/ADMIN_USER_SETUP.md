# Auto-Admin User Setup Guide

## Overview

The doctranslator backend automatically creates an admin user on startup if the required environment variables are set. This eliminates the need for manual admin user creation.

## How It Works

When the backend starts, the `init_database()` function automatically:
1. Creates database tables (if needed)
2. Seeds modular pipeline configuration
3. **Checks for admin user environment variables**
4. **Creates admin user if credentials are provided**
5. **Updates existing user to ADMIN role if they exist**

## Setup in Railway

### Step 1: Set Environment Variables

Add these environment variables to your Railway backend service:

```bash
# Required for admin creation
INITIAL_ADMIN_EMAIL=admin@doctranslator.com
INITIAL_ADMIN_PASSWORD=YourSecurePassword123!

# Optional: Admin display name
INITIAL_ADMIN_NAME="System Administrator"

# Required: JWT secret
JWT_SECRET_KEY=your-jwt-secret-key-here
```

### Step 2: Deploy

Simply deploy your backend. On startup, the admin user will be created automatically.

### Step 3: Verify

Check the logs to confirm admin creation:

```
✅ Created new admin user: admin@doctranslator.com
```

## Behavior

### First Startup (No Admin Exists)
- Creates a new admin user with the provided credentials
- User is created with ADMIN role
- Email is verified, account is active
- Log: `✅ Created new admin user: {email}`

### Admin Already Exists
- Checks if admin user exists
- If exists and is ADMIN: Logs success, no changes
- Log: `✅ Admin user {email} already exists`

### User Exists but Not Admin
- Upgrades existing user to ADMIN role
- Log: `✅ Updated existing user {email} to ADMIN role`

### Environment Variables Not Set
- Skips admin user creation
- Log: `ℹ️ INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD not set - skipping admin user creation`

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `INITIAL_ADMIN_EMAIL` | Email for admin account | `admin@doctranslator.com` |
| `INITIAL_ADMIN_PASSWORD` | Password for admin account | `SecurePass123!` |
| `JWT_SECRET_KEY` | Secret key for JWT signing | Auto-generated or custom |

### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `INITIAL_ADMIN_NAME` | Display name for admin | `System Administrator` | `"John Doe"` |

## Security Considerations

1. **Password Requirements**
   - Minimum 8 characters (enforced by system)
   - Recommend: 12+ characters with mixed case, numbers, symbols

2. **Email Validation**
   - Must be a valid email format (containing `@`)
   - Used for login authentication

3. **Idempotent Creation**
   - Safe to restart the app - won't create duplicate admins
   - Can safely update environment variables and restart

4. **Role Upgrades**
   - Existing users with the same email will be upgraded to ADMIN
   - No account deletion occurs

## Troubleshooting

### Admin User Not Created

**Problem:** No admin user in database despite setting environment variables

**Possible Causes:**
1. Environment variables not set in Railway
2. Database connection issues
3. Errors during user creation (check logs)

**Solution:**
```bash
# Check if environment variables are set
railway variables

# Check logs for errors
railway logs --service backend
```

### Existing User Not Upgraded

**Problem:** User exists but is still a regular user, not admin

**Solution:**
- Restart the backend service
- The upgrade logic runs on every startup
- Check logs: `✅ Updated existing user {email} to ADMIN role`

### Environment Variables Ignored

**Problem:** Log shows "skipping admin user creation"

**Solution:**
- Verify variables are set: `railway variables`
- Check exact variable names (case-sensitive)
- Restart backend service

## Manual Creation (Fallback)

If automatic creation fails, use the manual script:

```bash
# SSH into Railway or run locally
railway shell

# Run admin creation script
python backend/scripts/create_admin_user.py
```

## Integration with Other Systems

### CI/CD Pipeline

You can set environment variables in your CI/CD configuration:

```yaml
# Example for GitHub Actions
env:
  INITIAL_ADMIN_EMAIL: ${{ secrets.ADMIN_EMAIL }}
  INITIAL_ADMIN_PASSWORD: ${{ secrets.ADMIN_PASSWORD }}
  JWT_SECRET_KEY: ${{ secrets.JWT_SECRET_KEY }}
```

### Docker Compose

```yaml
services:
  backend:
    environment:
      INITIAL_ADMIN_EMAIL: admin@localhost
      INITIAL_ADMIN_PASSWORD: admin123
      JWT_SECRET_KEY: local-secret-key
```

## Logs Reference

### Successful Admin Creation
```
✅ Created new admin user: admin@doctranslator.com
```

### Admin Already Exists
```
✅ Admin user admin@doctranslator.com already exists
```

### User Upgraded to Admin
```
✅ Updated existing user user@example.com to ADMIN role
```

### Skipped (No Variables)
```
ℹ️ INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD not set - skipping admin user creation
```

### Error
```
❌ Error creating admin user: <error message>
```

## Best Practices

1. **Use Strong Passwords**: At least 12 characters with complexity
2. **Secure Secret Keys**: Use random, secure JWT secret keys
3. **Review Logs**: Always check startup logs for admin creation status
4. **Update Passwords**: Change admin password after first login
5. **Enable 2FA**: Consider enabling two-factor authentication for admin accounts
6. **Limit Admin Accounts**: Keep admin accounts to minimum necessary

## Next Steps

After admin user is created:
1. Login via `/login` page with your credentials
2. Access admin settings via settings icon
3. Manage users, API keys, and view audit logs
4. Configure system settings as needed

The auto-admin creation makes deployment seamless - just set the environment variables and deploy! 🚀
