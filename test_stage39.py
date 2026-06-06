"""
阶段39测试: 超时接口标准化
"""
import sys
sys.path.insert(0, '/workspace')

import time
import threading
from self_evolving_agent.core.timeout import (
    TimeoutController, TimeoutStrategy, TimeoutAction,
    TimeoutResult, timeout_protected, with_timeout, create_timeout_controller
)


def test_timeout_basic():
    """测试基本超时功能"""
    controller = TimeoutController(timeout_ms=50)

    # 快速操作，不应超时
    result = controller.execute(lambda: "done")
    assert result.success is True
    assert result.result == "done"
    assert result.timed_out is False
    print("  [test_timeout_basic] 快速操作不超时 ✓")

    # 慢操作，应超时
    def slow_op():
        time.sleep(0.2)
        return "done"

    result = controller.execute(slow_op)
    assert result.success is False
    assert result.timed_out is True
    assert "timed out" in str(result.error).lower()
    print("  [test_timeout_basic] 慢操作超时 ✓")

    controller.shutdown()


def test_timeout_action_raise():
    """测试超时抛出异常"""
    controller = TimeoutController(timeout_ms=50, action=TimeoutAction.RAISE)

    result = controller.execute(lambda: time.sleep(0.2) or "done")
    assert result.timed_out is True
    assert isinstance(result.error, TimeoutError)
    print("  [test_timeout_action_raise] 超时抛出异常 ✓")
    controller.shutdown()


def test_timeout_action_return_none():
    """测试超时返回None"""
    controller = TimeoutController(timeout_ms=50, action=TimeoutAction.RETURN_NONE)

    result = controller.execute(lambda: time.sleep(0.2) or "done")
    assert result.timed_out is True
    assert result.success is True
    assert result.result is None
    print("  [test_timeout_action_return_none] 超时返回None ✓")
    controller.shutdown()


def test_timeout_action_fallback():
    """测试超时降级"""
    controller = TimeoutController(
        timeout_ms=50,
        action=TimeoutAction.FALLBACK,
        fallback_fn=lambda: "fallback_value"
    )

    result = controller.execute(lambda: time.sleep(0.2) or "done")
    assert result.timed_out is True
    assert result.success is True
    assert result.result == "fallback_value"
    print("  [test_timeout_action_fallback] 超时降级 ✓")
    controller.shutdown()


def test_timeout_decorator():
    """测试超时装饰器"""
    call_count = 0

    @timeout_protected(timeout_ms=50)
    def my_slow_func():
        nonlocal call_count
        call_count += 1
        time.sleep(0.2)
        return "result"

    try:
        my_slow_func()
        assert False, "应抛出TimeoutError"
    except TimeoutError:
        pass

    assert call_count >= 1
    print("  [test_timeout_decorator] 装饰器超时 ✓")


def test_with_timeout():
    """测试便捷函数"""
    result = with_timeout(lambda: time.sleep(0.2) or "done", timeout_ms=50)
    assert result.timed_out is True
    print("  [test_with_timeout] 便捷函数 ✓")


def test_timeout_stats():
    """测试统计信息"""
    controller = TimeoutController(timeout_ms=50)

    # 1成功1超时
    controller.execute(lambda: "ok")
    controller.execute(lambda: time.sleep(0.2) or "done")

    stats = controller.get_stats()
    assert stats["total_calls"] == 2
    assert stats["total_timeouts"] == 1
    assert stats["total_successes"] == 1
    assert stats["timeout_rate"] == 0.5
    print("  [test_timeout_stats] 统计信息 ✓")
    controller.shutdown()


def test_dynamic_timeout():
    """测试动态超时策略"""
    controller = TimeoutController(
        timeout_ms=100,
        strategy=TimeoutStrategy.DYNAMIC
    )

    # 先积累历史记录
    for _ in range(15):
        controller.execute(lambda: time.sleep(0.01) or "ok")

    # 动态超时应该基于历史调整
    stats = controller.get_stats()
    assert stats["strategy"] == "dynamic"
    assert stats["total_successes"] == 15
    print("  [test_dynamic_timeout] 动态超时策略 ✓")
    controller.shutdown()


def test_adaptive_timeout():
    """测试自适应超时策略"""
    controller = TimeoutController(
        timeout_ms=100,
        strategy=TimeoutStrategy.ADAPTIVE
    )

    # 积累调用
    for _ in range(25):
        controller.execute(lambda: time.sleep(0.01) or "ok")

    stats = controller.get_stats()
    assert stats["strategy"] == "adaptive"
    print("  [test_adaptive_timeout] 自适应超时策略 ✓")
    controller.shutdown()


def test_concurrent_timeout():
    """测试并发超时安全"""
    controller = TimeoutController(timeout_ms=100)
    results = []
    errors = []

    def worker():
        for _ in range(10):
            try:
                r = controller.execute(lambda: time.sleep(0.01) or "ok")
                results.append(r.success)
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(results) == 30
    assert all(results)
    print("  [test_concurrent_timeout] 并发安全 ✓")
    controller.shutdown()


if __name__ == "__main__":
    print("=" * 60)
    print("阶段39测试: 超时接口标准化")
    print("=" * 60)

    test_timeout_basic()
    test_timeout_action_raise()
    test_timeout_action_return_none()
    test_timeout_action_fallback()
    test_timeout_decorator()
    test_with_timeout()
    test_timeout_stats()
    test_dynamic_timeout()
    test_adaptive_timeout()
    test_concurrent_timeout()

    print("=" * 60)
    print("全部10项测试通过 ✓")
    print("=" * 60)
