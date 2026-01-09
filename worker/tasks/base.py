"""
Base Task Class for Enhanced Error Handling and Retry Logic

Provides retry strategies, error handling, deduplication, and standardized logging.
"""
import logging
import traceback
from typing import Any, Dict, Optional
from datetime import datetime
from celery import Task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

logger = logging.getLogger(__name__)


class BaseDocumentTask(Task):
    """
    Enhanced base task with automatic retry, error handling, and monitoring.

    Features:
    - Exponential backoff retry strategy
    - Enhanced error logging with context
    - Graceful timeout handling
    - Task deduplication support
    - Standardized state management
    """

    # Retry configuration (can be overridden per task)
    autoretry_for = (ConnectionError, TimeoutError)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes
    retry_jitter = True

    # Timeout configuration
    soft_time_limit = 1080  # 18 minutes (from config.py)
    time_limit = 1200  # 20 minutes (from config.py)

    # Task acknowledgment behavior
    acks_late = True
    reject_on_worker_lost = True

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        Called when task is retried.

        Args:
            exc: Exception that caused retry
            task_id: Unique task ID
            args: Task positional arguments
            kwargs: Task keyword arguments
            einfo: Exception info object
        """
        retry_count = self.request.retries
        max_retries = self.retry_kwargs.get('max_retries', 3)

        logger.warning(
            f"🔄 Task retry {retry_count}/{max_retries} - {self.name}",
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'retry_count': retry_count,
                'max_retries': max_retries,
                'exception': str(exc),
                'exception_type': type(exc).__name__
            }
        )

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Called when task fails (after all retries exhausted).

        Args:
            exc: Exception that caused failure
            task_id: Unique task ID
            args: Task positional arguments
            kwargs: Task keyword arguments
            einfo: Exception info object
        """
        logger.error(
            f"❌ Task failed permanently - {self.name}",
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'exception': str(exc),
                'exception_type': type(exc).__name__,
                'traceback': traceback.format_exc(),
                'task_args': args,  # Can't use 'args' - reserved by logging
                'task_kwargs': kwargs
            }
        )

        # Check if this is a timeout failure
        if isinstance(exc, SoftTimeLimitExceeded):
            logger.error(
                f"⏱️ Task exceeded time limit - {self.name}",
                extra={
                    'task_id': task_id,
                    'soft_limit': self.soft_time_limit,
                    'hard_limit': self.time_limit
                }
            )

    def on_success(self, retval, task_id, args, kwargs):
        """
        Called when task completes successfully.

        Args:
            retval: Task return value
            task_id: Unique task ID
            args: Task positional arguments
            kwargs: Task keyword arguments
        """
        logger.info(
            f"✅ Task completed successfully - {self.name}",
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'retry_count': self.request.retries
            }
        )

    def apply_retry_strategy(self, exc: Exception, processing_id: Optional[str] = None) -> None:
        """
        Apply intelligent retry strategy based on exception type.

        Args:
            exc: Exception that occurred
            processing_id: Optional processing ID for logging

        Raises:
            MaxRetriesExceededError: If max retries exceeded
            Exception: Re-raises if not retriable
        """
        # Determine if exception is retriable
        is_retriable = self._is_retriable_exception(exc)

        if not is_retriable:
            logger.error(
                f"❌ Non-retriable exception - {type(exc).__name__}: {str(exc)}",
                extra={
                    'processing_id': processing_id,
                    'task_name': self.name,
                    'exception_type': type(exc).__name__
                }
            )
            raise exc

        # Calculate backoff delay
        retry_count = self.request.retries
        max_retries = self.retry_kwargs.get('max_retries', 3)

        if retry_count >= max_retries:
            logger.error(
                f"❌ Max retries exceeded - {self.name}",
                extra={
                    'processing_id': processing_id,
                    'retry_count': retry_count,
                    'max_retries': max_retries
                }
            )
            raise MaxRetriesExceededError(
                f"Task {self.name} exceeded max retries ({max_retries})"
            )

        # Calculate exponential backoff
        countdown = self._calculate_backoff_delay(retry_count)

        logger.warning(
            f"⏳ Retrying in {countdown}s - {self.name}",
            extra={
                'processing_id': processing_id,
                'retry_count': retry_count + 1,
                'max_retries': max_retries,
                'countdown': countdown,
                'exception': str(exc)
            }
        )

        # Retry with calculated countdown
        raise self.retry(exc=exc, countdown=countdown)

    def _is_retriable_exception(self, exc: Exception) -> bool:
        """
        Determine if exception should trigger retry.

        Args:
            exc: Exception to check

        Returns:
            bool: True if retriable, False otherwise
        """
        # Check if exception type is in autoretry list
        for exc_type in self.autoretry_for:
            if isinstance(exc, exc_type):
                return True

        # Additional retriable exceptions
        retriable_exceptions = (
            # Network and connection errors
            ConnectionError,
            TimeoutError,
            ConnectionResetError,
            ConnectionAbortedError,
            ConnectionRefusedError,

            # Database connection errors
            Exception,  # Will check message for database errors
        )

        # Check for database connection errors by message
        if isinstance(exc, Exception):
            error_msg = str(exc).lower()
            db_error_keywords = [
                'connection refused',
                'connection reset',
                'connection timeout',
                'database is locked',
                'could not connect',
                'too many connections'
            ]

            if any(keyword in error_msg for keyword in db_error_keywords):
                return True

        return isinstance(exc, retriable_exceptions)

    def _calculate_backoff_delay(self, retry_count: int) -> int:
        """
        Calculate exponential backoff delay with jitter.

        Args:
            retry_count: Current retry attempt number

        Returns:
            int: Delay in seconds
        """
        import random

        # Base delay from config (default 60 seconds)
        base_delay = 60

        # Exponential backoff: base_delay * 2^retry_count
        delay = base_delay * (2 ** retry_count)

        # Cap at maximum backoff (from config: 600 seconds = 10 minutes)
        max_backoff = self.retry_backoff_max if hasattr(self, 'retry_backoff_max') else 600
        delay = min(delay, max_backoff)

        # Add jitter (random variation ±25%) to prevent thundering herd
        if self.retry_jitter:
            jitter_range = delay * 0.25
            jitter = random.uniform(-jitter_range, jitter_range)
            delay = int(delay + jitter)

        return max(1, delay)  # Minimum 1 second

    def update_task_progress(
        self,
        state: str,
        progress: int,
        status: str,
        current_step: str,
        processing_id: Optional[str] = None,
        **kwargs
    ):
        """
        Standardized task progress update.

        Args:
            state: Celery task state (PENDING, PROCESSING, SUCCESS, FAILURE)
            progress: Progress percentage (0-100)
            status: Status message
            current_step: Human-readable current step
            processing_id: Optional processing ID
            **kwargs: Additional metadata
        """
        meta = {
            'progress': progress,
            'status': status,
            'current_step': current_step,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }

        if processing_id:
            meta['processing_id'] = processing_id

        self.update_state(state=state, meta=meta)

        logger.debug(
            f"📊 Task progress update - {self.name}",
            extra={
                'task_id': self.request.id,
                'state': state,
                'progress': progress,
                'status': status,
                'current_step': current_step
            }
        )

    def get_task_context(self) -> Dict[str, Any]:
        """
        Get current task execution context.

        Returns:
            dict: Task context information
        """
        return {
            'task_id': self.request.id,
            'task_name': self.name,
            'retry_count': self.request.retries,
            'max_retries': self.retry_kwargs.get('max_retries', 3),
            'eta': self.request.eta,
            'expires': self.request.expires,
            'delivery_info': self.request.delivery_info
        }

    def log_task_start(self, processing_id: Optional[str] = None, **kwargs):
        """
        Log task start with context.

        Args:
            processing_id: Optional processing ID
            **kwargs: Additional context to log
        """
        context = self.get_task_context()
        context.update(kwargs)

        logger.info(
            f"🚀 Task started - {self.name}",
            extra={
                'processing_id': processing_id,
                **context
            }
        )

    def log_task_end(self, processing_id: Optional[str] = None, success: bool = True, **kwargs):
        """
        Log task completion with context.

        Args:
            processing_id: Optional processing ID
            success: Whether task succeeded
            **kwargs: Additional context to log
        """
        context = self.get_task_context()
        context.update(kwargs)

        status_emoji = "✅" if success else "❌"
        status_word = "completed" if success else "failed"

        logger.info(
            f"{status_emoji} Task {status_word} - {self.name}",
            extra={
                'processing_id': processing_id,
                'success': success,
                **context
            }
        )
