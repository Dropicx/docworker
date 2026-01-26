"""
Chat Router for GuidelineChat

Streaming proxy endpoint for Dify RAG service.
Uses SSE (Server-Sent Events) for real-time streaming responses.
"""

import logging
import os

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Configuration from environment (reuse existing Dify config)
DIFY_RAG_URL = os.getenv("DIFY_RAG_URL", "")
DIFY_RAG_API_KEY = os.getenv("DIFY_RAG_API_KEY", "")


class ChatRequest(BaseModel):
    """Request model for chat messages."""

    query: str
    conversation_id: str | None = None


@router.post("/message")
async def stream_chat_message(request: ChatRequest):
    """
    Proxy chat message to Dify with SSE streaming.

    Uses the existing Dify RAG configuration but with streaming mode
    for real-time response delivery.
    """
    if not DIFY_RAG_URL or not DIFY_RAG_API_KEY:
        raise HTTPException(
            status_code=503, detail="Chat service not configured. Please set DIFY_RAG_URL and DIFY_RAG_API_KEY."
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
                    f"{DIFY_RAG_URL}/v1/chat-messages",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {DIFY_RAG_API_KEY}",
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
    if not DIFY_RAG_URL:
        return {"status": "not_configured", "url": None}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{DIFY_RAG_URL}/health")

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "url": DIFY_RAG_URL,
                    "api_key_configured": bool(DIFY_RAG_API_KEY),
                }
            else:
                return {
                    "status": "error",
                    "url": DIFY_RAG_URL,
                    "error": f"HTTP {response.status_code}",
                }

    except httpx.TimeoutException:
        return {"status": "timeout", "url": DIFY_RAG_URL, "error": "Connection timeout"}

    except httpx.ConnectError as e:
        return {"status": "unreachable", "url": DIFY_RAG_URL, "error": str(e)}

    except Exception as e:
        return {"status": "error", "url": DIFY_RAG_URL, "error": str(e)}
