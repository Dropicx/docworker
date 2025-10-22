"""
Tests for Error Handling Infrastructure

Tests the exception hierarchy, circuit breaker, and retry mechanisms.
"""

import asyncio
import time

import pytest

from app.core.circuit_breaker import CircuitBreaker, CircuitState
from app.core.exceptions import (
    APITimeoutError,
    AuthenticationError,
    BaseAppError,
    CircuitBreakerError,
    FileValidationError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
    get_http_status_code,
    is_retryable_error,
)
from app.core.retry_policy import (
    execute_async_with_retries,
    execute_with_retries,
    get_api_retry_policy,
    get_conservative_retry_policy,
    is_transient_error,
)


# ==================== Exception Tests ====================


def test_base_exception_structure():
    """Test that BaseAppError has correct structure."""
    exc = BaseAppError(
        message="Test error",
        details={"key": "value"},
        error_code="TEST_ERROR",
    )

    assert exc.message == "Test error"
    assert exc.details == {"key": "value"}
    assert exc.error_code == "TEST_ERROR"
    assert exc.timestamp is not None

    # Test to_dict
    error_dict = exc.to_dict()
    assert error_dict["error"]["code"] == "TEST_ERROR"
    assert error_dict["error"]["message"] == "Test error"
    assert error_dict["error"]["details"] == {"key": "value"}


def test_validation_error():
    """Test ValidationError with field information."""
    exc = ValidationError(
        message="Invalid input",
        field="email",
        details={"pattern": "email@example.com"},
    )

    assert exc.message == "Invalid input"
    assert exc.details["field"] == "email"
    assert exc.error_code == "VALIDATION_ERROR"


def test_file_validation_error():
    """Test FileValidationError with file information."""
    exc = FileValidationError(
        message="File too large",
        filename="document.pdf",
        file_size=52428800,
    )

    assert exc.message == "File too large"
    assert exc.details["filename"] == "document.pdf"
    assert exc.details["file_size"] == 52428800
    assert exc.error_code == "FILE_VALIDATION_ERROR"


def test_service_unavailable_error():
    """Test ServiceUnavailableError with retry information."""
    exc = ServiceUnavailableError(
        message="OVH API down",
        service_name="ovh-ai-api",
        retry_after=60,
    )

    assert exc.message == "OVH API down"
    assert exc.details["service"] == "ovh-ai-api"
    assert exc.details["retry_after_seconds"] == 60
    assert exc.error_code == "SERVICE_UNAVAILABLE"


def test_resource_not_found_error():
    """Test ResourceNotFoundError."""
    exc = ResourceNotFoundError(
        message="Job not found",
        resource_type="pipeline_job",
        resource_id="abc123",
    )

    assert exc.message == "Job not found"
    assert exc.details["resource_type"] == "pipeline_job"
    assert exc.details["resource_id"] == "abc123"


def test_http_status_code_mapping():
    """Test HTTP status code mapping for exceptions."""
    assert get_http_status_code(ValidationError("test")) == 400
    assert get_http_status_code(AuthenticationError("test")) == 401
    assert get_http_status_code(ResourceNotFoundError("test")) == 404
    assert get_http_status_code(ServiceUnavailableError("test")) == 503
    assert get_http_status_code(CircuitBreakerError("test", "service")) == 503


def test_retryable_error_detection():
    """Test detection of retryable errors."""
    # Retryable
    assert is_retryable_error(ServiceUnavailableError("test"))
    assert is_retryable_error(APITimeoutError("test"))

    # Not retryable
    assert not is_retryable_error(AuthenticationError("test"))
    assert not is_retryable_error(ValidationError("test"))
    assert not is_retryable_error(CircuitBreakerError("test", "service"))


# ==================== Circuit Breaker Tests ====================


def test_circuit_breaker_initialization():
    """Test circuit breaker initial state."""
    cb = CircuitBreaker(
        name="test-service",
        failure_threshold=3,
        recovery_timeout=10,
    )

    assert cb.name == "test-service"
    assert cb.state == CircuitState.CLOSED
    assert cb.is_closed
    assert not cb.is_open


def test_circuit_breaker_opens_after_threshold():
    """Test that circuit opens after failure threshold."""
    cb = CircuitBreaker(
        name="test-service",
        failure_threshold=3,
        expected_exception=ServiceUnavailableError,
    )

    # Create a failing function
    @cb.call
    def failing_func():
        raise ServiceUnavailableError("Service down")

    # Trigger failures
    for _ in range(3):
        with pytest.raises(ServiceUnavailableError):
            failing_func()

    # Circuit should now be open
    assert cb.is_open
    assert cb.state == CircuitState.OPEN


def test_circuit_breaker_blocks_when_open():
    """Test that open circuit blocks requests."""
    cb = CircuitBreaker(
        name="test-service",
        failure_threshold=2,
        recovery_timeout=60,
        expected_exception=Exception,
    )

    @cb.call
    def failing_func():
        raise Exception("Error")

    # Open the circuit
    for _ in range(2):
        with pytest.raises(Exception):
            failing_func()

    assert cb.is_open

    # Next call should raise CircuitBreakerError
    with pytest.raises(CircuitBreakerError) as exc_info:
        failing_func()

    assert "OPEN" in str(exc_info.value)


def test_circuit_breaker_reset():
    """Test manual circuit breaker reset."""
    cb = CircuitBreaker(
        name="test-service",
        failure_threshold=2,
        expected_exception=Exception,
    )

    @cb.call
    def failing_func():
        raise Exception("Error")

    # Open the circuit
    for _ in range(2):
        with pytest.raises(Exception):
            failing_func()

    assert cb.is_open

    # Reset
    cb.reset()

    assert cb.is_closed
    assert cb.get_status()["failure_count"] == 0


def test_circuit_breaker_half_open_transition():
    """Test transition from OPEN to HALF_OPEN after recovery timeout."""
    cb = CircuitBreaker(
        name="test-service",
        failure_threshold=2,
        recovery_timeout=1,  # 1 second for test
        expected_exception=Exception,
    )

    call_count = [0]

    @cb.call
    def sometimes_failing_func():
        call_count[0] += 1
        if call_count[0] <= 2:
            raise Exception("Error")
        return "success"

    # Open the circuit
    for _ in range(2):
        with pytest.raises(Exception):
            sometimes_failing_func()

    assert cb.is_open

    # Wait for recovery timeout
    time.sleep(1.5)

    # Next call should transition to HALF_OPEN and succeed
    result = sometimes_failing_func()
    assert result == "success"


@pytest.mark.asyncio
async def test_circuit_breaker_async():
    """Test circuit breaker with async functions."""
    cb = CircuitBreaker(
        name="test-async",
        failure_threshold=2,
        expected_exception=Exception,
    )

    call_count = [0]

    @cb.call_async
    async def async_func():
        call_count[0] += 1
        if call_count[0] <= 2:
            raise Exception("Error")
        return "success"

    # Open the circuit
    for _ in range(2):
        with pytest.raises(Exception):
            await async_func()

    assert cb.is_open

    # Should raise CircuitBreakerError
    with pytest.raises(CircuitBreakerError):
        await async_func()


# ==================== Retry Policy Tests ====================


def test_retry_with_transient_error():
    """Test that transient errors are retried."""
    call_count = [0]

    def failing_then_success():
        call_count[0] += 1
        if call_count[0] < 3:
            raise ServiceUnavailableError("Temporary failure")
        return "success"

    # First test: Conservative policy (2 attempts) with function that needs 3 attempts
    # Should fail after exhausting retries
    with pytest.raises(ServiceUnavailableError):
        execute_with_retries(
            func=failing_then_success,
            policy=get_conservative_retry_policy(),  # 2 attempts max
            operation_name="test",
        )

    # Verify it tried 2 times
    assert call_count[0] == 2

    # Second test: Conservative policy with function that succeeds on retry
    call_count[0] = 0

    def failing_then_success_v2():
        call_count[0] += 1
        if call_count[0] < 2:  # Fail once, succeed on retry
            raise ServiceUnavailableError("Temporary failure")
        return "success"

    result = execute_with_retries(
        func=failing_then_success_v2,
        policy=get_conservative_retry_policy(),
        operation_name="test",
    )

    assert result == "success"
    assert call_count[0] == 2  # Called twice (1 failure + 1 success)


def test_retry_does_not_retry_auth_errors():
    """Test that authentication errors are not retried."""
    call_count = [0]

    def auth_failure():
        call_count[0] += 1
        raise AuthenticationError("Invalid token")

    with pytest.raises(AuthenticationError):
        execute_with_retries(
            func=auth_failure,
            policy=get_conservative_retry_policy(),
            operation_name="test",
        )

    # Should only be called once (no retries for auth errors)
    assert call_count[0] == 1


@pytest.mark.asyncio
async def test_async_retry_with_transient_error():
    """Test async retry with transient errors."""
    call_count = [0]

    async def failing_then_success():
        call_count[0] += 1
        if call_count[0] < 2:
            raise ServiceUnavailableError("Temporary failure")
        return "success"

    result = await execute_async_with_retries(
        func=failing_then_success,
        policy=get_conservative_retry_policy(),
        operation_name="test",
    )

    assert result == "success"
    assert call_count[0] == 2


def test_transient_error_detection():
    """Test transient error detection logic."""
    # Transient errors
    assert is_transient_error(ServiceUnavailableError("test"))
    assert is_transient_error(APITimeoutError("test"))
    assert is_transient_error(Exception("Connection timeout"))
    assert is_transient_error(Exception("503 Service Unavailable"))

    # Not transient
    assert not is_transient_error(AuthenticationError("test"))
    assert not is_transient_error(ValidationError("test"))
    assert not is_transient_error(CircuitBreakerError("test", "service"))


# ==================== Integration Tests ====================


def test_circuit_breaker_with_retry():
    """Test combining circuit breaker and retry logic."""
    cb = CircuitBreaker(
        name="test-integration",
        failure_threshold=3,
        expected_exception=ServiceUnavailableError,
    )

    call_count = [0]

    @cb.call
    def failing_service():
        call_count[0] += 1
        raise ServiceUnavailableError("Service down")

    # Try with retries - should open circuit after threshold
    for _ in range(3):
        with pytest.raises(ServiceUnavailableError):
            failing_service()

    # Circuit is now open
    assert cb.is_open

    # Retry should fail fast with CircuitBreakerError (not retry transient error)
    with pytest.raises(CircuitBreakerError):
        failing_service()

    # Call count should be 3 (before circuit opened)
    # After circuit opens, CircuitBreakerError is raised before calling the function
    assert call_count[0] == 3
