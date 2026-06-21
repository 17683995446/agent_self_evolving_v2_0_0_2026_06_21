"""
阶段130: 性能优化层 — 专项测试

测试覆盖：
1. PerformanceMetrics: 计时、计数、直方图、统计
2. LRUCache: 基本操作、LRU淘汰、TTL过期、统计
3. CacheLayer: 多级缓存、回填、失效
4. cached装饰器: 自动缓存
5. ConcurrentExecutor: 提交、批量、结果、超时
6. LazyLoader: 懒加载、线程安全、重置
7. BatchProcessor: 批量处理、刷新
8. ObjectPool: 获取/释放、池化复用
9. Profiler: 性能分析、报告
10. PerformanceMonitor: 集成接口
11. Agent集成
12. 并发安全
13. 性能基准
14. 异常容错
15. 第一性原理验证
"""

import time
import threading
import pytest
from unittest.mock import MagicMock, patch

from self_evolving_agent.core.performance import (
    PerformanceMetrics,
    TimerRecord,
    TimerContext,
    CacheEntry,
    LRUCache,
    CacheLayer,
    cached,
    ConcurrentExecutor,
    TaskResult,
    run_concurrent,
    LazyLoader,
    lazy,
    BatchProcessor,
    ObjectPool,
    ProfileEntry,
    Profiler,
    PerformanceMonitor,
    create_performance_monitor,
    timed,
)


# ============================================================
# PerformanceMetrics 测试
# ============================================================

class TestPerformanceMetrics:
    """性能指标收集器测试"""

    def test_timer_basic(self):
        """测试基本计时"""
        metrics = PerformanceMetrics()
        with metrics.timer("operation"):
            time.sleep(0.01)
        stats = metrics.get_timer_stats("operation")
        assert stats["count"] == 1
        assert stats["total"] >= 0.01
        assert stats["avg"] >= 0.01

    def test_timer_multiple(self):
        """测试多次计时"""
        metrics = PerformanceMetrics()
        for _ in range(5):
            with metrics.timer("op"):
                time.sleep(0.001)
        stats = metrics.get_timer_stats("op")
        assert stats["count"] == 5
        assert stats["min"] <= stats["max"]
        assert stats["avg"] > 0

    def test_timer_with_metadata(self):
        """测试带元数据的计时"""
        metrics = PerformanceMetrics()
        with metrics.timer("op", user="test", action="compute"):
            pass
        stats = metrics.get_timer_stats("op")
        assert stats["count"] == 1

    def test_counter_increment(self):
        """测试计数器递增"""
        metrics = PerformanceMetrics()
        metrics.increment("requests")
        metrics.increment("requests")
        metrics.increment("requests", 5)
        assert metrics.get_counter("requests") == 7

    def test_counter_default_zero(self):
        """测试未定义计数器返回0"""
        metrics = PerformanceMetrics()
        assert metrics.get_counter("nonexistent") == 0

    def test_histogram_observe(self):
        """测试直方图观测"""
        metrics = PerformanceMetrics()
        for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
            metrics.observe("latency", v)
        stats = metrics.get_histogram_stats("latency")
        assert stats["count"] == 5
        assert stats["avg"] == 3.0
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0

    def test_histogram_percentiles(self):
        """测试直方图百分位数"""
        metrics = PerformanceMetrics()
        for i in range(100):
            metrics.observe("latency", float(i + 1))
        stats = metrics.get_histogram_stats("latency")
        assert stats["count"] == 100
        assert stats["p50"] >= 49
        assert stats["p90"] >= 89
        assert stats["p99"] >= 98

    def test_get_all_counters(self):
        """测试获取所有计数器"""
        metrics = PerformanceMetrics()
        metrics.increment("a")
        metrics.increment("b", 10)
        counters = metrics.get_all_counters()
        assert counters["a"] == 1
        assert counters["b"] == 10

    def test_reset(self):
        """测试重置"""
        metrics = PerformanceMetrics()
        with metrics.timer("op"):
            pass
        metrics.increment("count")
        metrics.observe("hist", 1.0)
        metrics.reset()
        assert metrics.get_timer_stats("op") == {}
        assert metrics.get_counter("count") == 0
        assert metrics.get_histogram_stats("hist") == {}

    def test_snapshot(self):
        """测试快照"""
        metrics = PerformanceMetrics()
        with metrics.timer("op"):
            pass
        metrics.increment("count")
        snap = metrics.snapshot()
        assert "timers" in snap
        assert "counters" in snap
        assert "histograms" in snap
        assert "timestamp" in snap

    def test_max_records_limit(self):
        """测试最大记录限制"""
        metrics = PerformanceMetrics(max_records=10)
        for _ in range(20):
            with metrics.timer("op"):
                pass
        stats = metrics.get_timer_stats("op")
        assert stats["count"] == 10  # 只保留最近10条

    def test_timer_stats_empty(self):
        """测试空计时统计"""
        metrics = PerformanceMetrics()
        assert metrics.get_timer_stats("nonexistent") == {}

    def test_histogram_stats_empty(self):
        """测试空直方图统计"""
        metrics = PerformanceMetrics()
        assert metrics.get_histogram_stats("nonexistent") == {}

    def test_histogram_size_limit(self):
        """测试直方图大小限制"""
        metrics = PerformanceMetrics()
        for i in range(1500):
            metrics.observe("latency", float(i))
        stats = metrics.get_histogram_stats("latency")
        assert stats["count"] <= 1000  # 限制后的大小


# ============================================================
# LRUCache 测试
# ============================================================

class TestLRUCache:
    """LRU缓存测试"""

    def test_put_and_get(self):
        """测试基本存取"""
        cache = LRUCache(max_size=10)
        cache.put("key", "value")
        assert cache.get("key") == "value"

    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        cache = LRUCache()
        assert cache.get("nonexistent") is None

    def test_lru_eviction(self):
        """测试LRU淘汰"""
        cache = LRUCache(max_size=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        # 访问a，使其成为最近使用
        cache.get("a")
        # 插入d，应淘汰b（最久未使用）
        cache.put("d", 4)
        assert cache.get("b") is None
        assert cache.get("a") == 1
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_lru_eviction_without_access(self):
        """测试无访问时的LRU淘汰"""
        cache = LRUCache(max_size=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # 应淘汰a
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_ttl_expiration(self):
        """测试TTL过期"""
        cache = LRUCache(max_size=10)
        cache.put("key", "value", ttl=0.05)
        assert cache.get("key") == "value"
        time.sleep(0.06)
        assert cache.get("key") is None

    def test_ttl_not_expired(self):
        """测试TTL未过期"""
        cache = LRUCache(max_size=10)
        cache.put("key", "value", ttl=1.0)
        assert cache.get("key") == "value"

    def test_invalidate(self):
        """测试失效"""
        cache = LRUCache(max_size=10)
        cache.put("key", "value")
        assert cache.invalidate("key") is True
        assert cache.get("key") is None
        assert cache.invalidate("nonexistent") is False

    def test_clear(self):
        """测试清空"""
        cache = LRUCache(max_size=10)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.clear()
        assert cache.size() == 0
        assert cache.get("a") is None

    def test_size(self):
        """测试大小"""
        cache = LRUCache(max_size=10)
        assert cache.size() == 0
        cache.put("a", 1)
        assert cache.size() == 1
        cache.put("b", 2)
        assert cache.size() == 2

    def test_stats(self):
        """测试统计"""
        cache = LRUCache(max_size=10)
        cache.put("a", 1)
        cache.get("a")  # hit
        cache.get("b")  # miss
        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["max_size"] == 10
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_update_existing_key(self):
        """测试更新已存在的键"""
        cache = LRUCache(max_size=10)
        cache.put("key", "old")
        cache.put("key", "new")
        assert cache.get("key") == "new"
        assert cache.size() == 1

    def test_access_count(self):
        """测试访问计数"""
        cache = LRUCache(max_size=10)
        cache.put("key", "value")
        cache.get("key")
        cache.get("key")
        cache.get("key")
        # 内部访问计数
        with cache._lock:
            entry = cache._cache.get("key")
            assert entry.access_count == 3


# ============================================================
# CacheLayer 测试
# ============================================================

class TestCacheLayer:
    """多级缓存测试"""

    def test_default_levels(self):
        """测试默认缓存层"""
        layer = CacheLayer()
        layer.put("key", "value")
        assert layer.get("key") == "value"

    def test_custom_levels(self):
        """测试自定义缓存层"""
        levels = [
            {"name": "L1", "max_size": 10, "ttl": 60},
            {"name": "L2", "max_size": 100, "ttl": 3600},
            {"name": "L3", "max_size": 1000, "ttl": None},
        ]
        layer = CacheLayer(levels=levels)
        layer.put("key", "value")
        assert layer.get("key") == "value"

    def test_backfill(self):
        """测试回填上级缓存"""
        layer = CacheLayer()
        layer.put("key", "value")
        # 清空L1，保留L2
        layer._caches[0][1].clear()
        # 从L2获取应回填L1
        result = layer.get("key")
        assert result == "value"
        assert layer._caches[0][1].get("key") == "value"

    def test_invalidate_all_levels(self):
        """测试所有层失效"""
        layer = CacheLayer()
        layer.put("key", "value")
        layer.invalidate("key")
        assert layer.get("key") is None

    def test_clear_all(self):
        """测试清空所有层"""
        layer = CacheLayer()
        layer.put("a", 1)
        layer.put("b", 2)
        layer.clear()
        assert layer.get("a") is None
        assert layer.get("b") is None

    def test_stats_all_levels(self):
        """测试所有层统计"""
        layer = CacheLayer()
        layer.put("key", "value")
        layer.get("key")
        stats = layer.stats()
        assert "L1" in stats
        assert "L2" in stats

    def test_miss_returns_none(self):
        """测试未命中返回None"""
        layer = CacheLayer()
        assert layer.get("nonexistent") is None


# ============================================================
# cached装饰器测试
# ============================================================

class TestCachedDecorator:
    """缓存装饰器测试"""

    def test_basic_caching(self):
        """测试基本缓存"""
        layer = CacheLayer()
        call_count = 0

        @cached(layer)
        def expensive_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert expensive_func(5) == 10
        assert expensive_func(5) == 10  # 应从缓存获取
        assert call_count == 1

    def test_different_args(self):
        """测试不同参数"""
        layer = CacheLayer()
        call_count = 0

        @cached(layer)
        def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert func(5) == 10
        assert func(6) == 12
        assert call_count == 2

    def test_custom_key_fn(self):
        """测试自定义键函数"""
        layer = CacheLayer()
        call_count = 0

        def key_fn(*args, **kwargs):
            return f"custom:{args[0]}"

        @cached(layer, key_fn=key_fn)
        def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert func(5) == 10
        assert func(5) == 10
        assert call_count == 1

    def test_none_result_not_cached(self):
        """测试None结果不缓存"""
        layer = CacheLayer()
        call_count = 0

        @cached(layer)
        def func(x):
            nonlocal call_count
            call_count += 1
            return None

        func(5)
        func(5)
        assert call_count == 2  # None不缓存，每次都调用

    def test_ttl_in_decorator(self):
        """测试装饰器TTL"""
        layer = CacheLayer()
        call_count = 0

        @cached(layer, ttl=0.05)
        def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert func(5) == 10
        assert func(5) == 10
        assert call_count == 1
        time.sleep(0.06)
        assert func(5) == 10
        assert call_count == 2


# ============================================================
# ConcurrentExecutor 测试
# ============================================================

class TestConcurrentExecutor:
    """并发执行器测试"""

    def test_submit_and_get_result(self):
        """测试提交和获取结果"""
        with ConcurrentExecutor(max_workers=2) as executor:
            executor.submit("task1", lambda x: x * 2, 5)
            result = executor.get_result("task1")
            assert result.result == 10
            assert result.error is None

    def test_submit_batch(self):
        """测试批量提交"""
        with ConcurrentExecutor(max_workers=4) as executor:
            tasks = [
                (f"task_{i}", lambda x: x * 2, (i,), {})
                for i in range(5)
            ]
            task_ids = executor.submit_batch(tasks)
            assert len(task_ids) == 5
            results = executor.wait_all()
            for i in range(5):
                assert results[f"task_{i}"].result == i * 2

    def test_wait_all(self):
        """测试等待所有"""
        with ConcurrentExecutor(max_workers=4) as executor:
            for i in range(5):
                executor.submit(f"task_{i}", lambda x: x ** 2, i)
            results = executor.wait_all()
            assert len(results) == 5
            for i in range(5):
                assert results[f"task_{i}"].result == i ** 2

    def test_error_handling(self):
        """测试错误处理"""
        def failing_func():
            raise ValueError("test error")

        with ConcurrentExecutor(max_workers=2) as executor:
            executor.submit("fail_task", failing_func)
            result = executor.get_result("fail_task")
            assert result.result is None
            assert isinstance(result.error, ValueError)

    def test_get_result_nonexistent(self):
        """测试获取不存在任务的结果"""
        with ConcurrentExecutor(max_workers=2) as executor:
            result = executor.get_result("nonexistent")
            assert result.error is not None
            assert isinstance(result.error, ValueError)

    def test_map(self):
        """测试映射"""
        with ConcurrentExecutor(max_workers=4) as executor:
            results = executor.map(lambda x: x * 2, [1, 2, 3, 4, 5])
            assert list(results) == [2, 4, 6, 8, 10]

    def test_metrics(self):
        """测试指标"""
        with ConcurrentExecutor(max_workers=2) as executor:
            executor.submit("task1", lambda: 42)
            executor.get_result("task1")
            metrics = executor.metrics()
            assert metrics.get("tasks_submitted", 0) >= 1
            assert metrics.get("tasks_completed", 0) >= 1

    def test_context_manager(self):
        """测试上下文管理器"""
        executor = ConcurrentExecutor(max_workers=2)
        with executor as e:
            assert e is executor
        # 关闭后不应崩溃

    def test_run_concurrent_helper(self):
        """测试run_concurrent便捷函数"""
        results = run_concurrent(
            lambda x: x * 2,
            [1, 2, 3, 4, 5],
            max_workers=3,
        )
        assert len(results) == 5
        values = [r.result for r in results]
        assert values == [2, 4, 6, 8, 10]


# ============================================================
# LazyLoader 测试
# ============================================================

class TestLazyLoader:
    """懒加载器测试"""

    def test_lazy_initialization(self):
        """测试懒初始化"""
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return "value"

        loader = LazyLoader(factory)
        assert not loader.is_initialized
        assert loader.get() == "value"
        assert loader.is_initialized
        assert call_count == 1

    def test_single_initialization(self):
        """测试只初始化一次"""
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return [1, 2, 3]

        loader = LazyLoader(factory)
        loader.get()
        loader.get()
        loader.get()
        assert call_count == 1

    def test_reset(self):
        """测试重置"""
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return "value"

        loader = LazyLoader(factory)
        loader.get()
        loader.reset()
        assert not loader.is_initialized
        loader.get()
        assert call_count == 2

    def test_lazy_helper(self):
        """测试lazy便捷函数"""
        loader = lazy(lambda: 42)
        assert loader.get() == 42

    def test_concurrent_initialization(self):
        """测试并发初始化（线程安全）"""
        call_count = 0
        lock = threading.Lock()

        def factory():
            nonlocal call_count
            with lock:
                call_count += 1
            time.sleep(0.01)
            return "value"

        loader = LazyLoader(factory)
        threads = [threading.Thread(target=loader.get) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert call_count == 1  # 只初始化一次


# ============================================================
# BatchProcessor 测试
# ============================================================

class TestBatchProcessor:
    """批处理器测试"""

    def test_batch_trigger(self):
        """测试批量触发"""
        def processor(items):
            return [x * 2 for x in items]

        bp = BatchProcessor(processor=processor, batch_size=3)
        assert bp.add(1) is None
        assert bp.add(2) is None
        result = bp.add(3)
        assert result == [2, 4, 6]

    def test_flush(self):
        """测试刷新"""
        def processor(items):
            return [x * 2 for x in items]

        bp = BatchProcessor(processor=processor, batch_size=10)
        bp.add(1)
        bp.add(2)
        result = bp.flush()
        assert result == [2, 4]

    def test_flush_empty(self):
        """测试空刷新"""
        def processor(items):
            return items

        bp = BatchProcessor(processor=processor, batch_size=10)
        assert bp.flush() is None

    def test_add_many(self):
        """测试批量添加"""
        def processor(items):
            return [x * 2 for x in items]

        bp = BatchProcessor(processor=processor, batch_size=3)
        results = bp.add_many([1, 2, 3, 4, 5, 6, 7])
        assert len(results) == 2  # 2个批次
        assert results[0] == [2, 4, 6]
        assert results[1] == [8, 10, 12]
        # 剩余1个未处理
        assert bp.pending_count() == 1

    def test_pending_count(self):
        """测试待处理计数"""
        def processor(items):
            return items

        bp = BatchProcessor(processor=processor, batch_size=5)
        bp.add(1)
        bp.add(2)
        assert bp.pending_count() == 2

    def test_metrics(self):
        """测试指标"""
        def processor(items):
            return [x * 2 for x in items]

        bp = BatchProcessor(processor=processor, batch_size=2)
        bp.add(1)
        bp.add(2)  # 触发批次
        metrics = bp.metrics()
        assert "counters" in metrics
        assert metrics["counters"].get("batches_processed", 0) >= 1

    def test_processor_error(self):
        """测试处理器错误"""
        def failing_processor(items):
            raise ValueError("batch error")

        bp = BatchProcessor(processor=failing_processor, batch_size=2)
        bp.add(1)
        with pytest.raises(ValueError):
            bp.add(2)


# ============================================================
# ObjectPool 测试
# ============================================================

class TestObjectPool:
    """对象池测试"""

    def test_acquire_and_release(self):
        """测试获取和释放"""
        create_count = 0

        def factory():
            nonlocal create_count
            create_count += 1
            return {"id": create_count}

        pool = ObjectPool(factory=factory, max_size=3)
        obj1 = pool.acquire()
        obj2 = pool.acquire()
        assert create_count == 2

        pool.release(obj1)
        pool.release(obj2)
        assert pool.size() == 2

        # 复用（FIFO：先释放的先获取）
        obj3 = pool.acquire()
        assert obj3 is obj1  # FIFO顺序
        assert create_count == 2  # 没有创建新对象

    def test_max_size(self):
        """测试最大大小"""
        def factory():
            return {}

        pool = ObjectPool(factory=factory, max_size=2)
        obj1 = pool.acquire()
        obj2 = pool.acquire()
        obj3 = pool.acquire()
        pool.release(obj1)
        pool.release(obj2)
        pool.release(obj3)  # 超过max_size，不应入池
        assert pool.size() == 2

    def test_clear(self):
        """测试清空"""
        def factory():
            return {}

        pool = ObjectPool(factory=factory, max_size=5)
        pool.acquire()
        pool.release({})
        pool.clear()
        assert pool.size() == 0

    def test_size(self):
        """测试大小"""
        def factory():
            return {}

        pool = ObjectPool(factory=factory, max_size=5)
        assert pool.size() == 0
        obj = pool.acquire()
        pool.release(obj)
        assert pool.size() == 1


# ============================================================
# Profiler 测试
# ============================================================

class TestProfiler:
    """性能分析器测试"""

    def test_profile_decorator(self):
        """测试分析装饰器"""
        profiler = Profiler()

        @profiler.profile("my_func")
        def my_func():
            return 42

        my_func()
        my_func()
        report = profiler.get_report()
        assert "my_func" in report
        assert report["my_func"]["calls"] == 2
        assert report["my_func"]["total_time"] > 0

    def test_profile_default_name(self):
        """测试默认名称"""
        profiler = Profiler()

        @profiler.profile()
        def my_func():
            return 42

        my_func()
        report = profiler.get_report()
        assert "my_func" in report

    def test_avg_time(self):
        """测试平均时间"""
        profiler = Profiler()

        @profiler.profile("op")
        def op():
            time.sleep(0.001)

        for _ in range(5):
            op()

        report = profiler.get_report()
        assert report["op"]["calls"] == 5
        assert report["op"]["avg_time"] > 0

    def test_min_max_time(self):
        """测试最小最大时间"""
        profiler = Profiler()

        @profiler.profile("op")
        def op(duration):
            time.sleep(duration)

        op(0.001)
        op(0.01)

        report = profiler.get_report()
        assert report["op"]["min_time"] <= report["op"]["max_time"]

    def test_reset(self):
        """测试重置"""
        profiler = Profiler()

        @profiler.profile("op")
        def op():
            pass

        op()
        profiler.reset()
        assert profiler.get_report() == {}

    def test_top_n(self):
        """测试Top N"""
        profiler = Profiler()

        @profiler.profile("fast")
        def fast():
            return 1

        @profiler.profile("slow")
        def slow():
            time.sleep(0.01)
            return 2

        for _ in range(10):
            fast()
        for _ in range(2):
            slow()

        top = profiler.top_n(n=2, by="total_time")
        assert len(top) == 2
        # slow的总时间应该更长
        assert top[0][0] == "slow"

    def test_top_n_by_calls(self):
        """测试按调用次数排序"""
        profiler = Profiler()

        @profiler.profile("a")
        def a():
            pass

        @profiler.profile("b")
        def b():
            pass

        for _ in range(5):
            a()
        for _ in range(2):
            b()

        top = profiler.top_n(n=2, by="calls")
        assert top[0][0] == "a"
        assert top[0][1]["calls"] == 5


# ============================================================
# PerformanceMonitor 测试
# ============================================================

class TestPerformanceMonitor:
    """性能监控器测试"""

    def test_creation(self):
        """测试创建"""
        monitor = create_performance_monitor()
        assert monitor.metrics is not None
        assert monitor.cache is not None
        assert monitor.executor is not None
        assert monitor.profiler is not None

    def test_custom_config(self):
        """测试自定义配置"""
        monitor = PerformanceMonitor(
            cache_max_size=500,
            executor_workers=2,
            batch_size=50,
        )
        assert monitor is not None

    def test_cached_decorator(self):
        """测试缓存装饰器"""
        monitor = create_performance_monitor()
        call_count = 0

        @monitor.cached()
        def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert func(5) == 10
        assert func(5) == 10
        assert call_count == 1

    def test_profiled_decorator(self):
        """测试分析装饰器"""
        monitor = create_performance_monitor()

        @monitor.profiled("test_op")
        def func():
            return 42

        func()
        report = monitor.profiler.get_report()
        assert "test_op" in report

    def test_get_batch_processor(self):
        """测试获取批处理器"""
        monitor = create_performance_monitor()
        bp = monitor.get_batch_processor(
            "test_bp",
            processor=lambda items: items,
            batch_size=5,
        )
        assert bp is not None
        # 再次获取应返回同一实例
        bp2 = monitor.get_batch_processor(
            "test_bp",
            processor=lambda items: items,
        )
        assert bp is bp2

    def test_get_pool(self):
        """测试获取对象池"""
        monitor = create_performance_monitor()
        pool = monitor.get_pool("test_pool", factory=lambda: {}, max_size=5)
        assert pool is not None
        pool2 = monitor.get_pool("test_pool", factory=lambda: {})
        assert pool is pool2

    def test_get_lazy(self):
        """测试获取懒加载器"""
        monitor = create_performance_monitor()
        loader = monitor.get_lazy("test_lazy", factory=lambda: 42)
        assert loader.get() == 42
        loader2 = monitor.get_lazy("test_lazy", factory=lambda: 42)
        assert loader is loader2

    def test_report(self):
        """测试报告"""
        monitor = create_performance_monitor()
        monitor.cache.put("key", "value")
        report = monitor.report()
        assert "metrics" in report
        assert "cache" in report
        assert "executor" in report
        assert "profiler" in report
        assert "batch_processors" in report
        assert "pools" in report
        assert "lazy_loaders" in report

    def test_reset(self):
        """测试重置"""
        monitor = create_performance_monitor()
        monitor.cache.put("key", "value")
        monitor.reset()
        assert monitor.cache.get("key") is None


# ============================================================
# timed装饰器测试
# ============================================================

class TestTimedDecorator:
    """计时装饰器测试"""

    def test_timed(self):
        """测试计时装饰器"""
        metrics = PerformanceMetrics()

        @timed(metrics=metrics, name="timed_op")
        def func():
            time.sleep(0.001)
            return 42

        result = func()
        assert result == 42
        stats = metrics.get_timer_stats("timed_op")
        assert stats["count"] == 1

    def test_timed_default_name(self):
        """测试默认名称"""
        metrics = PerformanceMetrics()

        @timed(metrics=metrics)
        def my_func():
            return 42

        my_func()
        stats = metrics.get_timer_stats("my_func")
        assert stats["count"] == 1


# ============================================================
# Agent集成测试
# ============================================================

class TestAgentIntegration:
    """Agent集成测试"""

    def test_agent_has_performance_monitor(self):
        """测试Agent有性能监控器"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        assert agent.performance_monitor is not None

    def test_agent_cache_operations(self):
        """测试Agent缓存操作"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        agent.cache_put("test_key", "test_value")
        assert agent.cache_get("test_key") == "test_value"

    def test_agent_cache_invalidate(self):
        """测试Agent缓存失效"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        agent.cache_put("test_key", "test_value")
        agent.cache_invalidate("test_key")
        assert agent.cache_get("test_key") is None

    def test_agent_performance_report(self):
        """测试Agent性能报告"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        report = agent.get_performance_report()
        assert "cache" in report
        assert "metrics" in report

    def test_agent_cache_stats(self):
        """测试Agent缓存统计"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        stats = agent.get_cache_stats()
        assert "L1" in stats

    def test_agent_reset_performance(self):
        """测试Agent重置性能"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        agent.cache_put("key", "value")
        agent.reset_performance()
        assert agent.cache_get("key") is None

    def test_agent_run_concurrent(self):
        """测试Agent并发执行"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        results = agent.run_concurrent_tasks(
            lambda x: x * 2,
            [1, 2, 3, 4, 5],
            max_workers=3,
        )
        assert results == [2, 4, 6, 8, 10]

    def test_agent_profiler_report(self):
        """测试Agent分析报告"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        report = agent.get_profiler_report()
        assert isinstance(report, dict)


# ============================================================
# 并发安全测试
# ============================================================

class TestConcurrencySafety:
    """并发安全测试"""

    def test_lru_cache_concurrent(self):
        """测试LRU缓存并发安全"""
        cache = LRUCache(max_size=100)
        errors = []

        def worker():
            try:
                for i in range(100):
                    cache.put(f"key_{i}", i)
                    cache.get(f"key_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_metrics_concurrent(self):
        """测试指标并发安全"""
        metrics = PerformanceMetrics()
        errors = []

        def worker():
            try:
                for i in range(100):
                    with metrics.timer("op"):
                        pass
                    metrics.increment("counter")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert metrics.get_counter("counter") == 1000

    def test_batch_processor_concurrent(self):
        """测试批处理器并发安全"""
        processed = []
        lock = threading.Lock()

        def processor(items):
            with lock:
                processed.extend(items)
            return items

        bp = BatchProcessor(processor=processor, batch_size=10)
        errors = []

        def worker():
            try:
                for i in range(50):
                    bp.add(i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        bp.flush()
        assert len(errors) == 0
        assert len(processed) == 250

    def test_object_pool_concurrent(self):
        """测试对象池并发安全"""
        create_count = 0
        lock = threading.Lock()

        def factory():
            nonlocal create_count
            with lock:
                create_count += 1
            return {}

        pool = ObjectPool(factory=factory, max_size=5)
        errors = []

        def worker():
            try:
                for _ in range(20):
                    obj = pool.acquire()
                    time.sleep(0.001)
                    pool.release(obj)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ============================================================
# 性能基准测试
# ============================================================

class TestPerformanceBenchmarks:
    """性能基准测试"""

    def test_cache_hit_is_faster(self):
        """测试缓存命中更快"""
        cache = LRUCache(max_size=1000)

        def expensive_compute(x):
            time.sleep(0.001)
            return x * 2

        # 首次计算（未命中）
        start = time.perf_counter()
        result1 = expensive_compute(5)
        cache.put("key", result1)
        miss_time = time.perf_counter() - start

        # 缓存命中
        start = time.perf_counter()
        result2 = cache.get("key")
        hit_time = time.perf_counter() - start

        assert result1 == result2
        assert hit_time < miss_time

    def test_concurrent_faster_than_sequential(self):
        """测试并发比串行快"""
        def slow_task(x):
            time.sleep(0.05)
            return x * 2

        # 串行
        start = time.perf_counter()
        sequential_results = [slow_task(i) for i in range(5)]
        sequential_time = time.perf_counter() - start

        # 并发
        start = time.perf_counter()
        concurrent_results = run_concurrent(slow_task, list(range(5)), max_workers=5)
        concurrent_time = time.perf_counter() - start

        assert [r.result for r in concurrent_results] == sequential_results
        # 并发应明显快于串行（至少快2倍）
        assert concurrent_time < sequential_time * 0.7

    def test_batch_processor_efficiency(self):
        """测试批处理器效率"""
        call_count = 0

        def batch_processor(items):
            nonlocal call_count
            call_count += 1
            return [x * 2 for x in items]

        bp = BatchProcessor(processor=batch_processor, batch_size=100)
        for i in range(1000):
            bp.add(i)
        bp.flush()

        # 1000项，批量100，应调用10次处理器
        assert call_count == 10

    def test_lazy_loader_saves_initialization(self):
        """测试懒加载节省初始化"""
        init_count = 0

        def factory():
            nonlocal init_count
            init_count += 1
            time.sleep(0.01)
            return "value"

        loader = LazyLoader(factory)
        # 未访问，不应初始化
        assert init_count == 0
        # 首次访问才初始化
        loader.get()
        assert init_count == 1


# ============================================================
# 异常容错测试
# ============================================================

class TestErrorHandling:
    """异常容错测试"""

    def test_cache_none_value(self):
        """测试缓存None值"""
        cache = LRUCache(max_size=10)
        cache.put("key", None)
        # None被视为未命中
        assert cache.get("key") is None

    def test_executor_task_exception(self):
        """测试执行器任务异常"""
        def failing():
            raise RuntimeError("task failed")

        with ConcurrentExecutor(max_workers=2) as executor:
            executor.submit("fail", failing)
            result = executor.get_result("fail")
            assert result.error is not None
            assert isinstance(result.error, RuntimeError)

    def test_batch_processor_exception_propagation(self):
        """测试批处理器异常传播"""
        def failing_processor(items):
            if len(items) >= 2:
                raise ValueError("too many items")
            return items

        bp = BatchProcessor(processor=failing_processor, batch_size=2)
        bp.add(1)
        with pytest.raises(ValueError):
            bp.add(2)

    def test_lazy_loader_factory_exception(self):
        """测试懒加载工厂异常"""
        def failing_factory():
            raise RuntimeError("init failed")

        loader = LazyLoader(failing_factory)
        with pytest.raises(RuntimeError):
            loader.get()

    def test_object_pool_factory_exception(self):
        """测试对象池工厂异常"""
        def failing_factory():
            raise RuntimeError("create failed")

        pool = ObjectPool(factory=failing_factory, max_size=5)
        with pytest.raises(RuntimeError):
            pool.acquire()


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_measurement_first_principle(self):
        """第一性原理：测量先行"""
        # 不可测量的无法优化 → 提供完整测量能力
        metrics = PerformanceMetrics()
        with metrics.timer("operation"):
            pass
        metrics.increment("counter")
        metrics.observe("histogram", 1.0)

        # 所有指标都可获取
        assert metrics.get_timer_stats("operation")["count"] == 1
        assert metrics.get_counter("counter") == 1
        assert metrics.get_histogram_stats("histogram")["count"] == 1

    def test_cache_reuse_principle(self):
        """第一性原理：缓存复用"""
        # 重复计算的结果应被缓存
        cache = LRUCache(max_size=10)
        call_count = 0

        def compute(x):
            nonlocal call_count
            call_count += 1
            return x ** 2

        # 首次计算
        result1 = compute(5)
        cache.put("5", result1)
        # 从缓存获取
        result2 = cache.get("5")
        assert result1 == result2
        assert call_count == 1  # 只计算一次

    def test_concurrency_principle(self):
        """第一性原理：并发并行"""
        # 独立任务应并行执行
        def independent_task(x):
            time.sleep(0.01)
            return x * 2

        # 并发执行独立任务
        results = run_concurrent(independent_task, [1, 2, 3, 4], max_workers=4)
        assert len(results) == 4
        assert all(r.error is None for r in results)

    def test_lazy_loading_principle(self):
        """第一性原理：懒加载"""
        # 不需要的资源不应提前初始化
        initialized = False

        def factory():
            nonlocal initialized
            initialized = True
            return "value"

        loader = LazyLoader(factory)
        # 创建加载器但不访问
        assert not initialized
        # 首次访问才初始化
        loader.get()
        assert initialized

    def test_batching_principle(self):
        """第一性原理：批处理"""
        # 多个小操作应合并为大操作
        call_count = 0

        def processor(items):
            nonlocal call_count
            call_count += 1
            return [x * 2 for x in items]

        bp = BatchProcessor(processor=processor, batch_size=10)
        # 添加10个项，应只调用1次处理器
        for i in range(10):
            bp.add(i)

        assert call_count == 1  # 批量处理，只调用1次

    def test_pooling_principle(self):
        """第一性原理：资源池化"""
        # 重复创建/销毁的资源应池化
        create_count = 0

        def factory():
            nonlocal create_count
            create_count += 1
            return {}

        pool = ObjectPool(factory=factory, max_size=5)
        # 获取并释放5次
        for _ in range(5):
            obj = pool.acquire()
            pool.release(obj)

        # 只创建1个对象（复用）
        assert create_count == 1
