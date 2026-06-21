"""性能基准测试Mixin — 阶段149从agent.py拆分"""

from typing import Any, Callable, Dict, List

from ..core.benchmark import (
    Benchmark, BenchmarkSuite, BenchmarkResult, quick_benchmark,
)


class BenchmarkMixin:
    """性能基准测试接口（阶段141）"""

    def run_benchmark(self, benchmark: Benchmark) -> BenchmarkResult:
        """运行单个基准测试（阶段141新增）"""
        return self._benchmark.run_benchmark(benchmark)

    def run_quick_benchmark(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 10,
    ) -> BenchmarkResult:
        """快速基准测试（阶段141新增）"""
        return quick_benchmark(name, func, iterations, warmup)

    def add_benchmark_suite(self, suite: BenchmarkSuite) -> None:
        """添加基准测试套件（阶段141新增）"""
        self._benchmark.add_suite(suite)

    def run_benchmark_suite(self, suite_name: str) -> List[BenchmarkResult]:
        """运行指定基准测试套件（阶段141新增）"""
        return self._benchmark.run_suite(suite_name)

    def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """运行所有基准测试套件（阶段141新增）"""
        return self._benchmark.run_all()

    def get_benchmark_results(self) -> List[BenchmarkResult]:
        """获取所有基准测试结果（阶段141新增）"""
        return self._benchmark.get_results()

    def clear_benchmark_results(self) -> None:
        """清空基准测试结果（阶段141新增）"""
        self._benchmark.clear_results()

    def get_benchmark_summary(self) -> Dict[str, Any]:
        """获取基准测试摘要（阶段141新增）"""
        return self._benchmark.get_summary()

    def set_performance_baseline(
        self,
        name: str,
        max_avg_time: float,
        min_ops_per_second: float,
    ) -> None:
        """设置性能基线（阶段141新增）"""
        self._benchmark.baseline.set_baseline(name, max_avg_time, min_ops_per_second)

    def get_performance_baseline(self) -> Dict[str, Any]:
        """获取性能基线（阶段141新增）"""
        return self._benchmark.baseline.to_dict()

    def list_benchmark_suites(self) -> List[str]:
        """列出所有基准测试套件（阶段141新增）"""
        return self._benchmark.list_suites()
