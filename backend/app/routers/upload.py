import uuid
import time
import logging
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

from app.models.document import UploadResponse, ProcessingStatus, DocumentType, ErrorResponse
from app.services.file_validator import FileValidator
from app.database.connection import get_db_session
from app.database.modular_pipeline_models import PipelineJobDB, StepExecutionStatus

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiting für Upload
limiter = Limiter(key_func=get_remote_address)

@router.post("/upload", response_model=UploadResponse)
@limiter.limit("5/minute")  # Maximal 5 Uploads pro Minute
async def upload_document(
    request: Request,
    file: UploadFile = File(..., description="Medizinisches Dokument (PDF, JPG, PNG)")
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
        logger.debug(f"🔍 Upload-Request erhalten: {file.filename}, Content-Type: {file.content_type}")
        
        # Grundlegende Validierung
        if not file.filename:
            logger.error(f"❌ Dateiname fehlt!")
            raise HTTPException(
                status_code=400,
                detail="Dateiname fehlt"
            )
        
        # Dateivalidierung
        logger.debug(f"🔍 Validiere Datei: {file.filename}")
        is_valid, error_message = await FileValidator.validate_file(file)
        if not is_valid:
            logger.error(f"❌ Dateivalidierung fehlgeschlagen: {error_message}")
            raise HTTPException(
                status_code=400,
                detail=f"Dateivalidierung fehlgeschlagen: {error_message}"
            )
        
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
        db = next(get_db_session())
        try:
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
                    "branching_field": step.branching_field
                }
                for step in pipeline_steps_list
            ]

            ocr_config = {
                "selected_engine": str(ocr_config_obj.selected_engine) if ocr_config_obj else "TESSERACT",
                "tesseract_config": ocr_config_obj.tesseract_config if ocr_config_obj else {},
                "paddleocr_config": ocr_config_obj.paddleocr_config if ocr_config_obj else {},
                "vision_llm_config": ocr_config_obj.vision_llm_config if ocr_config_obj else {}
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
                pipeline_config=pipeline_steps,  # Snapshot der Pipeline-Konfiguration
                ocr_config=ocr_config  # Snapshot der OCR-Konfiguration
            )

            db.add(pipeline_job)
            db.commit()
            db.refresh(pipeline_job)

            # Queue Celery task (nur wenn nicht im Test-Modus)
            try:
                from worker.tasks.document_processing import process_medical_document
                process_medical_document.delay(processing_id, options={})
                logger.info(f"📤 Job queued to Redis: {job_id[:8]}")
            except Exception as queue_error:
                logger.warning(f"⚠️ Failed to queue Celery task (running without worker?): {queue_error}")
                # Job bleibt in DB als PENDING, kann später verarbeitet werden

        finally:
            db.close()
        
        # Response erstellen
        response = UploadResponse(
            processing_id=processing_id,
            filename=file.filename,
            file_type=file_type,
            file_size=file_size,
            status=ProcessingStatus.PENDING,
            message="Datei erfolgreich hochgeladen und in Warteschlange eingereiht"
        )
        
        success_log = f"📄 Datei hochgeladen: {file.filename} ({file_size} bytes) - ID: {processing_id[:8]}"
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
            status_code=500,
            detail=f"Interner Server-Fehler beim Upload: {str(e)}"
        )

@router.delete("/upload/{processing_id}")
@limiter.limit("10/minute")
async def cancel_processing(
    request: Request,
    processing_id: str
):
    """
    Bricht die Verarbeitung ab und löscht alle zugehörigen Daten
    
    - **processing_id**: ID der zu stornierenden Verarbeitung
    """
    
    try:
        from app.services.cleanup import get_from_processing_store, remove_from_processing_store
        
        # Verarbeitung finden
        processing_data = get_from_processing_store(processing_id)
        
        if not processing_data:
            raise HTTPException(
                status_code=404,
                detail="Verarbeitung nicht gefunden"
            )
        
        # Verarbeitung stoppen und Daten löschen
        remove_from_processing_store(processing_id)
        
        cancel_log = f"🚫 Verarbeitung abgebrochen: {processing_id[:8]}"
        print(cancel_log, flush=True)
        logger.info(cancel_log)
        
        return {
            "message": "Verarbeitung erfolgreich abgebrochen",
            "processing_id": processing_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Abbruch-Fehler: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Abbrechen der Verarbeitung: {str(e)}"
        )

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
        "ocr_languages": ["German", "English"]
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
            "warnings": {
                "high_memory": memory_warning,
                "many_uploads": active_uploads > 100
            },
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now()
        } 