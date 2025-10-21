"""
Monitoring Router

Provides proxy access to Flower dashboard and worker monitoring endpoints.
"""
import os
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
import httpx

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

# Flower service URL and authentication from environment variables
FLOWER_URL = os.getenv('FLOWER_URL', 'http://localhost:5555')
FLOWER_BASIC_AUTH = os.getenv('FLOWER_BASIC_AUTH', '')  # Format: "user:password"


def get_flower_auth():
    """Get HTTP Basic Auth tuple for Flower if configured."""
    if FLOWER_BASIC_AUTH and ':' in FLOWER_BASIC_AUTH:
        username, password = FLOWER_BASIC_AUTH.split(':', 1)
        return (username, password)
    return None


@router.get("/flower/{path:path}", response_class=HTMLResponse)
async def flower_proxy(path: str, request: Request):
    """
    Proxy requests to Flower dashboard.

    This allows the frontend to access Flower through the backend API,
    avoiding CORS issues and providing a unified API endpoint.

    Args:
        path: Path to proxy to Flower
        request: FastAPI request object

    Returns:
        Response from Flower service
    """
    try:
        # Build full URL with query parameters
        query_string = str(request.url.query) if request.url.query else ""
        url = f"{FLOWER_URL}/{path}"
        if query_string:
            url = f"{url}?{query_string}"

        logger.debug(f"🌸 Proxying request to Flower: {url}")

        # Forward request to Flower with authentication if configured
        auth = get_flower_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, auth=auth)

        # Return response with original content type
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers={
                "Content-Type": response.headers.get("Content-Type", "text/html"),
            }
        )

    except httpx.ConnectError:
        logger.error(f"❌ Failed to connect to Flower service at {FLOWER_URL}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Flower service unavailable",
                "message": "Could not connect to Flower monitoring service. Please ensure it is running.",
                "flower_url": FLOWER_URL
            }
        )
    except Exception as e:
        logger.error(f"❌ Error proxying to Flower: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Proxy error",
                "message": str(e)
            }
        )


@router.get("/flower-status")
async def flower_status():
    """
    Check if Flower service is available.

    Returns:
        Status information about Flower service
    """
    try:
        auth = get_flower_auth()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{FLOWER_URL}/api/workers", auth=auth)

        if response.status_code == 200:
            workers = response.json()
            return {
                "available": True,
                "flower_url": FLOWER_URL,
                "workers": workers,
                "worker_count": len(workers)
            }
        else:
            return {
                "available": False,
                "flower_url": FLOWER_URL,
                "error": f"Unexpected status code: {response.status_code}"
            }

    except httpx.ConnectError:
        logger.warning(f"⚠️ Flower service not available at {FLOWER_URL}")
        return {
            "available": False,
            "flower_url": FLOWER_URL,
            "error": "Connection refused"
        }
    except Exception as e:
        logger.error(f"❌ Error checking Flower status: {str(e)}")
        return {
            "available": False,
            "flower_url": FLOWER_URL,
            "error": str(e)
        }


@router.get("/worker-stats")
async def worker_stats():
    """
    Get worker statistics from Flower.

    Returns:
        Worker statistics including active tasks, queues, etc.
    """
    try:
        auth = get_flower_auth()
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get workers
            workers_response = await client.get(f"{FLOWER_URL}/api/workers", auth=auth)

            # Get tasks
            tasks_response = await client.get(f"{FLOWER_URL}/api/tasks", auth=auth)

        if workers_response.status_code == 200 and tasks_response.status_code == 200:
            workers = workers_response.json()
            tasks = tasks_response.json()

            # Calculate statistics
            active_workers = len([w for w in workers.values() if w.get('status') == 'Online'])

            return {
                "workers": {
                    "total": len(workers),
                    "active": active_workers,
                    "details": workers
                },
                "tasks": {
                    "total": len(tasks),
                    "details": tasks
                },
                "queues": {
                    "high_priority": 0,  # Flower API doesn't expose queue lengths directly
                    "default": 0,
                    "low_priority": 0,
                    "maintenance": 0
                }
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="Failed to fetch worker statistics from Flower"
            )

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Flower service unavailable"
        )
    except Exception as e:
        logger.error(f"❌ Error fetching worker stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
