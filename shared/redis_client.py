"""
Redis Client Singleton

Provides a shared Redis connection for task queue and caching.
"""
import os
import redis
from typing import Optional
import logging

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """
    Get Redis client singleton

    Returns:
        redis.Redis: Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        logger.info(f"🔗 Connecting to Redis: {redis_url.split('@')[0]}...")

        _redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30
        )

        # Test connection
        try:
            _redis_client.ping()
            logger.info("✅ Redis connection successful")
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {str(e)}")
            raise

    return _redis_client


def close_redis():
    """Close Redis connection"""
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None
        logger.info("🔌 Redis connection closed")
