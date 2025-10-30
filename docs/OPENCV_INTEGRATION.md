# OpenCV Integration Verification Guide

## Overview

This guide helps verify that OpenCV is properly installed and the quality gate is working correctly after deployment.

## What Was Changed

### 1. Added OpenCV Dependency
**File**: `backend/requirements.txt`
```
opencv-python-headless==4.10.0.84  # Image quality analysis (headless for Railway deployment)
```

### 2. Quality Gate Already Integrated
The quality gate code was already implemented in:
- `backend/app/routers/upload.py:121-185` - Quality check at upload
- `backend/app/services/file_quality_detector.py` - OpenCV-based quality analysis
- Database fields: `min_ocr_confidence_threshold` and `enable_markdown_tables`

## Deployment Steps

### 1. Push Changes to Railway
```bash
git add backend/requirements.txt
git commit -m "Add OpenCV for image quality detection"
git push origin main  # or your deployment branch
```

### 2. Monitor Railway Deployment
1. Go to Railway dashboard
2. Watch deployment logs
3. Wait for build to complete (~2-5 minutes)
4. Check for successful startup

## Verification Checklist

### ✅ Step 1: Check Deployment Logs

**Look for OpenCV initialization** in Railway logs:

**BEFORE (without OpenCV)**:
```
INFO | app.services.file_quality_detector | OpenCV available: False
INFO | app.routers.upload | Quality: 0.50
```

**AFTER (with OpenCV)** - Should see:
```
INFO | app.services.file_quality_detector | OpenCV available: True
INFO | app.routers.upload | Quality: [actual calculated score]
```

### ✅ Step 2: Test with Blurry Image

**Upload a blurry document** and check response:

**Expected Response** (422 Unprocessable Entity):
```json
{
  "error": "poor_document_quality",
  "message": "Document quality is too low for reliable processing",
  "details": {
    "confidence_score": 0.25,
    "min_threshold": 0.5,
    "issues": ["poor_image_quality", "low_blur_detection"],
    "suggestions": [
      "Ensure good lighting without shadows or glare",
      "Hold camera steady to avoid blur",
      "Use a higher resolution camera if available"
    ]
  }
}
```

**Backend Logs Should Show**:
```
INFO | app.routers.upload | 📊 Quality check: confidence=0.25, threshold=0.50
WARNING | app.routers.upload | ❌ Quality gate rejected: [filename] (confidence=0.25 < threshold=0.50)
```

### ✅ Step 3: Test with Clear Image

**Upload a clear, high-quality document**:

**Expected Response** (200 OK):
```json
{
  "processing_id": "uuid-here",
  "filename": "document.jpg",
  "status": "PENDING",
  "message": "Datei erfolgreich hochgeladen und in Warteschlange eingereiht"
}
```

**Backend Logs Should Show**:
```
INFO | app.routers.upload | 📊 Quality check: confidence=0.75, threshold=0.50
INFO | app.routers.upload | ✅ Quality gate passed for [filename]
```

## Quality Detection Metrics

### Image Quality Calculation
The quality score is calculated as:
```python
quality_score = (blur_score * 0.6) + (contrast_score * 0.4)
```

### Individual Metrics
- **Blur Score** (0.0-1.0): Laplacian variance-based blur detection
- **Contrast Score** (0.0-1.0): Histogram analysis for dynamic range
- **Final Quality** (0.0-1.0): Weighted combination

### Quality Thresholds
- **< 0.30**: Very poor (severe blur/low contrast)
- **0.30-0.50**: Poor (below threshold by default)
- **0.50-0.70**: Acceptable (passes quality gate)
- **0.70-0.85**: Good quality
- **> 0.85**: Excellent quality

## Adjusting the Quality Threshold

Current default: **0.50** (50%)

### Via Database
```sql
-- Connect to Railway PostgreSQL
psql $DATABASE_URL

-- View current threshold
SELECT id, min_ocr_confidence_threshold, enable_markdown_tables
FROM ocr_configuration;

-- Adjust threshold (example: raise to 0.60)
UPDATE ocr_configuration
SET min_ocr_confidence_threshold = 0.60
WHERE id = 1;
```

### Recommended Thresholds
- **0.40**: Lenient (accept more images, higher false positives)
- **0.50**: Balanced (default, good starting point)
- **0.60**: Strict (fewer false positives, may reject borderline images)
- **0.70**: Very strict (only accept high-quality images)

## Troubleshooting

### Problem: OpenCV Still Shows False

**Possible Causes**:
1. Railway build cache (old dependencies)
2. Deployment not completed
3. Wrong service/instance

**Solution**:
```bash
# Force Railway rebuild
railway up --force

# Or clear Railway build cache via dashboard:
# Settings → Service → Redeploy
```

### Problem: All Images Get Same Score

**Symptoms**: All images show 0.50 confidence

**Cause**: OpenCV not loaded (fallback behavior)

**Solution**: Verify OpenCV import in logs:
```
INFO | app.services.file_quality_detector | OpenCV available: True
```

### Problem: Too Many Rejections

**Symptoms**: Good images are being rejected

**Solution**: Lower threshold:
```sql
UPDATE ocr_configuration
SET min_ocr_confidence_threshold = 0.40
WHERE id = 1;
```

### Problem: Quality Gate Not Rejecting Poor Images

**Symptoms**: Blurry images pass quality gate

**Solutions**:
1. Verify OpenCV is installed (check logs)
2. Check threshold isn't too low (should be ≥ 0.50)
3. Test with very blurry image (known bad quality)

## Expected Performance Impact

### Memory Usage
- **OpenCV Footprint**: ~50MB additional memory
- **Railway T-shirt size**: Should work fine with current plan

### Deployment Time
- **Build Time**: +30-60 seconds (one-time OpenCV installation)
- **Runtime**: No performance impact (OpenCV only used during upload)

### Processing Time
- **Quality Analysis**: ~100-500ms per image
- **User Experience**: Negligible (happens during upload)

## Success Criteria

✅ Deployment logs show `OpenCV available: True`
✅ Blurry images rejected with quality scores < 0.50
✅ Clear images accepted with quality scores > 0.50
✅ Users receive actionable feedback (issues + suggestions)
✅ Quality gate stops processing before OCR step
✅ No impact on existing clear image uploads

## Next Steps After Verification

1. **Monitor Rejection Rates**: Track how many images are rejected
2. **Collect User Feedback**: Are suggestions helpful?
3. **Adjust Threshold**: Fine-tune based on real usage
4. **Test Edge Cases**: Medium-quality images, specific document types
5. **Performance Monitoring**: Check Railway resource usage

## Related Documentation

- [File Quality Detector](../backend/app/services/file_quality_detector.py) - Quality detection implementation
- [Upload Router](../backend/app/routers/upload.py) - Quality gate integration
- [Database Schema](DATABASE.md) - OCR configuration fields
- [Architecture](ARCHITECTURE.md) - System overview

## Support

If quality detection isn't working as expected:
1. Check Railway deployment logs for OpenCV availability
2. Test with known blurry/clear images
3. Verify database threshold setting
4. Monitor backend logs during uploads
