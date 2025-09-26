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
from app.services.ovh_client import OVHClient
from app.services.unified_prompt_manager import UnifiedPromptManager
from app.services.ai_logging_service import AILoggingService
from app.routers.process_unified import process_document_unified
from app.database.connection import get_session
from sqlalchemy.orm import Session
import os

# Smart text extractor selection based on OCR availability
try:
    # Try to import the OCR-enabled text extractor first
    from app.services.text_extractor_ocr import TextExtractorWithOCR
    text_extractor = TextExtractorWithOCR()
    print("📄 Using OCR-enabled text extractor", flush=True)
except ImportError as e:
    # Fallback to simple text extractor if OCR dependencies are missing
    print(f"⚠️ OCR dependencies missing ({e}), using simple text extractor", flush=True)
    from app.services.text_extractor_simple import TextExtractor
    text_extractor = TextExtractor()

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("/process/{processing_id}")
@limiter.limit("3/minute")  # Maximal 3 Verarbeitungen pro Minute
async def start_processing(
    processing_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    options: Optional[ProcessingOptions] = None
):
    """
    Startet die Verarbeitung eines hochgeladenen Dokuments
    
    - **processing_id**: ID des hochgeladenen Dokuments
    - **options**: Verarbeitungsoptionen (z.B. Zielsprache)
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
        
        # Verarbeitungsoptionen speichern
        if options:
            processing_data["options"] = options.dict()
        
        # Verarbeitung im Hintergrund starten
        background_tasks.add_task(process_document, processing_id)
        
        # Status auf PROCESSING setzen
        update_processing_store(processing_id, {
            "status": ProcessingStatus.PROCESSING,
            "progress_percent": 10,
            "current_step": "Verarbeitung gestartet",
            "started_at": datetime.now(),
            "options": options.dict() if options else {}
        })
        
        print(f"🔄 Verarbeitung gestartet: {processing_id[:8]} (Sprache: {options.target_language if options else 'Keine'})")
        
        return {
            "message": "Verarbeitung gestartet",
            "processing_id": processing_id,
            "status": ProcessingStatus.PROCESSING,
            "target_language": options.target_language if options else None
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
    Verarbeitet Dokument im Hintergrund mit dem neuen unified System
    """
    # Use unified system (always)
    await process_document_unified(processing_id)

async def process_document_optimized(processing_id: str):
    """
    Optimized document processing - now uses unified system
    """
    # Use unified system (same as regular processing)
    await process_document_unified(processing_id)

async def process_document_legacy(processing_id: str):
    try:
        processing_data = get_from_processing_store(processing_id)
        if not processing_data:
            return
        
        start_time = time.time()
        options = processing_data.get("options", {})
        target_language = options.get("target_language")
        
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
        
        # Schritt 2: Text-Vereinfachung
        update_processing_store(processing_id, {
            "status": ProcessingStatus.TRANSLATING,
            "progress_percent": 40,
            "current_step": "Text wird in einfache Sprache übersetzt..."
        })
        
        # OVH API verwenden für Übersetzung
        from app.services.ovh_client import OVHClient
        ovh_client = OVHClient()
        
        # Prüfe OVH-Verbindung
        ovh_connected, error_msg = await ovh_client.check_connection()
        if not ovh_connected:
            raise Exception(f"OVH API nicht verfügbar: {error_msg}")
        
        # Get database session for logging and prompts
        db_session = next(get_session())
        ai_logger = AILoggingService(db_session)
        
        # Custom Prompts laden (für Validierung)
        from app.services.prompt_manager import PromptManager
        from app.models.document_types import DocumentClass
        prompt_manager = PromptManager()
        db_prompt_manager = DatabasePromptManager(db_session)
        
        # Erstmal mit "universal" laden, dann nach Klassifizierung aktualisieren
        document_class = DocumentClass.ARZTBRIEF  # Default
        try:
            custom_prompts = db_prompt_manager.load_prompts(document_class)
        except Exception as e:
            print(f"Database prompt loading failed, using file-based: {e}")
            custom_prompts = prompt_manager.load_prompts(document_class)
        
        # Medizinische Inhaltsvalidierung (nur wenn aktiviert)
        global_pipeline = get_global_pipeline_service()
        global_pipeline.db_session = db  # Pass database session
        document_specific_enabled = custom_prompts.pipeline_steps.get("MEDICAL_VALIDATION", {}).enabled
        
        if not global_pipeline.should_skip_step("MEDICAL_VALIDATION", document_specific_enabled):
            from app.services.medical_content_validator import MedicalContentValidator
            validator = MedicalContentValidator(ovh_client)
            is_medical, validation_confidence, validation_method = await validator.validate_medical_content(extracted_text)
            
            # Log medical validation
            ai_logger.log_medical_validation(
                processing_id=processing_id,
                input_text=extracted_text[:1000],  # Log first 1000 chars
                is_medical=is_medical,
                confidence=validation_confidence,
                method=validation_method,
                document_type=document_class.value
            )
            
            if not is_medical:
                print(f"❌ Medical validation: FAILED (confidence: {validation_confidence:.2%}, method: {validation_method})")
                print(f"📄 Document does not contain medical content - stopping pipeline")
                
                # Update status to non-medical content
                update_processing_store(processing_id, {
                    "status": ProcessingStatus.NON_MEDICAL_CONTENT,
                    "progress_percent": 100,
                    "current_step": "Document does not contain medical content",
                    "error": "This document does not appear to contain medical content. Please upload a medical document (doctor's letter, lab results, medical report, etc.).",
                    "validation_details": {
                        "is_medical": False,
                        "confidence": validation_confidence,
                        "method": validation_method
                    },
                    "completed_at": datetime.now()
                })
                
                print(f"🛑 Processing stopped: Non-medical content detected")
                return
            else:
                print(f"✅ Medical validation: PASSED (confidence: {validation_confidence:.2%}, method: {validation_method})")
        else:
            print(f"⏭️ Medical validation: SKIPPED (disabled)")
        
        # Erst Text vorverarbeiten (PII-Entfernung)
        cleaned_text = await ovh_client.preprocess_medical_text(extracted_text)
        
        # Dokumenttyp klassifizieren (nur wenn aktiviert)
        detected_doc_type = "arztbrief"  # Default
        document_specific_enabled = custom_prompts.pipeline_steps.get("CLASSIFICATION", {}).enabled
        
        if not global_pipeline.should_skip_step("CLASSIFICATION", document_specific_enabled):
            from app.services.document_classifier import DocumentClassifier
            classifier = DocumentClassifier(ovh_client)
            classification_result = await classifier.classify_document(cleaned_text)
            detected_doc_type = classification_result.document_class.value
            document_class = DocumentClass(detected_doc_type)
            
            # Log classification
            ai_logger.log_classification(
                processing_id=processing_id,
                input_text=cleaned_text[:1000],  # Log first 1000 chars
                document_type=detected_doc_type,
                confidence=classification_result.confidence,
                method=classification_result.method
            )
            
            # Reload prompts with correct type
            try:
                custom_prompts = db_prompt_manager.load_prompts(document_class)
            except Exception as e:
                print(f"Database prompt loading failed, using file-based: {e}")
                custom_prompts = prompt_manager.load_prompts(document_class)
            
            print(f"📋 Document classification: {detected_doc_type} (confidence: {classification_result.confidence:.2%}, method: {classification_result.method})")
        else:
            print(f"⏭️ Document classification: SKIPPED (disabled)")
        
        print(f"📝 Using custom prompts for {detected_doc_type} (version: {custom_prompts.version})")
        
        # Übersetzung (nur wenn aktiviert)
        translated_text = cleaned_text  # Start with cleaned text
        translation_confidence = 1.0  # Default confidence
        
        document_specific_enabled = custom_prompts.pipeline_steps.get("TRANSLATION", {}).enabled
        
        if not global_pipeline.should_skip_step("TRANSLATION", document_specific_enabled):
            translated_text, _, translation_confidence, _ = await ovh_client.translate_medical_document(
                cleaned_text, document_type=detected_doc_type, custom_prompts=custom_prompts
            )
            
            # Log translation
            ai_logger.log_translation(
                processing_id=processing_id,
                input_text=cleaned_text[:1000],  # Log first 1000 chars
                output_text=translated_text[:1000],  # Log first 1000 chars
                confidence=translation_confidence,
                model_used="OVH-Llama-3.3-70B",
                document_type=detected_doc_type
            )
            
            print(f"🌍 Translation: COMPLETED (confidence: {translation_confidence:.2%})")
        else:
            print(f"⏭️ Translation: SKIPPED (disabled)")
        
        # Qualitätsprüfung (Fact Check + Grammar Check)
        from app.services.quality_checker import QualityChecker
        quality_checker = QualityChecker(ovh_client)
        
        # Fact Check (nur wenn aktiviert)
        document_specific_enabled = custom_prompts.pipeline_steps.get("FACT_CHECK", {}).enabled
        
        if not global_pipeline.should_skip_step("FACT_CHECK", document_specific_enabled):
            fact_checked_text, fact_check_results = await quality_checker.fact_check(
                translated_text, document_class, custom_prompts.fact_check_prompt
            )
            
            # Log fact check
            changes_made = fact_check_results.get('changes_made', 0)
            ai_logger.log_quality_check(
                processing_id=processing_id,
                step_name="fact_check",
                input_text=translated_text[:1000],
                output_text=fact_checked_text[:1000],
                changes_made=changes_made,
                document_type=detected_doc_type
            )
            
            translated_text = fact_checked_text
            print(f"🔍 Fact check: COMPLETED ({fact_check_results.get('status', 'unknown')})")
        else:
            print(f"⏭️ Fact check: SKIPPED (disabled)")
        
        # Grammar Check (nur wenn aktiviert)
        document_specific_enabled = custom_prompts.pipeline_steps.get("GRAMMAR_CHECK", {}).enabled
        
        if not global_pipeline.should_skip_step("GRAMMAR_CHECK", document_specific_enabled):
            grammar_checked_text, grammar_check_results = await quality_checker.grammar_check(
                translated_text, "de", custom_prompts.grammar_check_prompt
            )
            
            # Log grammar check
            changes_made = grammar_check_results.get('changes_made', 0)
            ai_logger.log_quality_check(
                processing_id=processing_id,
                step_name="grammar_check",
                input_text=translated_text[:1000],
                output_text=grammar_checked_text[:1000],
                changes_made=changes_made,
                document_type=detected_doc_type
            )
            
            translated_text = grammar_checked_text
            print(f"✏️ Grammar check: COMPLETED ({grammar_check_results.get('status', 'unknown')})")
        else:
            print(f"⏭️ Grammar check: SKIPPED (disabled)")
        
        # Schritt 3: Optionale Sprachübersetzung
        language_translated_text = None
        language_confidence_score = None
        
        document_specific_enabled = custom_prompts.pipeline_steps.get("LANGUAGE_TRANSLATION", {}).enabled
        
        if target_language and not global_pipeline.should_skip_step("LANGUAGE_TRANSLATION", document_specific_enabled):
            update_processing_store(processing_id, {
                "status": ProcessingStatus.LANGUAGE_TRANSLATING,
                "progress_percent": 70,
                "current_step": f"Übersetzung in {target_language.value}..."
            })
            
            # Use custom language translation prompt if available
            language_prompt = custom_prompts.language_translation_prompt if custom_prompts else None
            language_translated_text, language_confidence_score = await ovh_client.translate_to_language(
                translated_text, target_language, custom_prompt=language_prompt
            )
            print(f"🌐 Language translation: COMPLETED (confidence: {language_confidence_score:.2%})")
        elif target_language:
            print(f"⏭️ Language translation: SKIPPED (disabled)")
            language_translated_text = None
            language_confidence_score = None
        
        # Schritt 4: Ergebnis finalisieren
        progress_percent = 90
        update_processing_store(processing_id, {
            "progress_percent": progress_percent,
            "current_step": "Ergebnis wird vorbereitet..."
        })
        
        processing_time = time.time() - start_time
        overall_confidence = translation_confidence
        if language_confidence_score:
            overall_confidence = (translation_confidence + language_confidence_score) / 2
        
        # Final Quality Check (nur wenn aktiviert)
        document_specific_enabled = custom_prompts.pipeline_steps.get("FINAL_CHECK", {}).enabled
        
        if not global_pipeline.should_skip_step("FINAL_CHECK", document_specific_enabled):
            final_checked_text, final_check_results = await quality_checker.final_check(
                translated_text, custom_prompts.final_check_prompt
            )
            translated_text = final_checked_text
            print(f"✅ Final quality check: COMPLETED ({final_check_results.get('status', 'unknown')})")
        else:
            print(f"⏭️ Final quality check: SKIPPED (disabled)")
        
        # Formatierung (nur wenn aktiviert)
        document_specific_enabled = custom_prompts.pipeline_steps.get("FORMATTING", {}).enabled
        
        if not global_pipeline.should_skip_step("FORMATTING", document_specific_enabled):
            print(f"[FORMATTING] Applying final formatting to translated text...")
            from app.services.ovh_client import OVHClient
            ovh_client = OVHClient()
            translated_text = ovh_client._improve_formatting(translated_text)
            if language_translated_text:
                language_translated_text = ovh_client._improve_formatting(language_translated_text)
            print(f"🎨 Formatting: COMPLETED")
        else:
            print(f"⏭️ Formatting: SKIPPED (disabled)")
        
        # Debug-Logging um zu sehen was passiert
        print(f"[FORMATTING] Complete:")
        print(f"  - Arrows in text: {translated_text.count('→')}")
        print(f"  - Bullets in text: {translated_text.count('•')}")
        print(f"  - Lines in text: {len(translated_text.split(chr(10)))}")
        
        # Ergebnis speichern - verwende cleaned_text statt extracted_text
        result = TranslationResult(
            processing_id=processing_id,
            original_text=cleaned_text,  # Zeige den bereinigten Text statt Rohdaten
            translated_text=translated_text,
            language_translated_text=language_translated_text,
            target_language=SupportedLanguage(target_language) if target_language else None,
            document_type_detected=detected_doc_type,
            confidence_score=overall_confidence,
            language_confidence_score=language_confidence_score,
            processing_time_seconds=processing_time
        )
        
        update_processing_store(processing_id, {
            "status": ProcessingStatus.COMPLETED,
            "progress_percent": 100,
            "current_step": "Verarbeitung abgeschlossen",
            "result": result.dict(),
            "completed_at": datetime.now()
        })
        
        language_info = f" + {target_language}" if target_language else ""
        print(f"✅ Legacy processing completed: {processing_id[:8]} ({processing_time:.2f}s{language_info})")
        
    except Exception as e:
        print(f"❌ Legacy processing error {processing_id[:8]}: {e}")
        
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

# Global optimized pipeline instance removed - now using unified system

@router.get("/process/pipeline-stats")
async def get_pipeline_stats():
    """
    Get pipeline performance statistics
    """
    try:
        return {
            "pipeline_mode": "unified",
            "cache_statistics": {
                "prompt_cache": "Database-based prompt storage",
                "ai_logging": "Comprehensive interaction tracking"
            },
            "performance_improvements": {
                "unified_system": "Single source of truth for all prompts",
                "database_storage": "Persistent prompt and configuration storage",
                "universal_pipeline": "Global pipeline step control",
                "ai_logging": "Complete interaction traceability",
                "async_operations": "Non-blocking AI API calls"
            },
            "timestamp": datetime.now()
        }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now()
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