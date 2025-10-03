# 🚨 Railway Quick Fix - Frontend API Connection

## Problem
Frontend shows: `❌ API Error: undefined /health undefined` and `Request aborted`

## Root Cause
Frontend nginx can't find the backend service - missing environment variable.

---

## ✅ Solution (3 Steps)

### Step 1: Check Your Backend Service Name
1. Open Railway Dashboard
2. Go to your project
3. Note the **exact name** of your backend service (e.g., "backend", "doctranslator-backend", etc.)

### Step 2: Verify Environment Variables in Frontend Service

⚠️ **Important:** You should already have these variables set. Just verify they exist:

1. Railway Dashboard → **Frontend Service** → **Variables** tab
2. Check these variables exist:
   ```
   BACKEND_URL=YOUR-BACKEND-SERVICE-NAME.railway.internal
   BACKEND_PORT=9122
   ```

   **Example:**
   ```
   BACKEND_URL=backend.railway.internal
   BACKEND_PORT=9122
   ```

3. **If missing**, add them:
   - Click **"+ New Variable"**
   - Add both variables with your backend service's internal domain

**Finding your backend internal domain:**
- Railway Dashboard → Backend Service → Settings → Copy the internal domain
- Format: `SERVICE-NAME.railway.internal`

### Step 3: Deploy Updated Code & Redeploy Frontend
1. **Push the fixed code:**
   ```bash
   git add frontend/Dockerfile frontend/entrypoint.sh docs/
   git commit -m "fix: Dynamic nginx configuration for Railway internal networking"
   git push origin main
   ```

2. **Wait for automatic deployment** (both services will redeploy)

3. **If auto-deploy is disabled**, manually deploy:
   - Railway Dashboard → Frontend Service → Click **"Deploy"**

---

## ✅ Verify Fix

### 1. Check Frontend Logs
```bash
railway logs --service frontend
```

**Expected output:**
```
🚀 Starting Frontend with dynamic configuration...
📡 Backend URL: http://backend.railway.internal:9122
✅ Nginx configuration generated
🚀 Starting nginx...
```

### 2. Test Frontend
Open your frontend URL: `https://your-frontend.railway.app`

**Expected:**
- ✅ No API errors in browser console
- ✅ Health check passes
- ✅ Page loads without errors

### 3. Test Backend Connection
Open browser console and check:
```javascript
// Should see successful API calls
🌐 API Request: GET /health
✅ API Response: 200 /health
```

---

## 🆘 Still Not Working?

### Alternative 1: Check Environment Variable Values
If still not working, verify the exact values:

1. Railway Dashboard → Frontend Service → Variables
2. Check values match your backend:
   ```
   BACKEND_URL=your-backend-service-name.railway.internal
   BACKEND_PORT=9122
   ```
3. Update if needed and redeploy

### Alternative 2: Check Backend Health First
```bash
# Test backend is accessible
railway run --service backend curl http://localhost:9122/api/health
```

### Alternative 3: Check Service Names
Railway service names must match exactly (case-sensitive):
```bash
railway status
```

---

## 📝 What Changed

**Before:**
- nginx.conf had hardcoded service name: `http://doctranslator-backend.railway.internal:9122`
- This failed because your backend service has a different name

**After:**
- `entrypoint.sh` dynamically generates nginx.conf using `BACKEND_INTERNAL_URL` environment variable
- Railway's service reference system automatically resolves the correct internal URL
- Frontend can connect to backend regardless of service naming

---

## 🎯 Summary

1. ✅ Verify `BACKEND_URL` and `BACKEND_PORT` are set in Railway frontend variables
2. ✅ Push updated code with `entrypoint.sh` and fixed `Dockerfile`
3. ✅ Redeploy frontend service
4. ✅ Verify logs show correct backend URL (should show both URL and port)
5. ✅ Test frontend - API errors should be gone

**Total time:** 5 minutes

**What the fix does:** The entrypoint script now uses your existing `BACKEND_URL` and `BACKEND_PORT` environment variables to dynamically generate the nginx configuration at container startup.

**Questions?** Check `docs/RAILWAY_DEPLOYMENT_GUIDE.md` for detailed troubleshooting.
