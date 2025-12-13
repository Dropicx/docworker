"""Celery Client for Backend-Worker Communication.

Lightweight Celery client that enables FastAPI backend to enqueue asynchronous
document processing tasks to the worker service. Provides task queuing, status
monitoring, and cancellation capabilities via Redis message broker.

**Architecture**:
    - Backend (FastAPI): Enqueues tasks via this client
    - Redis: Message broker for task queue
    - Worker (Celery): Processes tasks asynchronously
    - Separation: Backend never blocks on long-running AI processing

**Message Flow**:
    1. User uploads document → Backend validates & stores
    2. Backend calls enqueue_document_processing() → Task to Redis queue
    3. Worker picks up task → Processes document through pipeline
    4. Worker updates database → Backend polls status
    5. User retrieves results → Backend serves from database

**Configuration**:
    - Broker: Redis (REDIS_URL env var, default: redis://localhost:6379/0)
    - Backend: Same Redis instance (stores task results)
    - Serialization: JSON (task_serializer, result_serializer)
    - Timezone: Europe/Berlin with UTC enabled
    - Result expiry: 1 hour (result_expires=3600)

**Environment Variables**:
    - REDIS_URL: Redis connection string (required for production)
      * Format: redis://[:password@]hostname[:port]/db
      * Example: redis://user:pass@localhost:6379/0

**Usage Example**:
    >>> from app.services.celery_client import enqueue_document_processing, get_task_status
    >>>
    >>> # Backend enqueues document processing
    >>> task_id = enqueue_document_processing(
    ...     processing_id="abc123",
    ...     options={"target_language": "EN"}
    ... )
    >>> print(f"Task ID: {task_id}")
    Task ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
    >>>
    >>> # Poll task status
    >>> status = get_task_status(task_id)
    >>> print(status)
    {
        'task_id': 'a1b2c3d4...',
        'status': 'PROGRESS',
        'ready': False,
        'info': {'step': 'TRANSLATION', 'progress': 0.6}
    }
    >>>
    >>> # Cancel if needed
    >>> cancel_task(task_id, terminate=False)

**Task States** (Celery standard):
    - PENDING: Task queued, not yet picked up by worker
    - STARTED: Worker started processing
    - PROGRESS: Worker reporting progress updates
    - SUCCESS: Task completed successfully
    - FAILURE: Task failed with error
    - REVOKED: Task cancelled before completion

**Production Deployment**:
    - Redis: Use managed Redis (e.g., Railway, AWS ElastiCache)
    - Connection pooling: Redis handles multiple backend/worker connections
    - Result persistence: Task results stored in Redis for 1 hour
    - Monitoring: Use Flower (Celery monitoring tool) for visibility

**Error Handling**:
    - Redis connection errors propagate to caller
    - Task enqueueing failures logged and raised
    - Worker failures: Task status shows FAILURE with error message

Note:
    **Client Only**: This module creates Celery client, not worker.
    Worker defined in separate worker/ directory with task implementations.

    **No Task Definitions**: Backend only enqueues tasks via send_task().
    Actual task logic (process_medical_document) resides in worker service.

    **Shared Redis**: Backend and worker must connect to same Redis instance
    for task queue to function. Verify REDIS_URL matches across services.
"""

import logging
import os
from typing import Any

from celery import Celery

logger = logging.getLogger(__name__)

# Create Celery client (connects to same Redis as worker)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_client = Celery("doctranslator_backend", broker=REDIS_URL, backend=REDIS_URL)

# Configure client with task routing (matches worker config)
celery_client.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Berlin",
    enable_utc=True,
    result_expires=3600,  # Task results expire after 1 hour
    # Task routing - ensures tasks go to correct priority queues
    task_routes={
        "process_medical_document": {"queue": "high_priority"},
        "cleanup_orphaned_jobs": {"queue": "maintenance"},
        "cleanup_celery_results": {"queue": "maintenance"},
        "cleanup_old_files": {"queue": "maintenance"},
        "database_maintenance": {"queue": "maintenance"},
    },
)

logger.info(f"🔗 Celery client configured with Redis: {REDIS_URL.split('@')[0]}...")
logger.info("📋 Task routing: process_medical_document → high_priority queue")


def test_privacy_filter_via_worker(text: str, timeout: int = 30) -> dict[str, Any]:
    """Test privacy filter using the worker's NER capabilities.

    Sends text to worker for PII detection and removal. Uses worker's spaCy model
    for intelligent name recognition not available in backend service.

    Args:
        text: Text to process through privacy filter
        timeout: Maximum seconds to wait for result (default: 30)

    Returns:
        dict: Processing result with cleaned text and metadata:
            - status: "success" or "error"
            - input_length: Original text length
            - output_length: Cleaned text length
            - cleaned_text: Text with PII removed
            - processing_time_ms: Time taken in milliseconds
            - pii_types_detected: List of PII types found
            - entities_detected: Number of entities removed
            - quality_score: Quality score (0-100)
            - review_recommended: Whether manual review is suggested
            - passes_performance_target: Whether <100ms target was met

    Raises:
        TimeoutError: If worker doesn't respond within timeout
        Exception: If task fails or worker error occurs
    """
    try:
        logger.info(f"📤 Sending privacy filter test to worker ({len(text)} chars)")

        result = celery_client.send_task(
            "test_privacy_filter",
            args=(text,),
            queue="default"
        )

        # Wait for result with timeout
        task_result = result.get(timeout=timeout)

        if task_result.get("status") == "error":
            raise Exception(task_result.get("error", "Unknown worker error"))

        logger.info(f"✅ Privacy filter test completed via worker")
        return task_result

    except Exception as e:
        logger.error(f"❌ Privacy filter test failed: {str(e)}")
        raise


def get_privacy_filter_status_via_worker(timeout: int = 10) -> dict[str, Any]:
    """Get privacy filter capabilities from worker.

    Queries worker for filter status including NER availability, spaCy model,
    and database counts. Reflects actual production processing capabilities.

    Args:
        timeout: Maximum seconds to wait for result (default: 10)

    Returns:
        dict: Filter capabilities and statistics:
            - status: "success" or "error"
            - filter_capabilities: {has_ner, spacy_model, removal_method, custom_terms_loaded}
            - detection_stats: {pii_types_count, medical_terms_count, drug_database_count, ...}

    Raises:
        TimeoutError: If worker doesn't respond within timeout
        Exception: If task fails or worker error occurs
    """
    try:
        logger.info("📤 Requesting privacy filter status from worker")

        result = celery_client.send_task(
            "get_privacy_filter_status",
            queue="default"
        )

        # Wait for result with timeout
        task_result = result.get(timeout=timeout)

        if task_result.get("status") == "error":
            raise Exception(task_result.get("error", "Unknown worker error"))

        logger.info(f"✅ Got privacy filter status from worker (NER: {task_result.get('filter_capabilities', {}).get('has_ner')})")
        return task_result

    except Exception as e:
        logger.error(f"❌ Failed to get privacy filter status: {str(e)}")
        raise


def enqueue_document_processing(processing_id: str, options: dict[str, Any] | None = None) -> str:
    """Enqueue asynchronous document processing task to worker via Redis.

    Sends document processing request to Celery worker through Redis message queue.
    Non-blocking operation - returns immediately with task ID for status tracking.
    Worker processes document through full AI pipeline asynchronously.

    Args:
        processing_id: Unique document processing identifier (UUID) from database
        options: Processing configuration dict (default: {}), may include:
            - target_language (str): Output language code (e.g., "EN", "FR")
            - skip_ocr (bool): Skip OCR if text already extracted
            - priority (str): Task priority ("high", "normal", "low")
            - custom fields per pipeline configuration

    Returns:
        str: Celery task ID (UUID) for tracking task status and results

    Raises:
        Exception: If Redis connection fails or task enqueueing fails

    Example:
        >>> # Basic enqueueing
        >>> task_id = enqueue_document_processing("doc_abc123")
        >>> print(f"Task queued: {task_id}")
        Task queued: a1b2c3d4-e5f6-7890-abcd-ef1234567890
        >>>
        >>> # With options
        >>> task_id = enqueue_document_processing(
        ...     processing_id="doc_abc123",
        ...     options={
        ...         "target_language": "EN",
        ...         "skip_ocr": False,
        ...         "priority": "high"
        ...     }
        ... )
        >>>
        >>> # Monitor task
        >>> import time
        >>> while True:
        ...     status = get_task_status(task_id)
        ...     if status['ready']:
        ...         break
        ...     time.sleep(1)

    Note:
        **Task Routing**:
        Sends to 'process_medical_document' task on worker.
        Worker must have matching task definition registered.

        **Error Propagation**:
        Redis connection errors and enqueueing failures raise exceptions.
        Caller should handle and return appropriate HTTP error to user.

        **Result Storage**:
        Task result stored in Redis for 1 hour (result_expires=3600).
        After expiry, result deleted but database still has processing output.

        **Idempotency**:
        Same processing_id can be enqueued multiple times (creates separate tasks).
        Worker should check database status to avoid duplicate processing.

        **Performance**:
        Enqueueing typically <10ms. Worker processing time: 30s-10min depending
        on document complexity and AI model performance.
    """
    try:
        logger.info(f"📤 Enqueueing document processing: {processing_id}")

        # Send task to worker
        result = celery_client.send_task(
            "process_medical_document", args=(processing_id,), kwargs={"options": options or {}}
        )

        logger.info(f"✅ Task enqueued: {processing_id} (task_id: {result.id})")
        return result.id

    except Exception as e:
        logger.error(f"❌ Failed to enqueue task for {processing_id}: {str(e)}")
        raise


def get_task_status(task_id: str) -> dict[str, Any]:
    """Query current status and result of Celery task from Redis.

    Retrieves task state, progress information, and results/errors from Redis
    backend. Used for polling-based status updates to frontend or monitoring dashboards.

    Args:
        task_id: Celery task ID (UUID) returned from enqueue_document_processing()

    Returns:
        dict[str, Any]: Task status dict with keys:
            - task_id (str): Task identifier (same as input)
            - status (str): Celery task state (PENDING, STARTED, PROGRESS, SUCCESS, FAILURE, REVOKED)
            - ready (bool): True if task completed (success or failure)
            - successful (bool|None): True if completed successfully, None if not ready
            - failed (bool|None): True if failed, None if not ready
            - result (Any): Task return value if successful (present when successful=True)
            - error (str): Error message if failed (present when failed=True)
            - info (dict): Progress information if in progress (present when status=PROGRESS)

    Example:
        >>> task_id = enqueue_document_processing("doc_abc123")
        >>>
        >>> # Poll during processing
        >>> status = get_task_status(task_id)
        >>> print(status)
        {
            'task_id': 'a1b2c3d4...',
            'status': 'PROGRESS',
            'ready': False,
            'successful': None,
            'failed': None,
            'info': {'current_step': 'TRANSLATION', 'progress': 0.6}
        }
        >>>
        >>> # After completion
        >>> status = get_task_status(task_id)
        >>> if status['successful']:
        ...     print(f"Result: {status['result']}")
        >>> elif status['failed']:
        ...     print(f"Error: {status['error']}")

    Note:
        **Task States**:
        - PENDING: Queued, not started
        - STARTED: Worker picked up task
        - PROGRESS: Worker reporting progress (custom state)
        - SUCCESS: Completed successfully
        - FAILURE: Failed with error
        - REVOKED: Cancelled by cancel_task()

        **Result Expiry**:
        Task results auto-deleted after 1 hour (result_expires=3600).
        Status query after expiry returns PENDING (can't distinguish from never-queued).

        **Progress Updates**:
        Worker can update 'info' field during processing:
        ```python
        self.update_state(state='PROGRESS', meta={'current_step': 'TRANSLATION'})
        ```

        **Performance**:
        Redis lookup typically <5ms. Safe for polling every 1-5 seconds.
        For real-time updates, consider WebSocket push notifications instead.

        **No Errors Raised**:
        Always returns dict. Check status['status'] for actual state.
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_client)

    status_info = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "failed": result.failed() if result.ready() else None,
    }

    # Add result or error if complete
    if result.ready():
        if result.successful():
            status_info["result"] = result.result
        elif result.failed():
            status_info["error"] = str(result.info)
    else:
        # Get progress info if available
        if result.info:
            status_info["info"] = result.info

    return status_info


def cancel_task(task_id: str, terminate: bool = False) -> bool:
    """Cancel or terminate a queued/running Celery task.

    Sends revocation signal to worker to stop task processing. Behavior depends
    on terminate flag and task state. Safe to call on already-completed tasks.

    Args:
        task_id: Celery task ID (UUID) to cancel
        terminate: Termination mode (default: False):
            - False (soft cancel): Task marked as revoked, worker checks at next safe point
            - True (hard terminate): SIGTERM sent to worker process (immediate stop)

    Returns:
        bool: True if revocation signal sent successfully, False if error occurred

    Example:
        >>> task_id = enqueue_document_processing("doc_abc123")
        >>>
        >>> # User cancels processing
        >>> # Soft cancel (graceful, recommended)
        >>> success = cancel_task(task_id, terminate=False)
        >>> if success:
        ...     print("Task revoked, worker will stop at next checkpoint")
        >>>
        >>> # Hard terminate (for stuck tasks)
        >>> success = cancel_task(task_id, terminate=True)
        >>> if success:
        ...     print("Worker process terminated immediately")
        >>>
        >>> # Check if cancelled
        >>> status = get_task_status(task_id)
        >>> print(status['status'])
        'REVOKED'

    Note:
        **Soft Cancel (terminate=False)**:
        - Default and recommended for most cases
        - Worker checks revoked status between pipeline steps
        - Allows graceful cleanup (close files, save partial results)
        - Task may complete if already in final step
        - Status eventually shows REVOKED

        **Hard Terminate (terminate=True)**:
        - Use only for stuck/hung tasks
        - Sends SIGTERM to worker OS process
        - Immediate stop, no cleanup
        - May leave database in inconsistent state
        - Worker restarts after termination

        **Timing**:
        - Queued tasks (PENDING): Immediate revocation, never start
        - Running tasks: Depends on mode (soft=next checkpoint, hard=immediate)
        - Completed tasks: No effect (already SUCCESS/FAILURE)

        **Error Handling**:
        Exceptions logged and return False. Never raises.
        Common errors: Redis connection failure, invalid task_id.

        **Database Cleanup**:
        Consider updating database status after cancellation:
        ```python
        if cancel_task(task_id):
            db.update_processing_status(processing_id, "CANCELLED")
        ```

        **Worker Behavior**:
        Worker must check self.request.id against revoked tasks.
        Default Celery workers handle this automatically.
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
