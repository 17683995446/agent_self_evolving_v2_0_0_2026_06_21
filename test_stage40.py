"""
阶段40测试: 并发控制接口标准化
"""
import sys
sys.path.insert(0, '/workspace')

import time
import threading
from self_evolving_agent.core.concurrency import (
    RWLock, Semaphore, ConcurrencyController,
    LockPriority, create_rwlock, create_semaphore
)


def test_rwlock_read_concurrent():
    """测试读锁并发"""
    lock = RWLock()
    results = []

    def reader():
        with lock.read_lock():
            results.append("read")
            time.sleep(0.05)

    threads = [threading.Thread(target=reader) for _ in range(5)]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = (time.time() - start) * 1000

    # 5个读线程并发，总时间应小于串行（250ms）
    assert len(results) == 5
    assert elapsed < 150, f"读锁未并发: {elapsed}ms"
    print("  [test_rwlock_read_concurrent] 读锁并发 ✓")


def test_rwlock_write_exclusive():
    """测试写锁互斥"""
    lock = RWLock()
    results = []

    def writer(n):
        with lock.write_lock():
            results.append(f"write{n}")
            time.sleep(0.05)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(3)]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = (time.time() - start) * 1000

    # 3个写线程串行，总时间应大于100ms
    assert len(results) == 3
    assert elapsed > 100, f"写锁未互斥: {elapsed}ms"
    print("  [test_rwlock_write_exclusive] 写锁互斥 ✓")


def test_rwlock_read_write_blocking():
    """测试读写互斥"""
    lock = RWLock()
    order = []

    def reader():
        with lock.read_lock():
            order.append("read_start")
            time.sleep(0.1)
            order.append("read_end")

    def writer():
        time.sleep(0.02)  # 让reader先获取锁
        with lock.write_lock():
            order.append("write")

    t1 = threading.Thread(target=reader)
    t2 = threading.Thread(target=writer)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # writer必须在reader结束后才能执行
    assert order.index("write") > order.index("read_end")
    print("  [test_rwlock_read_write_blocking] 读写互斥 ✓")


def test_rwlock_timeout():
    """测试锁超时"""
    lock = RWLock()

    # 先获取写锁
    lock.acquire_write()

    # 读锁应超时
    acquired = lock.acquire_read(timeout_ms=50)
    assert acquired is False

    lock.release_write()
    print("  [test_rwlock_timeout] 锁超时 ✓")


def test_rwlock_stats():
    """测试锁统计"""
    lock = RWLock()

    with lock.read_lock():
        pass

    with lock.write_lock():
        pass

    stats = lock.get_stats()
    assert stats["total_acquisitions"] == 2
    assert stats["total_releases"] == 2
    assert stats["readers"] == 0
    assert stats["writer"] is False
    print("  [test_rwlock_stats] 锁统计 ✓")


def test_semaphore_limit():
    """测试信号量限制并发数"""
    sem = Semaphore(max_permits=2)
    active_count = [0]
    max_active = [0]
    lock = threading.Lock()

    def worker():
        with sem.acquire():
            with lock:
                active_count[0] += 1
                max_active[0] = max(max_active[0], active_count[0])
            time.sleep(0.1)
            with lock:
                active_count[0] -= 1

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert max_active[0] == 2, f"最大并发数应为2，实际{max_active[0]}"
    print("  [test_semaphore_limit] 信号量限制并发 ✓")


def test_semaphore_timeout():
    """测试信号量超时"""
    sem = Semaphore(max_permits=1)
    sem._acquire()  # 占用唯一许可

    acquired = sem._acquire(timeout_ms=50)
    assert acquired is False

    sem.release()
    print("  [test_semaphore_timeout] 信号量超时 ✓")


def test_concurrency_controller():
    """测试并发控制器"""
    ctrl = ConcurrencyController()

    lock1 = ctrl.get_rwlock("resource_a")
    lock2 = ctrl.get_rwlock("resource_a")  # 应返回同一个
    assert lock1 is lock2

    sem1 = ctrl.get_semaphore("pool_b", max_permits=3)
    sem2 = ctrl.get_semaphore("pool_b", max_permits=3)
    assert sem1 is sem2

    stats = ctrl.get_stats()
    assert "resource_a" in stats
    assert "pool_b" in stats
    print("  [test_concurrency_controller] 并发控制器 ✓")


def test_rwlock_write_priority():
    """测试写优先策略"""
    lock = RWLock(priority=LockPriority.WRITE)

    # 获取读锁
    lock.acquire_read()

    # 启动一个写等待
    write_done = [False]
    def writer():
        with lock.write_lock():
            write_done[0] = True

    t = threading.Thread(target=writer)
    t.start()
    time.sleep(0.02)

    # 写等待时，新读请求应被阻塞
    read_acquired = lock.acquire_read(timeout_ms=50)
    assert read_acquired is False  # 因为写优先

    lock.release_read()
    t.join(timeout=1)
    assert write_done[0] is True
    print("  [test_rwlock_write_priority] 写优先策略 ✓")


def test_create_helpers():
    """测试便捷创建函数"""
    lock = create_rwlock(priority=LockPriority.READ)
    assert lock._priority == LockPriority.READ

    sem = create_semaphore(max_permits=5)
    assert sem.get_stats()["max_permits"] == 5
    print("  [test_create_helpers] 便捷创建 ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("阶段40测试: 并发控制接口标准化")
    print("=" * 60)

    test_rwlock_read_concurrent()
    test_rwlock_write_exclusive()
    test_rwlock_read_write_blocking()
    test_rwlock_timeout()
    test_rwlock_stats()
    test_semaphore_limit()
    test_semaphore_timeout()
    test_concurrency_controller()
    test_rwlock_write_priority()
    test_create_helpers()

    print("=" * 60)
    print("全部10项测试通过 ✓")
    print("=" * 60)
