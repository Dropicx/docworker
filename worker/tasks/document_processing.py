"""
Document Processing Tasks

Background tasks for medical document translation and processing.
"""
import logging
import sys
import time
from datetime import datetime
from celery import Task
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
    from app.services.modular_pipeline_executor import ModularPipelineExecutor
    from app.services.ocr_engine_manager import OCREngineManager
    from sqlalchemy.orm import Session

    db: Session = next(get_db_session())

    try:
        # Load job from database
        job = db.query(PipelineJobDB).filter_by(processing_id=processing_id).first()

        if not job:
            logger.error(f"❌ Job not found: {processing_id}")
            raise ValueError(f"Job not found: {processing_id}")

        logger.info(f"📋 Loaded job: {job.filename} ({job.file_size} bytes)")

        # Merge options: Celery task options take priority, fallback to job's processing_options
        if not options:
            options = {}
        if job.processing_options:
            # Job's processing_options as base, task options override
            merged_options = {**job.processing_options, **options}
            options = merged_options
            logger.info(f"📋 Processing options: {options}")

        # Update job status to RUNNING
        job.status = StepExecutionStatus.RUNNING
        # Preserve started_at from upload endpoint (includes queue time)
        # Only set if somehow missing (shouldn't happen in normal flow)
        if not job.started_at:
            job.started_at = datetime.now()
            logger.warning("⚠️ started_at was not set by upload endpoint, setting now")
        job.progress_percent = 0
        db.commit()

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
            job.progress_percent = 10
            db.commit()
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
            job.ocr_time_seconds = ocr_time
            db.commit()  # Persist OCR time immediately
            logger.info(f"✅ OCR completed in {ocr_time:.2f}s: {len(extracted_text)} characters, confidence: {ocr_confidence:.2%}")

            # ⚡ Step 1.5: LOCAL PII Removal (BEFORE sending to AI pipeline)
            # Check if PII removal is enabled in OCR config
            ocr_config = db.query(OCRConfigurationDB).first()
            pii_enabled = ocr_config.pii_removal_enabled if ocr_config else True

            if pii_enabled:
                logger.info("🔒 Starting local PII removal...")
                job.progress_percent = 15
                db.commit()
                self.update_state(
                    state='PROCESSING',
                    meta={'progress': 15, 'status': 'pii_removal', 'current_step': 'Entfernung persönlicher Daten'}
                )

                from app.services.optimized_privacy_filter import OptimizedPrivacyFilter

                pii_filter = OptimizedPrivacyFilter()
                pii_start_time = time.time()
                original_length = len(extracted_text)

                extracted_text = pii_filter.remove_pii(extracted_text)

                pii_time_ms = (time.time() - pii_start_time) * 1000
                cleaned_length = len(extracted_text)

                logger.info(f"✅ PII removal completed in {pii_time_ms:.1f}ms")
                logger.info(f"   Original: {original_length} chars → Cleaned: {cleaned_length} chars")
            else:
                logger.info("⏭️  PII removal disabled - skipping privacy filter")

        # Update progress
        job.progress_percent = 20
        db.commit()

        # Step 2: Execute pipeline steps
        logger.info("🔄 Starting pipeline execution...")
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
        success, final_output, metadata = await_sync(
            executor.execute_pipeline(
                processing_id=processing_id,
                input_text=extracted_text,
                context=pipeline_context
            )
        )

        pipeline_time = time.time() - pipeline_start
        job.ai_processing_time_seconds = pipeline_time
        db.commit()  # Persist AI processing time immediately

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

                # Store error details in job before raising exception
                job.error_message = f"[{failed_step}] {error_msg}"
                job.error_step_id = failed_step_id
                db.commit()

                raise Exception(f"Pipeline execution failed at '{failed_step}': {error_msg}")

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
        job.status = StepExecutionStatus.COMPLETED
        job.completed_at = datetime.now()
        job.progress_percent = 100
        job.result_data = result_data
        job.total_execution_time_seconds = total_time
        # Note: job.ocr_time_seconds and job.ai_processing_time_seconds already committed earlier
        db.commit()

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

    except Exception as e:
        logger.error(f"❌ Error processing document {processing_id}: {str(e)}")

        # Update job status to FAILED
        if 'job' in locals():
            job.status = StepExecutionStatus.FAILED
            job.failed_at = datetime.now()
            job.error_message = str(e)
            db.commit()

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
