"""
Chat Router for GuidelineChat

Streaming proxy endpoint for multiple Dify RAG apps.
Uses SSE (Server-Sent Events) for real-time streaming responses.

Supports multiple chat modes:
- guidelines: Q&A for medical guidelines (AWMF)
- befund: Generate recommendation text for Befundberichte
"""

import logging
import os

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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


@router.get("/apps")
async def list_chat_apps() -> list[AppInfo]:
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
async def stream_chat_message(request: ChatRequest):
    """
    Proxy chat message to Dify with SSE streaming.

    Supports multiple Dify apps via app_id parameter.
    """
    # Get app configuration
    app_config = DIFY_APPS.get(request.app_id)
    if not app_config:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown app_id: {request.app_id}. Available: {list(DIFY_APPS.keys())}",
        )

    api_key = app_config["api_key"]

    if not DIFY_BASE_URL or not api_key:
        raise HTTPException(
            status_code=503,
            detail=f"Chat app '{request.app_id}' not configured. Missing API key or base URL.",
        )

    async def generate():
        """Generate SSE stream from Dify response."""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "query": request.query,
                    "response_mode": "streaming",
                    "user": "anonymous",
                    "inputs": {},
                }

                # Only include conversation_id if provided (for continuing conversations)
                if request.conversation_id:
                    payload["conversation_id"] = request.conversation_id

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
                        logger.error(f"Dify error: {response.status_code} - {error_text[:200]}")
                        yield f'data: {{"event": "error", "message": "Dify error: {response.status_code}"}}\n\n'
                        return

                    async for chunk in response.aiter_text():
                        # Forward the SSE chunks directly
                        yield chunk

        except httpx.TimeoutException:
            logger.error("Dify request timed out")
            yield 'data: {"event": "error", "message": "Request timed out"}\n\n'

        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to Dify: {e}")
            yield 'data: {"event": "error", "message": "Failed to connect to chat service"}\n\n'

        except Exception as e:
            logger.error(f"Chat streaming error: {e}")
            yield f'data: {{"event": "error", "message": "Internal error: {str(e)}"}}\n\n'

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
async def chat_health():
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
