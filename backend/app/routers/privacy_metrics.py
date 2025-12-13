"""Privacy Filter Metrics API Router.

Issue #35 Phase 6.3: Production Monitoring
Provides endpoints for monitoring PII detection performance and statistics.

Updated to use worker for all processing (ensures NER is available).
"""

from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.celery_client import (
    test_privacy_filter_via_worker,
    get_privacy_filter_status_via_worker,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/privacy", tags=["Privacy Metrics"])


# ==================== RESPONSE MODELS ====================


class ConfidenceBreakdown(BaseModel):
    """Confidence level breakdown for PII removals."""
    high_confidence: int = 0
    medium_confidence: int = 0
    low_confidence: int = 0
    pattern_based: int = 0


class DetectionStats(BaseModel):
    """PII detection statistics."""
    pii_types_supported: list[str]
    pii_types_count: int
    medical_terms_count: int
    drug_database_count: int
    abbreviations_count: int
    eponyms_count: int
    loinc_codes_count: int


class FilterCapabilities(BaseModel):
    """Privacy filter capabilities and configuration."""
    has_ner: bool
    spacy_model: str
    removal_method: str
    custom_terms_loaded: bool


class PrivacyMetricsResponse(BaseModel):
    """Complete privacy metrics response."""
    timestamp: str
    filter_capabilities: FilterCapabilities
    detection_stats: DetectionStats
    performance_target_ms: int = 100
    worker_status: str = "connected"


class LiveTestResult(BaseModel):
    """Result of a live privacy filter test."""
    input_length: int
    output_length: int
    cleaned_text: str
    processing_time_ms: float
    pii_types_detected: list[str]
    entities_detected: int
    quality_score: float
    review_recommended: bool
    passes_performance_target: bool


class LiveTestRequest(BaseModel):
    """Request body for live testing."""
    text: str


# ==================== ENDPOINTS ====================


@router.get("/metrics", response_model=PrivacyMetricsResponse)
async def get_privacy_metrics():
    """Get privacy filter capabilities and detection statistics from worker.

    Returns comprehensive information about the privacy filter's:
    - NER availability and configuration (from worker)
    - Number of PII types supported
    - Medical term protection counts
    - Drug database size
    - Performance targets
    """
    try:
        # Get status from worker (has NER loaded)
        worker_status = get_privacy_filter_status_via_worker(timeout=10)

        caps = worker_status["filter_capabilities"]
        stats = worker_status["detection_stats"]

        return PrivacyMetricsResponse(
            timestamp=datetime.now().isoformat(),
            filter_capabilities=FilterCapabilities(
                has_ner=caps["has_ner"],
                spacy_model=caps["spacy_model"],
                removal_method=caps["removal_method"],
                custom_terms_loaded=caps["custom_terms_loaded"],
            ),
            detection_stats=DetectionStats(
                pii_types_supported=stats["pii_types_supported"],
                pii_types_count=stats["pii_types_count"],
                medical_terms_count=stats["medical_terms_count"],
                drug_database_count=stats["drug_database_count"],
                abbreviations_count=stats["abbreviations_count"],
                eponyms_count=stats["eponyms_count"],
                loinc_codes_count=stats["loinc_codes_count"],
            ),
            performance_target_ms=100,
            worker_status="connected",
        )

    except Exception as e:
        logger.error(f"Failed to get metrics from worker: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Worker unavailable: {str(e)}. Please ensure the worker service is running."
        )


@router.post("/test", response_model=LiveTestResult)
async def test_privacy_filter(request: LiveTestRequest):
    """Live test the privacy filter with custom text via worker.

    Processes the provided text using the worker's full NER capabilities:
    - spaCy de_core_news_md model for intelligent name detection
    - Pattern-based PII removal
    - Medical term protection

    Returns:
    - Processing time
    - PII types detected
    - Quality score
    - Review recommendations
    - Cleaned text output

    Note: The input text is NOT stored or logged.
    """
    if not request.text:
        raise HTTPException(status_code=400, detail="Text is required")

    if len(request.text) > 50000:
        raise HTTPException(status_code=400, detail="Text too long (max 50000 chars)")

    try:
        # Process via worker (has NER loaded)
        result = test_privacy_filter_via_worker(request.text, timeout=30)

        return LiveTestResult(
            input_length=result["input_length"],
            output_length=result["output_length"],
            cleaned_text=result["cleaned_text"],
            processing_time_ms=result["processing_time_ms"],
            pii_types_detected=result["pii_types_detected"],
            entities_detected=result["entities_detected"],
            quality_score=result["quality_score"],
            review_recommended=result["review_recommended"],
            passes_performance_target=result["passes_performance_target"],
        )

    except Exception as e:
        logger.error(f"Privacy filter test failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Worker processing failed: {str(e)}. Please ensure the worker service is running."
        )


@router.get("/health")
async def privacy_filter_health():
    """Check privacy filter health and readiness via worker.

    Returns:
    - Filter initialization status
    - NER model availability (from worker)
    - Medical term database status
    - Worker connection status
    """
    try:
        # Get status from worker
        worker_status = get_privacy_filter_status_via_worker(timeout=5)

        caps = worker_status["filter_capabilities"]
        stats = worker_status["detection_stats"]

        return {
            "status": "healthy",
            "filter_ready": True,
            "ner_available": caps["has_ner"],
            "spacy_model": caps["spacy_model"],
            "medical_terms_loaded": stats["medical_terms_count"] > 0,
            "drug_database_loaded": stats["drug_database_count"] > 0,
            "worker_connected": True,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.warning(f"Worker health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "filter_ready": False,
            "ner_available": False,
            "worker_connected": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/pii-types")
async def list_pii_types():
    """List all PII types detected by the privacy filter.

    Returns detailed information about each PII type including:
    - Type identifier
    - Description
    - Replacement marker used
    """
    pii_types = [
        {"type": "birthdate", "description": "Birth dates (Geb., Geboren)", "marker": "[GEBURTSDATUM ENTFERNT]"},
        {"type": "patient_name", "description": "Patient names (explicit patterns)", "marker": "[NAME ENTFERNT]"},
        {"type": "street_address", "description": "Street addresses", "marker": "[ADRESSE ENTFERNT]"},
        {"type": "postal_code_city", "description": "PLZ and city names", "marker": "[PLZ/ORT ENTFERNT]"},
        {"type": "phone_number", "description": "Phone numbers", "marker": "[TELEFON ENTFERNT]"},
        {"type": "mobile_phone", "description": "Mobile phone numbers", "marker": "[MOBILTELEFON ENTFERNT]"},
        {"type": "fax_number", "description": "Fax numbers", "marker": "[FAX ENTFERNT]"},
        {"type": "email_address", "description": "Email addresses", "marker": "[EMAIL ENTFERNT]"},
        {"type": "insurance_number", "description": "Insurance numbers", "marker": "[NUMMER ENTFERNT]"},
        {"type": "insurance_policy", "description": "Insurance policy numbers", "marker": "[VERSICHERTENNUMMER ENTFERNT]"},
        {"type": "patient_id", "description": "Patient IDs and case numbers", "marker": "[PATIENTEN-ID ENTFERNT]"},
        {"type": "hospital_id", "description": "Hospital/clinic internal numbers", "marker": "[KRANKENHAUS-NR ENTFERNT]"},
        {"type": "tax_id", "description": "German tax ID (Steuer-ID)", "marker": "[STEUER-ID ENTFERNT]"},
        {"type": "social_security_number", "description": "German social security number", "marker": "[SOZIALVERSICHERUNGSNUMMER ENTFERNT]"},
        {"type": "passport_number", "description": "German passport number", "marker": "[REISEPASSNUMMER ENTFERNT]"},
        {"type": "id_card_number", "description": "German ID card number", "marker": "[PERSONALAUSWEIS ENTFERNT]"},
        {"type": "gender", "description": "Gender information (when labeled)", "marker": "[GESCHLECHT ENTFERNT]"},
        {"type": "url", "description": "Website URLs", "marker": "[URL ENTFERNT]"},
    ]

    return {
        "pii_types": pii_types,
        "total_count": len(pii_types),
        "timestamp": datetime.now().isoformat(),
    }
