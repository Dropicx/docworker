# Railway Development Environment Setup

Complete guide to setting up a development environment on Railway with PostgreSQL database for local development.

## Overview

This approach provides:
- ✅ Production parity (same PostgreSQL database engine)
- ✅ Shared dev database accessible from local machine
- ✅ No local PostgreSQL installation needed
- ✅ Separate dev/production environments
- ✅ Team collaboration with shared data

## Prerequisites

- Railway account ([railway.app](https://railway.app))
- OVH AI Endpoints access token
- Git repository connected to Railway

## Step 1: Create Railway Dev Environment (5 min)

### 1.1 Navigate to Railway Dashboard

1. Go to [railway.app](https://railway.app)
2. Log in to your account
3. Select your DocTranslator project

### 1.2 Create Development Environment

1. Click on the environment dropdown (usually says "production")
2. Click "New Environment"
3. Name it `development` or `dev`
4. Click "Create Environment"

This creates an isolated environment separate from production.

## Step 2: Add PostgreSQL Database (5 min)

### 2.1 Add Database Service

1. Make sure you're in the `development` environment
2. Click "+ New Service"
3. Select "Database"
4. Choose "PostgreSQL"
5. Railway will provision the database automatically
6. Wait 1-2 minutes for it to be ready

### 2.2 Enable Public Networking

**Important:** This allows your local machine to connect to the database.

1. Click on the PostgreSQL service in Railway
2. Go to "Settings" tab
3. Scroll down to "Networking" section
4. Click "Enable Public Networking"
5. Railway will generate a public URL

### 2.3 Copy Database Connection String

1. Still in PostgreSQL service, go to "Connect" tab
2. Select "Public URL" (not Private URL)
3. Copy the full `DATABASE_URL` - it looks like:
   ```
   postgresql://postgres:xxxxxxx@containers-us-west-XX.railway.app:XXXXX/railway
   ```
4. Save this for the next step

## Step 3: Configure Environment Variables (5 min)

### 3.1 Set Railway Environment Variables

In your Railway dev environment:

1. Click on your main service (the one that runs your app)
2. Go to "Variables" tab
3. Add these variables:

```bash
# Required
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token-here
OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1
USE_OVH_ONLY=true

# Optional
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

**Note:** `DATABASE_URL` is automatically set when you add PostgreSQL service.

## Step 4: Initialize Database Schema (10 min)

You have two options to initialize the database:

### Option A: Using Railway CLI (Recommended)

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Link to your project
cd /home/catchmelit/Projects/doctranslator
railway link

# 4. Select development environment
railway environment

# 5. Run database initialization
railway run python backend/app/database/init_db.py
```

### Option B: Temporary Local Connection

```bash
# 1. Create temporary .env file
cd backend
cat > .env << 'EOF'
DATABASE_URL=postgresql://postgres:xxxxxxx@containers-us-west-XX.railway.app:XXXXX/railway
EOF

# 2. Run initialization
python app/database/init_db.py

# 3. Delete .env file (important for security!)
rm .env
```

### Verify Database Initialization

```bash
# Using psql (if installed)
psql "postgresql://postgres:xxx@containers-us-west-XX.railway.app:XXXXX/railway" -c "\dt"

# You should see these tables:
# - universal_prompts
# - document_specific_prompts
# - universal_pipeline_steps
# - ai_interaction_logs
# - system_settings
```

## Step 5: Configure Local Development (5 min)

### 5.1 Create Local Environment File

```bash
cd backend
cp .env.example .env.development
```

### 5.2 Edit .env.development

Open `backend/.env.development` and fill in:

```env
# Railway Dev PostgreSQL (Public URL)
DATABASE_URL=postgresql://postgres:xxxxxxx@containers-us-west-XX.railway.app:XXXXX/railway

# OVH AI Endpoints
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token-here
OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1
USE_OVH_ONLY=true

# Development Settings
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

### 5.3 Verify Configuration

The file `backend/.env.development` should:
- ✅ Exist in backend/ directory
- ✅ Contain your Railway DATABASE_URL
- ✅ Contain your OVH API token
- ❌ NEVER be committed to git (.gitignore protects it)

## Step 6: Test Local Connection (5 min)

### 6.1 Setup Python Environment

```bash
cd backend

# Create virtual environment (if not exists)
python -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 6.2 Start Backend

```bash
# Load environment variables
export $(cat .env.development | xargs)

# Or on Windows (PowerShell):
# Get-Content .env.development | ForEach-Object { $_ -split '=' | Set-Variable -Name $_[0] -Value $_[1] }

# Start backend
python -m uvicorn app.main:app --reload --port 9122
```

### 6.3 Test Endpoints

```bash
# In another terminal:

# Test health
curl http://localhost:9122/api/health

# Test database connection (should return prompts)
curl http://localhost:9122/api/settings/universal-prompts

# Expected output: JSON with medical_validation_prompt, etc.
```

## Step 7: Start Frontend (5 min)

```bash
cd frontend

# Install dependencies (if not done)
npm install

# Start dev server
npm run dev

# Access at http://localhost:5173
```

The frontend connects to backend at `localhost:9122`, which connects to Railway PostgreSQL.

## Daily Development Workflow

### Starting Development

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
export $(cat .env.development | xargs)
python -m uvicorn app.main:app --reload --port 9122

# Terminal 2: Frontend
cd frontend
npm run dev
```

### Testing

1. Open http://localhost:5173
2. Upload a test medical document
3. Verify processing works
4. Check settings panel
5. All data persists in Railway PostgreSQL

### Making Changes

```bash
# 1. Make code changes
# 2. Backend auto-reloads (--reload flag)
# 3. Frontend auto-reloads (Vite HMR)
# 4. Test immediately
# 5. Commit when ready
```

## Security Best Practices

### ✅ DO:

- Use `.env.development` for local dev (gitignored)
- Keep dev and production databases separate
- Rotate DATABASE_URL if accidentally exposed
- Use strong passwords for Railway databases
- Enable 2FA on Railway account

### ❌ DON'T:

- Commit `.env.development` or any `.env.*` files
- Use production DATABASE_URL for development
- Share DATABASE_URL publicly (Slack, email, etc.)
- Store credentials in code or documentation
- Disable public networking after setup (breaks local dev)

## Troubleshooting

### Connection Refused / Timeout

**Problem:** Can't connect to Railway PostgreSQL from local

**Solutions:**
1. Verify "Public Networking" is enabled in Railway
2. Check DATABASE_URL is correct (from "Public URL" tab)
3. Test connection: `psql "$DATABASE_URL" -c "SELECT 1;"`
4. Check firewall allows outbound port 5432

### Database Not Found

**Problem:** Tables don't exist in database

**Solutions:**
1. Run `python app/database/init_db.py` with Railway DATABASE_URL
2. Check Railway logs for initialization errors
3. Verify database exists in Railway dashboard

### Import Errors

**Problem:** `ModuleNotFoundError` when running init_db.py

**Solutions:**
```bash
# Ensure you're in backend directory
cd backend

# Set PYTHONPATH
export PYTHONPATH=/home/catchmelit/Projects/doctranslator/backend

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Slow Performance

**Problem:** Queries are slow from local development

**Cause:** Public database URL has network latency (50-100ms typical)

**Solutions:**
- Normal for dev - production uses internal networking (faster)
- Railway paid plan may improve performance
- Consider caching frequently accessed data
- Use connection pooling (already configured in connection.py)

### Environment Variables Not Loading

**Problem:** Backend can't find OVH token or DATABASE_URL

**Solutions:**
```bash
# Verify .env.development exists
ls -la backend/.env.development

# Manually load variables
export $(cat backend/.env.development | xargs)

# Verify they're loaded
echo $DATABASE_URL
echo $OVH_AI_ENDPOINTS_ACCESS_TOKEN

# Or use python-dotenv
pip install python-dotenv
python -c "from dotenv import load_dotenv; load_dotenv('backend/.env.development'); import os; print(os.getenv('DATABASE_URL'))"
```

## Railway Cost Considerations

### Free Tier:
- ✅ PostgreSQL database included
- ✅ Suitable for development
- ⚠️ Limited to 1GB storage, 1GB RAM
- ⚠️ May sleep after inactivity

### Paid Plans:
- Better performance
- No sleep mode
- More resources
- Production-grade SLA

**Recommendation:** Use free tier for development, upgrade for production.

## Team Collaboration

### Sharing Dev Environment

1. **Share Railway Project:**
   - Invite team members in Railway Dashboard
   - They can access same dev environment
   - Each member gets their own local .env.development

2. **Shared Database:**
   - Everyone connects to same Railway PostgreSQL
   - Changes are immediately visible to team
   - Good for testing with shared data

3. **Isolation:**
   - Use separate Railway projects for individual dev work
   - Or use local SQLite for isolated testing
   - Merge to shared dev environment for integration

## Next Steps

After setup is complete:

1. ✅ Test document upload and processing
2. ✅ Test all 3 document types (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE)
3. ✅ Test multi-language translation
4. ✅ Test admin settings panel
5. ✅ Review database contents in Railway dashboard
6. ✅ Set up production environment (separate guide)

## Related Documentation

- [Database Architecture](./DATABASE.md)
- [API Reference](./API.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Local Development Quick Start](./DEVELOPMENT.md)

## Support

**Railway Issues:**
- [Railway Discord](https://discord.gg/railway)
- [Railway Docs](https://docs.railway.app/)

**Project Issues:**
- Check logs in Railway dashboard
- Review backend console output
- Check browser console for frontend errors
