"""
Task Queue Abstraction Layer

Provides queue abstraction for pipeline execution.
Current: In-memory (direct execution)
Future: Redis-based worker queue

Design Pattern:
- InMemoryTaskQueue: Immediate execution (current)
- RedisTaskQueue: Queue-based execution with workers (future)
"""

import logging
import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskQueue(ABC):
    """
    Abstract base class for task queues.

    All task queue implementations must inherit from this class
    and implement the required methods.
    """

    @abstractmethod
    async def enqueue(
        self,
        task_name: str,
        task_data: Dict[str, Any],
        priority: int = 0
    ) -> str:
        """
        Enqueue a task for processing.

        Args:
            task_name: Name of the task to execute
            task_data: Data needed for task execution
            priority: Task priority (higher = more urgent)

        Returns:
            job_id: Unique identifier for the queued job
        """
        pass

    @abstractmethod
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a queued job.

        Args:
            job_id: Job identifier

        Returns:
            Job status dict or None if not found
        """
        pass

    @abstractmethod
    async def get_job_result(self, job_id: str) -> Optional[Any]:
        """
        Get result of a completed job.

        Args:
            job_id: Job identifier

        Returns:
            Job result or None if not ready
        """
        pass

    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending or running job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancelled successfully, False otherwise
        """
        pass


class InMemoryTaskQueue(TaskQueue):
    """
    In-memory task queue with immediate execution.

    Current implementation: Executes tasks immediately in the same process.
    No actual queueing or worker processes.

    This is suitable for:
    - Development and testing
    - Low-traffic production (current state)
    - Single-instance deployments
    """

    def __init__(self):
        """Initialize in-memory task queue."""
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.task_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]] = {}

        logger.info("📦 InMemoryTaskQueue initialized (direct execution mode)")

    def register_task_handler(
        self,
        task_name: str,
        handler: Callable[[Dict[str, Any]], Awaitable[Any]]
    ):
        """
        Register a task handler function.

        Args:
            task_name: Name of the task
            handler: Async function to handle the task
        """
        self.task_handlers[task_name] = handler
        logger.debug(f"✅ Registered handler for task: {task_name}")

    async def enqueue(
        self,
        task_name: str,
        task_data: Dict[str, Any],
        priority: int = 0
    ) -> str:
        """
        Enqueue and immediately execute a task.

        Args:
            task_name: Name of the task to execute
            task_data: Data needed for task execution
            priority: Task priority (ignored in direct execution mode)

        Returns:
            job_id: Unique identifier for the job
        """
        job_id = str(uuid.uuid4())

        # Create job record
        self.jobs[job_id] = {
            "job_id": job_id,
            "task_name": task_name,
            "task_data": task_data,
            "priority": priority,
            "status": JobStatus.PENDING,
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }

        logger.info(f"📋 Task '{task_name}' enqueued with job_id: {job_id[:8]}...")

        # Execute immediately (no actual queue)
        asyncio.create_task(self._execute_task(job_id))

        return job_id

    async def _execute_task(self, job_id: str):
        """
        Execute a task immediately.

        Args:
            job_id: Job identifier
        """
        job = self.jobs.get(job_id)
        if not job:
            logger.error(f"❌ Job {job_id[:8]}... not found")
            return

        task_name = job["task_name"]
        task_data = job["task_data"]

        # Check if handler is registered
        handler = self.task_handlers.get(task_name)
        if not handler:
            error = f"No handler registered for task: {task_name}"
            logger.error(f"❌ {error}")
            self._mark_job_failed(job_id, error)
            return

        # Update job status
        job["status"] = JobStatus.RUNNING
        job["started_at"] = datetime.now()

        logger.info(f"🔄 Executing task '{task_name}' (job: {job_id[:8]}...)")

        try:
            # Execute the task handler
            result = await handler(task_data)

            # Mark job as completed
            job["status"] = JobStatus.COMPLETED
            job["completed_at"] = datetime.now()
            job["result"] = result

            execution_time = (job["completed_at"] - job["started_at"]).total_seconds()
            logger.info(f"✅ Task '{task_name}' completed in {execution_time:.2f}s (job: {job_id[:8]}...)")

        except Exception as e:
            error = str(e)
            logger.error(f"❌ Task '{task_name}' failed: {error}")
            self._mark_job_failed(job_id, error)

    def _mark_job_failed(self, job_id: str, error: str):
        """Mark a job as failed."""
        job = self.jobs.get(job_id)
        if job:
            job["status"] = JobStatus.FAILED
            job["completed_at"] = datetime.now()
            job["error"] = error

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a job.

        Args:
            job_id: Job identifier

        Returns:
            Job status dict or None if not found
        """
        job = self.jobs.get(job_id)
        if not job:
            return None

        return {
            "job_id": job["job_id"],
            "task_name": job["task_name"],
            "status": job["status"],
            "created_at": job["created_at"].isoformat(),
            "started_at": job["started_at"].isoformat() if job["started_at"] else None,
            "completed_at": job["completed_at"].isoformat() if job["completed_at"] else None,
            "error": job["error"]
        }

    async def get_job_result(self, job_id: str) -> Optional[Any]:
        """
        Get result of a completed job.

        Args:
            job_id: Job identifier

        Returns:
            Job result or None if not ready
        """
        job = self.jobs.get(job_id)
        if not job:
            return None

        if job["status"] != JobStatus.COMPLETED:
            return None

        return job["result"]

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job (not supported in direct execution mode).

        Args:
            job_id: Job identifier

        Returns:
            False (cancellation not supported)
        """
        logger.warning("⚠️ Job cancellation not supported in direct execution mode")
        return False


# ==================== FUTURE: REDIS TASK QUEUE ====================
#
# class RedisTaskQueue(TaskQueue):
#     """
#     Redis-based task queue with worker processes.
#
#     Future implementation for scaled production deployments.
#     Requires:
#     - Redis server
#     - Worker processes (OCR worker, AI worker)
#     - Job serialization/deserialization
#     """
#
#     def __init__(self, redis_url: str):
#         """
#         Initialize Redis task queue.
#
#         Args:
#             redis_url: Redis connection URL
#         """
#         import redis
#         from rq import Queue
#
#         self.redis_client = redis.from_url(redis_url)
#         self.ocr_queue = Queue('ocr_queue', connection=self.redis_client)
#         self.ai_queue = Queue('ai_queue', connection=self.redis_client)
#
#         logger.info("📦 RedisTaskQueue initialized")
#         logger.info(f"   - OCR Queue: {self.ocr_queue.name}")
#         logger.info(f"   - AI Queue: {self.ai_queue.name}")
#
#     async def enqueue(
#         self,
#         task_name: str,
#         task_data: Dict[str, Any],
#         priority: int = 0
#     ) -> str:
#         """
#         Enqueue a task to Redis queue.
#
#         Routes to appropriate queue:
#         - OCR tasks -> ocr_queue (Worker 2)
#         - AI tasks -> ai_queue (Worker 1)
#         """
#         # Determine queue based on task name
#         queue = self.ocr_queue if 'ocr' in task_name.lower() else self.ai_queue
#
#         # Enqueue task
#         job = queue.enqueue(
#             f'workers.{task_name}',
#             task_data,
#             job_timeout='10m',
#             result_ttl=3600  # Keep results for 1 hour
#         )
#
#         logger.info(f"📋 Task '{task_name}' enqueued to {queue.name} with job_id: {job.id}")
#         return job.id
#
#     async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
#         """Get status from Redis queue."""
#         from rq.job import Job
#
#         try:
#             job = Job.fetch(job_id, connection=self.redis_client)
#             return {
#                 "job_id": job.id,
#                 "status": job.get_status(),
#                 "created_at": job.created_at.isoformat() if job.created_at else None,
#                 "started_at": job.started_at.isoformat() if job.started_at else None,
#                 "ended_at": job.ended_at.isoformat() if job.ended_at else None,
#                 "result": job.result if job.is_finished else None,
#                 "error": str(job.exc_info) if job.is_failed else None
#             }
#         except Exception as e:
#             logger.error(f"❌ Failed to fetch job {job_id}: {e}")
#             return None
#
#     async def get_job_result(self, job_id: str) -> Optional[Any]:
#         """Get result from Redis queue."""
#         from rq.job import Job
#
#         try:
#             job = Job.fetch(job_id, connection=self.redis_client)
#             return job.result if job.is_finished else None
#         except Exception as e:
#             logger.error(f"❌ Failed to get result for job {job_id}: {e}")
#             return None
#
#     async def cancel_job(self, job_id: str) -> bool:
#         """Cancel a Redis job."""
#         from rq.job import Job
#
#         try:
#             job = Job.fetch(job_id, connection=self.redis_client)
#             job.cancel()
#             logger.info(f"✅ Job {job_id} cancelled")
#             return True
#         except Exception as e:
#             logger.error(f"❌ Failed to cancel job {job_id}: {e}")
#             return False


# ==================== TASK QUEUE FACTORY ====================

def create_task_queue(queue_type: str = "memory", **kwargs) -> TaskQueue:
    """
    Factory function to create appropriate task queue.

    Args:
        queue_type: Type of queue ('memory' or 'redis')
        **kwargs: Additional arguments for queue initialization

    Returns:
        TaskQueue instance
    """
    if queue_type == "memory":
        return InMemoryTaskQueue()
    # elif queue_type == "redis":
    #     redis_url = kwargs.get("redis_url")
    #     if not redis_url:
    #         raise ValueError("redis_url required for Redis task queue")
    #     return RedisTaskQueue(redis_url)
    else:
        raise ValueError(f"Unknown queue type: {queue_type}")


# ==================== GLOBAL TASK QUEUE INSTANCE ====================

# Global task queue instance (can be switched via environment variable)
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """
    Get the global task queue instance.

    Returns:
        TaskQueue instance
    """
    global _task_queue

    if _task_queue is None:
        # Determine queue type from environment
        import os
        use_redis = os.getenv("USE_REDIS_QUEUE", "false").lower() == "true"

        if use_redis:
            logger.info("🔄 Redis queue not yet implemented, using in-memory queue")
            _task_queue = create_task_queue("memory")
            # Future:
            # redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            # _task_queue = create_task_queue("redis", redis_url=redis_url)
        else:
            _task_queue = create_task_queue("memory")

    return _task_queue
