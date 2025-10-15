"""
Error Handling Middleware for FastAPI

Provides centralized exception handling with standardized error responses,
logging, and monitoring integration. Catches all exceptions and transforms
them into consistent JSON error responses.

Features:
- Standardized error response format
- Automatic HTTP status code mapping
- Comprehensive error logging
- Development vs production error details
- Request context in error logs
"""

import logging
import traceback
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.exceptions import BaseAppException, get_http_status_code

logger = logging.getLogger(__name__)


def create_error_response(
    error_code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    Create standardized error response.

    Args:
        error_code: Machine-readable error code
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error context
        request_id: Request tracking ID

    Returns:
        Standardized error response dictionary
    """
    from datetime import datetime

    response = {
        "error": {
            "code": error_code,
            "message": message,
            "status_code": status_code,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    }

    if details:
        response["error"]["details"] = details

    if request_id:
        response["error"]["request_id"] = request_id

    return response


async def base_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """
    Handle custom application exceptions.

    Args:
        request: FastAPI request object
        exc: Application exception

    Returns:
        JSON error response
    """
    status_code = get_http_status_code(exc)

    # Log with appropriate level based on status code
    if status_code >= 500:
        logger.error(
            f"❌ Application error: {exc.error_code} | "
            f"Path: {request.url.path} | "
            f"Message: {exc.message}",
            exc_info=True,
        )
    elif status_code >= 400:
        logger.warning(
            f"⚠️ Client error: {exc.error_code} | " f"Path: {request.url.path} | " f"Message: {exc.message}"
        )

    # Get request ID if available
    request_id = request.headers.get("X-Request-ID")

    # Create standardized response
    response = create_error_response(
        error_code=exc.error_code,
        message=exc.message,
        status_code=status_code,
        details=exc.details if hasattr(exc, "details") else None,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=status_code,
        content=response,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle Starlette/FastAPI HTTP exceptions.

    Args:
        request: FastAPI request object
        exc: HTTP exception

    Returns:
        JSON error response
    """
    # Log client errors (4xx) as warnings, server errors (5xx) as errors
    if exc.status_code >= 500:
        logger.error(
            f"❌ HTTP {exc.status_code}: {exc.detail} | Path: {request.url.path}", exc_info=True
        )
    elif exc.status_code >= 400:
        logger.warning(f"⚠️ HTTP {exc.status_code}: {exc.detail} | Path: {request.url.path}")

    request_id = request.headers.get("X-Request-ID")

    response = create_error_response(
        error_code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        status_code=exc.status_code,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: FastAPI request object
        exc: Validation error

    Returns:
        JSON error response with validation details
    """
    # Extract validation errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append(
            {
                "field": field,
                "message": error["msg"],
                "type": error["type"],
            }
        )

    logger.warning(f"⚠️ Validation error | Path: {request.url.path} | Errors: {len(errors)}")

    request_id = request.headers.get("X-Request-ID")

    response = create_error_response(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"validation_errors": errors},
        request_id=request_id,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unhandled exceptions (catch-all).

    Args:
        request: FastAPI request object
        exc: Any unhandled exception

    Returns:
        JSON error response
    """
    # Log full exception details
    logger.error(
        f"❌ Unhandled exception: {type(exc).__name__} | "
        f"Path: {request.url.path} | "
        f"Message: {str(exc)}",
        exc_info=True,
    )

    request_id = request.headers.get("X-Request-ID")

    # In development, include stack trace
    details = None
    if settings.debug:
        details = {
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        }

    response = create_error_response(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=details,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response,
    )


def register_error_handlers(app) -> None:
    """
    Register all error handlers with FastAPI application.

    Args:
        app: FastAPI application instance

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> register_error_handlers(app)
    """
    # Custom application exceptions
    app.add_exception_handler(BaseAppException, base_exception_handler)

    # HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Catch-all for unhandled exceptions
    app.add_exception_handler(Exception, unhandled_exception_handler)

    logger.info("✅ Error handlers registered successfully")
