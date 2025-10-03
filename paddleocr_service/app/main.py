"""
PaddleOCR Microservice - Fast CPU-based OCR

Provides OCR extraction endpoints using PaddleOCR.
Designed as a standalone microservice for Railway deployment.
"""

import io
import logging
import time
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# PaddleOCR imports
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    PaddleOCR = None

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global OCR instance (initialized at startup)
paddle_ocr = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize PaddleOCR at startup"""
    global paddle_ocr

    logger.info("🚀 PaddleOCR Service starting up...")

    if not PADDLEOCR_AVAILABLE:
        logger.error("❌ PaddleOCR is not installed!")
        yield
        return

    try:
        logger.info("🔧 Initializing PaddleOCR (CPU mode)...")
        start_init = time.time()

        paddle_ocr = PaddleOCR(
            use_angle_cls=True,  # Enable text angle classification
            lang='german',       # German language support (includes Latin characters)
            use_gpu=False,       # CPU mode
            show_log=False       # Reduce console noise
        )

        init_time = time.time() - start_init
        logger.info(f"✅ PaddleOCR initialized successfully in {init_time:.2f}s")
        logger.info(f"   - Models: Detection ✓ | Recognition ✓ | Angle Classification ✓")
        logger.info(f"   - Mode: CPU | Language: DE (German) | GPU: Disabled")
        logger.info("🟢 Service ready to process requests")

    except Exception as e:
        logger.error(f"❌ Failed to initialize PaddleOCR: {e}")
        paddle_ocr = None

    yield

    logger.info("🛑 PaddleOCR Service shutting down...")


app = FastAPI(
    title="PaddleOCR Microservice",
    description="Fast CPU-based OCR extraction using PaddleOCR",
    version="1.0.0",
    lifespan=lifespan
)


# ==================== PYDANTIC MODELS ====================

class OCRResponse(BaseModel):
    """Response model for OCR extraction"""
    text: str
    confidence: float
    processing_time: float
    engine: str = "PaddleOCR"
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    paddleocr_available: bool
    version: str


# ==================== ENDPOINTS ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="PaddleOCR Microservice",
        paddleocr_available=paddle_ocr is not None,
        version="1.0.0"
    )


@app.post("/extract", response_model=OCRResponse)
async def extract_text(
    file: UploadFile = File(..., description="Image file (JPEG, PNG) or PDF")
):
    """
    Extract text from an image using PaddleOCR.

    Args:
        file: Uploaded image file (JPEG, PNG, PDF)

    Returns:
        OCRResponse with extracted text and confidence
    """
    if paddle_ocr is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PaddleOCR is not available. Service not properly initialized."
        )

    start_time = time.time()

    try:
        # Read file content
        file_content = await file.read()

        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type: {file.content_type}. Only images are supported."
            )

        logger.info(f"📄 Processing file: {file.filename} ({len(file_content)} bytes)")

        # Convert bytes to image format PaddleOCR expects
        from PIL import Image
        image = Image.open(io.BytesIO(file_content))

        # Run OCR
        result = paddle_ocr.ocr(image, cls=True)

        # Extract text and confidence
        extracted_text = []
        confidences = []

        if result and result[0]:
            for line in result[0]:
                if line and len(line) >= 2:
                    text = line[1][0]  # Text content
                    conf = line[1][1]  # Confidence score
                    extracted_text.append(text)
                    confidences.append(conf)

        # Combine text
        full_text = "\n".join(extracted_text)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        processing_time = time.time() - start_time

        logger.info(f"✅ OCR completed in {processing_time:.2f}s - {len(full_text)} chars, {avg_confidence:.2%} confidence")

        return OCRResponse(
            text=full_text,
            confidence=avg_confidence,
            processing_time=processing_time,
            engine="PaddleOCR",
            details={
                "lines_detected": len(extracted_text),
                "file_size_bytes": len(file_content),
                "filename": file.filename
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ OCR extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR extraction failed: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "PaddleOCR Microservice",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "extract": "/extract (POST)",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9123,
        log_level="info"
    )
