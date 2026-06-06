"""
阶段37: 重试接口标准化 — 验证测试

验证目标:
1. 成功时立即返回不重试
2. 失败时按策略重试
3. 不可重试异常直接失败
4. 退避策略计算正确
5. 装饰器自动重试
6. 统计信息准确
"""

import sys
import time
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.retry import (
    BackoffStrategy, RetryPolicy, RetryResult, RetryExecutor,
    retryable, with_retry,
)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print('='*60)


def test_success_no_retry():
    """测试成功不重试"""
    print_section("成功不重试")

    policy = RetryPolicy(max_retries=3)
    executor = RetryExecutor(policy)

    def success_op():
        return 42

    result = executor.execute(success_op)
    assert result.success == True
    assert result.result == 42
    assert result.attempts == 1  # 只执行1次
    print(f"成功结果: {result.result}, 尝试次数: {result.attempts}")

    print("\n成功不重试测试通过!")
    return True


def test_retry_on_failure():
    """测试失败重试"""
    print_section("失败重试")

    policy = RetryPolicy(max_retries=2, base_delay_ms=10.0)
    executor = RetryExecutor(policy)

    call_count = [0]

    def flaky_op():
        call_count[0] += 1
        if call_count[0] < 3:
            raise ValueError("Transient error")
        return "success"

    result = executor.execute(flaky_op)
    assert result.success == True
    assert result.result == "success"
    assert result.attempts == 3  # 2次失败 + 1次成功
    print(f"成功结果: {result.result}, 尝试次数: {result.attempts}")

    print("\n失败重试测试通过!")
    return True


def test_max_retries_exceeded():
    """测试超过最大重试次数"""
    print_section("超过最大重试次数")

    policy = RetryPolicy(max_retries=2, base_delay_ms=10.0)
    executor = RetryExecutor(policy)

    def always_fail():
        raise RuntimeError("Always fails")

    result = executor.execute(always_fail)
    assert result.success == False
    assert result.attempts == 3  # 初始 + 2次重试
    assert result.error is not None
    print(f"失败, 尝试次数: {result.attempts}, 错误: {result.last_error}")

    print("\n超过最大重试次数测试通过!")
    return True


def test_non_retryable_exception():
    """测试不可重试异常"""
    print_section("不可重试异常")

    policy = RetryPolicy(
        max_retries=3,
        base_delay_ms=10.0,
        retryable_exceptions=[ValueError],
    )
    executor = RetryExecutor(policy)

    def raises_type_error():
        raise TypeError("Not retryable")

    result = executor.execute(raises_type_error)
    assert result.success == False
    assert result.attempts == 1  # 只执行1次，不重试
    print(f"不可重试异常, 尝试次数: {result.attempts}")

    print("\n不可重试异常测试通过!")
    return True


def test_backoff_strategies():
    """测试退避策略"""
    print_section("退避策略")

    # 固定
    fixed = RetryPolicy(backoff_strategy=BackoffStrategy.FIXED, base_delay_ms=100.0)
    assert fixed.calculate_delay(0) == 100.0
    assert fixed.calculate_delay(2) == 100.0
    print(f"固定退避: {fixed.calculate_delay(2)}ms")

    # 线性
    linear = RetryPolicy(backoff_strategy=BackoffStrategy.LINEAR, base_delay_ms=100.0)
    assert linear.calculate_delay(0) == 100.0
    assert linear.calculate_delay(1) == 200.0
    assert linear.calculate_delay(2) == 300.0
    print(f"线性退避(attempt=2): {linear.calculate_delay(2)}ms")

    # 指数
    exp = RetryPolicy(backoff_strategy=BackoffStrategy.EXPONENTIAL, base_delay_ms=100.0)
    assert exp.calculate_delay(0) == 100.0
    assert exp.calculate_delay(1) == 200.0
    assert exp.calculate_delay(2) == 400.0
    print(f"指数退避(attempt=2): {exp.calculate_delay(2)}ms")

    # 上限
    capped = RetryPolicy(
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        base_delay_ms=100.0,
        max_delay_ms=500.0,
    )
    assert capped.calculate_delay(10) == 500.0  # 被上限截断
    print(f"上限退避(attempt=10): {capped.calculate_delay(10)}ms")

    print("\n退避策略测试通过!")
    return True


def test_retry_decorator():
    """测试重试装饰器"""
    print_section("重试装饰器")

    call_count = [0]

    @retryable(RetryPolicy(max_retries=2, base_delay_ms=10.0))
    def decorated_function():
        call_count[0] += 1
        if call_count[0] < 2:
            raise ValueError("Retry me")
        return "done"

    result = decorated_function()
    assert result == "done"
    assert call_count[0] == 2
    print(f"装饰器结果: {result}, 调用次数: {call_count[0]}")

    # 统计
    stats = decorated_function.get_retry_stats()
    assert stats["total_attempts"] == 2
    assert stats["total_successes"] == 1
    print(f"装饰器统计: {stats}")

    print("\n重试装饰器测试通过!")
    return True


def test_with_retry_convenience():
    """测试便捷函数"""
    print_section("便捷函数")

    call_count = [0]

    def operation():
        call_count[0] += 1
        if call_count[0] < 2:
            raise ConnectionError("Network error")
        return "connected"

    result = with_retry(
        operation,
        max_retries=3,
        base_delay_ms=10.0,
        retryable_exceptions=[ConnectionError],
    )

    assert result.success == True
    assert result.result == "connected"
    print(f"便捷函数结果: {result.result}, 尝试: {result.attempts}")

    print("\n便捷函数测试通过!")
    return True


def test_total_timeout():
    """测试总超时"""
    print_section("总超时")

    policy = RetryPolicy(
        max_retries=100,
        base_delay_ms=100.0,
        total_timeout_ms=150.0,
    )
    executor = RetryExecutor(policy)

    def slow_fail():
        raise ValueError("fail")

    start = time.time()
    result = executor.execute(slow_fail)
    elapsed = (time.time() - start) * 1000

    assert result.success == False
    assert elapsed < 500  # 应在超时前结束（允许较大误差）
    print(f"总超时触发, 耗时: {elapsed:.0f}ms, 尝试: {result.attempts}")

    print("\n总超时测试通过!")
    return True


def test_retry_stats():
    """测试重试统计"""
    print_section("重试统计")

    policy = RetryPolicy(max_retries=1, base_delay_ms=10.0)
    executor = RetryExecutor(policy)

    # 成功
    executor.execute(lambda: "ok")
    # 失败
    executor.execute(lambda: (_ for _ in ()).throw(ValueError()))
    # 成功
    executor.execute(lambda: "ok2")

    stats = executor.get_stats()
    # total_attempts = 1(成功) + 2(失败重试1次) + 1(成功) = 4
    assert stats["total_attempts"] == 4
    assert stats["total_successes"] == 2
    assert stats["total_failures"] == 1
    assert abs(stats["success_rate"] - 2.0 / 4.0) < 0.01
    print(f"统计: {stats}")

    print("\n重试统计测试通过!")
    return True


def test_retry_result_structure():
    """测试结果结构"""
    print_section("结果结构")

    result = RetryResult(
        success=True,
        result="data",
        attempts=2,
        total_time_ms=50.0,
    )
    assert result.success == True
    assert result.result == "data"
    assert result.attempts == 2
    print(f"成功结果: {result}")

    fail_result = RetryResult(
        success=False,
        error=ValueError("test"),
        last_error="test",
    )
    assert fail_result.success == False
    assert fail_result.last_error == "test"
    print(f"失败结果: {fail_result}")

    print("\n结果结构测试通过!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("阶段37: 重试接口标准化 — 验证测试")
    print("="*60)

    tests = [
        test_success_no_retry,
        test_retry_on_failure,
        test_max_retries_exceeded,
        test_non_retryable_exception,
        test_backoff_strategies,
        test_retry_decorator,
        test_with_retry_convenience,
        test_total_timeout,
        test_retry_stats,
        test_retry_result_structure,
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
