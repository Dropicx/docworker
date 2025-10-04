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

        # Update job status to RUNNING
        job.status = StepExecutionStatus.RUNNING
        job.started_at = datetime.now()
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
            logger.info(f"✅ OCR completed in {ocr_time:.2f}s: {len(extracted_text)} characters, confidence: {ocr_confidence:.2%}")

            # ⚡ Step 1.5: LOCAL PII Removal (BEFORE sending to AI pipeline)
            # Check if PII removal is enabled in OCR config
            ocr_config = db.query(OCRConfigurationDB).first()
            pii_enabled = ocr_config.pii_removal_enabled if ocr_config else True

            if pii_enabled:
                logger.info("🔒 Starting local PII removal...")
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

        # Execute pipeline (async method, need to await)
        success, final_output, metadata = await_sync(
            executor.execute_pipeline(
                processing_id=processing_id,
                input_text=extracted_text,
                context=options or {}
            )
        )

        pipeline_time = time.time() - pipeline_start
        job.ai_processing_time_seconds = pipeline_time

        # Check if pipeline succeeded
        if not success:
            raise Exception(f"Pipeline execution failed: {metadata.get('error', 'Unknown error')}")

        # Build result data structure (matches TranslationResult model)
        total_time = time.time() - job.started_at.timestamp()
        result_data = {
            "processing_id": processing_id,
            "original_text": extracted_text,
            "translated_text": final_output,
            "language_translated_text": metadata.get('language_translation', None),
            "target_language": options.get('target_language', None) if options else None,
            "document_type_detected": metadata.get('document_class', 'UNKNOWN'),
            "confidence_score": metadata.get('confidence_score', 0.0),
            "language_confidence_score": metadata.get('language_confidence', None),
            "processing_time_seconds": total_time
        }

        # Update job with final results
        job.status = StepExecutionStatus.COMPLETED
        job.completed_at = datetime.now()
        job.progress_percent = 100
        job.result_data = result_data
        job.total_execution_time_seconds = total_time
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
