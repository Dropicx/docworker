"""
Unified Processing Router

This module contains the new, unified processing logic that uses only
the universal prompt system and database storage.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.models.document_types import DocumentClass
from app.models.document import SupportedLanguage, ProcessingStatus
from app.services.ovh_client import OVHClient
from app.services.unified_prompt_manager import UnifiedPromptManager
from app.services.ai_logging_service import AILoggingService
from app.database.connection import get_session
from app.models.document import TranslationResult
from app.services.cleanup import (
    get_from_processing_store, 
    update_processing_store,
    remove_from_processing_store
)

logger = logging.getLogger(__name__)

router = APIRouter()

async def process_document_unified(processing_id: str):
    """
    Process a document using the unified universal prompt system.
    This replaces all old processing logic.
    """
    try:
        print(f"🚀 Starting unified processing: {processing_id[:8]}")
        
        # Get processing data
        processing_data = get_from_processing_store(processing_id)
        if not processing_data:
            print(f"❌ Processing data not found: {processing_id[:8]}")
            return
        
        # Get database session
        with get_session() as db:
            # Initialize services
            unified_manager = UnifiedPromptManager(db)
            ai_logger = AILoggingService(db)
            ovh_client = OVHClient()
            
            # Step 0: Conditional Text Extraction (OCR if needed)
            extracted_text = processing_data.get("extracted_text", "")

            if not extracted_text:
                print(f"📄 No pre-extracted text found - checking if OCR needed: {processing_id[:8]}")

                # Check if we have file content that needs OCR
                file_content = processing_data.get("file_content")
                file_type = processing_data.get("file_type", "")
                filename = processing_data.get("filename", "")

                if file_content and file_type:
                    # Check if file type requires OCR (images, PDFs)
                    needs_ocr = file_type.lower() in ['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'bmp', 'gif']

                    if needs_ocr:
                        print(f"🔍 File type '{file_type}' requires OCR - starting text extraction")
                        update_processing_store(processing_id, {
                            "status": ProcessingStatus.PROCESSING,
                            "progress_percent": 5,
                            "current_step": "Extracting text from image/PDF..."
                        })

                        # Import and use the hybrid text extractor for conditional OCR
                        from app.services.hybrid_text_extractor import HybridTextExtractor

                        try:
                            hybrid_extractor = HybridTextExtractor()
                            extracted_text, extraction_confidence = await hybrid_extractor.extract_text(
                                file_content, file_type, filename
                            )

                            if extracted_text and len(extracted_text.strip()) >= 10:
                                # Store extracted text for future use
                                processing_data["extracted_text"] = extracted_text
                                processing_data["extraction_confidence"] = extraction_confidence
                                processing_data["extraction_method"] = "hybrid_ocr"
                                update_processing_store(processing_id, processing_data)

                                print(f"✅ Text extracted successfully: {len(extracted_text)} chars (confidence: {extraction_confidence:.2%})")
                            else:
                                raise Exception("Insufficient text extracted from document")

                        except Exception as e:
                            print(f"❌ OCR extraction failed: {e}")
                            update_processing_store(processing_id, {
                                "status": ProcessingStatus.ERROR,
                                "error": f"Text extraction failed: {str(e)}",
                                "error_at": datetime.now()
                            })
                            return
                    else:
                        # File type doesn't need OCR (e.g., plain text files)
                        if file_type.lower() in ['txt', 'text']:
                            try:
                                extracted_text = file_content.decode('utf-8') if isinstance(file_content, bytes) else str(file_content)
                                print(f"📝 Text file processed directly: {len(extracted_text)} chars")
                            except Exception as e:
                                print(f"❌ Failed to decode text file: {e}")
                                update_processing_store(processing_id, {
                                    "status": ProcessingStatus.ERROR,
                                    "error": f"Failed to process text file: {str(e)}",
                                    "error_at": datetime.now()
                                })
                                return
                        else:
                            print(f"❌ Unsupported file type for processing: {file_type}")
                            update_processing_store(processing_id, {
                                "status": ProcessingStatus.ERROR,
                                "error": f"Unsupported file type: {file_type}",
                                "error_at": datetime.now()
                            })
                            return
                else:
                    print(f"❌ No file content available for processing: {processing_id[:8]}")
                    update_processing_store(processing_id, {
                        "status": ProcessingStatus.ERROR,
                        "error": "No file content found for processing",
                        "error_at": datetime.now()
                    })
                    return
            else:
                print(f"✅ Using pre-extracted text: {len(extracted_text)} chars")

            if not extracted_text:
                print(f"❌ No text available after extraction: {processing_id[:8]}")
                update_processing_store(processing_id, {
                    "status": ProcessingStatus.ERROR,
                    "error": "No text extracted or provided",
                    "error_at": datetime.now()
                })
                return

            print(f"📄 Processing text: {len(extracted_text)} characters")
            start_time = time.time()
            
            # Step 1: Medical Content Validation
            if unified_manager.is_pipeline_step_enabled("MEDICAL_VALIDATION"):
                print(f"🔍 Medical validation: STARTING")
                update_processing_store(processing_id, {
                    "status": ProcessingStatus.PROCESSING,
                    "progress_percent": 10,
                    "current_step": "Validating medical content..."
                })
                
                from app.services.medical_content_validator import MedicalContentValidator
                validator = MedicalContentValidator(ovh_client)
                is_medical, validation_confidence, validation_method = await validator.validate_medical_content(extracted_text)
                
                # Log medical validation
                ai_logger.log_medical_validation(
                    processing_id=processing_id,
                    input_text=extracted_text[:1000],
                    is_medical=is_medical,
                    confidence=validation_confidence,
                    method=validation_method,
                    document_type="UNKNOWN"
                )
                
                if not is_medical:
                    print(f"❌ Medical validation: FAILED (confidence: {validation_confidence:.2%}, method: {validation_method})")
                    update_processing_store(processing_id, {
                        "status": ProcessingStatus.NON_MEDICAL_CONTENT,
                        "progress_percent": 100,
                        "current_step": "Document does not contain medical content",
                        "error": "Document does not contain medical content",
                        "completed_at": datetime.now()
                    })
                    return
                else:
                    print(f"✅ Medical validation: PASSED (confidence: {validation_confidence:.2%}, method: {validation_method})")
            else:
                print(f"⏭️ Medical validation: SKIPPED (disabled)")
            
            # Step 2: Text Preprocessing
            if unified_manager.is_pipeline_step_enabled("PREPROCESSING"):
                print(f"🧹 Preprocessing: STARTING")
                update_processing_store(processing_id, {
                    "status": ProcessingStatus.PROCESSING,
                    "progress_percent": 20,
                    "current_step": "Preprocessing text..."
                })
                
                cleaned_text = await ovh_client.preprocess_medical_text(extracted_text)
                print(f"✅ Preprocessing: COMPLETED")
            else:
                cleaned_text = extracted_text
                print(f"⏭️ Preprocessing: SKIPPED (disabled)")
            
            # Step 3: Document Classification
            detected_doc_type = "arztbrief"  # Default
            if unified_manager.is_pipeline_step_enabled("CLASSIFICATION"):
                print(f"🏷️ Classification: STARTING")
                update_processing_store(processing_id, {
                    "status": ProcessingStatus.PROCESSING,
                    "progress_percent": 30,
                    "current_step": "Classifying document type..."
                })
                
                from app.services.document_classifier import DocumentClassifier
                classifier = DocumentClassifier(ovh_client)
                classification_result = await classifier.classify_document(cleaned_text)
                detected_doc_type = classification_result.document_class.value
                document_class = DocumentClass(detected_doc_type)
                
                # Log classification
                ai_logger.log_classification(
                    processing_id=processing_id,
                    input_text=cleaned_text[:1000],
                    detected_type=detected_doc_type,
                    confidence=classification_result.confidence,
                    document_type=detected_doc_type
                )
                
                print(f"✅ Classification: {detected_doc_type.upper()} (confidence: {classification_result.confidence:.2%})")
            else:
                document_class = DocumentClass.ARZTBRIEF
                print(f"⏭️ Classification: SKIPPED (disabled)")
            
            # Step 4: Get combined prompts for the detected document type
            combined_prompts = unified_manager.get_combined_prompts(document_class)
            
            # Step 5: Translation
            translated_text = cleaned_text
            translation_confidence = 1.0
            
            if unified_manager.is_pipeline_step_enabled("TRANSLATION", document_class):
                print(f"🔄 Translation: STARTING")
                update_processing_store(processing_id, {
                    "status": ProcessingStatus.PROCESSING,
                    "progress_percent": 40,
                    "current_step": "Translating to simple language..."
                })
                
                # Use the document-specific translation prompt
                translation_prompt = combined_prompts.get("translation_prompt", "")
                if translation_prompt:
                    translated_text, _, translation_confidence, _ = await ovh_client.translate_medical_document(
                        cleaned_text, 
                        document_type=detected_doc_type, 
                        custom_prompts=None,  # We'll pass the prompt directly
                        translation_prompt=translation_prompt
                    )
                
                # Log translation
                ai_logger.log_translation(
                    processing_id=processing_id,
                    input_text=cleaned_text[:1000],
                    output_text=translated_text[:1000],
                    confidence=translation_confidence,
                    document_type=detected_doc_type
                )
                
                print(f"✅ Translation: COMPLETED (confidence: {translation_confidence:.2%})")
            else:
                print(f"⏭️ Translation: SKIPPED (disabled)")
            
            # Step 6: Quality Checks
            from app.services.quality_checker import QualityChecker
            quality_checker = QualityChecker(ovh_client)
            
            # Fact Check
            if unified_manager.is_pipeline_step_enabled("FACT_CHECK", document_class):
                print(f"🔍 Fact check: STARTING")
                update_processing_store(processing_id, {
                    "status": ProcessingStatus.PROCESSING,
                    "progress_percent": 50,
                    "current_step": "Fact checking..."
                })
                
                fact_check_prompt = combined_prompts.get("fact_check_prompt", "")
                if fact_check_prompt:
                    fact_checked_text, fact_check_results = await quality_checker.fact_check(
                        translated_text, document_class, fact_check_prompt
                    )
                    translated_text = fact_checked_text
                
                # Log fact check
                ai_logger.log_fact_check(
                    processing_id=processing_id,
                    input_text=translated_text[:1000],
                    output_text=translated_text[:1000],
                    results=fact_check_results,
                    document_type=detected_doc_type
                )
                
                print(f"✅ Fact check: COMPLETED")
            else:
                print(f"⏭️ Fact check: SKIPPED (disabled)")
            
            # Grammar Check
            if unified_manager.is_pipeline_step_enabled("GRAMMAR_CHECK", document_class):
                print(f"📝 Grammar check: STARTING")
                update_processing_store(processing_id, {
                    "status": ProcessingStatus.PROCESSING,
                    "progress_percent": 60,
                    "current_step": "Grammar checking..."
                })
                
                grammar_check_prompt = combined_prompts.get("grammar_check_prompt", "")
                if grammar_check_prompt:
                    grammar_checked_text, grammar_check_results = await quality_checker.grammar_check(
                        translated_text, "de", grammar_check_prompt
                    )
                    translated_text = grammar_checked_text
                
                # Log grammar check
                ai_logger.log_grammar_check(
                    processing_id=processing_id,
                    input_text=translated_text[:1000],
                    output_text=translated_text[:1000],
                    results=grammar_check_results,
                    document_type=detected_doc_type
                )
                
                print(f"✅ Grammar check: COMPLETED")
            else:
                print(f"⏭️ Grammar check: SKIPPED (disabled)")
            
            # Step 7: Language Translation (if target language specified)
            target_language = processing_data.get("target_language")
            language_translated_text = None
            language_confidence_score = None
            
            if target_language and unified_manager.is_pipeline_step_enabled("LANGUAGE_TRANSLATION"):
                print(f"🌍 Language translation: STARTING")
                update_processing_store(processing_id, {
                    "status": ProcessingStatus.LANGUAGE_TRANSLATING,
                    "progress_percent": 70,
                    "current_step": f"Translating to {target_language.value}..."
                })
                
                language_translation_prompt = combined_prompts.get("language_translation_prompt", "")
                if language_translation_prompt:
                    # Replace {language} placeholder
                    formatted_prompt = language_translation_prompt.format(language=target_language.value)
                    language_translated_text, language_confidence_score = await ovh_client.translate_to_language(
                        translated_text, target_language.value, formatted_prompt
                    )
                
                # Log language translation
                ai_logger.log_language_translation(
                    processing_id=processing_id,
                    input_text=translated_text[:1000],
                    output_text=language_translated_text[:1000] if language_translated_text else "",
                    target_language=target_language.value,
                    confidence=language_confidence_score or 0.0,
                    document_type=detected_doc_type
                )
                
                print(f"✅ Language translation: COMPLETED (confidence: {language_confidence_score:.2%})")
            else:
                print(f"⏭️ Language translation: SKIPPED (disabled or no target language)")
            
            # Step 8: Final Quality Check
            if unified_manager.is_pipeline_step_enabled("FINAL_CHECK"):
                print(f"✅ Final check: STARTING")
                update_processing_store(processing_id, {
                    "status": ProcessingStatus.PROCESSING,
                    "progress_percent": 80,
                    "current_step": "Final quality check..."
                })
                
                final_check_prompt = combined_prompts.get("final_check_prompt", "")
                if final_check_prompt:
                    final_checked_text, final_check_results = await quality_checker.final_check(
                        translated_text, final_check_prompt
                    )
                    translated_text = final_checked_text
                
                # Log final check
                ai_logger.log_final_check(
                    processing_id=processing_id,
                    input_text=translated_text[:1000],
                    output_text=translated_text[:1000],
                    results=final_check_results,
                    document_type=detected_doc_type
                )
                
                print(f"✅ Final check: COMPLETED")
            else:
                print(f"⏭️ Final check: SKIPPED (disabled)")
            
            # Step 9: Formatting (Document-specific)
            if unified_manager.is_pipeline_step_enabled("FORMATTING", document_class):
                print(f"🎨 Formatting: STARTING")
                update_processing_store(processing_id, {
                    "status": ProcessingStatus.PROCESSING,
                    "progress_percent": 90,
                    "current_step": "Formatting text..."
                })
                
                # Get document-specific formatting prompt
                formatting_prompt = combined_prompts.get("formatting_prompt", "")
                if formatting_prompt:
                    # Apply formatting using OVH client
                    formatted_text = await ovh_client.format_text(translated_text, formatting_prompt)
                    translated_text = formatted_text
                
                print(f"✅ Formatting: COMPLETED")
            else:
                print(f"⏭️ Formatting: SKIPPED (disabled)")
            
            # Calculate final metrics
            processing_time = time.time() - start_time
            overall_confidence = translation_confidence
            if language_confidence_score:
                overall_confidence = (translation_confidence + language_confidence_score) / 2
            
            # Create result
            result = TranslationResult(
                processing_id=processing_id,
                original_text=extracted_text,
                translated_text=translated_text,
                language_translated_text=language_translated_text,
                target_language=SupportedLanguage(target_language) if target_language else None,
                document_type_detected=detected_doc_type,
                confidence_score=overall_confidence,
                language_confidence_score=language_confidence_score,
                processing_time_seconds=processing_time
            )
            
            # Update processing store with final result
            update_processing_store(processing_id, {
                "status": ProcessingStatus.COMPLETED,
                "progress_percent": 100,
                "current_step": "Processing completed (Unified System)",
                "result": result.dict(),
                "completed_at": datetime.now(),
                "unified": True
            })
            
            print(f"✅ Unified processing completed: {processing_id[:8]} ({processing_time:.2f}s)")
            
    except Exception as e:
        print(f"❌ Unified processing error {processing_id[:8]}: {e}")
        logger.error(f"Unified processing error: {e}")
        
        update_processing_store(processing_id, {
            "status": ProcessingStatus.ERROR,
            "current_step": "Error in unified processing",
            "error": str(e),
            "error_at": datetime.now()
        })
