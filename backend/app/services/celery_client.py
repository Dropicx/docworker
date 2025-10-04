"""
Celery Client for Backend

Allows backend to enqueue tasks to the worker service.
"""
import os
import logging
from typing import Optional, Dict, Any
from celery import Celery

logger = logging.getLogger(__name__)

# Create Celery client (connects to same Redis as worker)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

celery_client = Celery(
    'doctranslator_backend',
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Configure client
celery_client.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Berlin',
    enable_utc=True,
    result_expires=3600,  # Task results expire after 1 hour
)

logger.info(f"🔗 Celery client configured with Redis: {REDIS_URL.split('@')[0]}...")


def enqueue_document_processing(processing_id: str, options: Optional[Dict[str, Any]] = None) -> str:
    """
    Enqueue document processing task to worker

    Args:
        processing_id: Processing ID
        options: Processing options (target_language, etc.)

    Returns:
        str: Task ID
    """
    try:
        logger.info(f"📤 Enqueueing document processing: {processing_id}")

        # Send task to worker
        result = celery_client.send_task(
            'process_medical_document',
            args=(processing_id,),
            kwargs={'options': options or {}}
        )

        logger.info(f"✅ Task enqueued: {processing_id} (task_id: {result.id})")
        return result.id

    except Exception as e:
        logger.error(f"❌ Failed to enqueue task for {processing_id}: {str(e)}")
        raise


def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get status of a Celery task

    Args:
        task_id: Task ID

    Returns:
        dict: Task status information
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_client)

    status_info = {
        'task_id': task_id,
        'status': result.status,
        'ready': result.ready(),
        'successful': result.successful() if result.ready() else None,
        'failed': result.failed() if result.ready() else None,
    }

    # Add result or error if complete
    if result.ready():
        if result.successful():
            status_info['result'] = result.result
        elif result.failed():
            status_info['error'] = str(result.info)
    else:
        # Get progress info if available
        if result.info:
            status_info['info'] = result.info

    return status_info


def cancel_task(task_id: str, terminate: bool = False) -> bool:
    """
    Cancel a running task

    Args:
        task_id: Task ID to cancel
        terminate: If True, terminate immediately

    Returns:
        bool: Success status
    """
    try:
        from celery.result import AsyncResult

        result = AsyncResult(task_id, app=celery_client)
        result.revoke(terminate=terminate)

        logger.info(f"🚫 Task cancelled: {task_id} (terminate={terminate})")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to cancel task {task_id}: {str(e)}")
        return False
