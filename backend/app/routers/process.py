import asyncio
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.document import (
    ProcessingProgress, 
    TranslationResult, 
    ProcessingStatus,
    ErrorResponse
)
from app.services.cleanup import (
    get_from_processing_store, 
    update_processing_store,
    remove_from_processing_store
)
from app.services.text_extractor import TextExtractor
from app.services.ollama_client import OllamaClient

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Service-Instanzen
text_extractor = TextExtractor()
ollama_client = OllamaClient()

@router.post("/process/{processing_id}")
@limiter.limit("3/minute")  # Maximal 3 Verarbeitungen pro Minute
async def start_processing(
    processing_id: str,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Startet die Verarbeitung eines hochgeladenen Dokuments
    
    - **processing_id**: ID des hochgeladenen Dokuments
    """
    
    try:
        # Verarbeitungsdaten abrufen
        processing_data = get_from_processing_store(processing_id)
        
        if not processing_data:
            raise HTTPException(
                status_code=404,
                detail="Verarbeitung nicht gefunden oder bereits abgelaufen"
            )
        
        # Status prüfen
        current_status = processing_data.get("status")
        if current_status == ProcessingStatus.PROCESSING:
            raise HTTPException(
                status_code=409,
                detail="Verarbeitung läuft bereits"
            )
        
        if current_status == ProcessingStatus.COMPLETED:
            raise HTTPException(
                status_code=409,
                detail="Verarbeitung bereits abgeschlossen"
            )
        
        # Verarbeitung im Hintergrund starten
        background_tasks.add_task(process_document, processing_id)
        
        # Status auf PROCESSING setzen
        update_processing_store(processing_id, {
            "status": ProcessingStatus.PROCESSING,
            "progress_percent": 10,
            "current_step": "Verarbeitung gestartet",
            "started_at": datetime.now()
        })
        
        print(f"🔄 Verarbeitung gestartet: {processing_id[:8]}")
        
        return {
            "message": "Verarbeitung gestartet",
            "processing_id": processing_id,
            "status": ProcessingStatus.PROCESSING
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Start-Verarbeitung Fehler: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Starten der Verarbeitung: {str(e)}"
        )

async def process_document(processing_id: str):
    """
    Verarbeitet Dokument im Hintergrund
    """
    try:
        processing_data = get_from_processing_store(processing_id)
        if not processing_data:
            return
        
        start_time = time.time()
        
        # Schritt 1: Textextraktion
        update_processing_store(processing_id, {
            "status": ProcessingStatus.EXTRACTING_TEXT,
            "progress_percent": 20,
            "current_step": "Text wird extrahiert..."
        })
        
        file_content = processing_data["file_content"]
        file_type = processing_data["file_type"]
        filename = processing_data["filename"]
        
        extracted_text, text_confidence = await text_extractor.extract_text(
            file_content, file_type, filename
        )
        
        if not extracted_text or len(extracted_text.strip()) < 10:
            raise Exception("Nicht genügend Text extrahiert")
        
        # Schritt 2: Text-Übersetzung
        update_processing_store(processing_id, {
            "status": ProcessingStatus.TRANSLATING,
            "progress_percent": 60,
            "current_step": "Text wird in einfache Sprache übersetzt..."
        })
        
        # Ollama-Verbindung prüfen
        if not await ollama_client.check_connection():
            raise Exception("Ollama-Dienst nicht verfügbar")
        
        translated_text, detected_doc_type, translation_confidence = await ollama_client.translate_medical_text(
            extracted_text
        )
        
        # Schritt 3: Ergebnis finalisieren
        update_processing_store(processing_id, {
            "progress_percent": 90,
            "current_step": "Ergebnis wird vorbereitet..."
        })
        
        processing_time = time.time() - start_time
        overall_confidence = (text_confidence + translation_confidence) / 2
        
        # Ergebnis speichern
        result = TranslationResult(
            processing_id=processing_id,
            original_text=extracted_text,
            translated_text=translated_text,
            document_type_detected=detected_doc_type,
            confidence_score=overall_confidence,
            processing_time_seconds=processing_time
        )
        
        update_processing_store(processing_id, {
            "status": ProcessingStatus.COMPLETED,
            "progress_percent": 100,
            "current_step": "Verarbeitung abgeschlossen",
            "result": result.dict(),
            "completed_at": datetime.now()
        })
        
        print(f"✅ Verarbeitung abgeschlossen: {processing_id[:8]} ({processing_time:.2f}s)")
        
    except Exception as e:
        print(f"❌ Verarbeitungsfehler {processing_id[:8]}: {e}")
        
        update_processing_store(processing_id, {
            "status": ProcessingStatus.ERROR,
            "current_step": "Fehler bei der Verarbeitung",
            "error": str(e),
            "error_at": datetime.now()
        })

@router.get("/process/{processing_id}/status", response_model=ProcessingProgress)
async def get_processing_status(processing_id: str):
    """
    Gibt den aktuellen Verarbeitungsstatus zurück
    
    - **processing_id**: ID der Verarbeitung
    """
    
    try:
        processing_data = get_from_processing_store(processing_id)
        
        if not processing_data:
            raise HTTPException(
                status_code=404,
                detail="Verarbeitung nicht gefunden oder bereits abgelaufen"
            )
        
        return ProcessingProgress(
            processing_id=processing_id,
            status=processing_data.get("status", ProcessingStatus.PENDING),
            progress_percent=processing_data.get("progress_percent", 0),
            current_step=processing_data.get("current_step", "Warten..."),
            message=processing_data.get("message"),
            error=processing_data.get("error")
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
async def get_processing_result(processing_id: str):
    """
    Gibt das Verarbeitungsergebnis zurück
    
    - **processing_id**: ID der Verarbeitung
    """
    
    try:
        processing_data = get_from_processing_store(processing_id)
        
        if not processing_data:
            raise HTTPException(
                status_code=404,
                detail="Verarbeitung nicht gefunden oder bereits abgelaufen"
            )
        
        status = processing_data.get("status")
        
        if status != ProcessingStatus.COMPLETED:
            raise HTTPException(
                status_code=409,
                detail=f"Verarbeitung noch nicht abgeschlossen. Status: {status}"
            )
        
        result_data = processing_data.get("result")
        if not result_data:
            raise HTTPException(
                status_code=500,
                detail="Verarbeitungsergebnis nicht verfügbar"
            )
        
        # Nach Abruf des Ergebnisses aus Speicher entfernen
        remove_from_processing_store(processing_id)
        
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

@router.get("/process/models")
async def get_available_models():
    """
    Gibt verfügbare Ollama-Modelle zurück
    """
    
    try:
        models = await ollama_client.list_models()
        connection_status = await ollama_client.check_connection()
        
        return {
            "connected": connection_status,
            "models": models,
            "recommended": "mistral-nemo:latest" if "mistral-nemo:latest" in models else models[0] if models else None,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "models": [],
            "timestamp": datetime.now()
        } 