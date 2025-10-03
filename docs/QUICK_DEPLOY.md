# 🚀 Quick Deployment Checklist

## ✅ Step-by-Step Fix

### 1. Push All Changes to Git
```bash
cd /home/catchmelit/Projects/doctranslator

# Check what needs to be committed
git status

# Add all frontend changes
git add frontend/Dockerfile frontend/entrypoint.sh frontend/src/components/

# Commit
git commit -m "fix: Dynamic nginx config + cleanup settings UI"

# Push to Railway
git push origin main
```

### 2. Verify Railway Environment Variables

**Go to Railway Dashboard → Frontend Service → Variables**

You MUST have these two variables set:
```bash
BACKEND_URL=your-backend-name.railway.internal
BACKEND_PORT=9122
```

**If missing:**
1. Click "+ New Variable"
2. Add both variables
3. Replace `your-backend-name` with your actual backend service name

**To find backend service name:**
- Railway Dashboard → Your Project
- Look at backend service name (e.g., "backend", "doctranslator-backend")
- Use format: `SERVICE-NAME.railway.internal`

### 3. Wait for Railway Deployment

**Check deployment status:**
1. Railway Dashboard → Your Project
2. Watch frontend service for "Building..." → "Deploying..." → "Active"
3. This takes 2-5 minutes

### 4. Check Frontend Logs

```bash
railway logs --service frontend --follow
```

**You MUST see these lines:**
```
🚀 Starting Frontend with dynamic configuration...
📡 Backend URL: backend.railway.internal
📡 Backend Port: 9122
📡 Full Backend URL: http://backend.railway.internal:9122
✅ Nginx configuration generated
```

**If you DON'T see these lines** → The new Dockerfile didn't deploy yet. Wait longer or force redeploy.

### 5. Clear Browser Cache

**After Railway shows "Active":**

**Chrome/Brave:**
1. Press `Ctrl+Shift+Delete` (Windows/Linux) or `Cmd+Shift+Delete` (Mac)
2. Select "Cached images and files"
3. Click "Clear data"

**Or use hard refresh:**
- `Ctrl+Shift+R` (Windows/Linux)
- `Cmd+Shift+R` (Mac)

### 6. Verify Fix

**Open your frontend URL in a NEW incognito/private window:**
1. Press `F12` to open DevTools
2. Go to Console tab
3. Refresh page

**Expected (good):**
```
🌐 API Request: GET /health
✅ API Response: 200 /health
```

**If still errors (bad):**
```
❌ API Error: undefined /health undefined
```

---

## 🔍 Troubleshooting

### Still Getting Errors?

**1. Check Build Hash**
Look at the error - is it showing old hash `index-CJbzsUzR.js` or new hash `index-BOxWL4Uw.js`?

- **Old hash** → Browser cache or Railway hasn't deployed new code
- **New hash** → Environment variables issue

**2. Verify Environment Variables**
```bash
# In Railway Dashboard → Frontend Service → Variables
BACKEND_URL=backend.railway.internal  ← Check this matches your backend name
BACKEND_PORT=9122
```

**3. Force Railway Redeploy**
1. Railway Dashboard → Frontend Service
2. Click "Settings" → "Deploy"
3. Or click "Redeploy" button

**4. Check Backend is Running**
```bash
# Test backend directly
curl https://YOUR-BACKEND-URL.railway.app/api/health
```

Expected: `{"status": "healthy", ...}`

**5. Test Internal Networking**
```bash
# SSH into frontend container (if possible)
railway run --service frontend sh

# Inside container, test backend connection
curl http://backend.railway.internal:9122/api/health
```

---

## 📊 Deployment Status

### How to Know It Worked

✅ **Railway logs show:** Backend URL correctly configured
✅ **Browser DevTools:** API calls return 200 OK
✅ **Frontend loads:** No network errors in console
✅ **Settings page:** Can authenticate and see pipeline config

---

## ⚡ Quick Commands

```bash
# Push changes
git add frontend/ docs/
git commit -m "fix: Dynamic nginx + UI cleanup"
git push origin main

# Watch deployment
railway logs --service frontend --follow

# Check if deployed
railway status

# Force redeploy
railway redeploy --service frontend
```

---

## 🎯 Expected Timeline

1. **Git push** → Immediate
2. **Railway build** → 2-3 minutes
3. **Railway deploy** → 1-2 minutes
4. **Total** → ~5 minutes

After 5 minutes, clear browser cache and test again.
