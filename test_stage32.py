"""
阶段32: 资源配额管理 — 验证测试

验证目标:
1. 配额申请成功时返回分配记录
2. 配额超限按策略处理（拒绝/等待/降级）
3. 配额释放后可用资源增加
4. 上下文管理器自动释放
5. 所有者资源使用可查询
6. 泄漏检测可发现长期未释放配额
"""

import sys
import time
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.quota import (
    ResourceType, QuotaExceedPolicy, QuotaAllocation,
    QuotaManager, QuotaContext,
)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print('='*60)


def test_basic_allocation():
    """测试基本配额分配"""
    print_section("基本配额分配")

    manager = QuotaManager()
    manager.set_limit(ResourceType.MEMORY, 100.0)

    # 申请50MB
    alloc = manager.allocate(ResourceType.MEMORY, 50.0, "module_a")
    assert alloc is not None
    assert alloc.amount == 50.0
    assert alloc.owner == "module_a"
    assert alloc.resource_type == ResourceType.MEMORY
    print(f"分配: {alloc.amount}MB, 所有者: {alloc.owner}")

    # 检查使用
    assert manager.get_used(ResourceType.MEMORY) == 50.0
    assert manager.get_available(ResourceType.MEMORY) == 50.0
    print(f"已用: {manager.get_used(ResourceType.MEMORY)}, 可用: {manager.get_available(ResourceType.MEMORY)}")

    # 释放
    assert manager.release(alloc.allocation_id) == True
    assert manager.get_used(ResourceType.MEMORY) == 0.0
    print(f"释放后已用: {manager.get_used(ResourceType.MEMORY)}")

    print("\n基本配额分配测试通过!")
    return True


def test_reject_policy():
    """测试拒绝策略"""
    print_section("拒绝策略")

    manager = QuotaManager()
    manager.set_limit(ResourceType.MEMORY, 100.0)

    # 先申请80MB
    alloc1 = manager.allocate(ResourceType.MEMORY, 80.0, "user1")
    assert alloc1 is not None

    # 再申请30MB，应被拒绝
    alloc2 = manager.allocate(ResourceType.MEMORY, 30.0, "user2",
                              policy=QuotaExceedPolicy.REJECT)
    assert alloc2 is None
    print(f"申请80MB成功，再申请30MB被拒绝: True")

    # 释放后应可申请
    manager.release(alloc1.allocation_id)
    alloc3 = manager.allocate(ResourceType.MEMORY, 30.0, "user2")
    assert alloc3 is not None
    print(f"释放后申请30MB成功: True")

    print("\n拒绝策略测试通过!")
    return True


def test_downgrade_policy():
    """测试降级策略"""
    print_section("降级策略")

    manager = QuotaManager()
    manager.set_limit(ResourceType.MEMORY, 100.0)

    # 先申请70MB
    alloc1 = manager.allocate(ResourceType.MEMORY, 70.0, "user1")

    # 申请50MB，降级策略应分配可用部分（30MB）
    alloc2 = manager.allocate(ResourceType.MEMORY, 50.0, "user2",
                              policy=QuotaExceedPolicy.DOWNGRADE)
    assert alloc2 is not None
    assert alloc2.amount == 30.0  # 只分配可用部分
    print(f"申请50MB，降级分配: {alloc2.amount}MB")

    print("\n降级策略测试通过!")
    return True


def test_wait_policy():
    """测试等待策略"""
    print_section("等待策略")

    manager = QuotaManager()
    manager.set_limit(ResourceType.MEMORY, 100.0)

    # 先申请90MB
    alloc1 = manager.allocate(ResourceType.MEMORY, 90.0, "user1")

    # 在另一个线程等待并释放
    import threading
    result = [None]

    def waiter():
        result[0] = manager.allocate(ResourceType.MEMORY, 30.0, "user2",
                                     policy=QuotaExceedPolicy.WAIT,
                                     timeout_ms=500)

    def releaser():
        time.sleep(0.1)
        manager.release(alloc1.allocation_id)

    t1 = threading.Thread(target=waiter)
    t2 = threading.Thread(target=releaser)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert result[0] is not None
    assert result[0].amount == 30.0
    print(f"等待后成功分配: {result[0].amount}MB")

    print("\n等待策略测试通过!")
    return True


def test_wait_timeout():
    """测试等待超时"""
    print_section("等待超时")

    manager = QuotaManager()
    manager.set_limit(ResourceType.MEMORY, 100.0)

    # 申请全部配额
    alloc = manager.allocate(ResourceType.MEMORY, 100.0, "user1")

    # 等待100ms，应超时
    start = time.time()
    result = manager.allocate(ResourceType.MEMORY, 10.0, "user2",
                              policy=QuotaExceedPolicy.WAIT,
                              timeout_ms=100)
    elapsed = (time.time() - start) * 1000

    assert result is None
    assert elapsed >= 90  # 允许10ms误差
    print(f"等待超时: True, 耗时: {elapsed:.0f}ms")

    print("\n等待超时测试通过!")
    return True


def test_context_manager():
    """测试上下文管理器"""
    print_section("上下文管理器")

    manager = QuotaManager()
    manager.set_limit(ResourceType.MEMORY, 100.0)

    # 使用with语句
    with QuotaContext(manager, ResourceType.MEMORY, 50.0, "module_x") as alloc:
        assert alloc is not None
        assert manager.get_used(ResourceType.MEMORY) == 50.0
        print(f"with内已用: {manager.get_used(ResourceType.MEMORY)}")

    # 退出后自动释放
    assert manager.get_used(ResourceType.MEMORY) == 0.0
    print(f"with后已用: {manager.get_used(ResourceType.MEMORY)}")

    # 异常时也应释放
    try:
        with QuotaContext(manager, ResourceType.MEMORY, 30.0, "module_y") as alloc:
            assert manager.get_used(ResourceType.MEMORY) == 30.0
            raise ValueError("Test error")
    except ValueError:
        pass

    assert manager.get_used(ResourceType.MEMORY) == 0.0
    print(f"异常后已用: {manager.get_used(ResourceType.MEMORY)}")

    print("\n上下文管理器测试通过!")
    return True


def test_owner_usage():
    """测试所有者资源使用"""
    print_section("所有者资源使用")

    manager = QuotaManager()
    manager.set_limit(ResourceType.MEMORY, 100.0)
    manager.set_limit(ResourceType.THREAD, 10.0)

    manager.allocate(ResourceType.MEMORY, 30.0, "owner_a")
    manager.allocate(ResourceType.MEMORY, 20.0, "owner_a")
    manager.allocate(ResourceType.THREAD, 5.0, "owner_a")
    manager.allocate(ResourceType.MEMORY, 10.0, "owner_b")

    usage_a = manager.get_owner_usage("owner_a")
    assert usage_a[ResourceType.MEMORY] == 50.0
    assert usage_a[ResourceType.THREAD] == 5.0
    print(f"owner_a使用: {usage_a}")

    usage_b = manager.get_owner_usage("owner_b")
    assert usage_b[ResourceType.MEMORY] == 10.0
    print(f"owner_b使用: {usage_b}")

    # 释放owner_a全部
    count = manager.release_all("owner_a")
    assert count == 3
    assert manager.get_owner_usage("owner_a") == {}
    print(f"释放owner_a全部: {count} 个")

    print("\n所有者资源使用测试通过!")
    return True


def test_all_usage():
    """测试全部资源使用"""
    print_section("全部资源使用")

    manager = QuotaManager()
    manager.set_limit(ResourceType.MEMORY, 100.0)
    manager.set_limit(ResourceType.CPU_TIME, 1000.0)

    manager.allocate(ResourceType.MEMORY, 40.0, "user1")
    manager.allocate(ResourceType.MEMORY, 30.0, "user2")

    usage = manager.get_all_usage()
    assert usage[ResourceType.MEMORY]["used"] == 70.0
    assert usage[ResourceType.MEMORY]["limit"] == 100.0
    assert usage[ResourceType.CPU_TIME]["used"] == 0.0
    assert usage[ResourceType.CPU_TIME]["limit"] == 1000.0
    print(f"全部使用: {usage}")

    print("\n全部资源使用测试通过!")
    return True


def test_exceed_callback():
    """测试超限回调"""
    print_section("超限回调")

    manager = QuotaManager()
    manager.set_limit(ResourceType.MEMORY, 50.0)

    events = []

    def callback(resource_type, owner, requested, available):
        events.append((resource_type.value, owner, requested, available))

    manager.add_exceed_callback(callback)

    # 申请全部
    manager.allocate(ResourceType.MEMORY, 50.0, "user1")

    # 再申请，触发超限
    manager.allocate(ResourceType.MEMORY, 10.0, "user2", policy=QuotaExceedPolicy.REJECT)

    assert len(events) == 1
    assert events[0] == ("memory", "user2", 10.0, 0.0)
    print(f"超限事件: {events}")

    print("\n超限回调测试通过!")
    return True


def test_leak_detection():
    """测试泄漏检测"""
    print_section("泄漏检测")

    manager = QuotaManager()
    manager.set_limit(ResourceType.MEMORY, 100.0)

    # 申请但不释放
    alloc = manager.allocate(ResourceType.MEMORY, 10.0, "leaky_module")

    # 检查泄漏（设置很短的超时以便测试）
    # 由于刚分配，不会检测到泄漏
    leaks = manager.check_leaks(max_age_seconds=0.001)
    time.sleep(0.01)
    leaks = manager.check_leaks(max_age_seconds=0.001)

    assert len(leaks) >= 1
    assert leaks[0].owner == "leaky_module"
    print(f"检测到泄漏: {len(leaks)} 个, 所有者: {leaks[0].owner}")

    print("\n泄漏检测测试通过!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("阶段32: 资源配额管理 — 验证测试")
    print("="*60)

    tests = [
        test_basic_allocation,
        test_reject_policy,
        test_downgrade_policy,
        test_wait_policy,
        test_wait_timeout,
        test_context_manager,
        test_owner_usage,
        test_all_usage,
        test_exceed_callback,
        test_leak_detection,
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
