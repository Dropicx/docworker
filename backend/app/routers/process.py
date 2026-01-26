from datetime import datetime
import logging
import os
import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.dependencies import get_processing_service, get_statistics_service
from app.core.permissions import get_current_user_optional
from app.database.auth_models import UserDB
from app.models.document import (
    LANGUAGE_NAMES,
    GuidelinesResponse,
    ProcessingOptions,
    ProcessingProgress,
    SupportedLanguage,
    TranslationResult,
)
from app.services.pipeline_progress_tracker import PipelineProgressTracker
from app.services.processing_service import ProcessingService, STEP_DESCRIPTIONS
from app.services.statistics_service import StatisticsService

# Setup logging
logger = logging.getLogger(__name__)

# Authentication setup
security = HTTPBearer()


def verify_session_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """
    Verify session token for pipeline statistics access.
    Uses minimal auth from settings_auth router.
    """
    token = credentials.credentials
    # Simple token validation - check if token matches access code hash
    import hashlib

    expected_token = hashlib.sha256(
        os.getenv("SETTINGS_ACCESS_CODE", "admin123").encode()
    ).hexdigest()

    if token == expected_token:
        return True

    raise HTTPException(status_code=401, detail="Invalid or expired session token")


# ==================== TEXT EXTRACTION ====================
# NOTE: OCR and text extraction now happen in the WORKER service, not backend
# Backend delegates all document processing to the Celery worker via upload endpoint
# This eliminates OCR dependencies from backend and improves architecture separation
print("📄 Backend service initialized (OCR handled by worker)", flush=True)

router = APIRouter()
limiter = Limiter(
    key_func=get_remote_address,
    enabled=os.getenv("ENVIRONMENT") not in ["test", "development"],
)


@router.post("/process/{processing_id}")
@limiter.limit("3/minute")  # Maximal 3 Verarbeitungen pro Minute
async def start_processing(
    processing_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    options: ProcessingOptions | None = None,
    service: ProcessingService = Depends(get_processing_service),
):
    """
    Startet die Verarbeitung eines hochgeladenen Dokuments

    - **processing_id**: ID des hochgeladenen Dokuments
    - **options**: Verarbeitungsoptionen (z.B. Zielsprache)
    """
    try:
        options_dict = options.dict() if options else {}
        return service.start_processing(processing_id, options_dict)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.error(f"❌ Start-Verarbeitung Fehler: {e}")
        raise HTTPException(
            status_code=500, detail=f"Fehler beim Starten der Verarbeitung: {str(e)}"
        ) from e


@router.get("/process/{processing_id}/status", response_model=ProcessingProgress)
async def get_processing_status(
    processing_id: str, service: ProcessingService = Depends(get_processing_service)
):
    """
    Gibt den aktuellen Verarbeitungsstatus zurück (aus Datenbank)

    - **processing_id**: ID der Verarbeitung
    """
    try:
        status_dict = service.get_processing_status(processing_id)

        # Enrich with real-time step info from Redis
        tracker = PipelineProgressTracker()
        redis_progress = await tracker.get_progress(processing_id)

        if redis_progress and redis_progress.get("current_step_name"):
            status_dict["current_step_name"] = redis_progress["current_step_name"]
            status_dict["ui_stage"] = redis_progress.get("ui_stage")
            status_dict["progress_percent"] = redis_progress["progress_percent"]
            status_dict["current_step"] = STEP_DESCRIPTIONS.get(
                redis_progress["current_step_name"],
                status_dict["current_step"],
            )

        return ProcessingProgress(**status_dict)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"❌ Status-Abfrage Fehler: {e}")
        raise HTTPException(
            status_code=500, detail=f"Fehler beim Abrufen des Status: {str(e)}"
        ) from e


@router.get("/process/{processing_id}/result", response_model=TranslationResult)
async def get_processing_result(
    processing_id: str,
    current_user: UserDB | None = Depends(get_current_user_optional),
    service: ProcessingService = Depends(get_processing_service),
):
    """
    Gibt das Verarbeitungsergebnis zurück (aus Datenbank)

    - **processing_id**: ID der Verarbeitung

    Note: Original text is only returned for authenticated admin users.
    Non-admin users receive a placeholder message instead.
    """
    try:
        result_data = service.get_processing_result(processing_id)

        # Hide original text for non-admin users (security measure)
        is_admin = current_user and current_user.role == "admin"
        if not is_admin:
            result_data["original_text"] = "[Nur für Administratoren sichtbar]"

        return TranslationResult(**result_data)

    except ValueError as e:
        # Service raises ValueError for both not-found and not-completed
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        logger.error(f"❌ Ergebnis-Abfrage Fehler: {e}")
        raise HTTPException(
            status_code=500, detail=f"Fehler beim Abrufen des Ergebnisses: {str(e)}"
        ) from e


@router.get("/process/{processing_id}/guidelines", response_model=GuidelinesResponse)
async def get_guidelines(
    processing_id: str,
    target_language: str = Query(default="en", description="Target language for translation"),
    service: ProcessingService = Depends(get_processing_service),
):
    """
    Fetch AWMF guideline recommendations for a completed translation.

    This is a potentially slow operation (up to 90s) as it queries the Dify RAG service.
    Should be called asynchronously after the main result is displayed.
    """
    from app.services.dify_rag_client import DifyRAGClient

    start_time = time.time()

    # Check if Dify RAG is configured
    rag_client = DifyRAGClient()
    if not rag_client.is_enabled:
        return GuidelinesResponse(
            processing_id=processing_id,
            status="not_configured",
            error_message="AWMF Leitlinien service is not configured",
            timestamp=datetime.now(),
        )

    try:
        # Get the job to access the translated text
        result_data = service.get_processing_result(processing_id)

        # Use translated text as context for guidelines
        medical_text = result_data.get("translated_text") or result_data.get("original_text", "")
        document_type = result_data.get("document_type_detected") or "UNKNOWN"

        # Query Dify RAG for guidelines
        guidelines_text, metadata = await rag_client.query_guidelines(
            medical_text=medical_text,
            document_type=document_type,
            target_language=target_language,
            user_id=processing_id,
        )

        processing_time = time.time() - start_time

        if not guidelines_text:
            return GuidelinesResponse(
                processing_id=processing_id,
                status="not_available",
                document_type=document_type,
                target_language=target_language,
                metadata=metadata,
                error_message=metadata.get("reason", "No guidelines found"),
                processing_time_seconds=processing_time,
                timestamp=datetime.now(),
            )

        # Return successful response with formatted bilingual text
        return GuidelinesResponse(
            processing_id=processing_id,
            status="success",
            guidelines_text=guidelines_text,
            target_language=target_language,
            document_type=document_type,
            metadata=metadata,
            processing_time_seconds=processing_time,
            timestamp=datetime.now(),
        )

    except ValueError as e:
        # Job not found or not completed
        return GuidelinesResponse(
            processing_id=processing_id,
            status="error",
            error_message=str(e),
            processing_time_seconds=time.time() - start_time,
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error(f"Guidelines fetch failed for {processing_id}: {e}")
        return GuidelinesResponse(
            processing_id=processing_id,
            status="error",
            error_message=f"Failed to fetch guidelines: {str(e)[:100]}",
            processing_time_seconds=time.time() - start_time,
            timestamp=datetime.now(),
        )


@router.get("/process/active")
@limiter.limit("30/minute")
async def get_active_processes(
    request: Request, service: ProcessingService = Depends(get_processing_service)
):
    """
    Gibt Übersicht über aktive Verarbeitungen zurück (für Debugging)
    """
    try:
        return service.get_active_processes()
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now()}


# Global optimized pipeline instance removed - now using unified system


@router.get("/process/pipeline-stats")
async def get_pipeline_stats(
    authenticated: bool = Depends(verify_session_token),
    service: StatisticsService = Depends(get_statistics_service),
):
    """
    Get comprehensive pipeline performance statistics from actual database data
    Requires authentication via settings session token.
    """
    if not authenticated:
        raise HTTPException(
            status_code=401, detail="Authentication required to access pipeline statistics"
        )

    try:
        return service.get_pipeline_statistics()
    except Exception as e:
        logger.error(f"Failed to get pipeline statistics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve pipeline statistics: {str(e)}"
        ) from e


@router.post("/process/clear-cache")
async def clear_pipeline_cache(service: StatisticsService = Depends(get_statistics_service)):
    """
    Clear the pipeline prompt cache (unified system)
    """
    try:
        return service.clear_cache()
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now()}


@router.get("/process/performance-comparison")
async def get_performance_comparison(service: StatisticsService = Depends(get_statistics_service)):
    """
    Get performance comparison between optimized and legacy pipeline
    """
    return service.get_performance_comparison()


@router.get("/process/models")
async def get_available_models():
    """
    Gibt verfügbare OVH-Modelle zurück
    """

    # OVH verwendet feste Modelle die in den Umgebungsvariablen konfiguriert sind
    return {
        "connected": True,
        "models": [
            os.getenv("OVH_MAIN_MODEL", "Meta-Llama-3_3-70B-Instruct"),
            os.getenv("OVH_PREPROCESSING_MODEL", "Mistral-Nemo-Instruct-2407"),
            os.getenv("OVH_TRANSLATION_MODEL", "Meta-Llama-3_3-70B-Instruct"),
        ],
        "recommended": os.getenv("OVH_MAIN_MODEL", "Meta-Llama-3_3-70B-Instruct"),
        "api_mode": "OVH AI Endpoints",
        "timestamp": datetime.now(),
    }


@router.get("/process/languages")
async def get_available_languages():
    """
    Gibt verfügbare Sprachen für die Übersetzung zurück
    """

    try:
        # Sehr gut unterstützte Sprachen (beste Llama 3.3 Performance)
        best_supported = [
            SupportedLanguage.ENGLISH,
            SupportedLanguage.GERMAN,
            SupportedLanguage.FRENCH,
            SupportedLanguage.SPANISH,
            SupportedLanguage.ITALIAN,
            SupportedLanguage.PORTUGUESE,
            SupportedLanguage.DUTCH,
        ]

        # Gut unterstützte Sprachen
        well_supported = [
            SupportedLanguage.RUSSIAN,
            SupportedLanguage.CHINESE_SIMPLIFIED,
            SupportedLanguage.CHINESE_TRADITIONAL,
            SupportedLanguage.JAPANESE,
            SupportedLanguage.KOREAN,
            SupportedLanguage.ARABIC,
            SupportedLanguage.HINDI,
            SupportedLanguage.POLISH,
            SupportedLanguage.CZECH,
            SupportedLanguage.SWEDISH,
            SupportedLanguage.NORWEGIAN,
            SupportedLanguage.DANISH,
        ]

        # Alle verfügbaren Sprachen
        all_languages = []

        # Zuerst sehr gut unterstützte Sprachen
        for lang in best_supported:
            all_languages.append(
                {
                    "code": lang.value,
                    "name": LANGUAGE_NAMES[lang],
                    "popular": True,
                    "quality": "excellent",
                }
            )

        # Dann gut unterstützte Sprachen
        for lang in well_supported:
            all_languages.append(
                {
                    "code": lang.value,
                    "name": LANGUAGE_NAMES[lang],
                    "popular": False,
                    "quality": "good",
                }
            )

        return {
            "languages": all_languages,
            "total_count": len(all_languages),
            "best_supported_count": len(best_supported),
            "well_supported_count": len(well_supported),
            "timestamp": datetime.now(),
        }

    except Exception as e:
        return {"error": str(e), "languages": [], "timestamp": datetime.now()}
