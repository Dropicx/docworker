"""
Circuit Breaker Pattern Implementation

Implements the circuit breaker pattern to prevent cascading failures when
external services (OVH AI, Redis) are unhealthy. The circuit breaker has
three states: CLOSED, OPEN, and HALF_OPEN.

State Transitions:
- CLOSED → OPEN: After failure_threshold consecutive failures
- OPEN → HALF_OPEN: After recovery_timeout seconds
- HALF_OPEN → CLOSED: After success_threshold consecutive successes
- HALF_OPEN → OPEN: On any failure

This prevents the application from repeatedly calling failing services,
allowing them time to recover while providing fast failures to clients.
"""

from collections.abc import Callable
from enum import Enum
from functools import wraps
import logging
from threading import Lock
import time
from typing import Any, ParamSpec, TypeVar

from app.core.exceptions import CircuitBreakerError, ServiceUnavailableError

logger = logging.getLogger(__name__)

# Type variables for generic decorators
P = ParamSpec("P")
T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Failing, reject requests immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting external service calls.

    Example:
        >>> cb = CircuitBreaker("ovh-ai", failure_threshold=5, recovery_timeout=60)
        >>> @cb.call
        ... async def call_ovh_api():
        ...     return await ovh_client.process_text(...)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Unique identifier for this circuit breaker
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes before closing from half-open
            recovery_timeout: Seconds to wait before trying again (OPEN → HALF_OPEN)
            expected_exception: Exception type that triggers circuit breaker
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._lock = Lock()

        logger.info(
            f"🔌 Circuit breaker '{name}' initialized: "
            f"failure_threshold={failure_threshold}, "
            f"recovery_timeout={recovery_timeout}s"
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing)."""
        return self.state == CircuitState.OPEN

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        return time.time() - self._last_failure_time >= self.recovery_timeout

    def _handle_success(self) -> None:
        """Record successful call."""
        with self._lock:
            self._failure_count = 0

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                logger.info(
                    f"✅ Circuit '{self.name}': Success in HALF_OPEN "
                    f"({self._success_count}/{self.success_threshold})"
                )

                if self._success_count >= self.success_threshold:
                    logger.info(f"🔌 Circuit '{self.name}': HALF_OPEN → CLOSED (recovered)")
                    self._state = CircuitState.CLOSED
                    self._success_count = 0

    def _handle_failure(self, exception: Exception) -> None:
        """Record failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                logger.warning(f"❌ Circuit '{self.name}': Failed in HALF_OPEN → OPEN")
                self._state = CircuitState.OPEN
                self._success_count = 0
                self._failure_count = 1

            elif self._state == CircuitState.CLOSED:
                logger.warning(
                    f"⚠️ Circuit '{self.name}': Failure {self._failure_count}/{self.failure_threshold}"
                )

                if self._failure_count >= self.failure_threshold:
                    logger.error(
                        f"🔴 Circuit '{self.name}': CLOSED → OPEN "
                        f"(threshold reached: {self._failure_count} failures)"
                    )
                    self._state = CircuitState.OPEN

    def call(self, func: Callable[P, T]) -> Callable[P, T]:
        """
        Decorator to protect a function with circuit breaker.

        Example:
            >>> cb = CircuitBreaker("my-service")
            >>> @cb.call
            ... def my_api_call():
            ...     return requests.get("https://api.example.com")
        """

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Check if circuit is open
            with self._lock:
                current_state = self._state

                if current_state == CircuitState.OPEN:
                    # Check if we should try recovery
                    if self._should_attempt_recovery():
                        logger.info(
                            f"🔄 Circuit '{self.name}': OPEN → HALF_OPEN (attempting recovery)"
                        )
                        self._state = CircuitState.HALF_OPEN
                        self._success_count = 0
                    else:
                        # Fail fast - circuit is open
                        raise CircuitBreakerError(
                            f"Circuit breaker '{self.name}' is OPEN - service unavailable",
                            service_name=self.name,
                            failure_count=self._failure_count,
                            details={
                                "state": "OPEN",
                                "last_failure": self._last_failure_time,
                                "retry_after": int(
                                    self.recovery_timeout - (time.time() - self._last_failure_time)
                                ),
                            },
                        )

            # Try to call the function
            try:
                result = func(*args, **kwargs)
                self._handle_success()
                return result

            except self.expected_exception as e:
                self._handle_failure(e)
                raise

        return wrapper

    async def call_async(self, func: Callable[P, T]) -> Callable[P, T]:
        """
        Async decorator to protect an async function with circuit breaker.

        Example:
            >>> cb = CircuitBreaker("my-service")
            >>> @cb.call_async
            ... async def my_api_call():
            ...     return await httpx.get("https://api.example.com")
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Check if circuit is open
            with self._lock:
                current_state = self._state

                if current_state == CircuitState.OPEN:
                    # Check if we should try recovery
                    if self._should_attempt_recovery():
                        logger.info(
                            f"🔄 Circuit '{self.name}': OPEN → HALF_OPEN (attempting recovery)"
                        )
                        self._state = CircuitState.HALF_OPEN
                        self._success_count = 0
                    else:
                        # Fail fast - circuit is open
                        raise CircuitBreakerError(
                            f"Circuit breaker '{self.name}' is OPEN - service unavailable",
                            service_name=self.name,
                            failure_count=self._failure_count,
                            details={
                                "state": "OPEN",
                                "last_failure": self._last_failure_time,
                                "retry_after": int(
                                    self.recovery_timeout - (time.time() - self._last_failure_time)
                                ),
                            },
                        )

            # Try to call the function
            try:
                result = await func(*args, **kwargs)
                self._handle_success()
                return result

            except self.expected_exception as e:
                self._handle_failure(e)
                raise

        return wrapper

    def get_status(self) -> dict[str, Any]:
        """Get current circuit breaker status."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "failure_threshold": self.failure_threshold,
                "success_threshold": self.success_threshold,
                "recovery_timeout": self.recovery_timeout,
                "last_failure_time": self._last_failure_time,
                "time_until_recovery": max(
                    0, int(self.recovery_timeout - (time.time() - self._last_failure_time))
                )
                if self._state == CircuitState.OPEN
                else 0,
            }

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            logger.info(f"🔄 Circuit '{self.name}': Manual reset to CLOSED")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = 0.0


# ==================== Global Circuit Breakers ====================

# Circuit breaker for OVH AI Endpoints
ovh_ai_breaker = CircuitBreaker(
    name="ovh-ai-api",
    failure_threshold=5,  # Open after 5 consecutive failures
    success_threshold=2,  # Close after 2 consecutive successes
    recovery_timeout=60,  # Wait 60s before trying again
    expected_exception=ServiceUnavailableError,
)

# Circuit breaker for Redis/Celery
redis_breaker = CircuitBreaker(
    name="redis",
    failure_threshold=3,  # Redis failures are more critical
    success_threshold=2,
    recovery_timeout=30,  # Shorter recovery for Redis
    expected_exception=Exception,  # Catch all Redis exceptions
)


def get_circuit_breaker(name: str) -> CircuitBreaker | None:
    """
    Get a circuit breaker by name.

    Args:
        name: Circuit breaker name

    Returns:
        CircuitBreaker instance or None if not found
    """
    breakers = {
        "ovh-ai-api": ovh_ai_breaker,
        "redis": redis_breaker,
    }
    return breakers.get(name)


def get_all_circuit_breakers() -> dict[str, CircuitBreaker]:
    """Get all configured circuit breakers."""
    return {
        "ovh-ai-api": ovh_ai_breaker,
        "redis": redis_breaker,
    }


def get_circuit_breakers_status() -> dict[str, dict[str, Any]]:
    """Get status of all circuit breakers."""
    return {name: cb.get_status() for name, cb in get_all_circuit_breakers().items()}
