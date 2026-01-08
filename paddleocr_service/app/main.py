"""
PaddleOCR Microservice v3.0 - Fast OCR (No PPStructureV3)

Simple, fast OCR extraction using PaddleOCR.
Optimized for speed - no heavy document structure analysis.
"""

import io
import logging
import os
import sys
import time
from typing import Dict, Any, Optional

# ==================== ENVIRONMENT SETUP ====================
MODEL_CACHE_DIR = os.environ.get("PADDLEX_HOME", "/home/appuser/.paddlex")
os.environ["PADDLEX_HOME"] = MODEL_CACHE_DIR
os.environ["HF_HOME"] = f"{MODEL_CACHE_DIR}/huggingface"
os.environ["DISABLE_MODEL_SOURCE_CHECK"] = "True"

from fastapi import FastAPI, File, UploadFile, HTTPException, status, Depends
from pydantic import BaseModel
from contextlib import asynccontextmanager

from app.auth import verify_api_key
import uvicorn

# Logging
class FlushingStreamHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[FlushingStreamHandler(sys.stdout)],
    force=True
)
logger = logging.getLogger(__name__)

# ==================== IMPORTS ====================
PADDLEOCR_AVAILABLE = False

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
    logger.info("PaddleOCR available")
except ImportError as e:
    logger.error(f"PaddleOCR not available: {e}")
    PaddleOCR = None

# Global OCR engine
ocr_engine = None


# ==================== MODELS ====================

class OCRResponse(BaseModel):
    text: str
    confidence: float
    processing_time: float
    engine: str = "PaddleOCR"
    lines_detected: int = 0


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    paddleocr_available: bool
    gpu_enabled: bool


# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ocr_engine

    use_gpu = os.environ.get("USE_GPU", "false").lower() == "true"
    device = 'gpu' if use_gpu else 'cpu'

    logger.info("PaddleOCR Microservice v3.0 (Fast Mode) starting up...")
    logger.info(f"   USE_GPU: {use_gpu}")
    logger.info(f"   Device: {device}")

    if use_gpu:
        try:
            import paddle
            paddle.set_device('gpu:0')
            logger.info("GPU device set to gpu:0")
        except Exception as e:
            logger.warning(f"Failed to set GPU: {e}, using CPU")
            device = 'cpu'

    if PADDLEOCR_AVAILABLE:
        try:
            logger.info(f"Initializing PaddleOCR ({device})...")
            start_init = time.time()
            ocr_engine = PaddleOCR(
                lang='german',
                device=device,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,  # Disable to fix CPU kernel bug
            )
            logger.info(f"PaddleOCR initialized in {time.time() - start_init:.2f}s")
        except Exception as e:
            import traceback
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")

    if ocr_engine:
        logger.info(f"Service ready: PaddleOCR ({device})")
    else:
        logger.error("No OCR engine available!")

    yield
    logger.info("Shutting down...")


# ==================== APP ====================

app = FastAPI(
    title="PaddleOCR Microservice",
    description="Fast OCR extraction - no heavy structure analysis",
    version="3.0.0",
    lifespan=lifespan
)


# ==================== AUDIT LOGGING ====================
# Logs request metadata only (no document content) for security auditing
# Retention: 90 days (configured via logrotate on server)

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Separate audit logger
audit_logger = logging.getLogger("audit")
audit_handler = logging.FileHandler("/var/log/paddleocr-audit.log") if os.path.isdir("/var/log") else logging.StreamHandler(sys.stdout)
audit_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
audit_logger.addHandler(audit_handler)
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False  # Don't duplicate to main logger


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for audit logging.

    Logs request metadata only - NEVER logs request/response bodies
    to ensure document content is never persisted.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Get client IP (handle proxies)
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log metadata only (never body content)
        audit_logger.info(
            f"method={request.method} "
            f"path={request.url.path} "
            f"status={response.status_code} "
            f"duration={duration:.3f}s "
            f"client={client_ip}"
        )

        return response


app.add_middleware(AuditLoggingMiddleware)


# ==================== HELPERS ====================

def extract_text_from_file(file_content: bytes, is_pdf: bool) -> tuple[str, float, int]:
    """Extract text using PaddleOCR."""
    from PIL import Image
    import numpy as np
    import fitz  # PyMuPDF

    all_text = []
    all_confidences = []

    if is_pdf:
        pdf_document = fitz.open(stream=file_content, filetype="pdf")
        total_pages = len(pdf_document)
        logger.info(f"PDF has {total_pages} pages")

        for page_num in range(total_pages):
            page = pdf_document[page_num]
            # Use 200 DPI for speed (was 300)
            pix = page.get_pixmap(matrix=fitz.Matrix(200/72, 200/72))
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            image_array = np.array(image)

            result = ocr_engine.ocr(image_array)
            _parse_result(result, all_text, all_confidences)
            logger.info(f"Page {page_num + 1}/{total_pages} done")

        pdf_document.close()
    else:
        image = Image.open(io.BytesIO(file_content))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image_array = np.array(image)

        result = ocr_engine.ocr(image_array)
        _parse_result(result, all_text, all_confidences)

    full_text = "\n".join(all_text)
    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

    return full_text, avg_confidence, len(all_text)


def _parse_result(result: Any, all_text: list, all_confidences: list) -> None:
    """Parse OCR result from PaddleOCR."""
    if not result:
        return

    try:
        for page_result in result:
            if not page_result:
                continue

            # Handle OCRResult object (dict-like)
            if hasattr(page_result, 'get'):
                rec_texts = page_result.get('rec_texts', [])
                rec_scores = page_result.get('rec_scores', [])
                if rec_texts:
                    for i, t in enumerate(rec_texts):
                        if t:
                            all_text.append(str(t))
                            s = rec_scores[i] if i < len(rec_scores) else 0.9
                            all_confidences.append(float(s) if s else 0.9)
                    continue

            # Handle list format
            for line in page_result:
                if not line:
                    continue

                if hasattr(line, 'rec_text'):
                    text = line.rec_text
                    score = getattr(line, 'rec_score', 0.9)
                elif isinstance(line, dict):
                    text = line.get('rec_text', '')
                    score = line.get('rec_score', 0.9)
                elif isinstance(line, (list, tuple)) and len(line) >= 2:
                    text_part = line[1]
                    if isinstance(text_part, (list, tuple)) and len(text_part) >= 2:
                        text, score = text_part[0], text_part[1]
                    else:
                        text, score = str(text_part), 0.9
                else:
                    continue

                if text:
                    all_text.append(str(text))
                    all_confidences.append(float(score) if score else 0.9)
    except Exception as e:
        logger.warning(f"Error parsing result: {e}")


# ==================== ENDPOINTS ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    use_gpu = os.environ.get("USE_GPU", "false").lower() == "true"
    return HealthResponse(
        status="healthy" if ocr_engine else "degraded",
        service="PaddleOCR Microservice v3.0 (Fast)",
        version="3.0.0",
        paddleocr_available=ocr_engine is not None,
        gpu_enabled=use_gpu
    )


@app.post("/extract", response_model=OCRResponse, dependencies=[Depends(verify_api_key)])
async def extract_text(
    file: UploadFile = File(..., description="Image (JPEG, PNG) or PDF")
):
    """Extract text from document using PaddleOCR."""
    logger.info(f"Request: /extract ({file.filename})")

    if ocr_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR engine not available"
        )

    start_time = time.time()

    try:
        file_content = await file.read()
        file_size = len(file_content)
        logger.info(f"Processing: {file.filename} ({file_size} bytes)")

        is_pdf = (
            file.content_type == 'application/pdf' or
            (file.filename and file.filename.lower().endswith('.pdf'))
        )

        text, confidence, lines = extract_text_from_file(file_content, is_pdf)
        processing_time = time.time() - start_time

        logger.info(f"Done: {len(text)} chars, {lines} lines, {processing_time:.2f}s")

        return OCRResponse(
            text=text,
            confidence=confidence,
            processing_time=processing_time,
            engine="PaddleOCR",
            lines_detected=lines
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR failed: {str(e)}"
        )


@app.get("/")
async def root():
    return {
        "service": "PaddleOCR Microservice v3.0 (Fast)",
        "version": "3.0.0",
        "engine": "PaddleOCR",
        "endpoints": {
            "health": "/health",
            "extract": "/extract (POST)",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=9124, log_level="info")
