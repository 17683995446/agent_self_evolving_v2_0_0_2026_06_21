"""
阶段142: 多租户支持 — 租户隔离

第一性原理:
1. 隔离性 — 租户间数据、资源、配置相互隔离
2. 公平性 — 资源分配应公平，防止单一租户耗尽资源
3. 可管理性 — 租户可被创建、配置、暂停、删除
4. 可观测性 — 租户活动可被监控和审计
5. 可扩展性 — 支持大量租户，性能不显著下降

组件:
- Tenant — 租户定义
- TenantState — 租户状态
- ResourceQuota — 租户资源配额
- TenantContext — 租户上下文（线程局部）
- TenantIsolation — 租户隔离器（数据隔离）
- TenantManager — 租户管理器
"""

import os
import time
import threading
import uuid
from typing import Any, Dict, List, Optional, Set, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


# ============================================================
# 租户状态
# ============================================================

class TenantState(Enum):
    """租户状态"""
    ACTIVE = "active"       # 活跃
    SUSPENDED = "suspended" # 暂停
    TERMINATED = "terminated"  # 终止
    PENDING = "pending"     # 待激活


# ============================================================
# 资源配额
# ============================================================

@dataclass
class ResourceQuota:
    """租户资源配额"""
    max_requests_per_minute: int = 1000
    max_concurrent_tasks: int = 10
    max_storage_mb: int = 1024
    max_users: int = 50
    max_plugins: int = 20
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_requests_per_minute": self.max_requests_per_minute,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "max_storage_mb": self.max_storage_mb,
            "max_users": self.max_users,
            "max_plugins": self.max_plugins,
            "custom": self.custom,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceQuota":
        return cls(
            max_requests_per_minute=data.get("max_requests_per_minute", 1000),
            max_concurrent_tasks=data.get("max_concurrent_tasks", 10),
            max_storage_mb=data.get("max_storage_mb", 1024),
            max_users=data.get("max_users", 50),
            max_plugins=data.get("max_plugins", 20),
            custom=data.get("custom", {}),
        )


# ============================================================
# 租户
# ============================================================

@dataclass
class Tenant:
    """租户"""
    tenant_id: str
    name: str
    state: TenantState = TenantState.PENDING
    quota: ResourceQuota = field(default_factory=ResourceQuota)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    suspended_at: Optional[float] = None
    terminated_at: Optional[float] = None

    @property
    def active(self) -> bool:
        return self.state == TenantState.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "state": self.state.value,
            "quota": self.quota.to_dict(),
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "suspended_at": self.suspended_at,
            "terminated_at": self.terminated_at,
        }


# ============================================================
# 资源使用统计
# ============================================================

@dataclass
class ResourceUsage:
    """租户资源使用统计"""
    tenant_id: str
    requests_this_minute: int = 0
    concurrent_tasks: int = 0
    storage_used_mb: float = 0
    user_count: int = 0
    plugin_count: int = 0
    last_request_time: float = 0
    request_history: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "requests_this_minute": self.requests_this_minute,
            "concurrent_tasks": self.concurrent_tasks,
            "storage_used_mb": self.storage_used_mb,
            "user_count": self.user_count,
            "plugin_count": self.plugin_count,
            "last_request_time": self.last_request_time,
        }


# ============================================================
# 租户上下文
# ============================================================

_context_local = threading.local()


class TenantContext:
    """
    租户上下文

    携带当前请求的租户信息，通过线程局部存储传递。
    """

    def __init__(self, tenant_id: Optional[str] = None, tenant: Optional[Tenant] = None):
        self._tenant_id = tenant_id
        self._tenant = tenant

    @property
    def tenant_id(self) -> Optional[str]:
        return self._tenant_id

    @property
    def tenant(self) -> Optional[Tenant]:
        return self._tenant

    @property
    def has_tenant(self) -> bool:
        return self._tenant_id is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self._tenant_id,
            "has_tenant": self.has_tenant,
        }


def get_current_tenant_id() -> Optional[str]:
    """获取当前线程的租户ID"""
    ctx = getattr(_context_local, "context", None)
    return ctx.tenant_id if ctx else None


def get_current_tenant_context() -> TenantContext:
    """获取当前线程的租户上下文"""
    ctx = getattr(_context_local, "context", None)
    if ctx is None:
        return TenantContext()
    return ctx


def set_tenant_context(context: TenantContext) -> None:
    """设置当前线程的租户上下文"""
    _context_local.context = context


def clear_tenant_context() -> None:
    """清除当前线程的租户上下文"""
    if hasattr(_context_local, "context"):
        del _context_local.context


class tenant_scope:
    """
    租户作用域上下文管理器

    with tenant_scope("tenant_123"):
        # 在此作用域内，当前租户为tenant_123
        ...
    """

    def __init__(self, tenant_id: str, tenant: Optional[Tenant] = None):
        self._tenant_id = tenant_id
        self._tenant = tenant
        self._previous_context: Optional[TenantContext] = None

    def __enter__(self) -> TenantContext:
        self._previous_context = getattr(_context_local, "context", None)
        ctx = TenantContext(tenant_id=self._tenant_id, tenant=self._tenant)
        set_tenant_context(ctx)
        return ctx

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._previous_context is not None:
            set_tenant_context(self._previous_context)
        else:
            clear_tenant_context()


# ============================================================
# 租户隔离器
# ============================================================

class TenantIsolation:
    """
    租户数据隔离器

    为每个租户维护独立的数据命名空间。
    """

    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}  # tenant_id -> {key -> value}
        self._counters: Dict[str, Dict[str, int]] = {}  # tenant_id -> {counter_name -> value}
        self._lock = threading.RLock()

    def set_data(self, tenant_id: str, key: str, value: Any) -> None:
        """设置租户数据"""
        with self._lock:
            if tenant_id not in self._data:
                self._data[tenant_id] = {}
            self._data[tenant_id][key] = value

    def get_data(self, tenant_id: str, key: str, default: Any = None) -> Any:
        """获取租户数据"""
        with self._lock:
            return self._data.get(tenant_id, {}).get(key, default)

    def delete_data(self, tenant_id: str, key: str) -> bool:
        """删除租户数据"""
        with self._lock:
            if tenant_id in self._data and key in self._data[tenant_id]:
                del self._data[tenant_id][key]
                return True
            return False

    def get_all_data(self, tenant_id: str) -> Dict[str, Any]:
        """获取租户所有数据"""
        with self._lock:
            return dict(self._data.get(tenant_id, {}))

    def clear_tenant(self, tenant_id: str) -> None:
        """清空租户所有数据"""
        with self._lock:
            self._data.pop(tenant_id, None)
            self._counters.pop(tenant_id, None)

    def increment_counter(self, tenant_id: str, counter_name: str, amount: int = 1) -> int:
        """递增计数器"""
        with self._lock:
            if tenant_id not in self._counters:
                self._counters[tenant_id] = {}
            self._counters[tenant_id][counter_name] = self._counters[tenant_id].get(counter_name, 0) + amount
            return self._counters[tenant_id][counter_name]

    def get_counter(self, tenant_id: str, counter_name: str) -> int:
        """获取计数器值"""
        with self._lock:
            return self._counters.get(tenant_id, {}).get(counter_name, 0)

    def reset_counter(self, tenant_id: str, counter_name: str) -> None:
        """重置计数器"""
        with self._lock:
            if tenant_id in self._counters:
                self._counters[tenant_id][counter_name] = 0

    def get_all_counters(self, tenant_id: str) -> Dict[str, int]:
        """获取租户所有计数器"""
        with self._lock:
            return dict(self._counters.get(tenant_id, {}))

    def list_tenants(self) -> List[str]:
        """列出所有有数据的租户"""
        with self._lock:
            all_tenants = set(self._data.keys()) | set(self._counters.keys())
            return list(all_tenants)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "tenant_count": len(self.list_tenants()),
                "total_data_keys": sum(len(d) for d in self._data.values()),
                "total_counters": sum(len(c) for c in self._counters.values()),
            }


# ============================================================
# 租户管理器
# ============================================================

class TenantManager:
    """
    租户管理器

    管理租户的生命周期、资源配额、使用统计。
    """

    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}
        self._usage: Dict[str, ResourceUsage] = {}
        self._isolation: Dict[str, TenantIsolation] = {}
        self._lock = threading.RLock()
        self._request_history: Dict[str, List[float]] = {}  # tenant_id -> timestamps
        self._on_create: Optional[Callable[[Tenant], None]] = None
        self._on_suspend: Optional[Callable[[Tenant], None]] = None
        self._on_terminate: Optional[Callable[[Tenant], None]] = None

    @property
    def on_create(self):
        return self._on_create

    @property
    def on_suspend(self):
        return self._on_suspend

    @property
    def on_terminate(self):
        return self._on_terminate

    def set_callbacks(
        self,
        on_create: Optional[Callable[[Tenant], None]] = None,
        on_suspend: Optional[Callable[[Tenant], None]] = None,
        on_terminate: Optional[Callable[[Tenant], None]] = None,
    ) -> None:
        """设置生命周期回调"""
        if on_create is not None:
            self._on_create = on_create
        if on_suspend is not None:
            self._on_suspend = on_suspend
        if on_terminate is not None:
            self._on_terminate = on_terminate

    # ---------- 租户生命周期 ----------

    def create_tenant(
        self,
        name: str,
        quota: Optional[ResourceQuota] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
        activate: bool = True,
    ) -> Tenant:
        """创建租户"""
        with self._lock:
            if tenant_id is None:
                tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"

            if tenant_id in self._tenants:
                raise ValueError(f"Tenant '{tenant_id}' already exists")

            tenant = Tenant(
                tenant_id=tenant_id,
                name=name,
                state=TenantState.ACTIVE if activate else TenantState.PENDING,
                quota=quota or ResourceQuota(),
                metadata=metadata or {},
            )
            self._tenants[tenant_id] = tenant
            self._usage[tenant_id] = ResourceUsage(tenant_id=tenant_id)
            self._isolation[tenant_id] = TenantIsolation()
            self._request_history[tenant_id] = []

        if self._on_create:
            try:
                self._on_create(tenant)
            except Exception:
                pass

        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户"""
        with self._lock:
            return self._tenants.get(tenant_id)

    def list_tenants(self, state: Optional[TenantState] = None) -> List[Tenant]:
        """列出租户"""
        with self._lock:
            tenants = list(self._tenants.values())
        if state:
            tenants = [t for t in tenants if t.state == state]
        return tenants

    def update_tenant(
        self,
        tenant_id: str,
        name: Optional[str] = None,
        quota: Optional[ResourceQuota] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tenant]:
        """更新租户"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None:
                return None
            if name is not None:
                tenant.name = name
            if quota is not None:
                tenant.quota = quota
            if metadata is not None:
                tenant.metadata.update(metadata)
            tenant.updated_at = time.time()
            return tenant

    def suspend_tenant(self, tenant_id: str) -> bool:
        """暂停租户"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None:
                return False
            tenant.state = TenantState.SUSPENDED
            tenant.suspended_at = time.time()
            tenant.updated_at = time.time()

        if self._on_suspend:
            try:
                self._on_suspend(tenant)
            except Exception:
                pass
        return True

    def resume_tenant(self, tenant_id: str) -> bool:
        """恢复租户"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None:
                return False
            tenant.state = TenantState.ACTIVE
            tenant.suspended_at = None
            tenant.updated_at = time.time()
            return True

    def terminate_tenant(self, tenant_id: str) -> bool:
        """终止租户"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None:
                return False
            tenant.state = TenantState.TERMINATED
            tenant.terminated_at = time.time()
            tenant.updated_at = time.time()
            # 清理隔离数据
            isolation = self._isolation.get(tenant_id)
            if isolation:
                isolation.clear_tenant(tenant_id)

        if self._on_terminate:
            try:
                self._on_terminate(tenant)
            except Exception:
                pass
        return True

    def delete_tenant(self, tenant_id: str) -> bool:
        """删除租户（彻底删除）"""
        with self._lock:
            if tenant_id not in self._tenants:
                return False
            self._tenants.pop(tenant_id)
            self._usage.pop(tenant_id, None)
            self._isolation.pop(tenant_id, None)
            self._request_history.pop(tenant_id, None)
            return True

    # ---------- 状态检查 ----------

    def is_active(self, tenant_id: str) -> bool:
        """租户是否活跃"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            return tenant is not None and tenant.active

    def exists(self, tenant_id: str) -> bool:
        """租户是否存在"""
        with self._lock:
            return tenant_id in self._tenants

    # ---------- 资源配额检查 ----------

    def check_quota(self, tenant_id: str, resource: str, amount: int = 1) -> Tuple[bool, Optional[str]]:
        """
        检查资源配额

        Returns:
            (allowed, error_message)
        """
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None:
                return False, "Tenant not found"
            if not tenant.active:
                return False, "Tenant not active"

            usage = self._usage.get(tenant_id)
            if usage is None:
                return False, "Usage tracking not found"

            quota = tenant.quota

            if resource == "requests_per_minute":
                # 清理1分钟前的请求
                now = time.time()
                history = self._request_history.get(tenant_id, [])
                history = [t for t in history if now - t < 60]
                self._request_history[tenant_id] = history
                if len(history) + amount > quota.max_requests_per_minute:
                    return False, f"Rate limit: {len(history)}/{quota.max_requests_per_minute} requests/min"

            elif resource == "concurrent_tasks":
                if usage.concurrent_tasks + amount > quota.max_concurrent_tasks:
                    return False, f"Concurrent task limit: {usage.concurrent_tasks}/{quota.max_concurrent_tasks}"

            elif resource == "storage":
                if usage.storage_used_mb + amount > quota.max_storage_mb:
                    return False, f"Storage limit: {usage.storage_used_mb}/{quota.max_storage_mb} MB"

            elif resource == "users":
                if usage.user_count + amount > quota.max_users:
                    return False, f"User limit: {usage.user_count}/{quota.max_users}"

            elif resource == "plugins":
                if usage.plugin_count + amount > quota.max_plugins:
                    return False, f"Plugin limit: {usage.plugin_count}/{quota.max_plugins}"

            return True, None

    def record_request(self, tenant_id: str) -> None:
        """记录请求"""
        with self._lock:
            if tenant_id not in self._request_history:
                self._request_history[tenant_id] = []
            self._request_history[tenant_id].append(time.time())
            usage = self._usage.get(tenant_id)
            if usage:
                usage.last_request_time = time.time()

    def record_task_start(self, tenant_id: str) -> None:
        """记录任务开始"""
        with self._lock:
            usage = self._usage.get(tenant_id)
            if usage:
                usage.concurrent_tasks += 1

    def record_task_end(self, tenant_id: str) -> None:
        """记录任务结束"""
        with self._lock:
            usage = self._usage.get(tenant_id)
            if usage and usage.concurrent_tasks > 0:
                usage.concurrent_tasks -= 1

    def record_storage_use(self, tenant_id: str, mb: float) -> None:
        """记录存储使用"""
        with self._lock:
            usage = self._usage.get(tenant_id)
            if usage:
                usage.storage_used_mb = mb

    def record_user_count(self, tenant_id: str, count: int) -> None:
        """记录用户数"""
        with self._lock:
            usage = self._usage.get(tenant_id)
            if usage:
                usage.user_count = count

    def record_plugin_count(self, tenant_id: str, count: int) -> None:
        """记录插件数"""
        with self._lock:
            usage = self._usage.get(tenant_id)
            if usage:
                usage.plugin_count = count

    def get_usage(self, tenant_id: str) -> Optional[ResourceUsage]:
        """获取资源使用"""
        with self._lock:
            return self._usage.get(tenant_id)

    # ---------- 数据隔离 ----------

    def get_isolation(self, tenant_id: str) -> Optional[TenantIsolation]:
        """获取租户隔离器"""
        with self._lock:
            return self._isolation.get(tenant_id)

    def set_tenant_data(self, tenant_id: str, key: str, value: Any) -> bool:
        """设置租户数据"""
        with self._lock:
            isolation = self._isolation.get(tenant_id)
            if isolation is None:
                return False
            isolation.set_data(tenant_id, key, value)
            return True

    def get_tenant_data(self, tenant_id: str, key: str, default: Any = None) -> Any:
        """获取租户数据"""
        with self._lock:
            isolation = self._isolation.get(tenant_id)
            if isolation is None:
                return default
            return isolation.get_data(tenant_id, key, default)

    def delete_tenant_data(self, tenant_id: str, key: str) -> bool:
        """删除租户数据"""
        with self._lock:
            isolation = self._isolation.get(tenant_id)
            if isolation is None:
                return False
            return isolation.delete_data(tenant_id, key)

    # ---------- 上下文 ----------

    def create_context(self, tenant_id: str) -> TenantContext:
        """创建租户上下文"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
        return TenantContext(tenant_id=tenant_id, tenant=tenant)

    def execute_in_tenant_scope(
        self,
        tenant_id: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """在租户作用域内执行函数"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
        if tenant is None:
            raise ValueError(f"Tenant '{tenant_id}' not found")
        if not tenant.active:
            raise RuntimeError(f"Tenant '{tenant_id}' is not active")

        with tenant_scope(tenant_id, tenant):
            return func(*args, **kwargs)

    # ---------- 统计 ----------

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            tenants = list(self._tenants.values())

        state_counts = defaultdict(int)
        for t in tenants:
            state_counts[t.state.value] += 1

        return {
            "total_tenants": len(tenants),
            "by_state": dict(state_counts),
            "total_data_keys": sum(
                len(self._isolation[tid]._data.get(tid, {}))
                for tid in self._isolation
            ) if self._isolation else 0,
        }

    def get_tenant_summary(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """获取租户摘要"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            usage = self._usage.get(tenant_id)
            isolation = self._isolation.get(tenant_id)

        if tenant is None:
            return None

        summary = tenant.to_dict()
        if usage:
            summary["usage"] = usage.to_dict()
        if isolation:
            summary["data_keys"] = len(isolation.get_all_data(tenant_id))
            summary["counters"] = isolation.get_all_counters(tenant_id)
        return summary


# 便捷导入


# ============================================================
# 便捷函数
# ============================================================

def create_tenant_manager() -> TenantManager:
    """创建租户管理器"""
    return TenantManager()


def create_resource_quota(
    max_requests_per_minute: int = 1000,
    max_concurrent_tasks: int = 10,
    max_storage_mb: int = 1024,
    max_users: int = 50,
    max_plugins: int = 20,
) -> ResourceQuota:
    """创建资源配额"""
    return ResourceQuota(
        max_requests_per_minute=max_requests_per_minute,
        max_concurrent_tasks=max_concurrent_tasks,
        max_storage_mb=max_storage_mb,
        max_users=max_users,
        max_plugins=max_plugins,
    )


# 默认全局实例
_global_tenant_manager: Optional[TenantManager] = None
_global_tenant_lock = threading.Lock()


def get_global_tenant_manager() -> TenantManager:
    """获取全局租户管理器"""
    global _global_tenant_manager
    with _global_tenant_lock:
        if _global_tenant_manager is None:
            _global_tenant_manager = create_tenant_manager()
        return _global_tenant_manager
