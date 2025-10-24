# Redis Cleanup Analysis & Solutions

## Problem Summary

**Issue**: Redis database has many old tasks that aren't being cleaned up after days, causing memory bloat.

**Status**: Beat service IS deployed (`dockerfiles/Dockerfile.beat`), but cleanup tasks may not be executing properly.

---

## Current System State

### ✅ What's Configured Correctly
1. **Cleanup tasks ARE defined** (`worker/tasks/scheduled_tasks.py`):
   - `cleanup_celery_results` - Removes old Celery task results
   - `cleanup_orphaned_jobs` - Cleans up stuck jobs
   - `cleanup_old_files` - Removes old uploaded files
   - `database_maintenance` - Database cleanup

2. **Cleanup schedule IS configured** (`worker/config.py` lines 116-137):
   - `cleanup_orphaned_jobs`: Every 10 minutes
   - `cleanup_celery_results`: Every 1 hour
   - `cleanup_old_files`: Every 24 hours
   - `database_maintenance`: Every 24 hours

3. **Beat service Dockerfile exists** (`dockerfiles/Dockerfile.beat`)
   - Properly configured with `celery -A worker.worker.celery_app beat`
   - Should be deployed via Railway with RAILWAY_DOCKERFILE_PATH

4. **Worker consumes maintenance queue** (`dockerfiles/Dockerfile.worker:62`)
   - Queue list includes: `high_priority,default,low_priority,maintenance`

### ❓ What Needs Investigation

1. **Is Beat service actually running?**
   - Dockerfile exists, but is it deployed and running on Railway?
   - Check Railway dashboard for beat service status

2. **Are cleanup tasks being scheduled?**
   - Even if beat runs, tasks might not be scheduled correctly
   - Need to check Redis for beat scheduler activity

3. **Are cleanup tasks being executed?**
   - Tasks might be scheduled but failing silently
   - Need to check worker logs for task execution

4. **Backend client missing Redis TTL**
   - `backend/app/services/celery_client.py:106` has `result_expires=3600`
   - This tells Celery to consider results expired, but doesn't set Redis TTL
   - Missing `result_backend_transport_options` with `result_expires_in`

---

## Step 1: Diagnostic (Run First)

Before implementing solutions, diagnose the actual issue:

### Run Diagnostic Script

```bash
cd backend
python3 scripts/debug_beat_service.py
```

This will check:
- ✅ Is beat service running? (checks for `celery-beat-*` keys in Redis)
- ✅ Are tasks queued in maintenance queue?
- ✅ Have cleanup tasks ever executed? (checks for task results)
- ✅ Are workers registered and active?
- ⚠️ Any stuck/unacked tasks?

### Expected Findings

**If beat IS running:**
- Redis will have `celery-beat-*` keys
- Cleanup task results should exist (even if old)
- → Issue is likely with task execution or frequency

**If beat is NOT running:**
- No `celery-beat-*` keys in Redis
- No cleanup task results
- → Issue is with beat service deployment or startup

### Manual Task Test

Test if cleanup tasks work when manually triggered:

```bash
cd backend
python3 scripts/trigger_cleanup_manual.py
```

Choose option `1` to test `cleanup_celery_results`.

**If manual trigger succeeds:**
- Tasks are implemented correctly
- Issue is with beat scheduler

**If manual trigger fails:**
- Tasks have implementation bugs
- Check worker logs for errors

---

## Solution Options Based on Diagnosis

### Option 1: Fix Backend Redis TTL (Do This Regardless)

Update `backend/app/services/celery_client.py` line 100-115:

```python
celery_client.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Berlin",
    enable_utc=True,
    result_expires=3600,  # Task results expire after 1 hour

    # ⭐ ADD THIS - Set actual Redis TTL
    result_backend_transport_options={
        'result_expires': 3600,  # Actual Redis key TTL in seconds
        'retry_on_timeout': True,
        'socket_keepalive': True,
        'health_check_interval': 30,
    },

    # Task routing...
    task_routes={
        # ...existing routes...
    },
)
```

**Note**: This sets TTL on new results only. Old keys without TTL still need cleanup.

---

### Option 2: If Beat Service Not Running on Railway

**Check Railway Dashboard:**
1. Go to Railway dashboard → Project → Services
2. Look for `doctranslator-beat` service
3. Check status (should be "Active")
4. Click on service → View logs

**If Beat Service Doesn't Exist:**

Create new Railway service:
1. Railway dashboard → Add Service → Docker
2. Set `RAILWAY_DOCKERFILE_PATH=dockerfiles/Dockerfile.beat`
3. Environment variables (copy from worker service):
   - `REDIS_URL` (from Redis service)
   - `DATABASE_URL` (from PostgreSQL service)
   - `PYTHONPATH=/app:/app/worker:/app/backend:/app/shared`
   - Any OVH/AI tokens if tasks need them

**If Beat Service Exists But Crashed:**

Check logs for errors:
- Connection issues → Verify `REDIS_URL`
- Import errors → Verify `PYTHONPATH` and dependencies
- Schedule errors → Check `worker/config.py` CELERYBEAT_SCHEDULE

**Common Issues:**
- Beat tries to write schedule file → Needs write permissions
- Beat can't import tasks → Missing `worker/tasks/scheduled_tasks.py`
- Beat can't connect to Redis → Wrong `REDIS_URL`

---

### Option 3: If Beat Running But Tasks Not Executing

**Possible causes:**

1. **Tasks scheduled to wrong queue**
   - Check `worker/config.py:42-45` task routes
   - All cleanup tasks should route to `maintenance` queue

2. **Worker not consuming maintenance queue**
   - Check `dockerfiles/Dockerfile.worker:62`
   - Should include `--queues=....,maintenance`

3. **Tasks failing silently**
   - Check worker logs for errors when tasks run
   - Look for: `Task cleanup_celery_results[...]`

4. **Schedule not loaded**
   - Beat might be running but schedule not applied
   - Check beat logs for "Writing entries..."

**Fix:**
Restart beat service to reload schedule:
```bash
# Railway dashboard
Services → doctranslator-beat → Restart
```

---

### Option 4: Manual Cleanup Script (Immediate Relief)

For immediate cleanup while diagnosing beat service:

```bash
cd backend
python3 scripts/cleanup_redis_manual.py
```

The script will:
- Set 1-hour TTL on keys without expiration
- Delete expired keys
- Delete old task results (>2 hours)
- Show memory freed and statistics

**Note**: This is a one-time cleanup. You still need to fix the root cause (beat service)

---

## Recommended Implementation Plan

### Phase 1: Diagnosis (Do First)
1. ✅ Run diagnostic script: `python3 scripts/debug_beat_service.py`
2. ✅ Identify root cause (beat not running vs. tasks failing vs. other)
3. ✅ Run manual cleanup for immediate relief: `python3 scripts/cleanup_redis_manual.py`

### Phase 2: Fix Root Cause (Based on Diagnosis)

**If beat service not running:**
1. Check Railway dashboard for beat service status
2. Check beat service logs for errors
3. Fix deployment or configuration issues
4. Restart beat service

**If beat running but tasks not executing:**
1. Check worker logs for task execution errors
2. Verify task routing configuration
3. Verify worker consuming maintenance queue
4. Restart worker service if needed

**Regardless of diagnosis:**
1. Fix backend Redis TTL (Option 1)
2. Test manual task trigger: `python3 scripts/trigger_cleanup_manual.py`

### Phase 3: Verification (After Fix)
1. Wait 10 minutes (orphaned jobs cleanup schedule)
2. Run diagnostic script again
3. Verify cleanup tasks are executing
4. Monitor Redis key count decreasing

### Phase 4: Monitoring (Ongoing)
1. Set up alerts for Redis memory usage
2. Add Flower dashboard for Celery monitoring
3. Schedule periodic Redis checks

---

## Testing Cleanup Tasks

### Test Locally

1. Start services with Beat:
   ```bash
   docker-compose up -d beat
   docker-compose logs -f beat
   ```

2. Verify Beat is scheduling:
   ```
   [beat] Scheduler: Sending due task cleanup_celery_results
   [beat] Scheduler: Sending due task cleanup_orphaned_jobs
   ```

3. Check worker processes tasks:
   ```bash
   docker-compose logs -f worker | grep cleanup
   ```

4. Verify Redis cleanup:
   ```bash
   redis-cli -u "redis://..." KEYS "celery-task-meta-*" | wc -l
   ```

### Manual Task Trigger

Trigger cleanup task manually (for testing):

```python
from worker.tasks.scheduled_tasks import cleanup_celery_results

# Run directly (synchronous)
result = cleanup_celery_results()
print(result)

# Or enqueue via Celery
from worker.worker import celery_app
task = celery_app.send_task('cleanup_celery_results')
print(f"Task ID: {task.id}")
```

---

## Monitoring Redis

### Check Current State

```bash
# Connect to Redis
redis-cli -u "redis://default:zXupOXcPiRwhKDNbTByOkGybUQpSHxDN@yamanote.proxy.rlwy.net:26905"

# Count keys
DBSIZE

# Check memory usage
INFO memory

# List task result keys
KEYS celery-task-meta-*

# Check TTL of a key
TTL celery-task-meta-<some-task-id>
```

### Expected State After Fix

- All `celery-task-meta-*` keys have TTL set (not -1)
- Old keys (>2 hours) are deleted
- New keys auto-expire after 1 hour
- Cleanup tasks run on schedule

---

## Conclusion

**Problem**: Celery Beat scheduler not running → Cleanup tasks never execute → Redis fills up

**Solution**: Add Celery Beat service + Fix Redis TTL + Run manual cleanup

**Priority**:
1. **High**: Run manual cleanup (immediate relief)
2. **High**: Add Beat service (permanent fix)
3. **Medium**: Fix Redis TTL (prevent future accumulation)
4. **Low**: Add monitoring (operational visibility)

---

## Additional Resources

- Celery Beat Documentation: https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html
- Redis TTL Commands: https://redis.io/commands/expire/
- Railway Multi-Service Deployment: https://docs.railway.app/deploy/deployments
