"""
Redis caching service for query results
Supports both GCP discovery results and task queries
"""

import json
import os
import hashlib
from typing import Optional, Any, Dict, List, TypeVar, Callable
from datetime import datetime, timedelta
from functools import wraps
import asyncio
import logging

logger = logging.getLogger(__name__)

# Try to import redis, fall back to in-memory cache if not available
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache")

T = TypeVar('T')


class CacheConfig:
    """Cache configuration"""
    # Cache TTL settings (in seconds)
    GCP_ARCHITECTURE_TTL = 300  # 5 minutes
    GCP_RESOURCES_TTL = 300  # 5 minutes
    TASK_LIST_TTL = 60  # 1 minute
    TASK_DETAIL_TTL = 120  # 2 minutes
    
    # Cache key prefixes
    GCP_ARCH_PREFIX = "gcp:arch:"
    GCP_RESOURCES_PREFIX = "gcp:resources:"
    TASK_LIST_PREFIX = "tasks:list:"
    TASK_DETAIL_PREFIX = "tasks:detail:"
    
    # Maximum in-memory cache size (entries)
    MAX_MEMORY_CACHE_SIZE = 1000


class InMemoryCache:
    """Fallback in-memory LRU cache when Redis is unavailable"""
    
    def __init__(self, max_size: int = CacheConfig.MAX_MEMORY_CACHE_SIZE):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry)
        self._access_order: List[str] = []  # LRU tracking
        self._max_size = max_size
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if datetime.utcnow() < expiry:
                    # Update access order for LRU
                    if key in self._access_order:
                        self._access_order.remove(key)
                    self._access_order.append(key)
                    return value
                else:
                    # Expired, remove it
                    del self._cache[key]
                    if key in self._access_order:
                        self._access_order.remove(key)
            return None
    
    async def set(self, key: str, value: str, ex: int = 300) -> bool:
        async with self._lock:
            # Evict oldest entries if at capacity
            while len(self._cache) >= self._max_size and self._access_order:
                oldest_key = self._access_order.pop(0)
                if oldest_key in self._cache:
                    del self._cache[oldest_key]
            
            expiry = datetime.utcnow() + timedelta(seconds=ex)
            self._cache[key] = (value, expiry)
            
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            return True
    
    async def delete(self, key: str) -> int:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return 1
            return 0
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern (simple prefix match)"""
        async with self._lock:
            prefix = pattern.rstrip("*")
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            return len(keys_to_delete)
    
    async def exists(self, key: str) -> bool:
        result = await self.get(key)
        return result is not None
    
    async def close(self):
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()


class CacheService:
    """Redis cache service with fallback to in-memory cache"""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._memory_cache = InMemoryCache()
        self._connected = False
    
    async def connect(self):
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            logger.info("Using in-memory cache (Redis not installed)")
            return
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        try:
            self._redis = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            await self._redis.ping()
            self._connected = True
            logger.info(f"✅ Connected to Redis at {redis_url}")
        except Exception as e:
            logger.warning(f"⚠️ Could not connect to Redis: {e}. Using in-memory cache.")
            self._redis = None
            self._connected = False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
        await self._memory_cache.close()
    
    @property
    def client(self):
        """Get cache client (Redis or in-memory)"""
        return self._redis if self._redis else self._memory_cache
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments"""
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None)
        key_data = ":".join(key_parts)
        
        # Use hash for long keys
        if len(key_data) > 100:
            key_hash = hashlib.md5(key_data.encode()).hexdigest()[:16]
            return f"{prefix}{key_hash}"
        
        return f"{prefix}{key_data}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            data = await self.client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL"""
        try:
            data = json.dumps(value, default=str)
            await self.client.set(key, data, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        try:
            if self._redis:
                # Redis SCAN for pattern matching
                count = 0
                async for key in self._redis.scan_iter(match=pattern):
                    await self._redis.delete(key)
                    count += 1
                return count
            else:
                # In-memory pattern delete
                return await self._memory_cache.delete_pattern(pattern)
        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")
            return 0
    
    # ===== GCP Architecture Caching =====
    
    async def get_gcp_architecture(self, project_id: str) -> Optional[Dict]:
        """Get cached GCP architecture"""
        key = self._generate_key(CacheConfig.GCP_ARCH_PREFIX, project_id)
        return await self.get(key)
    
    async def set_gcp_architecture(self, project_id: str, architecture: Dict) -> bool:
        """Cache GCP architecture"""
        key = self._generate_key(CacheConfig.GCP_ARCH_PREFIX, project_id)
        return await self.set(key, architecture, CacheConfig.GCP_ARCHITECTURE_TTL)
    
    async def invalidate_gcp_architecture(self, project_id: str) -> bool:
        """Invalidate GCP architecture cache"""
        key = self._generate_key(CacheConfig.GCP_ARCH_PREFIX, project_id)
        return await self.delete(key)
    
    # ===== GCP Resources Caching =====
    
    async def get_gcp_resources(
        self,
        project_id: str,
        resource_type: Optional[str] = None,
        region: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """Get cached GCP resources with optional filters"""
        key = self._generate_key(
            CacheConfig.GCP_RESOURCES_PREFIX,
            project_id,
            type=resource_type,
            region=region
        )
        return await self.get(key)
    
    async def set_gcp_resources(
        self,
        project_id: str,
        resources: List[Dict],
        resource_type: Optional[str] = None,
        region: Optional[str] = None
    ) -> bool:
        """Cache GCP resources"""
        key = self._generate_key(
            CacheConfig.GCP_RESOURCES_PREFIX,
            project_id,
            type=resource_type,
            region=region
        )
        return await self.set(key, resources, CacheConfig.GCP_RESOURCES_TTL)
    
    async def invalidate_gcp_project(self, project_id: str) -> int:
        """Invalidate all caches for a GCP project"""
        count = 0
        count += await self.invalidate_pattern(f"{CacheConfig.GCP_ARCH_PREFIX}{project_id}*")
        count += await self.invalidate_pattern(f"{CacheConfig.GCP_RESOURCES_PREFIX}{project_id}*")
        return count
    
    # ===== Task Caching =====
    
    async def get_task_list(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """Get cached task list"""
        key = self._generate_key(
            CacheConfig.TASK_LIST_PREFIX,
            project=project_id or "all",
            status=status
        )
        return await self.get(key)
    
    async def set_task_list(
        self,
        tasks: List[Dict],
        project_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> bool:
        """Cache task list"""
        key = self._generate_key(
            CacheConfig.TASK_LIST_PREFIX,
            project=project_id or "all",
            status=status
        )
        return await self.set(key, tasks, CacheConfig.TASK_LIST_TTL)
    
    async def get_task_detail(self, task_id: str) -> Optional[Dict]:
        """Get cached task detail"""
        key = self._generate_key(CacheConfig.TASK_DETAIL_PREFIX, task_id)
        return await self.get(key)
    
    async def set_task_detail(self, task_id: str, task: Dict) -> bool:
        """Cache task detail"""
        key = self._generate_key(CacheConfig.TASK_DETAIL_PREFIX, task_id)
        return await self.set(key, task, CacheConfig.TASK_DETAIL_TTL)
    
    async def invalidate_task(self, task_id: str) -> int:
        """Invalidate task caches"""
        count = 0
        # Invalidate specific task
        key = self._generate_key(CacheConfig.TASK_DETAIL_PREFIX, task_id)
        if await self.delete(key):
            count += 1
        # Invalidate all task lists (since task changed)
        count += await self.invalidate_pattern(f"{CacheConfig.TASK_LIST_PREFIX}*")
        return count
    
    async def invalidate_all_tasks(self) -> int:
        """Invalidate all task caches"""
        count = 0
        count += await self.invalidate_pattern(f"{CacheConfig.TASK_LIST_PREFIX}*")
        count += await self.invalidate_pattern(f"{CacheConfig.TASK_DETAIL_PREFIX}*")
        return count


# Global cache instance
_cache_service: Optional[CacheService] = None


async def get_cache() -> CacheService:
    """Get or create cache service"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.connect()
    return _cache_service


async def close_cache():
    """Close cache service"""
    global _cache_service
    if _cache_service:
        await _cache_service.disconnect()
        _cache_service = None


# ===== Decorator for caching function results =====

def cached(
    prefix: str,
    ttl: int = 300,
    key_builder: Optional[Callable[..., str]] = None
):
    """
    Decorator for caching async function results
    
    Usage:
        @cached("my_func:", ttl=60)
        async def my_function(arg1, arg2):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = await get_cache()
            
            # Build cache key
            if key_builder:
                key = key_builder(*args, **kwargs)
            else:
                key_parts = [str(arg) for arg in args]
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key = f"{prefix}{':'.join(key_parts)}"
            
            # Try to get from cache
            cached_result = await cache.get(key)
            if cached_result is not None:
                logger.debug(f"Cache HIT: {key}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache MISS: {key}")
            result = await func(*args, **kwargs)
            
            if result is not None:
                await cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

