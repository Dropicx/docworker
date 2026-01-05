"""
PaddleOCR Microservice v2.0 - PP-StructureV3 Document Parsing

Provides OCR extraction using PaddleOCR 3.x with PP-StructureV3 for:
- Complex document parsing (tables, charts, seals)
- Markdown/JSON output preserving document structure
- Support for both images (PNG/JPG) and PDFs
- 109 language support

Designed as a standalone microservice for Railway deployment.
"""

import io
import logging
import os
import sys
import tempfile
import time
from enum import Enum
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Logging configuration - Standardized format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)
logger = logging.getLogger(__name__)

# ==================== IMPORTS ====================

PPSTRUCTUREV3_AVAILABLE = False
PADDLEOCR_LEGACY_AVAILABLE = False

try:
    from paddleocr import PPStructureV3
    PPSTRUCTUREV3_AVAILABLE = True
    logger.info("PPStructureV3 available")
except ImportError as e:
    logger.warning(f"PPStructureV3 not available: {e}")
    PPStructureV3 = None

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_LEGACY_AVAILABLE = True
    logger.info("PaddleOCR (legacy) available")
except ImportError:
    PaddleOCR = None

# Global pipeline instance (initialized at startup)
structure_pipeline = None
legacy_ocr = None


# ==================== ENUMS & MODELS ====================

class ExtractionMode(str, Enum):
    """Available extraction modes"""
    STRUCTURED = "structured"  # PP-StructureV3 with Markdown output
    TEXT = "text"              # Legacy simple text extraction
    AUTO = "auto"              # Default to structured


class OCRResponse(BaseModel):
    """Response model for OCR extraction (backward compatible + new fields)"""
    text: str
    confidence: float
    processing_time: float
    engine: str = "PPStructureV3"
    mode: str = "structured"
    markdown: Optional[str] = None
    structured_output: Optional[Dict[str, Any]] = None
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    paddleocr_available: bool  # Backward compatibility
    available_modes: Dict[str, bool]


# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize PP-StructureV3 at startup"""
    global structure_pipeline, legacy_ocr

    logger.info("PaddleOCR Microservice v2.0 starting up...")
    logger.info(f"   PPStructureV3 available: {PPSTRUCTUREV3_AVAILABLE}")
    logger.info(f"   PaddleOCR legacy available: {PADDLEOCR_LEGACY_AVAILABLE}")

    # Initialize PP-StructureV3 (primary engine)
    if PPSTRUCTUREV3_AVAILABLE:
        try:
            logger.info("Initializing PP-StructureV3 (CPU mode)...")
            start_init = time.time()

            structure_pipeline = PPStructureV3(
                use_doc_orientation_classify=False,  # CPU optimization
                use_doc_unwarping=False,             # CPU optimization
                use_textline_orientation=False,      # CPU optimization
                device="cpu",
            )

            init_time = time.time() - start_init
            logger.info(f"PP-StructureV3 initialized in {init_time:.2f}s")
            logger.info("   Features: Layout + Tables + Text Recognition")
            logger.info("   Output: Markdown + JSON structure")

        except Exception as e:
            logger.error(f"Failed to initialize PP-StructureV3: {e}")
            structure_pipeline = None

    # Initialize legacy PaddleOCR as fallback
    if PADDLEOCR_LEGACY_AVAILABLE and structure_pipeline is None:
        try:
            logger.info("Initializing PaddleOCR (legacy fallback)...")
            legacy_ocr = PaddleOCR(
                use_angle_cls=True,
                lang='german',
                use_gpu=False,
                show_log=False
            )
            logger.info("PaddleOCR legacy initialized")
        except Exception as e:
            logger.error(f"Failed to initialize legacy PaddleOCR: {e}")

    if structure_pipeline or legacy_ocr:
        logger.info("Service ready to process requests")
    else:
        logger.error("No OCR engine available!")

    yield

    logger.info("PaddleOCR Microservice shutting down...")


# ==================== APP ====================

app = FastAPI(
    title="PaddleOCR Microservice",
    description="Document parsing with PP-StructureV3 - Markdown/JSON output",
    version="2.0.0",
    lifespan=lifespan
)


# ==================== HELPER FUNCTIONS ====================

def extract_with_ppstructurev3(file_path: str, filename: str) -> tuple[str, str, float, Dict]:
    """
    Extract content using PP-StructureV3.

    Returns: (text, markdown, confidence, structured_data)
    """
    import json as json_module
    import glob

    logger.info(f"Running PP-StructureV3 on: {filename}")

    output = structure_pipeline.predict(input=file_path)

    all_markdown = []
    all_text = []
    structured_pages = []

    # Log output type for debugging
    logger.info(f"PP-StructureV3 output type: {type(output)}, length: {len(output) if hasattr(output, '__len__') else 'N/A'}")

    for idx, result in enumerate(output):
        page_markdown = ""
        page_text = ""
        page_structure = {}

        # Log result type for debugging
        logger.debug(f"Result {idx} type: {type(result)}")
        if hasattr(result, '__dict__'):
            logger.debug(f"Result {idx} attributes: {list(result.__dict__.keys())[:10]}")

        # Method 1: Try save_to_markdown (most reliable)
        try:
            if hasattr(result, 'save_to_markdown'):
                with tempfile.TemporaryDirectory() as tmpdir:
                    result.save_to_markdown(save_path=tmpdir)
                    md_files = glob.glob(f"{tmpdir}/**/*.md", recursive=True)
                    if md_files:
                        with open(md_files[0], 'r', encoding='utf-8') as f:
                            page_markdown = f.read()
                        logger.debug(f"Got markdown from save_to_markdown: {len(page_markdown)} chars")
        except Exception as e:
            logger.warning(f"save_to_markdown failed: {e}")

        # Method 2: Try save_to_json
        try:
            if hasattr(result, 'save_to_json'):
                with tempfile.TemporaryDirectory() as tmpdir:
                    result.save_to_json(save_path=tmpdir)
                    json_files = glob.glob(f"{tmpdir}/**/*.json", recursive=True)
                    if json_files:
                        with open(json_files[0], 'r', encoding='utf-8') as f:
                            page_structure = json_module.load(f)
                        logger.debug(f"Got JSON structure: {type(page_structure)}")
        except Exception as e:
            logger.warning(f"save_to_json failed: {e}")

        # Method 3: Try direct attribute access with type checking
        try:
            # Handle markdown attribute (might be str or dict)
            if hasattr(result, 'markdown'):
                md_val = result.markdown
                if isinstance(md_val, str):
                    page_markdown = md_val
                elif isinstance(md_val, dict):
                    # If it's a dict, try to extract text content
                    page_structure = md_val
                    logger.debug(f"markdown attribute is dict with keys: {list(md_val.keys())[:5]}")

            # Handle text attribute
            if hasattr(result, 'text'):
                txt_val = result.text
                if isinstance(txt_val, str):
                    page_text = txt_val
                elif isinstance(txt_val, list):
                    # Join list of text blocks
                    page_text = "\n".join(str(t) for t in txt_val if t)

            # Handle json attribute
            if hasattr(result, 'json'):
                json_val = result.json
                if isinstance(json_val, dict):
                    page_structure = json_val
        except Exception as e:
            logger.debug(f"Direct attribute access failed: {e}")

        # Method 4: If result is a dict itself, extract from it
        if isinstance(result, dict):
            logger.debug(f"Result is dict with keys: {list(result.keys())[:10]}")
            page_text = result.get('text', '') or result.get('content', '')
            if isinstance(page_text, list):
                page_text = "\n".join(str(t) for t in page_text if t)
            page_structure = result

        # Method 5: Try to get rec_text from result (common in PaddleOCR)
        if not page_text:
            try:
                if hasattr(result, 'rec_text'):
                    rec_texts = result.rec_text
                    if isinstance(rec_texts, list):
                        page_text = "\n".join(str(t) for t in rec_texts if t)
                    elif isinstance(rec_texts, str):
                        page_text = rec_texts
            except Exception as e:
                logger.debug(f"rec_text extraction failed: {e}")

        # Use markdown as text if no plain text available
        if page_markdown and not page_text:
            page_text = page_markdown

        # Ensure we only append strings
        if page_markdown and isinstance(page_markdown, str):
            all_markdown.append(page_markdown)
        if page_text and isinstance(page_text, str):
            all_text.append(page_text)
        if page_structure:
            structured_pages.append({"page": idx + 1, "content": page_structure})

    # Combine all pages - ensure all items are strings
    full_markdown = "\n\n---\n\n".join(str(m) for m in all_markdown) if all_markdown else ""
    full_text = "\n\n".join(str(t) for t in all_text) if all_text else full_markdown

    # PP-StructureV3 doesn't provide confidence scores, use default
    confidence = 0.90 if full_text else 0.0

    structured_output = {
        "pages": structured_pages,
        "total_pages": len(output)
    } if structured_pages else {}

    logger.info(f"Extraction complete: {len(full_text)} chars text, {len(full_markdown)} chars markdown")

    return full_text, full_markdown, confidence, structured_output


def extract_with_legacy_ocr(file_content: bytes, is_pdf: bool) -> tuple[str, float, int]:
    """
    Extract text using legacy PaddleOCR.

    Returns: (text, confidence, lines_detected)
    """
    from PIL import Image
    import numpy as np
    import fitz  # PyMuPDF

    all_text = []
    all_confidences = []

    if is_pdf:
        pdf_document = fitz.open(stream=file_content, filetype="pdf")
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            image_array = np.array(image)

            result = legacy_ocr.ocr(image_array, cls=True)
            if result and result[0]:
                for line in result[0]:
                    if line and len(line) >= 2:
                        all_text.append(line[1][0])
                        all_confidences.append(line[1][1])
        pdf_document.close()
    else:
        image = Image.open(io.BytesIO(file_content))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image_array = np.array(image)

        result = legacy_ocr.ocr(image_array, cls=True)
        if result and result[0]:
            for line in result[0]:
                if line and len(line) >= 2:
                    all_text.append(line[1][0])
                    all_confidences.append(line[1][1])

    full_text = "\n".join(all_text)
    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

    return full_text, avg_confidence, len(all_text)


# ==================== ENDPOINTS ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="PaddleOCR Microservice v2.0",
        version="2.0.0",
        paddleocr_available=structure_pipeline is not None or legacy_ocr is not None,
        available_modes={
            "structured": structure_pipeline is not None,
            "text": legacy_ocr is not None or structure_pipeline is not None,
            "auto": structure_pipeline is not None or legacy_ocr is not None
        }
    )


@app.post("/extract", response_model=OCRResponse)
async def extract_text(
    file: UploadFile = File(..., description="Image file (JPEG, PNG) or PDF"),
    mode: ExtractionMode = Query(
        default=ExtractionMode.AUTO,
        description="Extraction mode: structured (Markdown output), text (simple), auto (default)"
    )
):
    """
    Extract text from document using PP-StructureV3 or legacy PaddleOCR.

    **Modes:**
    - `structured` (default): PP-StructureV3 with Markdown/JSON output - best for tables
    - `text`: Simple text extraction (legacy mode)
    - `auto`: Automatically selects structured if available

    **Supported formats:** PNG, JPG, JPEG, PDF

    **Returns:**
    - `text`: Extracted text content (always present for backward compatibility)
    - `markdown`: Structured Markdown output (structured mode only)
    - `structured_output`: JSON structure with layout info (structured mode only)
    """
    # Check service availability
    if structure_pipeline is None and legacy_ocr is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No OCR engine available. Service not properly initialized."
        )

    start_time = time.time()

    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        logger.info(f"Processing: {file.filename} ({file_size} bytes, type: {file.content_type})")

        # Detect file type
        is_pdf = (
            file.content_type == 'application/pdf' or
            (file.filename and file.filename.lower().endswith('.pdf'))
        )

        # Validate file type for images
        if not is_pdf:
            valid_image_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
            if file.content_type and file.content_type not in valid_image_types:
                # Check by extension as fallback
                if file.filename:
                    ext = file.filename.lower().split('.')[-1]
                    if ext not in ['jpg', 'jpeg', 'png', 'webp', 'pdf']:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Unsupported file type: {file.content_type}. Supported: PNG, JPG, PDF"
                        )

        # Determine actual mode
        actual_mode = mode
        if mode == ExtractionMode.AUTO:
            actual_mode = ExtractionMode.STRUCTURED if structure_pipeline else ExtractionMode.TEXT

        # Route to appropriate extractor
        if actual_mode == ExtractionMode.STRUCTURED and structure_pipeline:
            # PP-StructureV3 needs file path, save to temp file
            suffix = ".pdf" if is_pdf else ".png"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            try:
                text, markdown, confidence, structured_output = extract_with_ppstructurev3(
                    tmp_path, file.filename
                )
                engine = "PPStructureV3"
                used_mode = "structured"
            finally:
                # Clean up temp file
                os.unlink(tmp_path)

        elif legacy_ocr:
            # Legacy PaddleOCR extraction
            text, confidence, lines_detected = extract_with_legacy_ocr(file_content, is_pdf)
            markdown = None
            structured_output = None
            engine = "PaddleOCR"
            used_mode = "text"

        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Requested mode '{mode}' is not available"
            )

        processing_time = time.time() - start_time

        logger.info(
            f"Extraction complete: {len(text)} chars, {confidence:.0%} confidence, "
            f"{processing_time:.2f}s ({engine})"
        )

        return OCRResponse(
            text=text,
            confidence=confidence,
            processing_time=processing_time,
            engine=engine,
            mode=used_mode,
            markdown=markdown,
            structured_output=structured_output,
            details={
                "filename": file.filename,
                "file_size_bytes": file_size,
                "file_type": "PDF" if is_pdf else "Image",
                "pages_processed": structured_output.get("total_pages", 1) if structured_output else 1
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR extraction failed: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "PaddleOCR Microservice v2.0",
        "version": "2.0.0",
        "engine": "PP-StructureV3" if structure_pipeline else "PaddleOCR (legacy)",
        "features": [
            "Table recognition",
            "Chart extraction",
            "Markdown output",
            "JSON structure",
            "PDF support",
            "Image support (PNG, JPG)"
        ],
        "modes": ["structured", "text", "auto"],
        "endpoints": {
            "health": "/health",
            "extract": "/extract (POST) - ?mode=structured|text|auto",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    # Use :: for IPv6 to support Railway internal networking
    uvicorn.run(
        "app.main:app",
        host="::",
        port=9123,
        log_level="info"
    )
