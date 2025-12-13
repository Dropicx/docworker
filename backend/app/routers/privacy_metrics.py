"""Privacy Filter Metrics API Router.

Issue #35 Phase 6.3: Production Monitoring
Provides endpoints for monitoring PII detection performance and statistics.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.privacy_filter_advanced import AdvancedPrivacyFilter


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


# ==================== CACHED FILTER INSTANCE ====================

# Singleton filter instance for metrics (avoid repeated initialization)
_filter_instance: Optional[AdvancedPrivacyFilter] = None


def get_filter() -> AdvancedPrivacyFilter:
    """Get or create the privacy filter instance."""
    global _filter_instance
    if _filter_instance is None:
        _filter_instance = AdvancedPrivacyFilter(load_custom_terms=False)
    return _filter_instance


# ==================== ENDPOINTS ====================


@router.get("/metrics", response_model=PrivacyMetricsResponse)
async def get_privacy_metrics():
    """Get privacy filter capabilities and detection statistics.

    Returns comprehensive information about the privacy filter's:
    - NER availability and configuration
    - Number of PII types supported
    - Medical term protection counts
    - Drug database size
    - Performance targets
    """
    try:
        filter_instance = get_filter()

        # List of PII types we detect
        pii_types = [
            "birthdate",
            "patient_name",
            "street_address",
            "postal_code_city",
            "phone_number",
            "mobile_phone",
            "fax_number",
            "email_address",
            "insurance_number",
            "insurance_policy",
            "patient_id",
            "hospital_id",
            "tax_id",
            "social_security_number",
            "passport_number",
            "id_card_number",
            "gender",
            "url",
            "salutation",
        ]

        return PrivacyMetricsResponse(
            timestamp=datetime.now().isoformat(),
            filter_capabilities=FilterCapabilities(
                has_ner=filter_instance.has_ner,
                spacy_model="de_core_news_sm" if filter_instance.has_ner else "none",
                removal_method="AdvancedPrivacyFilter_Phase5",
                custom_terms_loaded=filter_instance._custom_terms_loaded,
            ),
            detection_stats=DetectionStats(
                pii_types_supported=pii_types,
                pii_types_count=len(pii_types),
                medical_terms_count=len(filter_instance.medical_terms),
                drug_database_count=len(filter_instance.drug_database),
                abbreviations_count=len(filter_instance.protected_abbreviations),
                eponyms_count=len(filter_instance.medical_eponyms),
                loinc_codes_count=len(filter_instance.common_loinc_codes),
            ),
            performance_target_ms=100,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.post("/test", response_model=LiveTestResult)
async def test_privacy_filter(request: LiveTestRequest):
    """Live test the privacy filter with custom text.

    Processes the provided text and returns:
    - Processing time
    - PII types detected
    - Quality score
    - Review recommendations

    This endpoint is useful for:
    - Testing PII detection on sample documents
    - Validating filter behavior
    - Performance testing

    Note: The input text is NOT stored or logged.
    """
    if not request.text:
        raise HTTPException(status_code=400, detail="Text is required")

    if len(request.text) > 50000:
        raise HTTPException(status_code=400, detail="Text too long (max 50000 chars)")

    try:
        import time
        filter_instance = get_filter()

        start = time.perf_counter()
        cleaned_text, metadata = filter_instance.remove_pii(request.text)
        processing_time_ms = (time.perf_counter() - start) * 1000

        quality_summary = metadata.get("quality_summary", {})

        return LiveTestResult(
            input_length=len(request.text),
            output_length=len(cleaned_text),
            cleaned_text=cleaned_text,
            processing_time_ms=round(processing_time_ms, 2),
            pii_types_detected=metadata.get("pii_types_detected", []),
            entities_detected=metadata.get("entities_detected", 0),
            quality_score=quality_summary.get("quality_score", 100.0),
            review_recommended=metadata.get("review_recommended", False),
            passes_performance_target=processing_time_ms < 100,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/health")
async def privacy_filter_health():
    """Check privacy filter health and readiness.

    Returns:
    - Filter initialization status
    - NER model availability
    - Medical term database status
    """
    try:
        filter_instance = get_filter()

        return {
            "status": "healthy",
            "filter_ready": True,
            "ner_available": filter_instance.has_ner,
            "medical_terms_loaded": len(filter_instance.medical_terms) > 0,
            "drug_database_loaded": len(filter_instance.drug_database) > 0,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "filter_ready": False,
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
