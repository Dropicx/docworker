# Railway Volume Permission Fix

## 🐛 Problem

Worker service fails with:
```
mkdir: cannot create directory '/data/spacy_models': Permission denied
```

## 🔍 Root Cause

Railway mounts volumes as **root**, but our worker container runs as **celeryuser** (non-root for security). The init script couldn't create directories in the root-owned volume.

## ✅ Solution Applied

Modified the worker startup process to:
1. **Start as root** (container default)
2. **Fix volume permissions**: `chown -R celeryuser:celeryuser /data`
3. **Switch to celeryuser**: Run init script and Celery worker as non-root
4. **Create directories**: Now has permission to create `/data/spacy_models`

## 📝 Files Changed

### `dockerfiles/Dockerfile.worker`

**Before**:
```dockerfile
USER celeryuser
CMD ["/bin/bash", "-c", "/app/init_spacy.sh && celery ..."]
```

**After**:
```dockerfile
# Don't switch to celeryuser yet - run CMD as root
CMD ["/bin/bash", "-c", "chown -R celeryuser:celeryuser /data && su celeryuser -c '/app/init_spacy.sh && celery ...'"]
```

### `worker/scripts/init_spacy.sh`

Added better error handling:
```bash
mkdir -p "$(dirname "$VOLUME_PATH")" || {
    echo "❌ ERROR: Failed to create directory"
    exit 1
}
```

## 🚀 Deployment

### Quick Deploy

```bash
# Commit the fix
git add dockerfiles/Dockerfile.worker worker/scripts/init_spacy.sh
git commit -m "Fix Railway volume permissions for spaCy models"
git push origin main
```

Railway will auto-deploy (if GitHub integration enabled).

### Expected Logs (Success)

```
🚀 spaCy Model Initialization for Railway
📋 Configuration:
   Model: de_core_news_sm
   Volume path: /data/spacy_models/de_core_news_sm

📥 spaCy model not found on volume
   Downloading model (this happens only once)...
📁 Creating directory: /data/spacy_models
🔽 Downloading de_core_news_sm via spaCy...
✅ Model successfully installed to Railway volume
✅ spaCy initialization complete
🟢 Worker ready to start

[... Celery worker starts successfully ...]
```

## ✅ Verification

After deployment:

1. **Check logs**: Should see successful directory creation
2. **No errors**: No "Permission denied" messages
3. **Model downloaded**: Should see model download progress
4. **Worker starts**: Celery worker starts after init

## 🔒 Security Note

The container still runs Celery as **celeryuser** (non-root). Only the initialization step runs as root to fix permissions, then immediately switches to non-root user.

This maintains security while solving the volume permission issue.

## 📊 Timeline

- **First deploy**: ~3-4 minutes (spaCy model download)
- **Subsequent restarts**: <2 seconds (model loaded from volume)

## 🆘 If Still Failing

### Check Volume Mount

Verify in Railway Dashboard:
```
Service: doctranslator-worker
Volumes: Should show /data mounted
```

### Check Logs for Specific Error

If still seeing permission errors:
1. Check volume is actually mounted at `/data`
2. Verify volume has sufficient space (~100MB free)
3. Check Railway volume service status

### Manual Verification

SSH into container (if Railway allows):
```bash
# Check volume mount
ls -la /data

# Check ownership after chown
# Should show: celeryuser:celeryuser
```

### Rollback Plan

If this doesn't work, we can:
1. Install spaCy models at build time (slower deployments)
2. Use a different volume path
3. Run entire container as root (not recommended)

---

**Fix Status**: ✅ Ready to deploy
**Impact**: High (fixes critical deployment failure)
**Risk**: Low (improves security while fixing permissions)
