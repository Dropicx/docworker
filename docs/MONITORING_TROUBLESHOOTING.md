# Monitoring Dashboard Troubleshooting

Guide for fixing "Workers: 0 / 0" and other monitoring issues.

## What I Fixed

### 1. ✅ Real Queue Lengths from Redis
**Before**: Hardcoded `0` for all queues
**After**: Live queue lengths from Redis using `LLEN` command

```python
def get_queue_lengths():
    redis_client = get_redis()
    return {
        "high_priority": redis_client.llen("high_priority"),
        "default": redis_client.llen("default"),
        "low_priority": redis_client.llen("low_priority"),
        "maintenance": redis_client.llen("maintenance")
    }
```

### 2. ✅ Improved Worker Detection
**Before**: Checked `w.get('status') == 'Online'` which Flower might not return
**After**: Robust detection that handles multiple Flower API formats

```python
# Fallback logic:
# 1. Check for 'stats' or 'status' fields
# 2. If status != 'offline', count as active
# 3. If no status info, assume all returned workers are active
if active_workers == 0 and total_workers > 0:
    active_workers = total_workers
```

### 3. ✅ Added Debug Logging
- Backend logs Flower API response
- Frontend logs received data in browser console

---

## Current Status Analysis

Based on your screenshot:

```
Workers: 0 / 0 aktiv
Tasks: 3 gesamt
Queues: All 0
```

**What this means**:

1. **Workers: 0 / 0**
   - ❌ **Flower is NOT seeing any workers**
   - Possible causes:
     - Workers haven't started yet
     - Workers not connected to same Redis as Flower
     - Worker service not deployed/running

2. **Tasks: 3**
   - ✅ **This is correct** - historical task count from Redis
   - Means 3 tasks have been processed since worker started

3. **Queues: All 0**
   - ✅ **This is correct** - no tasks currently waiting
   - Normal if no documents uploaded recently

---

## Debugging Steps

### Step 1: Check if Flower Service is Running

**In Railway Dashboard**:
1. Go to `flower-service`
2. Check **Deployment** status → Should show "Active"
3. Check **Logs** → Should see:
   ```
   [INFO/MainProcess] Received task: process_medical_document
   [INFO/MainProcess] celery@flower-xxx ready
   ```

**If not deployed**: Deploy `flower-service` first!

### Step 2: Check if Worker Service is Running

**In Railway Dashboard**:
1. Go to `worker-service`
2. Check **Deployment** status → Should show "Active"
3. Check **Logs** → Should see:
   ```
   ✅ Celery worker initialized with enhanced configuration
   ⚙️  Worker settings:
      - Concurrency: 2
   🔄 Priority queues configured:
      - high_priority: Interactive user uploads
   [MainProcess] Connected to redis://...
   [MainProcess] celery@worker-xxx ready.
   ```

**If not seeing "ready"**: Worker failed to start, check error logs.

### Step 3: Check Redis Connection

**All services must connect to SAME Redis instance!**

**In Railway Dashboard** (check all services):
- `worker-service` → Variables → `REDIS_URL`
- `flower-service` → Variables → `REDIS_URL`
- `beat-service` → Variables → `REDIS_URL`
- `backend` → Variables → `REDIS_URL`

**They MUST all have the EXACT same value**:
```
REDIS_URL=${{REDIS.REDIS_URL}}
```

If different, workers and Flower can't see each other!

### Step 4: Check Backend Logs

**In Railway → backend → Logs**, look for:

```
📊 Flower API response - Workers: 0, Tasks: 3
```

**If you see this**: Flower is running but workers haven't registered yet.

**If you don't see this**: The monitoring API endpoint isn't being called.

### Step 5: Check Frontend Browser Console

**In your browser**:
1. Open Settings Modal → Worker Monitoring tab
2. Open Browser DevTools (F12)
3. Go to **Console** tab
4. Look for:
   ```
   📊 Worker Stats received: {workers: {total: 0, active: 0}, tasks: {total: 3}, queues: {...}}
   ```

**What to check**:
- **workers.total: 0** → Flower not seeing workers
- **workers.total > 0, active: 0** → Workers registered but detected as offline
- **Error messages** → API call failing

### Step 6: Check Flower Web UI Directly

**Open Flower in browser**:
1. Get public URL from Railway → `flower-service` → Settings → **Domain**
2. Open in browser (e.g., `https://flower-service-production-xxx.railway.app`)
3. Login with basic auth (username/password from `FLOWER_BASIC_AUTH`)
4. Check **Workers** page

**What you should see**:
- At least 1 worker listed (e.g., `celery@worker-1-xxx`)
- Status: **Online**
- Active tasks, completed tasks stats

**If no workers shown**: Workers not connected to Flower!

---

## Common Issues & Solutions

### Issue 1: "Workers: 0 / 0" but Worker Logs Show "ready"

**Cause**: Workers and Flower using different Redis instances

**Solution**:
1. Check `REDIS_URL` in all services (see Step 3 above)
2. Ensure all use `${{REDIS.REDIS_URL}}` reference
3. Redeploy all services

### Issue 2: "Workers: 0 / 0" and Worker Not Starting

**Cause**: Worker service deployment failed

**Solution**:
1. Check worker logs for errors
2. Common errors:
   - **Module not found**: Python dependency missing
   - **Redis connection failed**: `REDIS_URL` incorrect
   - **Import error**: Code syntax error

### Issue 3: Flower Shows Workers, Frontend Shows 0

**Cause**: Backend monitoring API can't reach Flower

**Solution**:
1. Check `FLOWER_URL_INTERNAL` in backend
2. Should be: `http://flower-service.railway.internal:5555`
3. Check `FLOWER_BASIC_AUTH` matches between services
4. Check backend logs for Flower API errors

### Issue 4: "Connection refused" Error

**Cause**: Flower service not running or wrong URL

**Solution**:
1. Verify flower-service deployed and active
2. Check `FLOWER_URL_INTERNAL` uses Railway private networking:
   ```
   http://flower-service.railway.internal:5555
   ```
3. NOT public URL like `https://flower-xxx.railway.app`

### Issue 5: Queue Lengths All 0 (Expected)

**This is normal** if:
- No documents currently being processed
- All tasks completed successfully
- No scheduled maintenance tasks pending

**Queues only show > 0 when**:
- Document uploaded and waiting (high_priority)
- Workers busy, tasks queuing up (default)
- Scheduled tasks waiting (maintenance)

---

## Expected Values

### Normal Operation (1 Worker)
```
Workers: 1 / 1 aktiv
Tasks: X gesamt (increases over time)
Queues:
  High Priority: 0-2 (during upload)
  Default: 0
  Low Priority: 0
  Maintenance: 0-1 (during scheduled cleanup)
```

### Normal Operation (3 Replicas)
```
Workers: 3 / 3 aktiv
Tasks: X gesamt
Queues: (same as above)
```

### During Document Processing
```
Workers: 1 / 1 aktiv
Tasks: X gesamt
Queues:
  High Priority: 1 (document being processed)
  Default: 0
  Low Priority: 0
  Maintenance: 0
```

### During High Traffic (Multiple Documents)
```
Workers: 3 / 3 aktiv
Tasks: X gesamt
Queues:
  High Priority: 5 (waiting for free worker)
  Default: 0
  Low Priority: 0
  Maintenance: 0
```

---

## Verification Checklist

- [ ] 1. Flower service deployed and running
- [ ] 2. Worker service deployed and running
- [ ] 3. Beat service deployed and running (if created)
- [ ] 4. All services using same `REDIS_URL`
- [ ] 5. Flower logs show workers registered
- [ ] 6. Worker logs show "celery@worker-xxx ready"
- [ ] 7. Backend logs show Flower API calls
- [ ] 8. Frontend console shows worker stats data
- [ ] 9. Flower web UI shows workers online
- [ ] 10. Test document upload processes successfully

---

## Quick Fix Commands

### Redeploy All Monitoring Services (Railway CLI)
```bash
# If you have Railway CLI installed
railway up -s flower-service
railway up -s worker-service
railway up -s beat-service
railway up -s backend
```

### Or use Railway Dashboard:
1. Click each service
2. Click **"Deploy"**
3. Wait for "Active" status

---

## Getting Help

**If issue persists after following this guide**:

1. **Collect logs** from Railway:
   - Worker service logs (last 100 lines)
   - Flower service logs (last 100 lines)
   - Backend logs (search for "monitoring")

2. **Check browser console**:
   - Open DevTools (F12)
   - Copy console output

3. **Check Flower web UI**:
   - Take screenshot of Workers page
   - Take screenshot of Tasks page

4. **Verify environment variables**:
   - Export from each service (without sensitive values)

With this info, you can debug or ask for help with specific error messages!
