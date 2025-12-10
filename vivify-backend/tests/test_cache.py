"""
Tests for Redis caching service
Verifies caching functionality with in-memory fallback
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta

from services.cache import (
    CacheService, CacheConfig, InMemoryCache,
    get_cache, close_cache, cached
)


@pytest.fixture
async def cache_service():
    """Create a cache service for testing (uses in-memory fallback)"""
    service = CacheService()
    # Don't connect to Redis - use in-memory cache
    yield service
    await service.disconnect()


@pytest.fixture
async def memory_cache():
    """Create an in-memory cache for testing"""
    cache = InMemoryCache(max_size=100)
    yield cache
    await cache.close()


class TestInMemoryCache:
    """Tests for the in-memory LRU cache fallback"""
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, memory_cache):
        """Test basic set and get operations"""
        await memory_cache.set("test_key", '{"value": "test"}', ex=300)
        result = await memory_cache.get("test_key")
        
        assert result == '{"value": "test"}'
    
    @pytest.mark.asyncio
    async def test_expiry(self, memory_cache):
        """Test that expired keys return None"""
        await memory_cache.set("expiring_key", "value", ex=1)
        
        # Key should exist immediately
        result = await memory_cache.get("expiring_key")
        assert result == "value"
        
        # Wait for expiry
        await asyncio.sleep(1.1)
        
        # Key should be expired
        result = await memory_cache.get("expiring_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete(self, memory_cache):
        """Test key deletion"""
        await memory_cache.set("delete_key", "value", ex=300)
        
        # Verify key exists
        assert await memory_cache.get("delete_key") == "value"
        
        # Delete key
        deleted = await memory_cache.delete("delete_key")
        assert deleted == 1
        
        # Verify key is gone
        assert await memory_cache.get("delete_key") is None
    
    @pytest.mark.asyncio
    async def test_delete_pattern(self, memory_cache):
        """Test pattern-based deletion"""
        await memory_cache.set("prefix:key1", "value1", ex=300)
        await memory_cache.set("prefix:key2", "value2", ex=300)
        await memory_cache.set("other:key3", "value3", ex=300)
        
        # Delete prefix:* pattern
        deleted = await memory_cache.delete_pattern("prefix:*")
        assert deleted == 2
        
        # Verify prefix keys are gone
        assert await memory_cache.get("prefix:key1") is None
        assert await memory_cache.get("prefix:key2") is None
        
        # Verify other key still exists
        assert await memory_cache.get("other:key3") == "value3"
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        small_cache = InMemoryCache(max_size=3)
        
        await small_cache.set("key1", "value1", ex=300)
        await small_cache.set("key2", "value2", ex=300)
        await small_cache.set("key3", "value3", ex=300)
        
        # Access key1 to make it recently used
        await small_cache.get("key1")
        
        # Add key4 - should evict key2 (least recently used)
        await small_cache.set("key4", "value4", ex=300)
        
        # key1 should still exist (was accessed)
        assert await small_cache.get("key1") == "value1"
        # key2 should be evicted
        assert await small_cache.get("key2") is None
        # key3 and key4 should exist
        assert await small_cache.get("key3") == "value3"
        assert await small_cache.get("key4") == "value4"
        
        await small_cache.close()


class TestCacheService:
    """Tests for the main cache service"""
    
    @pytest.mark.asyncio
    async def test_set_and_get_json(self, cache_service):
        """Test setting and getting JSON data"""
        test_data = {"name": "test", "count": 42, "nested": {"key": "value"}}
        
        success = await cache_service.set("json_key", test_data, ttl=300)
        assert success is True
        
        result = await cache_service.get("json_key")
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_gcp_architecture_caching(self, cache_service):
        """Test GCP architecture caching methods"""
        project_id = "test-project"
        architecture = {
            "project": project_id,
            "resources": [{"id": "vm-1", "type": "compute"}],
            "totalCost": 100.0
        }
        
        # Cache architecture
        success = await cache_service.set_gcp_architecture(project_id, architecture)
        assert success is True
        
        # Retrieve cached architecture
        cached = await cache_service.get_gcp_architecture(project_id)
        assert cached == architecture
        
        # Invalidate cache
        success = await cache_service.invalidate_gcp_architecture(project_id)
        assert success is True
        
        # Verify cache is cleared
        cached = await cache_service.get_gcp_architecture(project_id)
        assert cached is None
    
    @pytest.mark.asyncio
    async def test_task_list_caching(self, cache_service):
        """Test task list caching methods"""
        tasks = [
            {"id": "task-1", "title": "Task 1", "status": "todo"},
            {"id": "task-2", "title": "Task 2", "status": "inprogress"},
        ]
        
        # Cache task list
        success = await cache_service.set_task_list(tasks, project_id="test", status="todo")
        assert success is True
        
        # Retrieve cached tasks
        cached = await cache_service.get_task_list(project_id="test", status="todo")
        assert cached == tasks
    
    @pytest.mark.asyncio
    async def test_task_detail_caching(self, cache_service):
        """Test individual task caching"""
        task = {"id": "task-1", "title": "Detailed Task", "description": "Full details"}
        
        # Cache task
        success = await cache_service.set_task_detail("task-1", task)
        assert success is True
        
        # Retrieve cached task
        cached = await cache_service.get_task_detail("task-1")
        assert cached == task
    
    @pytest.mark.asyncio
    async def test_task_invalidation(self, cache_service):
        """Test task cache invalidation"""
        # Cache some data
        await cache_service.set_task_detail("task-1", {"id": "task-1"})
        await cache_service.set_task_list([{"id": "task-1"}])
        
        # Invalidate task
        count = await cache_service.invalidate_task("task-1")
        
        # Verify caches are cleared
        assert await cache_service.get_task_detail("task-1") is None


class TestCachedDecorator:
    """Tests for the @cached decorator"""
    
    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        """Test that @cached decorator caches function results"""
        call_count = 0
        
        @cached("test_func:", ttl=60)
        async def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y
        
        # Initialize cache
        await get_cache()
        
        # First call - should execute function
        result1 = await expensive_function(1, 2)
        assert result1 == 3
        assert call_count == 1
        
        # Second call with same args - should use cache
        result2 = await expensive_function(1, 2)
        assert result2 == 3
        assert call_count == 1  # Function not called again
        
        # Different args - should execute function
        result3 = await expensive_function(2, 3)
        assert result3 == 5
        assert call_count == 2
        
        await close_cache()


class TestCacheTTL:
    """Tests for cache TTL configuration"""
    
    def test_cache_config_values(self):
        """Verify cache TTL configuration values"""
        assert CacheConfig.GCP_ARCHITECTURE_TTL == 300  # 5 minutes
        assert CacheConfig.GCP_RESOURCES_TTL == 300
        assert CacheConfig.TASK_LIST_TTL == 60  # 1 minute
        assert CacheConfig.TASK_DETAIL_TTL == 120  # 2 minutes
    
    def test_cache_key_prefixes(self):
        """Verify cache key prefixes are set"""
        assert CacheConfig.GCP_ARCH_PREFIX == "gcp:arch:"
        assert CacheConfig.GCP_RESOURCES_PREFIX == "gcp:resources:"
        assert CacheConfig.TASK_LIST_PREFIX == "tasks:list:"
        assert CacheConfig.TASK_DETAIL_PREFIX == "tasks:detail:"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

