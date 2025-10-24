# Redis Investigation Summary Report

**Date**: 2025-10-24
**Environment**: Dev (Railway)
**Redis**: `yamanote.proxy.rlwy.net:26905`

---

## Executive Summary

### ✅ Your System is Actually Healthy!

**Redis State**:
- Total keys: 14 (very small)
- Memory usage: 1.88M (tiny)
- All task results have proper TTLs (auto-expire after 1 hour)
- No accumulated old data

**Services Status**:
- ✅ Beat service: **RUNNING** (scheduling tasks for 2+ days)
- ❌ Worker service: **NOT RUNNING** (not processing tasks)
- ✅ Backend: Setting TTLs correctly

---

## What You Were Seeing

### The `celery-task-meta-*` Keys

You saw 7 keys like:
```
celery-task-meta-1bfda497-8bee-42f0-8b08-6a1b53fae16a - TTL: 1693s
celery-task-meta-1f848389-4dc6-4084-a992-52ea712d9e8f - TTL: 2293s
```

**What these are:**
- **Task result storage** - Stores the result of completed Celery tasks
- **TTL set** - Each expires after 1 hour (3600 seconds)
- **Automatically cleaned** - Redis removes them when TTL expires
- **Normal behavior** - This is how Celery works! ✅

**Why you see them:**
- When backend enqueues a task, Celery creates a `celery-task-meta-{task_id}` key
- The key stores the task status and result
- After 1 hour, Redis automatically deletes it (TTL mechanism)
- New tasks create new keys, old ones disappear

**This is NOT a problem** - Your Redis is working correctly!

---

## Beat Service Analysis

### Beat IS Working!

From your beat logs (2025-10-22 to 2025-10-24):

**Scheduled Tasks (Every 10 Minutes)**:
```
[10:51:08] Scheduler: Sending due task cleanup_orphaned_jobs
[11:01:08] Scheduler: Sending due task cleanup_orphaned_jobs
[11:11:08] Scheduler: Sending due task cleanup_orphaned_jobs
... (continued for 2+ days)
```

**Hourly Tasks**:
```
[11:41:08] Scheduler: Sending due task cleanup_celery_results
[12:41:08] Scheduler: Sending due task cleanup_celery_results
... (every hour)
```

**Daily Tasks**:
```
[2025-10-23 10:41:08] Scheduler: Sending due task database_maintenance
[2025-10-23 10:41:08] Scheduler: Sending due task cleanup_old_files
```

✅ **Beat service is 100% healthy and working!**

---

## Worker Service Issue

### Worker is NOT Running

**Evidence**:
- No worker registration keys in Redis
- No workers consuming from queues
- Maintenance queue is empty (tasks not being processed)

**Impact**:
- Beat schedules tasks → Tasks sit in Redis queues
- No worker to execute them → Tasks never run
- Cleanup never happens (but Redis is clean anyway due to TTLs!)

**Why Redis is still clean despite no cleanup:**
- Backend sets `result_expires=3600` on all task results
- Redis automatically deletes expired keys
- TTL mechanism is working perfectly
- You don't actually NEED the cleanup tasks for dev!

---

## What's Happening in Your Dev Environment

### Task Flow (Current State)

```
Beat Service (✅ Running)
    ↓
Schedules: cleanup_celery_results
    ↓
Redis Queue: "maintenance"
    ↓
Worker Service (❌ NOT RUNNING)
    ↓
❌ Task Never Executes
    ↓
Task result expires after 1 hour (TTL)
    ↓
✅ Redis stays clean anyway!
```

### Why Redis Only Has 14 Keys

1. **Low dev usage** - Not many tasks being created
2. **TTLs working** - Old results auto-expire after 1 hour
3. **No accumulation** - Expired keys automatically removed

---

## Recommendations

### For Dev Environment: **No Action Needed!**

**Your dev Redis is healthy:**
- Only 14 keys (excellent)
- All have proper TTLs
- Auto-cleanup via TTL mechanism
- No memory issues

**You DON'T need worker service in dev** unless you're:
- Testing document processing workflows
- Testing scheduled cleanup tasks
- Running background jobs

### For Production Environment: **Check Worker Service**

If you're using production for actual document processing:

1. **Verify worker service exists**
   - Railway dashboard → Services → Look for `doctranslator-worker`

2. **Check worker logs**
   - Should see: "Received task: process_medical_document"
   - Should see: "Received task: cleanup_celery_results"

3. **If worker missing**
   - Deploy worker service using `dockerfiles/Dockerfile.worker`
   - Set environment variables (REDIS_URL, DATABASE_URL, etc.)

---

## Understanding Celery Keys

### Key Types in Your Redis

1. **Task Results** (`celery-task-meta-*`) - 7 keys
   - Purpose: Store task execution results
   - TTL: 1 hour (auto-expire)
   - Normal: Yes, this is how Celery works

2. **Kombu Bindings** (`_kombu.binding.*`) - 7 keys
   - Purpose: Queue definitions and routing
   - TTL: None (permanent)
   - Normal: Yes, these define your queues

### Why You See Different Counts

**Diagnostic said "0 task results"** but you see 7 keys:
- Diagnostic looks for **cleanup task results** specifically
- You have 7 **general task results** (from other operations)
- None of them are from cleanup tasks (because worker never ran them)

---

## Conclusion

### The Bottom Line

**You asked**: "Why don't tasks get cleaned up after days?"

**Answer**:
1. ✅ They DO get cleaned up (via TTL after 1 hour)
2. ✅ Beat is scheduling cleanup tasks correctly
3. ❌ Worker isn't running to execute cleanup tasks
4. ✅ But TTL mechanism works anyway, so Redis stays clean!

**What you thought was a problem** (7 task keys) **is actually normal behavior!**

### Action Items

**Dev Environment**:
- ✅ No action needed
- Redis is healthy
- TTLs are working
- Only 14 keys is excellent

**If you want cleanup tasks to actually run** (optional for dev):
1. Deploy worker service to Railway dev
2. Worker will consume and execute scheduled cleanup tasks
3. But this isn't necessary since TTLs already keep Redis clean

**Production Environment**:
- Check if worker service is deployed and running
- Worker is REQUIRED for document processing
- Cleanup tasks are nice-to-have (TTLs work as backup)

---

## Next Steps

**Option 1: Do Nothing** (Recommended for dev)
- Current state is fine
- Redis is clean
- TTLs working

**Option 2: Deploy Worker** (If you need task processing)
- Create Railway service with `dockerfiles/Dockerfile.worker`
- Same environment variables as beat service
- Will enable actual task execution

**Option 3: Monitor Production** (If using production)
- Check production Redis key count
- Check if worker service exists
- Ensure document processing works
