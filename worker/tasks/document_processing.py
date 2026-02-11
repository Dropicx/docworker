"""
Document Processing Tasks

Background tasks for document translation and processing (generic pipeline).
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

logger = logging.getLogger(__name__)


def _process_document_impl(self, processing_id: str, options: dict = None):
    """
    Shared implementation for document processing pipeline.

    Args:
        self: Celery task instance (for update_state)
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

        # CRITICAL: Copy file_content to local variable
        # The repository already expunges the entity after decryption, so it's already
        # detached from the session and safe from accidental overwrites.
        file_content_for_processing = job.file_content
        job_id_for_updates = job.id  # Store ID for updates
        
        # Note: No need to expunge here - the repository already did it when returning the entity.
        logger.debug(f"Entity already expunged by repository (id={job_id_for_updates}), proceeding with processing")

        # Verify file_content is decrypted (should be plaintext PDF bytes, not encrypted string)
        if file_content_for_processing:
            file_content_len = len(file_content_for_processing)
            file_content_preview = file_content_for_processing[:50] if isinstance(file_content_for_processing, bytes) else str(file_content_for_processing)[:50]
            logger.info(f"📋 Loaded job: {job.filename} ({job.file_size} bytes)")
            logger.info(f"🔍 file_content after load: {file_content_len} bytes")
            
            # Check if it's decrypted (should be PDF binary, not encrypted string)
            if isinstance(file_content_for_processing, bytes):
                try:
                    # Try to decode as UTF-8 to check if it's encrypted
                    decoded = file_content_for_processing[:100].decode('utf-8')
                    if decoded.startswith('gAAAAA') or decoded.startswith('Z0FBQUFB'):
                        logger.error(f"❌ ERROR: file_content is still ENCRYPTED! This should be decrypted!")
                        logger.error(f"   Preview: {decoded[:50]}...")
                        raise ValueError("file_content was not decrypted by repository!")
                    else:
                        logger.debug(f"   file_content preview (decoded): {decoded[:50]}...")
                except UnicodeDecodeError:
                    # Cannot decode as UTF-8 - this is good, it means it's binary (PDF)
                    if file_content_for_processing[:4] == b'%PDF':
                        logger.info(f"   ✅ Verified: file_content is decrypted (starts with %PDF)")
                    else:
                        logger.warning(f"   ⚠️ file_content doesn't start with %PDF: {file_content_preview.hex()[:20]}...")
            else:
                logger.warning(f"   ⚠️ file_content is not bytes: {type(file_content_for_processing)}")
        else:
            logger.warning(f"   ⚠️ file_content is None")

        # Merge options: Celery task options take priority, fallback to job's processing_options
        if not options:
            options = {}
        if job.processing_options:
            # Job's processing_options as base, task options override
            merged_options = {**job.processing_options, **options}
            options = merged_options
            logger.info(f"📋 Processing options: {options}")

        # Update job status to RUNNING (using repository to handle encryption)
        # Use job_id_for_updates since job entity is expunged
        update_data = {"status": StepExecutionStatus.RUNNING, "progress_percent": 0}
        # Preserve started_at from upload endpoint (includes queue time)
        # Only set if somehow missing (shouldn't happen in normal flow)
        if not job.started_at:
            update_data["started_at"] = datetime.now()
            logger.warning("⚠️ started_at was not set by upload endpoint, setting now")
        job_repo.update(job_id_for_updates, **update_data)

        # Update Celery task state
        self.update_state(
            state='PROCESSING',
            meta={'progress': 0, 'status': 'starting', 'current_step': 'Initialisierung'}
        )

        # Execute modular pipeline
        executor = ModularPipelineExecutor(db)

        # Step 1: OCR (if needed)
        extracted_text = ""
        ocr_markdown = None  # Markdown-formatted text
        ocr_confidence = 0.0
        if job.file_type in ["pdf", "image", "jpg", "jpeg", "png"]:
            logger.info(f"🔍 Starting OCR for {job.file_type.upper()}...")
            # Use repository update to avoid overwriting encrypted file_content
            job_repo.update(job_id_for_updates, progress_percent=10)
            self.update_state(
                state='PROCESSING',
                meta={'progress': 10, 'status': 'ocr', 'current_step': 'Texterkennung (OCR)'}
            )

            ocr_manager = OCREngineManager(db)
            start_time = time.time()

            # Call OCR engine (selected engine from database configuration)
            # Use file_content_for_processing (local copy) instead of job.file_content
            ocr_result = await_sync(
                ocr_manager.extract_text(
                    file_content=file_content_for_processing,
                    file_type=job.file_type,
                    filename=job.filename
                )
            )

            # Extract values from OCRResult
            extracted_text = ocr_result.text
            ocr_confidence = ocr_result.confidence
            ocr_markdown = ocr_result.markdown

            ocr_time = time.time() - start_time
            # Use repository update to avoid overwriting encrypted file_content
            job_repo.update(job_id_for_updates, ocr_time_seconds=ocr_time)
            logger.info(f"✅ OCR completed in {ocr_time:.2f}s: {len(extracted_text)} characters, confidence: {ocr_confidence:.2%}")

            # ⚡ Step 1.5: PII Removal (BEFORE sending to AI pipeline)
            # External PII service (Hetzner SpaCy with large models)
            # Fallback: Railway PII service (if Hetzner unavailable)
            # Check if PII removal is enabled in OCR config
            ocr_config = db.query(OCRConfigurationDB).first()
            pii_enabled = ocr_config.pii_removal_enabled if ocr_config else True

            if pii_enabled:
                logger.info("🔒 Starting PII removal (external service)...")
                # Use repository update to avoid overwriting encrypted file_content
                job_repo.update(job_id_for_updates, progress_percent=15)
                self.update_state(
                    state='PROCESSING',
                    meta={'progress': 15, 'status': 'pii_removal', 'current_step': 'Entfernung persönlicher Daten'}
                )

                from app.services.pii_service_client import PIIServiceClient

                pii_start_time = time.time()
                original_length = len(extracted_text)

                # Get source language from options (default to German)
                source_language = options.get('source_language', 'de') if options else 'de'
                logger.info(f"   Using language model: {source_language}")

                # External PII service (Hetzner primary, Railway fallback)
                pii_client = PIIServiceClient()
                extracted_text, pii_metadata = await_sync(
                    pii_client.remove_pii(extracted_text, language=source_language)
                )

                pii_time_ms = (time.time() - pii_start_time) * 1000
                cleaned_length = len(extracted_text)
                entities_detected = pii_metadata.get("entities_detected", 0)
                custom_terms_synced = pii_metadata.get("custom_terms_synced", 0)

                # Log results
                logger.info(f"✅ PII removal completed in {pii_time_ms:.1f}ms")
                logger.info(f"   Original: {original_length} chars → Cleaned: {cleaned_length} chars")
                logger.info(f"   📊 Entities removed: {entities_detected}, Custom terms synced: {custom_terms_synced}")
            else:
                logger.info("⏭️  PII removal disabled - skipping privacy filter")

        # Update progress (use repository to avoid overwriting encrypted file_content)
        job_repo.update(job_id_for_updates, progress_percent=20)

        # Step 2: Execute pipeline steps
        logger.info("🔄 Starting pipeline execution...")
        logger.info(f"   Document: {job.filename} ({len(extracted_text)} characters)")
        self.update_state(
            state='PROCESSING',
            meta={'progress': 20, 'status': 'pipeline', 'current_step': 'Pipeline-Verarbeitung'}
        )

        pipeline_start = time.time()

        # Prepare context with PII-cleaned OCR text
        # Note: extracted_text has already been through PII removal (if enabled)
        pipeline_context = options or {}
        pipeline_context['original_text'] = extracted_text  # PII-cleaned OCR text (safe for AI processing)
        pipeline_context['ocr_text'] = extracted_text  # Alias for clarity
        pipeline_context['ocr_markdown'] = ocr_markdown
        pipeline_context['ocr_confidence'] = ocr_confidence

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
        job_repo.update(job_id_for_updates, ai_processing_time_seconds=pipeline_time)

        # Check if pipeline succeeded or terminated early
        if not success:
            # Check if this is a controlled termination (valid outcome) vs. actual failure
            if metadata.get('terminated', False):
                # ==================== CONTROLLED TERMINATION ====================
                # This is a VALID outcome (e.g., content validation failed / unsupported content)
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
                job_repo.update(
                    job_id_for_updates,
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
        # Worker owns the job lifecycle and writes results to individual columns
        # Executor is a pure service that returns metadata

        # Calculate total processing time (includes OCR + PII + Pipeline + Queue time)
        total_time = time.time() - job.started_at.timestamp()

        # Extract document class information from metadata
        document_class_info = metadata.get('document_class', {})
        document_class_key = document_class_info.get('class_key', 'UNKNOWN') if isinstance(document_class_info, dict) else 'UNKNOWN'

        # ==================== FINALIZE JOB (SINGLE SOURCE OF TRUTH) ====================
        # Update job columns directly (Issue #55: separate encrypted DB columns)
        # Content columns will be encrypted by repository automatically
        job_repo.update(
            job_id_for_updates,
            status=StepExecutionStatus.COMPLETED,
            completed_at=datetime.now(),
            progress_percent=100,
            total_execution_time_seconds=total_time,

            # Encrypted content
            original_text=extracted_text,
            translated_text=final_output,
            language_translated_text=metadata.get('language_translation'),
            ocr_markdown=ocr_markdown,

            # Metadata (unencrypted, queryable)
            document_type_detected=document_class_key,
            confidence_score=metadata.get('confidence_score', 0.0),
            ocr_confidence=ocr_confidence,
            language_confidence_score=metadata.get('language_confidence'),
            pipeline_execution_time=metadata.get('pipeline_execution_time', 0.0),
            total_steps=metadata.get('total_steps', 0),
            target_language=options.get('target_language') if options else None,

            # Complex metadata (JSON)
            branching_path=metadata.get('branching_path', []),
            document_class=document_class_info,

            # Termination info
            terminated=metadata.get('terminated', False),
            termination_reason=metadata.get('termination_reason'),
            termination_message=metadata.get('termination_message'),
            termination_step=metadata.get('termination_step'),
            matched_value=metadata.get('matched_value'),
        )

        logger.info(f"✅ Document processed successfully: {processing_id}")

        return {
            'status': 'completed',
            'processing_id': processing_id,
            'metrics': {
                'ocr_time': job.ocr_time_seconds,
                'pipeline_time': job.ai_processing_time_seconds,
                'total_time': total_time
            }
        }

    except SoftTimeLimitExceeded as e:
        # Handle timeout gracefully
        logger.error(f"⏱️ Processing timeout for document {processing_id} (exceeded soft time limit)")

        # Update job status using repository
        try:
            if 'job_id_for_updates' in locals():
                job_repo.update(
                    job_id_for_updates,
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
            if 'job_id_for_updates' in locals():
                job_repo.update(
                    job_id_for_updates,
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


@celery_app.task(bind=True, name='process_document')
def process_document(self, processing_id: str, options: dict = None):
    """Background task for document processing (primary task name)."""
    return _process_document_impl(self, processing_id, options)


@celery_app.task(bind=True, name='process_medical_document')
def process_medical_document(self, processing_id: str, options: dict = None):
    """Alias for process_document (backward compatibility)."""
    return _process_document_impl(self, processing_id, options)


def await_sync(coroutine):
    """Helper to run async functions in sync context"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coroutine)


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
