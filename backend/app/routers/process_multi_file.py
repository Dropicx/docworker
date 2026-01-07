"""
Multi-File Processing Router (DEPRECATED)

This endpoint is deprecated in favor of the worker-based pipeline.
Use the /upload endpoint to submit documents, then /process/{id} to start processing.

The new architecture:
1. POST /upload - Upload document, creates job in database
2. POST /process/{processing_id} - Start processing with options (target_language, etc.)
3. GET /result/{processing_id} - Poll for results

OCR is now handled by OCREngineManager with:
- Mistral OCR (primary)
- PaddleOCR Hetzner (fallback)
"""

import logging
import os

from fastapi import APIRouter, File, HTTPException, UploadFile

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
MAX_FILES = int(os.getenv("MAX_FILES_PER_BATCH", "10"))
MAX_TOTAL_SIZE = int(os.getenv("MAX_TOTAL_BATCH_SIZE", "50000000"))  # 50MB


@router.post("/process-multi-file")
async def process_multiple_files(
    files: list[UploadFile] = File(...),
):
    """
    DEPRECATED: Multi-file processing endpoint.

    This endpoint has been deprecated. Please use the following flow instead:
    1. POST /upload - Upload each document individually
    2. POST /process/{processing_id} - Start processing
    3. GET /result/{processing_id} - Get results

    The new architecture uses a worker-based pipeline with:
    - Mistral OCR (primary OCR engine)
    - PaddleOCR Hetzner (fallback OCR engine)
    """
    logger.warning("⚠️ DEPRECATED: /process-multi-file endpoint called")

    raise HTTPException(
        status_code=410,  # Gone
        detail={
            "error": "endpoint_deprecated",
            "message": "This endpoint has been deprecated. Please use /upload and /process/{id} instead.",
            "migration": {
                "step_1": "POST /upload - Upload document",
                "step_2": "POST /process/{processing_id} - Start processing with options",
                "step_3": "GET /result/{processing_id} - Poll for results",
            },
            "ocr_engines": ["MISTRAL_OCR (primary)", "PADDLEOCR (fallback via Hetzner)"],
        },
    )


@router.get("/multi-file/limits")
async def get_multi_file_limits():
    """Get the limits for file uploads (redirects to main upload limits)"""
    return {
        "deprecated": True,
        "message": "Use /upload/limits instead",
        "max_files_per_batch": MAX_FILES,
        "max_total_size": MAX_TOTAL_SIZE,
        "supported_formats": ["pdf", "jpg", "jpeg", "png"],
        "ocr_engines": ["MISTRAL_OCR", "PADDLEOCR"],
    }


@router.post("/process-multi-file/batch-status")
async def get_batch_processing_status(session_ids: list[str]):
    """DEPRECATED: Use /result/{processing_id} for individual job status"""
    raise HTTPException(
        status_code=410,
        detail={
            "error": "endpoint_deprecated",
            "message": "Use GET /result/{processing_id} for job status",
        },
    )


@router.post("/analyze-files")
async def analyze_files_strategy(files: list[UploadFile] = File(...)):
    """
    DEPRECATED: File analysis endpoint.

    Quality analysis is now performed automatically during upload.
    Documents that don't meet quality thresholds are rejected at upload time.
    """
    raise HTTPException(
        status_code=410,
        detail={
            "error": "endpoint_deprecated",
            "message": "File quality analysis is now performed automatically during /upload",
        },
    )
