"""
Structured Exception Hierarchy

Provides comprehensive, categorized exceptions for improved error handling,
logging, and debugging across the DocTranslator application.
"""

from datetime import datetime, timezone
from typing import Any


class BaseAppError(Exception):
    """
    Base exception for all application-specific exceptions.

    All custom exceptions should inherit from this class for consistent
    error handling and logging throughout the application.

    Attributes:
        message: Human-readable error message
        details: Additional context about the error
        timestamp: When the error occurred
        error_code: Machine-readable error code for API responses
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ):
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now(datetime.UTC)
        self.error_code = error_code or self.__class__.__name__
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
                "timestamp": self.timestamp.isoformat() + "Z",
            }
        }


# ==================== Validation Errors ====================


class ValidationError(BaseAppError):
    """
    Raised when input validation fails.

    Examples:
        - Invalid file format
        - File size exceeds limit
        - Missing required fields
        - Invalid parameter values
    """

    def __init__(
        self, message: str, field: str | None = None, details: dict[str, Any] | None = None
    ):
        super().__init__(message, details, "VALIDATION_ERROR")
        if field:
            self.details["field"] = field


class FileValidationError(ValidationError):
    """Raised when file validation fails."""

    def __init__(
        self,
        message: str,
        filename: str | None = None,
        file_size: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if filename:
            details["filename"] = filename
        if file_size:
            details["file_size"] = file_size
        super().__init__(message, None, details)
        self.error_code = "FILE_VALIDATION_ERROR"


# ==================== External Service Errors ====================


class ExternalServiceError(BaseAppError):
    """
    Base class for external service failures.

    Examples:
        - OVH AI API failures
        - Database connection issues
        - Redis/Celery failures
    """

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if service_name:
            details["service"] = service_name
        super().__init__(message, details, "EXTERNAL_SERVICE_ERROR")


class ServiceUnavailableError(ExternalServiceError):
    """
    Raised when an external service is temporarily unavailable.

    This indicates a transient failure that may succeed on retry.
    Circuit breakers should track these errors.

    Examples:
        - HTTP 503 Service Unavailable
        - Connection timeout
        - Network errors
        - Service temporarily down
    """

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(message, service_name, details)
        self.error_code = "SERVICE_UNAVAILABLE"


class RateLimitError(ExternalServiceError):
    """
    Raised when API rate limits are exceeded.

    Examples:
        - HTTP 429 Too Many Requests
        - OVH AI rate limiting
        - Redis connection pool exhausted
    """

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        retry_after: int | None = None,
        limit: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        if limit:
            details["rate_limit"] = limit
        super().__init__(message, service_name, details)
        self.error_code = "RATE_LIMIT_EXCEEDED"


class AuthenticationError(ExternalServiceError):
    """
    Raised when authentication fails with external services.

    Examples:
        - HTTP 401 Unauthorized
        - Invalid API token
        - Expired credentials
    """

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, service_name, details)
        self.error_code = "AUTHENTICATION_ERROR"


class APITimeoutError(ExternalServiceError):
    """
    Raised when an API call times out.

    This is a transient error suitable for retry with exponential backoff.
    """

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        timeout_seconds: float | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(message, service_name, details)
        self.error_code = "API_TIMEOUT"


# ==================== Processing Errors ====================


class ProcessingError(BaseAppError):
    """
    Raised when document processing fails.

    Examples:
        - OCR extraction failure
        - Translation failure
        - Pipeline step failure
    """

    def __init__(
        self,
        message: str,
        processing_id: str | None = None,
        step: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if processing_id:
            details["processing_id"] = processing_id
        if step:
            details["step"] = step
        super().__init__(message, details, "PROCESSING_ERROR")


class OCRError(ProcessingError):
    """Raised when OCR text extraction fails."""

    def __init__(
        self,
        message: str,
        engine: str | None = None,
        confidence: float | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if engine:
            details["ocr_engine"] = engine
        if confidence is not None:
            details["confidence"] = confidence
        super().__init__(message, None, None, details)
        self.error_code = "OCR_ERROR"


class TranslationError(ProcessingError):
    """Raised when translation fails."""

    def __init__(
        self,
        message: str,
        model: str | None = None,
        source_lang: str | None = None,
        target_lang: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if model:
            details["model"] = model
        if source_lang:
            details["source_language"] = source_lang
        if target_lang:
            details["target_language"] = target_lang
        super().__init__(message, None, None, details)
        self.error_code = "TRANSLATION_ERROR"


class PipelineStepError(ProcessingError):
    """Raised when a specific pipeline step fails."""

    def __init__(
        self,
        message: str,
        step_name: str,
        step_order: int | None = None,
        processing_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        details["step_name"] = step_name
        if step_order is not None:
            details["step_order"] = step_order
        super().__init__(message, processing_id, step_name, details)
        self.error_code = "PIPELINE_STEP_ERROR"


# ==================== Database Errors ====================


class DatabaseError(BaseAppError):
    """
    Raised when database operations fail.

    Examples:
        - Connection failures
        - Query execution errors
        - Constraint violations
    """

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if operation:
            details["operation"] = operation
        super().__init__(message, details, "DATABASE_ERROR")


class ResourceNotFoundError(DatabaseError):
    """Raised when a requested resource is not found in the database."""

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, None, details)
        self.error_code = "RESOURCE_NOT_FOUND"


# ==================== Configuration Errors ====================


class ConfigurationError(BaseAppError):
    """
    Raised when application configuration is invalid or missing.

    Examples:
        - Missing environment variables
        - Invalid configuration values
        - Missing API keys
    """

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, details, "CONFIGURATION_ERROR")


# ==================== Circuit Breaker Errors ====================


class CircuitBreakerError(BaseAppError):
    """
    Raised when a circuit breaker is open and blocks a request.

    This prevents cascading failures by failing fast when a service
    is known to be unhealthy.
    """

    def __init__(
        self,
        message: str,
        service_name: str,
        failure_count: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        details["service"] = service_name
        if failure_count:
            details["failure_count"] = failure_count
        super().__init__(message, details, "CIRCUIT_BREAKER_OPEN")


# ==================== Helper Functions ====================


def is_retryable_error(exception: Exception) -> bool:
    """
    Check if an exception is retryable (transient failure).

    Args:
        exception: The exception to check

    Returns:
        True if the error should be retried, False otherwise
    """
    retryable_types = (
        ServiceUnavailableError,
        APITimeoutError,
        RateLimitError,
    )
    return isinstance(exception, retryable_types)


def get_http_status_code(exception: Exception) -> int:
    """
    Get the appropriate HTTP status code for an exception.

    Args:
        exception: The exception to map

    Returns:
        HTTP status code (400-599)
    """
    status_mapping = {
        ValidationError: 400,
        FileValidationError: 400,
        AuthenticationError: 401,
        ResourceNotFoundError: 404,
        RateLimitError: 429,
        ServiceUnavailableError: 503,
        ConfigurationError: 500,
        DatabaseError: 500,
        ProcessingError: 500,
        CircuitBreakerError: 503,
    }

    for exc_type, status_code in status_mapping.items():
        if isinstance(exception, exc_type):
            return status_code

    # Default status codes for base classes
    if isinstance(exception, BaseAppError):
        return 500

    # Unknown exceptions
    return 500
