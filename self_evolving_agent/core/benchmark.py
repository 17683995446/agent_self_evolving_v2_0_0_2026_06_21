"""
阶段141: 性能基准套件 — 基准测试

第一性原理:
1. 可测量性 — 性能必须可量化测量，而非凭感觉
2. 可重复性 — 基准测试结果应可重复
3. 可比较性 — 不同版本/配置的性能应可比较
4. 渐进改进 — 性能改进应基于数据，而非猜测
5. 回归检测 — 性能回归应被自动检测

组件:
- BenchmarkResult — 基准测试结果
- Benchmark — 基准测试基类
- FunctionBenchmark — 函数基准测试
- SuiteBenchmark — 套件基准测试
- BenchmarkSuite — 基准测试套件
- BenchmarkRunner — 基准测试运行器
- PerformanceBaseline — 性能基线
- BenchmarkReporter — 报告生成器
"""

import os
import sys
import time
import json
import statistics
import threading
import traceback
from typing import Any, Dict, List, Optional, Callable, Tuple, Type
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from collections import defaultdict


# ============================================================
# 基准测试结果
# ============================================================

class BenchmarkStatus(Enum):
    """基准测试状态"""
    PASSED = "passed"     # 通过（在基线范围内）
    FAILED = "failed"     # 失败（超出基线范围）
    ERROR = "error"       # 错误（执行异常）
    SKIPPED = "skipped"   # 跳过


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    status: BenchmarkStatus
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    median_time: float
    stdev_time: float
    ops_per_second: float
    timestamp: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    samples: List[float] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == BenchmarkStatus.PASSED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "iterations": self.iterations,
            "total_time": round(self.total_time, 6),
            "avg_time": round(self.avg_time, 6),
            "min_time": round(self.min_time, 6),
            "max_time": round(self.max_time, 6),
            "median_time": round(self.median_time, 6),
            "stdev_time": round(self.stdev_time, 6),
            "ops_per_second": round(self.ops_per_second, 2),
            "timestamp": self.timestamp,
            "error": self.error,
            "metadata": self.metadata,
        }


# ============================================================
# 基准测试基类
# ============================================================

class Benchmark(ABC):
    """
    基准测试基类

    所有基准测试都应继承此类。
    """

    def __init__(self, name: str, iterations: int = 100, warmup: int = 10):
        self._name = name
        self._iterations = iterations
        self._warmup = warmup
        self._setup_done = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def iterations(self) -> int:
        return self._iterations

    @abstractmethod
    def setup(self) -> None:
        """设置（在每个测试前调用）"""
        ...

    @abstractmethod
    def run(self) -> None:
        """运行一次测试"""
        ...

    def teardown(self) -> None:
        """清理（在每个测试后调用）"""
        pass

    def execute(self) -> BenchmarkResult:
        """执行基准测试"""
        timestamp = time.time()

        # 设置
        try:
            if not self._setup_done:
                self.setup()
                self._setup_done = True
        except Exception as e:
            return BenchmarkResult(
                name=self._name,
                status=BenchmarkStatus.ERROR,
                iterations=0,
                total_time=0,
                avg_time=0,
                min_time=0,
                max_time=0,
                median_time=0,
                stdev_time=0,
                ops_per_second=0,
                timestamp=timestamp,
                error=f"Setup failed: {e}",
            )

        # 预热
        for _ in range(self._warmup):
            try:
                self.run()
            except Exception:
                pass

        # 正式测试
        samples: List[float] = []
        error = None

        for _ in range(self._iterations):
            start = time.perf_counter()
            try:
                self.run()
            except Exception as e:
                error = f"{type(e).__name__}: {e}"
                break
            elapsed = time.perf_counter() - start
            samples.append(elapsed)

        # 清理
        try:
            self.teardown()
        except Exception:
            pass

        if error:
            return BenchmarkResult(
                name=self._name,
                status=BenchmarkStatus.ERROR,
                iterations=len(samples),
                total_time=sum(samples) if samples else 0,
                avg_time=statistics.mean(samples) if samples else 0,
                min_time=min(samples) if samples else 0,
                max_time=max(samples) if samples else 0,
                median_time=statistics.median(samples) if samples else 0,
                stdev_time=statistics.stdev(samples) if len(samples) > 1 else 0,
                ops_per_second=0,
                timestamp=timestamp,
                error=error,
                samples=samples,
            )

        # 计算统计
        total_time = sum(samples)
        avg_time = statistics.mean(samples)
        min_time = min(samples)
        max_time = max(samples)
        median_time = statistics.median(samples)
        stdev_time = statistics.stdev(samples) if len(samples) > 1 else 0
        ops_per_second = len(samples) / total_time if total_time > 0 else 0

        return BenchmarkResult(
            name=self._name,
            status=BenchmarkStatus.PASSED,
            iterations=len(samples),
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            median_time=median_time,
            stdev_time=stdev_time,
            ops_per_second=ops_per_second,
            timestamp=timestamp,
            samples=samples,
        )


# ============================================================
# 函数基准测试
# ============================================================

class FunctionBenchmark(Benchmark):
    """函数基准测试 — 包装普通函数"""

    def __init__(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 10,
        setup_func: Optional[Callable] = None,
        teardown_func: Optional[Callable] = None,
    ):
        super().__init__(name, iterations, warmup)
        self._func = func
        self._setup_func = setup_func
        self._teardown_func = teardown_func

    def setup(self) -> None:
        if self._setup_func:
            self._setup_func()

    def run(self) -> None:
        self._func()

    def teardown(self) -> None:
        if self._teardown_func:
            self._teardown_func()


# ============================================================
# 性能基线
# ============================================================

@dataclass
class BaselineEntry:
    """基线条目"""
    name: str
    max_avg_time: float  # 最大平均时间（秒）
    min_ops_per_second: float  # 最小每秒操作数
    max_stdev_time: Optional[float] = None  # 最大标准差（可选）

    def check(self, result: BenchmarkResult) -> Tuple[bool, Optional[str]]:
        """检查结果是否符合基线"""
        if result.avg_time > self.max_avg_time:
            return False, f"Avg time {result.avg_time:.6f}s exceeds max {self.max_avg_time:.6f}s"
        if result.ops_per_second < self.min_ops_per_second:
            return False, f"Ops/sec {result.ops_per_second:.2f} below min {self.min_ops_per_second:.2f}"
        if self.max_stdev_time and result.stdev_time > self.max_stdev_time:
            return False, f"Stdev {result.stdev_time:.6f}s exceeds max {self.max_stdev_time:.6f}s"
        return True, None


class PerformanceBaseline:
    """
    性能基线

    存储各基准测试的性能基线，用于回归检测。
    """

    def __init__(self):
        self._entries: Dict[str, BaselineEntry] = {}
        self._lock = threading.RLock()

    def set_baseline(
        self,
        name: str,
        max_avg_time: float,
        min_ops_per_second: float,
        max_stdev_time: Optional[float] = None,
    ) -> None:
        """设置基线"""
        with self._lock:
            self._entries[name] = BaselineEntry(
                name=name,
                max_avg_time=max_avg_time,
                min_ops_per_second=min_ops_per_second,
                max_stdev_time=max_stdev_time,
            )

    def get_baseline(self, name: str) -> Optional[BaselineEntry]:
        """获取基线"""
        with self._lock:
            return self._entries.get(name)

    def remove_baseline(self, name: str) -> None:
        """移除基线"""
        with self._lock:
            self._entries.pop(name, None)

    def check(self, result: BenchmarkResult) -> Tuple[bool, Optional[str]]:
        """检查结果是否符合基线"""
        with self._lock:
            entry = self._entries.get(result.name)

        if entry is None:
            return True, None  # 无基线，默认通过

        return entry.check(result)

    def list_baselines(self) -> List[str]:
        """列出所有基线名称"""
        with self._lock:
            return list(self._entries.keys())

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                name: {
                    "max_avg_time": e.max_avg_time,
                    "min_ops_per_second": e.min_ops_per_second,
                    "max_stdev_time": e.max_stdev_time,
                }
                for name, e in self._entries.items()
            }

    def save(self, file_path: str) -> None:
        """保存基线到文件"""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def load(self, file_path: str) -> None:
        """从文件加载基线"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for name, entry in data.items():
            self.set_baseline(
                name,
                max_avg_time=entry["max_avg_time"],
                min_ops_per_second=entry["min_ops_per_second"],
                max_stdev_time=entry.get("max_stdev_time"),
            )


# ============================================================
# 基准测试套件
# ============================================================

class BenchmarkSuite:
    """
    基准测试套件

    管理一组相关的基准测试。
    """

    def __init__(self, name: str, description: str = ""):
        self._name = name
        self._description = description
        self._benchmarks: List[Benchmark] = []
        self._lock = threading.RLock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def add(self, benchmark: Benchmark) -> None:
        """添加基准测试"""
        with self._lock:
            self._benchmarks.append(benchmark)

    def remove(self, name: str) -> None:
        """移除基准测试"""
        with self._lock:
            self._benchmarks = [b for b in self._benchmarks if b.name != name]

    def get(self, name: str) -> Optional[Benchmark]:
        """获取基准测试"""
        with self._lock:
            for b in self._benchmarks:
                if b.name == name:
                    return b
        return None

    def list_benchmarks(self) -> List[str]:
        """列出所有基准测试名称"""
        with self._lock:
            return [b.name for b in self._benchmarks]

    def count(self) -> int:
        """基准测试数量"""
        with self._lock:
            return len(self._benchmarks)

    def run_all(self) -> List[BenchmarkResult]:
        """运行所有基准测试"""
        with self._lock:
            benchmarks = list(self._benchmarks)

        results = []
        for benchmark in benchmarks:
            result = benchmark.execute()
            results.append(result)
        return results


# ============================================================
# 基准测试运行器
# ============================================================

class BenchmarkRunner:
    """
    基准测试运行器

    协调基准测试的执行，整合基线检查。
    """

    def __init__(self):
        self._suites: Dict[str, BenchmarkSuite] = {}
        self._baseline = PerformanceBaseline()
        self._results: List[BenchmarkResult] = []
        self._lock = threading.RLock()

    @property
    def baseline(self) -> PerformanceBaseline:
        return self._baseline

    def add_suite(self, suite: BenchmarkSuite) -> None:
        """添加套件"""
        with self._lock:
            self._suites[suite.name] = suite

    def get_suite(self, name: str) -> Optional[BenchmarkSuite]:
        """获取套件"""
        with self._lock:
            return self._suites.get(name)

    def list_suites(self) -> List[str]:
        """列出所有套件"""
        with self._lock:
            return list(self._suites.keys())

    def run_suite(self, suite_name: str) -> List[BenchmarkResult]:
        """运行指定套件"""
        with self._lock:
            suite = self._suites.get(suite_name)

        if suite is None:
            return []

        results = suite.run_all()

        # 检查基线
        checked_results = []
        for result in results:
            if result.status == BenchmarkStatus.PASSED:
                passed, error = self._baseline.check(result)
                if not passed:
                    result = BenchmarkResult(
                        name=result.name,
                        status=BenchmarkStatus.FAILED,
                        iterations=result.iterations,
                        total_time=result.total_time,
                        avg_time=result.avg_time,
                        min_time=result.min_time,
                        max_time=result.max_time,
                        median_time=result.median_time,
                        stdev_time=result.stdev_time,
                        ops_per_second=result.ops_per_second,
                        timestamp=result.timestamp,
                        error=error,
                        metadata=result.metadata,
                        samples=result.samples,
                    )
            checked_results.append(result)

        with self._lock:
            self._results.extend(checked_results)

        return checked_results

    def run_all(self) -> List[BenchmarkResult]:
        """运行所有套件"""
        all_results = []
        with self._lock:
            suite_names = list(self._suites.keys())

        for name in suite_names:
            results = self.run_suite(name)
            all_results.extend(results)

        return all_results

    def run_benchmark(self, benchmark: Benchmark) -> BenchmarkResult:
        """运行单个基准测试"""
        result = benchmark.execute()
        if result.status == BenchmarkStatus.PASSED:
            passed, error = self._baseline.check(result)
            if not passed:
                result = BenchmarkResult(
                    name=result.name,
                    status=BenchmarkStatus.FAILED,
                    iterations=result.iterations,
                    total_time=result.total_time,
                    avg_time=result.avg_time,
                    min_time=result.min_time,
                    max_time=result.max_time,
                    median_time=result.median_time,
                    stdev_time=result.stdev_time,
                    ops_per_second=result.ops_per_second,
                    timestamp=result.timestamp,
                    error=error,
                    metadata=result.metadata,
                    samples=result.samples,
                )
        with self._lock:
            self._results.append(result)
        return result

    def get_results(self) -> List[BenchmarkResult]:
        """获取所有结果"""
        with self._lock:
            return list(self._results)

    def clear_results(self) -> None:
        """清空结果"""
        with self._lock:
            self._results.clear()

    def get_summary(self) -> Dict[str, Any]:
        """获取摘要"""
        with self._lock:
            results = list(self._results)

        summary = {
            "total": len(results),
            "passed": sum(1 for r in results if r.status == BenchmarkStatus.PASSED),
            "failed": sum(1 for r in results if r.status == BenchmarkStatus.FAILED),
            "errors": sum(1 for r in results if r.status == BenchmarkStatus.ERROR),
            "skipped": sum(1 for r in results if r.status == BenchmarkStatus.SKIPPED),
            "suites": len(self._suites),
            "baselines": len(self._baseline.list_baselines()),
        }
        return summary


# ============================================================
# 报告生成器
# ============================================================

class BenchmarkReporter:
    """基准测试报告生成器"""

    @staticmethod
    def to_text(results: List[BenchmarkResult]) -> str:
        """生成文本报告"""
        lines = []
        lines.append("=" * 80)
        lines.append("基准测试报告")
        lines.append("=" * 80)
        lines.append("")

        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        lines.append(f"总计: {len(results)} | 通过: {passed} | 失败: {failed}")
        lines.append("")

        # 表头
        lines.append(f"{'名称':<40} {'状态':<8} {'平均时间':<15} {'ops/sec':<12} {'迭代':<8}")
        lines.append("-" * 80)

        for result in results:
            name = result.name[:38]
            status = "通过" if result.passed else "失败"
            avg = f"{result.avg_time * 1000:.3f}ms"
            ops = f"{result.ops_per_second:.1f}"
            iters = str(result.iterations)
            lines.append(f"{name:<40} {status:<8} {avg:<15} {ops:<12} {iters:<8}")

        lines.append("")
        lines.append("=" * 80)
        return "\n".join(lines)

    @staticmethod
    def to_json(results: List[BenchmarkResult]) -> str:
        """生成JSON报告"""
        data = {
            "results": [r.to_dict() for r in results],
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed),
            },
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def to_dict(results: List[BenchmarkResult]) -> Dict[str, Any]:
        """生成字典报告"""
        return {
            "results": [r.to_dict() for r in results],
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed),
            },
        }

    @staticmethod
    def save(results: List[BenchmarkResult], file_path: str, format: str = "json") -> None:
        """保存报告到文件"""
        if format == "json":
            content = BenchmarkReporter.to_json(results)
        else:
            content = BenchmarkReporter.to_text(results)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)


# ============================================================
# 预定义基准测试
# ============================================================

class AgentObserveBenchmark(Benchmark):
    """Agent感知操作基准测试"""

    def __init__(self, agent_factory: Callable, iterations: int = 50, warmup: int = 5):
        super().__init__("agent_observe", iterations, warmup)
        self._agent_factory = agent_factory
        self._agent = None

    def setup(self) -> None:
        self._agent = self._agent_factory()
        if hasattr(self._agent, "initialize"):
            self._agent.initialize({})

    def run(self) -> None:
        if self._agent and hasattr(self._agent, "observe"):
            try:
                self._agent.observe({})
            except Exception:
                pass

    def teardown(self) -> None:
        if self._agent and hasattr(self._agent, "stop"):
            try:
                self._agent.stop()
            except Exception:
                pass


class ConfigAccessBenchmark(Benchmark):
    """配置访问基准测试"""

    def __init__(self, config_manager_factory: Callable, iterations: int = 1000, warmup: int = 100):
        super().__init__("config_access", iterations, warmup)
        self._factory = config_manager_factory
        self._config = None

    def setup(self) -> None:
        self._config = self._factory()
        self._config.set("bench.key", "value")
        self._config.set("bench.nested.key", 42)

    def run(self) -> None:
        self._config.get("bench.key")
        self._config.get("bench.nested.key")
        self._config.get("nonexistent", "default")


class CacheAccessBenchmark(Benchmark):
    """缓存访问基准测试"""

    def __init__(self, cache_factory: Callable, iterations: int = 1000, warmup: int = 100):
        super().__init__("cache_access", iterations, warmup)
        self._factory = cache_factory
        self._cache = None

    def setup(self) -> None:
        self._cache = self._factory()
        for i in range(100):
            self._cache.put(f"key_{i}", f"value_{i}")

    def run(self) -> None:
        for i in range(10):
            self._cache.get(f"key_{i}")


# ============================================================
# 便捷函数
# ============================================================

def create_benchmark_runner() -> BenchmarkRunner:
    """创建基准测试运行器"""
    return BenchmarkRunner()


def create_benchmark_suite(name: str, description: str = "") -> BenchmarkSuite:
    """创建基准测试套件"""
    return BenchmarkSuite(name, description)


def quick_benchmark(
    name: str,
    func: Callable,
    iterations: int = 100,
    warmup: int = 10,
) -> BenchmarkResult:
    """快速基准测试"""
    benchmark = FunctionBenchmark(name, func, iterations, warmup)
    return benchmark.execute()
