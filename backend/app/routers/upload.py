import uuid
import time
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

from app.models.document import UploadResponse, ProcessingStatus, DocumentType, ErrorResponse
from app.services.file_validator import FileValidator
from app.services.cleanup import add_to_processing_store

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
        
        # Eindeutige Verarbeitungs-ID generieren
        processing_id = str(uuid.uuid4())
        
        # Dateityp bestimmen
        file_type_str = FileValidator.get_file_type(file.filename)
        file_type = DocumentType.PDF if file_type_str == "pdf" else DocumentType.IMAGE
        
        # Dateiinhalt lesen
        file_content = await file.read()
        file_size = len(file_content)
        
        # Daten im Processing Store speichern
        processing_data = {
            "filename": file.filename,
            "file_type": file_type_str,
            "file_size": file_size,
            "file_content": file_content,
            "status": ProcessingStatus.PENDING,
            "progress_percent": 0,
            "current_step": "Upload abgeschlossen",
            "uploaded_at": datetime.now(),
            "client_ip": get_remote_address(request)
        }
        
        add_to_processing_store(processing_id, processing_data)
        
        # Response erstellen
        response = UploadResponse(
            processing_id=processing_id,
            filename=file.filename,
            file_type=file_type,
            file_size=file_size,
            status=ProcessingStatus.PENDING,
            message="Datei erfolgreich hochgeladen und zur Verarbeitung bereit"
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