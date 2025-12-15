"""
Document Processing Tasks

Background tasks for medical document translation and processing.
"""
import logging
import sys
import time
from datetime import datetime
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from worker.worker import celery_app

# Add backend to path
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/home/catchmelit/Projects/doctranslator/backend')

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='process_medical_document')
def process_medical_document(self, processing_id: str, options: dict = None):
    """
    Background task for processing medical documents with modular pipeline

    Args:
        processing_id: Unique identifier for the processing job
        options: Optional processing parameters (target_language, etc.)

    Returns:
        dict: Processing result with status and data
    """
    logger.info(f"📄 Processing document: {processing_id}")

    # Import dependencies
    from app.database.connection import get_db_session
    from app.database.modular_pipeline_models import PipelineJobDB, StepExecutionStatus, OCRConfigurationDB
    from app.repositories.pipeline_job_repository import PipelineJobRepository
    from app.services.modular_pipeline_executor import ModularPipelineExecutor
    from app.services.ocr_engine_manager import OCREngineManager
    from sqlalchemy.orm import Session

    db: Session = next(get_db_session())

    try:
        # Load job from database using repository (ensures file_content is decrypted)
        job_repo = PipelineJobRepository(db)
        job = job_repo.get_by_processing_id(processing_id)

        if not job:
            logger.error(f"❌ Job not found: {processing_id}")
            raise ValueError(f"Job not found: {processing_id}")

        # Verify file_content is decrypted (should be plaintext PDF bytes, not encrypted string)
        if job.file_content:
            file_content_len = len(job.file_content)
            file_content_preview = job.file_content[:50] if isinstance(job.file_content, bytes) else str(job.file_content)[:50]
            logger.info(f"📋 Loaded job: {job.filename} ({job.file_size} bytes)")
            logger.info(f"🔍 file_content after load: {file_content_len} bytes")
            
            # Check if it's decrypted (should be PDF binary, not encrypted string)
            if isinstance(job.file_content, bytes):
                try:
                    # Try to decode as UTF-8 to check if it's encrypted
                    decoded = job.file_content[:100].decode('utf-8')
                    if decoded.startswith('gAAAAA') or decoded.startswith('Z0FBQUFB'):
                        logger.error(f"❌ ERROR: file_content is still ENCRYPTED! This should be decrypted!")
                        logger.error(f"   Preview: {decoded[:50]}...")
                        raise ValueError("file_content was not decrypted by repository!")
                    else:
                        logger.debug(f"   file_content preview (decoded): {decoded[:50]}...")
                except UnicodeDecodeError:
                    # Cannot decode as UTF-8 - this is good, it means it's binary (PDF)
                    if job.file_content[:4] == b'%PDF':
                        logger.info(f"   ✅ Verified: file_content is decrypted (starts with %PDF)")
                    else:
                        logger.warning(f"   ⚠️ file_content doesn't start with %PDF: {file_content_preview.hex()[:20]}...")
            else:
                logger.warning(f"   ⚠️ file_content is not bytes: {type(job.file_content)}")
        else:
            logger.warning(f"   ⚠️ file_content is None")

        # NOTE: We do NOT expire the entity here because:
        # 1. The update() method uses SQLAlchemy's update() statement which only updates specified fields
        # 2. Expiring would cause SQLAlchemy to reload file_content from DB (encrypted) when accessed
        # 3. We need the decrypted file_content for OCR processing
        # The update() method already prevents overwriting encrypted fields not in kwargs

        # Merge options: Celery task options take priority, fallback to job's processing_options
        if not options:
            options = {}
        if job.processing_options:
            # Job's processing_options as base, task options override
            merged_options = {**job.processing_options, **options}
            options = merged_options
            logger.info(f"📋 Processing options: {options}")

        # Update job status to RUNNING (using repository to handle encryption)
        update_data = {"status": StepExecutionStatus.RUNNING, "progress_percent": 0}
        # Preserve started_at from upload endpoint (includes queue time)
        # Only set if somehow missing (shouldn't happen in normal flow)
        if not job.started_at:
            update_data["started_at"] = datetime.now()
            logger.warning("⚠️ started_at was not set by upload endpoint, setting now")
        job = job_repo.update(job.id, **update_data)

        # Update Celery task state
        self.update_state(
            state='PROCESSING',
            meta={'progress': 0, 'status': 'starting', 'current_step': 'Initialisierung'}
        )

        # Execute modular pipeline
        executor = ModularPipelineExecutor(db)

        # Step 1: OCR (if needed)
        extracted_text = ""
        if job.file_type in ["pdf", "image", "jpg", "jpeg", "png"]:
            logger.info(f"🔍 Starting OCR for {job.file_type.upper()}...")
            # Use repository update to avoid overwriting encrypted file_content
            job = job_repo.update(job.id, progress_percent=10)
            self.update_state(
                state='PROCESSING',
                meta={'progress': 10, 'status': 'ocr', 'current_step': 'Texterkennung (OCR)'}
            )

            ocr_manager = OCREngineManager(db)
            start_time = time.time()

            # Call OCR engine (selected engine from database configuration)
            extracted_text, ocr_confidence = await_sync(
                ocr_manager.extract_text(
                    file_content=job.file_content,
                    file_type=job.file_type,
                    filename=job.filename
                )
            )

            ocr_time = time.time() - start_time
            # Use repository update to avoid overwriting encrypted file_content
            job = job_repo.update(job.id, ocr_time_seconds=ocr_time)
            logger.info(f"✅ OCR completed in {ocr_time:.2f}s: {len(extracted_text)} characters, confidence: {ocr_confidence:.2%}")

            # ⚡ Step 1.5: LOCAL PII Removal (BEFORE sending to AI pipeline)
            # Check if PII removal is enabled in OCR config
            ocr_config = db.query(OCRConfigurationDB).first()
            pii_enabled = ocr_config.pii_removal_enabled if ocr_config else True

            if pii_enabled:
                logger.info("🔒 Starting local PII removal...")
                # Use repository update to avoid overwriting encrypted file_content
                job = job_repo.update(job.id, progress_percent=15)
                self.update_state(
                    state='PROCESSING',
                    meta={'progress': 15, 'status': 'pii_removal', 'current_step': 'Entfernung persönlicher Daten'}
                )

                from app.services.privacy_filter_advanced import AdvancedPrivacyFilter

                pii_filter = AdvancedPrivacyFilter()
                pii_start_time = time.time()
                original_length = len(extracted_text)

                # Phase 1.4: remove_pii() now returns (cleaned_text, metadata) tuple
                extracted_text, pii_metadata = pii_filter.remove_pii(extracted_text)

                pii_time_ms = (time.time() - pii_start_time) * 1000
                cleaned_length = len(extracted_text)

                logger.info(f"✅ PII removal completed in {pii_time_ms:.1f}ms")
                logger.info(f"   Original: {original_length} chars → Cleaned: {cleaned_length} chars")

                # Log enhanced metadata from Phase 1.4
                if pii_metadata.get("entities_detected", 0) > 0:
                    logger.info(
                        f"   📊 Detected: {pii_metadata['entities_detected']} entities, "
                        f"Preserved: {pii_metadata['eponyms_preserved']} eponyms, "
                        f"Low confidence: {pii_metadata['low_confidence_count']}"
                    )
            else:
                logger.info("⏭️  PII removal disabled - skipping privacy filter")

        # Update progress (use repository to avoid overwriting encrypted file_content)
        job = job_repo.update(job.id, progress_percent=20)

        # Step 2: Execute pipeline steps
        logger.info("🔄 Starting pipeline execution...")
        logger.info(f"   Document: {job.filename} ({len(extracted_text)} characters)")
        self.update_state(
            state='PROCESSING',
            meta={'progress': 20, 'status': 'pipeline', 'current_step': 'Pipeline-Verarbeitung'}
        )

        pipeline_start = time.time()

        # Prepare context with PII-cleaned OCR text preserved
        # Note: extracted_text has already been through PII removal (if enabled)
        pipeline_context = options or {}
        pipeline_context['original_text'] = extracted_text  # PII-cleaned OCR text (safe for AI processing)
        pipeline_context['ocr_text'] = extracted_text  # Alias for clarity

        # Execute pipeline (async method, need to await)
        logger.info(f"⏱️  Pipeline execution timeout: 18 minutes (soft limit)")
        success, final_output, metadata = await_sync(
            executor.execute_pipeline(
                processing_id=processing_id,
                input_text=extracted_text,
                context=pipeline_context
            )
        )

        pipeline_time = time.time() - pipeline_start
        # Use repository update to avoid overwriting encrypted file_content
        job = job_repo.update(job.id, ai_processing_time_seconds=pipeline_time)

        # Check if pipeline succeeded or terminated early
        if not success:
            # Check if this is a controlled termination (valid outcome) vs. actual failure
            if metadata.get('terminated', False):
                # ==================== CONTROLLED TERMINATION ====================
                # This is a VALID outcome (e.g., non-medical content detected)
                # Not an error - just an early exit with a specific reason
                termination_reason = metadata.get('termination_reason', 'Processing stopped')
                termination_message = metadata.get('termination_message', 'Processing was terminated.')
                termination_step = metadata.get('termination_step', 'Unknown')

                logger.warning(f"🛑 Pipeline terminated at '{termination_step}': {termination_reason}")
                logger.info(f"   Message: {termination_message}")

                # Set final_output to termination message for user display
                final_output = termination_message

                # Continue to finalization (this is a valid outcome, not an error)
            else:
                # ==================== ACTUAL PIPELINE FAILURE ====================
                # This is a real error - executor encountered a problem
                error_msg = metadata.get('error', 'Unknown error')
                failed_step = metadata.get('failed_at_step', 'Unknown step')
                error_type = metadata.get('error_type', 'unknown')
                failed_step_id = metadata.get('failed_step_id', None)

                logger.error(f"❌ Pipeline failed at step '{failed_step}': {error_msg}")
                logger.error(f"   Error type: {error_type}, Step ID: {failed_step_id}")

                # Store error details in job (using repository)
                job = job_repo.update(
                    job.id,
                    status=StepExecutionStatus.FAILED,
                    failed_at=datetime.now(),
                    error_message=f"[{failed_step}] {error_msg}",
                    error_step_id=failed_step_id,
                )

                # Update Celery state with proper serializable error (avoid exception serialization issues)
                self.update_state(
                    state='FAILURE',
                    meta={
                        'error': error_msg,
                        'error_type': error_type,
                        'failed_step': failed_step,
                        'failed_step_id': failed_step_id,
                        'processing_id': processing_id,
                        'message': f"Pipeline execution failed at '{failed_step}': {error_msg}"
                    }
                )

                # Return failure status instead of raising to avoid Celery serialization issues
                return {
                    'status': 'failed',
                    'processing_id': processing_id,
                    'error': error_msg,
                    'error_type': error_type,
                    'failed_step': failed_step,
                    'failed_step_id': failed_step_id
                }

        # ==================== WORKER IS THE ORCHESTRATOR ====================
        # Worker owns the job lifecycle and builds final result_data
        # Executor is a pure service that returns metadata

        # Calculate total processing time (includes OCR + PII + Pipeline + Queue time)
        total_time = time.time() - job.started_at.timestamp()

        # Extract document class information from metadata
        document_class_info = metadata.get('document_class', {})
        document_class_key = document_class_info.get('class_key', 'UNKNOWN') if isinstance(document_class_info, dict) else 'UNKNOWN'

        # Build comprehensive result_data from all processing stages
        result_data = {
            # ==================== PIPELINE EXECUTION METADATA ====================
            "branching_path": metadata.get('branching_path', []),  # Complete decision tree
            "document_class": document_class_info,  # Document classification details
            "total_steps": metadata.get('total_steps', 0),
            "pipeline_execution_time": metadata.get('pipeline_execution_time', 0.0),

            # ==================== PROCESSING METADATA ====================
            "processing_id": processing_id,
            "original_text": extracted_text,
            "translated_text": final_output,
            "document_type_detected": document_class_key,

            # ==================== TIMING BREAKDOWN ====================
            "ocr_time_seconds": job.ocr_time_seconds,
            "ai_processing_time_seconds": metadata.get('pipeline_execution_time', 0.0),
            "processing_time_seconds": total_time,  # Required by TranslationResult model

            # ==================== QUALITY METRICS ====================
            "confidence_score": metadata.get('confidence_score', 0.0),
            "language_translated_text": metadata.get('language_translation', None),
            "language_confidence_score": metadata.get('language_confidence', None),

            # ==================== TERMINATION INFO (if applicable) ====================
            "terminated": metadata.get('terminated', False),
            "termination_reason": metadata.get('termination_reason', None),
            "termination_message": metadata.get('termination_message', None),
            "termination_step": metadata.get('termination_step', None),
            "matched_value": metadata.get('matched_value', None),

            # ==================== REQUEST CONTEXT ====================
            "target_language": options.get('target_language', None) if options else None
        }

        # ==================== FINALIZE JOB (SINGLE SOURCE OF TRUTH) ====================
        # Update job using repository (ensures proper handling of encrypted fields)
        job = job_repo.update(
            job.id,
            status=StepExecutionStatus.COMPLETED,
            completed_at=datetime.now(),
            progress_percent=100,
            result_data=result_data,
            total_execution_time_seconds=total_time,
        )
        # Note: job.ocr_time_seconds and job.ai_processing_time_seconds already committed earlier

        logger.info(f"✅ Document processed successfully: {processing_id}")

        return {
            'status': 'completed',
            'processing_id': processing_id,
            'result': result_data,
            'metrics': {
                'ocr_time': job.ocr_time_seconds,
                'pipeline_time': job.ai_processing_time_seconds,
                'total_time': job.total_execution_time_seconds
            }
        }

    except SoftTimeLimitExceeded as e:
        # Handle timeout gracefully
        logger.error(f"⏱️ Processing timeout for document {processing_id} (exceeded soft time limit)")

        # Update job status using repository
        try:
            if 'job' in locals() and job:
                job_repo.update(
                    job.id,
                    status=StepExecutionStatus.FAILED,
                    failed_at=datetime.now(),
                    error_message=(
                        "Processing timeout: Document processing took too long (>18 minutes). "
                        "This may happen with very large or complex documents. "
                        "Please try with a smaller document or contact support."
                    ),
                )
        except Exception as update_error:
            logger.error(f"Failed to update job status after timeout: {update_error}")

        # Update Celery state with proper serializable error
        self.update_state(
            state='FAILURE',
            meta={
                'error': 'Processing timeout exceeded',
                'error_type': 'timeout',
                'processing_id': processing_id,
                'message': 'Document processing took too long. Please try with a smaller document.'
            }
        )

        # Don't re-raise - return failure status instead to avoid serialization issues
        return {
            'status': 'failed',
            'processing_id': processing_id,
            'error': 'Processing timeout exceeded',
            'error_type': 'timeout'
        }

    except Exception as e:
        logger.error(f"❌ Error processing document {processing_id}: {str(e)}")

        # Update job status to FAILED using repository
        try:
            if 'job' in locals() and job:
                job_repo.update(
                    job.id,
                    status=StepExecutionStatus.FAILED,
                    failed_at=datetime.now(),
                    error_message=str(e),
                )
        except Exception as update_error:
            logger.error(f"Failed to update job status after error: {update_error}")

        # Update Celery state
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'processing_id': processing_id}
        )
        raise

    finally:
        db.close()


def await_sync(coroutine):
    """Helper to run async functions in sync context"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coroutine)


@celery_app.task(name='test_privacy_filter')
def test_privacy_filter(text: str) -> dict:
    """
    Test the privacy filter on provided text using the worker's NER capabilities.

    Args:
        text: Text to process through the privacy filter

    Returns:
        dict: Processing result with cleaned text and metadata
    """
    import time
    logger.info(f"🔒 Testing privacy filter on {len(text)} characters")

    try:
        from app.services.privacy_filter_advanced import AdvancedPrivacyFilter

        filter_instance = AdvancedPrivacyFilter(load_custom_terms=False)

        start = time.perf_counter()
        cleaned_text, metadata = filter_instance.remove_pii(text)
        processing_time_ms = (time.perf_counter() - start) * 1000

        quality_summary = metadata.get("quality_summary", {})

        logger.info(f"✅ Privacy filter test completed in {processing_time_ms:.1f}ms")

        return {
            "status": "success",
            "input_length": len(text),
            "output_length": len(cleaned_text),
            "cleaned_text": cleaned_text,
            "processing_time_ms": round(processing_time_ms, 2),
            "pii_types_detected": metadata.get("pii_types_detected", []),
            "entities_detected": metadata.get("entities_detected", 0),
            "quality_score": quality_summary.get("quality_score", 100.0),
            "review_recommended": metadata.get("review_recommended", False),
            "passes_performance_target": processing_time_ms < 100,
        }

    except Exception as e:
        logger.error(f"❌ Privacy filter test failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@celery_app.task(name='get_privacy_filter_status')
def get_privacy_filter_status() -> dict:
    """
    Get the privacy filter status and capabilities from the worker.

    Returns:
        dict: Filter capabilities including NER status and database counts
    """
    logger.info("📊 Getting privacy filter status from worker")

    try:
        from app.services.privacy_filter_advanced import AdvancedPrivacyFilter

        filter_instance = AdvancedPrivacyFilter(load_custom_terms=False)

        pii_types = [
            "birthdate", "patient_name", "street_address", "postal_code_city",
            "phone_number", "mobile_phone", "fax_number", "email_address",
            "insurance_number", "insurance_policy", "patient_id", "hospital_id",
            "tax_id", "social_security_number", "passport_number", "id_card_number",
            "gender", "url", "salutation",
        ]

        status = {
            "status": "success",
            "filter_capabilities": {
                "has_ner": filter_instance.has_ner,
                "spacy_model": "de_core_news_md" if filter_instance.has_ner else "none",
                "removal_method": "AdvancedPrivacyFilter_Phase5",
                "custom_terms_loaded": filter_instance._custom_terms_loaded,
            },
            "detection_stats": {
                "pii_types_supported": pii_types,
                "pii_types_count": len(pii_types),
                "medical_terms_count": len(filter_instance.medical_terms),
                "drug_database_count": len(filter_instance.drug_database),
                "abbreviations_count": len(filter_instance.protected_abbreviations),
                "eponyms_count": len(filter_instance.medical_eponyms),
                "loinc_codes_count": len(filter_instance.common_loinc_codes),
            },
        }

        logger.info(f"✅ Privacy filter status: NER={'active' if filter_instance.has_ner else 'inactive'}")
        return status

    except Exception as e:
        logger.error(f"❌ Failed to get privacy filter status: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@celery_app.task(name='cleanup_old_files')
def cleanup_old_files():
    """
    Scheduled task to clean up old temporary files
    """
    logger.info("🧹 Running scheduled cleanup task")

    try:
        import sys
        sys.path.insert(0, '/app/backend')
        from app.services.cleanup import cleanup_temp_files

        # Run cleanup
        import asyncio
        files_removed = asyncio.run(cleanup_temp_files())

        logger.info(f"✅ Cleanup complete: {files_removed} files removed")

        return {
            'status': 'completed',
            'files_removed': files_removed
        }

    except Exception as e:
        logger.error(f"❌ Cleanup error: {str(e)}")
        raise
