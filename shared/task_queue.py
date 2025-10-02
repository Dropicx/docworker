"""
Task Queue Utilities

Functions for enqueueing and monitoring Celery tasks.
"""
import logging
from typing import Dict, Any, Optional
from celery.result import AsyncResult

logger = logging.getLogger(__name__)


def enqueue_task(
    celery_app,
    task_name: str,
    task_args: tuple = (),
    task_kwargs: dict = None,
    queue: str = 'default'
) -> str:
    """
    Enqueue a Celery task

    Args:
        celery_app: Celery application instance
        task_name: Name of the task to execute
        task_args: Positional arguments for the task
        task_kwargs: Keyword arguments for the task
        queue: Queue name to send task to

    Returns:
        str: Task ID
    """
    if task_kwargs is None:
        task_kwargs = {}

    logger.info(f"📤 Enqueueing task: {task_name}")

    try:
        result = celery_app.send_task(
            task_name,
            args=task_args,
            kwargs=task_kwargs,
            queue=queue
        )

        logger.info(f"✅ Task enqueued: {task_name} (ID: {result.id})")
        return result.id

    except Exception as e:
        logger.error(f"❌ Failed to enqueue task {task_name}: {str(e)}")
        raise


def get_task_status(celery_app, task_id: str) -> Dict[str, Any]:
    """
    Get status of a Celery task

    Args:
        celery_app: Celery application instance
        task_id: Task ID to check

    Returns:
        dict: Task status information
    """
    result = AsyncResult(task_id, app=celery_app)

    status_info = {
        'task_id': task_id,
        'status': result.status,
        'ready': result.ready(),
        'successful': result.successful() if result.ready() else None,
        'failed': result.failed() if result.ready() else None,
    }

    # Add result or error if task is complete
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


def cancel_task(celery_app, task_id: str, terminate: bool = False) -> bool:
    """
    Cancel a running task

    Args:
        celery_app: Celery application instance
        task_id: Task ID to cancel
        terminate: If True, terminate the task immediately

    Returns:
        bool: True if cancellation was successful
    """
    try:
        result = AsyncResult(task_id, app=celery_app)
        result.revoke(terminate=terminate)

        logger.info(f"🚫 Task cancelled: {task_id} (terminate={terminate})")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to cancel task {task_id}: {str(e)}")
        return False


def get_queue_length(redis_client, queue_name: str = 'celery') -> int:
    """
    Get number of tasks in queue

    Args:
        redis_client: Redis client instance
        queue_name: Name of the Celery queue

    Returns:
        int: Number of tasks in queue
    """
    try:
        return redis_client.llen(queue_name)
    except Exception as e:
        logger.error(f"❌ Failed to get queue length: {str(e)}")
        return -1
