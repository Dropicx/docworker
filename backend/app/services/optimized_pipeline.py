"""
Optimized pipeline processor with caching and async support
"""

import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import logging

from app.models.document_types import DocumentClass, DocumentPrompts
from app.services.database_prompt_manager import DatabasePromptManager
from app.services.ai_logging_service import AILoggingService
from app.services.ovh_client import OVHClient
from app.database.connection import get_session
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class OptimizedPipelineProcessor:
    """
    Optimized pipeline processor with:
    - Prompt caching to avoid repeated database calls
    - Async processing for parallel operations
    - Smart step consolidation
    - Performance monitoring
    """

    def __init__(self):
        self.prompt_cache: Dict[DocumentClass, DocumentPrompts] = {}
        self.cache_expiry: Dict[DocumentClass, datetime] = {}
        self.cache_timeout = 300  # 5 minutes cache timeout
        self.ovh_client = OVHClient()

    async def process_document_optimized(
        self,
        processing_id: str,
        file_content: bytes,
        file_type: str,
        filename: str,
        options: Optional[Dict[str, Any]] = None,
        update_callback=None
    ) -> Dict[str, Any]:
        """
        Optimized document processing with performance improvements
        """
        start_time = time.time()
        options = options or {}
        target_language = options.get("target_language")

        # Get database session and AI logger
        db_session = next(get_session())
        ai_logger = AILoggingService(db_session)

        try:
            # Step 1: Text Extraction (unchanged - necessary synchronous step)
            if update_callback:
                update_callback("Extracting text...", 15)

            from app.services.text_extractor_ocr import TextExtractorWithOCR
            text_extractor = TextExtractorWithOCR()

            extracted_text, text_confidence = await text_extractor.extract_text(
                file_content, file_type, filename
            )

            if not extracted_text or len(extracted_text.strip()) < 10:
                raise Exception("Not enough text extracted")

            # Step 2: Get cached prompts (major optimization)
            if update_callback:
                update_callback("Loading processing configuration...", 25)

            document_class = DocumentClass.ARZTBRIEF  # Default
            custom_prompts = await self._get_cached_prompts(document_class, db_session)

            # Step 3: Medical Validation with AI prompt (NEW - uses dedicated prompt)
            if custom_prompts.pipeline_steps.get("MEDICAL_VALIDATION", {}).enabled:
                if update_callback:
                    update_callback("Validating medical content...", 35)

                is_medical, validation_confidence = await self._validate_medical_content_ai(
                    extracted_text, custom_prompts.medical_validation_prompt, ai_logger, processing_id
                )

                if not is_medical:
                    return {
                        "status": "non_medical",
                        "error": "Document does not contain medical content",
                        "confidence": validation_confidence
                    }

            # Step 4: Classification and preprocessing in parallel (OPTIMIZATION)
            if update_callback:
                update_callback("Analyzing document type and cleaning data...", 45)

            classification_task, preprocessing_task = await asyncio.gather(
                self._classify_document_ai(extracted_text, custom_prompts.classification_prompt, ai_logger, processing_id),
                self._preprocess_text_ai(extracted_text, custom_prompts.preprocessing_prompt, ai_logger, processing_id),
                return_exceptions=True
            )

            # Handle results
            if isinstance(classification_task, Exception):
                logger.error(f"Classification failed: {classification_task}")
                detected_doc_type = "arztbrief"  # fallback
            else:
                detected_doc_type = classification_task
                document_class = DocumentClass(detected_doc_type)
                # Reload prompts for correct document type
                custom_prompts = await self._get_cached_prompts(document_class, db_session)

            if isinstance(preprocessing_task, Exception):
                logger.error(f"Preprocessing failed: {preprocessing_task}")
                cleaned_text = extracted_text  # fallback
            else:
                cleaned_text = preprocessing_task

            # Step 5: Translation
            if update_callback:
                update_callback("Translating to patient-friendly language...", 60)

            translated_text, translation_confidence = await self._translate_document_ai(
                cleaned_text, detected_doc_type, custom_prompts.translation_prompt, ai_logger, processing_id
            )

            # Step 6: Quality checks in parallel (OPTIMIZATION - fact_check + grammar_check)
            if update_callback:
                update_callback("Performing quality checks...", 75)

            quality_tasks = []

            if custom_prompts.pipeline_steps.get("FACT_CHECK", {}).enabled:
                quality_tasks.append(
                    self._fact_check_ai(translated_text, custom_prompts.fact_check_prompt, ai_logger, processing_id)
                )
            else:
                quality_tasks.append(asyncio.create_task(self._return_unchanged(translated_text)))

            if custom_prompts.pipeline_steps.get("GRAMMAR_CHECK", {}).enabled:
                quality_tasks.append(
                    self._grammar_check_ai(translated_text, custom_prompts.grammar_check_prompt, ai_logger, processing_id)
                )
            else:
                quality_tasks.append(asyncio.create_task(self._return_unchanged(translated_text)))

            # Execute quality checks in parallel
            fact_checked_text, grammar_checked_text = await asyncio.gather(*quality_tasks, return_exceptions=True)

            # Use grammar-checked text if available, otherwise fact-checked
            if not isinstance(grammar_checked_text, Exception):
                final_text = grammar_checked_text
            elif not isinstance(fact_checked_text, Exception):
                final_text = fact_checked_text
            else:
                final_text = translated_text

            # Step 7: Language translation (if needed)
            language_translated_text = None
            language_confidence_score = None

            if target_language and custom_prompts.pipeline_steps.get("LANGUAGE_TRANSLATION", {}).enabled:
                if update_callback:
                    update_callback(f"Translating to {target_language}...", 85)

                language_translated_text, language_confidence_score = await self._translate_to_language_ai(
                    final_text, target_language, custom_prompts.language_translation_prompt, ai_logger, processing_id
                )

            # Step 8: Final processing (formatting + final check - can be combined)
            if update_callback:
                update_callback("Finalizing document...", 95)

            final_tasks = []

            if custom_prompts.pipeline_steps.get("FINAL_CHECK", {}).enabled:
                final_tasks.append(
                    self._final_check_ai(final_text, custom_prompts.final_check_prompt, ai_logger, processing_id)
                )
            else:
                final_tasks.append(asyncio.create_task(self._return_unchanged(final_text)))

            if custom_prompts.pipeline_steps.get("FORMATTING", {}).enabled:
                final_tasks.append(
                    self._format_text_ai(final_text, custom_prompts.formatting_prompt, ai_logger, processing_id)
                )
            else:
                final_tasks.append(asyncio.create_task(self._return_unchanged(final_text)))

            # Execute final steps in parallel
            final_checked_text, formatted_text = await asyncio.gather(*final_tasks, return_exceptions=True)

            # Use the best result available
            if not isinstance(formatted_text, Exception):
                final_output = formatted_text
            elif not isinstance(final_checked_text, Exception):
                final_output = final_checked_text
            else:
                final_output = final_text

            # Apply formatting to language translation as well
            if language_translated_text and custom_prompts.pipeline_steps.get("FORMATTING", {}).enabled:
                if not isinstance(formatted_text, Exception):
                    language_translated_text = await self._format_text_ai(
                        language_translated_text, custom_prompts.formatting_prompt, ai_logger, processing_id
                    )

            # Calculate processing time and confidence
            processing_time = time.time() - start_time
            overall_confidence = translation_confidence
            if language_confidence_score:
                overall_confidence = (translation_confidence + language_confidence_score) / 2

            return {
                "status": "completed",
                "original_text": cleaned_text,
                "translated_text": final_output,
                "language_translated_text": language_translated_text,
                "target_language": target_language,
                "document_type_detected": detected_doc_type,
                "confidence_score": overall_confidence,
                "language_confidence_score": language_confidence_score,
                "processing_time_seconds": processing_time,
                "optimized": True
            }

        except Exception as e:
            logger.error(f"Optimized pipeline error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "processing_time_seconds": time.time() - start_time
            }
        finally:
            db_session.close()

    async def _get_cached_prompts(self, document_type: DocumentClass, db_session: Session) -> DocumentPrompts:
        """Get prompts with caching to avoid repeated database calls"""
        now = datetime.now()

        # Check if we have a valid cache entry
        if (document_type in self.prompt_cache and
            document_type in self.cache_expiry and
            now < self.cache_expiry[document_type]):
            return self.prompt_cache[document_type]

        # Load from database
        db_prompt_manager = DatabasePromptManager(db_session)
        prompts = db_prompt_manager.load_prompts(document_type)

        # Cache the result
        self.prompt_cache[document_type] = prompts
        self.cache_expiry[document_type] = datetime.fromtimestamp(now.timestamp() + self.cache_timeout)

        logger.info(f"Cached prompts for {document_type.value} (expires in {self.cache_timeout}s)")
        return prompts

    async def _validate_medical_content_ai(
        self, text: str, prompt: str, ai_logger: AILoggingService, processing_id: str
    ) -> Tuple[bool, float]:
        """AI-based medical validation using dedicated prompt"""
        start_time = time.time()

        try:
            response = await self.ovh_client.generate_simple(prompt + "\n\n" + text[:2000])
            processing_time = int((time.time() - start_time) * 1000)

            # Log the interaction
            ai_logger.log_medical_validation(
                processing_id=processing_id,
                input_text=text[:1000],
                is_medical="MEDIZINISCH" in response.upper(),
                confidence=0.9,  # High confidence for AI-based validation
                method="ai_prompt"
            )

            is_medical = "MEDIZINISCH" in response.upper()
            return is_medical, 0.9

        except Exception as e:
            logger.error(f"Medical validation failed: {e}")
            return True, 0.5  # Default to medical if validation fails

    async def _classify_document_ai(
        self, text: str, prompt: str, ai_logger: AILoggingService, processing_id: str
    ) -> str:
        """AI-based document classification"""
        try:
            response = await self.ovh_client.generate_simple(prompt + "\n\n" + text[:2000])

            # Extract document type from response
            if "ARZTBRIEF" in response.upper():
                doc_type = "arztbrief"
            elif "BEFUNDBERICHT" in response.upper():
                doc_type = "befundbericht"
            elif "LABORWERTE" in response.upper():
                doc_type = "laborwerte"
            else:
                doc_type = "arztbrief"  # fallback

            ai_logger.log_classification(
                processing_id=processing_id,
                input_text=text[:1000],
                document_type=doc_type,
                confidence=0.85,
                method="ai_prompt"
            )

            return doc_type

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return "arztbrief"  # fallback

    async def _preprocess_text_ai(
        self, text: str, prompt: str, ai_logger: AILoggingService, processing_id: str
    ) -> str:
        """AI-based text preprocessing"""
        try:
            response = await self.ovh_client.generate_simple(prompt + "\n\n" + text)
            return response.strip()
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            return text  # fallback to original

    async def _translate_document_ai(
        self, text: str, doc_type: str, prompt: str, ai_logger: AILoggingService, processing_id: str
    ) -> Tuple[str, float]:
        """AI-based document translation"""
        try:
            translated_text, _, confidence, _ = await self.ovh_client.translate_medical_document(
                text, document_type=doc_type, custom_prompts=None, use_prompt=prompt
            )

            ai_logger.log_translation(
                processing_id=processing_id,
                input_text=text[:1000],
                output_text=translated_text[:1000],
                confidence=confidence,
                model_used="OVH-Llama-3.3-70B",
                document_type=doc_type
            )

            return translated_text, confidence

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text, 0.5  # fallback

    async def _fact_check_ai(
        self, text: str, prompt: str, ai_logger: AILoggingService, processing_id: str
    ) -> str:
        """AI-based fact checking"""
        try:
            response = await self.ovh_client.generate_simple(prompt + "\n\n" + text)
            return response.strip()
        except Exception as e:
            logger.error(f"Fact check failed: {e}")
            return text  # fallback

    async def _grammar_check_ai(
        self, text: str, prompt: str, ai_logger: AILoggingService, processing_id: str
    ) -> str:
        """AI-based grammar checking"""
        try:
            response = await self.ovh_client.generate_simple(prompt + "\n\n" + text)
            return response.strip()
        except Exception as e:
            logger.error(f"Grammar check failed: {e}")
            return text  # fallback

    async def _translate_to_language_ai(
        self, text: str, target_language: str, prompt: str, ai_logger: AILoggingService, processing_id: str
    ) -> Tuple[str, float]:
        """AI-based language translation"""
        try:
            formatted_prompt = prompt.replace("{language}", target_language)
            response = await self.ovh_client.generate_simple(formatted_prompt + "\n\n" + text)

            return response.strip(), 0.85

        except Exception as e:
            logger.error(f"Language translation failed: {e}")
            return text, 0.5  # fallback

    async def _final_check_ai(
        self, text: str, prompt: str, ai_logger: AILoggingService, processing_id: str
    ) -> str:
        """AI-based final quality check"""
        try:
            response = await self.ovh_client.generate_simple(prompt + "\n\n" + text)
            return response.strip()
        except Exception as e:
            logger.error(f"Final check failed: {e}")
            return text  # fallback

    async def _format_text_ai(
        self, text: str, prompt: str, ai_logger: AILoggingService, processing_id: str
    ) -> str:
        """AI-based text formatting"""
        try:
            response = await self.ovh_client.generate_simple(prompt + "\n\n" + text)
            return response.strip()
        except Exception as e:
            logger.error(f"Formatting failed: {e}")
            return text  # fallback

    async def _return_unchanged(self, text: str) -> str:
        """Helper function to return text unchanged (for disabled steps)"""
        return text

    def clear_prompt_cache(self):
        """Clear the prompt cache"""
        self.prompt_cache.clear()
        self.cache_expiry.clear()
        logger.info("Prompt cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = datetime.now()
        active_entries = sum(1 for doc_type in self.cache_expiry
                           if doc_type in self.cache_expiry and now < self.cache_expiry[doc_type])

        return {
            "total_entries": len(self.prompt_cache),
            "active_entries": active_entries,
            "expired_entries": len(self.prompt_cache) - active_entries,
            "cache_timeout_seconds": self.cache_timeout
        }