"""
Pipeline Progress Tracker

Publishes real-time pipeline step state to Redis for live frontend tracking.
Uses a Redis hash per job with TTL-based auto-cleanup.

All methods are no-ops if Redis is unavailable — pipeline execution is never blocked.
"""

import json
import logging

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis key prefix for pipeline progress
_KEY_PREFIX = "doctranslator:pipeline_progress"
_TTL_SECONDS = 3600


class PipelineProgressTracker:
    """
    Lightweight async service that writes/reads a Redis hash per processing job.

    Redis key: doctranslator:pipeline_progress:{processing_id}
    Type: Hash
    TTL: 3600s (auto-cleanup)

    Fields:
        current_step_name   - e.g. "TRANSLATION"
        steps_completed     - JSON array of completed step names
        total_steps         - total step count as string
        phase               - "universal" | "class_specific" | "post_branching"
    """

    _pool: ConnectionPool | None = None

    async def _get_client(self) -> aioredis.Redis | None:
        """Get async Redis client, reusing CacheService's connection pool pattern."""
        if not settings.redis_url:
            return None

        try:
            if PipelineProgressTracker._pool is None:
                PipelineProgressTracker._pool = ConnectionPool.from_url(
                    settings.redis_url,
                    max_connections=settings.redis_max_connections,
                    decode_responses=True,
                )
            return aioredis.Redis(connection_pool=PipelineProgressTracker._pool)
        except RedisError as e:
            logger.warning(f"Pipeline progress tracker: Redis unavailable: {e}")
            return None

    def _key(self, processing_id: str) -> str:
        return f"{_KEY_PREFIX}:{processing_id}"

    async def step_started(
        self,
        processing_id: str,
        step_name: str,
        completed_count: int,
        total_steps: int,
        phase: str,
    ) -> None:
        """Record that a step has started executing."""
        client = await self._get_client()
        if not client:
            return

        try:
            key = self._key(processing_id)
            await client.hset(
                key,
                mapping={
                    "current_step_name": step_name,
                    "completed_count": str(completed_count),
                    "total_steps": str(total_steps),
                    "phase": phase,
                },
            )
            # Set TTL on first write (won't reset if already set)
            await client.expire(key, _TTL_SECONDS, nx=True)
        except RedisError as e:
            logger.warning(f"Pipeline progress tracker: failed to write step_started: {e}")

    async def step_completed(self, processing_id: str, step_name: str) -> None:
        """Append a completed step name to the steps_completed list."""
        client = await self._get_client()
        if not client:
            return

        try:
            key = self._key(processing_id)
            raw = await client.hget(key, "steps_completed")
            completed = json.loads(raw) if raw else []
            completed.append(step_name)
            await client.hset(key, "steps_completed", json.dumps(completed))
        except RedisError as e:
            logger.warning(f"Pipeline progress tracker: failed to write step_completed: {e}")

    async def update_total_steps(self, processing_id: str, total: int) -> None:
        """Update total step count (called after branching when total becomes known)."""
        client = await self._get_client()
        if not client:
            return

        try:
            await client.hset(self._key(processing_id), "total_steps", str(total))
        except RedisError as e:
            logger.warning(f"Pipeline progress tracker: failed to update total_steps: {e}")

    async def get_progress(self, processing_id: str) -> dict | None:
        """
        Read current progress from Redis.

        Returns a structured dict with computed progress_percent,
        or None if key doesn't exist or Redis is unavailable.
        """
        client = await self._get_client()
        if not client:
            return None

        try:
            key = self._key(processing_id)
            data = await client.hgetall(key)
            if not data:
                return None

            steps_completed = json.loads(data.get("steps_completed", "[]"))
            total_steps = int(data.get("total_steps", "1"))
            completed_count = len(steps_completed)

            progress_percent = int(completed_count / max(total_steps, 1) * 100)
            progress_percent = min(progress_percent, 99)  # Never show 100% until truly done

            return {
                "current_step_name": data.get("current_step_name"),
                "steps_completed": steps_completed,
                "total_steps": total_steps,
                "completed_count": completed_count,
                "progress_percent": progress_percent,
                "phase": data.get("phase", "universal"),
            }
        except RedisError as e:
            logger.warning(f"Pipeline progress tracker: failed to read progress: {e}")
            return None

    async def cleanup(self, processing_id: str) -> None:
        """Delete the progress key (or just let TTL expire)."""
        client = await self._get_client()
        if not client:
            return

        try:
            await client.delete(self._key(processing_id))
        except RedisError as e:
            logger.warning(f"Pipeline progress tracker: failed to cleanup: {e}")
