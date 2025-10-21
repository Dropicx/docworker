# Flower Dashboard Setup Guide

Complete setup instructions for the Flower monitoring dashboard on Railway.

## 📋 Railway Services Overview

Your project should have these services:
- `redis` - Message broker
- `worker-service` - Celery worker with priority queues
- `flower-service` - Monitoring dashboard ← **Configure this**
- `backend` - FastAPI backend
- `frontend` - React frontend

---

## 🚀 Step-by-Step Setup

### Step 1: Flower Service Configuration

**In Railway → flower-service → Settings:**

#### Build Settings
- **Dockerfile Path**: `dockerfiles/Dockerfile.flower`
- **Root Directory**: (leave empty)

#### Environment Variables
```bash
# Redis connection (reference from Redis service)
REDIS_URL=${{REDIS.REDIS_URL}}

# Port (Railway auto-detects)
PORT=5555

# Basic Authentication (IMPORTANT - protects your dashboard)
FLOWER_BASIC_AUTH=admin:your-secure-password-here
```

⚠️ **Replace `your-secure-password-here` with a strong password!**

---

### Step 2: Expose Flower Publicly

**In Railway → flower-service → Settings → Networking:**

1. Click **"Generate Domain"**
2. Copy the generated URL (e.g., `https://flower-service-production-xxxx.up.railway.app`)
3. Save it for Step 3

---

### Step 3: Update Backend Configuration

**In Railway → backend → Settings → Variables:**

Add or update:
```bash
# Public Flower URL (from Step 2) - for frontend button
FLOWER_URL_PUBLIC=https://flower-service-production-xxxx.up.railway.app

# Internal Flower URL - for backend API calls (faster, private network)
FLOWER_URL_INTERNAL=http://flower-service.railway.internal:5555

# Same auth credentials as flower-service (for API access)
FLOWER_BASIC_AUTH=admin:your-secure-password-here
```

⚠️ **Use the EXACT same `FLOWER_BASIC_AUTH` value as flower-service!**

**Why two URLs?**
- `FLOWER_URL_INTERNAL`: Backend → Flower API calls (stays on Railway private network, faster)
- `FLOWER_URL_PUBLIC`: Frontend button → User's browser (needs public URL)

---

### Step 4: Deploy Everything

1. Commit and push all code changes
2. Railway will auto-deploy:
   - `flower-service` (with public domain)
   - `backend` (with updated Flower URL)
   - `frontend` (with updated dashboard component)

---

## ✅ Verify It's Working

### 1. Check Flower Service Logs

In Railway → flower-service → Logs, you should see:
```
[I] Visit me at http://0.0.0.0:5555
[I] Broker: redis://...
[I] Registered tasks: ['process_medical_document', ...]
```

### 2. Test Direct Access

Open the Flower URL in your browser:
```
https://flower-service-production-xxxx.up.railway.app
```

You should see:
- Login prompt (username: `admin`, password: your password)
- Flower dashboard with worker stats

### 3. Test via App UI

1. Go to your DocTranslator app
2. Open **Settings** modal
3. Click **"Worker Monitoring"** tab
4. You should see:
   - ✅ Worker stats cards (workers, tasks, queues)
   - ✅ "Open Flower Dashboard" button
5. Click the button → Opens Flower in new tab

---

## 🔒 Security

✅ **Double Authentication:**
- Settings modal requires access code
- Flower requires basic auth (username/password)

✅ **Railway Private Network:**
- Worker ↔ Flower communication stays on private network
- Only the web UI is public (protected by auth)

✅ **No Sensitive Data Exposed:**
- Flower shows task metadata, not task payloads
- Redis credentials are not displayed

---

## 🎯 Features Available

Once configured, you get:

### In-App Stats (Settings → Worker Monitoring)
- 👷 Worker count (active/total)
- 📊 Task count (total processed)
- 📋 Queue status (high_priority, default, low_priority, maintenance)
- 🔄 Auto-refresh every 5 seconds

### Full Flower Dashboard (New Tab)
- 📈 Real-time graphs and metrics
- 📜 Complete task history
- 👷 Worker pool management
- 🔄 Task revocation and retry
- 📊 Queue statistics
- ⏱️ Task execution timelines
- 🔍 Search and filter tasks

---

## 🐛 Troubleshooting

### Flower shows "Service unavailable"

**Check:**
1. Flower service is running in Railway
2. `FLOWER_URL` in backend matches the generated domain
3. `FLOWER_BASIC_AUTH` is set in BOTH services

**Solution:** Redeploy flower-service and backend

### Can't login to Flower

**Check:**
1. Using correct username: `admin`
2. Using correct password from `FLOWER_BASIC_AUTH`

**Solution:** Update password in both services, redeploy

### Worker stats show 0 workers

**Check:**
1. Worker service is running
2. Worker is connected to same Redis as Flower
3. Check worker logs for connection errors

**Solution:** Check `REDIS_URL` in worker-service

---

## 📝 Configuration Summary

| Service | Environment Variable | Value |
|---------|---------------------|-------|
| **flower-service** | `REDIS_URL` | `${{REDIS.REDIS_URL}}` |
| **flower-service** | `PORT` | `5555` |
| **flower-service** | `FLOWER_BASIC_AUTH` | `admin:your-password` |
| **backend** | `FLOWER_URL_PUBLIC` | `https://flower-xxx.railway.app` |
| **backend** | `FLOWER_URL_INTERNAL` | `http://flower-service.railway.internal:5555` |
| **backend** | `FLOWER_BASIC_AUTH` | `admin:your-password` (same) |

---

## 🎉 You're Done!

Your Flower monitoring dashboard is now fully operational with:
- ✅ Priority queue monitoring
- ✅ Worker health tracking
- ✅ Real-time task statistics
- ✅ Complete task history
- ✅ Secure authentication
- ✅ Professional UI

Enjoy monitoring your workers! 🌸
