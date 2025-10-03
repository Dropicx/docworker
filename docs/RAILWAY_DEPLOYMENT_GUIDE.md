# 🚂 Railway Deployment Guide - Modular Pipeline System

Complete guide to deploying the DocTranslator modular pipeline system on Railway.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Database Migration](#database-migration)
3. [Environment Variables](#environment-variables)
4. [Deployment Steps](#deployment-steps)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Using the Modular Pipeline](#using-the-modular-pipeline)
7. [Troubleshooting](#troubleshooting)

---

## ✅ Prerequisites

- Railway account with project already created
- PostgreSQL database service in Railway
- OVH AI Endpoints access token
- Git repository connected to Railway

---

## 🗄️ Database Migration

### What's New in the Database

The modular pipeline system adds **5 new tables**:

1. **`ocr_configuration`** - OCR engine selection (Tesseract/PaddleOCR/Vision LLM/Hybrid)
2. **`available_models`** - AI model registry (Llama 3.3 70B, Mistral Nemo, etc.)
3. **`dynamic_pipeline_steps`** - User-defined pipeline steps with custom prompts
4. **`pipeline_jobs`** - Job tracking for pipeline execution
5. **`pipeline_step_executions`** - Detailed step execution logs

### Migration Process

**Option 1: Automatic Migration (Recommended)**

Railway will automatically run database initialization on deployment:

1. The `init_db.py` script runs automatically
2. New tables are created
3. Default data is seeded (OCR config, models, pipeline steps)

**Option 2: Manual Migration**

If you need to run migration manually:

```bash
# Connect to Railway backend container via CLI
railway run bash

# Inside container, run:
cd backend
python app/database/init_db.py
```

### Migration Safety

✅ **Safe**: The migration only **creates new tables** - it does NOT modify existing tables.

✅ **No Data Loss**: Your existing `universal_prompts`, `document_specific_prompts`, and other tables remain untouched.

✅ **Rollback**: If needed, you can drop new tables manually:

```sql
DROP TABLE IF EXISTS pipeline_step_executions CASCADE;
DROP TABLE IF EXISTS pipeline_jobs CASCADE;
DROP TABLE IF EXISTS dynamic_pipeline_steps CASCADE;
DROP TABLE IF EXISTS available_models CASCADE;
DROP TABLE IF EXISTS ocr_configuration CASCADE;
```

---

## 🔐 Environment Variables

### Required Variables (Same as Before)

```bash
# OVH AI Endpoints (REQUIRED)
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-ovh-token-here

# Database (Automatically set by Railway PostgreSQL)
DATABASE_URL=postgresql://...

# Optional Configuration
USE_OVH_ONLY=true
OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1
OVH_MAIN_MODEL=Meta-Llama-3_3-70B-Instruct
OVH_PREPROCESSING_MODEL=Mistral-Nemo-Instruct-2407
```

### New Optional Variables (For Future Worker System)

```bash
# Worker System (Not yet active, for future use)
USE_REDIS_QUEUE=false  # Set to 'true' when Redis workers are ready
REDIS_URL=redis://...  # Only needed when USE_REDIS_QUEUE=true
```

### Frontend Environment Variables

**REQUIRED:** Set these environment variables in Railway frontend service:

```bash
# Backend Internal URL (Railway private network)
BACKEND_URL=backend.railway.internal  # Replace with your backend service name

# Backend Port
BACKEND_PORT=9122
```

**How to set in Railway:**
1. Go to Railway Dashboard → Frontend Service → Variables
2. Click **"+ New Variable"** for each:

   **Variable 1:**
   - **Key**: `BACKEND_URL`
   - **Value**: `YOUR-BACKEND-SERVICE-NAME.railway.internal`
   - Example: `backend.railway.internal` or `doctranslator-backend.railway.internal`

   **Variable 2:**
   - **Key**: `BACKEND_PORT`
   - **Value**: `9122`

3. Click **"Add"** for each variable
4. Redeploy frontend service

**Finding your backend service internal URL:**
- Railway Dashboard → Backend Service → Settings
- Look for "Private Networking" or internal domain
- Format is always: `SERVICE-NAME.railway.internal`

---

## 🚀 Deployment Steps

### Step 1: Push Code to Repository

```bash
# Ensure you're on the correct branch
git status

# Add all changes
git add .

# Commit with descriptive message
git commit -m "feat: Add modular pipeline system with user-configurable steps"

# Push to Railway-connected branch (usually main or dev)
git push origin main  # or 'dev' if that's your Railway branch
```

### Step 2: Deploy Backend Service

1. **Railway Dashboard** → Your Project → **Backend Service**
2. Click **"Deploy"** (or it auto-deploys on push)
3. Watch deployment logs for:
   ```
   🚀 Medical Document Translator starting up...
   🗄️ Initializing database...
   ✅ Database initialized successfully
   ✅ Database seeded with unified data successfully
   ✅ Database seeded with modular pipeline configuration successfully
   ```

### Step 3: Deploy Frontend Service

1. **Railway Dashboard** → Your Project → **Frontend Service**
2. Click **"Deploy"** (or auto-deploys)
3. Verify build completes successfully

### Step 4: Verify Services Health

**Backend Health Check:**
```bash
curl https://your-backend-url.railway.app/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "ovh_api": "connected"
}
```

**Frontend Health Check:**
```bash
curl https://your-frontend-url.railway.app/health
```

Expected: `200 OK` with "healthy" response

---

## ✅ Post-Deployment Verification

### 1. Verify Database Tables Created

Connect to Railway PostgreSQL:

```bash
railway connect  # Select PostgreSQL service
```

Then run:

```sql
-- Check new tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('ocr_configuration', 'available_models', 'dynamic_pipeline_steps', 'pipeline_jobs', 'pipeline_step_executions');
```

Expected: 5 rows returned

### 2. Verify Seed Data

```sql
-- Check OCR configuration
SELECT selected_engine FROM ocr_configuration;
-- Expected: TESSERACT

-- Check available models
SELECT name, display_name FROM available_models;
-- Expected: 3 rows (Llama 3.3 70B, Mistral Nemo, Qwen 2.5 VL)

-- Check pipeline steps
SELECT name, "order", enabled FROM dynamic_pipeline_steps ORDER BY "order";
-- Expected: 9 rows (Medical Validation, Classification, etc.)
```

### 3. Test API Endpoints

**Get Available Models** (requires authentication):

```bash
# First authenticate (use your settings access code)
curl -X POST https://your-backend-url.railway.app/api/settings/auth \
  -H "Content-Type: application/json" \
  -d '{"password": "your-access-code"}'

# Response will include: {"session_token": "..."}

# Use token to access pipeline API
curl https://your-backend-url.railway.app/api/pipeline/models \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

Expected: JSON array with 3 models

**Get Pipeline Steps**:

```bash
curl https://your-backend-url.railway.app/api/pipeline/steps \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

Expected: JSON array with 9 pipeline steps

### 4. Test Frontend UI

1. Open your frontend URL in browser
2. Go to **Settings** (gear icon)
3. Enter access code and authenticate
4. Click **"⚙️ Pipeline-Konfiguration"** tab
5. You should see:
   - OCR Engine selection (4 options: Tesseract, PaddleOCR, Vision LLM, Hybrid)
   - Pipeline steps list (9 default steps)
   - Add/Edit/Delete buttons

---

## 🎯 Using the Modular Pipeline

### Configure OCR Engine

1. **Settings** → **Pipeline-Konfiguration**
2. Select your preferred OCR engine:
   - **Tesseract** (fast, good for clean docs)
   - **Vision LLM** (slow but accurate, complex docs)
   - **Hybrid** (automatic routing - recommended)
   - **PaddleOCR** (future: 30x faster than Vision LLM)
3. Click **"Speichern"** (Save)

### Add/Edit Pipeline Steps

**Add New Step:**

1. Click **"Schritt hinzufügen"** (Add Step)
2. Fill in:
   - **Name**: e.g., "Custom Validation"
   - **Order**: Position in pipeline (1-100)
   - **Prompt Template**: Must include `{input_text}`
   - **AI Model**: Select from dropdown
   - **Temperature**: 0.0 (precise) to 2.0 (creative)
   - **Max Tokens**: Optional limit
3. Click **"Erstellen"** (Create)

**Edit Existing Step:**

1. Click **Edit** (pencil icon) on any step
2. Modify prompt, model, or settings
3. Click **"Speichern"** (Save)

**Delete Step:**

1. Click **Delete** (trash icon)
2. Confirm deletion

**Enable/Disable Step:**

1. Click the **Settings** icon on a step
2. Step is immediately enabled/disabled

### Test Your Pipeline

1. Go to main upload page
2. Upload a medical document
3. Select target language
4. Click **"Dokument verarbeiten"** (Process Document)
5. Watch progress - new pipeline executes your configured steps!

---

## 🐛 Troubleshooting

### Database Initialization Failed

**Symptoms:**
```
❌ Database initialization failed
```

**Solution:**
1. Check Railway PostgreSQL is running
2. Verify `DATABASE_URL` is set correctly
3. Check backend logs for specific error
4. Manually run: `railway run python backend/app/database/init_db.py`

---

### Pipeline Steps Not Showing

**Symptoms:** Frontend shows "Keine Pipeline-Schritte konfiguriert."

**Solution:**
1. Check backend logs for seeding errors
2. Verify database tables exist (see verification section)
3. Manually seed: `railway run python backend/app/database/modular_pipeline_seed.py`

---

### Frontend Can't Reach Backend API

**Symptoms:**
- "❌ API Error: undefined /health undefined"
- "Request aborted"
- "NetworkError when attempting to fetch resource"
- Frontend loads but API calls fail

**Root Cause:** Frontend can't connect to backend service

**Solution:**
1. **Check Environment Variables:**
   ```bash
   # In Railway frontend service → Variables, verify both exist:
   BACKEND_URL=backend.railway.internal
   BACKEND_PORT=9122
   ```

2. **Verify Backend Service Name:**
   - Railway Dashboard → Your Project → Check backend service name
   - Update `BACKEND_URL` to match: `your-backend-name.railway.internal`
   - Example: If backend is "doctranslator-backend", use:
     ```bash
     BACKEND_URL=doctranslator-backend.railway.internal
     ```

3. **Check Frontend Logs:**
   ```bash
   railway logs --service frontend
   ```
   Look for:
   ```
   📡 Backend URL: backend.railway.internal
   📡 Backend Port: 9122
   📡 Full Backend URL: http://backend.railway.internal:9122
   ```

4. **Test Backend Directly:**
   ```bash
   # Get backend public URL from Railway dashboard
   curl https://YOUR-BACKEND-URL.railway.app/api/health
   ```

5. **Verify Internal Networking:**
   - Railway Dashboard → Backend Service → Settings
   - Check "Private Networking" is enabled
   - Copy the internal domain (should end in `.railway.internal`)

6. **Redeploy Frontend:**
   - After setting/updating variables, click "Deploy" in Railway frontend service

---

### Authentication Failed

**Symptoms:** "Not authenticated" when accessing pipeline settings

**Solution:**
1. Verify you're logged in to Settings
2. Check browser localStorage has `settings_auth_token`
3. Try logging out and back in
4. Check backend `/api/settings/auth` endpoint works

---

### OCR Engine Selection Not Saving

**Symptoms:** OCR engine reverts after save

**Solution:**
1. Check browser console for errors
2. Verify backend `/api/pipeline/ocr-config` endpoint works
3. Check PostgreSQL `ocr_configuration` table exists
4. Try manual update via API (see Test API Endpoints section)

---

## 📊 Monitoring

### Backend Logs

Watch real-time backend logs:

```bash
railway logs --service backend --follow
```

Look for:
- `✅ Database initialized successfully`
- `✅ Database seeded with modular pipeline configuration successfully`
- `🚀 Medical Document Translator starting up...`

### Database Metrics

Railway Dashboard → PostgreSQL → Metrics

Monitor:
- **Connections**: Should stay stable
- **Queries**: Will increase with pipeline activity
- **Storage**: New tables add ~10MB

### Performance

Expected metrics:
- **Database initialization**: ~5-10 seconds
- **API response time**: <200ms for pipeline config
- **Pipeline execution**: Depends on steps (1-5 minutes typical)

---

## 🔮 Future: Redis Worker System

The system is **worker-ready** but currently runs synchronously.

### When to Enable Workers

Enable Redis workers when:
- Processing >100 documents/day
- Need parallel processing
- Want to scale OCR and AI separately

### Migration to Workers

1. **Add Redis to Railway:**
   - Railway Dashboard → Add Service → Redis

2. **Set Environment Variables:**
   ```bash
   USE_REDIS_QUEUE=true
   REDIS_URL=redis://...  # Provided by Railway Redis
   ```

3. **Deploy Worker Processes:**
   - Worker 1: AI API requests
   - Worker 2: PaddleOCR processing

4. **Update Configuration:**
   - No code changes needed!
   - System automatically switches to queue-based execution

---

## 📚 Additional Resources

- **API Documentation**: `/docs/API.md`
- **Database Schema**: `/docs/DATABASE.md`
- **Architecture**: `/docs/ARCHITECTURE.md`
- **Backend Code**: `/backend/app/services/modular_pipeline_executor.py`
- **Frontend Code**: `/frontend/src/components/settings/PipelineBuilder.tsx`

---

## ✅ Deployment Checklist

- [ ] Code pushed to Railway-connected branch
- [ ] Backend deployed successfully
- [ ] Frontend deployed successfully
- [ ] Database tables created (5 new tables)
- [ ] Seed data inserted (OCR config, models, steps)
- [ ] API endpoints responding (auth, pipeline config, models, steps)
- [ ] Frontend Pipeline tab accessible
- [ ] Can select OCR engine and save
- [ ] Can add/edit/delete pipeline steps
- [ ] Document processing uses new pipeline
- [ ] Logs show no errors

---

## 🎉 Success!

Your modular pipeline system is now live on Railway!

**Next Steps:**
1. Configure your preferred OCR engine
2. Customize pipeline steps for your needs
3. Test with real medical documents
4. Monitor performance and adjust as needed

**Need Help?**
- Check backend logs: `railway logs --service backend`
- Check frontend logs: `railway logs --service frontend`
- Review this guide's Troubleshooting section
- Check Railway service health in dashboard

---

**Happy Deploying! 🚀**
