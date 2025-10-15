# Error Handling & Reliability

This document describes the comprehensive error handling and reliability system implemented in DocTranslator.

## Overview

The system provides:
- **Structured Exception Hierarchy** - Categorized exceptions for clear error handling
- **Circuit Breaker Pattern** - Prevents cascading failures when services are down
- **Retry Mechanisms** - Automatic retry with exponential backoff for transient failures
- **Standardized Error Responses** - Consistent JSON error format across all APIs
- **Comprehensive Logging** - Detailed error tracking and debugging information

## Exception Hierarchy

All application exceptions inherit from `BaseAppException` and provide:
- Human-readable error messages
- Machine-readable error codes
- Additional context (details dictionary)
- Timestamp tracking
- Standardized JSON serialization

### Exception Categories

#### Validation Errors
```python
from app.core.exceptions import ValidationError, FileValidationError

# Input validation
raise ValidationError("Invalid target language", field="target_language")

# File validation
raise FileValidationError(
    "File size exceeds 50MB limit",
    filename="document.pdf",
    file_size=52428800
)
```

#### External Service Errors
```python
from app.core.exceptions import (
    ServiceUnavailableError,
    RateLimitError,
    AuthenticationError,
    APITimeoutError
)

# Service temporarily down
raise ServiceUnavailableError(
    "OVH AI API is temporarily unavailable",
    service_name="ovh-ai-api",
    retry_after=60
)

# Rate limit exceeded
raise RateLimitError(
    "API rate limit exceeded",
    service_name="ovh-ai-api",
    retry_after=30,
    limit=100
)

# Authentication failure
raise AuthenticationError(
    "Invalid API token",
    service_name="ovh-ai-api"
)

# Timeout
raise APITimeoutError(
    "API request timed out",
    service_name="ovh-ai-api",
    timeout_seconds=60.0
)
```

#### Processing Errors
```python
from app.core.exceptions import (
    ProcessingError,
    OCRError,
    TranslationError,
    PipelineStepError
)

# OCR failure
raise OCRError(
    "Failed to extract text from image",
    engine="qwen-2.5-vl",
    confidence=0.3
)

# Translation failure
raise TranslationError(
    "Translation failed",
    model="llama-3.3-70b",
    source_lang="de",
    target_lang="en"
)

# Pipeline step failure
raise PipelineStepError(
    "Step failed to complete",
    step_name="MEDICAL_VALIDATION",
    step_order=2,
    processing_id="abc123"
)
```

#### Database Errors
```python
from app.core.exceptions import DatabaseError, ResourceNotFoundError

# Resource not found
raise ResourceNotFoundError(
    "Processing job not found",
    resource_type="pipeline_job",
    resource_id="abc123"
)

# Database operation failure
raise DatabaseError(
    "Failed to update job status",
    operation="update"
)
```

## Circuit Breaker Pattern

Circuit breakers prevent cascading failures by failing fast when services are unhealthy.

### States
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Service failing, reject requests immediately
- **HALF_OPEN**: Testing if service recovered

### Configuration

```python
from app.core.circuit_breaker import CircuitBreaker, ovh_ai_breaker

# Create custom circuit breaker
cb = CircuitBreaker(
    name="my-service",
    failure_threshold=5,        # Open after 5 failures
    success_threshold=2,        # Close after 2 successes
    recovery_timeout=60,        # Wait 60s before retry
    expected_exception=Exception
)
```

### Usage

```python
from app.core.circuit_breaker import ovh_ai_breaker
from app.core.exceptions import ServiceUnavailableError

# Synchronous function
@ovh_ai_breaker.call
def call_ovh_api():
    response = requests.post(...)
    if response.status_code == 503:
        raise ServiceUnavailableError("OVH API unavailable")
    return response.json()

# Async function
@ovh_ai_breaker.call_async
async def call_ovh_api_async():
    response = await httpx.post(...)
    if response.status_code == 503:
        raise ServiceUnavailableError("OVH API unavailable")
    return response.json()
```

### Global Circuit Breakers

Pre-configured circuit breakers are available:
- `ovh_ai_breaker` - For OVH AI Endpoints
- `redis_breaker` - For Redis/Celery operations

### Monitoring

```python
from app.core.circuit_breaker import get_circuit_breakers_status

# Get status of all circuit breakers
status = get_circuit_breakers_status()
# {
#   "ovh-ai-api": {
#     "name": "ovh-ai-api",
#     "state": "closed",
#     "failure_count": 0,
#     "failure_threshold": 5,
#     "time_until_recovery": 0
#   }
# }
```

## Retry Policies

Automatic retry with exponential backoff for transient failures.

### Built-in Policies

```python
from app.core.retry_policy import (
    get_default_retry_policy,
    get_api_retry_policy,
    get_aggressive_retry_policy,
    get_conservative_retry_policy,
    get_database_retry_policy,
)

# Default: 3 attempts, 2s, 4s, 8s backoff
default_policy = get_default_retry_policy()

# API calls: 4 attempts, 4s, 8s, 16s, 32s backoff
api_policy = get_api_retry_policy()

# Critical operations: 5 attempts, 4s, 8s, 16s, 30s, 30s backoff
aggressive_policy = get_aggressive_retry_policy()

# Non-critical: 2 attempts, 1s, 2s backoff
conservative_policy = get_conservative_retry_policy()

# Database: 3 attempts, 1s, 2s, 4s backoff
db_policy = get_database_retry_policy()
```

### Using Decorators

```python
from app.core.retry_policy import with_retries, with_async_retries, get_api_retry_policy

# Synchronous function with retries
@with_retries(policy=get_api_retry_policy(), operation_name="Call OVH API")
def call_api():
    response = requests.post(...)
    if response.status_code >= 500:
        raise ServiceUnavailableError("API error")
    return response.json()

# Async function with retries
@with_async_retries(policy=get_api_retry_policy(), operation_name="Call OVH API")
async def call_api_async():
    response = await httpx.post(...)
    if response.status_code >= 500:
        raise ServiceUnavailableError("API error")
    return response.json()
```

### Manual Execution

```python
from app.core.retry_policy import execute_with_retries, execute_async_with_retries

# Synchronous
result = execute_with_retries(
    func=lambda: make_api_call(),
    policy=get_api_retry_policy(),
    operation_name="API call"
)

# Async
result = await execute_async_with_retries(
    func=lambda: make_api_call_async(),
    policy=get_api_retry_policy(),
    operation_name="API call"
)
```

### What Gets Retried?

The system automatically identifies transient errors:
- `ServiceUnavailableError`
- `APITimeoutError`
- `RateLimitError`
- Errors containing keywords: "timeout", "connection", "temporary", "unavailable", "503", "502", "504"

**Note**: `CircuitBreakerError` is never retried (fail fast by design).

## Error Response Format

All API errors return standardized JSON:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "File size exceeds limit",
    "status_code": 400,
    "timestamp": "2025-01-15T10:30:00Z",
    "details": {
      "field": "file",
      "max_size": 52428800,
      "actual_size": 104857600
    },
    "request_id": "abc123"
  }
}
```

### HTTP Status Codes

| Exception Type | Status Code | Description |
|---|---|---|
| `ValidationError` | 400 | Bad Request - Invalid input |
| `FileValidationError` | 400 | Bad Request - Invalid file |
| `AuthenticationError` | 401 | Unauthorized - Invalid credentials |
| `ResourceNotFoundError` | 404 | Not Found - Resource doesn't exist |
| `RateLimitError` | 429 | Too Many Requests - Rate limit exceeded |
| `ServiceUnavailableError` | 503 | Service Unavailable - Temporary failure |
| `CircuitBreakerError` | 503 | Service Unavailable - Circuit open |
| `ProcessingError` | 500 | Internal Server Error - Processing failed |
| `DatabaseError` | 500 | Internal Server Error - DB operation failed |
| `ConfigurationError` | 500 | Internal Server Error - Invalid config |

## Combining Circuit Breaker + Retry

For maximum resilience, combine both patterns:

```python
from app.core.circuit_breaker import ovh_ai_breaker
from app.core.retry_policy import with_async_retries, get_api_retry_policy
from app.core.exceptions import ServiceUnavailableError, APITimeoutError

@with_async_retries(policy=get_api_retry_policy(), operation_name="OVH AI call")
@ovh_ai_breaker.call_async
async def call_ovh_with_protection():
    """
    This function is protected by:
    1. Circuit breaker (fails fast if service is down)
    2. Retry logic (retries transient failures)
    3. Proper exception handling
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                "https://api.ovh.com/endpoint",
                json={"prompt": "..."}
            )

            if response.status_code == 503:
                raise ServiceUnavailableError(
                    "OVH AI temporarily unavailable",
                    service_name="ovh-ai-api",
                    retry_after=30
                )

            if response.status_code == 401:
                raise AuthenticationError(
                    "Invalid OVH API token",
                    service_name="ovh-ai-api"
                )

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as e:
            raise APITimeoutError(
                "OVH AI request timed out",
                service_name="ovh-ai-api",
                timeout_seconds=60.0
            ) from e
        except httpx.RequestError as e:
            raise ServiceUnavailableError(
                f"OVH AI connection error: {e}",
                service_name="ovh-ai-api"
            ) from e
```

## Migration Guide

### Before (Old Code)
```python
try:
    response = await client.chat.completions.create(...)
    return response.choices[0].message.content
except Exception as e:
    logger.error(f"API error: {e}")
    return f"Error: {str(e)}"
```

### After (New Code)
```python
from app.core.circuit_breaker import ovh_ai_breaker
from app.core.retry_policy import with_async_retries, get_api_retry_policy
from app.core.exceptions import ServiceUnavailableError, APITimeoutError

@with_async_retries(policy=get_api_retry_policy())
@ovh_ai_breaker.call_async
async def process_with_ai():
    try:
        response = await client.chat.completions.create(...)
        return response.choices[0].message.content
    except asyncio.TimeoutError as e:
        raise APITimeoutError(
            "AI request timed out",
            service_name="ovh-ai-api",
            timeout_seconds=60.0
        ) from e
    except Exception as e:
        raise ServiceUnavailableError(
            f"AI service error: {e}",
            service_name="ovh-ai-api"
        ) from e
```

## Monitoring & Debugging

### Check Circuit Breaker Status

```python
from app.core.circuit_breaker import get_all_circuit_breakers

# Get all breakers
breakers = get_all_circuit_breakers()
for name, breaker in breakers.items():
    status = breaker.get_status()
    print(f"{name}: {status['state']} (failures: {status['failure_count']})")
```

### Reset Circuit Breaker

```python
from app.core.circuit_breaker import ovh_ai_breaker

# Manually reset to CLOSED state
ovh_ai_breaker.reset()
```

### Logging

All error handling components provide comprehensive logging:
- Circuit breaker state changes
- Retry attempts
- Exception details
- Request context

## Best Practices

1. **Use Specific Exceptions**: Choose the most specific exception type
2. **Provide Context**: Include relevant details in exception constructors
3. **Chain Exceptions**: Use `raise ... from e` to preserve stack traces
4. **Log Appropriately**: Let middleware handle logging, don't duplicate
5. **Fail Fast**: Don't retry authentication errors or validation errors
6. **Monitor Circuit Breakers**: Track their state in production
7. **Test Error Paths**: Write tests for error scenarios
8. **Document Error Codes**: Keep error codes consistent across services

## Testing

```python
import pytest
from app.core.exceptions import ServiceUnavailableError
from app.core.circuit_breaker import CircuitBreaker

def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker("test", failure_threshold=3)

    # Simulate failures
    for _ in range(3):
        try:
            @cb.call
            def failing_func():
                raise ServiceUnavailableError("Service down")
            failing_func()
        except ServiceUnavailableError:
            pass

    # Circuit should now be open
    assert cb.is_open

    # Next call should fail fast with CircuitBreakerError
    with pytest.raises(CircuitBreakerError):
        @cb.call
        def another_call():
            return "success"
        another_call()
```

## Configuration

Environment variables for error handling:
- `LOG_LEVEL`: Set to `DEBUG` for detailed retry/circuit breaker logs
- `DEBUG`: Set to `true` to include stack traces in error responses (dev only)

## Dependencies

- `tenacity==8.2.3` - Retry mechanisms
- `pybreaker==1.1.1` - Circuit breaker pattern (alternative implementation)

Note: This implementation uses a custom circuit breaker for better integration.
