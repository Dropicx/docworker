"""
Redis Cache Service

Provides async Redis caching with graceful degradation for configuration data.
Uses cache-aside pattern with namespace-based key management.
"""

import json
import logging
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Async Redis cache service with connection pooling and graceful degradation.

    Features:
    - Async operations (non-blocking)
    - Connection pool reuse (singleton pattern)
    - Graceful degradation when Redis unavailable
    - JSON serialization for complex objects
    - Namespace-based key management
    - Metrics for cache hits/misses

    Usage:
        cache = CacheService()
        await cache.set("pipeline_steps", "enabled", steps_list, ttl=600)
        cached = await cache.get("pipeline_steps", "enabled")
    """

    _instance: "CacheService | None" = None
    _pool: ConnectionPool | None = None
    _client: aioredis.Redis | None = None
    _is_healthy: bool = True
    _failure_count: int = 0
    _max_failures: int = 3

    # Cache namespaces
    NS_PIPELINE_STEPS = "pipeline_steps"
    NS_DOCUMENT_CLASSES = "document_classes"
    NS_AVAILABLE_MODELS = "available_models"
    NS_SYSTEM_SETTINGS = "system_settings"
    NS_OCR_CONFIG = "ocr_config"

    # Metrics
    _cache_hits: int = 0
    _cache_misses: int = 0
    _cache_errors: int = 0

    def __new__(cls) -> "CacheService":
        """Singleton pattern for cache service."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize cache service (idempotent for singleton)."""
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._key_prefix = settings.cache_key_prefix
        self._enabled = settings.cache_enabled and settings.redis_url is not None

        if self._enabled:
            logger.info(
                f"Cache service initialized: prefix='{self._key_prefix}', "
                f"default_ttl={settings.cache_default_ttl_seconds}s"
            )
        else:
            logger.warning(
                "Cache service disabled: cache_enabled=%s, redis_url=%s",
                settings.cache_enabled,
                "set" if settings.redis_url else "not set",
            )

    def _make_key(self, namespace: str, key: str) -> str:
        """Create namespaced cache key."""
        return f"{self._key_prefix}:{namespace}:{key}"

    async def _get_client(self) -> aioredis.Redis | None:
        """Get Redis client with lazy initialization."""
        if not self._enabled:
            return None

        if not self._is_healthy:
            return None

        if self._client is not None:
            return self._client

        try:
            if self._pool is None:
                self._pool = ConnectionPool.from_url(
                    settings.redis_url,
                    max_connections=settings.redis_max_connections,
                    decode_responses=True,
                )
                logger.debug("Redis connection pool created")

            self._client = aioredis.Redis(connection_pool=self._pool)
            logger.info("Redis cache client connected")
            return self._client

        except RedisError as e:
            logger.error(f"Failed to create Redis client: {e}")
            self._handle_failure()
            return None

    def _handle_failure(self) -> None:
        """Handle Redis failure, potentially marking as unhealthy."""
        self._failure_count += 1
        self._cache_errors += 1

        if self._failure_count >= self._max_failures:
            logger.warning(
                f"Redis marked unhealthy after {self._failure_count} failures. "
                "Cache operations will fallback to database."
            )
            self._is_healthy = False

    def _handle_success(self) -> None:
        """Handle successful operation, reset failure count."""
        if self._failure_count > 0:
            logger.info("Redis recovered, resetting failure count")
        self._failure_count = 0
        self._is_healthy = True

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        if hasattr(value, "__dict__"):
            # SQLAlchemy model or similar object
            return json.dumps(self._model_to_dict(value))
        if isinstance(value, list):
            return json.dumps([self._model_to_dict(item) for item in value])
        if isinstance(value, dict):
            return json.dumps(value)
        return json.dumps(value)

    def _model_to_dict(self, obj: Any) -> dict:
        """Convert SQLAlchemy model or Pydantic model to dict."""
        if hasattr(obj, "model_dump"):
            # Pydantic v2
            return obj.model_dump()
        if hasattr(obj, "dict"):
            # Pydantic v1
            return obj.dict()
        if hasattr(obj, "__dict__"):
            # SQLAlchemy model - filter out internal attributes
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith("_"):
                    # Handle datetime serialization
                    if hasattr(value, "isoformat"):
                        result[key] = value.isoformat()
                    else:
                        result[key] = value
            return result
        return obj

    def _deserialize(self, value: str) -> Any:
        """Deserialize JSON string to value."""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def get(self, namespace: str, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            namespace: Cache namespace (e.g., 'pipeline_steps')
            key: Cache key within namespace

        Returns:
            Cached value or None if not found/error
        """
        client = await self._get_client()
        if client is None:
            self._cache_misses += 1
            return None

        cache_key = self._make_key(namespace, key)

        try:
            value = await client.get(cache_key)
            if value is None:
                self._cache_misses += 1
                logger.debug(f"Cache MISS: {cache_key}")
                return None

            self._cache_hits += 1
            self._handle_success()
            logger.debug(f"Cache HIT: {cache_key}")
            return self._deserialize(value)

        except RedisError as e:
            logger.warning(f"Cache get error for {cache_key}: {e}")
            self._handle_failure()
            self._cache_misses += 1
            return None

    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            namespace: Cache namespace
            key: Cache key within namespace
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (uses default if not specified)

        Returns:
            True if cached successfully, False otherwise
        """
        client = await self._get_client()
        if client is None:
            return False

        cache_key = self._make_key(namespace, key)
        ttl = ttl or settings.cache_default_ttl_seconds

        try:
            serialized = self._serialize(value)
            await client.setex(cache_key, ttl, serialized)
            self._handle_success()
            logger.debug(f"Cache SET: {cache_key} (ttl={ttl}s)")
            return True

        except RedisError as e:
            logger.warning(f"Cache set error for {cache_key}: {e}")
            self._handle_failure()
            return False

    async def delete(self, namespace: str, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            namespace: Cache namespace
            key: Cache key within namespace

        Returns:
            True if deleted successfully, False otherwise
        """
        client = await self._get_client()
        if client is None:
            return False

        cache_key = self._make_key(namespace, key)

        try:
            await client.delete(cache_key)
            self._handle_success()
            logger.debug(f"Cache DELETE: {cache_key}")
            return True

        except RedisError as e:
            logger.warning(f"Cache delete error for {cache_key}: {e}")
            self._handle_failure()
            return False

    async def delete_namespace(self, namespace: str) -> int:
        """
        Delete all keys in a namespace (cache invalidation).

        Args:
            namespace: Cache namespace to clear

        Returns:
            Number of keys deleted
        """
        client = await self._get_client()
        if client is None:
            return 0

        pattern = f"{self._key_prefix}:{namespace}:*"

        try:
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await client.delete(*keys)
                self._handle_success()
                logger.info(f"Cache INVALIDATE: {namespace} ({deleted} keys)")
                return deleted

            return 0

        except RedisError as e:
            logger.warning(f"Cache invalidate error for {namespace}: {e}")
            self._handle_failure()
            return 0

    async def invalidate_pipeline_cache(self) -> None:
        """Invalidate all pipeline-related caches."""
        await self.delete_namespace(self.NS_PIPELINE_STEPS)
        await self.delete_namespace(self.NS_DOCUMENT_CLASSES)
        await self.delete_namespace(self.NS_AVAILABLE_MODELS)
        logger.info("Pipeline cache invalidated")

    async def invalidate_settings_cache(self) -> None:
        """Invalidate all settings-related caches."""
        await self.delete_namespace(self.NS_SYSTEM_SETTINGS)
        await self.delete_namespace(self.NS_OCR_CONFIG)
        logger.info("Settings cache invalidated")

    async def invalidate_all(self) -> None:
        """Invalidate all caches."""
        await self.invalidate_pipeline_cache()
        await self.invalidate_settings_cache()
        logger.info("All caches invalidated")

    async def health_check(self) -> bool:
        """
        Check Redis connectivity.

        Returns:
            True if Redis is healthy, False otherwise
        """
        if not self._enabled:
            return False

        client = await self._get_client()
        if client is None:
            return False

        try:
            await client.ping()
            self._handle_success()
            return True

        except RedisError as e:
            logger.warning(f"Redis health check failed: {e}")
            self._handle_failure()
            return False

    def get_metrics(self) -> dict[str, Any]:
        """
        Get cache performance metrics.

        Returns:
            Dictionary with cache statistics
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0

        return {
            "enabled": self._enabled,
            "is_healthy": self._is_healthy,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_errors": self._cache_errors,
            "hit_rate_percent": round(hit_rate, 2),
            "failure_count": self._failure_count,
        }

    async def close(self) -> None:
        """Close Redis connections."""
        if self._client is not None:
            await self._client.close()
            self._client = None

        if self._pool is not None:
            await self._pool.disconnect()
            self._pool = None

        logger.info("Redis cache connections closed")


# Singleton instance
def get_cache_service() -> CacheService:
    """Get the singleton cache service instance."""
    return CacheService()
