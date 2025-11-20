# Quality Gate Configuration and Adjustment Guide

## Overview

The Quality Gate is an automated document quality assessment system that evaluates uploads before processing to ensure reliable OCR results. It analyzes images and PDFs using computer vision and content analysis to reject low-quality documents that would produce unreliable results.

## How It Works

### Quality Assessment Process

1. **Document Upload** - User uploads PDF or image file
2. **Quality Analysis** - FileQualityDetector analyzes the document
3. **Confidence Scoring** - System calculates quality confidence score (0.0-1.0)
4. **Threshold Check** - Compares score against configured threshold
5. **Gate Decision**:
   - **Pass** (score ≥ threshold) → Document proceeds to processing
   - **Reject** (score < threshold) → User receives detailed feedback with improvement suggestions

### Quality Metrics

**For Images:**
- **Blur Detection** - Laplacian variance analysis (60% weight)
- **Contrast Analysis** - Histogram-based dynamic range check (40% weight)
- **Final Score** = (blur_score × 0.6) + (contrast_score × 0.4)

**For PDFs:**
- **Text Coverage** - Percentage of pages with embedded text (60% weight)
- **Text Quality** - Font quality, readability assessment (40% weight)
- **Final Score** = (text_coverage × 0.6) + (text_quality × 0.4)

### Quality Score Interpretation

| Score Range | Quality Level | Action |
|-------------|---------------|--------|
| 0.00-0.30 | Very Poor | Rejected - severe quality issues |
| 0.30-0.50 | Poor | Rejected by default |
| 0.50-0.70 | Acceptable | Accepted - reliable processing expected |
| 0.70-0.85 | Good | Accepted - high quality |
| 0.85-1.00 | Excellent | Accepted - optimal quality |

## Configuration

### Default Settings

```python
# Default quality threshold
min_ocr_confidence_threshold = 0.5  # 50%

# Storage location
# Database: ocr_configuration table
# Field: min_ocr_confidence_threshold
```

### Adjusting the Threshold

#### Method 1: Direct Database Update (Production)

```sql
-- Connect to Railway PostgreSQL
psql $DATABASE_URL

-- View current threshold
SELECT id, min_ocr_confidence_threshold, enable_markdown_tables
FROM ocr_configuration
WHERE id = 1;

-- Adjust threshold (example: raise to 60%)
UPDATE ocr_configuration
SET min_ocr_confidence_threshold = 0.60
WHERE id = 1;

-- Verify update
SELECT id, min_ocr_confidence_threshold
FROM ocr_configuration
WHERE id = 1;
```

#### Method 2: Via Admin API (Future)

```bash
# Update threshold via API (when implemented)
curl -X PUT https://api.doctranslator.com/api/settings/ocr-config \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"min_ocr_confidence_threshold": 0.55}'
```

### Recommended Thresholds by Use Case

| Use Case | Threshold | Reasoning |
|----------|-----------|-----------|
| **Development/Testing** | 0.30-0.40 | Accept more documents for testing |
| **General Use** | 0.50 (default) | Balanced - good starting point |
| **Medical Critical** | 0.60-0.70 | Higher accuracy requirements |
| **Production Quality** | 0.55-0.65 | Moderate strictness |
| **Maximum Strictness** | 0.70-0.80 | Only high-quality documents |

**⚠️ Warning**: Setting threshold too high (>0.75) may reject valid documents. Setting too low (<0.35) defeats the purpose of quality gate.

## OpenCV Integration

### Requirement

The quality gate requires OpenCV for accurate quality assessment:

```bash
# In requirements.txt
opencv-python-headless==4.10.0.84  # Headless for Railway deployment
```

### Checking OpenCV Status

**Backend Logs:**
```
INFO | app.services.file_quality_detector | OpenCV available: True
```

**Without OpenCV:**
- Quality scores default to 0.5 (medium quality)
- Blur detection unavailable
- Contrast analysis unavailable
- Table detection unavailable
- System still functional but less accurate

### Verifying OpenCV in Production

```bash
# Check Railway logs for OpenCV initialization
railway logs --filter "OpenCV"

# Should see:
# INFO | app.services.file_quality_detector | OpenCV available: True

# Test with actual upload and check response
curl -X POST https://your-app.railway.app/api/upload \
  -F "file=@test_image.jpg" \
  -F "target_language=EN"
```

## User Experience

### Successful Upload (Quality Pass)

**Request:**
```bash
POST /api/upload
Content-Type: multipart/form-data
file: clear_document.pdf
```

**Response (200 OK):**
```json
{
  "processing_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "clear_document.pdf",
  "status": "PENDING",
  "message": "Datei erfolgreich hochgeladen und in Warteschlange eingereiht"
}
```

**Backend Log:**
```
INFO | app.routers.upload | 📊 Quality check: confidence=0.75, threshold=0.50
INFO | app.routers.upload | ✅ Quality gate passed for clear_document.pdf
```

### Failed Upload (Quality Rejection)

**Request:**
```bash
POST /api/upload
Content-Type: multipart/form-data
file: blurry_scan.jpg
```

**Response (422 Unprocessable Entity):**
```json
{
  "detail": {
    "error": "poor_document_quality",
    "message": "Document quality is too low for reliable processing",
    "details": {
      "confidence_score": 0.32,
      "min_threshold": 0.5,
      "issues": [
        "poor_image_quality",
        "significant_blur_detected",
        "low_contrast"
      ],
      "suggestions": [
        "Ensure good lighting without shadows or glare",
        "Hold camera steady to avoid blur",
        "Clean the document scanner glass if using a scanner",
        "Use a higher resolution camera if available",
        "Ensure document is flat and not wrinkled"
      ]
    }
  }
}
```

**Backend Log:**
```
INFO | app.routers.upload | 📊 Quality check: confidence=0.32, threshold=0.50
WARNING | app.routers.upload | ❌ Quality gate rejected: blurry_scan.jpg (confidence=0.32 < threshold=0.50)
```

## Monitoring and Optimization

### Key Metrics to Track

1. **Rejection Rate** - Percentage of uploads rejected
   ```sql
   -- Track rejections (implement logging table)
   SELECT
     DATE(created_at) as date,
     COUNT(*) as total_uploads,
     SUM(CASE WHEN quality_score < threshold THEN 1 ELSE 0 END) as rejections,
     AVG(quality_score) as avg_quality
   FROM upload_quality_logs
   GROUP BY DATE(created_at)
   ORDER BY date DESC
   LIMIT 30;
   ```

2. **Average Quality Scores** - Trend analysis
3. **False Positives** - Good documents rejected (user feedback)
4. **False Negatives** - Poor documents accepted (OCR failures)

### Optimization Strategy

**Phase 1: Initial Deployment**
- Start with default threshold (0.50)
- Monitor for 2 weeks
- Collect user feedback

**Phase 2: Data Collection**
- Track rejection rates (target: 10-20%)
- Analyze quality score distribution
- Identify edge cases

**Phase 3: Threshold Tuning**
- If rejection rate too high (>30%) → lower threshold by 0.05
- If too many OCR failures → raise threshold by 0.05
- Iterate weekly until optimal

**Phase 4: Continuous Monitoring**
- Set up alerting for rejection rate spikes
- Review user feedback monthly
- Adjust threshold seasonally if needed

### Troubleshooting

#### Problem: All images show same score (0.50)

**Symptom:** Every upload gets confidence=0.50

**Cause:** OpenCV not loaded (fallback behavior)

**Solution:**
```bash
# Check Railway logs
railway logs --filter "OpenCV available"

# Should see: "OpenCV available: True"
# If "False", rebuild service:
railway service redeploy --force
```

#### Problem: Too many rejections

**Symptom:** >30% of uploads rejected, users complaining

**Solutions:**
1. Lower threshold temporarily:
   ```sql
   UPDATE ocr_configuration SET min_ocr_confidence_threshold = 0.40;
   ```
2. Analyze rejected documents - are they actually poor quality?
3. Consider different thresholds for different document types

#### Problem: Poor OCR results despite passing gate

**Symptom:** Documents pass but OCR accuracy is poor

**Solutions:**
1. Raise threshold:
   ```sql
   UPDATE ocr_configuration SET min_ocr_confidence_threshold = 0.60;
   ```
2. Check if specific document types consistently fail
3. Review quality metric weights (blur vs contrast)

#### Problem: Quality gate bypassed or failing silently

**Symptom:** No quality checks in logs

**Check:**
```python
# In upload.py around line 122
# Ensure quality gate code is not commented out
logger.debug(f"🔍 Running quality gate check for {file.filename}")
quality_detector = FileQualityDetector()
```

**Solution:** Verify upload router has quality gate integration

## Testing Quality Gate

### Manual Testing

**Test with Clear Image:**
```bash
# Create test image
python3 << 'EOF'
from PIL import Image, ImageDraw
img = Image.new('RGB', (1000, 1000), 'white')
draw = ImageDraw.Draw(img)
for i in range(20):
    draw.text((50, 50 + i * 40), f'Clear text line {i+1}', fill='black')
img.save('clear_test.png')
EOF

# Upload
curl -X POST http://localhost:9122/api/upload \
  -F "file=@clear_test.png" \
  -F "target_language=EN"

# Should return: 200 OK
```

**Test with Blurry Image:**
```bash
# Create blurry image
python3 << 'EOF'
from PIL import Image, ImageDraw, ImageFilter
img = Image.new('RGB', (800, 800), 'white')
draw = ImageDraw.Draw(img)
for i in range(15):
    draw.text((40, 40 + i * 50), f'Blurry text {i+1}', fill='black')
img = img.filter(ImageFilter.GaussianBlur(radius=20))
img.save('blurry_test.png')
EOF

# Upload
curl -X POST http://localhost:9122/api/upload \
  -F "file=@blurry_test.png" \
  -F "target_language=EN"

# Should return: 422 Unprocessable Entity with quality details
```

### Automated Testing

```bash
# Run quality gate tests
cd backend
pytest tests/test_file_quality_detector.py -v

# Run with coverage
pytest tests/test_file_quality_detector.py --cov=app.services.file_quality_detector --cov-report=term-missing
```

**Expected Results:**
- Clear images: Pass quality gate (score ≥ 0.50)
- Blurry images: Detected and scored appropriately
- PDFs with text: LOCAL_TEXT strategy selected
- PDFs with tables: VISION_LLM or HYBRID strategy

## Performance Impact

### Resource Usage

| Component | Impact |
|-----------|--------|
| **Memory** | +50MB (OpenCV footprint) |
| **CPU** | ~100-500ms per image analysis |
| **Latency** | +0.5-1s total upload time |
| **Storage** | Negligible (no additional storage) |

### Optimization Tips

1. **Caching**: Quality scores could be cached for duplicate uploads
2. **Parallel Processing**: Quality check runs async during upload
3. **Sampling**: For multi-page PDFs, sample pages instead of all
4. **Progressive Enhancement**: Start with basic checks, add OpenCV features gradually

## Advanced Configuration

### Custom Quality Metrics

To adjust quality calculation weights in `file_quality_detector.py`:

```python
# Current: backend/app/services/file_quality_detector.py:1024
def _calculate_quality_score(self, cv_image):
    blur_score = self._detect_blur(cv_image)
    contrast_score = self._calculate_contrast(cv_image)

    # Adjust these weights based on your needs
    quality = (blur_score * 0.6) + (contrast_score * 0.4)
    # Example: Prioritize contrast over blur
    # quality = (blur_score * 0.4) + (contrast_score * 0.6)

    return quality
```

### Per-Document-Type Thresholds (Future Enhancement)

```sql
-- Proposed schema extension
ALTER TABLE ocr_configuration
ADD COLUMN min_threshold_arztbrief FLOAT DEFAULT 0.50,
ADD COLUMN min_threshold_befundbericht FLOAT DEFAULT 0.55,
ADD COLUMN min_threshold_laborwerte FLOAT DEFAULT 0.60;

-- Lab reports need higher quality due to critical values
-- Doctor's letters can tolerate slightly lower quality
```

## Related Documentation

- [OpenCV Integration Guide](OPENCV_INTEGRATION.md) - Deployment and verification
- [File Quality Detector Source](../backend/app/services/file_quality_detector.py) - Implementation details
- [Upload Router Source](../backend/app/routers/upload.py) - Quality gate integration
- [Database Schema](DATABASE.md) - OCR configuration table

## Support and Feedback

**Monitoring Dashboard:**
- Railway logs: `railway logs --filter "Quality"`
- Rejection tracking: Check database for patterns

**Common Questions:**
- **Q: Can users bypass the quality gate?**
  A: No, it's enforced at the API level before processing

- **Q: How often should threshold be adjusted?**
  A: Review monthly, adjust only if rejection rate is problematic

- **Q: What if OpenCV fails to install?**
  A: System falls back to default scores (0.5), still functional but less accurate

- **Q: Can threshold be different for different user groups?**
  A: Not currently, but could be added as enhancement (user_id-based override)

**Need Help?**
- Check Railway logs for quality gate messages
- Review test results: `pytest tests/test_file_quality_detector.py -v`
- Adjust threshold incrementally (±0.05 at a time)
- Monitor impact over 3-7 days before further changes

---

**Last Updated:** 2025-11-19
**Version:** 1.0.0
**Maintainer:** DocTranslator Team
