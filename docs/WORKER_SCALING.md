# Worker Scaling Guide

Complete guide for scaling Celery workers on Railway.

## Architecture Overview

```
┌─────────────────┐
│   Redis Broker  │ ← Message queue for all services
└────────┬────────┘
         │
    ┌────┴──────────────────────┐
    │                           │
┌───▼──────────┐    ┌──────────▼──────┐
│ Beat Service │    │ Worker Service  │
│  (1 replica) │    │ (1-10 replicas) │
│              │    │                 │
│ Schedules:   │    │ Processes:      │
│ - Cleanup    │    │ - Documents     │
│ - Maintenance│    │ - All tasks     │
└──────────────┘    └─────────────────┘
                         │ × Replicas
                    ┌────┴────┬────────┐
                    │         │        │
               Worker-1  Worker-2  Worker-N
             (2 processes each)
```

## Service Breakdown

### 1. Beat Service (Scheduler)
- **Purpose**: Schedules periodic tasks (cleanup, maintenance)
- **Replicas**: **ALWAYS 1** (never scale)
- **Why**: Multiple schedulers = duplicate tasks
- **Configuration**: `dockerfiles/Dockerfile.beat`

### 2. Worker Service (Task Executor)
- **Purpose**: Processes document translation tasks
- **Replicas**: **1-10** (scale based on load)
- **Concurrency**: 2 processes per replica (configurable)
- **Configuration**: `dockerfiles/Dockerfile.worker`

### 3. Flower Service (Monitoring)
- **Purpose**: Real-time worker monitoring dashboard
- **Replicas**: 1 (no need to scale)
- **Configuration**: `dockerfiles/Dockerfile.flower`

---

## Railway Setup Instructions

### Step 1: Create Beat Service (New!)

**In Railway Dashboard:**

1. Click **"+ New"** → **"Empty Service"**
2. Name it: `beat-service`
3. Go to **Settings** → **Build**:
   - **Dockerfile Path**: `dockerfiles/Dockerfile.beat`
   - **Root Directory**: (leave empty)
4. Go to **Settings** → **Variables**:
   ```bash
   REDIS_URL=${{REDIS.REDIS_URL}}
   ```
5. **DO NOT** set replicas (defaults to 1 - this is correct!)
6. Click **"Deploy"**

**Verify Logs**:
```
[INFO/Beat] Scheduler: Sending due task cleanup_old_files
[INFO/Beat] Scheduler: Sending due task cleanup_orphaned_jobs
```

### Step 2: Update Worker Service

**In Railway Dashboard:**

1. Go to `worker-service` → **Settings** → **Build**
2. Verify **Dockerfile Path**: `dockerfiles/Dockerfile.worker`
3. Go to **Settings** → **General** → **Replicas**
4. Set replicas based on your needs:
   - **Low traffic**: 1-2 replicas
   - **Medium traffic**: 3-5 replicas
   - **High traffic**: 5-10 replicas
5. Click **"Deploy"**

**Verify Logs** (should NOT show Beat scheduler):
```
[INFO/MainProcess] Connected to redis://...
[INFO/MainProcess] celery@worker-1 ready.
[config:high_priority,default,low_priority,maintenance]
```

### Step 3: Monitor Worker Count

**In Flower Dashboard**:
1. Open Settings Modal → Worker Monitoring
2. Click **"Open Flower Dashboard"**
3. Check **"Workers"** tab
4. You should see:
   - `celery@worker-1` (replica 1)
   - `celery@worker-2` (replica 2)
   - ... (one per replica)

---

## Scaling Strategies

### Vertical Scaling (Concurrency)

**What**: Increase processes **within** each worker container

**How**: Modify `Dockerfile.worker` line 62:
```bash
--concurrency=4  # Increase from 2 to 4
```

**When to use**:
- ✅ CPU-bound tasks (heavy computation)
- ✅ I/O-bound tasks can handle more concurrency
- ✅ Single replica but want more parallel processing

**Limits**:
- Railway containers have limited CPU cores (2-4 typically)
- Too high = context switching overhead
- Recommended: 2-4 processes per container

**Example**:
- 1 replica × 4 concurrency = **4 worker processes**

### Horizontal Scaling (Replicas) ⭐ Recommended

**What**: Multiple worker containers running in parallel

**How**: Railway → `worker-service` → Settings → Replicas

**When to use**:
- ✅ High task volume (many documents)
- ✅ Better fault tolerance
- ✅ Easier to scale up/down
- ✅ Better resource isolation

**Limits**:
- Railway plan limits (check your tier)
- Each replica = separate container = more cost
- Database connection pool limits

**Example**:
- 5 replicas × 2 concurrency = **10 worker processes**

### Hybrid Scaling (Both) 🚀 Maximum Performance

**What**: Combine replicas + concurrency

**Configuration**:
```bash
# Dockerfile.worker
--concurrency=4

# Railway Settings
Replicas: 3
```

**Result**:
- 3 replicas × 4 concurrency = **12 worker processes**

**When to use**:
- ✅ Very high traffic
- ✅ Complex documents (long processing times)
- ✅ Need maximum throughput

---

## Performance Tuning

### Concurrency Calculation

**Formula**:
```
Optimal Concurrency = CPU Cores × (1 + Wait Ratio)

Where:
- CPU Cores: Container CPU limit (usually 2-4)
- Wait Ratio: I/O wait time / CPU time
  - CPU-bound (AI models): 0.0-0.5
  - I/O-bound (network/disk): 1.0-3.0
```

**Our Tasks (Medical Documents)**:
- AI translation: CPU-bound (wait ratio ≈ 0.5)
- OCR: Mix of CPU + I/O (wait ratio ≈ 1.0)

**Recommendation**:
```bash
# Conservative (safe for all document types)
--concurrency=2

# Aggressive (for high I/O, many network calls)
--concurrency=4
```

### Memory Considerations

Each worker process uses memory:
- **Base Python + Libraries**: ~200MB
- **Celery overhead**: ~50MB
- **AI Models (spaCy, PaddleOCR)**: ~500MB (loaded once per container)
- **Per-task memory**: ~100-300MB (document size dependent)

**Example Memory Usage**:
```
1 replica, concurrency=2:
  Base: 200MB + 500MB (models) = 700MB
  Per task: 2 × 200MB = 400MB
  Total: ~1.1GB

3 replicas, concurrency=2:
  Total: 3 × 1.1GB = ~3.3GB
```

**Railway Memory Limits**:
- Check your plan's memory limits
- Monitor via Flower → Worker stats → Memory usage
- Set alerts for >80% memory usage

---

## Monitoring & Alerts

### Key Metrics to Watch

**In Flower Dashboard**:
1. **Active Workers**: Should match replica count × concurrency
2. **Task Queue Length**:
   - `high_priority`: Should be near 0 (processed immediately)
   - `maintenance`: Can have backlog (not urgent)
3. **Task Success Rate**: Should be >95%
4. **Average Task Time**: Baseline and compare trends

### Setting Up Alerts (Future Enhancement)

**Recommended Alerts**:
```yaml
# Example alerting rules (implement with external service)
alerts:
  - name: "High Queue Backlog"
    condition: high_priority queue > 10 tasks
    action: Scale up replicas

  - name: "Worker Crash"
    condition: active_workers < expected_count
    action: Alert ops team

  - name: "High Failure Rate"
    condition: failure_rate > 10%
    action: Check logs, alert team

  - name: "Memory Pressure"
    condition: memory_usage > 80%
    action: Reduce concurrency or scale up
```

---

## Common Scenarios

### Scenario 1: Normal Load (1-10 docs/hour)
```yaml
beat-service:
  replicas: 1

worker-service:
  replicas: 1
  concurrency: 2

Total: 2 worker processes
Cost: Minimal
```

### Scenario 2: Medium Load (10-50 docs/hour)
```yaml
beat-service:
  replicas: 1

worker-service:
  replicas: 3
  concurrency: 2

Total: 6 worker processes
Cost: 3× worker service
```

### Scenario 3: High Load (50-200 docs/hour)
```yaml
beat-service:
  replicas: 1

worker-service:
  replicas: 5
  concurrency: 3

Total: 15 worker processes
Cost: 5× worker service
```

### Scenario 4: Burst Load (variable, spiky traffic)
```yaml
beat-service:
  replicas: 1

worker-service:
  replicas: 2-10 (auto-scale)
  concurrency: 2

Use Railway's auto-scaling if available
```

---

## Troubleshooting

### Workers Not Showing Up in Flower

**Symptoms**: Flower shows 0 workers or fewer than expected

**Checks**:
1. Verify worker replicas in Railway settings
2. Check worker logs for startup errors
3. Verify `REDIS_URL` matches across all services
4. Check if workers are consuming from correct queues

**Solution**: Redeploy worker service, check logs

### Duplicate Scheduled Tasks

**Symptoms**: Cleanup tasks run multiple times, duplicate logs

**Cause**: Multiple Beat schedulers running

**Checks**:
1. Beat service replicas should be exactly 1
2. Worker service should NOT have `--beat` flag
3. Check logs: only beat-service should show "Scheduler: Sending due task"

**Solution**: Remove `--beat` from worker, ensure beat-service replicas = 1

### High Memory Usage

**Symptoms**: Workers crashing, OOM (out of memory) errors

**Checks**:
1. Check Flower → Worker stats → Memory per worker
2. Review concurrency setting (might be too high)
3. Check for memory leaks (should be prevented by `max_tasks_per_child=50`)

**Solution**:
```bash
# Option 1: Reduce concurrency
--concurrency=1

# Option 2: Reduce max tasks per child (recycle more often)
--max-tasks-per-child=25

# Option 3: Upgrade Railway plan for more memory
```

### Task Backlog Growing

**Symptoms**: high_priority queue length increasing, slow processing

**Checks**:
1. Check active worker count vs. expected
2. Review average task processing time (might have increased)
3. Check for failed tasks (shown in Flower)
4. Verify worker logs for errors

**Solution**:
```bash
# Short-term: Scale up replicas
Replicas: 3 → 5

# Long-term: Optimize task processing
- Reduce timeout limits if too high
- Optimize AI model calls
- Add more aggressive caching
```

---

## Cost Optimization

### Railway Pricing Considerations

**Each service consumes resources**:
- Beat service: 1 replica (always running) - Small cost
- Worker service: N replicas - Scales with load
- Flower service: 1 replica (always running) - Small cost

**Cost Formula**:
```
Total Cost ≈ (1 + N + 1) × base_service_cost
Where N = worker replicas
```

**Optimization Tips**:
1. **Start small**: 1-2 worker replicas, scale up as needed
2. **Monitor usage**: Use Flower to track actual utilization
3. **Auto-scale**: Use Railway's auto-scaling if available (reduces idle cost)
4. **Off-peak scaling**: Reduce replicas during low-traffic periods
5. **Concurrency first**: Max out concurrency before adding replicas

---

## Migration Checklist

### Current Setup (Single Worker with Beat)
```yaml
worker-service:
  dockerfile: Dockerfile.worker
  cmd: celery worker --beat  # ❌ Contains scheduler
  replicas: 1
```

### New Setup (Separated Beat + Scalable Workers)
```yaml
beat-service:  # ✅ New service
  dockerfile: Dockerfile.beat
  cmd: celery beat
  replicas: 1 (never change)

worker-service:  # ✅ Updated
  dockerfile: Dockerfile.worker
  cmd: celery worker  # ✅ No --beat flag
  replicas: 1-10 (scalable)
```

### Migration Steps

- [ ] 1. Create `beat-service` in Railway
- [ ] 2. Configure environment variables for beat-service
- [ ] 3. Deploy beat-service
- [ ] 4. Verify beat-service logs (should show scheduler)
- [ ] 5. Redeploy `worker-service` (removes --beat flag)
- [ ] 6. Verify worker-service logs (no scheduler messages)
- [ ] 7. Check Flower dashboard (workers should appear)
- [ ] 8. Scale worker-service replicas as needed
- [ ] 9. Test document upload and processing
- [ ] 10. Monitor for 24 hours to ensure no issues

---

## Summary

**Best Practices**:
- ✅ Use Railway Replicas for horizontal scaling
- ✅ Keep Beat service at 1 replica (never scale)
- ✅ Start with low concurrency (2-3), increase if needed
- ✅ Monitor via Flower dashboard
- ✅ Scale based on actual queue length, not guesses

**Recommended Starting Point**:
```yaml
beat-service:
  replicas: 1
  concurrency: N/A

worker-service:
  replicas: 2-3
  concurrency: 2

Total worker processes: 4-6
```

Scale up from there based on traffic patterns! 🚀
