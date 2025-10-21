# Railway Deployment Guide - Optimized PII Filter

> ## ⚠️ DEPRECATED (2025-10-13)
>
> **This deployment guide is DEPRECATED.**
>
> **Current Implementation**: The system now uses `AdvancedPrivacyFilter` without Railway volume
> - No special volume configuration needed
> - Works with or without spaCy (graceful fallback)
> - Better medical term coverage
> - See current implementation in `worker/tasks/document_processing.py:123`
>
> This guide is kept for historical reference only.

## ✅ Implementation Complete

All code changes for the optimized PII filter with Railway volume integration have been implemented.

---

## 📋 Pre-Deployment Checklist

### Files Created/Modified

✅ **Created**:
- `backend/app/services/optimized_privacy_filter.py` - Hybrid PII filter
- `worker/scripts/init_spacy.sh` - spaCy model initialization
- `backend/tests/test_optimized_privacy_filter.py` - Unit tests
- `docs/OPTIMIZED_PII_FILTER.md` - Comprehensive documentation
- `docs/RAILWAY_DEPLOYMENT_GUIDE.md` - This file

✅ **Modified**:
- `dockerfiles/Dockerfile.worker` - Volume support + initialization
- `worker/tasks/document_processing.py` - PII filter integration
- `docs/ARCHITECTURE.md` - Updated with new system

---

## 🚀 Railway Deployment Steps

### Step 1: Add Volume to Worker Service

1. **Log into Railway Dashboard**
   - Navigate to your project
   - Select the **worker service**

2. **Add Volume**
   ```
   Service: doctranslator-worker
   Volume Path: /data
   Recommended Size: 5GB
   ```

3. **Verify Volume**
   - Check that volume is mounted at `/data`
   - Railway will provision persistent storage

### Step 2: Set Environment Variables

Add to **worker service** environment variables:

```bash
# Required - Path to spaCy model on volume
SPACY_MODEL_PATH=/data/spacy_models/de_core_news_sm

# Optional - Skip initialization for testing
# SKIP_SPACY_INIT=false
```

### Step 3: Deploy Worker Service

#### Option A: Automatic Deploy (Recommended)

If you have GitHub integration:

```bash
# Commit changes
git add .
git commit -m "Add optimized PII filter with Railway volume"
git push origin main

# Railway will auto-deploy
```

#### Option B: Manual Deploy via Railway CLI

```bash
# Install Railway CLI if not already installed
npm install -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Deploy worker service
railway up --service doctranslator-worker
```

### Step 4: Monitor First Deployment

**Expected Timeline**:
- Build: ~2-3 minutes
- spaCy model download: ~30 seconds
- Total first deploy: ~3-4 minutes

**Watch Logs**:
```bash
# Via Railway CLI
railway logs --service doctranslator-worker

# Via Dashboard
# Navigate to worker service → Deployments → View Logs
```

**Expected Log Output**:
```
================================================
🚀 spaCy Model Initialization for Railway
================================================
📋 Configuration:
   Model: de_core_news_sm
   Volume path: /data/spacy_models/de_core_news_sm
   Skip init: false

📥 spaCy model not found on volume
   Downloading model (this happens only once)...
🔽 Downloading de_core_news_sm via spaCy...
📦 Found model at: /usr/local/lib/python3.11/site-packages/de_core_news_sm
📋 Copying model to volume: /data/spacy_models/de_core_news_sm
✅ Model successfully installed to Railway volume
✅ Model verified and ready to use

================================================
📊 Model Information:
   Name: de_core_news_sm
   Version: 3.8.0
   Language: de
   Pipeline: ['tok2vec', 'tagger', 'parser', 'ner']
   Size: ~15MB
================================================
✅ spaCy initialization complete
🟢 Worker ready to start
================================================

[... Celery worker starts ...]
```

### Step 5: Verify Deployment

#### Check 1: Volume Persistence

After first deployment, **restart the worker**:

```bash
# Via Railway CLI
railway restart --service doctranslator-worker

# Via Dashboard
# Service → Settings → Restart
```

**Expected Log Output** (should be FAST, ~2s):
```
================================================
🚀 spaCy Model Initialization for Railway
================================================
✅ spaCy model found on Railway volume
   Path: /data/spacy_models/de_core_news_sm
✅ Model integrity verified
⚡ Using cached model (fast startup)
================================================
🟢 Worker ready to start
================================================
```

#### Check 2: PII Filter Functionality

Process a test document and check logs:

**Expected Logs During Processing**:
```
📄 Processing document: abc-123-def
📋 Loaded job: test_document.pdf (12345 bytes)
🔍 Starting OCR for PDF...
✅ OCR completed in 1.23s: 1523 characters, confidence: 94.5%
🔒 Starting local PII removal...
🔍 Starting optimized PII removal...
⚡ Applying fast regex filter...
📝 Using heuristic name detection...
✅ PII removal completed in 67.2ms
   Original: 1523 chars → Cleaned: 1401 chars
🔄 Starting pipeline execution...
✅ Document processed successfully: abc-123-def
```

#### Check 3: Performance Metrics

Monitor PII removal times in logs:

- **Target**: 50-100ms average
- **Fast path (simple docs)**: 10-30ms
- **Slow path (complex docs)**: 100-150ms

If times are consistently >200ms, check troubleshooting section.

---

## 🧪 Testing

### Local Testing (Optional)

Before deploying, you can test locally:

```bash
# 1. Navigate to backend
cd backend

# 2. Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov

# 3. Run tests
pytest tests/test_optimized_privacy_filter.py -v

# Expected output:
# test_initialization PASSED
# test_remove_obvious_pii_patterns PASSED
# test_preserve_medical_terms PASSED
# test_preserve_lab_values PASSED
# ... (all tests passing)
```

### Integration Testing on Railway

After deployment:

1. **Upload a test document** via frontend
2. **Check worker logs** for PII removal metrics
3. **Verify output** - medical terms preserved, PII removed
4. **Monitor performance** - check processing times

---

## 📊 Expected Performance Improvements

### Before vs After

| Metric | Old System | New System | Improvement |
|--------|------------|------------|-------------|
| **Avg PII Removal** | 200ms | 50-100ms | **60-70% faster** |
| **Simple Documents** | 180ms | 10-20ms | **90% faster** |
| **Complex Documents** | 230ms | 100-120ms | **50% faster** |
| **Deployment Time** | 30s every deploy | <2s after first | **93% faster** |
| **Network Traffic** | ~15MB per deploy | 0MB after first | **100% reduction** |

### Resource Usage

| Resource | Usage | Notes |
|----------|-------|-------|
| **RAM** | 200MB | Same as before |
| **Volume Storage** | ~50MB | Persistent spaCy model |
| **CPU** | Low | Optimized execution paths |
| **Network** | 0MB* | *After first deploy |

---

## 🚨 Troubleshooting

### Issue 1: "spaCy model not found on volume"

**Symptom**: Every deployment downloads model

**Solutions**:
1. Verify volume is attached: Railway Dashboard → Worker → Volumes
2. Check volume path is `/data`
3. Verify `SPACY_MODEL_PATH` env var is set correctly
4. Check volume has sufficient space (~100MB free)

**Diagnostic Commands**:
```bash
# SSH into worker container (if available)
railway run --service doctranslator-worker bash

# Check volume mount
ls -la /data
ls -la /data/spacy_models

# Check environment
echo $SPACY_MODEL_PATH
```

### Issue 2: Slow PII Removal (>200ms)

**Symptom**: Logs show PII removal consistently >200ms

**Solutions**:
1. Check if spaCy NER is always being triggered (should be conditional)
2. Verify spaCy is loading from volume (check logs for path)
3. Check Railway worker resources (need ≥512MB RAM)
4. Review heuristic thresholds in `optimized_privacy_filter.py`

**Diagnostic Logs**:
```
# Good (fast path):
⚡ Applying fast regex filter...
📝 Using heuristic name detection...
✅ PII removal completed in 23.5ms

# Good (slow path when needed):
⚡ Applying fast regex filter...
🧠 Applying spaCy NER for name detection...
✅ PII removal completed in 115.3ms

# Bad (always slow):
⚡ Applying fast regex filter...
🧠 Applying spaCy NER for name detection...  # Every time!
✅ PII removal completed in 235.7ms
```

### Issue 3: Medical Terms Removed

**Symptom**: Medical terminology incorrectly filtered

**Solutions**:
1. Check which terms are being removed (enable debug logging)
2. Add missing terms to protection lists
3. Run validation test: `pytest tests/test_optimized_privacy_filter.py::test_preserve_medical_terms -v`
4. Review term protection mechanism

**Debug Mode**:
```python
# Add to worker environment variables
LOG_LEVEL=DEBUG

# This will show detailed PII filter logs
```

### Issue 4: Volume Permissions

**Symptom**: "Permission denied" when writing to `/data`

**Solutions**:
1. Check Dockerfile.worker has correct ownership:
   ```dockerfile
   chown -R celeryuser:celeryuser /data
   ```
2. Verify worker runs as `celeryuser` (non-root)
3. Check Railway volume permissions

---

## 🔄 Rollback Plan

If critical issues occur, rollback by:

### Option 1: Code Rollback (Recommended)

```bash
# 1. Edit worker/tasks/document_processing.py
# Change line ~100 from:
from app.services.optimized_privacy_filter import OptimizedPrivacyFilter

# To:
from app.services.privacy_filter_advanced import AdvancedPrivacyFilter

# 2. Change line ~102 from:
pii_filter = OptimizedPrivacyFilter()

# To:
pii_filter = AdvancedPrivacyFilter()

# 3. Commit and deploy
git add worker/tasks/document_processing.py
git commit -m "Rollback to AdvancedPrivacyFilter"
git push
```

### Option 2: Git Rollback (Full)

```bash
# Rollback to previous commit
git log --oneline  # Find commit hash before changes
git revert <commit-hash>
git push
```

---

## 📈 Monitoring & Metrics

### Key Metrics to Monitor

1. **PII Removal Time**
   - Target: <100ms average
   - Alert if: >200ms consistently

2. **spaCy Model Loading**
   - First deploy: ~30s
   - Subsequent: <2s
   - Alert if: Always downloading

3. **Worker Memory**
   - Expected: ~200-300MB
   - Alert if: >500MB

4. **Volume Usage**
   - Expected: ~50MB
   - Alert if: Growing beyond 100MB

### Setting Up Alerts (Optional)

Railway provides built-in metrics. Configure alerts for:

- **Memory usage** > 80%
- **CPU usage** > 90%
- **Deployment failures**
- **Health check failures**

---

## 🎯 Success Criteria

Your deployment is successful when:

✅ Worker service deploys without errors
✅ spaCy model downloads on first deploy (check logs)
✅ Subsequent restarts load model from volume (<2s)
✅ PII removal times are 50-100ms average (check logs)
✅ Medical terms are preserved (test with sample document)
✅ No PII sent to OVH AI (verify in logs)
✅ End-to-end processing works correctly

---

## 📞 Support & Resources

### Documentation
- [OPTIMIZED_PII_FILTER.md](OPTIMIZED_PII_FILTER.md) - Detailed technical docs
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [Railway Volumes Docs](https://docs.railway.app/reference/volumes)

### Logs & Debugging
```bash
# View worker logs
railway logs --service doctranslator-worker

# View specific timeframe
railway logs --service doctranslator-worker --since 1h

# Follow logs in real-time
railway logs --service doctranslator-worker --follow
```

### Testing Commands
```bash
# Run all tests
cd backend && pytest tests/ -v

# Run only PII filter tests
pytest tests/test_optimized_privacy_filter.py -v

# Run with coverage
pytest tests/test_optimized_privacy_filter.py --cov=app.services.optimized_privacy_filter
```

---

## ✅ Post-Deployment Checklist

After successful deployment:

- [ ] Verify volume is persistent (restart worker, check logs)
- [ ] Test with sample documents (Arztbrief, Laborwerte)
- [ ] Monitor PII removal times for first 10-20 documents
- [ ] Check medical term preservation (manual verification)
- [ ] Verify no PII in OVH AI request logs
- [ ] Set up monitoring alerts (optional)
- [ ] Document any custom configuration
- [ ] Update team on new system

---

## 🎉 Next Steps

After successful deployment:

1. **Monitor Performance**: Watch logs for first day
2. **Collect Metrics**: Track PII removal times
3. **Fine-tune**: Adjust heuristics if needed
4. **Scale**: Increase worker concurrency if needed
5. **Optimize**: Add custom medical terms as discovered

---

**Deployment Guide Version**: 1.0.0
**Last Updated**: 2025-01-04
**Estimated Deployment Time**: 5-10 minutes (first time)

Good luck with your deployment! 🚀
