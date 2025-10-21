"""
Monitoring Router

Provides proxy access to Flower dashboard and worker monitoring endpoints.
"""
import os
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
import httpx

# Import Redis client for queue length queries
from shared.redis_client import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

# Flower service URLs and authentication from environment variables
# FLOWER_URL_INTERNAL: Used by backend for API calls (Railway private network)
# FLOWER_URL_PUBLIC: Returned to frontend for browser access
FLOWER_URL_INTERNAL = os.getenv('FLOWER_URL_INTERNAL', 'http://flower-service.railway.internal:5555')
FLOWER_URL_PUBLIC = os.getenv('FLOWER_URL_PUBLIC', os.getenv('FLOWER_URL', 'http://localhost:5555'))
FLOWER_BASIC_AUTH = os.getenv('FLOWER_BASIC_AUTH', '')  # Format: "user:password"


def get_flower_auth():
    """Get HTTP Basic Auth tuple for Flower if configured."""
    if FLOWER_BASIC_AUTH and ':' in FLOWER_BASIC_AUTH:
        username, password = FLOWER_BASIC_AUTH.split(':', 1)
        return (username, password)
    return None


def get_queue_lengths():
    """Get current queue lengths from Redis.

    Returns:
        Dict with queue names and their lengths
    """
    try:
        redis_client = get_redis()
        return {
            "high_priority": redis_client.llen("high_priority"),
            "default": redis_client.llen("default"),
            "low_priority": redis_client.llen("low_priority"),
            "maintenance": redis_client.llen("maintenance")
        }
    except Exception as e:
        logger.error(f"❌ Error fetching queue lengths from Redis: {str(e)}")
        return {
            "high_priority": 0,
            "default": 0,
            "low_priority": 0,
            "maintenance": 0
        }


@router.get("/flower-status")
async def flower_status():
    """
    Check if Flower service is available.

    Returns:
        Status information about Flower service
    """
    try:
        auth = get_flower_auth()
        # Use internal URL for API calls (faster, stays on private network)
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{FLOWER_URL_INTERNAL}/api/workers", auth=auth)

        if response.status_code == 200:
            workers = response.json()
            return {
                "available": True,
                "flower_url": FLOWER_URL_PUBLIC,  # Return public URL for frontend
                "workers": workers,
                "worker_count": len(workers)
            }
        else:
            return {
                "available": False,
                "flower_url": FLOWER_URL_PUBLIC,
                "error": f"Unexpected status code: {response.status_code}"
            }

    except httpx.ConnectError:
        logger.warning(f"⚠️ Flower service not available at {FLOWER_URL_INTERNAL}")
        return {
            "available": False,
            "flower_url": FLOWER_URL_PUBLIC,
            "error": "Connection refused"
        }
    except Exception as e:
        logger.error(f"❌ Error checking Flower status: {str(e)}")
        return {
            "available": False,
            "flower_url": FLOWER_URL_PUBLIC,
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
        # Use internal URL for API calls (faster, stays on private network)
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get workers
            workers_response = await client.get(f"{FLOWER_URL_INTERNAL}/api/workers", auth=auth)

            # Get tasks
            tasks_response = await client.get(f"{FLOWER_URL_INTERNAL}/api/tasks", auth=auth)

        if workers_response.status_code == 200 and tasks_response.status_code == 200:
            workers = workers_response.json()
            tasks = tasks_response.json()

            # Debug logging
            logger.debug(f"📊 Flower API response - Workers: {len(workers)}, Tasks: {len(tasks)}")
            if workers:
                logger.debug(f"   Worker names: {list(workers.keys())}")

            # Calculate worker statistics
            # Flower API: workers dict where each key is a worker name
            # Workers are active if they appear in the response
            total_workers = len(workers)

            # Count active workers (workers with 'stats' field are active)
            # If no 'stats' field exists, assume all returned workers are active
            active_workers = 0
            for worker_name, worker_info in workers.items():
                # Check if worker has stats (indicates it's responding)
                if isinstance(worker_info, dict):
                    # If it has 'stats' key, it's definitely active
                    if 'stats' in worker_info or 'status' in worker_info:
                        # Check status field if present
                        status = worker_info.get('status', 'online')
                        if status != 'offline':
                            active_workers += 1
                    else:
                        # Worker present in response = active
                        active_workers += 1

            # If all workers have no status info, assume all are active
            if active_workers == 0 and total_workers > 0:
                active_workers = total_workers

            # Get real queue lengths from Redis
            queue_lengths = get_queue_lengths()

            return {
                "workers": {
                    "total": total_workers,
                    "active": active_workers,
                    "details": workers
                },
                "tasks": {
                    "total": len(tasks),
                    "details": tasks
                },
                "queues": queue_lengths
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
