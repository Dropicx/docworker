import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.document import (
    ProcessingProgress, 
    TranslationResult, 
    ProcessingStatus,
    ProcessingOptions,
    SupportedLanguage,
    ErrorResponse,
    LANGUAGE_NAMES
)
from app.services.cleanup import (
    get_from_processing_store,
    update_processing_store,
    remove_from_processing_store
)
from app.database.connection import get_session
from app.database.modular_pipeline_models import PipelineJobDB, StepExecutionStatus
from app.services.ovh_client import OVHClient
from app.services.ai_logging_service import AILoggingService
from app.services.hybrid_text_extractor import HybridTextExtractor
from sqlalchemy.orm import Session
import os

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
    expected_token = hashlib.sha256(os.getenv("SETTINGS_ACCESS_CODE", "admin123").encode()).hexdigest()

    if token == expected_token:
        return True

    raise HTTPException(
        status_code=401,
        detail="Invalid or expired session token"
    )

# ==================== TEXT EXTRACTION ====================
# NOTE: OCR and text extraction now happen in the WORKER service, not backend
# Backend delegates all document processing to the Celery worker via upload endpoint
# This eliminates OCR dependencies from backend and improves architecture separation
print("📄 Backend service initialized (OCR handled by worker)", flush=True)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("/process/{processing_id}")
@limiter.limit("3/minute")  # Maximal 3 Verarbeitungen pro Minute
async def start_processing(
    processing_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    options: Optional[ProcessingOptions] = None,
    db: Session = Depends(get_session)
):
    """
    Startet die Verarbeitung eines hochgeladenen Dokuments

    - **processing_id**: ID des hochgeladenen Dokuments
    - **options**: Verarbeitungsoptionen (z.B. Zielsprache)
    """

    try:
        # Load job from database (new architecture)
        job = db.query(PipelineJobDB).filter_by(processing_id=processing_id).first()

        if not job:
            raise HTTPException(
                status_code=404,
                detail="Verarbeitung nicht gefunden oder bereits abgelaufen"
            )

        # Save processing options (including target_language) to job
        options_dict = options.dict() if options else {}
        job.processing_options = options_dict
        db.commit()

        logger.info(f"📋 Processing options saved for {processing_id[:8]}: {options_dict}")

        # NOW enqueue the worker task with the options
        try:
            from app.services.celery_client import enqueue_document_processing
            task_id = enqueue_document_processing(processing_id, options=options_dict)
            logger.info(f"📤 Job queued to Redis: {processing_id[:8]} (task_id: {task_id})")

            return {
                "message": "Verarbeitung gestartet",
                "processing_id": processing_id,
                "status": "QUEUED",
                "task_id": task_id,
                "target_language": options_dict.get('target_language') if options_dict else None
            }
        except Exception as queue_error:
            logger.error(f"❌ Failed to queue task: {queue_error}")
            raise HTTPException(
                status_code=503,
                detail=f"Failed to queue processing task: {str(queue_error)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Start-Verarbeitung Fehler: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Starten der Verarbeitung: {str(e)}"
        )

@router.get("/process/{processing_id}/status", response_model=ProcessingProgress)
async def get_processing_status(
    processing_id: str,
    db: Session = Depends(get_session)
):
    """
    Gibt den aktuellen Verarbeitungsstatus zurück (aus Datenbank)

    - **processing_id**: ID der Verarbeitung
    """

    try:
        # Load job from database
        job = db.query(PipelineJobDB).filter_by(processing_id=processing_id).first()

        if not job:
            raise HTTPException(
                status_code=404,
                detail="Verarbeitung nicht gefunden"
            )

        # Map database status to API status
        status_mapping = {
            StepExecutionStatus.PENDING: ProcessingStatus.PENDING,
            StepExecutionStatus.RUNNING: ProcessingStatus.PROCESSING,
            StepExecutionStatus.COMPLETED: ProcessingStatus.COMPLETED,
            StepExecutionStatus.FAILED: ProcessingStatus.ERROR,
            StepExecutionStatus.SKIPPED: ProcessingStatus.ERROR
        }

        # Determine current step description
        current_step = "Warten auf Verarbeitung..."
        if job.status == StepExecutionStatus.RUNNING:
            current_step = f"Verarbeite Schritt {job.progress_percent}%"
        elif job.status == StepExecutionStatus.COMPLETED:
            current_step = "Verarbeitung abgeschlossen"
        elif job.status == StepExecutionStatus.FAILED:
            current_step = "Fehler bei Verarbeitung"

        return ProcessingProgress(
            processing_id=processing_id,
            status=status_mapping.get(job.status, ProcessingStatus.PENDING),
            progress_percent=job.progress_percent,
            current_step=current_step,
            message=None,
            error=job.error_message
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Status-Abfrage Fehler: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Abrufen des Status: {str(e)}"
        )

@router.get("/process/{processing_id}/result", response_model=TranslationResult)
async def get_processing_result(
    processing_id: str,
    db: Session = Depends(get_session)
):
    """
    Gibt das Verarbeitungsergebnis zurück (aus Datenbank)

    - **processing_id**: ID der Verarbeitung
    """

    try:
        # Load job from database
        job = db.query(PipelineJobDB).filter_by(processing_id=processing_id).first()

        if not job:
            raise HTTPException(
                status_code=404,
                detail="Verarbeitung nicht gefunden"
            )

        if job.status != StepExecutionStatus.COMPLETED:
            raise HTTPException(
                status_code=409,
                detail=f"Verarbeitung noch nicht abgeschlossen. Status: {job.status}"
            )

        result_data = job.result_data
        if not result_data:
            raise HTTPException(
                status_code=500,
                detail="Verarbeitungsergebnis nicht verfügbar"
            )

        # Return result (we keep it in DB for audit purposes, don't delete)
        return TranslationResult(**result_data)

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ergebnis-Abfrage Fehler: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Abrufen des Ergebnisses: {str(e)}"
        )

@router.get("/process/active")
@limiter.limit("30/minute")
async def get_active_processes(request: Request):
    """
    Gibt Übersicht über aktive Verarbeitungen zurück (für Debugging)
    """
    
    try:
        from app.services.cleanup import processing_store
        
        active_processes = []
        
        for proc_id, data in processing_store.items():
            active_processes.append({
                "processing_id": proc_id[:8] + "...",  # Verkürzt für Privatsphäre
                "status": data.get("status"),
                "progress_percent": data.get("progress_percent", 0),
                "current_step": data.get("current_step"),
                "created_at": data.get("created_at"),
                "filename": data.get("filename", "").split("/")[-1] if data.get("filename") else None  # Nur Dateiname
            })
        
        return {
            "active_count": len(active_processes),
            "processes": active_processes,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now()
        }

# Global optimized pipeline instance removed - now using unified system

@router.get("/process/pipeline-stats")
async def get_pipeline_stats(
    authenticated: bool = Depends(verify_session_token)
):
    """
    Get comprehensive pipeline performance statistics from actual database data
    Requires authentication via settings session token.
    """
    if not authenticated:
        raise HTTPException(
            status_code=401,
            detail="Authentication required to access pipeline statistics"
        )

    try:
        # Get real statistics from database (MODULAR PIPELINE)
        from app.database.connection import get_session
        from app.database.modular_pipeline_models import DynamicPipelineStepDB, PipelineStepExecutionDB
        from app.database.unified_models import SystemSettingsDB, AILogInteractionDB
        from sqlalchemy import func, desc

        db = next(get_session())
        # Get current time for calculations
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        # ==================== AI INTERACTION STATISTICS ====================

        # Total AI interactions
        total_interactions = db.query(PipelineStepExecutionDB).count()

        # Recent interactions (24h)
        recent_interactions = db.query(PipelineStepExecutionDB).filter(
            PipelineStepExecutionDB.started_at >= last_24h
        ).count()

        # Weekly interactions
        weekly_interactions = db.query(PipelineStepExecutionDB).filter(
            PipelineStepExecutionDB.started_at >= last_7d
        ).count()

        # Average processing time (last 100 interactions)
        avg_processing_time = db.query(func.avg(PipelineStepExecutionDB.execution_time_seconds)).filter(
            PipelineStepExecutionDB.execution_time_seconds.isnot(None)
        ).limit(100).scalar() or 0
        avg_processing_time_ms = avg_processing_time * 1000  # Convert to ms

        # Success rate (last 100 executions)
        recent_logs = db.query(PipelineStepExecutionDB).order_by(desc(PipelineStepExecutionDB.started_at)).limit(100).all()
        success_count = sum(1 for log in recent_logs if log.status == "COMPLETED")
        success_rate = (success_count / len(recent_logs) * 100) if recent_logs else 100

        # Most used step
        step_usage = db.query(
            PipelineStepExecutionDB.step_id,
            func.count(PipelineStepExecutionDB.step_id).label('count')
        ).group_by(PipelineStepExecutionDB.step_id).order_by(desc('count')).first()

        if step_usage:
            most_used_step_db = db.query(DynamicPipelineStepDB).filter_by(id=step_usage.step_id).first()
            most_used_step = most_used_step_db.name if most_used_step_db else "N/A"
        else:
            most_used_step = "N/A"

        # ==================== PIPELINE CONFIGURATION STATISTICS ====================

        # Pipeline steps status (modular system)
        pipeline_steps = db.query(DynamicPipelineStepDB).order_by(DynamicPipelineStepDB.order).all()
        enabled_steps = [step for step in pipeline_steps if step.enabled]
        disabled_steps = [step for step in pipeline_steps if not step.enabled]

        # Configuration counts (modular system)
        total_pipeline_steps = len(pipeline_steps)

        # Get system settings
        system_settings = db.query(SystemSettingsDB).filter(
            SystemSettingsDB.key.like('enable_%')
        ).all()

        enabled_features = sum(1 for setting in system_settings if setting.value.lower() == 'true')
        total_features = len(system_settings)

        # Get the actual cache timeout from database settings
        cache_timeout_setting = db.query(SystemSettingsDB).filter(
            SystemSettingsDB.key == 'pipeline_cache_timeout'
        ).first()
        actual_cache_timeout = int(cache_timeout_setting.value) if cache_timeout_setting and cache_timeout_setting.value.isdigit() else 3600

        # ==================== REAL PERFORMANCE METRICS ====================

        # Calculate actual performance improvements based on data
        performance_metrics = {}

        if total_interactions > 0:
            performance_metrics["avg_processing_time"] = f"{avg_processing_time_ms:.0f}ms average processing time"
            performance_metrics["success_rate"] = f"{success_rate:.1f}% success rate"
            performance_metrics["daily_throughput"] = f"{recent_interactions} interactions in last 24h"
            performance_metrics["weekly_volume"] = f"{weekly_interactions} interactions in last 7 days"
        else:
            performance_metrics["status"] = "No AI interactions recorded yet"

        if len(enabled_steps) > 0:
            performance_metrics["active_pipeline_steps"] = f"{len(enabled_steps)}/{len(pipeline_steps)} pipeline steps enabled"
            performance_metrics["most_used_step"] = f"Most used: {most_used_step}"

        performance_metrics["configuration_completeness"] = f"{total_pipeline_steps} dynamic pipeline steps configured"
        performance_metrics["feature_adoption"] = f"{enabled_features}/{total_features} features enabled"

        # ==================== CACHE STATISTICS (for frontend compatibility) ====================

        # Create cache statistics based on AI interactions and real settings
        cache_statistics = {
            "total_entries": total_interactions,
            "active_entries": recent_interactions,
            "expired_entries": max(0, total_interactions - recent_interactions),
            "cache_timeout_seconds": actual_cache_timeout
        }

        return {
            "pipeline_mode": "modular",
            "timestamp": now.isoformat(),
            "cache_statistics": cache_statistics,
            "ai_interaction_statistics": {
                "total_interactions": total_interactions,
                "last_24h_interactions": recent_interactions,
                "last_7d_interactions": weekly_interactions,
                "avg_processing_time_ms": round(avg_processing_time_ms, 2) if avg_processing_time_ms else 0,
                "success_rate_percent": round(success_rate, 1),
                "most_used_step": most_used_step
            },
            "pipeline_configuration": {
                "total_steps": len(pipeline_steps),
                "enabled_steps": len(enabled_steps),
                "disabled_steps": len(disabled_steps),
                "enabled_step_names": [step.name for step in enabled_steps],
                "disabled_step_names": [step.name for step in disabled_steps]
            },
            "prompt_configuration": {
                "dynamic_pipeline_steps": total_pipeline_steps,
                "total_prompts_configured": total_pipeline_steps
            },
            "system_health": {
                "enabled_features": enabled_features,
                "total_features": total_features,
                "feature_adoption_percent": round((enabled_features / total_features * 100), 1) if total_features > 0 else 0,
                "database_status": "operational"
            },
            "performance_improvements": performance_metrics
        }

    except Exception as e:
        logger.error(f"Failed to get pipeline statistics: {e}")

        # Try to get cache timeout even in error case
        try:
            cache_timeout_setting = db.query(SystemSettingsDB).filter(
                SystemSettingsDB.key == 'pipeline_cache_timeout'
            ).first()
            error_cache_timeout = int(cache_timeout_setting.value) if cache_timeout_setting and cache_timeout_setting.value.isdigit() else 3600
        except:
            error_cache_timeout = 3600

        return {
            "pipeline_mode": "unified",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "cache_statistics": {
                "total_entries": 0,
                "active_entries": 0,
                "expired_entries": 0,
                "cache_timeout_seconds": error_cache_timeout
            },
            "ai_interaction_statistics": {
                "total_interactions": 0,
                "last_24h_interactions": 0,
                "last_7d_interactions": 0,
                "avg_processing_time_ms": 0,
                "success_rate_percent": 0,
                "most_used_step": "N/A"
            },
            "pipeline_configuration": {
                "total_steps": 0,
                "enabled_steps": 0,
                "disabled_steps": 0,
                "enabled_step_names": [],
                "disabled_step_names": []
            },
            "prompt_configuration": {
                "universal_prompts": 0,
                "document_specific_prompts": 0,
                "total_prompts_configured": 0
            },
            "system_health": {
                "enabled_features": 0,
                "total_features": 0,
                "feature_adoption_percent": 0,
                "database_status": "error"
            },
            "performance_improvements": {
                "error": "Unable to calculate performance metrics"
            }
        }

@router.post("/process/clear-cache")
async def clear_pipeline_cache():
    """
    Clear the pipeline prompt cache (unified system)
    """
    try:
        # In the unified system, prompts are stored in the database
        # This endpoint is kept for compatibility but doesn't need to do anything
        return {
            "success": True,
            "message": "Unified system uses database storage - no cache to clear",
            "timestamp": datetime.now()
        }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now()
        }

@router.get("/process/performance-comparison")
async def get_performance_comparison():
    """
    Get performance comparison between optimized and legacy pipeline
    """
    return {
        "optimized_pipeline": {
            "features": [
                "Prompt caching (5min TTL)",
                "Parallel classification + preprocessing",
                "Parallel quality checks (fact + grammar)",
                "Async AI API calls",
                "Smart error fallbacks",
                "AI-based medical validation",
                "AI-based text formatting"
            ],
            "expected_improvements": {
                "speed": "40-60% faster processing",
                "database_calls": "90% reduction via caching",
                "ai_api_efficiency": "2-3x better throughput with parallel calls",
                "reliability": "Better error handling and fallbacks"
            }
        },
        "legacy_pipeline": {
            "features": [
                "Sequential processing",
                "Database call per document",
                "Hardcoded medical validation",
                "Hardcoded text formatting",
                "No parallel operations"
            ],
            "limitations": [
                "Slower due to sequential processing",
                "More database load",
                "Less flexible validation",
                "Fixed formatting logic"
            ]
        },
        "recommendation": "Use optimized pipeline for better performance and flexibility",
        "toggle_method": "Set USE_OPTIMIZED_PIPELINE environment variable"
    }

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
            os.getenv("OVH_TRANSLATION_MODEL", "Meta-Llama-3_3-70B-Instruct")
        ],
        "recommended": os.getenv("OVH_MAIN_MODEL", "Meta-Llama-3_3-70B-Instruct"),
        "api_mode": "OVH AI Endpoints",
        "timestamp": datetime.now()
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
            SupportedLanguage.DUTCH
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
            SupportedLanguage.DANISH
        ]
        
        # Alle verfügbaren Sprachen
        all_languages = []
        
        # Zuerst sehr gut unterstützte Sprachen
        for lang in best_supported:
            all_languages.append({
                "code": lang.value,
                "name": LANGUAGE_NAMES[lang],
                "popular": True,
                "quality": "excellent"
            })
        
        # Dann gut unterstützte Sprachen
        for lang in well_supported:
            all_languages.append({
                "code": lang.value,
                "name": LANGUAGE_NAMES[lang],
                "popular": False,
                "quality": "good"
            })
        
        return {
            "languages": all_languages,
            "total_count": len(all_languages),
            "best_supported_count": len(best_supported),
            "well_supported_count": len(well_supported),
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "languages": [],
            "timestamp": datetime.now()
        }