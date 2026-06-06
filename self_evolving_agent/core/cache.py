"""
阶段34: 缓存接口标准化

第一性原理:
1. 缓存是空间换时间的核心策略
2. 但缓存必须有统一的接口、可配置的淘汰策略、可观测的命中率
3. 否则将成为一致性的噩梦

设计原则:
- 统一接口：get/set/delete/clear
- 支持TTL：每个条目可配置生存时间
- 多种淘汰策略：LRU/LFU/FIFO
- 可观测：命中率、大小、条目数
- 线程安全
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional, Generic, TypeVar
from enum import Enum
from datetime import datetime, timedelta
from collections import OrderedDict
import threading
import time

K = TypeVar('K')
V = TypeVar('V')


class EvictionPolicy(Enum):
    """淘汰策略"""
    LRU = "lru"         # 最近最少使用
    LFU = "lfu"         # 最不经常使用
    FIFO = "fifo"       # 先进先出
    TTL_ONLY = "ttl"    # 仅TTL过期


@dataclass
class CacheEntry(Generic[V]):
    """缓存条目"""
    value: V
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


# ============================================================
# 缓存接口
# ============================================================

class Cache(Generic[K, V]):
    """
    缓存接口

    第一性原理：缓存是对昂贵计算的短路，必须有明确的语义和边界
    """

    def get(self, key: K) -> Optional[V]:
        """获取值"""
        raise NotImplementedError

    def set(self, key: K, value: V, ttl_seconds: Optional[float] = None) -> None:
        """设置值"""
        raise NotImplementedError

    def delete(self, key: K) -> bool:
        """删除值"""
        raise NotImplementedError

    def clear(self) -> None:
        """清空缓存"""
        raise NotImplementedError

    def contains(self, key: K) -> bool:
        """检查是否包含"""
        raise NotImplementedError

    def size(self) -> int:
        """获取条目数"""
        raise NotImplementedError

    def keys(self) -> List[K]:
        """获取所有键"""
        raise NotImplementedError

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        raise NotImplementedError


# ============================================================
# 内存缓存实现
# ============================================================

class MemoryCache(Cache[K, V]):
    """
    内存缓存

    支持多种淘汰策略和TTL
    """

    def __init__(
        self,
        max_size: int = 1000,
        policy: EvictionPolicy = EvictionPolicy.LRU,
        default_ttl_seconds: Optional[float] = None,
    ):
        self.max_size = max_size
        self.policy = policy
        self.default_ttl_seconds = default_ttl_seconds

        self._data: Dict[K, CacheEntry[V]] = {}
        self._lock = threading.RLock()

        # 统计
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: K) -> Optional[V]:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                del self._data[key]
                self._misses += 1
                return None

            # 更新访问信息
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            self._hits += 1

            return entry.value

    def set(self, key: K, value: V, ttl_seconds: Optional[float] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds

        expires = None
        if ttl is not None:
            expires = datetime.now() + timedelta(seconds=ttl)

        entry = CacheEntry(
            value=value,
            expires_at=expires,
        )

        with self._lock:
            # 淘汰检查
            if key not in self._data and len(self._data) >= self.max_size:
                self._evict()

            self._data[key] = entry

    def delete(self, key: K) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def contains(self, key: K) -> bool:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return False
            if entry.is_expired():
                del self._data[key]
                return False
            return True

    def size(self) -> int:
        with self._lock:
            self._cleanup_expired()
            return len(self._data)

    def keys(self) -> List[K]:
        with self._lock:
            self._cleanup_expired()
            return list(self._data.keys())

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            return {
                "size": len(self._data),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "evictions": self._evictions,
                "policy": self.policy.value,
            }

    def _evict(self) -> None:
        """淘汰条目"""
        if not self._data:
            return

        if self.policy == EvictionPolicy.LRU:
            # 淘汰最近最少使用
            key_to_evict = min(self._data.keys(),
                               key=lambda k: self._data[k].last_accessed)
        elif self.policy == EvictionPolicy.LFU:
            # 淘汰最不经常使用
            key_to_evict = min(self._data.keys(),
                               key=lambda k: self._data[k].access_count)
        elif self.policy == EvictionPolicy.FIFO:
            # 淘汰最早进入
            key_to_evict = min(self._data.keys(),
                               key=lambda k: self._data[k].created_at)
        else:
            # TTL_ONLY：不主动淘汰，但这里必须淘汰一个
            key_to_evict = next(iter(self._data.keys()))

        del self._data[key_to_evict]
        self._evictions += 1

    def _cleanup_expired(self) -> None:
        """清理过期条目"""
        expired = [k for k, v in self._data.items() if v.is_expired()]
        for k in expired:
            del self._data[k]


# ============================================================
# LRU缓存（OrderedDict实现，O(1)访问）
# ============================================================

class LRUCache(Cache[K, V]):
    """
    LRU缓存

    使用OrderedDict实现O(1)的get和set
    """

    def __init__(self, max_size: int = 1000,
                 default_ttl_seconds: Optional[float] = None):
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds

        self._data: OrderedDict = OrderedDict()
        self._lock = threading.RLock()

        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: K) -> Optional[V]:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                del self._data[key]
                self._misses += 1
                return None

            # 移到末尾（最近使用）
            self._data.move_to_end(key)
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            self._hits += 1

            return entry.value

    def set(self, key: K, value: V, ttl_seconds: Optional[float] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expires = None
        if ttl is not None:
            expires = datetime.now() + timedelta(seconds=ttl)

        entry = CacheEntry(value=value, expires_at=expires)

        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                self._data[key] = entry
                return

            if len(self._data) >= self.max_size:
                self._data.popitem(last=False)
                self._evictions += 1

            self._data[key] = entry

    def delete(self, key: K) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def contains(self, key: K) -> bool:
        return self.get(key) is not None

    def size(self) -> int:
        with self._lock:
            self._cleanup_expired()
            return len(self._data)

    def keys(self) -> List[K]:
        with self._lock:
            self._cleanup_expired()
            return list(self._data.keys())

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            return {
                "size": len(self._data),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "evictions": self._evictions,
                "policy": "lru_ordered",
            }

    def _cleanup_expired(self) -> None:
        expired = [k for k, v in self._data.items() if v.is_expired()]
        for k in expired:
            del self._data[k]


# ============================================================
# 缓存装饰器
# ============================================================

def cached(cache: Cache, key_fn: Optional[Callable] = None,
           ttl_seconds: Optional[float] = None):
    """
    缓存装饰器

    自动缓存函数结果
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            if key_fn:
                cache_key = key_fn(*args, **kwargs)
            else:
                cache_key = (args, tuple(sorted(kwargs.items())))

            result = cache.get(cache_key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            return result

        return wrapper
    return decorator


# ============================================================
# 便捷函数
# ============================================================

def create_cache(max_size: int = 1000, policy: EvictionPolicy = EvictionPolicy.LRU,
                 default_ttl_seconds: Optional[float] = None) -> Cache:
    """创建缓存"""
    if policy == EvictionPolicy.LRU:
        return LRUCache(max_size, default_ttl_seconds)
    return MemoryCache(max_size, policy, default_ttl_seconds)
