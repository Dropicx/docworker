import logging
import os
import uuid
from datetime import datetime

from celery import Celery
from fastapi import Request, APIRouter, Depends, File, HTTPException, UploadFile
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.permissions import get_current_user_optional
from app.database.connection import get_session
from app.database.modular_pipeline_models import PipelineJobDB, StepExecutionStatus
from app.database.auth_models import UserDB
from app.models.document import DocumentType, ProcessingStatus, UploadResponse
from app.services.file_validator import FileValidator

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiting für Upload (disabled in test/development)
limiter = Limiter(
    key_func=get_remote_address,
    enabled=os.getenv("ENVIRONMENT") not in ["test", "development"],
)


@router.post("/upload", response_model=UploadResponse)
@limiter.limit("5/minute")  # Maximal 5 Uploads pro Minute (disabled in test/development)
async def upload_document(
    request: Request,
    file: UploadFile = File(..., description="Medizinisches Dokument (PDF, JPG, PNG)"),
    db: Session = Depends(get_session),
    current_user: UserDB | None = Depends(get_current_user_optional),  # Optional user tracking
):
    # Log upload request
    upload_log = f"📤 Upload request: {file.filename} ({file.content_type})"
    print(upload_log, flush=True)
    logger.info(upload_log)
    """
    Lädt ein medizinisches Dokument hoch und startet die Verarbeitung

    - **file**: Medizinisches Dokument (PDF, JPG, PNG)
    - **max_size**: 50MB (für Handyfotos optimiert)
    - **formats**: PDF, JPEG, PNG
    - **OCR**: Automatische Texterkennung für gescannte Dokumente
    """

    try:
        logger.debug(
            f"🔍 Upload-Request erhalten: {file.filename}, Content-Type: {file.content_type}"
        )

        # Grundlegende Validierung
        if not file.filename:
            logger.error("❌ Dateiname fehlt!")
            raise HTTPException(status_code=400, detail="Dateiname fehlt")

        # Dateivalidierung
        logger.debug(f"🔍 Validiere Datei: {file.filename}")
        is_valid, error_message = await FileValidator.validate_file(file)
        if not is_valid:
            logger.error(f"❌ Dateivalidierung fehlgeschlagen: {error_message}")
            raise HTTPException(
                status_code=400, detail=f"Dateivalidierung fehlgeschlagen: {error_message}"
            ) from e

        # Worker-Verfügbarkeit prüfen (skip in test/development environment)
        skip_worker_check = os.getenv("ENVIRONMENT") in ["test", "development"]
        if not skip_worker_check:
            logger.debug("🔍 Prüfe Worker-Verfügbarkeit...")
            try:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                celery_app = Celery(broker=redis_url, backend=redis_url)

                # Check worker availability directly
                inspect = celery_app.control.inspect(timeout=1.0)
                active_workers = inspect.active()

                if not active_workers:
                    logger.error("❌ Keine Worker verfügbar")
                    raise HTTPException(
                        status_code=503,
                        detail="Service temporarily unavailable: No workers available to process document. Please try again later.",
                    ) from e

                worker_count = len(active_workers)
                logger.info(f"✅ Worker verfügbar: {worker_count} aktive Worker")
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"⚠️ Worker-Check fehlgeschlagen (Upload wird fortgesetzt): {str(e)}")
                # Continue with upload even if worker check fails (might be temporary issue)
        else:
            logger.debug("⏭️ Worker-Check übersprungen (Test/Development-Modus)")

        # Eindeutige IDs generieren
        processing_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())

        # Dateityp bestimmen
        file_type_str = FileValidator.get_file_type(file.filename)
        file_type = DocumentType.PDF if file_type_str == "pdf" else DocumentType.IMAGE

        # Dateiinhalt lesen
        file_content = await file.read()
        file_size = len(file_content)

        # Pipeline-Konfiguration laden (für Job-Snapshot)
        from app.services.modular_pipeline_executor import ModularPipelineExecutor

        executor = ModularPipelineExecutor(db)

        # Lade aktuelle Pipeline- und OCR-Konfiguration
        pipeline_steps_list = executor.load_pipeline_steps()
        ocr_config_obj = executor.load_ocr_configuration()

        # Serialize für JSON-Speicherung
        pipeline_config = [
            {
                "id": step.id,
                "name": step.name,
                "order": step.order,
                "enabled": step.enabled,
                "prompt_template": step.prompt_template,
                "selected_model_id": step.selected_model_id,
                "document_class_id": step.document_class_id,
                "is_branching_step": step.is_branching_step,
                "branching_field": step.branching_field,
            }
            for step in pipeline_steps_list
        ]

        ocr_config = {
            "selected_engine": str(ocr_config_obj.selected_engine)
            if ocr_config_obj
            else "PADDLEOCR",
            "paddleocr_config": ocr_config_obj.paddleocr_config if ocr_config_obj else {},
            "vision_llm_config": ocr_config_obj.vision_llm_config if ocr_config_obj else {},
        }

        # Erstelle Pipeline-Job in der Datenbank
        pipeline_job = PipelineJobDB(
            job_id=job_id,
            processing_id=processing_id,
            filename=file.filename,
            file_type=file_type_str,
            file_size=file_size,
            file_content=file_content,
            client_ip=get_remote_address(request),
            status=StepExecutionStatus.PENDING,
            progress_percent=0,
            started_at=datetime.now(),  # Track when user initiates processing
            pipeline_config=pipeline_config,  # Snapshot der Pipeline-Konfiguration
            ocr_config=ocr_config,  # Snapshot der OCR-Konfiguration
            user_id=current_user.id if current_user else None,  # Track user if authenticated
        )

        db.add(pipeline_job)
        db.commit()
        db.refresh(pipeline_job)

        # NOTE: Worker is NOT enqueued here anymore!
        # It will be enqueued when frontend calls /process/{id} with options (target_language, etc.)
        # This allows frontend to set language selection BEFORE processing starts
        logger.info(
            f"📝 Job created and ready: {job_id[:8]} (status: PENDING, waiting for /process call)"
        )

        # Response erstellen
        response = UploadResponse(
            processing_id=processing_id,
            filename=file.filename,
            file_type=file_type,
            file_size=file_size,
            status=ProcessingStatus.PENDING,
            message="Datei erfolgreich hochgeladen und in Warteschlange eingereiht",
        )

        success_log = (
            f"📄 Datei hochgeladen: {file.filename} ({file_size} bytes) - ID: {processing_id[:8]}"
        )
        print(success_log, flush=True)
        logger.info(success_log)

        return response

    except HTTPException:
        raise
    except Exception as e:
        error_log = f"❌ Upload-Fehler: {e}"
        print(error_log, flush=True)
        logger.error(error_log)
        raise HTTPException(
            status_code=500, detail=f"Interner Server-Fehler beim Upload: {str(e)}"
        ) from e


@router.delete("/upload/{processing_id}")
@limiter.limit("10/minute")
async def cancel_processing(request: Request, processing_id: str):
    """
    Bricht die Verarbeitung ab und löscht alle zugehörigen Daten

    - **processing_id**: ID der zu stornierenden Verarbeitung
    """

    try:
        from app.services.cleanup import get_from_processing_store, remove_from_processing_store

        # Verarbeitung finden
        processing_data = get_from_processing_store(processing_id)

        if not processing_data:
            raise HTTPException(status_code=404, detail="Verarbeitung nicht gefunden")

        # Verarbeitung stoppen und Daten löschen
        remove_from_processing_store(processing_id)

        cancel_log = f"🚫 Verarbeitung abgebrochen: {processing_id[:8]}"
        print(cancel_log, flush=True)
        logger.info(cancel_log)

        return {"message": "Verarbeitung erfolgreich abgebrochen", "processing_id": processing_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Abbruch-Fehler: {e}")
        raise HTTPException(
            status_code=500, detail=f"Fehler beim Abbrechen der Verarbeitung: {str(e)}"
        ) from e


@router.get("/upload/limits")
async def get_upload_limits():
    """
    Gibt die aktuellen Upload-Limits und -Regeln zurück
    """

    return {
        "max_file_size_mb": 50,
        "allowed_formats": ["PDF", "JPG", "JPEG", "PNG"],
        "rate_limit": "5 uploads per minute",
        "max_pages_pdf": 50,
        "min_image_size": "100x100 pixels",
        "max_image_size": "8000x8000 pixels",
        "processing_timeout_minutes": 30,
        "ocr_supported": True,
        "ocr_languages": ["German", "English"],
    }


@router.get("/upload/health")
async def upload_health_check():
    """
    Überprüft die Gesundheit des Upload-Systems
    """

    try:
        from app.services.cleanup import get_memory_usage, processing_store

        memory_info = get_memory_usage()
        active_uploads = len(processing_store)

        # Warnung bei hoher Speichernutzung
        memory_warning = False
        if "percent" in memory_info and memory_info["percent"] > 80:
            memory_warning = True

        status = "healthy"
        if memory_warning or active_uploads > 100:
            status = "warning"

        return {
            "status": status,
            "active_uploads": active_uploads,
            "memory_usage": memory_info,
            "warnings": {"high_memory": memory_warning, "many_uploads": active_uploads > 100},
            "timestamp": datetime.now(),
        }

    except Exception as e:
        return {"status": "error", "error": str(e), "timestamp": datetime.now()}
