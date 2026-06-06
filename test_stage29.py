"""
阶段29: 健康检查接口 — 验证测试

验证目标:
1. 健康检查结果包含完整信息
2. 检查器分类正确（liveness/readiness/deep）
3. 注册表可注册、注销、查询
4. 状态聚合逻辑正确
5. 端点分层检查工作正常
6. 简单函数式检查器可用
"""

import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.health import (
    HealthStatus, HealthCheckResult, HealthChecker,
    LivenessChecker, ReadinessChecker, SimpleHealthChecker,
    HealthRegistry, HealthEndpoint, HealthReport,
)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print('='*60)


class MockLivenessChecker(LivenessChecker):
    """模拟存活检查器"""
    def __init__(self, healthy: bool = True):
        self._healthy = healthy
        self._name = "mock_liveness"
    
    @property
    def name(self) -> str:
        return self._name
    
    def check(self) -> HealthCheckResult:
        return HealthCheckResult(
            name=self.name,
            status=HealthStatus.HEALTHY if self._healthy else HealthStatus.UNHEALTHY,
            message="Mock liveness check",
        )


class MockReadinessChecker(ReadinessChecker):
    """模拟就绪检查器"""
    def __init__(self, status: HealthStatus = HealthStatus.HEALTHY):
        self._status = status
        self._name = "mock_readiness"
    
    @property
    def name(self) -> str:
        return self._name
    
    def check(self) -> HealthCheckResult:
        return HealthCheckResult(
            name=self.name,
            status=self._status,
            message="Mock readiness check",
        )


class MockDeepChecker(HealthChecker):
    """模拟深度检查器"""
    def __init__(self, name: str, status: HealthStatus = HealthStatus.HEALTHY):
        self._name = name
        self._status = status
    
    @property
    def name(self) -> str:
        return self._name
    
    def check(self) -> HealthCheckResult:
        return HealthCheckResult(
            name=self.name,
            status=self._status,
            message=f"Mock deep check: {self.name}",
        )


def test_health_status_enum():
    """测试健康状态枚举"""
    print_section("健康状态枚举")
    
    assert HealthStatus.HEALTHY.value == "healthy"
    assert HealthStatus.DEGRADED.value == "degraded"
    assert HealthStatus.UNHEALTHY.value == "unhealthy"
    assert HealthStatus.UNKNOWN.value == "unknown"
    print("状态值: healthy, degraded, unhealthy, unknown")
    
    print("\n健康状态枚举测试通过!")
    return True


def test_health_check_result():
    """测试结果数据结构"""
    print_section("健康检查结果")
    
    result = HealthCheckResult(
        name="memory",
        status=HealthStatus.HEALTHY,
        message="Memory usage normal: 45%",
        duration_ms=5.2,
        metadata={"used_mb": 1024, "total_mb": 2048},
    )
    
    assert result.name == "memory"
    assert result.status == HealthStatus.HEALTHY
    assert result.duration_ms == 5.2
    assert result.metadata["used_mb"] == 1024
    
    d = result.to_dict()
    assert d["name"] == "memory"
    assert d["status"] == "healthy"
    assert d["duration_ms"] == 5.2
    assert "timestamp" in d
    print(f"字典表示: {d}")
    
    print("\n健康检查结果测试通过!")
    return True


def test_checker_types():
    """测试检查器类型"""
    print_section("检查器类型")
    
    live = MockLivenessChecker()
    assert live.check_type == "liveness"
    assert live.name == "mock_liveness"
    print(f"存活检查器类型: {live.check_type}")
    
    ready = MockReadinessChecker()
    assert ready.check_type == "readiness"
    assert ready.name == "mock_readiness"
    print(f"就绪检查器类型: {ready.check_type}")
    
    deep = MockDeepChecker("database")
    assert deep.check_type == "deep"
    assert deep.name == "database"
    print(f"深度检查器类型: {deep.check_type}")
    
    print("\n检查器类型测试通过!")
    return True


def test_registry_register_unregister():
    """测试注册表注册和注销"""
    print_section("注册表注册和注销")
    
    registry = HealthRegistry()
    checker = MockDeepChecker("test")
    
    # 注册
    registry.register(checker)
    assert registry.get_checker("test") is not None
    print("注册检查器: 成功")
    
    # 列出
    checkers = registry.list_checkers()
    assert len(checkers) == 1
    print(f"列出检查器: {len(checkers)} 个")
    
    # 按类型列出
    deep_checkers = registry.list_checkers("deep")
    assert len(deep_checkers) == 1
    live_checkers = registry.list_checkers("liveness")
    assert len(live_checkers) == 0
    print(f"deep类型: {len(deep_checkers)} 个")
    print(f"liveness类型: {len(live_checkers)} 个")
    
    # 注销
    result = registry.unregister("test")
    assert result == True
    assert registry.get_checker("test") is None
    print("注销检查器: 成功")
    
    # 注销不存在的
    assert registry.unregister("nonexistent") == False
    print("注销不存在的: False")
    
    print("\n注册表注册和注销测试通过!")
    return True


def test_registry_run_checks():
    """测试运行检查"""
    print_section("运行检查")
    
    registry = HealthRegistry()
    registry.register(MockDeepChecker("db", HealthStatus.HEALTHY))
    registry.register(MockDeepChecker("cache", HealthStatus.DEGRADED))
    registry.register(MockDeepChecker("queue", HealthStatus.UNHEALTHY))
    
    results = registry.run_checks()
    assert len(results) == 3
    
    statuses = {r.name: r.status for r in results}
    assert statuses["db"] == HealthStatus.HEALTHY
    assert statuses["cache"] == HealthStatus.DEGRADED
    assert statuses["queue"] == HealthStatus.UNHEALTHY
    print(f"检查结果: {statuses}")
    
    print("\n运行检查测试通过!")
    return True


def test_overall_status_aggregation():
    """测试整体状态聚合"""
    print_section("整体状态聚合")
    
    registry = HealthRegistry()
    
    # 全部健康
    registry.register(MockDeepChecker("a", HealthStatus.HEALTHY))
    registry.register(MockDeepChecker("b", HealthStatus.HEALTHY))
    assert registry.get_overall_status() == HealthStatus.HEALTHY
    print("全部健康 -> HEALTHY")
    
    # 一个降级
    registry.unregister("b")
    registry.register(MockDeepChecker("b", HealthStatus.DEGRADED))
    assert registry.get_overall_status() == HealthStatus.DEGRADED
    print("一个降级 -> DEGRADED")
    
    # 一个不健康的覆盖降级
    registry.unregister("b")
    registry.register(MockDeepChecker("b", HealthStatus.UNHEALTHY))
    assert registry.get_overall_status() == HealthStatus.UNHEALTHY
    print("一个不健康 -> UNHEALTHY")
    
    # 空注册表
    empty_registry = HealthRegistry()
    assert empty_registry.get_overall_status() == HealthStatus.UNKNOWN
    print("空注册表 -> UNKNOWN")
    
    print("\n整体状态聚合测试通过!")
    return True


def test_health_endpoint():
    """测试健康检查端点"""
    print_section("健康检查端点")
    
    endpoint = HealthEndpoint()
    endpoint.registry.register(MockLivenessChecker(healthy=True))
    endpoint.registry.register(MockReadinessChecker(status=HealthStatus.HEALTHY))
    endpoint.registry.register(MockDeepChecker("db", HealthStatus.HEALTHY))
    
    # 存活检查
    live_report = endpoint.liveness()
    assert live_report.overall_status == HealthStatus.HEALTHY
    assert len(live_report.checks) == 1
    assert live_report.checks[0].name == "mock_liveness"
    print(f"存活检查: {live_report.overall_status.value}")
    
    # 就绪检查
    ready_report = endpoint.readiness()
    assert ready_report.overall_status == HealthStatus.HEALTHY
    assert len(ready_report.checks) == 1
    print(f"就绪检查: {ready_report.overall_status.value}")
    
    # 完整检查
    health_report = endpoint.health()
    assert health_report.overall_status == HealthStatus.HEALTHY
    assert len(health_report.checks) == 3
    print(f"完整检查: {health_report.overall_status.value}")
    print(f"检查项数: {len(health_report.checks)}")
    
    # 报告字典
    d = health_report.to_dict()
    assert d["overall_status"] == "healthy"
    assert d["healthy_count"] == 3
    assert d["unhealthy_count"] == 0
    print(f"报告字典: healthy_count={d['healthy_count']}")
    
    print("\n健康检查端点测试通过!")
    return True


def test_endpoint_with_unhealthy():
    """测试不健康状态的端点"""
    print_section("不健康状态端点")
    
    endpoint = HealthEndpoint()
    endpoint.registry.register(MockLivenessChecker(healthy=False))
    endpoint.registry.register(MockReadinessChecker(status=HealthStatus.DEGRADED))
    
    live_report = endpoint.liveness()
    assert live_report.overall_status == HealthStatus.UNHEALTHY
    print(f"存活检查(不健康): {live_report.overall_status.value}")
    
    ready_report = endpoint.readiness()
    assert ready_report.overall_status == HealthStatus.DEGRADED
    print(f"就绪检查(降级): {ready_report.overall_status.value}")
    
    print("\n不健康状态端点测试通过!")
    return True


def test_simple_health_checker():
    """测试简单函数式检查器"""
    print_section("简单函数式检查器")
    
    # 布尔返回
    checker1 = SimpleHealthChecker(
        "bool_check",
        lambda: (True, "All good", {"count": 42}),
        "readiness"
    )
    result1 = checker1.check()
    assert result1.status == HealthStatus.HEALTHY
    assert result1.message == "All good"
    assert result1.metadata["count"] == 42
    print(f"布尔检查: {result1.status.value}, {result1.message}")
    
    # 字符串返回
    checker2 = SimpleHealthChecker(
        "str_check",
        lambda: ("degraded", "Slow response", {"latency_ms": 500}),
    )
    result2 = checker2.check()
    assert result2.status == HealthStatus.DEGRADED
    print(f"字符串检查: {result2.status.value}, {result2.message}")
    
    # HealthStatus返回
    checker3 = SimpleHealthChecker(
        "enum_check",
        lambda: (HealthStatus.UNHEALTHY, "Connection refused", {}),
    )
    result3 = checker3.check()
    assert result3.status == HealthStatus.UNHEALTHY
    print(f"枚举检查: {result3.status.value}")
    
    # 异常处理
    checker4 = SimpleHealthChecker(
        "error_check",
        lambda: (_ for _ in ()).throw(ValueError("Oops")),
    )
    result4 = checker4.check()
    assert result4.status == HealthStatus.UNHEALTHY
    assert "exception" in result4.message.lower() or "failed" in result4.message.lower()
    print(f"异常检查: {result4.status.value}, {result4.message}")
    
    print("\n简单函数式检查器测试通过!")
    return True


def test_check_by_type_filtering():
    """测试按类型过滤检查"""
    print_section("按类型过滤检查")
    
    registry = HealthRegistry()
    registry.register(MockLivenessChecker())
    registry.register(MockReadinessChecker())
    registry.register(MockDeepChecker("db"))
    
    # 只运行存活检查
    live_results = registry.run_checks("liveness")
    assert len(live_results) == 1
    assert live_results[0].name == "mock_liveness"
    print(f"存活检查结果数: {len(live_results)}")
    
    # 只运行就绪检查
    ready_results = registry.run_checks("readiness")
    assert len(ready_results) == 1
    assert ready_results[0].name == "mock_readiness"
    print(f"就绪检查结果数: {len(ready_results)}")
    
    # 运行所有
    all_results = registry.run_checks()
    assert len(all_results) == 3
    print(f"所有检查结果数: {len(all_results)}")
    
    print("\n按类型过滤检查测试通过!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("阶段29: 健康检查接口 — 验证测试")
    print("="*60)
    
    tests = [
        test_health_status_enum,
        test_health_check_result,
        test_checker_types,
        test_registry_register_unregister,
        test_registry_run_checks,
        test_overall_status_aggregation,
        test_health_endpoint,
        test_endpoint_with_unhealthy,
        test_simple_health_checker,
        test_check_by_type_filtering,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"\n[失败] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("="*60)
