"""
缓存管理器

支持 Redis 和内存缓存（开发环境降级）
"""

import json
import logging
import time
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# 尝试导入 Redis
try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class InMemoryCache:
    """内存缓存（Redis 不可用时的降级方案）"""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}

    async def get(self, key: str) -> Optional[str]:
        if key in self._store:
            value, expire_at = self._store[key]
            if expire_at > time.time():
                return value
            del self._store[key]
        return None

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = (value, time.time() + ttl)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        if key in self._store:
            _, expire_at = self._store[key]
            if expire_at > time.time():
                return True
            del self._store[key]
        return False

    async def scan_iter(self, pattern: str):
        """简化的 scan_iter，仅支持前缀匹配"""
        prefix = pattern.rstrip("*")
        now = time.time()
        for key in list(self._store.keys()):
            if key.startswith(prefix):
                _, expire_at = self._store[key]
                if expire_at > now:
                    yield key
                else:
                    del self._store[key]

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        self._store.clear()


# 全局内存缓存实例（所有 CacheManager 共享）
_global_memory_cache: Optional[InMemoryCache] = None


class CacheManager:
    """
    缓存管理器

    优先使用 Redis，不可用时降级为共享的内存缓存。
    """

    def __init__(self, redis_url: Optional[str] = None):
        global _global_memory_cache
        if redis_url:
            self.redis_url = redis_url
        elif settings.REDIS_URL:
            self.redis_url = str(settings.REDIS_URL)
        else:
            self.redis_url = None
        self._use_memory = False
        # 内存缓存使用全局单例
        if _global_memory_cache is None:
            _global_memory_cache = InMemoryCache()
        self._client = _global_memory_cache

    async def _get_client(self):
        """获取缓存客户端（Redis 或内存）"""
        if self._client is not None:
            return self._client

        # 尝试 Redis
        if REDIS_AVAILABLE and self.redis_url:
            try:
                self._client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await self._client.ping()
                logger.info("Using Redis cache")
                return self._client
            except Exception as e:
                logger.warning(f"Redis unavailable, falling back to memory cache: {e}")

        # 降级到内存缓存
        self._client = InMemoryCache()
        self._use_memory = True
        logger.info("Using in-memory cache")
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在返回 None
        """
        try:
            client = await self._get_client()
            value = await client.get(f"{settings.CACHE_PREFIX}{key}")
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）

        Returns:
            是否成功
        """
        try:
            client = await self._get_client()
            serialized = json.dumps(value)
            ttl = ttl or settings.CACHE_TTL
            await client.setex(
                f"{settings.CACHE_PREFIX}{key}",
                ttl,
                serialized,
            )
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否成功
        """
        try:
            client = await self._get_client()
            await client.delete(f"{settings.CACHE_PREFIX}{key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        try:
            client = await self._get_client()
            return await client.exists(f"{settings.CACHE_PREFIX}{key}") > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False

    async def clear_prefix(self, prefix: str) -> int:
        """
        清除指定前缀的缓存

        Args:
            prefix: 缓存键前缀

        Returns:
            删除的数量
        """
        try:
            client = await self._get_client()
            pattern = f"{settings.CACHE_PREFIX}{prefix}*"
            keys = []
            async for key in client.scan_iter(pattern):
                keys.append(key)

            if keys:
                return await client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear_prefix error: {e}")
            return 0

    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
            self._client = None
