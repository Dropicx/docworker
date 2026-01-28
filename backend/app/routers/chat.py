"""
Chat Router for GuidelineChat

Streaming proxy endpoint for multiple Dify RAG apps.
Uses SSE (Server-Sent Events) for real-time streaming responses.

Supports multiple chat modes:
- guidelines: Q&A for medical guidelines (AWMF)
- befund: Generate recommendation text for Befundberichte

Rate limiting:
- /apps: 20/minute (lightweight endpoint)
- /health: 30/minute (allow monitoring)
- /message: Custom multi-window rate limiting (10/min, 50/hour, 200/day)

Request logging:
- All requests are logged to chat_logs table for analytics
- GDPR-compliant: no query text stored, PII is hashed
- Token usage and costs tracked from Dify responses
"""

import json
import logging
import os
import time

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.services.chat_log_service import chat_log_service
from app.services.chat_rate_limiter import chat_rate_limiter

# Rate limiting for lightweight endpoints (disabled in test/development)
limiter = Limiter(
    key_func=get_remote_address,
    enabled=os.getenv("ENVIRONMENT") not in ["test", "development"],
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Base Dify URL (same for all apps)
DIFY_BASE_URL = os.getenv("DIFY_RAG_URL", "")

# Multiple Dify app configurations
# Each app has its own API key configured in Dify
DIFY_APPS = {
    "guidelines": {
        "name": "Leitlinien Q&A",
        "description": "Fragen zu AWMF-Leitlinien beantworten",
        "api_key": os.getenv("DIFY_RAG_API_KEY", ""),  # Existing key
        "icon": "book-open",
    },
    "befund": {
        "name": "Befund-Empfehlungen",
        "description": "Leitlinienbasierte Empfehlungstexte generieren",
        "api_key": os.getenv("DIFY_BEFUND_API_KEY", ""),  # New key for Befund app
        "icon": "file-text",
    },
}


class ChatRequest(BaseModel):
    """Request model for chat messages."""

    query: str
    conversation_id: str | None = None
    app_id: str = "guidelines"  # Default to guidelines app


class AppInfo(BaseModel):
    """Response model for app information."""

    id: str
    name: str
    description: str
    icon: str
    available: bool


class RateLimitError(BaseModel):
    """Response model for rate limit errors."""

    error: str = "rate_limit_exceeded"
    message: str
    retry_after: int | None = None
    limit_type: str | None = None


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request, handling proxies."""
    # Check for forwarded headers (Railway, nginx, etc.)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (original client)
        return forwarded_for.split(",")[0].strip()

    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct connection IP
    if request.client:
        return request.client.host

    return "unknown"


def get_session_token(request: Request) -> str | None:
    """Extract chat session token from request headers."""
    return request.headers.get("X-Chat-Session")


def get_user_agent(request: Request) -> str | None:
    """Extract user agent from request headers."""
    return request.headers.get("User-Agent")


@router.get("/apps")
@limiter.limit(settings.chat_apps_rate_limit)
async def list_chat_apps(request: Request) -> list[AppInfo]:
    """List available chat apps/modes."""
    apps = []
    for app_id, config in DIFY_APPS.items():
        apps.append(
            AppInfo(
                id=app_id,
                name=config["name"],
                description=config["description"],
                icon=config["icon"],
                available=bool(config["api_key"] and DIFY_BASE_URL),
            )
        )
    return apps


@router.post("/message")
async def stream_chat_message(request: Request, chat_request: ChatRequest):
    """
    Proxy chat message to Dify with SSE streaming.

    Supports multiple Dify apps via app_id parameter.

    Rate limited: 10/minute, 50/hour, 200/day per IP:session combo.
    Violations trigger escalating penalties (warnings, temp bans, permanent bans).

    All requests are logged to chat_logs table for analytics (GDPR-compliant).
    """
    # Generate unique request ID for logging
    request_id = chat_log_service.generate_request_id()
    start_time = time.perf_counter()

    # Extract client identifiers
    ip_address = get_client_ip(request)
    session_token = get_session_token(request)
    user_agent = get_user_agent(request)

    # Check rate limit BEFORE processing
    rate_limit_result = chat_rate_limiter.check_rate_limit(
        ip_address=ip_address,
        session_token=session_token,
        user_agent=user_agent,
    )

    if not rate_limit_result.allowed:
        # Record the violation and apply escalating penalties
        violation_result = chat_rate_limiter.record_violation(
            ip_address=ip_address,
            session_token=session_token,
            user_agent=user_agent,
            limit_type=rate_limit_result.limit_type or "unknown",
        )

        # Log rate-limited request
        chat_log_service.log_request(
            request_id=request_id,
            app_id=chat_request.app_id,
            ip_address=ip_address,
            query=chat_request.query,
            session_token=session_token,
            conversation_id=chat_request.conversation_id,
            user_agent=user_agent,
            rate_limit_allowed=False,
            rate_limit_type=violation_result.limit_type or rate_limit_result.limit_type,
            violations_at_request=violation_result.violations,
        )

        # Use updated message/retry_after if penalty was escalated
        message = violation_result.message or rate_limit_result.message
        retry_after = violation_result.retry_after or rate_limit_result.retry_after

        logger.warning(
            f"Rate limit exceeded for {ip_address}: "
            f"type={rate_limit_result.limit_type}, violations={violation_result.violations}"
        )

        response = JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": message,
                "retry_after": retry_after,
                "limit_type": violation_result.limit_type or rate_limit_result.limit_type,
            },
        )
        if retry_after:
            response.headers["Retry-After"] = str(retry_after)
        return response

    # Get app configuration
    app_config = DIFY_APPS.get(chat_request.app_id)
    if not app_config:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown app_id: {chat_request.app_id}. Available: {list(DIFY_APPS.keys())}",
        )

    api_key = app_config["api_key"]

    if not DIFY_BASE_URL or not api_key:
        raise HTTPException(
            status_code=503,
            detail=f"Chat app '{chat_request.app_id}' not configured. Missing API key or base URL.",
        )

    # Log initial request (phase 1 of two-phase logging)
    chat_log_service.log_request(
        request_id=request_id,
        app_id=chat_request.app_id,
        ip_address=ip_address,
        query=chat_request.query,
        session_token=session_token,
        conversation_id=chat_request.conversation_id,
        user_agent=user_agent,
        rate_limit_allowed=True,
        violations_at_request=rate_limit_result.violations,
    )

    async def generate():
        """Generate SSE stream from Dify response with logging."""
        # Tracking variables for logging
        first_token_time_ms = None
        stream_chunks = 0
        message_end_data = None
        final_conversation_id = chat_request.conversation_id
        final_message_id = None
        error_occurred = False
        error_type = None
        error_message = None

        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "query": chat_request.query,
                    "response_mode": "streaming",
                    "user": "anonymous",
                    "inputs": {},
                }

                # Only include conversation_id if provided (for continuing conversations)
                if chat_request.conversation_id:
                    payload["conversation_id"] = chat_request.conversation_id

                async with client.stream(
                    "POST",
                    f"{DIFY_BASE_URL}/v1/chat-messages",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=120.0,
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        error_occurred = True
                        error_type = "dify_error"
                        error_message = f"HTTP {response.status_code}: {error_text[:200]}"
                        logger.error(f"Dify error: {response.status_code} - {error_text[:200]}")
                        yield f'data: {{"event": "error", "message": "Dify error: {response.status_code}"}}\n\n'
                        return

                    async for chunk in response.aiter_text():
                        stream_chunks += 1

                        # Track first token time
                        if first_token_time_ms is None:
                            first_token_time_ms = int((time.perf_counter() - start_time) * 1000)

                        # Parse SSE events to extract message_end data
                        # Dify sends events in format: "data: {...}\n\n"
                        if chunk.startswith("data: "):
                            try:
                                json_str = chunk[6:].strip()
                                if json_str:
                                    event_data = json.loads(json_str)
                                    event_type = event_data.get("event")

                                    # Extract conversation_id from any event
                                    if "conversation_id" in event_data:
                                        final_conversation_id = event_data["conversation_id"]

                                    # message_end contains token usage and metadata
                                    if event_type == "message_end":
                                        message_end_data = event_data
                                        final_message_id = event_data.get("message_id")
                                        if "metadata" in event_data and "usage" in event_data["metadata"]:
                                            # Dify usage format
                                            usage = event_data["metadata"]["usage"]
                                            message_end_data["prompt_tokens"] = usage.get("prompt_tokens")
                                            message_end_data["completion_tokens"] = usage.get("completion_tokens")
                                            message_end_data["total_tokens"] = usage.get("total_tokens")
                                            message_end_data["total_price"] = usage.get("total_price")
                            except json.JSONDecodeError:
                                # Not JSON or malformed, continue
                                pass

                        # Forward the SSE chunks directly
                        yield chunk

        except httpx.TimeoutException:
            error_occurred = True
            error_type = "timeout"
            error_message = "Request timed out"
            logger.error("Dify request timed out")
            yield 'data: {"event": "error", "message": "Request timed out"}\n\n'

        except httpx.ConnectError as e:
            error_occurred = True
            error_type = "connect_error"
            error_message = str(e)[:500]
            logger.error(f"Failed to connect to Dify: {e}")
            yield 'data: {"event": "error", "message": "Failed to connect to chat service"}\n\n'

        except Exception as e:
            error_occurred = True
            error_type = "internal_error"
            error_message = str(e)[:500]
            logger.error(f"Chat streaming error: {e}")
            yield f'data: {{"event": "error", "message": "Internal error: {str(e)}"}}\n\n'

        finally:
            # Update log with response data (phase 2 of two-phase logging)
            response_time_ms = int((time.perf_counter() - start_time) * 1000)

            # Extract token/cost data from message_end
            prompt_tokens = None
            completion_tokens = None
            total_tokens = None
            cost_usd = None
            log_metadata = None

            if message_end_data:
                prompt_tokens = message_end_data.get("prompt_tokens")
                completion_tokens = message_end_data.get("completion_tokens")
                total_tokens = message_end_data.get("total_tokens")
                cost_usd = message_end_data.get("total_price")

                # Store retriever_resources if present
                if "metadata" in message_end_data:
                    metadata = message_end_data["metadata"]
                    if "retriever_resources" in metadata:
                        log_metadata = {
                            "retriever_resources_count": len(metadata["retriever_resources"]),
                        }

            chat_log_service.update_with_response(
                request_id=request_id,
                status="error" if error_occurred else "success",
                message_id=final_message_id,
                conversation_id=final_conversation_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                response_time_ms=response_time_ms,
                first_token_time_ms=first_token_time_ms,
                stream_chunks=stream_chunks,
                error_type=error_type if error_occurred else None,
                error_message=error_message if error_occurred else None,
                log_metadata=log_metadata,
            )

    # Record the message AFTER starting the stream (request is being processed)
    chat_rate_limiter.record_message(
        ip_address=ip_address,
        session_token=session_token,
        user_agent=user_agent,
    )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/health")
@limiter.limit(settings.chat_health_rate_limit)
async def chat_health(request: Request):
    """Check health of chat service (Dify connection)."""
    if not DIFY_BASE_URL:
        return {"status": "not_configured", "url": None, "apps": {}}

    # Check which apps are configured
    apps_status = {}
    for app_id, config in DIFY_APPS.items():
        apps_status[app_id] = {
            "name": config["name"],
            "configured": bool(config["api_key"]),
        }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{DIFY_BASE_URL}/health")

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "url": DIFY_BASE_URL,
                    "apps": apps_status,
                }
            else:
                return {
                    "status": "error",
                    "url": DIFY_BASE_URL,
                    "error": f"HTTP {response.status_code}",
                    "apps": apps_status,
                }

    except httpx.TimeoutException:
        return {"status": "timeout", "url": DIFY_BASE_URL, "error": "Connection timeout", "apps": apps_status}

    except httpx.ConnectError as e:
        return {"status": "unreachable", "url": DIFY_BASE_URL, "error": str(e), "apps": apps_status}

    except Exception as e:
        return {"status": "error", "url": DIFY_BASE_URL, "error": str(e), "apps": apps_status}


@router.get("/rate-limit-status")
async def get_rate_limit_status(request: Request):
    """
    Get current rate limit status for the requesting client.

    Useful for clients to show remaining quota.
    """
    ip_address = get_client_ip(request)
    session_token = get_session_token(request)

    status = chat_rate_limiter.get_status(ip_address, session_token)

    # Remove sensitive identifier from public response
    safe_status = {
        "messages_minute": status["messages_minute"],
        "messages_hour": status["messages_hour"],
        "messages_day": status["messages_day"],
        "limits": status["limits"],
        "remaining_minute": status.get("remaining_minute", status["limits"]["minute"]),
        "remaining_hour": status.get("remaining_hour", status["limits"]["hour"]),
        "remaining_day": status.get("remaining_day", status["limits"]["day"]),
        "banned": status.get("banned", False),
    }

    if status.get("temp_ban_until"):
        safe_status["temp_ban_until"] = status["temp_ban_until"]

    return safe_status
