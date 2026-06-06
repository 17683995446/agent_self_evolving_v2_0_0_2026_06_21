"""
阶段36: 限流接口标准化 — 验证测试

验证目标:
1. 令牌桶允许突发流量
2. 固定窗口精确计数
3. 滑动窗口平滑限流
4. 分级限流多层检查
5. 统计信息准确
6. 创建便捷函数可用
"""

import sys
import time
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.rate_limiter import (
    RateLimitAlgorithm, RateLimitResult,
    TokenBucketRateLimiter, FixedWindowRateLimiter,
    SlidingWindowRateLimiter, TieredRateLimiter,
    create_rate_limiter,
)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print('='*60)


def test_token_bucket_burst():
    """测试令牌桶突发流量"""
    print_section("令牌桶突发流量")

    limiter = TokenBucketRateLimiter(rate_per_second=1.0, burst_size=5.0)

    # 初始有5个令牌，应允许5个请求
    allowed = 0
    for _ in range(5):
        result = limiter.acquire()
        if result.allowed:
            allowed += 1

    assert allowed == 5
    print(f"突发5个请求: 全部通过")

    # 第6个应被拒绝
    result = limiter.acquire()
    assert result.allowed == False
    print(f"第6个请求: 被拒绝")

    # 等待1秒补充1个令牌
    time.sleep(1.1)
    result = limiter.acquire()
    assert result.allowed == True
    print(f"等待1秒后: 通过")

    print("\n令牌桶突发流量测试通过!")
    return True


def test_fixed_window():
    """测试固定窗口"""
    print_section("固定窗口")

    limiter = FixedWindowRateLimiter(max_requests=3, window_seconds=1.0)

    # 3个请求通过
    for i in range(3):
        result = limiter.acquire()
        assert result.allowed == True, f"请求{i+1}应通过"
    print("前3个请求: 通过")

    # 第4个被拒绝
    result = limiter.acquire()
    assert result.allowed == False
    print("第4个请求: 被拒绝")

    # 等待窗口重置
    time.sleep(1.1)
    result = limiter.acquire()
    assert result.allowed == True
    print("窗口重置后: 通过")

    print("\n固定窗口测试通过!")
    return True


def test_sliding_window():
    """测试滑动窗口"""
    print_section("滑动窗口")

    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=1.0)

    # 3个请求通过
    for i in range(3):
        result = limiter.acquire()
        assert result.allowed == True
    print("前3个请求: 通过")

    # 第4个被拒绝
    result = limiter.acquire()
    assert result.allowed == False
    print("第4个请求: 被拒绝")

    # 等待最早请求滑出窗口
    time.sleep(1.1)
    result = limiter.acquire()
    assert result.allowed == True
    print("最早请求滑出后: 通过")

    print("\n滑动窗口测试通过!")
    return True


def test_tiered_limiter():
    """测试分级限流"""
    print_section("分级限流")

    tiered = TieredRateLimiter()

    # 注册全局和用户级限流
    tiered.register("global", TokenBucketRateLimiter(rate_per_second=10.0, burst_size=5.0))
    tiered.register("user_a", FixedWindowRateLimiter(max_requests=2, window_seconds=60.0))

    # 用户A请求（全局和用户级都检查）
    results = tiered.acquire(["global", "user_a"])
    assert results["global"].allowed == True
    assert results["user_a"].allowed == True
    print("第1次请求: 全局通过, 用户通过")

    # 再请求一次
    results = tiered.acquire(["global", "user_a"])
    assert results["global"].allowed == True
    assert results["user_a"].allowed == True
    print("第2次请求: 全局通过, 用户通过")

    # 第3次，用户级超限
    results = tiered.acquire(["global", "user_a"])
    assert results["global"].allowed == True
    assert results["user_a"].allowed == False
    print("第3次请求: 全局通过, 用户被拒绝")

    print("\n分级限流测试通过!")
    return True


def test_rate_limiter_stats():
    """测试限流器统计"""
    print_section("限流器统计")

    limiter = TokenBucketRateLimiter(rate_per_second=100.0, burst_size=5.0)

    # 5个通过
    for _ in range(5):
        limiter.acquire()
    # 5个拒绝
    for _ in range(5):
        limiter.acquire()

    stats = limiter.get_stats()
    assert stats["total_requests"] == 10
    assert stats["rejected_requests"] == 5
    assert stats["rejection_rate"] == 0.5
    print(f"统计: {stats}")

    print("\n限流器统计测试通过!")
    return True


def test_create_rate_limiter():
    """测试创建便捷函数"""
    print_section("创建便捷函数")

    tb = create_rate_limiter(RateLimitAlgorithm.TOKEN_BUCKET, rate_per_second=10.0, burst_size=20.0)
    assert isinstance(tb, TokenBucketRateLimiter)
    print("创建令牌桶: 成功")

    fw = create_rate_limiter(RateLimitAlgorithm.FIXED_WINDOW, max_requests=100, window_seconds=60.0)
    assert isinstance(fw, FixedWindowRateLimiter)
    print("创建固定窗口: 成功")

    sw = create_rate_limiter(RateLimitAlgorithm.SLIDING_WINDOW, max_requests=100, window_seconds=60.0)
    assert isinstance(sw, SlidingWindowRateLimiter)
    print("创建滑动窗口: 成功")

    print("\n创建便捷函数测试通过!")
    return True


def test_token_bucket_refill():
    """测试令牌桶补充"""
    print_section("令牌桶补充")

    limiter = TokenBucketRateLimiter(rate_per_second=2.0, burst_size=2.0)

    # 消耗所有令牌
    limiter.acquire()
    limiter.acquire()
    result = limiter.acquire()
    assert result.allowed == False
    print("消耗后: 被拒绝")

    # 等待0.5秒，补充1个令牌
    time.sleep(0.6)
    result = limiter.acquire()
    assert result.allowed == True
    print("0.5秒后: 通过（补充1个）")

    print("\n令牌桶补充测试通过!")
    return True


def test_fixed_window_reset():
    """测试固定窗口重置"""
    print_section("固定窗口重置")

    limiter = FixedWindowRateLimiter(max_requests=2, window_seconds=0.5)

    limiter.acquire()
    limiter.acquire()
    assert limiter.acquire().allowed == False
    print("窗口内2个通过，第3个拒绝")

    # 等待窗口过期
    time.sleep(0.6)

    # 新窗口应重置
    assert limiter.acquire().allowed == True
    assert limiter.acquire().allowed == True
    print("新窗口: 2个通过")

    print("\n固定窗口重置测试通过!")
    return True


def test_sliding_window_cleanup():
    """测试滑动窗口清理"""
    print_section("滑动窗口清理")

    limiter = SlidingWindowRateLimiter(max_requests=100, window_seconds=0.1)

    # 大量请求
    for _ in range(50):
        limiter.acquire()

    stats = limiter.get_stats()
    assert stats["current_requests"] == 50
    print(f"当前请求数: {stats['current_requests']}")

    # 等待过期
    time.sleep(0.15)

    # 再请求一次触发清理
    limiter.acquire()
    stats = limiter.get_stats()
    assert stats["current_requests"] == 1  # 清理后只剩1个
    print(f"清理后请求数: {stats['current_requests']}")

    print("\n滑动窗口清理测试通过!")
    return True


def test_tiered_all():
    """测试分级限流全部层级"""
    print_section("分级限流全部层级")

    tiered = TieredRateLimiter()
    tiered.register("api", TokenBucketRateLimiter(rate_per_second=5.0, burst_size=3.0))
    tiered.register("db", TokenBucketRateLimiter(rate_per_second=2.0, burst_size=2.0))

    # 全部层级检查
    results = tiered.acquire_all()
    assert all(r.allowed for r in results.values())
    print(f"全部层级通过: {results}")

    # 多次请求直到某个层级拒绝
    for _ in range(5):
        results = tiered.acquire_all()

    # DB层级应已超限
    assert results["db"].allowed == False
    print(f"DB层级超限: {results['db'].allowed}")

    print("\n分级限流全部层级测试通过!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("阶段36: 限流接口标准化 — 验证测试")
    print("="*60)

    tests = [
        test_token_bucket_burst,
        test_fixed_window,
        test_sliding_window,
        test_tiered_limiter,
        test_rate_limiter_stats,
        test_create_rate_limiter,
        test_token_bucket_refill,
        test_fixed_window_reset,
        test_sliding_window_cleanup,
        test_tiered_all,
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
