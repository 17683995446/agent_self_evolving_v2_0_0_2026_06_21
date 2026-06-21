"""性能优化Mixin — 阶段149从agent.py拆分"""

from typing import Any, Callable, Dict, List, Optional

from ..core.performance import run_concurrent


class PerformanceMixin:
    """性能优化接口（阶段130）"""

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告（阶段130新增）"""
        return self._perf_monitor.report()

    def reset_performance(self) -> None:
        """重置性能指标（阶段130新增）"""
        self._perf_monitor.reset()

    def get_cache_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取缓存统计（阶段130新增）"""
        return self._perf_monitor.cache.stats()

    def cache_get(self, key: str) -> Optional[Any]:
        """从缓存获取（阶段130新增）"""
        return self._perf_monitor.cache.get(key)

    def cache_put(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """写入缓存（阶段130新增）"""
        self._perf_monitor.cache.put(key, value, ttl=ttl)

    def cache_invalidate(self, key: str) -> None:
        """使缓存失效（阶段130新增）"""
        self._perf_monitor.cache.invalidate(key)

    def run_concurrent_tasks(
        self,
        func: Callable,
        items: List[Any],
        max_workers: int = 4,
        timeout: Optional[float] = None,
    ) -> List[Any]:
        """并发执行任务（阶段130新增）"""
        results = run_concurrent(func, items, max_workers=max_workers, timeout=timeout)
        return [r.result for r in results]

    def get_profiler_report(self) -> Dict[str, Dict[str, Any]]:
        """获取性能分析报告（阶段130新增）"""
        return self._perf_monitor.profiler.get_report()
