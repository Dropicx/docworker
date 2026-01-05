"""
PaddleOCR Microservice v2.1 - PP-StructureV3 Document Parsing (Lite)

Provides OCR extraction using PaddleOCR 3.x with PP-StructureV3 for:
- Document layout detection and text extraction
- Table recognition with Markdown output
- Support for both images (PNG/JPG) and PDFs

MEMORY OPTIMIZED: Disabled chart/formula recognition to fit Railway Pro (~4GB)
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

# ==================== ENVIRONMENT SETUP ====================
# Must set environment variables BEFORE importing paddleocr/paddlex
# These control model cache location and behavior

MODEL_CACHE_DIR = os.environ.get("PADDLEX_HOME", "/home/appuser/.paddlex")

# Set all relevant cache directories to the mounted volume
os.environ["PADDLEX_HOME"] = MODEL_CACHE_DIR
os.environ["HF_HOME"] = f"{MODEL_CACHE_DIR}/huggingface"
os.environ["HF_HUB_CACHE"] = f"{MODEL_CACHE_DIR}/huggingface/hub"
os.environ["HUGGINGFACE_HUB_CACHE"] = f"{MODEL_CACHE_DIR}/huggingface/hub"
os.environ["TRANSFORMERS_CACHE"] = f"{MODEL_CACHE_DIR}/transformers"

# Disable connectivity checks for faster startup
os.environ["DISABLE_MODEL_SOURCE_CHECK"] = "True"
os.environ["HF_HUB_OFFLINE"] = "0"  # Allow downloads but skip checks

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth import verify_api_key
import uvicorn

# Logging configuration - Standardized format with immediate flushing
class FlushingStreamHandler(logging.StreamHandler):
    """Stream handler that flushes after every emit for real-time logs."""
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

logger.info(f"Model cache directory: {MODEL_CACHE_DIR}")
logger.info(f"PADDLEX_HOME: {os.environ.get('PADDLEX_HOME')}")

# ==================== IMPORTS ====================

PPSTRUCTUREV3_AVAILABLE = False
PADDLEOCR_AVAILABLE = False

try:
    from paddleocr import PPStructureV3
    PPSTRUCTUREV3_AVAILABLE = True
    logger.info("PPStructureV3 available")
except ImportError as e:
    logger.warning(f"PPStructureV3 not available: {e}")
    PPStructureV3 = None

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
    logger.info("PaddleOCR 3.x available")
except ImportError:
    PaddleOCR = None
    PADDLEOCR_AVAILABLE = False

# Global pipeline instance (initialized at startup)
structure_pipeline = None
ocr_engine = None  # PaddleOCR 3.x standard OCR


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
    global structure_pipeline, ocr_engine

    logger.info("PaddleOCR Microservice v2.0 starting up...")
    logger.info(f"   PPStructureV3 available: {PPSTRUCTUREV3_AVAILABLE}")
    logger.info(f"   PaddleOCR 3.x available: {PADDLEOCR_AVAILABLE}")

    # PP-StructureV3 DISABLED - uses 32GB+ RAM regardless of parameters
    # The use_chart_recognition=False parameter doesn't prevent model loading
    logger.warning("⚠️ PP-StructureV3 DISABLED - too memory hungry (32GB+)")
    logger.info("Using PaddleOCR 3.x standard mode instead (~500MB)")
    structure_pipeline = None

    # Initialize PaddleOCR 3.x (standard mode, ~500MB RAM)
    if PADDLEOCR_AVAILABLE:
        try:
            logger.info("Initializing PaddleOCR 3.x...")
            start_init = time.time()
            # Disable optional preprocessing models to reduce startup time
            ocr_engine = PaddleOCR(
                lang='german',
                device='cpu',
                use_doc_orientation_classify=False,  # Skip document orientation detection
                use_doc_unwarping=False,             # Skip document unwarping
            )
            init_time = time.time() - start_init
            logger.info(f"✅ PaddleOCR initialized in {init_time:.2f}s")
            logger.info("   Features: Text detection + Recognition + Angle classification")
            logger.info("   Languages: German (de)")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            logger.exception(e)

    if structure_pipeline or ocr_engine:
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

def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively convert numpy arrays and other non-JSON-serializable types to Python native types.
    This is necessary because PP-StructureV3 returns numpy arrays in its output.
    """
    import numpy as np

    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(sanitize_for_json(item) for item in obj)
    else:
        return obj


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
            # Sanitize page_structure to convert numpy arrays to lists
            sanitized_structure = sanitize_for_json(page_structure)
            structured_pages.append({"page": idx + 1, "content": sanitized_structure})

    # Combine all pages - ensure all items are strings
    full_markdown = "\n\n---\n\n".join(str(m) for m in all_markdown) if all_markdown else ""
    full_text = "\n\n".join(str(t) for t in all_text) if all_text else full_markdown

    # PP-StructureV3 doesn't provide confidence scores, use default
    confidence = 0.90 if full_text else 0.0

    structured_output = {
        "pages": structured_pages,
        "total_pages": len(output)
    } if structured_pages else {}

    # Final sanitization pass to ensure no numpy arrays remain
    structured_output = sanitize_for_json(structured_output)

    logger.info(f"Extraction complete: {len(full_text)} chars text, {len(full_markdown)} chars markdown")

    return full_text, full_markdown, confidence, structured_output


def _parse_ocr_result(result: Any, all_text: list, all_confidences: list) -> None:
    """
    Parse OCR result from PaddleOCR 3.x (handles multiple result formats).
    """
    # Debug: Log what we received
    print(f"🔍 DEBUG _parse_ocr_result: result type={type(result)}", file=sys.stderr, flush=True)

    if not result:
        print(f"🔍 DEBUG: result is empty/None", file=sys.stderr, flush=True)
        return

    # Log structure
    if hasattr(result, '__len__'):
        print(f"🔍 DEBUG: result length={len(result)}", file=sys.stderr, flush=True)
    if hasattr(result, '__dict__'):
        print(f"🔍 DEBUG: result attrs={list(result.__dict__.keys())[:10]}", file=sys.stderr, flush=True)

    # PaddleOCR 3.x can return different structures
    # Try to handle both old format and new format
    try:
        for idx, page_result in enumerate(result):
            print(f"🔍 DEBUG: page_result[{idx}] type={type(page_result)}", file=sys.stderr, flush=True)
            if not page_result:
                print(f"🔍 DEBUG: page_result[{idx}] is empty", file=sys.stderr, flush=True)
                continue

            # Handle PaddleX OCRResult object (dict-like)
            type_name = type(page_result).__name__
            if type_name == 'OCRResult' or 'OCRResult' in str(type(page_result)):
                print(f"🔍 DEBUG: Detected OCRResult object", file=sys.stderr, flush=True)

                # OCRResult is dict-like, try to get keys first
                if hasattr(page_result, 'keys'):
                    keys = list(page_result.keys())
                    print(f"🔍 DEBUG: OCRResult keys: {keys}", file=sys.stderr, flush=True)

                # Try to get rec_texts from dict (note: plural 'rec_texts' not 'rec_text')
                rec_texts = page_result.get('rec_texts') if hasattr(page_result, 'get') else None
                rec_scores = page_result.get('rec_scores') if hasattr(page_result, 'get') else None

                if rec_texts:
                    print(f"🔍 DEBUG: rec_text from dict: type={type(rec_texts)}, len={len(rec_texts) if hasattr(rec_texts, '__len__') else 'N/A'}", file=sys.stderr, flush=True)
                    if isinstance(rec_texts, list):
                        for i, t in enumerate(rec_texts):
                            if t:
                                all_text.append(str(t))
                                s = rec_scores[i] if rec_scores and isinstance(rec_scores, list) and i < len(rec_scores) else 0.9
                                all_confidences.append(float(s) if s else 0.9)
                    elif rec_texts:
                        all_text.append(str(rec_texts))
                        all_confidences.append(0.9)
                else:
                    # Try str() method which might return formatted text
                    if hasattr(page_result, 'str'):
                        str_result = page_result.str
                        print(f"🔍 DEBUG: str method result type: {type(str_result)}", file=sys.stderr, flush=True)
                        if callable(str_result):
                            str_result = str_result()
                        if str_result:
                            print(f"🔍 DEBUG: str result (first 200 chars): {str(str_result)[:200]}", file=sys.stderr, flush=True)

                    # Try json() method
                    if hasattr(page_result, 'json'):
                        try:
                            json_data = page_result.json if not callable(page_result.json) else page_result.json()
                            print(f"🔍 DEBUG: json data type: {type(json_data)}", file=sys.stderr, flush=True)
                            if isinstance(json_data, dict):
                                print(f"🔍 DEBUG: json keys: {list(json_data.keys())[:10]}", file=sys.stderr, flush=True)
                                # Try to extract text from json
                                if 'rec_text' in json_data:
                                    texts = json_data['rec_text']
                                    scores = json_data.get('rec_score', [])
                                    if isinstance(texts, list):
                                        for i, t in enumerate(texts):
                                            if t:
                                                all_text.append(str(t))
                                                s = scores[i] if i < len(scores) else 0.9
                                                all_confidences.append(float(s) if s else 0.9)
                        except Exception as e:
                            print(f"🔍 DEBUG: json() failed: {e}", file=sys.stderr, flush=True)
                continue

            # Check if page_result itself has the text attributes (not nested)
            if hasattr(page_result, 'rec_text'):
                print(f"🔍 DEBUG: page_result has rec_text directly", file=sys.stderr, flush=True)
                texts = page_result.rec_text
                scores = getattr(page_result, 'rec_score', [0.9] * len(texts) if isinstance(texts, list) else [0.9])
                if isinstance(texts, list):
                    for t, s in zip(texts, scores if isinstance(scores, list) else [scores]):
                        if t:
                            all_text.append(str(t))
                            all_confidences.append(float(s) if s else 0.9)
                elif texts:
                    all_text.append(str(texts))
                    all_confidences.append(float(scores[0]) if isinstance(scores, list) else float(scores))
                continue

            for line_idx, line in enumerate(page_result):
                if line_idx == 0:
                    print(f"🔍 DEBUG: first line type={type(line)}", file=sys.stderr, flush=True)
                    if hasattr(line, '__dict__'):
                        print(f"🔍 DEBUG: first line attrs={list(line.__dict__.keys())}", file=sys.stderr, flush=True)

                if not line:
                    continue

                # New format: line might be a dict or have 'rec_text' attribute
                if hasattr(line, 'rec_text'):
                    text = line.rec_text
                    score = getattr(line, 'rec_score', 0.9)
                    if text:
                        all_text.append(str(text))
                        all_confidences.append(float(score) if score else 0.9)
                elif isinstance(line, dict):
                    text = line.get('rec_text') or line.get('text', '')
                    score = line.get('rec_score') or line.get('score', 0.9)
                    if text:
                        all_text.append(str(text))
                        all_confidences.append(float(score) if score else 0.9)
                elif isinstance(line, (list, tuple)) and len(line) >= 2:
                    # Old format: [[box], (text, confidence)]
                    text_part = line[1]
                    if isinstance(text_part, (list, tuple)) and len(text_part) >= 2:
                        text, conf = text_part[0], text_part[1]
                    elif isinstance(text_part, str):
                        text, conf = text_part, 0.9
                    else:
                        continue
                    if text:
                        all_text.append(str(text))
                        all_confidences.append(float(conf) if conf else 0.9)
    except Exception as e:
        logger.warning(f"Error parsing OCR result: {e}, result type: {type(result)}")
        # Try to extract any text we can find
        if isinstance(result, str):
            all_text.append(result)
            all_confidences.append(0.9)


def extract_with_ocr_engine(file_content: bytes, is_pdf: bool) -> tuple[str, float, int]:
    """
    Extract text using PaddleOCR 3.x standard mode.

    Returns: (text, confidence, lines_detected)
    """
    from PIL import Image
    import numpy as np
    import fitz  # PyMuPDF

    all_text = []
    all_confidences = []

    ocr_start = time.time()
    logger.info(f"🔍 Starting OCR extraction (is_pdf={is_pdf})")

    if is_pdf:
        pdf_document = fitz.open(stream=file_content, filetype="pdf")
        total_pages = len(pdf_document)
        logger.info(f"📄 PDF has {total_pages} pages")
        for page_num in range(total_pages):
            page_start = time.time()
            page = pdf_document[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            image_array = np.array(image)
            print(f"🔍 DEBUG: Page {page_num+1} image shape={image_array.shape}", file=sys.stderr, flush=True)

            result = ocr_engine.ocr(image_array)
            print(f"🔍 DEBUG: OCR returned type={type(result)}, is_none={result is None}", file=sys.stderr, flush=True)
            _parse_ocr_result(result, all_text, all_confidences)
            print(f"🔍 DEBUG: After parsing, text count={len(all_text)}", file=sys.stderr, flush=True)
            logger.info(f"📄 Page {page_num + 1}/{total_pages} OCR completed in {time.time() - page_start:.2f}s")
        pdf_document.close()
    else:
        image = Image.open(io.BytesIO(file_content))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image_array = np.array(image)
        logger.info(f"🖼️ Image size: {image_array.shape}")

        result = ocr_engine.ocr(image_array)
        _parse_ocr_result(result, all_text, all_confidences)

    full_text = "\n".join(all_text)
    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

    total_time = time.time() - ocr_start
    logger.info(f"✅ OCR extraction completed: {len(all_text)} lines, {len(full_text)} chars in {total_time:.2f}s")

    return full_text, avg_confidence, len(all_text)


# ==================== ENDPOINTS ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="PaddleOCR Microservice v2.0",
        version="2.0.0",
        paddleocr_available=structure_pipeline is not None or ocr_engine is not None,
        available_modes={
            "structured": structure_pipeline is not None,
            "text": ocr_engine is not None or structure_pipeline is not None,
            "auto": structure_pipeline is not None or ocr_engine is not None
        }
    )


@app.post("/extract", response_model=OCRResponse, dependencies=[Depends(verify_api_key)])
async def extract_text(
    file: UploadFile = File(..., description="Image file (JPEG, PNG) or PDF"),
    mode: ExtractionMode = Query(
        default=ExtractionMode.AUTO,
        description="Extraction mode: structured (Markdown output), text (simple), auto (default)"
    )
):
    """
    Extract text from document using PP-StructureV3 or legacy PaddleOCR.

    **Authentication:** Requires X-API-Key header if API_SECRET_KEY is set.

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
    # Log request immediately (before any processing) - use both logger and stderr for visibility
    print(f"📥 INCOMING REQUEST: /extract (mode={mode}, filename={file.filename})", file=sys.stderr, flush=True)
    logger.info(f"📥 INCOMING REQUEST: /extract (mode={mode}, filename={file.filename})")

    # Check service availability
    if structure_pipeline is None and ocr_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No OCR engine available. Service not properly initialized."
        )

    start_time = time.time()

    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        print(f"📄 Processing: {file.filename} ({file_size} bytes, type: {file.content_type})", file=sys.stderr, flush=True)
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

        elif ocr_engine:
            # PaddleOCR 3.x standard extraction
            text, confidence, lines_detected = extract_with_ocr_engine(file_content, is_pdf)
            markdown = None
            structured_output = None
            engine = "PaddleOCR-3.x"
            used_mode = "text"

        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Requested mode '{mode}' is not available"
            )

        processing_time = time.time() - start_time

        result_msg = f"✅ Extraction complete: {len(text)} chars, {confidence:.0%} confidence, {processing_time:.2f}s ({engine})"
        print(result_msg, file=sys.stderr, flush=True)
        logger.info(result_msg)
        print(f"📤 SENDING RESPONSE for {file.filename}", file=sys.stderr, flush=True)
        logger.info(f"📤 SENDING RESPONSE for {file.filename}")

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
    # Use 0.0.0.0 to listen on all interfaces (IPv4 and IPv6)
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9123,
        log_level="info"
    )
