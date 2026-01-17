"""
SpaCy PII Removal Microservice

GDPR-compliant PII (Personally Identifiable Information) removal for medical documents.
Supports German and English languages with large SpaCy models for maximum accuracy.

Endpoints:
    GET  /health     - Health check with model status
    POST /remove-pii - Remove PII from text (requires language parameter)
    POST /remove-pii/batch - Batch PII removal
"""

from contextlib import asynccontextmanager
import logging
import os
import time
from typing import Literal

import psutil
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.pii_filter import PIIFilter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global filter instance (loaded once at startup)
pii_filter: PIIFilter | None = None


# =============================================================================
# Request/Response Models
# =============================================================================

class PIIRemovalRequest(BaseModel):
    """Request model for PII removal."""
    text: str = Field(..., description="Text to process", min_length=1)
    language: Literal["de", "en"] = Field(
        default="de",
        description="Language of the text: 'de' for German, 'en' for English"
    )
    include_metadata: bool = Field(
        default=True,
        description="Include detection metadata in response"
    )
    custom_protection_terms: list[str] | None = Field(
        default=None,
        description="Additional terms to protect from removal (synced from database)"
    )


class PIIRemovalResponse(BaseModel):
    """Response model for PII removal."""
    cleaned_text: str
    processing_time_ms: float
    language_used: str
    metadata: dict | None = None


class PIIBatchRequest(BaseModel):
    """Request model for batch PII removal."""
    texts: list[str] = Field(..., description="List of texts to process", min_length=1)
    language: Literal["de", "en"] = Field(default="de")
    batch_size: int = Field(default=32, ge=1, le=100)
    custom_protection_terms: list[str] | None = Field(
        default=None,
        description="Additional terms to protect from removal (synced from database)"
    )


class PIIBatchResponse(BaseModel):
    """Response model for batch PII removal."""
    results: list[dict]
    total_documents: int
    processing_time_ms: float
    language_used: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    spacy_available: bool
    german_model_loaded: bool
    english_model_loaded: bool
    presidio_available: bool = False
    medialpy_available: bool = False
    medialpy_version: str | None = None
    medical_verifier_active: bool = False
    memory_usage_mb: float


# =============================================================================
# Application Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load SpaCy models at startup."""
    global pii_filter

    logger.info("=" * 60)
    logger.info("SpaCy PII Service Starting...")
    logger.info("=" * 60)

    # Log environment for debugging model loading issues
    import sys
    spacy_data_dir = os.environ.get("SPACY_DATA_DIR", "/data/models")
    logger.info(f"SPACY_DATA_DIR: {spacy_data_dir}")
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', '(not set)')}")
    logger.info(f"sys.path includes SPACY_DATA_DIR: {spacy_data_dir in sys.path}")

    # Check volume mount
    if os.path.isdir(spacy_data_dir):
        try:
            contents = os.listdir(spacy_data_dir)
            logger.info(f"Volume mount exists. Contents ({len(contents)} items): {contents}")
        except Exception as e:
            logger.warning(f"Could not list volume contents: {e}")
    else:
        logger.warning(f"Volume mount NOT found at {spacy_data_dir}")

    logger.info("Loading language models (this may take 60-90 seconds)...")

    try:
        # Initialize filter (loads both German and English models)
        pii_filter = PIIFilter()

        memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        logger.info(f"Models loaded successfully. Memory usage: {memory_mb:.1f}MB")
        logger.info(f"German model: {'OK' if pii_filter.german_model_loaded else 'FAILED'}")
        logger.info(f"English model: {'OK' if pii_filter.english_model_loaded else 'FAILED'}")
        logger.info("=" * 60)
        logger.info("Service ready to accept requests on port 9125")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Failed to initialize PII filter: {e}")
        pii_filter = None

    yield

    logger.info("Shutting down PII service...")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="SpaCy PII Removal Service",
    description="GDPR-compliant PII removal for German and English medical documents",
    version="1.0.0",
    lifespan=lifespan
)


# =============================================================================
# Audit Logging Middleware
# =============================================================================
# Logs request metadata only (no text content) for security auditing
# Retention: 90 days (configured via logrotate on server)

import sys
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Separate audit logger
audit_logger = logging.getLogger("audit")

# Try to write to file, fall back to stdout if permission denied
def _get_audit_handler():
    log_path = "/var/log/pii-audit.log"
    try:
        # Test if we can write to the log file
        handler = logging.FileHandler(log_path)
        logger.info(f"Audit logging to file: {log_path}")
        return handler
    except (PermissionError, OSError) as e:
        logger.warning(f"Cannot write to {log_path}: {e}. Using stdout for audit logs.")
        return logging.StreamHandler(sys.stdout)

audit_handler = _get_audit_handler()
audit_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
audit_logger.addHandler(audit_handler)
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False  # Don't duplicate to main logger


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for audit logging.

    Logs request metadata only - NEVER logs request/response bodies
    to ensure PII text content is never persisted.
    """

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()

        # Get client IP (handle proxies)
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.perf_counter() - start

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


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - service info."""
    return {
        "service": "SpaCy PII Removal Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "remove_pii": "/remove-pii",
            "batch": "/remove-pii/batch",
            "docs": "/docs"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint with model status."""
    memory_mb = psutil.Process().memory_info().rss / 1024 / 1024

    # Check MEDIALpy availability
    try:
        from app.medical_term_verifier import MEDIALPY_AVAILABLE, MEDIALPY_VERSION
        medialpy_available = MEDIALPY_AVAILABLE
        medialpy_version = MEDIALPY_VERSION
    except ImportError:
        medialpy_available = False
        medialpy_version = None

    if pii_filter is None:
        return HealthResponse(
            status="unhealthy",
            service="SpaCy PII Service",
            version="1.0.0",
            spacy_available=False,
            german_model_loaded=False,
            english_model_loaded=False,
            presidio_available=False,
            medialpy_available=medialpy_available,
            medialpy_version=medialpy_version,
            medical_verifier_active=False,
            memory_usage_mb=memory_mb
        )

    # Determine overall status
    if pii_filter.german_model_loaded and pii_filter.english_model_loaded:
        status = "healthy"
    elif pii_filter.german_model_loaded or pii_filter.english_model_loaded:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthResponse(
        status=status,
        service="SpaCy PII Service",
        version="1.0.0",
        spacy_available=True,
        german_model_loaded=pii_filter.german_model_loaded,
        english_model_loaded=pii_filter.english_model_loaded,
        presidio_available=pii_filter.presidio_available,
        medialpy_available=medialpy_available,
        medialpy_version=medialpy_version,
        medical_verifier_active=hasattr(pii_filter, 'medical_verifier'),
        memory_usage_mb=memory_mb
    )


@app.post("/remove-pii", response_model=PIIRemovalResponse, dependencies=[Depends(verify_api_key)])
async def remove_pii(request: PIIRemovalRequest):
    """
    Remove PII from text.

    Removes personally identifiable information while preserving medical content.
    Supports German (de) and English (en) languages.
    """
    if pii_filter is None:
        raise HTTPException(
            status_code=503,
            detail="PII filter not initialized. Check /health for status."
        )

    # Validate language model availability
    if request.language == "de" and not pii_filter.german_model_loaded:
        raise HTTPException(
            status_code=503,
            detail="German language model not loaded. Check /health for status."
        )
    if request.language == "en" and not pii_filter.english_model_loaded:
        raise HTTPException(
            status_code=503,
            detail="English language model not loaded. Check /health for status."
        )

    start = time.perf_counter()

    try:
        cleaned_text, metadata = pii_filter.remove_pii(
            text=request.text,
            language=request.language,
            custom_protection_terms=request.custom_protection_terms
        )
    except Exception as e:
        logger.error(f"PII removal failed: {e}")
        raise HTTPException(status_code=500, detail=f"PII removal failed: {str(e)}")

    processing_time_ms = (time.perf_counter() - start) * 1000

    return PIIRemovalResponse(
        cleaned_text=cleaned_text,
        processing_time_ms=round(processing_time_ms, 2),
        language_used=request.language,
        metadata=metadata if request.include_metadata else None
    )


@app.post("/remove-pii/batch", response_model=PIIBatchResponse, dependencies=[Depends(verify_api_key)])
async def remove_pii_batch(request: PIIBatchRequest):
    """
    Batch PII removal for multiple texts.

    More efficient than calling /remove-pii multiple times.
    """
    if pii_filter is None:
        raise HTTPException(
            status_code=503,
            detail="PII filter not initialized. Check /health for status."
        )

    start = time.perf_counter()

    try:
        results = pii_filter.remove_pii_batch(
            texts=request.texts,
            language=request.language,
            batch_size=request.batch_size,
            custom_protection_terms=request.custom_protection_terms
        )
    except Exception as e:
        logger.error(f"Batch PII removal failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch PII removal failed: {str(e)}")

    processing_time_ms = (time.perf_counter() - start) * 1000

    return PIIBatchResponse(
        results=[{"cleaned_text": t, "metadata": m} for t, m in results],
        total_documents=len(request.texts),
        processing_time_ms=round(processing_time_ms, 2),
        language_used=request.language
    )


# =============================================================================
# Run with Uvicorn
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "9125"))
    # HOST_BIND: "::" for IPv6 (Railway) or "0.0.0.0" for IPv4 (Hetzner)
    host = os.getenv("HOST_BIND", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
