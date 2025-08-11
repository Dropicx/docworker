# OCR Setup Documentation

## Overview

DocTranslator now includes full OCR (Optical Character Recognition) support for processing scanned documents and images. This allows the application to extract text from:

- 📷 Scanned PDFs (documents that are essentially images)
- 🖼️ Image files (JPG, PNG) containing text
- 📄 Mixed PDFs (combination of text and scanned pages)

## Components

### 1. Tesseract OCR Engine
- **Version**: 4.x or higher
- **Languages**: German (deu) and English (eng)
- **Purpose**: Core OCR processing engine

### 2. Poppler Utils
- **Tool**: pdftoppm
- **Purpose**: Convert PDF pages to images for OCR processing

### 3. Python Libraries
- **pytesseract**: Python wrapper for Tesseract
- **pdf2image**: Convert PDF to images
- **Pillow**: Image processing

## Installation

### Docker/Railway (Already Configured)

The `Dockerfile.railway` already includes all necessary dependencies:

```dockerfile
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-eng \
    poppler-utils
```

### Local Development

For local development, install the system dependencies:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng poppler-utils

# macOS
brew install tesseract tesseract-lang poppler

# Windows
# Download and install from: https://github.com/UB-Mannheim/tesseract/wiki
```

## Testing OCR Setup

Run the test script to verify OCR is properly configured:

```bash
cd backend
python test_ocr.py
```

Expected output:
```
=== OCR Setup Test ===

1. Checking pytesseract installation...
   ✅ pytesseract is installed

2. Checking Tesseract binary...
   ✅ Tesseract version: 4.1.1

3. Checking available languages...
   Available languages: eng, deu, osd
   ✅ Required languages (eng, deu) are available

4. Checking pdf2image installation...
   ✅ pdf2image is installed

5. Checking poppler-utils...
   ✅ poppler-utils is installed

6. Testing OCR functionality...
   ✅ OCR test successful

==============================
✅ All OCR components are properly configured!
==============================
```

## How It Works

### Processing Flow

1. **Document Upload**: User uploads a PDF or image file
2. **Text Extraction Attempt**: 
   - First tries to extract embedded text (fast)
   - If no text found, proceeds to OCR
3. **OCR Processing**:
   - Converts PDF pages to high-resolution images (300 DPI)
   - Preprocesses images (grayscale, resize if needed)
   - Runs Tesseract OCR with German + English
   - Calculates confidence scores
4. **Result**: Returns extracted text with confidence score

### Confidence Scores

- **0.95**: Embedded text found (highest quality)
- **0.85**: Text extracted with PyPDF2
- **0.50-0.90**: OCR result (varies by image quality)
- **< 0.50**: Low confidence, may need manual review

## Performance Considerations

### OCR Processing Time

- **Simple PDF (1-5 pages)**: 5-15 seconds
- **Complex PDF (10-20 pages)**: 30-60 seconds
- **High-res images**: 2-5 seconds per image

### Memory Usage

- OCR requires ~100-200MB RAM per page
- PDF to image conversion uses temporary disk space
- Automatic cleanup after processing

### Optimization Tips

1. **Image Quality**: Higher quality scans produce better OCR results
2. **DPI**: 300 DPI is optimal for OCR
3. **Language**: Specify correct language for better accuracy
4. **Preprocessing**: Clean, well-lit scans work best

## Troubleshooting

### Common Issues

#### 1. "Tesseract not found"
```bash
# Check if installed
which tesseract

# Install if missing
apt-get install tesseract-ocr
```

#### 2. "Language pack missing"
```bash
# List available languages
tesseract --list-langs

# Install German language pack
apt-get install tesseract-ocr-deu
```

#### 3. "PDF to image conversion failed"
```bash
# Check poppler-utils
which pdftoppm

# Install if missing
apt-get install poppler-utils
```

#### 4. Low OCR Accuracy
- Ensure document is scanned at 300+ DPI
- Check for skewed or rotated pages
- Verify text is clear and readable
- Consider preprocessing image (contrast, brightness)

## API Response with OCR

When OCR is used, the API response includes confidence information:

```json
{
  "status": "success",
  "processing_id": "uuid-here",
  "extracted_text": "...",
  "confidence": 0.78,
  "ocr_used": true,
  "pages_processed": 5,
  "processing_time": 12.5
}
```

## Health Check

The `/api/health/detailed` endpoint now includes OCR status:

```json
{
  "ocr_capabilities": {
    "tesseract_available": true,
    "tesseract_version": "4.1.1",
    "languages": ["eng", "deu", "osd"],
    "pdf2image_available": true,
    "status": "fully_functional"
  }
}
```

## Limitations

1. **Handwritten Text**: Limited support, accuracy varies
2. **Complex Layouts**: Tables and multi-column layouts may need adjustment
3. **Image Quality**: Poor quality scans result in lower accuracy
4. **Languages**: Currently optimized for German and English only
5. **Processing Time**: Large documents can take several minutes

## Future Improvements

- [ ] Add more language support (French, Spanish, Italian)
- [ ] Implement image preprocessing (deskew, denoise)
- [ ] Add handwriting recognition
- [ ] Parallel page processing for speed
- [ ] Caching of OCR results
- [ ] Advanced layout analysis