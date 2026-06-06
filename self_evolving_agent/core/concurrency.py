"""
阶段40: 并发控制接口标准化

第一性原理:
1. 共享资源在同一时间只能被有限数量的访问者使用
2. 并发控制是对资源访问的调度，必须防止竞态条件和死锁
3. 控制粒度要可调：从全局到资源级到用户级

设计原则:
- 信号量（Semaphore）：控制同时访问的最大数量
- 读写锁（RWLock）：读并发、写互斥
- 分布式锁接口：支持未来扩展
- 可观测：等待队列长度、获取锁耗时
"""

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar, Generic
from enum import Enum
from contextlib import contextmanager


T = TypeVar('T')


class LockType(Enum):
    """锁类型"""
    MUTEX = "mutex"       # 互斥锁
    RW = "rw"             # 读写锁
    SEMAPHORE = "semaphore"  # 信号量


class LockPriority(Enum):
    """锁优先级策略"""
    FAIR = "fair"         # 公平：按请求顺序
    WRITE = "write"       # 写优先
    READ = "read"         # 读优先


@dataclass
class LockStats:
    """锁统计信息"""
    total_acquisitions: int = 0
    total_releases: int = 0
    total_timeouts: int = 0
    current_holders: int = 0
    waiting_count: int = 0
    avg_wait_ms: float = 0.0


# ============================================================
# 读写锁
# ============================================================

class RWLock:
    """
    读写锁

    第一性原理：读操作不修改状态，可以并发；写操作修改状态，必须互斥
    """

    def __init__(self, priority: LockPriority = LockPriority.FAIR):
        self._priority = priority
        self._readers = 0
        self._writer = False
        self._read_wait = 0
        self._write_wait = 0
        self._cond = threading.Condition()
        self._stats = LockStats()
        self._wait_times: list[float] = []

    @contextmanager
    def read_lock(self, timeout_ms: Optional[float] = None):
        """获取读锁（上下文管理器）"""
        acquired = self.acquire_read(timeout_ms)
        try:
            yield acquired
        finally:
            if acquired:
                self.release_read()

    @contextmanager
    def write_lock(self, timeout_ms: Optional[float] = None):
        """获取写锁（上下文管理器）"""
        acquired = self.acquire_write(timeout_ms)
        try:
            yield acquired
        finally:
            if acquired:
                self.release_write()

    def acquire_read(self, timeout_ms: Optional[float] = None) -> bool:
        """获取读锁"""
        start = time.time()
        with self._cond:
            self._read_wait += 1
            self._stats.waiting_count = self._read_wait + self._write_wait

            deadline = None
            if timeout_ms is not None:
                deadline = time.time() + timeout_ms / 1000.0

            while True:
                # 检查是否可以获取读锁
                can_read = not self._writer
                if self._priority == LockPriority.WRITE:
                    can_read = can_read and self._write_wait == 0

                if can_read:
                    self._readers += 1
                    self._read_wait -= 1
                    self._stats.total_acquisitions += 1
                    self._stats.current_holders = self._readers + (1 if self._writer else 0)
                    self._stats.waiting_count = self._read_wait + self._write_wait

                    wait_ms = (time.time() - start) * 1000
                    self._wait_times.append(wait_ms)
                    if len(self._wait_times) > 100:
                        self._wait_times = self._wait_times[-100:]
                    self._stats.avg_wait_ms = sum(self._wait_times) / len(self._wait_times)
                    return True

                if deadline and time.time() >= deadline:
                    self._read_wait -= 1
                    self._stats.total_timeouts += 1
                    self._stats.waiting_count = self._read_wait + self._write_wait
                    return False

                self._cond.wait(timeout=0.1)

    def release_read(self) -> None:
        """释放读锁"""
        with self._cond:
            self._readers -= 1
            self._stats.total_releases += 1
            self._stats.current_holders = self._readers + (1 if self._writer else 0)
            if self._readers == 0:
                self._cond.notify_all()

    def acquire_write(self, timeout_ms: Optional[float] = None) -> bool:
        """获取写锁"""
        start = time.time()
        with self._cond:
            self._write_wait += 1
            self._stats.waiting_count = self._read_wait + self._write_wait

            deadline = None
            if timeout_ms is not None:
                deadline = time.time() + timeout_ms / 1000.0

            while True:
                can_write = self._readers == 0 and not self._writer
                if self._priority == LockPriority.READ:
                    can_write = can_write and self._read_wait == 0

                if can_write:
                    self._writer = True
                    self._write_wait -= 1
                    self._stats.total_acquisitions += 1
                    self._stats.current_holders = self._readers + 1
                    self._stats.waiting_count = self._read_wait + self._write_wait

                    wait_ms = (time.time() - start) * 1000
                    self._wait_times.append(wait_ms)
                    if len(self._wait_times) > 100:
                        self._wait_times = self._wait_times[-100:]
                    self._stats.avg_wait_ms = sum(self._wait_times) / len(self._wait_times)
                    return True

                if deadline and time.time() >= deadline:
                    self._write_wait -= 1
                    self._stats.total_timeouts += 1
                    self._stats.waiting_count = self._read_wait + self._write_wait
                    return False

                self._cond.wait(timeout=0.1)

    def release_write(self) -> None:
        """释放写锁"""
        with self._cond:
            self._writer = False
            self._stats.total_releases += 1
            self._stats.current_holders = self._readers
            self._cond.notify_all()

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._cond:
            return {
                "priority": self._priority.value,
                "readers": self._readers,
                "writer": self._writer,
                "read_wait": self._read_wait,
                "write_wait": self._write_wait,
                "total_acquisitions": self._stats.total_acquisitions,
                "total_releases": self._stats.total_releases,
                "total_timeouts": self._stats.total_timeouts,
                "current_holders": self._stats.current_holders,
                "avg_wait_ms": self._stats.avg_wait_ms,
            }


# ============================================================
# 信号量
# ============================================================

class Semaphore:
    """
    信号量

    第一性原理：限制同时访问某资源的线程数量
    """

    def __init__(self, max_permits: int = 1):
        self._max_permits = max_permits
        self._permits = max_permits
        self._cond = threading.Condition()
        self._stats = LockStats()
        self._wait_times: list[float] = []

    @contextmanager
    def acquire(self, timeout_ms: Optional[float] = None):
        """获取许可（上下文管理器）"""
        acquired = self._acquire(timeout_ms)
        try:
            yield acquired
        finally:
            if acquired:
                self.release()

    def _acquire(self, timeout_ms: Optional[float] = None) -> bool:
        """获取许可"""
        start = time.time()
        with self._cond:
            self._stats.waiting_count += 1

            deadline = None
            if timeout_ms is not None:
                deadline = time.time() + timeout_ms / 1000.0

            while self._permits <= 0:
                if deadline and time.time() >= deadline:
                    self._stats.waiting_count -= 1
                    self._stats.total_timeouts += 1
                    return False
                wait_time = 0.1
                if deadline:
                    wait_time = min(wait_time, deadline - time.time())
                if wait_time <= 0:
                    self._stats.waiting_count -= 1
                    self._stats.total_timeouts += 1
                    return False
                self._cond.wait(timeout=wait_time)

            self._permits -= 1
            self._stats.total_acquisitions += 1
            self._stats.current_holders = self._max_permits - self._permits
            self._stats.waiting_count -= 1

            wait_ms = (time.time() - start) * 1000
            self._wait_times.append(wait_ms)
            if len(self._wait_times) > 100:
                self._wait_times = self._wait_times[-100:]
            self._stats.avg_wait_ms = sum(self._wait_times) / len(self._wait_times) if self._wait_times else 0.0
            return True

    def release(self) -> None:
        """释放许可"""
        with self._cond:
            self._permits += 1
            self._stats.total_releases += 1
            self._stats.current_holders = self._max_permits - self._permits
            self._cond.notify()

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._cond:
            return {
                "max_permits": self._max_permits,
                "available_permits": self._permits,
                "total_acquisitions": self._stats.total_acquisitions,
                "total_releases": self._stats.total_releases,
                "total_timeouts": self._stats.total_timeouts,
                "current_holders": self._stats.current_holders,
                "avg_wait_ms": self._stats.avg_wait_ms,
            }


# ============================================================
# 并发控制器
# ============================================================

class ConcurrencyController:
    """
    并发控制器

    统一管理多种并发控制机制
    """

    def __init__(self):
        self._locks: dict[str, Any] = {}
        self._global_lock = threading.Lock()

    def get_rwlock(self, name: str, priority: LockPriority = LockPriority.FAIR) -> RWLock:
        """获取或创建读写锁"""
        with self._global_lock:
            if name not in self._locks:
                self._locks[name] = RWLock(priority=priority)
            return self._locks[name]

    def get_semaphore(self, name: str, max_permits: int = 1) -> Semaphore:
        """获取或创建信号量"""
        with self._global_lock:
            if name not in self._locks:
                self._locks[name] = Semaphore(max_permits=max_permits)
            return self._locks[name]

    def get_stats(self) -> dict[str, dict[str, Any]]:
        """获取所有锁的统计信息"""
        with self._global_lock:
            return {
                name: lock.get_stats()
                for name, lock in self._locks.items()
            }


# ============================================================
# 便捷函数
# ============================================================

def create_rwlock(priority: LockPriority = LockPriority.FAIR) -> RWLock:
    """创建读写锁"""
    return RWLock(priority=priority)


def create_semaphore(max_permits: int = 1) -> Semaphore:
    """创建信号量"""
    return Semaphore(max_permits=max_permits)
