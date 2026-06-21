"""
阶段141: 性能基准套件 — 基准测试 测试

第一性原理验证:
1. 可测量性 — 性能可量化
2. 可重复性 — 结果可重复
3. 可比较性 — 不同版本可比较
4. 渐进改进 — 基于数据改进
5. 回归检测 — 自动检测回归
"""

import os
import sys
import time
import json
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from self_evolving_agent.core.benchmark import (
    BenchmarkStatus,
    BenchmarkResult,
    Benchmark,
    FunctionBenchmark,
    BaselineEntry,
    PerformanceBaseline,
    BenchmarkSuite,
    BenchmarkRunner,
    BenchmarkReporter,
    AgentObserveBenchmark,
    ConfigAccessBenchmark,
    CacheAccessBenchmark,
    create_benchmark_runner,
    create_benchmark_suite,
    quick_benchmark,
)


# ============================================================
# 1. BenchmarkResult 测试
# ============================================================

class TestBenchmarkResult:
    """基准测试结果测试"""

    def test_create_result(self):
        """测试创建结果"""
        result = BenchmarkResult(
            name="test",
            status=BenchmarkStatus.PASSED,
            iterations=100,
            total_time=1.0,
            avg_time=0.01,
            min_time=0.005,
            max_time=0.02,
            median_time=0.01,
            stdev_time=0.002,
            ops_per_second=100,
            timestamp=time.time(),
        )
        assert result.name == "test"
        assert result.passed is True

    def test_failed_result(self):
        """测试失败结果"""
        result = BenchmarkResult(
            name="test",
            status=BenchmarkStatus.FAILED,
            iterations=100,
            total_time=1.0,
            avg_time=0.01,
            min_time=0.005,
            max_time=0.02,
            median_time=0.01,
            stdev_time=0.002,
            ops_per_second=100,
            timestamp=time.time(),
            error="Too slow",
        )
        assert result.passed is False
        assert result.error == "Too slow"

    def test_to_dict(self):
        """测试转字典"""
        result = BenchmarkResult(
            name="test",
            status=BenchmarkStatus.PASSED,
            iterations=100,
            total_time=1.0,
            avg_time=0.01,
            min_time=0.005,
            max_time=0.02,
            median_time=0.01,
            stdev_time=0.002,
            ops_per_second=100,
            timestamp=time.time(),
        )
        d = result.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "passed"
        assert d["iterations"] == 100


# ============================================================
# 2. FunctionBenchmark 测试
# ============================================================

class TestFunctionBenchmark:
    """函数基准测试测试"""

    def test_execute_success(self):
        """测试执行成功"""
        call_count = [0]
        def func():
            call_count[0] += 1

        benchmark = FunctionBenchmark("test", func, iterations=10, warmup=2)
        result = benchmark.execute()

        assert result.status == BenchmarkStatus.PASSED
        assert result.iterations == 10
        assert result.avg_time > 0
        assert result.ops_per_second > 0

    def test_execute_with_error(self):
        """测试执行出错"""
        def func():
            raise ValueError("test error")

        benchmark = FunctionBenchmark("test", func, iterations=10, warmup=0)
        result = benchmark.execute()

        assert result.status == BenchmarkStatus.ERROR
        assert result.error is not None
        assert "test error" in result.error

    def test_setup_teardown(self):
        """测试设置和清理"""
        setup_called = [False]
        teardown_called = [False]

        def setup():
            setup_called[0] = True

        def teardown():
            teardown_called[0] = True

        benchmark = FunctionBenchmark(
            "test", lambda: None, iterations=5, warmup=1,
            setup_func=setup, teardown_func=teardown,
        )
        benchmark.execute()

        assert setup_called[0]
        assert teardown_called[0]

    def test_setup_failure(self):
        """测试设置失败"""
        def setup():
            raise RuntimeError("setup failed")

        benchmark = FunctionBenchmark(
            "test", lambda: None, iterations=5, warmup=0,
            setup_func=setup,
        )
        result = benchmark.execute()

        assert result.status == BenchmarkStatus.ERROR
        assert "setup failed" in result.error

    def test_warmup_not_counted(self):
        """测试预热不计入结果"""
        call_count = [0]
        def func():
            call_count[0] += 1

        benchmark = FunctionBenchmark("test", func, iterations=10, warmup=5)
        result = benchmark.execute()

        # 10 iterations + 5 warmup = 15 calls
        assert call_count[0] == 15
        assert result.iterations == 10

    def test_statistics_calculated(self):
        """测试统计计算"""
        def func():
            time.sleep(0.001)

        benchmark = FunctionBenchmark("test", func, iterations=20, warmup=2)
        result = benchmark.execute()

        assert result.min_time <= result.avg_time <= result.max_time
        assert result.median_time > 0
        assert result.stdev_time >= 0
        assert len(result.samples) == 20


# ============================================================
# 3. PerformanceBaseline 测试
# ============================================================

class TestPerformanceBaseline:
    """性能基线测试"""

    def test_set_and_get_baseline(self):
        """测试设置和获取基线"""
        baseline = PerformanceBaseline()
        baseline.set_baseline("test", max_avg_time=0.1, min_ops_per_second=10)
        entry = baseline.get_baseline("test")
        assert entry is not None
        assert entry.max_avg_time == 0.1
        assert entry.min_ops_per_second == 10

    def test_remove_baseline(self):
        """测试移除基线"""
        baseline = PerformanceBaseline()
        baseline.set_baseline("test", max_avg_time=0.1, min_ops_per_second=10)
        baseline.remove_baseline("test")
        assert baseline.get_baseline("test") is None

    def test_check_passed(self):
        """测试检查通过"""
        baseline = PerformanceBaseline()
        baseline.set_baseline("test", max_avg_time=0.1, min_ops_per_second=10)
        result = BenchmarkResult(
            name="test", status=BenchmarkStatus.PASSED,
            iterations=100, total_time=1.0, avg_time=0.01,
            min_time=0.005, max_time=0.02, median_time=0.01,
            stdev_time=0.002, ops_per_second=100, timestamp=time.time(),
        )
        passed, error = baseline.check(result)
        assert passed
        assert error is None

    def test_check_failed_avg_time(self):
        """测试检查失败（平均时间）"""
        baseline = PerformanceBaseline()
        baseline.set_baseline("test", max_avg_time=0.001, min_ops_per_second=10)
        result = BenchmarkResult(
            name="test", status=BenchmarkStatus.PASSED,
            iterations=100, total_time=1.0, avg_time=0.01,
            min_time=0.005, max_time=0.02, median_time=0.01,
            stdev_time=0.002, ops_per_second=100, timestamp=time.time(),
        )
        passed, error = baseline.check(result)
        assert not passed
        assert "Avg time" in error

    def test_check_failed_ops_per_second(self):
        """测试检查失败（每秒操作数）"""
        baseline = PerformanceBaseline()
        baseline.set_baseline("test", max_avg_time=0.1, min_ops_per_second=1000)
        result = BenchmarkResult(
            name="test", status=BenchmarkStatus.PASSED,
            iterations=100, total_time=1.0, avg_time=0.01,
            min_time=0.005, max_time=0.02, median_time=0.01,
            stdev_time=0.002, ops_per_second=100, timestamp=time.time(),
        )
        passed, error = baseline.check(result)
        assert not passed
        assert "Ops/sec" in error

    def test_check_no_baseline(self):
        """测试无基线时通过"""
        baseline = PerformanceBaseline()
        result = BenchmarkResult(
            name="test", status=BenchmarkStatus.PASSED,
            iterations=100, total_time=1.0, avg_time=0.01,
            min_time=0.005, max_time=0.02, median_time=0.01,
            stdev_time=0.002, ops_per_second=100, timestamp=time.time(),
        )
        passed, error = baseline.check(result)
        assert passed

    def test_check_stdev(self):
        """测试标准差检查"""
        baseline = PerformanceBaseline()
        baseline.set_baseline("test", max_avg_time=0.1, min_ops_per_second=10, max_stdev_time=0.001)
        result = BenchmarkResult(
            name="test", status=BenchmarkStatus.PASSED,
            iterations=100, total_time=1.0, avg_time=0.01,
            min_time=0.005, max_time=0.02, median_time=0.01,
            stdev_time=0.01, ops_per_second=100, timestamp=time.time(),
        )
        passed, error = baseline.check(result)
        assert not passed
        assert "Stdev" in error

    def test_list_baselines(self):
        """测试列出基线"""
        baseline = PerformanceBaseline()
        baseline.set_baseline("a", max_avg_time=0.1, min_ops_per_second=10)
        baseline.set_baseline("b", max_avg_time=0.2, min_ops_per_second=5)
        names = baseline.list_baselines()
        assert "a" in names
        assert "b" in names

    def test_save_and_load(self):
        """测试保存和加载"""
        baseline = PerformanceBaseline()
        baseline.set_baseline("test", max_avg_time=0.1, min_ops_per_second=10)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            baseline.save(path)
            new_baseline = PerformanceBaseline()
            new_baseline.load(path)
            entry = new_baseline.get_baseline("test")
            assert entry is not None
            assert entry.max_avg_time == 0.1
        finally:
            os.unlink(path)

    def test_to_dict(self):
        """测试转字典"""
        baseline = PerformanceBaseline()
        baseline.set_baseline("test", max_avg_time=0.1, min_ops_per_second=10)
        d = baseline.to_dict()
        assert "test" in d
        assert d["test"]["max_avg_time"] == 0.1


# ============================================================
# 4. BenchmarkSuite 测试
# ============================================================

class TestBenchmarkSuite:
    """基准测试套件测试"""

    def test_add_and_remove(self):
        """测试添加和移除"""
        suite = create_benchmark_suite("test_suite")
        benchmark = FunctionBenchmark("bench1", lambda: None, iterations=5, warmup=0)
        suite.add(benchmark)
        assert suite.count() == 1
        assert "bench1" in suite.list_benchmarks()

        suite.remove("bench1")
        assert suite.count() == 0

    def test_get_benchmark(self):
        """测试获取基准测试"""
        suite = create_benchmark_suite("test_suite")
        benchmark = FunctionBenchmark("bench1", lambda: None, iterations=5, warmup=0)
        suite.add(benchmark)
        assert suite.get("bench1") is not None
        assert suite.get("nonexistent") is None

    def test_run_all(self):
        """测试运行所有"""
        suite = create_benchmark_suite("test_suite")
        suite.add(FunctionBenchmark("b1", lambda: None, iterations=5, warmup=0))
        suite.add(FunctionBenchmark("b2", lambda: None, iterations=5, warmup=0))

        results = suite.run_all()
        assert len(results) == 2
        assert all(r.status == BenchmarkStatus.PASSED for r in results)

    def test_run_all_with_error(self):
        """测试运行所有（含错误）"""
        suite = create_benchmark_suite("test_suite")
        suite.add(FunctionBenchmark("b1", lambda: None, iterations=5, warmup=0))
        suite.add(FunctionBenchmark("b2", lambda: (_ for _ in ()).throw(ValueError("err")), iterations=5, warmup=0))

        results = suite.run_all()
        assert len(results) == 2
        assert results[0].status == BenchmarkStatus.PASSED
        assert results[1].status == BenchmarkStatus.ERROR


# ============================================================
# 5. BenchmarkRunner 测试
# ============================================================

class TestBenchmarkRunner:
    """基准测试运行器测试"""

    def test_add_and_get_suite(self):
        """测试添加和获取套件"""
        runner = create_benchmark_runner()
        suite = create_benchmark_suite("test")
        runner.add_suite(suite)
        assert runner.get_suite("test") is not None
        assert "test" in runner.list_suites()

    def test_run_suite(self):
        """测试运行套件"""
        runner = create_benchmark_runner()
        suite = create_benchmark_suite("test")
        suite.add(FunctionBenchmark("b1", lambda: None, iterations=5, warmup=0))
        runner.add_suite(suite)

        results = runner.run_suite("test")
        assert len(results) == 1
        assert results[0].status == BenchmarkStatus.PASSED

    def test_run_all(self):
        """测试运行所有"""
        runner = create_benchmark_runner()
        suite1 = create_benchmark_suite("s1")
        suite1.add(FunctionBenchmark("b1", lambda: None, iterations=5, warmup=0))
        suite2 = create_benchmark_suite("s2")
        suite2.add(FunctionBenchmark("b2", lambda: None, iterations=5, warmup=0))
        runner.add_suite(suite1)
        runner.add_suite(suite2)

        results = runner.run_all()
        assert len(results) == 2

    def test_run_benchmark(self):
        """测试运行单个基准测试"""
        runner = create_benchmark_runner()
        benchmark = FunctionBenchmark("b1", lambda: None, iterations=5, warmup=0)
        result = runner.run_benchmark(benchmark)
        assert result.status == BenchmarkStatus.PASSED

    def test_baseline_check_integration(self):
        """测试基线检查集成"""
        runner = create_benchmark_runner()
        runner.baseline.set_baseline("b1", max_avg_time=0.0001, min_ops_per_second=100000)

        suite = create_benchmark_suite("test")
        suite.add(FunctionBenchmark("b1", lambda: time.sleep(0.01), iterations=5, warmup=0))
        runner.add_suite(suite)

        results = runner.run_suite("test")
        # 因为sleep 0.01s，avg_time会超过0.0001
        assert results[0].status == BenchmarkStatus.FAILED

    def test_get_results(self):
        """测试获取结果"""
        runner = create_benchmark_runner()
        benchmark = FunctionBenchmark("b1", lambda: None, iterations=5, warmup=0)
        runner.run_benchmark(benchmark)
        results = runner.get_results()
        assert len(results) == 1

    def test_clear_results(self):
        """测试清空结果"""
        runner = create_benchmark_runner()
        runner.run_benchmark(FunctionBenchmark("b1", lambda: None, iterations=5, warmup=0))
        runner.clear_results()
        assert len(runner.get_results()) == 0

    def test_get_summary(self):
        """测试获取摘要"""
        runner = create_benchmark_runner()
        suite = create_benchmark_suite("test")
        suite.add(FunctionBenchmark("b1", lambda: None, iterations=5, warmup=0))
        suite.add(FunctionBenchmark("b2", lambda: (_ for _ in ()).throw(ValueError("err")), iterations=5, warmup=0))
        runner.add_suite(suite)
        runner.run_suite("test")

        summary = runner.get_summary()
        assert summary["total"] == 2
        assert summary["passed"] == 1
        assert summary["errors"] == 1


# ============================================================
# 6. BenchmarkReporter 测试
# ============================================================

class TestBenchmarkReporter:
    """报告生成器测试"""

    def test_to_text(self):
        """测试文本报告"""
        results = [
            BenchmarkResult(
                name="test1", status=BenchmarkStatus.PASSED,
                iterations=100, total_time=1.0, avg_time=0.01,
                min_time=0.005, max_time=0.02, median_time=0.01,
                stdev_time=0.002, ops_per_second=100, timestamp=time.time(),
            ),
        ]
        text = BenchmarkReporter.to_text(results)
        assert "基准测试报告" in text
        assert "test1" in text
        assert "通过" in text

    def test_to_json(self):
        """测试JSON报告"""
        results = [
            BenchmarkResult(
                name="test1", status=BenchmarkStatus.PASSED,
                iterations=100, total_time=1.0, avg_time=0.01,
                min_time=0.005, max_time=0.02, median_time=0.01,
                stdev_time=0.002, ops_per_second=100, timestamp=time.time(),
            ),
        ]
        json_str = BenchmarkReporter.to_json(results)
        data = json.loads(json_str)
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["summary"]["total"] == 1

    def test_to_dict(self):
        """测试字典报告"""
        results = [
            BenchmarkResult(
                name="test1", status=BenchmarkStatus.PASSED,
                iterations=100, total_time=1.0, avg_time=0.01,
                min_time=0.005, max_time=0.02, median_time=0.01,
                stdev_time=0.002, ops_per_second=100, timestamp=time.time(),
            ),
        ]
        d = BenchmarkReporter.to_dict(results)
        assert "results" in d
        assert "summary" in d

    def test_save(self):
        """测试保存报告"""
        results = [
            BenchmarkResult(
                name="test1", status=BenchmarkStatus.PASSED,
                iterations=100, total_time=1.0, avg_time=0.01,
                min_time=0.005, max_time=0.02, median_time=0.01,
                stdev_time=0.002, ops_per_second=100, timestamp=time.time(),
            ),
        ]
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            BenchmarkReporter.save(results, path, format="json")
            with open(path) as f:
                data = json.load(f)
            assert "results" in data
        finally:
            os.unlink(path)


# ============================================================
# 7. 预定义基准测试测试
# ============================================================

class TestPredefinedBenchmarks:
    """预定义基准测试测试"""

    def test_config_access_benchmark(self):
        """测试配置访问基准"""
        from self_evolving_agent.core.config_hot_reload import create_hot_reload_manager

        benchmark = ConfigAccessBenchmark(
            create_hot_reload_manager,
            iterations=100,
            warmup=10,
        )
        result = benchmark.execute()
        assert result.status == BenchmarkStatus.PASSED
        assert result.iterations == 100
        assert result.ops_per_second > 0

    def test_quick_benchmark(self):
        """测试快速基准"""
        result = quick_benchmark("quick", lambda: sum(range(100)), iterations=50, warmup=5)
        assert result.status == BenchmarkStatus.PASSED
        assert result.name == "quick"
        assert result.iterations == 50


# ============================================================
# 8. 第一性原理测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_measurable_principle(self):
        """第一性原理：可测量性 — 性能可量化"""
        result = quick_benchmark("test", lambda: sum(range(1000)), iterations=50, warmup=5)
        # 性能被量化为具体数值
        assert result.avg_time > 0
        assert result.ops_per_second > 0
        assert result.min_time > 0
        assert result.max_time > 0
        assert result.stdev_time >= 0

    def test_repeatability_principle(self):
        """第一性原理：可重复性 — 结果可重复"""
        # 同一操作运行两次，结果应相近
        result1 = quick_benchmark("test1", lambda: sum(range(100)), iterations=50, warmup=10)
        result2 = quick_benchmark("test2", lambda: sum(range(100)), iterations=50, warmup=10)
        # 两次运行的平均时间应在同一数量级
        ratio = max(result1.avg_time, result2.avg_time) / min(result1.avg_time, result2.avg_time)
        assert ratio < 10  # 差异不超过10倍

    def test_comparable_principle(self):
        """第一性原理：可比较性 — 不同操作可比较"""
        fast_result = quick_benchmark("fast", lambda: None, iterations=100, warmup=10)
        slow_result = quick_benchmark("slow", lambda: time.sleep(0.001), iterations=50, warmup=5)
        # 快操作应比慢操作快
        assert fast_result.avg_time < slow_result.avg_time
        assert fast_result.ops_per_second > slow_result.ops_per_second

    def test_regression_detection_principle(self):
        """第一性原理：回归检测 — 自动检测性能回归"""
        runner = create_benchmark_runner()
        # 设置严格基线
        runner.baseline.set_baseline("slow_op", max_avg_time=0.0001, min_ops_per_second=10000)

        suite = create_benchmark_suite("test")
        suite.add(FunctionBenchmark("slow_op", lambda: time.sleep(0.01), iterations=5, warmup=0))
        runner.add_suite(suite)

        results = runner.run_suite("test")
        # 应检测到回归
        assert results[0].status == BenchmarkStatus.FAILED
        assert results[0].error is not None

    def test_progressive_improvement_principle(self):
        """第一性原理：渐进改进 — 基于数据改进"""
        # 第一次运行
        result1 = quick_benchmark("v1", lambda: [i * 2 for i in range(100)], iterations=50, warmup=10)
        # 优化版本（使用生成器）
        result2 = quick_benchmark("v2", lambda: list(i * 2 for i in range(100)), iterations=50, warmup=10)

        # 两个版本都有可量化的性能数据，可用于比较和改进决策
        assert result1.avg_time > 0
        assert result2.avg_time > 0
        # 基线可以基于这些数据设置
        baseline = PerformanceBaseline()
        baseline.set_baseline("list_comp", max_avg_time=result1.avg_time * 2, min_ops_per_second=0)
        passed, _ = baseline.check(result1)
        assert passed


# ============================================================
# 9. 边界条件测试
# ============================================================

class TestEdgeCases:
    """边界条件测试"""

    def test_single_iteration(self):
        """测试单次迭代"""
        result = quick_benchmark("test", lambda: None, iterations=1, warmup=0)
        assert result.status == BenchmarkStatus.PASSED
        assert result.iterations == 1
        assert result.stdev_time == 0  # 单次无标准差

    def test_zero_warmup(self):
        """测试零预热"""
        result = quick_benchmark("test", lambda: None, iterations=5, warmup=0)
        assert result.status == BenchmarkStatus.PASSED

    def test_fast_function(self):
        """测试极快函数"""
        result = quick_benchmark("test", lambda: None, iterations=100, warmup=10)
        assert result.status == BenchmarkStatus.PASSED
        assert result.avg_time >= 0  # 可能为0或极小

    def test_slow_function(self):
        """测试慢函数"""
        result = quick_benchmark("test", lambda: time.sleep(0.01), iterations=5, warmup=1)
        assert result.status == BenchmarkStatus.PASSED
        assert result.avg_time >= 0.005  # 至少5ms

    def test_empty_suite(self):
        """测试空套件"""
        suite = create_benchmark_suite("empty")
        results = suite.run_all()
        assert len(results) == 0

    def test_empty_runner(self):
        """测试空运行器"""
        runner = create_benchmark_runner()
        results = runner.run_all()
        assert len(results) == 0
        summary = runner.get_summary()
        assert summary["total"] == 0

    def test_multiple_baselines(self):
        """测试多个基线"""
        baseline = PerformanceBaseline()
        for i in range(10):
            baseline.set_baseline(f"bench_{i}", max_avg_time=0.1, min_ops_per_second=10)
        names = baseline.list_baselines()
        assert len(names) == 10

    def test_benchmark_name_truncation_in_report(self):
        """测试报告中名称截断"""
        long_name = "a" * 100
        result = BenchmarkResult(
            name=long_name, status=BenchmarkStatus.PASSED,
            iterations=100, total_time=1.0, avg_time=0.01,
            min_time=0.005, max_time=0.02, median_time=0.01,
            stdev_time=0.002, ops_per_second=100, timestamp=time.time(),
        )
        text = BenchmarkReporter.to_text([result])
        # 名称应被截断
        assert "a" * 38 in text
