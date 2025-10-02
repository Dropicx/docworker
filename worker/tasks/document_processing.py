"""
Document Processing Tasks

Background tasks for medical document translation and processing.
"""
import logging
from celery import Task
from worker.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='process_medical_document')
def process_medical_document(self, processing_id: str, options: dict = None):
    """
    Background task for processing medical documents

    Args:
        processing_id: Unique identifier for the processing job
        options: Optional processing parameters (target_language, etc.)

    Returns:
        dict: Processing result with status and data
    """
    logger.info(f"📄 Processing document: {processing_id}")

    try:
        # Update task state to PROCESSING
        self.update_state(
            state='PROCESSING',
            meta={'progress': 0, 'status': 'starting'}
        )

        # Import here to avoid circular dependencies
        import sys
        sys.path.insert(0, '/app/backend')
        from app.services.document_processor import process_document_complete

        # Update progress
        self.update_state(
            state='PROCESSING',
            meta={'progress': 10, 'status': 'initializing'}
        )

        # Process document (this calls the existing backend processing logic)
        result = process_document_complete(processing_id, options)

        # Update progress
        self.update_state(
            state='PROCESSING',
            meta={'progress': 90, 'status': 'finalizing'}
        )

        logger.info(f"✅ Document processed successfully: {processing_id}")

        return {
            'status': 'completed',
            'processing_id': processing_id,
            'result': result
        }

    except Exception as e:
        logger.error(f"❌ Error processing document {processing_id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'processing_id': processing_id}
        )
        raise


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
