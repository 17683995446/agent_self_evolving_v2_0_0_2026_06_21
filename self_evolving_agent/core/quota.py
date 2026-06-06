"""
阶段32: 资源配额管理

第一性原理:
1. 资源是有限的，使用资源必须申请配额
2. 没有配额管理，贪婪的模块将耗尽系统资源，导致整体崩溃
3. 配额必须可配置、可追踪、可释放

设计原则:
- 显式申请-使用-释放模式
- 配额分层：系统级 / 模块级 / 操作级
- 超限处理：拒绝、等待、降级
- 资源泄漏检测：自动追踪未释放配额
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional, Set
from enum import Enum
from datetime import datetime
import threading
import time
import uuid


class ResourceType(Enum):
    """资源类型"""
    MEMORY = "memory"           # 内存 (MB)
    CPU_TIME = "cpu_time"       # CPU时间 (ms)
    DISK = "disk"               # 磁盘空间 (MB)
    NETWORK = "network"         # 网络带宽 (KB/s)
    THREAD = "thread"           # 线程数
    FILE_DESCRIPTOR = "fd"      # 文件描述符
    CUSTOM = "custom"           # 自定义资源


class QuotaExceedPolicy(Enum):
    """配额超限策略"""
    REJECT = "reject"           # 直接拒绝
    WAIT = "wait"               # 等待直到有可用配额
    DOWNGRADE = "downgrade"     # 降级处理（返回简化结果）


@dataclass
class QuotaAllocation:
    """配额分配记录"""
    resource_type: ResourceType
    amount: float
    owner: str
    allocation_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 配额管理器
# ============================================================

class QuotaManager:
    """
    资源配额管理器

    第一性原理：资源使用必须有边界，边界必须可配置、可执行
    """

    def __init__(self):
        self._limits: Dict[ResourceType, float] = {}
        self._used: Dict[ResourceType, float] = {}
        self._allocations: Dict[str, QuotaAllocation] = {}
        self._owner_allocations: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()
        self._waiters: Dict[ResourceType, List[threading.Condition]] = {}
        self._exceed_callbacks: List[Callable[[ResourceType, str, float, float], None]] = []

    def set_limit(self, resource_type: ResourceType, limit: float) -> None:
        """设置资源上限"""
        with self._lock:
            self._limits[resource_type] = limit
            if resource_type not in self._used:
                self._used[resource_type] = 0.0

    def get_limit(self, resource_type: ResourceType) -> float:
        """获取资源上限"""
        with self._lock:
            return self._limits.get(resource_type, float('inf'))

    def get_used(self, resource_type: ResourceType) -> float:
        """获取已使用资源"""
        with self._lock:
            return self._used.get(resource_type, 0.0)

    def get_available(self, resource_type: ResourceType) -> float:
        """获取可用资源"""
        with self._lock:
            limit = self._limits.get(resource_type, float('inf'))
            used = self._used.get(resource_type, 0.0)
            return max(0.0, limit - used)

    def allocate(self, resource_type: ResourceType, amount: float, owner: str,
                 allocation_id: Optional[str] = None,
                 timeout_ms: Optional[float] = None,
                 policy: QuotaExceedPolicy = QuotaExceedPolicy.REJECT) -> Optional[QuotaAllocation]:
        """
        申请资源配额

        Args:
            resource_type: 资源类型
            amount: 申请数量
            owner: 配额所有者
            allocation_id: 分配ID（自动生成）
            timeout_ms: 等待超时（仅WAIT策略有效）
            policy: 超限策略

        Returns:
            配额分配记录，失败返回None
        """
        allocation_id = allocation_id or f"{owner}_{resource_type.value}_{uuid.uuid4().hex[:8]}"

        with self._lock:
            limit = self._limits.get(resource_type, float('inf'))
            used = self._used.get(resource_type, 0.0)

            if limit == float('inf'):
                # 无限制
                return self._do_allocate(resource_type, amount, owner, allocation_id)

            if used + amount <= limit:
                return self._do_allocate(resource_type, amount, owner, allocation_id)

            # 配额不足
            if policy == QuotaExceedPolicy.REJECT:
                self._notify_exceeded(resource_type, owner, amount, limit - used)
                return None

            elif policy == QuotaExceedPolicy.DOWNGRADE:
                # 分配可用部分
                available = limit - used
                if available > 0:
                    return self._do_allocate(resource_type, available, owner, allocation_id)
                return None

            elif policy == QuotaExceedPolicy.WAIT:
                if timeout_ms is None or timeout_ms <= 0:
                    return None

                # 等待可用配额
                condition = threading.Condition(self._lock)
                if resource_type not in self._waiters:
                    self._waiters[resource_type] = []
                self._waiters[resource_type].append(condition)

                deadline = time.time() + timeout_ms / 1000.0
                while used + amount > limit:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        self._waiters[resource_type].remove(condition)
                        return None
                    condition.wait(timeout=remaining)
                    used = self._used.get(resource_type, 0.0)

                self._waiters[resource_type].remove(condition)
                return self._do_allocate(resource_type, amount, owner, allocation_id)

        return None

    def _do_allocate(self, resource_type: ResourceType, amount: float,
                     owner: str, allocation_id: str) -> QuotaAllocation:
        """执行分配"""
        allocation = QuotaAllocation(
            resource_type=resource_type,
            amount=amount,
            owner=owner,
            allocation_id=allocation_id,
        )

        self._used[resource_type] = self._used.get(resource_type, 0.0) + amount
        self._allocations[allocation_id] = allocation

        if owner not in self._owner_allocations:
            self._owner_allocations[owner] = set()
        self._owner_allocations[owner].add(allocation_id)

        return allocation

    def release(self, allocation_id: str) -> bool:
        """释放配额"""
        with self._lock:
            allocation = self._allocations.get(allocation_id)
            if allocation is None:
                return False

            self._used[allocation.resource_type] -= allocation.amount
            del self._allocations[allocation_id]

            owner = allocation.owner
            if owner in self._owner_allocations:
                self._owner_allocations[owner].discard(allocation_id)

            # 通知等待者
            waiters = self._waiters.get(allocation.resource_type, [])
            for condition in waiters[:]:
                with condition:
                    condition.notify()

            return True

    def release_all(self, owner: str) -> int:
        """释放某所有者的全部配额"""
        with self._lock:
            allocation_ids = list(self._owner_allocations.get(owner, set()))

        count = 0
        for aid in allocation_ids:
            if self.release(aid):
                count += 1
        return count

    def get_owner_usage(self, owner: str) -> Dict[ResourceType, float]:
        """获取某所有者的资源使用"""
        with self._lock:
            result: Dict[ResourceType, float] = {}
            for aid in self._owner_allocations.get(owner, set()):
                alloc = self._allocations.get(aid)
                if alloc:
                    result[alloc.resource_type] = result.get(alloc.resource_type, 0.0) + alloc.amount
            return result

    def get_all_usage(self) -> Dict[ResourceType, Dict[str, float]]:
        """获取所有资源的使用情况"""
        with self._lock:
            result: Dict[ResourceType, Dict[str, float]] = {}
            for alloc in self._allocations.values():
                if alloc.resource_type not in result:
                    result[alloc.resource_type] = {"used": 0.0, "limit": 0.0}
                result[alloc.resource_type]["used"] += alloc.amount

            for rt, limit in self._limits.items():
                if rt not in result:
                    result[rt] = {"used": 0.0, "limit": 0.0}
                result[rt]["limit"] = limit

            return result

    def add_exceed_callback(self, callback: Callable[[ResourceType, str, float, float], None]) -> None:
        """添加超限回调"""
        self._exceed_callbacks.append(callback)

    def _notify_exceeded(self, resource_type: ResourceType, owner: str,
                         requested: float, available: float) -> None:
        """通知配额超限"""
        for callback in self._exceed_callbacks:
            try:
                callback(resource_type, owner, requested, available)
            except Exception:
                pass

    def check_leaks(self, max_age_seconds: float = 3600.0) -> List[QuotaAllocation]:
        """检查可能的资源泄漏（长期未释放的配额）"""
        now = datetime.now()
        leaks = []

        with self._lock:
            for alloc in self._allocations.values():
                age = (now - alloc.timestamp).total_seconds()
                if age > max_age_seconds:
                    leaks.append(alloc)

        return leaks


# ============================================================
# 配额上下文管理器
# ============================================================

class QuotaContext:
    """
    配额上下文管理器

    使用with语句自动申请和释放配额
    """

    def __init__(self, manager: QuotaManager, resource_type: ResourceType,
                 amount: float, owner: str, **kwargs):
        self.manager = manager
        self.resource_type = resource_type
        self.amount = amount
        self.owner = owner
        self.kwargs = kwargs
        self.allocation: Optional[QuotaAllocation] = None

    def __enter__(self) -> Optional[QuotaAllocation]:
        self.allocation = self.manager.allocate(
            self.resource_type, self.amount, self.owner, **self.kwargs
        )
        return self.allocation

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.allocation:
            self.manager.release(self.allocation.allocation_id)


# ============================================================
# 便捷函数
# ============================================================

_global_quota_manager = QuotaManager()


def get_global_quota_manager() -> QuotaManager:
    """获取全局配额管理器"""
    return _global_quota_manager


def set_global_limit(resource_type: ResourceType, limit: float) -> None:
    """设置全局资源限制"""
    _global_quota_manager.set_limit(resource_type, limit)
