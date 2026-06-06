"""
阶段34: 缓存接口标准化 — 验证测试

验证目标:
1. 基本get/set/delete/clear工作正常
2. TTL过期自动失效
3. 淘汰策略正确（LRU/LFU/FIFO）
4. 统计信息准确（命中率）
5. 缓存装饰器自动缓存
6. 线程安全
"""

import sys
import time
import threading
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.cache import (
    EvictionPolicy, MemoryCache, LRUCache, CacheEntry,
    cached, create_cache,
)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print('='*60)


def test_basic_cache():
    """测试基本缓存操作"""
    print_section("基本缓存操作")

    cache = MemoryCache(max_size=100)

    # set和get
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    print(f"get a: {cache.get('a')}, get b: {cache.get('b')}")

    # 不存在的key
    assert cache.get("c") is None
    print("get c (不存在): None")

    # contains
    assert cache.contains("a") == True
    assert cache.contains("c") == False
    print("contains a: True, contains c: False")

    # delete
    assert cache.delete("a") == True
    assert cache.get("a") is None
    print("delete a后 get a: None")

    # size
    assert cache.size() == 1
    print(f"size: {cache.size()}")

    # clear
    cache.clear()
    assert cache.size() == 0
    print("clear后 size: 0")

    print("\n基本缓存操作测试通过!")
    return True


def test_ttl_expiration():
    """测试TTL过期"""
    print_section("TTL过期")

    cache = MemoryCache(max_size=100)

    # 设置0.1秒TTL
    cache.set("x", "value", ttl_seconds=0.1)
    assert cache.get("x") == "value"
    print("刚设置 get x: value")

    # 等待过期
    time.sleep(0.15)
    assert cache.get("x") is None
    print("0.15秒后 get x: None")

    # 默认TTL
    cache2 = MemoryCache(max_size=100, default_ttl_seconds=0.1)
    cache2.set("y", "value")
    assert cache2.get("y") == "value"
    time.sleep(0.15)
    assert cache2.get("y") is None
    print("默认TTL 0.1秒后 get y: None")

    print("\nTTL过期测试通过!")
    return True


def test_lru_eviction():
    """测试LRU淘汰"""
    print_section("LRU淘汰")

    cache = MemoryCache(max_size=3, policy=EvictionPolicy.LRU)

    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    # 访问a，使其变为最近使用
    cache.get("a")

    # 添加d，应淘汰b（最久未使用）
    cache.set("d", 4)

    assert cache.contains("a") == True
    assert cache.contains("b") == False  # 被淘汰
    assert cache.contains("c") == True
    assert cache.contains("d") == True
    print(f"淘汰后: a={cache.contains('a')}, b={cache.contains('b')}, c={cache.contains('c')}, d={cache.contains('d')}")

    print("\nLRU淘汰测试通过!")
    return True


def test_fifo_eviction():
    """测试FIFO淘汰"""
    print_section("FIFO淘汰")

    cache = MemoryCache(max_size=3, policy=EvictionPolicy.FIFO)

    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    # 访问a，但FIFO不更新顺序
    cache.get("a")

    # 添加d，应淘汰a（最早进入）
    cache.set("d", 4)

    assert cache.contains("a") == False  # 被淘汰
    assert cache.contains("b") == True
    assert cache.contains("c") == True
    assert cache.contains("d") == True
    print(f"FIFO淘汰后: a={cache.contains('a')}, b={cache.contains('b')}, c={cache.contains('c')}, d={cache.contains('d')}")

    print("\nFIFO淘汰测试通过!")
    return True


def test_lfu_eviction():
    """测试LFU淘汰"""
    print_section("LFU淘汰")

    cache = MemoryCache(max_size=3, policy=EvictionPolicy.LFU)

    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    # 多次访问a和b
    cache.get("a")
    cache.get("a")
    cache.get("b")

    # 添加d，应淘汰c（访问次数最少）
    cache.set("d", 4)

    assert cache.contains("a") == True
    assert cache.contains("b") == True
    assert cache.contains("c") == False  # 被淘汰
    assert cache.contains("d") == True
    print(f"LFU淘汰后: a={cache.contains('a')}, b={cache.contains('b')}, c={cache.contains('c')}, d={cache.contains('d')}")

    print("\nLFU淘汰测试通过!")
    return True


def test_cache_stats():
    """测试缓存统计"""
    print_section("缓存统计")

    cache = MemoryCache(max_size=100)

    # 未命中
    cache.get("missing")

    # 命中
    cache.set("key", "value")
    cache.get("key")
    cache.get("key")

    stats = cache.get_stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 2.0 / 3.0
    assert stats["size"] == 1
    print(f"统计: {stats}")

    print("\n缓存统计测试通过!")
    return True


def test_lru_cache_ordered():
    """测试LRU有序缓存"""
    print_section("LRU有序缓存")

    cache = LRUCache(max_size=3)

    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    # 访问a
    cache.get("a")

    # 添加d
    cache.set("d", 4)

    assert cache.contains("a") == True
    assert cache.contains("b") == False
    print(f"LRUCache淘汰后: a={cache.contains('a')}, b={cache.contains('b')}")

    # 更新已存在key
    cache.set("a", 10)
    assert cache.get("a") == 10
    print(f"更新后 get a: {cache.get('a')}")

    print("\nLRU有序缓存测试通过!")
    return True


def test_cache_decorator():
    """测试缓存装饰器"""
    print_section("缓存装饰器")

    cache = MemoryCache(max_size=100)
    call_count = [0]

    @cached(cache, ttl_seconds=1.0)
    def expensive_function(x):
        call_count[0] += 1
        return x * x

    # 第一次调用
    result1 = expensive_function(5)
    assert result1 == 25
    assert call_count[0] == 1
    print(f"第一次调用: {result1}, 调用次数: {call_count[0]}")

    # 第二次调用（应从缓存获取）
    result2 = expensive_function(5)
    assert result2 == 25
    assert call_count[0] == 1  # 未增加
    print(f"第二次调用: {result2}, 调用次数: {call_count[0]}")

    # 不同参数
    result3 = expensive_function(6)
    assert result3 == 36
    assert call_count[0] == 2
    print(f"不同参数调用: {result3}, 调用次数: {call_count[0]}")

    print("\n缓存装饰器测试通过!")
    return True


def test_create_cache():
    """测试便捷创建函数"""
    print_section("便捷创建函数")

    lru = create_cache(max_size=50, policy=EvictionPolicy.LRU)
    assert isinstance(lru, LRUCache)
    print(f"创建LRU缓存: {type(lru).__name__}")

    fifo = create_cache(max_size=50, policy=EvictionPolicy.FIFO)
    assert isinstance(fifo, MemoryCache)
    print(f"创建FIFO缓存: {type(fifo).__name__}")

    print("\n便捷创建函数测试通过!")
    return True


def test_thread_safety():
    """测试线程安全"""
    print_section("线程安全")

    cache = MemoryCache(max_size=1000)
    errors = []

    def writer():
        try:
            for i in range(100):
                cache.set(f"key_{i}", i)
        except Exception as e:
            errors.append(e)

    def reader():
        try:
            for i in range(100):
                cache.get(f"key_{i}")
        except Exception as e:
            errors.append(e)

    threads = []
    for _ in range(5):
        threads.append(threading.Thread(target=writer))
        threads.append(threading.Thread(target=reader))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    print(f"10线程并发读写: 0 错误")

    print("\n线程安全测试通过!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("阶段34: 缓存接口标准化 — 验证测试")
    print("="*60)

    tests = [
        test_basic_cache,
        test_ttl_expiration,
        test_lru_eviction,
        test_fifo_eviction,
        test_lfu_eviction,
        test_cache_stats,
        test_lru_cache_ordered,
        test_cache_decorator,
        test_create_cache,
        test_thread_safety,
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
