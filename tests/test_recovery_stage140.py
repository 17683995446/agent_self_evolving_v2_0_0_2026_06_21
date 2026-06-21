"""
阶段140: 错误恢复策略 — 自动恢复 测试

第一性原理验证:
1. 弹性 — 从错误中恢复
2. 隔离性 — 错误不传播
3. 可观测性 — 错误被记录
4. 渐进降级 — 部分失效时降级
5. 自愈性 — 自动检测和修复
"""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from self_evolving_agent.core.recovery import (
    ErrorSeverity,
    RecoveryAction,
    ErrorContext,
    RetryPolicy,
    FallbackHandler,
    CircuitState,
    CircuitBreakerPolicy,
    HealthCheckResult,
    HealthMonitor,
    RecoveryStrategy,
    RecoveryManager,
    create_recovery_manager,
    create_retry_policy,
    create_circuit_breaker,
    create_recovery_strategy,
)


# ============================================================
# 1. ErrorContext 测试
# ============================================================

class TestErrorContext:
    """错误上下文测试"""

    def test_create_error_context(self):
        """测试创建错误上下文"""
        ctx = ErrorContext(
            error_id="err_1",
            error_type="ValueError",
            error_message="Invalid value",
            traceback_str="traceback",
            component="test_component",
            operation="test_op",
            timestamp=time.time(),
        )
        assert ctx.error_id == "err_1"
        assert ctx.error_type == "ValueError"
        assert ctx.severity == ErrorSeverity.MEDIUM

    def test_to_dict(self):
        """测试转字典"""
        ctx = ErrorContext(
            error_id="err_1",
            error_type="ValueError",
            error_message="msg",
            traceback_str="tb",
            component="comp",
            operation="op",
            timestamp=time.time(),
            severity=ErrorSeverity.HIGH,
            recovery_action=RecoveryAction.RETRY,
            recovery_success=True,
        )
        d = ctx.to_dict()
        assert d["error_id"] == "err_1"
        assert d["severity"] == "high"
        assert d["recovery_action"] == "retry"
        assert d["recovery_success"] is True

    def test_severity_levels(self):
        """测试严重级别"""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_recovery_actions(self):
        """测试恢复动作"""
        assert RecoveryAction.RETRY.value == "retry"
        assert RecoveryAction.FALLBACK.value == "fallback"
        assert RecoveryAction.CIRCUIT_BREAK.value == "circuit_break"
        assert RecoveryAction.DEGRADE.value == "degrade"


# ============================================================
# 2. RetryPolicy 测试
# ============================================================

class TestRetryPolicy:
    """重试策略测试"""

    def test_execute_success_first_try(self):
        """测试首次成功"""
        policy = RetryPolicy(max_retries=3, base_delay=0)
        call_count = [0]

        def func():
            call_count[0] += 1
            return "success"

        result, error = policy.execute(func)
        assert result == "success"
        assert error is None
        assert call_count[0] == 1

    def test_execute_success_after_retry(self):
        """测试重试后成功"""
        policy = RetryPolicy(max_retries=3, base_delay=0)
        call_count = [0]

        def func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("fail")
            return "success"

        result, error = policy.execute(func)
        assert result == "success"
        assert error is None
        assert call_count[0] == 3

    def test_execute_all_retries_fail(self):
        """测试所有重试都失败"""
        policy = RetryPolicy(max_retries=2, base_delay=0)

        def func():
            raise ValueError("always fail")

        result, error = policy.execute(func)
        assert result is None
        assert isinstance(error, ValueError)
        assert str(error) == "always fail"

    def test_should_retry(self):
        """测试是否应该重试"""
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(ValueError(), 0)
        assert policy.should_retry(ValueError(), 2)
        assert not policy.should_retry(ValueError(), 3)

    def test_get_delay_exponential(self):
        """测试指数退避"""
        policy = RetryPolicy(base_delay=0.1, exponential=True)
        assert policy.get_delay(0) == 0.1
        assert policy.get_delay(1) == 0.2
        assert policy.get_delay(2) == 0.4

    def test_get_delay_max_cap(self):
        """测试延迟上限"""
        policy = RetryPolicy(base_delay=0.1, max_delay=0.5, exponential=True)
        assert policy.get_delay(10) == 0.5

    def test_get_delay_fixed(self):
        """测试固定延迟"""
        policy = RetryPolicy(base_delay=0.5, exponential=False)
        assert policy.get_delay(0) == 0.5
        assert policy.get_delay(5) == 0.5

    def test_retryable_exceptions(self):
        """测试可重试异常类型"""
        policy = RetryPolicy(retryable_exceptions={ValueError})
        assert policy.should_retry(ValueError(), 0)
        assert not policy.should_retry(TypeError(), 0)

    def test_get_stats(self):
        """测试统计"""
        policy = RetryPolicy(max_retries=1, base_delay=0)
        policy.execute(lambda: "ok")
        stats = policy.get_stats()
        assert stats["successes"] == 1

    def test_zero_retries(self):
        """测试零重试"""
        policy = RetryPolicy(max_retries=0, base_delay=0)

        def func():
            raise ValueError("fail")

        result, error = policy.execute(func)
        assert result is None
        assert isinstance(error, ValueError)


# ============================================================
# 3. FallbackHandler 测试
# ============================================================

class TestFallbackHandler:
    """回退处理器测试"""

    def test_register_and_execute(self):
        """测试注册和执行"""
        handler = FallbackHandler()
        handler.register("op", lambda: "fallback_result")

        result, error = handler.execute("op")
        assert result == "fallback_result"
        assert error is None

    def test_execute_no_fallback(self):
        """测试无回退"""
        handler = FallbackHandler()
        result, error = handler.execute("nonexistent")
        assert result is None
        assert error is not None

    def test_has_fallback(self):
        """测试检查回退"""
        handler = FallbackHandler()
        handler.register("op", lambda: "result")
        assert handler.has_fallback("op")
        assert not handler.has_fallback("other")

    def test_unregister(self):
        """测试注销"""
        handler = FallbackHandler()
        handler.register("op", lambda: "result")
        handler.unregister("op")
        assert not handler.has_fallback("op")

    def test_fallback_with_error(self):
        """测试回退函数出错"""
        handler = FallbackHandler()
        handler.register("op", lambda: (_ for _ in ()).throw(ValueError("fallback error")))
        result, error = handler.execute("op")
        assert result is None
        assert isinstance(error, ValueError)

    def test_fallback_with_args(self):
        """测试带参数的回退"""
        handler = FallbackHandler()
        handler.register("op", lambda x, y: x + y)
        result, error = handler.execute("op", 1, 2)
        assert result == 3

    def test_get_stats(self):
        """测试统计"""
        handler = FallbackHandler()
        handler.register("op", lambda: "ok")
        handler.execute("op")
        handler.execute("nonexistent")
        stats = handler.get_stats()
        assert stats["invoked"] == 2
        assert stats["successes"] == 1
        assert stats["failures"] == 1


# ============================================================
# 4. CircuitBreakerPolicy 测试
# ============================================================

class TestCircuitBreakerPolicy:
    """熔断策略测试"""

    def test_initial_state_closed(self):
        """测试初始状态为关闭"""
        cb = CircuitBreakerPolicy()
        assert cb.state == CircuitState.CLOSED

    def test_can_execute_when_closed(self):
        """测试关闭时可执行"""
        cb = CircuitBreakerPolicy()
        assert cb.can_execute()

    def test_open_after_threshold(self):
        """测试达到阈值后熔断"""
        cb = CircuitBreakerPolicy(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_cannot_execute_when_open(self):
        """测试熔断时不可执行"""
        cb = CircuitBreakerPolicy(failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert not cb.can_execute()

    def test_half_open_after_timeout(self):
        """测试超时后半开"""
        cb = CircuitBreakerPolicy(failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    def test_close_after_half_open_success(self):
        """测试半开状态下成功后关闭"""
        cb = CircuitBreakerPolicy(failure_threshold=1, recovery_timeout=0.1, half_open_max_calls=2)
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_reopen_after_half_open_failure(self):
        """测试半开状态下失败后重新熔断"""
        cb = CircuitBreakerPolicy(failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_reset(self):
        """测试重置"""
        cb = CircuitBreakerPolicy(failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    def test_get_stats(self):
        """测试统计"""
        cb = CircuitBreakerPolicy(failure_threshold=3)
        cb.record_failure()
        stats = cb.get_stats()
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 1


# ============================================================
# 5. HealthMonitor 测试
# ============================================================

class TestHealthMonitor:
    """健康监控测试"""

    def test_register_and_check(self):
        """测试注册和检查"""
        monitor = HealthMonitor()
        monitor.register_check("db", lambda: HealthCheckResult(
            component="db", healthy=True, message="OK", timestamp=time.time()
        ))

        result = monitor.check_one("db")
        assert result is not None
        assert result.healthy is True

    def test_check_all(self):
        """测试检查所有"""
        monitor = HealthMonitor()
        monitor.register_check("comp1", lambda: HealthCheckResult(
            component="comp1", healthy=True, message="OK", timestamp=time.time()
        ))
        monitor.register_check("comp2", lambda: HealthCheckResult(
            component="comp2", healthy=False, message="FAIL", timestamp=time.time()
        ))

        results = monitor.check_all()
        assert len(results) == 2
        assert results["comp1"].healthy is True
        assert results["comp2"].healthy is False

    def test_is_healthy(self):
        """测试整体健康"""
        monitor = HealthMonitor()
        monitor.register_check("comp1", lambda: HealthCheckResult(
            component="comp1", healthy=True, message="OK", timestamp=time.time()
        ))
        monitor.check_all()
        assert monitor.is_healthy()

        monitor.register_check("comp2", lambda: HealthCheckResult(
            component="comp2", healthy=False, message="FAIL", timestamp=time.time()
        ))
        monitor.check_all()
        assert not monitor.is_healthy()

    def test_unhealthy_callback(self):
        """测试不健康回调"""
        monitor = HealthMonitor()
        received = []
        monitor.set_unhealthy_callback(lambda r: received.append(r))

        monitor.register_check("bad", lambda: HealthCheckResult(
            component="bad", healthy=False, message="FAIL", timestamp=time.time()
        ))
        monitor.check_all()
        assert len(received) == 1
        assert received[0].component == "bad"

    def test_check_error_handled(self):
        """测试检查异常处理"""
        monitor = HealthMonitor()
        monitor.register_check("bad", lambda: (_ for _ in ()).throw(RuntimeError("check failed")))
        result = monitor.check_one("bad")
        assert result is not None
        assert result.healthy is False
        assert "check failed" in result.message

    def test_unregister_check(self):
        """测试注销检查"""
        monitor = HealthMonitor()
        monitor.register_check("comp", lambda: HealthCheckResult(
            component="comp", healthy=True, message="OK", timestamp=time.time()
        ))
        monitor.unregister_check("comp")
        assert "comp" not in monitor.get_registered_components()

    def test_get_health(self):
        """测试获取健康状态"""
        monitor = HealthMonitor()
        monitor.register_check("comp", lambda: HealthCheckResult(
            component="comp", healthy=True, message="OK", timestamp=time.time()
        ))
        monitor.check_all()
        health = monitor.get_health()
        assert "comp" in health
        assert health["comp"]["healthy"] is True

    def test_get_health_single(self):
        """测试获取单个组件健康"""
        monitor = HealthMonitor()
        monitor.register_check("comp", lambda: HealthCheckResult(
            component="comp", healthy=True, message="OK", timestamp=time.time()
        ))
        monitor.check_all()
        health = monitor.get_health("comp")
        assert health["healthy"] is True

    def test_get_registered_components(self):
        """测试获取已注册组件"""
        monitor = HealthMonitor()
        monitor.register_check("a", lambda: HealthCheckResult("a", True, "ok", time.time()))
        monitor.register_check("b", lambda: HealthCheckResult("b", True, "ok", time.time()))
        components = monitor.get_registered_components()
        assert "a" in components
        assert "b" in components


# ============================================================
# 6. RecoveryStrategy 测试
# ============================================================

class TestRecoveryStrategy:
    """恢复策略测试"""

    def test_execute_success(self):
        """测试执行成功"""
        strategy = create_recovery_strategy("test_op", max_retries=2)
        result, error = strategy.execute(lambda: "success")
        assert result == "success"
        assert error is None

    def test_execute_with_retry(self):
        """测试带重试的执行"""
        strategy = create_recovery_strategy("test_op", max_retries=3)
        call_count = [0]

        def func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("fail")
            return "success"

        result, error = strategy.execute(func)
        assert result == "success"
        assert error is None
        assert call_count[0] == 2

    def test_execute_with_fallback(self):
        """测试带回退的执行"""
        strategy = create_recovery_strategy("test_op", max_retries=1, use_fallback=True)
        strategy.fallback_handler.register("test_op", lambda: "fallback")

        result, error = strategy.execute(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert result == "fallback"
        assert error is not None
        assert error.recovery_action == RecoveryAction.FALLBACK
        assert error.recovery_success is True

    def test_execute_all_fail(self):
        """测试全部失败"""
        strategy = create_recovery_strategy("test_op", max_retries=1, use_circuit_breaker=False)
        result, error = strategy.execute(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert result is None
        assert error is not None
        assert error.recovery_success is False

    def test_circuit_breaker_integration(self):
        """测试熔断器集成"""
        strategy = create_recovery_strategy("test_op", max_retries=0, use_circuit_breaker=True)
        strategy.circuit_breaker._failure_threshold = 2

        # 两次失败后熔断
        strategy.execute(lambda: (_ for _ in ()).throw(ValueError("fail")))
        strategy.execute(lambda: (_ for _ in ()).throw(ValueError("fail")))

        # 第三次应被熔断
        result, error = strategy.execute(lambda: "should not reach")
        assert result is None
        assert error is not None
        assert error.recovery_action == RecoveryAction.CIRCUIT_BREAK

    def test_get_stats(self):
        """测试统计"""
        strategy = create_recovery_strategy("test_op", max_retries=1)
        strategy.execute(lambda: "ok")
        stats = strategy.get_stats()
        assert stats["name"] == "test_op"
        assert "retry" in stats


# ============================================================
# 7. RecoveryManager 测试
# ============================================================

class TestRecoveryManager:
    """恢复管理器测试"""

    def test_execute_without_strategy(self):
        """测试无策略时执行"""
        mgr = create_recovery_manager()
        result, error = mgr.execute("op", lambda: "success")
        assert result == "success"
        assert error is None

    def test_execute_with_error_no_strategy(self):
        """测试无策略时出错"""
        mgr = create_recovery_manager()
        result, error = mgr.execute("op", lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert result is None
        assert error is not None
        assert error.error_type == "ValueError"

    def test_execute_with_strategy(self):
        """测试带策略执行"""
        mgr = create_recovery_manager()
        strategy = create_recovery_strategy("test_op", max_retries=2)
        mgr.register_strategy(strategy)

        call_count = [0]
        def func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("fail")
            return "success"

        result, error = mgr.execute("test_op", func)
        assert result == "success"
        assert error is None

    def test_error_history(self):
        """测试错误历史"""
        mgr = create_recovery_manager()
        mgr.execute("op1", lambda: (_ for _ in ()).throw(ValueError("err1")))
        mgr.execute("op2", lambda: (_ for _ in ()).throw(TypeError("err2")))

        history = mgr.get_error_history()
        assert len(history) == 2
        assert history[0]["error_type"] == "ValueError"
        assert history[1]["error_type"] == "TypeError"

    def test_error_history_by_component(self):
        """测试按组件查询错误历史"""
        mgr = create_recovery_manager()
        mgr.execute("comp1", lambda: (_ for _ in ()).throw(ValueError("err1")))
        mgr.execute("comp2", lambda: (_ for _ in ()).throw(ValueError("err2")))
        mgr.execute("comp1", lambda: (_ for _ in ()).throw(ValueError("err3")))

        history = mgr.get_error_history(component="comp1")
        assert len(history) == 2
        assert all(h["component"] == "comp1" for h in history)

    def test_error_count(self):
        """测试错误计数"""
        mgr = create_recovery_manager()
        mgr.execute("op", lambda: (_ for _ in ()).throw(ValueError("err")))
        assert mgr.get_error_count() == 1

    def test_clear_errors(self):
        """测试清空错误"""
        mgr = create_recovery_manager()
        mgr.execute("op", lambda: (_ for _ in ()).throw(ValueError("err")))
        mgr.clear_errors()
        assert mgr.get_error_count() == 0

    def test_register_health_check(self):
        """测试注册健康检查"""
        mgr = create_recovery_manager()
        mgr.register_health_check("db", lambda: HealthCheckResult(
            "db", True, "OK", time.time()
        ))
        health = mgr.check_health("db")
        assert health["healthy"] is True

    def test_check_health_all(self):
        """测试检查所有健康"""
        mgr = create_recovery_manager()
        mgr.register_health_check("c1", lambda: HealthCheckResult("c1", True, "ok", time.time()))
        mgr.register_health_check("c2", lambda: HealthCheckResult("c2", False, "fail", time.time()))
        results = mgr.check_health()
        assert len(results) == 2

    def test_get_system_health(self):
        """测试系统整体健康"""
        mgr = create_recovery_manager()
        mgr.register_health_check("c1", lambda: HealthCheckResult("c1", True, "ok", time.time()))
        mgr.check_health()
        health = mgr.get_system_health()
        assert health["healthy"] is True
        assert health["error_count"] == 0

    def test_get_stats(self):
        """测试统计"""
        mgr = create_recovery_manager()
        strategy = create_recovery_strategy("op")
        mgr.register_strategy(strategy)
        stats = mgr.get_stats()
        assert stats["strategy_count"] == 1
        assert "op" in stats["strategies"]

    def test_global_retry(self):
        """测试全局重试"""
        mgr = create_recovery_manager()
        mgr.set_global_retry(create_retry_policy(max_retries=2, base_delay=0))

        call_count = [0]
        def func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("fail")
            return "success"

        result, error = mgr.execute("any_op", func)
        assert result == "success"
        assert error is None

    def test_remove_strategy(self):
        """测试移除策略"""
        mgr = create_recovery_manager()
        strategy = create_recovery_strategy("op")
        mgr.register_strategy(strategy)
        mgr.remove_strategy("op")
        assert mgr.get_strategy("op") is None


# ============================================================
# 8. 第一性原理测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_resilience_principle(self):
        """第一性原理：弹性 — 从错误中恢复"""
        policy = RetryPolicy(max_retries=3, base_delay=0)
        attempts = [0]

        def flaky_func():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ConnectionError("connection failed")
            return "recovered"

        result, error = policy.execute(flaky_func)
        assert result == "recovered"
        assert error is None
        assert attempts[0] == 3  # 经过3次尝试

    def test_isolation_principle(self):
        """第一性原理：隔离性 — 错误不传播"""
        mgr = create_recovery_manager()

        # 操作A失败
        result_a, error_a = mgr.execute("op_a", lambda: (_ for _ in ()).throw(ValueError("A failed")))
        assert result_a is None
        assert error_a is not None

        # 操作B不受影响
        result_b, error_b = mgr.execute("op_b", lambda: "B success")
        assert result_b == "B success"
        assert error_b is None

    def test_observability_principle(self):
        """第一性原理：可观测性 — 错误被记录"""
        mgr = create_recovery_manager()
        mgr.execute("op1", lambda: (_ for _ in ()).throw(ValueError("error1")))
        mgr.execute("op2", lambda: (_ for _ in ()).throw(TypeError("error2")))

        history = mgr.get_error_history()
        assert len(history) == 2
        # 每个错误都有完整信息
        for err in history:
            assert err["error_id"] is not None
            assert err["error_type"] is not None
            assert err["error_message"] is not None
            assert err["timestamp"] is not None
            assert err["component"] is not None

    def test_graceful_degradation_principle(self):
        """第一性原理：渐进降级 — 回退而非崩溃"""
        strategy = create_recovery_strategy("api_call", max_retries=1, use_fallback=True)
        strategy.fallback_handler.register("api_call", lambda: {"cached": True, "data": []})

        # 主操作失败，但回退成功
        result, error = strategy.execute(
            lambda: (_ for _ in ()).throw(ConnectionError("API down"))
        )
        assert result is not None
        assert result["cached"] is True
        assert error is not None
        assert error.recovery_success is True

    def test_self_healing_principle(self):
        """第一性原理：自愈性 — 熔断器自动恢复"""
        cb = CircuitBreakerPolicy(failure_threshold=1, recovery_timeout=0.1)

        # 熔断
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # 等待恢复
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        # 成功后恢复
        cb.record_success()
        # half_open_max_calls默认为3，需要更多成功
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_circuit_breaker_protection(self):
        """第一性原理：熔断保护 — 防止级联失败"""
        strategy = create_recovery_strategy("protected_op", max_retries=0, use_circuit_breaker=True)
        strategy.circuit_breaker._failure_threshold = 2

        # 前两次失败
        for _ in range(2):
            strategy.execute(lambda: (_ for _ in ()).throw(ValueError("fail")))

        # 第三次被熔断，不执行函数
        executed = [False]
        def func():
            executed[0] = True
            return "result"

        result, error = strategy.execute(func)
        assert result is None
        assert executed[0] is False  # 函数未被调用
        assert error.recovery_action == RecoveryAction.CIRCUIT_BREAK

    def test_retry_then_fallback(self):
        """第一性原理：多层恢复 — 重试失败后回退"""
        strategy = create_recovery_strategy("multi", max_retries=2, use_fallback=True)
        strategy.fallback_handler.register("multi", lambda: "fallback")

        attempts = [0]
        def always_fail():
            attempts[0] += 1
            raise ValueError("always fails")

        result, error = strategy.execute(always_fail)
        assert result == "fallback"
        assert error is not None
        assert error.recovery_action == RecoveryAction.FALLBACK
        # 应该重试了2次（max_retries=2，加上初始共3次）
        assert attempts[0] == 3


# ============================================================
# 9. 边界条件测试
# ============================================================

class TestEdgeCases:
    """边界条件测试"""

    def test_empty_operation_name(self):
        """测试空操作名"""
        mgr = create_recovery_manager()
        result, error = mgr.execute("", lambda: "ok")
        assert result == "ok"
        assert error is None

    def test_none_func(self):
        """测试None函数"""
        mgr = create_recovery_manager()
        result, error = mgr.execute("op", None)
        assert result is None
        assert error is not None

    def test_concurrent_execute(self):
        """测试并发执行"""
        import threading
        mgr = create_recovery_manager()
        errors = []

        def worker():
            try:
                for i in range(20):
                    mgr.execute("op", lambda: i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_large_error_history(self):
        """测试大量错误历史"""
        mgr = create_recovery_manager()
        for i in range(100):
            mgr.execute("op", lambda: (_ for _ in ()).throw(ValueError(f"err_{i}")))
        # 历史有上限
        assert mgr.get_error_count() <= 1000

    def test_health_check_with_details(self):
        """测试带详情的健康检查"""
        monitor = HealthMonitor()
        monitor.register_check("db", lambda: HealthCheckResult(
            component="db",
            healthy=True,
            message="OK",
            timestamp=time.time(),
            details={"connections": 5, "latency_ms": 12},
        ))
        result = monitor.check_one("db")
        assert result.details["connections"] == 5
        assert result.details["latency_ms"] == 12

    def test_recovery_strategy_no_retry_no_fallback(self):
        """测试无重试无回退的策略"""
        strategy = RecoveryStrategy(name="simple")
        result, error = strategy.execute(lambda: "ok")
        assert result == "ok"
        assert error is None

        result, error = strategy.execute(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert result is None
        assert error is not None
        assert error.recovery_action == RecoveryAction.ESCALATE
