# Concurrency vs Replicas - Complete Guide

Understanding the difference between `--concurrency` and Railway replicas.

---

## Two Ways to Scale Workers

### 1. **Concurrency** (Within Container)
`--concurrency=4` in Dockerfile.worker

### 2. **Replicas** (Multiple Containers)
Railway → worker-service → Settings → Replicas

---

## Concurrency Deep Dive

### What `--concurrency=4` Actually Does

**At Worker Startup**:
```python
# Celery starts with prefork pool (default)
celery worker --concurrency=4 --pool=prefork

# Immediately creates 4 child processes:
Main Process (PID 1)
  ├─ Fork → Worker Process 1 (PID 10)
  ├─ Fork → Worker Process 2 (PID 11)
  ├─ Fork → Worker Process 3 (PID 12)
  └─ Fork → Worker Process 4 (PID 13)

# All 4 processes run THIS CODE in parallel:
while True:
    task = redis.blpop('high_priority')  # Blocking wait
    if task:
        process_medical_document(task)
```

**Key Points**:
- ✅ All 4 processes created at startup (not on demand!)
- ✅ All 4 run continuously until worker shutdown
- ✅ Each process can handle 1 task at a time
- ✅ Processes compete for tasks from Redis queue
- ✅ Maximum **4 simultaneous tasks** per container

### Memory Model

Each process loads **full application into memory**:
```
Process 1: Python runtime + Libraries + AI models = ~1.1GB
Process 2: Python runtime + Libraries + AI models = ~1.1GB
Process 3: Python runtime + Libraries + AI models = ~1.1GB
Process 4: Python runtime + Libraries + AI models = ~1.1GB

Total: ~4.4GB per container
```

**AI models loaded per process**:
- spaCy model: ~500MB
- PaddleOCR model: ~200MB
- Python + libraries: ~400MB

### When Processes Are Used

```
Concurrency = 4

Upload 1 doc:  [█░░░] 1/4 processes busy (25% utilization)
Upload 2 docs: [██░░] 2/4 processes busy (50% utilization)
Upload 3 docs: [███░] 3/4 processes busy (75% utilization)
Upload 4 docs: [████] 4/4 processes busy (100% utilization)
Upload 5 docs: [████] + Queue:1 (100% utilization, queue building)
```

### Choosing Concurrency

**Formula**:
```
Optimal Concurrency = CPU Cores × (1 + Wait Ratio)

Wait Ratio = (I/O Wait Time) / (CPU Time)
```

**Your Medical Documents**:
- CPU-heavy: AI translation, OCR processing
- Wait Ratio: ~0.5-1.0 (some I/O for API calls, file operations)
- Railway CPU: ~2-4 cores per container

**Recommendations**:

```yaml
Conservative (current): --concurrency=4
  - Safe for 2-4 core containers
  - Good memory fit (~4.4GB)
  - Recommended for Railway Starter plan

Aggressive: --concurrency=6
  - For 4-8 core containers
  - ~6.6GB memory needed
  - Railway Pro plan recommended

Memory-Limited: --concurrency=2
  - For memory-constrained plans
  - ~2.2GB total
  - Lower throughput but safer
```

---

## Replicas Deep Dive

### What Railway Replicas Do

**Setting Replicas = 3**:
```
Railway creates 3 SEPARATE containers:

Container 1 (worker-replica-1)
  Main Process
    ├─ Worker Process 1
    ├─ Worker Process 2
    ├─ Worker Process 3
    └─ Worker Process 4

Container 2 (worker-replica-2)
  Main Process
    ├─ Worker Process 1
    ├─ Worker Process 2
    ├─ Worker Process 3
    └─ Worker Process 4

Container 3 (worker-replica-3)
  Main Process
    ├─ Worker Process 1
    ├─ Worker Process 2
    ├─ Worker Process 3
    └─ Worker Process 4

Total: 3 containers × 4 processes = 12 worker processes
```

**Key Points**:
- ✅ Complete isolation (separate containers)
- ✅ Separate memory (3 × 4.4GB = ~13GB total)
- ✅ Can run on different physical machines
- ✅ Automatic load balancing across replicas
- ✅ Fault tolerance (if 1 container crashes, others continue)

### When Replicas Are Used

**All replicas run simultaneously, always!**

```
3 Replicas, Concurrency 4 = 12 simultaneous tasks

Upload 1 doc:  [█░░░][░░░░][░░░░] 1/12 processes busy (8%)
Upload 4 docs: [████][░░░░][░░░░] 4/12 processes busy (33%)
Upload 12 docs:[████][████][████] 12/12 processes busy (100%)
Upload 20 docs:[████][████][████] + Queue:8 (100% + backlog)
```

### Choosing Replicas

**Traffic-based recommendations**:

```yaml
Low Traffic (1-10 docs/hour):
  Replicas: 1
  Concurrency: 2-4
  Total: 2-4 processes
  Cost: $X/month

Medium Traffic (10-50 docs/hour):
  Replicas: 2-3
  Concurrency: 4
  Total: 8-12 processes
  Cost: $2-3X/month

High Traffic (50-200 docs/hour):
  Replicas: 5-10
  Concurrency: 4
  Total: 20-40 processes
  Cost: $5-10X/month

Burst Traffic (variable):
  Replicas: 2-10 (auto-scale)
  Concurrency: 4
  Auto-scaling based on queue length
```

---

## Comparison Matrix

| Feature | Concurrency | Replicas |
|---------|-------------|----------|
| **Scaling Type** | Vertical (more processes) | Horizontal (more containers) |
| **Startup Cost** | All processes start immediately | All replicas start immediately |
| **Memory per Unit** | ~1.1GB per process | ~4.4GB per container (with concurrency=4) |
| **Fault Tolerance** | No (container crash = all processes lost) | Yes (replica crash = others continue) |
| **Maximum Tasks** | = concurrency value | = replicas × concurrency |
| **Load Balancing** | OS scheduler (same container) | Redis queue (across containers) |
| **Cost** | Single container cost | Multiply by replica count |
| **Ideal For** | Single machine optimization | Distributed workload, high availability |

---

## Real-World Scenarios

### Scenario 1: Startup (No Load)
```yaml
Config: 1 replica, concurrency=4

System State:
  Containers: 1 (active)
  Processes: 4 (idle, waiting)
  Memory: 4.4GB
  CPU: ~5% (idle processes)
  Active Tasks: 0

Cost: 1× base cost
```

### Scenario 2: Single User Upload
```yaml
Config: 1 replica, concurrency=4

System State:
  Containers: 1 (active)
  Processes: 4 (1 busy, 3 idle)
  Memory: 4.4GB
  CPU: ~25% (1 process working)
  Active Tasks: 1
  Queue: 0

Cost: 1× base cost
Utilization: 25%
```

### Scenario 3: 4 Simultaneous Uploads
```yaml
Config: 1 replica, concurrency=4

System State:
  Containers: 1 (active)
  Processes: 4 (all busy)
  Memory: 4.4GB
  CPU: ~100% (all processes working)
  Active Tasks: 4
  Queue: 0

Cost: 1× base cost
Utilization: 100% ✅ Perfect!
```

### Scenario 4: 10 Simultaneous Uploads (Overload)
```yaml
Config: 1 replica, concurrency=4

System State:
  Containers: 1 (active)
  Processes: 4 (all busy)
  Memory: 4.4GB
  CPU: ~100%
  Active Tasks: 4
  Queue: 6 (waiting!)

Cost: 1× base cost
Utilization: 100%
Problem: 6 docs waiting ~20min each
```

### Scenario 5: 10 Uploads with Scaling
```yaml
Config: 3 replicas, concurrency=4

System State:
  Containers: 3 (all active)
  Processes: 12 (10 busy, 2 idle)
  Memory: 13.2GB (3 × 4.4GB)
  CPU: ~83% average across containers
  Active Tasks: 10
  Queue: 0 ✅

Cost: 3× base cost
Utilization: 83% ✅ Good!
Result: All 10 docs processing simultaneously
```

---

## Current Recommendation

### Your Setup (as of now)
```yaml
worker-service:
  replicas: 1 (assumed - check Railway)
  concurrency: 4
  total_processes: 4
  max_simultaneous_tasks: 4
```

### Recommended Changes

**For Low-Medium Traffic** (current usage):
```yaml
# Keep as is
worker-service:
  replicas: 1
  concurrency: 4

Why:
  - Handles 4 simultaneous documents
  - Cost-effective
  - Good for testing and normal operation
```

**For Growing Traffic** (10+ docs/hour):
```yaml
# Scale horizontally
worker-service:
  replicas: 2-3
  concurrency: 4
  total_processes: 8-12

Why:
  - Fault tolerance
  - Better distribution
  - Handles burst traffic
```

**For Production/High Traffic**:
```yaml
# Optimal setup
worker-service:
  replicas: 3-5
  concurrency: 4
  total_processes: 12-20

Why:
  - High availability
  - Load distribution
  - Queue rarely builds up
  - Can handle 12-20 simultaneous documents
```

---

## How to Monitor Utilization

### In Flower Dashboard

**Workers Tab**:
- Shows all replicas and their processes
- Example with 3 replicas, concurrency 4:
  ```
  celery@worker-1-abc (4 processes)
  celery@worker-2-def (4 processes)
  celery@worker-3-ghi (4 processes)
  ```

**Tasks Tab**:
- Filter by state: STARTED (active)
- Count active tasks vs total processes
- Utilization = Active Tasks / Total Processes

### Utilization Calculation

```python
Total Processes = Replicas × Concurrency
Utilization = Active Tasks / Total Processes

Example:
  Replicas: 3
  Concurrency: 4
  Total Processes: 12
  Active Tasks: 8
  Utilization: 8/12 = 66.7%
```

**Ideal Utilization**:
- **<50%**: Over-provisioned, consider reducing replicas
- **50-80%**: Good utilization, room for burst traffic
- **80-95%**: High utilization, consider adding replicas
- **>95%**: At capacity, queues building up, SCALE NOW!

---

## Auto-Scaling Strategy

### Manual Scaling (Your Current Setup)
- Monitor queue length in Flower
- If queue consistently >10: Add 1 replica
- If utilization consistently <30%: Remove 1 replica

### Future: Railway Auto-Scaling
```yaml
# When Railway supports auto-scaling
worker-service:
  min_replicas: 2
  max_replicas: 10
  scale_up_when: queue_length > 5
  scale_down_when: queue_length < 2 AND utilization < 30%
```

---

## Summary

**Concurrency** = How many tasks **one container** can handle
**Replicas** = How many **containers** you run

**Both are always-on** (not on-demand):
- Concurrency: Processes pre-forked at startup
- Replicas: Containers always running

**Scaling Decision Tree**:
```
Need more capacity?
  ↓
  More than 1 container worth? → Add Replicas
  ↓                      ↓
  No                    Yes
  ↓                      ↓
  Increase Concurrency  Keep Concurrency=4
  (if memory allows)    Add more replicas
```

**Your Current Config** (`concurrency=4`):
- ✅ 4 processes always running
- ✅ Can handle 4 simultaneous tasks
- ✅ Good for 80% of use cases
- ✅ Add replicas for more capacity, not concurrency
