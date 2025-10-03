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

### Step 2: Set Environment Variable in Frontend Service
1. Railway Dashboard → **Frontend Service** → **Variables** tab
2. Click **"+ New Variable"**
3. Add:
   ```
   Key:   BACKEND_INTERNAL_URL
   Value: ${{YOUR-BACKEND-SERVICE-NAME.RAILWAY_PRIVATE_DOMAIN}}
   ```

   **Example if backend service is named "backend":**
   ```
   BACKEND_INTERNAL_URL=${{backend.RAILWAY_PRIVATE_DOMAIN}}
   ```

   **Example if backend service is named "doctranslator-backend":**
   ```
   BACKEND_INTERNAL_URL=${{doctranslator-backend.RAILWAY_PRIVATE_DOMAIN}}
   ```

4. Click **"Add"** to save

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

### Alternative 1: Use Explicit Service URL
If service reference doesn't work, use explicit URL:

1. Get backend service name from Railway dashboard
2. Set variable manually:
   ```
   BACKEND_INTERNAL_URL=http://YOUR-SERVICE-NAME.railway.internal:9122
   ```

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

1. ✅ Set `BACKEND_INTERNAL_URL=${{backend.RAILWAY_PRIVATE_DOMAIN}}` in frontend variables
2. ✅ Push updated code with `entrypoint.sh` and fixed `Dockerfile`
3. ✅ Redeploy frontend service
4. ✅ Verify logs show correct backend URL
5. ✅ Test frontend - API errors should be gone

**Total time:** 5 minutes

**Questions?** Check `docs/RAILWAY_DEPLOYMENT_GUIDE.md` for detailed troubleshooting.
