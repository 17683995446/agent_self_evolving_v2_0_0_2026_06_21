"""
阶段59: 自动化测试接口标准化

第一性原理:
1. 测试是质量的守门员：没有自动化测试，质量无法保证
2. 测试必须快速反馈：慢测试会被跳过
3. 测试必须独立：一个测试的失败不应影响其他测试

设计原则:
- TestCase: 测试用例
- TestSuite: 测试套件
- TestRunner: 测试运行器
- TestReport: 测试报告
- 支持setup/teardown、参数化测试、并发执行
"""

import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class TestStatus(Enum):
    """测试状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    status: TestStatus
    elapsed_ms: float = 0.0
    error: str = ""
    output: str = ""


# ============================================================
# 测试用例
# ============================================================

class TestCase:
    """
    测试用例

    单个可执行的测试单元
    """

    def __init__(
        self,
        test_id: str,
        fn: Callable[..., Any],
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        setup: Optional[Callable[..., Any]] = None,
        teardown: Optional[Callable[..., Any]] = None,
    ):
        self.test_id = test_id
        self.fn = fn
        self.args = args
        self.kwargs = kwargs or {}
        self.setup = setup
        self.teardown = teardown

    def run(self) -> TestResult:
        """执行测试"""
        start = time.time()
        try:
            if self.setup:
                self.setup()
            self.fn(*self.args, **self.kwargs)
            elapsed = (time.time() - start) * 1000
            if self.teardown:
                self.teardown()
            return TestResult(
                test_id=self.test_id,
                status=TestStatus.PASSED,
                elapsed_ms=elapsed,
            )
        except AssertionError as e:
            elapsed = (time.time() - start) * 1000
            if self.teardown:
                try:
                    self.teardown()
                except Exception:
                    pass
            return TestResult(
                test_id=self.test_id,
                status=TestStatus.FAILED,
                elapsed_ms=elapsed,
                error=str(e),
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            if self.teardown:
                try:
                    self.teardown()
                except Exception:
                    pass
            return TestResult(
                test_id=self.test_id,
                status=TestStatus.ERROR,
                elapsed_ms=elapsed,
                error=f"{e}\n{traceback.format_exc()}",
            )


# ============================================================
# 测试套件
# ============================================================

class TestSuite:
    """
    测试套件

    组织多个测试用例的集合
    """

    def __init__(self, suite_id: str):
        self.suite_id = suite_id
        self._tests: List[TestCase] = []
        self._lock = threading.Lock()

    def add_test(self, test: TestCase) -> None:
        """添加测试"""
        with self._lock:
            self._tests.append(test)

    def add_tests(self, tests: List[TestCase]) -> None:
        """批量添加测试"""
        with self._lock:
            self._tests.extend(tests)

    def get_tests(self) -> List[TestCase]:
        """获取所有测试"""
        with self._lock:
            return list(self._tests)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "suite_id": self.suite_id,
                "total_tests": len(self._tests),
            }


# ============================================================
# 测试运行器
# ============================================================

class TestRunner:
    """
    测试运行器

    执行测试套件，收集结果
    """

    def __init__(self, parallel: bool = False, max_workers: int = 4):
        self.parallel = parallel
        self.max_workers = max_workers
        self._results: List[TestResult] = []
        self._lock = threading.Lock()

    def run(self, suite: TestSuite) -> "TestReport":
        """执行测试套件"""
        tests = suite.get_tests()
        self._results = []

        if self.parallel and len(tests) > 1:
            self._run_parallel(tests)
        else:
            self._run_sequential(tests)

        return TestReport(
            suite_id=suite.suite_id,
            results=list(self._results),
        )

    def _run_sequential(self, tests: List[TestCase]) -> None:
        """顺序执行"""
        for test in tests:
            result = test.run()
            self._results.append(result)

    def _run_parallel(self, tests: List[TestCase]) -> None:
        """并行执行"""
        def run_test(test: TestCase):
            result = test.run()
            with self._lock:
                self._results.append(result)

        threads = []
        for test in tests:
            t = threading.Thread(target=run_test, args=(test,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    def run_single(self, test: TestCase) -> TestResult:
        """执行单个测试"""
        return test.run()


# ============================================================
# 测试报告
# ============================================================

@dataclass
class TestReport:
    """测试报告"""
    suite_id: str
    results: List[TestResult]
    timestamp: float = field(default_factory=time.time)

    def get_summary(self) -> Dict[str, Any]:
        """获取摘要"""
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in self.results if r.status == TestStatus.ERROR)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
        total_time = sum(r.elapsed_ms for r in self.results)

        return {
            "suite_id": self.suite_id,
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "success_rate": passed / len(self.results) if self.results else 0.0,
            "total_time_ms": total_time,
        }

    def get_failures(self) -> List[TestResult]:
        """获取失败的测试"""
        return [r for r in self.results if r.status in (TestStatus.FAILED, TestStatus.ERROR)]


# ============================================================
# 参数化测试工具
# ============================================================

def parameterized_test(test_id_prefix: str, fn: Callable[..., Any], param_list: List[tuple]) -> List[TestCase]:
    """
    创建参数化测试用例

    Args:
        test_id_prefix: 测试ID前缀
        fn: 测试函数
        param_list: 参数列表 [(args_tuple, kwargs_dict), ...]

    Returns:
        测试用例列表
    """
    tests = []
    for i, (args, kwargs) in enumerate(param_list):
        test_id = f"{test_id_prefix}_{i}"
        tests.append(TestCase(test_id=test_id, fn=fn, args=args, kwargs=kwargs))
    return tests


# ============================================================
# 便捷函数
# ============================================================

def create_test_case(
    test_id: str,
    fn: Callable[..., Any],
    *args,
    setup: Optional[Callable[..., Any]] = None,
    teardown: Optional[Callable[..., Any]] = None,
    **kwargs,
) -> TestCase:
    """创建测试用例"""
    return TestCase(
        test_id=test_id,
        fn=fn,
        args=args,
        kwargs=kwargs,
        setup=setup,
        teardown=teardown,
    )


def create_test_suite(suite_id: str) -> TestSuite:
    """创建测试套件"""
    return TestSuite(suite_id=suite_id)


def create_test_runner(parallel: bool = False, max_workers: int = 4) -> TestRunner:
    """创建测试运行器"""
    return TestRunner(parallel=parallel, max_workers=max_workers)
