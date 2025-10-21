"""
Retry Policy Configuration using Tenacity

Provides declarative retry mechanisms with exponential backoff for handling
transient failures in external services (OVH AI, Redis, Database).

Features:
- Exponential backoff with jitter
- Configurable max retries per operation
- Retry only on specific exceptions
- Comprehensive logging
- Before/after retry callbacks
"""

from collections.abc import Callable
import logging
from typing import Any

from tenacity import (
    AsyncRetrying,
    RetryError,
    Retrying,
    before_sleep_log,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.exceptions import CircuitBreakerError, RateLimitError, is_retryable_error

logger = logging.getLogger(__name__)


# ==================== Retry Predicates ====================


def is_transient_error(exception: Exception) -> bool:
    """
    Check if exception is a transient error that should be retried.

    Args:
        exception: The exception to check

    Returns:
        True if error should be retried, False otherwise
    """
    # Never retry circuit breaker errors (they fail fast by design)
    if isinstance(exception, CircuitBreakerError):
        return False

    # Use the helper from exceptions module
    if is_retryable_error(exception):
        return True

    # Check for common transient error patterns in exception messages
    error_msg = str(exception).lower()
    transient_patterns = [
        "timeout",
        "connection",
        "temporary",
        "unavailable",
        "overloaded",
        "503",
        "502",
        "504",
    ]
    return any(pattern in error_msg for pattern in transient_patterns)


# ==================== Retry Policies ====================


def get_default_retry_policy() -> dict[str, Any]:
    """
    Get default retry policy configuration.

    Returns:
        Dictionary with tenacity retry configuration
    """
    return {
        "stop": stop_after_attempt(3),  # Max 3 attempts
        "wait": wait_exponential(multiplier=1, min=2, max=10),  # 2s, 4s, 8s
        "retry": retry_if_exception(is_transient_error),
        "before_sleep": before_sleep_log(logger, logging.WARNING),
        "reraise": True,  # Re-raise the last exception if all retries fail
    }


def get_aggressive_retry_policy() -> dict[str, Any]:
    """
    Get aggressive retry policy for critical operations.

    Uses more retries and longer backoff for important operations
    that must succeed (e.g., database transactions, critical API calls).

    Returns:
        Dictionary with tenacity retry configuration
    """
    return {
        "stop": stop_after_attempt(5),  # Max 5 attempts
        "wait": wait_exponential(multiplier=1, min=4, max=30),  # 4s, 8s, 16s, 30s, 30s
        "retry": retry_if_exception(is_transient_error),
        "before_sleep": before_sleep_log(logger, logging.WARNING),
        "reraise": True,
    }


def get_conservative_retry_policy() -> dict[str, Any]:
    """
    Get conservative retry policy for non-critical operations.

    Uses fewer retries and shorter backoff for operations where
    fast failure is acceptable (e.g., optional enhancements, caching).

    Returns:
        Dictionary with tenacity retry configuration
    """
    return {
        "stop": stop_after_attempt(2),  # Max 2 attempts
        "wait": wait_exponential(multiplier=1, min=1, max=5),  # 1s, 2s
        "retry": retry_if_exception(is_transient_error),
        "before_sleep": before_sleep_log(logger, logging.INFO),
        "reraise": True,
    }


def get_api_retry_policy() -> dict[str, Any]:
    """
    Get retry policy specifically for external API calls (OVH AI).

    Handles rate limiting with longer backoff and respects 429 responses.

    Returns:
        Dictionary with tenacity retry configuration
    """

    def should_retry_api_error(exception: Exception) -> bool:
        """Custom retry logic for API errors."""
        # Always retry transient errors
        if is_transient_error(exception):
            return True

        # Retry rate limits with exponential backoff
        if isinstance(exception, RateLimitError):
            return True

        # Don't retry authentication errors (they won't fix themselves)
        from app.core.exceptions import AuthenticationError

        if isinstance(exception, AuthenticationError):
            return False

        return False

    return {
        "stop": stop_after_attempt(4),  # Max 4 attempts for API calls
        "wait": wait_exponential(multiplier=2, min=4, max=60),  # 4s, 8s, 16s, 32s
        "retry": retry_if_exception(should_retry_api_error),
        "before_sleep": before_sleep_log(logger, logging.WARNING),
        "reraise": True,
    }


def get_database_retry_policy() -> dict[str, Any]:
    """
    Get retry policy for database operations.

    Handles connection pools, deadlocks, and transient DB failures.

    Returns:
        Dictionary with tenacity retry configuration
    """
    from app.core.exceptions import DatabaseError

    return {
        "stop": stop_after_attempt(3),  # Max 3 attempts for DB
        "wait": wait_exponential(multiplier=0.5, min=1, max=5),  # 1s, 2s, 4s
        "retry": retry_if_exception_type(DatabaseError),
        "before_sleep": before_sleep_log(logger, logging.WARNING),
        "reraise": True,
    }


# ==================== Retry Decorators ====================


def with_retries(
    policy: dict[str, Any] | None = None,
    operation_name: str | None = None,
) -> Callable:
    """
    Decorator to add retry logic to a synchronous function.

    Args:
        policy: Retry policy configuration (defaults to get_default_retry_policy())
        operation_name: Name for logging purposes

    Example:
        >>> @with_retries(policy=get_api_retry_policy(), operation_name="OVH API call")
        ... def call_ovh_api():
        ...     return requests.post(...)
    """
    retry_policy = policy or get_default_retry_policy()

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                name = operation_name or func.__name__
                logger.debug(f"🔄 Starting operation with retries: {name}")

                for attempt in Retrying(**retry_policy):
                    with attempt:
                        result = func(*args, **kwargs)
                        if attempt.retry_state.attempt_number > 1:
                            logger.info(
                                f"✅ Operation '{name}' succeeded on attempt "
                                f"{attempt.retry_state.attempt_number}"
                            )
                        return result

            except RetryError as e:
                name = operation_name or func.__name__
                logger.error(
                    f"❌ Operation '{name}' failed after {e.last_attempt.attempt_number} attempts"
                )
                raise e.last_attempt.exception() from e

        return wrapper

    return decorator


def with_async_retries(
    policy: dict[str, Any] | None = None,
    operation_name: str | None = None,
) -> Callable:
    """
    Decorator to add retry logic to an async function.

    Args:
        policy: Retry policy configuration (defaults to get_default_retry_policy())
        operation_name: Name for logging purposes

    Example:
        >>> @with_async_retries(policy=get_api_retry_policy(), operation_name="OVH API call")
        ... async def call_ovh_api():
        ...     return await httpx.post(...)
    """
    retry_policy = policy or get_default_retry_policy()

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            try:
                name = operation_name or func.__name__
                logger.debug(f"🔄 Starting async operation with retries: {name}")

                async for attempt in AsyncRetrying(**retry_policy):
                    with attempt:
                        result = await func(*args, **kwargs)
                        if attempt.retry_state.attempt_number > 1:
                            logger.info(
                                f"✅ Operation '{name}' succeeded on attempt "
                                f"{attempt.retry_state.attempt_number}"
                            )
                        return result

            except RetryError as e:
                name = operation_name or func.__name__
                logger.error(
                    f"❌ Async operation '{name}' failed after "
                    f"{e.last_attempt.attempt_number} attempts"
                )
                raise e.last_attempt.exception() from e

        return wrapper

    return decorator


# ==================== Helper Functions ====================


def execute_with_retries(
    func: Callable,
    policy: dict[str, Any] | None = None,
    operation_name: str | None = None,
) -> Any:
    """
    Execute a function with retry logic (manual, non-decorator approach).

    Args:
        func: Function to execute
        policy: Retry policy configuration
        operation_name: Name for logging

    Returns:
        Function result

    Example:
        >>> result = execute_with_retries(
        ...     lambda: requests.get("https://api.example.com"),
        ...     policy=get_api_retry_policy(),
        ...     operation_name="Fetch data"
        ... )
    """
    retry_policy = policy or get_default_retry_policy()
    name = operation_name or "operation"

    try:
        logger.debug(f"🔄 Executing '{name}' with retries")

        for attempt in Retrying(**retry_policy):
            with attempt:
                result = func()
                if attempt.retry_state.attempt_number > 1:
                    logger.info(
                        f"✅ Operation '{name}' succeeded on attempt "
                        f"{attempt.retry_state.attempt_number}"
                    )
                return result

    except RetryError as e:
        logger.error(f"❌ Operation '{name}' failed after {e.last_attempt.attempt_number} attempts")
        raise e.last_attempt.exception() from e


async def execute_async_with_retries(
    func: Callable,
    policy: dict[str, Any] | None = None,
    operation_name: str | None = None,
) -> Any:
    """
    Execute an async function with retry logic (manual, non-decorator approach).

    Args:
        func: Async function to execute
        policy: Retry policy configuration
        operation_name: Name for logging

    Returns:
        Function result

    Example:
        >>> result = await execute_async_with_retries(
        ...     lambda: httpx.AsyncClient().get("https://api.example.com"),
        ...     policy=get_api_retry_policy(),
        ...     operation_name="Fetch data"
        ... )
    """
    retry_policy = policy or get_default_retry_policy()
    name = operation_name or "async operation"

    try:
        logger.debug(f"🔄 Executing async '{name}' with retries")

        async for attempt in AsyncRetrying(**retry_policy):
            with attempt:
                result = await func()
                if attempt.retry_state.attempt_number > 1:
                    logger.info(
                        f"✅ Async operation '{name}' succeeded on attempt "
                        f"{attempt.retry_state.attempt_number}"
                    )
                return result

    except RetryError as e:
        logger.error(
            f"❌ Async operation '{name}' failed after {e.last_attempt.attempt_number} attempts"
        )
        raise e.last_attempt.exception() from e
