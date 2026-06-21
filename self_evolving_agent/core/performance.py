"""
阶段130: 性能优化层 — 测量、缓存、并发、批处理

第一性原理:
1. 测量先行：不可测量的东西无法优化（"Premature optimization is the root of all evil" — 但无测量更糟）
2. 缓存复用：重复计算的结果应被缓存（时间换空间）
3. 并发并行：独立任务应并行执行（Amdahl定律）
4. 懒加载：不需要的资源不应提前初始化（延迟到首次使用）
5. 批处理：多个小操作应合并为大操作（减少开销摊薄）
6. 资源池化：重复创建/销毁的资源应池化（对象复用）

提供:
- PerformanceMetrics: 性能指标收集（计时器、计数器、直方图）
- CacheLayer: 多级缓存（LRU + TTL）
- ConcurrentExecutor: 并发执行器（线程池）
- LazyLoader: 懒加载器
- BatchProcessor: 批处理器
- ObjectPool: 对象池
- Profiler: 性能分析器
- PerformanceMonitor: 性能监控器
"""

import time
import threading
import functools
import collections
import heapq
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Generic, Iterator
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from collections import OrderedDict, deque

T = TypeVar("T")
R = TypeVar("R")


# ============================================================
# 性能指标收集
# ============================================================

@dataclass
class TimerRecord:
    """计时记录"""
    name: str
    duration: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CounterRecord:
    """计数记录"""
    name: str
    value: int
    timestamp: float


@dataclass
class HistogramRecord:
    """直方图记录"""
    name: str
    value: float
    timestamp: float


class PerformanceMetrics:
    """
    性能指标收集器

    线程安全地收集计时、计数、直方图指标。
    """

    def __init__(self, max_records: int = 10000):
        self._max_records = max_records
        self._timers: deque = deque(maxlen=max_records)
        self._counters: Dict[str, int] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._lock = threading.RLock()

    def timer(self, name: str, **metadata) -> "TimerContext":
        """创建计时上下文管理器"""
        return TimerContext(self, name, metadata)

    def record_timer(self, name: str, duration: float, **metadata) -> None:
        """记录计时"""
        with self._lock:
            self._timers.append(TimerRecord(
                name=name, duration=duration,
                timestamp=time.time(), metadata=metadata
            ))

    def increment(self, name: str, value: int = 1) -> None:
        """增加计数器"""
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value

    def get_counter(self, name: str) -> int:
        """获取计数器值"""
        with self._lock:
            return self._counters.get(name, 0)

    def observe(self, name: str, value: float) -> None:
        """记录直方图观测值"""
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = []
            hist = self._histograms[name]
            hist.append(value)
            # 限制直方图大小
            if len(hist) > 1000:
                self._histograms[name] = hist[-500:]

    def get_timer_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """获取计时统计"""
        with self._lock:
            timers = list(self._timers)
            if name:
                timers = [t for t in timers if t.name == name]
            if not timers:
                return {}
            durations = [t.duration for t in timers]
            return {
                "count": len(durations),
                "total": sum(durations),
                "avg": sum(durations) / len(durations),
                "min": min(durations),
                "max": max(durations),
                "last": durations[-1] if durations else 0,
            }

    def get_histogram_stats(self, name: str) -> Dict[str, Any]:
        """获取直方图统计"""
        with self._lock:
            hist = self._histograms.get(name, [])
            if not hist:
                return {}
            sorted_hist = sorted(hist)
            n = len(sorted_hist)
            return {
                "count": n,
                "avg": sum(hist) / n,
                "min": sorted_hist[0],
                "max": sorted_hist[-1],
                "p50": sorted_hist[n // 2],
                "p90": sorted_hist[int(n * 0.9)] if n > 1 else sorted_hist[0],
                "p99": sorted_hist[int(n * 0.99)] if n > 1 else sorted_hist[0],
            }

    def get_all_counters(self) -> Dict[str, int]:
        """获取所有计数器"""
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        """重置所有指标"""
        with self._lock:
            self._timers.clear()
            self._counters.clear()
            self._histograms.clear()

    def snapshot(self) -> Dict[str, Any]:
        """获取指标快照"""
        with self._lock:
            return {
                "timers": self.get_timer_stats(),
                "counters": dict(self._counters),
                "histograms": {
                    name: self.get_histogram_stats(name)
                    for name in self._histograms
                },
                "timestamp": time.time(),
            }


class TimerContext:
    """计时上下文管理器"""

    def __init__(self, metrics: PerformanceMetrics, name: str, metadata: Dict[str, Any]):
        self._metrics = metrics
        self._name = name
        self._metadata = metadata
        self._start: Optional[float] = None

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._start is not None:
            duration = time.perf_counter() - self._start
            self._metrics.record_timer(self._name, duration, **self._metadata)
        return False


# ============================================================
# 缓存层
# ============================================================

@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""
    value: T
    created_at: float
    ttl: Optional[float] = None
    access_count: int = 0
    last_access: float = 0.0

    def is_expired(self) -> bool:
        """是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl


class LRUCache(Generic[T]):
    """
    LRU缓存

    最近最少使用淘汰策略。
    线程安全。
    """

    def __init__(self, max_size: int = 1000):
        self._max_size = max_size
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[T]:
        """获取缓存值"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            # 移到末尾（最近使用）
            self._cache.move_to_end(key)
            entry.access_count += 1
            entry.last_access = time.time()
            self._hits += 1
            return entry.value

    def put(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """放入缓存"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            entry = CacheEntry(
                value=value, created_at=time.time(),
                ttl=ttl, last_access=time.time()
            )
            self._cache[key] = entry
            # 淘汰最久未使用
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def invalidate(self, key: str) -> bool:
        """使缓存条目失效"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def size(self) -> int:
        """获取缓存大小"""
        with self._lock:
            return len(self._cache)

    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
            }


class CacheLayer:
    """
    多级缓存层

    支持多级缓存（L1/L2），可配置TTL和最大大小。
    """

    def __init__(self, levels: Optional[List[Dict[str, Any]]] = None):
        if levels is None:
            levels = [
                {"name": "L1", "max_size": 100, "ttl": 60},
                {"name": "L2", "max_size": 1000, "ttl": 3600},
            ]
        self._caches: List[Tuple[str, LRUCache]] = [
            (cfg["name"], LRUCache(max_size=cfg.get("max_size", 1000)))
            for cfg in levels
        ]
        self._ttls: Dict[str, Optional[float]] = {
            cfg["name"]: cfg.get("ttl") for cfg in levels
        }

    def get(self, key: str) -> Optional[Any]:
        """从多级缓存获取"""
        for i, (name, cache) in enumerate(self._caches):
            value = cache.get(key)
            if value is not None:
                # 回填上级缓存
                for j in range(i):
                    upper_name, upper_cache = self._caches[j]
                    upper_cache.put(key, value, ttl=self._ttls.get(upper_name))
                return value
        return None

    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """写入所有缓存层"""
        for name, cache in self._caches:
            effective_ttl = ttl if ttl is not None else self._ttls.get(name)
            cache.put(key, value, ttl=effective_ttl)

    def invalidate(self, key: str) -> None:
        """使所有层的缓存失效"""
        for _, cache in self._caches:
            cache.invalidate(key)

    def clear(self) -> None:
        """清空所有缓存"""
        for _, cache in self._caches:
            cache.clear()

    def stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有缓存层统计"""
        return {name: cache.stats() for name, cache in self._caches}


def cached(cache: CacheLayer, key_fn: Optional[Callable] = None, ttl: Optional[float] = None):
    """
    缓存装饰器

    自动缓存函数结果。
    key_fn: 自定义缓存键生成函数
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if key_fn:
                key = key_fn(*args, **kwargs)
            else:
                key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            value = cache.get(key)
            if value is not None:
                return value
            value = func(*args, **kwargs)
            if value is not None:
                cache.put(key, value, ttl=ttl)
            return value
        return wrapper
    return decorator


# ============================================================
# 并发执行器
# ============================================================

@dataclass
class TaskResult(Generic[T]):
    """并发任务结果"""
    task_id: str
    result: Optional[T] = None
    error: Optional[Exception] = None
    duration: float = 0.0


class ConcurrentExecutor:
    """
    并发执行器

    基于线程池的并发任务执行。
    支持任务提交、批量执行、结果收集。
    """

    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: Dict[str, Future] = {}
        self._lock = threading.RLock()
        self._metrics = PerformanceMetrics()

    def submit(self, task_id: str, func: Callable, *args, **kwargs) -> str:
        """提交任务"""
        with self._lock:
            future = self._executor.submit(func, *args, **kwargs)
            self._futures[task_id] = future
            self._metrics.increment("tasks_submitted")
            return task_id

    def submit_batch(self, tasks: List[Tuple[str, Callable, tuple, dict]]) -> List[str]:
        """批量提交任务"""
        task_ids = []
        for task_id, func, args, kwargs in tasks:
            tid = self.submit(task_id, func, *args, **kwargs)
            task_ids.append(tid)
        return task_ids

    def get_result(self, task_id: str, timeout: Optional[float] = None) -> TaskResult:
        """获取任务结果"""
        with self._lock:
            future = self._futures.get(task_id)
        if future is None:
            return TaskResult(task_id=task_id, error=ValueError(f"Task {task_id} not found"))

        start = time.perf_counter()
        try:
            result = future.result(timeout=timeout)
            duration = time.perf_counter() - start
            self._metrics.increment("tasks_completed")
            return TaskResult(task_id=task_id, result=result, duration=duration)
        except Exception as e:
            duration = time.perf_counter() - start
            self._metrics.increment("tasks_failed")
            return TaskResult(task_id=task_id, error=e, duration=duration)

    def wait_all(self, timeout: Optional[float] = None) -> Dict[str, TaskResult]:
        """等待所有任务完成"""
        results = {}
        with self._lock:
            futures = dict(self._futures)
        for task_id, future in futures.items():
            start = time.perf_counter()
            try:
                result = future.result(timeout=timeout)
                duration = time.perf_counter() - start
                results[task_id] = TaskResult(
                    task_id=task_id, result=result, duration=duration
                )
                self._metrics.increment("tasks_completed")
            except Exception as e:
                duration = time.perf_counter() - start
                results[task_id] = TaskResult(
                    task_id=task_id, error=e, duration=duration
                )
                self._metrics.increment("tasks_failed")
        return results

    def map(self, func: Callable, iterable: Iterator, timeout: Optional[float] = None) -> List[Any]:
        """映射并发执行"""
        return list(self._executor.map(func, iterable, timeout=timeout))

    def shutdown(self, wait: bool = True) -> None:
        """关闭执行器"""
        self._executor.shutdown(wait=wait)

    def metrics(self) -> Dict[str, Any]:
        """获取执行器指标"""
        return self._metrics.get_all_counters()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False


def run_concurrent(
    func: Callable,
    items: List[Any],
    max_workers: int = 4,
    timeout: Optional[float] = None,
) -> List[TaskResult]:
    """并发执行函数（便捷函数）"""
    with ConcurrentExecutor(max_workers=max_workers) as executor:
        tasks = [
            (f"task_{i}", func, (item,), {})
            for i, item in enumerate(items)
        ]
        executor.submit_batch(tasks)
        results = executor.wait_all(timeout=timeout)
        return [results[f"task_{i}"] for i in range(len(items))]


# ============================================================
# 懒加载器
# ============================================================

class LazyLoader(Generic[T]):
    """
    懒加载器

    延迟初始化到首次访问。
    线程安全。
    """

    def __init__(self, factory: Callable[[], T]):
        self._factory = factory
        self._value: Optional[T] = None
        self._lock = threading.Lock()
        self._initialized = False

    def get(self) -> T:
        """获取值（首次访问时初始化）"""
        if self._initialized:
            return self._value  # type: ignore
        with self._lock:
            if not self._initialized:
                self._value = self._factory()
                self._initialized = True
        return self._value  # type: ignore

    @property
    def is_initialized(self) -> bool:
        """是否已初始化"""
        return self._initialized

    def reset(self) -> None:
        """重置（下次访问重新初始化）"""
        with self._lock:
            self._value = None
            self._initialized = False


def lazy(factory: Callable[[], T]) -> LazyLoader[T]:
    """创建懒加载器"""
    return LazyLoader(factory)


# ============================================================
# 批处理器
# ============================================================

class BatchProcessor(Generic[T, R]):
    """
    批处理器

    收集多个请求，达到阈值后批量处理。
    线程安全。
    """

    def __init__(
        self,
        processor: Callable[[List[T]], List[R]],
        batch_size: int = 100,
    ):
        self._processor = processor
        self._batch_size = batch_size
        self._buffer: List[T] = []
        self._lock = threading.Lock()
        self._metrics = PerformanceMetrics()

    def add(self, item: T) -> Optional[List[R]]:
        """添加项，达到批量大小时触发处理"""
        with self._lock:
            self._buffer.append(item)
            if len(self._buffer) >= self._batch_size:
                batch = self._buffer
                self._buffer = []
            else:
                return None
        # 在锁外处理
        return self._process(batch)

    def add_many(self, items: List[T]) -> List[List[R]]:
        """添加多项，返回所有触发的批处理结果"""
        results = []
        with self._lock:
            for item in items:
                self._buffer.append(item)
                if len(self._buffer) >= self._batch_size:
                    batch = self._buffer
                    self._buffer = []
                    # 在锁外处理
                    result = self._process(batch)
                    if result:
                        results.append(result)
        return results

    def flush(self) -> Optional[List[R]]:
        """刷新缓冲区，处理剩余项"""
        with self._lock:
            if not self._buffer:
                return None
            batch = self._buffer
            self._buffer = []
        return self._process(batch)

    def _process(self, batch: List[T]) -> List[R]:
        """处理批次"""
        with self._metrics.timer("batch_process"):
            try:
                result = self._processor(batch)
                self._metrics.increment("batches_processed")
                self._metrics.increment("items_processed", len(batch))
                return result
            except Exception:
                self._metrics.increment("batches_failed")
                raise

    def pending_count(self) -> int:
        """待处理项数"""
        with self._lock:
            return len(self._buffer)

    def metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self._metrics.snapshot()


# ============================================================
# 对象池
# ============================================================

class ObjectPool(Generic[T]):
    """
    对象池

    复用对象，避免频繁创建/销毁。
    线程安全。
    """

    def __init__(self, factory: Callable[[], T], max_size: int = 10):
        self._factory = factory
        self._max_size = max_size
        self._pool: deque = deque()
        self._created = 0
        self._lock = threading.Lock()

    def acquire(self) -> T:
        """获取对象"""
        with self._lock:
            if self._pool:
                return self._pool.popleft()
            self._created += 1
        return self._factory()

    def release(self, obj: T) -> None:
        """释放对象回池"""
        with self._lock:
            if len(self._pool) < self._max_size:
                self._pool.append(obj)

    def size(self) -> int:
        """池中对象数"""
        with self._lock:
            return len(self._pool)

    def clear(self) -> None:
        """清空池"""
        with self._lock:
            self._pool.clear()


# ============================================================
# 性能分析器
# ============================================================

@dataclass
class ProfileEntry:
    """性能分析条目"""
    name: str
    calls: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0

    @property
    def avg_time(self) -> float:
        return self.total_time / self.calls if self.calls > 0 else 0.0


class Profiler:
    """
    性能分析器

    记录函数调用次数和耗时。
    """

    def __init__(self):
        self._entries: Dict[str, ProfileEntry] = {}
        self._lock = threading.RLock()

    def profile(self, name: Optional[str] = None):
        """性能分析装饰器"""
        def decorator(func):
            entry_name = name or func.__name__
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    duration = time.perf_counter() - start
                    self._record(entry_name, duration)
            return wrapper
        return decorator

    def _record(self, name: str, duration: float) -> None:
        """记录调用"""
        with self._lock:
            if name not in self._entries:
                self._entries[name] = ProfileEntry(name=name)
            entry = self._entries[name]
            entry.calls += 1
            entry.total_time += duration
            entry.min_time = min(entry.min_time, duration)
            entry.max_time = max(entry.max_time, duration)

    def get_report(self) -> Dict[str, Dict[str, Any]]:
        """获取分析报告"""
        with self._lock:
            return {
                name: {
                    "calls": e.calls,
                    "total_time": e.total_time,
                    "avg_time": e.avg_time,
                    "min_time": e.min_time if e.calls > 0 else 0,
                    "max_time": e.max_time,
                }
                for name, e in self._entries.items()
            }

    def reset(self) -> None:
        """重置分析器"""
        with self._lock:
            self._entries.clear()

    def top_n(self, n: int = 10, by: str = "total_time") -> List[Tuple[str, Dict[str, Any]]]:
        """获取Top N"""
        report = self.get_report()
        sorted_items = sorted(report.items(), key=lambda x: x[1].get(by, 0), reverse=True)
        return sorted_items[:n]


# ============================================================
# 性能监控器
# ============================================================

class PerformanceMonitor:
    """
    性能监控器

    集成所有性能优化组件，提供统一接口。
    """

    def __init__(
        self,
        cache_max_size: int = 1000,
        executor_workers: int = 4,
        batch_size: int = 100,
    ):
        self._metrics = PerformanceMetrics()
        self._cache = CacheLayer()
        self._executor = ConcurrentExecutor(max_workers=executor_workers)
        self._profiler = Profiler()
        self._batch_processors: Dict[str, BatchProcessor] = {}
        self._pools: Dict[str, ObjectPool] = {}
        self._lazy_loaders: Dict[str, LazyLoader] = {}
        self._lock = threading.RLock()

    @property
    def metrics(self) -> PerformanceMetrics:
        return self._metrics

    @property
    def cache(self) -> CacheLayer:
        return self._cache

    @property
    def executor(self) -> ConcurrentExecutor:
        return self._executor

    @property
    def profiler(self) -> Profiler:
        return self._profiler

    def get_batch_processor(
        self,
        name: str,
        processor: Callable,
        batch_size: int = 100,
    ) -> BatchProcessor:
        """获取或创建批处理器"""
        with self._lock:
            if name not in self._batch_processors:
                self._batch_processors[name] = BatchProcessor(
                    processor=processor, batch_size=batch_size
                )
            return self._batch_processors[name]

    def get_pool(
        self,
        name: str,
        factory: Callable,
        max_size: int = 10,
    ) -> ObjectPool:
        """获取或创建对象池"""
        with self._lock:
            if name not in self._pools:
                self._pools[name] = ObjectPool(factory=factory, max_size=max_size)
            return self._pools[name]

    def get_lazy(self, name: str, factory: Callable) -> LazyLoader:
        """获取或创建懒加载器"""
        with self._lock:
            if name not in self._lazy_loaders:
                self._lazy_loaders[name] = LazyLoader(factory)
            return self._lazy_loaders[name]

    def cached(self, key_fn: Optional[Callable] = None, ttl: Optional[float] = None):
        """缓存装饰器"""
        return cached(self._cache, key_fn=key_fn, ttl=ttl)

    def profiled(self, name: Optional[str] = None):
        """性能分析装饰器"""
        return self._profiler.profile(name=name)

    def report(self) -> Dict[str, Any]:
        """获取完整性能报告"""
        return {
            "metrics": self._metrics.snapshot(),
            "cache": self._cache.stats(),
            "executor": self._executor.metrics(),
            "profiler": self._profiler.get_report(),
            "batch_processors": {
                name: bp.metrics()
                for name, bp in self._batch_processors.items()
            },
            "pools": {
                name: {"size": pool.size(), "max_size": pool._max_size}
                for name, pool in self._pools.items()
            },
            "lazy_loaders": {
                name: {"initialized": loader.is_initialized}
                for name, loader in self._lazy_loaders.items()
            },
        }

    def reset(self) -> None:
        """重置所有性能组件"""
        self._metrics.reset()
        self._cache.clear()
        self._profiler.reset()


# ============================================================
# 便捷函数
# ============================================================

def create_performance_monitor(
    cache_max_size: int = 1000,
    executor_workers: int = 4,
    batch_size: int = 100,
) -> PerformanceMonitor:
    """创建性能监控器"""
    return PerformanceMonitor(
        cache_max_size=cache_max_size,
        executor_workers=executor_workers,
        batch_size=batch_size,
    )


def timed(metrics: Optional[PerformanceMetrics] = None, name: Optional[str] = None):
    """
    计时装饰器

    自动记录函数执行时间。
    """
    _metrics = metrics or PerformanceMetrics()

    def decorator(func):
        timer_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with _metrics.timer(timer_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator
