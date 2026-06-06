"""
阶段38测试: 熔断接口标准化
"""
import sys
sys.path.insert(0, '/workspace')

import time
import threading
from self_evolving_agent.core.circuit_breaker import (
    CircuitBreaker, CircuitState, CircuitBreakerAction,
    CircuitBreakerResult, circuit_breaker_protected, create_circuit_breaker
)


def test_circuit_breaker_states():
    """测试熔断器三种状态转换"""
    cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout_ms=100, success_threshold=1)

    # 初始状态：CLOSED
    assert cb.state == CircuitState.CLOSED

    # 连续失败3次，达到阈值，应变为OPEN
    for i in range(3):
        result = cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        assert result.success is False

    assert cb.state == CircuitState.OPEN
    print("  [test_circuit_breaker_states] 状态转换: CLOSED -> OPEN ✓")

    # 等待恢复超时
    time.sleep(0.15)

    # 下一次调用应进入HALF_OPEN，成功阈值1，成功后直接CLOSED
    result = cb.call(lambda: "success")
    assert cb.state == CircuitState.CLOSED
    assert result.success is True
    print("  [test_circuit_breaker_states] 状态转换: OPEN -> HALF_OPEN -> CLOSED ✓")


def test_circuit_open_fast_fail():
    """测试OPEN状态快速失败"""
    cb = CircuitBreaker(name="fast_fail", failure_threshold=2, recovery_timeout_ms=5000)

    # 触发熔断
    for _ in range(2):
        cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

    assert cb.state == CircuitState.OPEN

    # 快速失败，不执行操作
    result = cb.call(lambda: "should_not_execute")
    assert result.success is False
    assert "is OPEN" in str(result.error)
    print("  [test_circuit_open_fast_fail] OPEN状态快速失败 ✓")


def test_circuit_fallback():
    """测试降级fallback"""
    cb = CircuitBreaker(
        name="fallback_test",
        failure_threshold=2,
        recovery_timeout_ms=5000,
        action=CircuitBreakerAction.FALLBACK,
        fallback_fn=lambda *args, **kwargs: "fallback_result"
    )

    # 触发熔断
    for _ in range(2):
        cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

    assert cb.state == CircuitState.OPEN

    # 应返回降级结果
    result = cb.call(lambda: "original")
    assert result.success is True
    assert result.result == "fallback_result"
    assert result.from_fallback is True
    print("  [test_circuit_fallback] 降级fallback ✓")


def test_half_open_recovery():
    """测试半开状态恢复"""
    cb = CircuitBreaker(
        name="recovery",
        failure_threshold=2,
        recovery_timeout_ms=50,
        half_open_max_calls=5,
        success_threshold=2
    )

    # 触发熔断
    for _ in range(2):
        cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

    assert cb.state == CircuitState.OPEN

    # 等待恢复
    time.sleep(0.08)

    # 半开状态成功2次，应恢复CLOSED
    for _ in range(2):
        result = cb.call(lambda: "ok")
        assert result.success is True

    assert cb.state == CircuitState.CLOSED
    print("  [test_half_open_recovery] 半开状态恢复 ✓")


def test_half_open_reopen():
    """测试半开状态再次失败重新打开"""
    cb = CircuitBreaker(
        name="reopen",
        failure_threshold=2,
        recovery_timeout_ms=50,
        half_open_max_calls=5,
        success_threshold=2
    )

    # 触发熔断
    for _ in range(2):
        cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

    assert cb.state == CircuitState.OPEN

    # 等待恢复
    time.sleep(0.08)

    # 半开状态再次失败
    result = cb.call(lambda: (_ for _ in ()).throw(Exception("fail again")))
    assert result.success is False
    assert cb.state == CircuitState.OPEN
    print("  [test_half_open_reopen] 半开状态重新打开 ✓")


def test_circuit_stats():
    """测试统计信息"""
    cb = CircuitBreaker(name="stats_test", failure_threshold=5)

    # 3成功2失败
    for _ in range(3):
        cb.call(lambda: "success")
    for _ in range(2):
        cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

    stats = cb.get_stats()
    assert stats["name"] == "stats_test"
    assert stats["total_calls"] == 5
    assert stats["total_successes"] == 3
    assert stats["total_failures"] == 2
    assert stats["failure_rate"] == 0.4
    assert stats["state"] == "closed"
    print("  [test_circuit_stats] 统计信息 ✓")


def test_circuit_decorator():
    """测试装饰器"""
    cb = CircuitBreaker(name="decorator_test", failure_threshold=2)

    @circuit_breaker_protected(breaker=cb)
    def my_operation(x):
        if x < 0:
            raise ValueError("negative")
        return x * 2

    # 正常调用
    assert my_operation(5) == 10

    # 触发熔断
    for _ in range(2):
        try:
            my_operation(-1)
        except ValueError:
            pass

    assert cb.state == CircuitState.OPEN

    # 熔断后调用应抛出异常
    try:
        my_operation(5)
        assert False, "应抛出异常"
    except Exception as e:
        assert "is OPEN" in str(e)

    print("  [test_circuit_decorator] 装饰器 ✓")


def test_circuit_reset():
    """测试手动重置"""
    cb = CircuitBreaker(name="reset", failure_threshold=2)

    for _ in range(2):
        cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

    assert cb.state == CircuitState.OPEN

    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.get_stats()["failure_count"] == 0

    # 重置后可以正常调用
    result = cb.call(lambda: "ok")
    assert result.success is True
    print("  [test_circuit_reset] 手动重置 ✓")


def test_concurrent_access():
    """测试并发访问安全"""
    cb = CircuitBreaker(name="concurrent", failure_threshold=100)

    results = []
    errors = []

    def worker():
        for _ in range(20):
            try:
                r = cb.call(lambda: "ok")
                results.append(r.success)
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(results) == 100
    assert all(results)
    print("  [test_concurrent_access] 并发访问安全 ✓")


def test_create_circuit_breaker():
    """测试便捷创建函数"""
    cb = create_circuit_breaker(name="quick", failure_threshold=10)
    assert cb.name == "quick"
    assert cb.failure_threshold == 10
    assert cb.state == CircuitState.CLOSED
    print("  [test_create_circuit_breaker] 便捷创建 ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("阶段38测试: 熔断接口标准化")
    print("=" * 60)

    test_circuit_breaker_states()
    test_circuit_open_fast_fail()
    test_circuit_fallback()
    test_half_open_recovery()
    test_half_open_reopen()
    test_circuit_stats()
    test_circuit_decorator()
    test_circuit_reset()
    test_concurrent_access()
    test_create_circuit_breaker()

    print("=" * 60)
    print("全部10项测试通过 ✓")
    print("=" * 60)
