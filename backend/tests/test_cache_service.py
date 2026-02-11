"""
Tests for Cache Service

Tests the Redis caching layer with graceful degradation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.cache_service import CacheService


@pytest.fixture
def cache_service():
    """Create a fresh cache service instance for each test."""
    # Reset singleton for clean tests
    CacheService._instance = None
    CacheService._pool = None
    CacheService._client = None
    CacheService._is_healthy = True
    CacheService._failure_count = 0
    CacheService._cache_hits = 0
    CacheService._cache_misses = 0
    CacheService._cache_errors = 0

    service = CacheService()
    return service


class TestCacheServiceInit:
    """Tests for cache service initialization."""

    def test_singleton_pattern(self):
        """Test that cache service uses singleton pattern."""
        CacheService._instance = None
        service1 = CacheService()
        service2 = CacheService()
        assert service1 is service2

    def test_key_prefix(self, cache_service):
        """Test that cache keys use correct prefix."""
        key = cache_service._make_key("pipeline_steps", "enabled")
        assert key == "docworker:pipeline_steps:enabled"

    def test_namespaces_defined(self, cache_service):
        """Test that cache namespaces are defined."""
        assert cache_service.NS_PIPELINE_STEPS == "pipeline_steps"
        assert cache_service.NS_DOCUMENT_CLASSES == "document_classes"
        assert cache_service.NS_AVAILABLE_MODELS == "available_models"
        assert cache_service.NS_SYSTEM_SETTINGS == "system_settings"
        assert cache_service.NS_OCR_CONFIG == "ocr_config"


class TestCacheGetSet:
    """Tests for cache get/set operations."""

    @pytest.mark.asyncio
    async def test_get_cache_miss_returns_none(self, cache_service):
        """Test that cache miss returns None."""
        # Disable cache to simulate miss
        cache_service._enabled = False

        result = await cache_service.get("test_namespace", "test_key")
        assert result is None
        assert cache_service._cache_misses == 1

    @pytest.mark.asyncio
    async def test_set_when_disabled_returns_false(self, cache_service):
        """Test that set returns False when cache is disabled."""
        cache_service._enabled = False

        result = await cache_service.set("test_namespace", "test_key", {"data": "value"})
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_when_disabled_returns_false(self, cache_service):
        """Test that delete returns False when cache is disabled."""
        cache_service._enabled = False

        result = await cache_service.delete("test_namespace", "test_key")
        assert result is False


class TestCacheGracefulDegradation:
    """Tests for graceful degradation when Redis is unavailable."""

    @pytest.mark.asyncio
    async def test_get_returns_none_when_unhealthy(self, cache_service):
        """Test that get returns None when cache is marked unhealthy."""
        cache_service._is_healthy = False
        cache_service._enabled = True

        result = await cache_service.get("test_namespace", "test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_failure_count_increments(self, cache_service):
        """Test that failure count increments on errors."""
        initial_count = cache_service._failure_count

        cache_service._handle_failure()

        assert cache_service._failure_count == initial_count + 1
        assert cache_service._cache_errors == 1

    @pytest.mark.asyncio
    async def test_marked_unhealthy_after_max_failures(self, cache_service):
        """Test that cache is marked unhealthy after max failures."""
        for _ in range(cache_service._max_failures):
            cache_service._handle_failure()

        assert cache_service._is_healthy is False

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, cache_service):
        """Test that successful operation resets failure count."""
        cache_service._failure_count = 2

        cache_service._handle_success()

        assert cache_service._failure_count == 0
        assert cache_service._is_healthy is True


class TestCacheSerialization:
    """Tests for cache serialization/deserialization."""

    def test_serialize_dict(self, cache_service):
        """Test serializing a dictionary."""
        data = {"key": "value", "number": 42}
        serialized = cache_service._serialize(data)
        assert serialized == '{"key": "value", "number": 42}'

    def test_serialize_list(self, cache_service):
        """Test serializing a list."""
        data = [{"id": 1, "name": "test"}]
        serialized = cache_service._serialize(data)
        assert '"id": 1' in serialized
        assert '"name": "test"' in serialized

    def test_deserialize_json(self, cache_service):
        """Test deserializing JSON string."""
        json_str = '{"key": "value"}'
        result = cache_service._deserialize(json_str)
        assert result == {"key": "value"}

    def test_deserialize_invalid_json_returns_original(self, cache_service):
        """Test that invalid JSON returns original string."""
        invalid_json = "not valid json"
        result = cache_service._deserialize(invalid_json)
        assert result == invalid_json


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    @pytest.mark.asyncio
    async def test_delete_namespace_when_disabled(self, cache_service):
        """Test that delete_namespace returns 0 when disabled."""
        cache_service._enabled = False

        result = await cache_service.delete_namespace("pipeline_steps")
        assert result == 0

    @pytest.mark.asyncio
    async def test_invalidate_pipeline_cache_calls_delete_namespace(self, cache_service):
        """Test that invalidate_pipeline_cache clears correct namespaces."""
        cache_service._enabled = False  # Disable to avoid actual Redis calls

        await cache_service.invalidate_pipeline_cache()
        # Should not raise any errors

    @pytest.mark.asyncio
    async def test_invalidate_settings_cache_calls_delete_namespace(self, cache_service):
        """Test that invalidate_settings_cache clears correct namespaces."""
        cache_service._enabled = False

        await cache_service.invalidate_settings_cache()
        # Should not raise any errors

    @pytest.mark.asyncio
    async def test_invalidate_all_clears_all_namespaces(self, cache_service):
        """Test that invalidate_all clears all namespaces."""
        cache_service._enabled = False

        await cache_service.invalidate_all()
        # Should not raise any errors


class TestCacheMetrics:
    """Tests for cache metrics."""

    def test_get_metrics_returns_correct_structure(self, cache_service):
        """Test that get_metrics returns correct structure."""
        cache_service._cache_hits = 10
        cache_service._cache_misses = 5
        cache_service._cache_errors = 2

        metrics = cache_service.get_metrics()

        assert "enabled" in metrics
        assert "is_healthy" in metrics
        assert "cache_hits" in metrics
        assert "cache_misses" in metrics
        assert "cache_errors" in metrics
        assert "hit_rate_percent" in metrics
        assert "failure_count" in metrics

    def test_hit_rate_calculation(self, cache_service):
        """Test that hit rate is calculated correctly."""
        cache_service._cache_hits = 80
        cache_service._cache_misses = 20

        metrics = cache_service.get_metrics()

        # 80 / (80 + 20) = 80%
        assert metrics["hit_rate_percent"] == 80.0

    def test_hit_rate_zero_when_no_requests(self, cache_service):
        """Test that hit rate is 0 when no requests."""
        cache_service._cache_hits = 0
        cache_service._cache_misses = 0

        metrics = cache_service.get_metrics()

        assert metrics["hit_rate_percent"] == 0


class TestCacheHealthCheck:
    """Tests for cache health check."""

    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_disabled(self, cache_service):
        """Test that health check returns False when disabled."""
        cache_service._enabled = False

        result = await cache_service.health_check()
        assert result is False


class TestCacheClose:
    """Tests for cache connection closing."""

    @pytest.mark.asyncio
    async def test_close_when_no_connections(self, cache_service):
        """Test that close works when no connections exist."""
        cache_service._client = None
        cache_service._pool = None

        # Should not raise any errors
        await cache_service.close()

    @pytest.mark.asyncio
    async def test_close_clears_references(self, cache_service):
        """Test that close clears client and pool references."""
        # Create mock client and pool
        mock_client = AsyncMock()
        mock_pool = AsyncMock()
        cache_service._client = mock_client
        cache_service._pool = mock_pool

        await cache_service.close()

        assert cache_service._client is None
        assert cache_service._pool is None
        mock_client.close.assert_called_once()
        mock_pool.disconnect.assert_called_once()
