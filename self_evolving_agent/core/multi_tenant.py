"""
阶段50: 多租户接口标准化

第一性原理:
1. 多个用户/组织共享同一系统，但数据必须隔离
2. 租户是资源的边界：数据、配置、配额相互独立
3. 租户切换必须安全、无泄漏

设计原则:
- Tenant: 租户定义
- TenantContext: 租户上下文（线程本地存储）
- TenantManager: 租户管理
- 资源隔离：数据、配置、配额
"""

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class TenantStatus(Enum):
    """租户状态"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


@dataclass
class Tenant:
    """租户"""
    tenant_id: str
    name: str
    status: TenantStatus = TenantStatus.ACTIVE
    config: Dict[str, Any] = field(default_factory=dict)
    quotas: Dict[str, float] = field(default_factory=dict)


# ============================================================
# 租户上下文
# ============================================================

class TenantContext:
    """
    租户上下文

    使用线程本地存储确保租户隔离
    """

    _local = threading.local()

    @classmethod
    def get_current_tenant_id(cls) -> Optional[str]:
        """获取当前租户ID"""
        return getattr(cls._local, "tenant_id", None)

    @classmethod
    def set_current_tenant(cls, tenant_id: str) -> None:
        """设置当前租户"""
        cls._local.tenant_id = tenant_id

    @classmethod
    def clear(cls) -> None:
        """清除当前租户"""
        if hasattr(cls._local, "tenant_id"):
            delattr(cls._local, "tenant_id")


# ============================================================
# 租户管理器
# ============================================================

class TenantManager:
    """
    租户管理器

    管理所有租户的生命周期和资源隔离
    """

    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}
        self._lock = threading.Lock()

    def create_tenant(self, tenant_id: str, name: str, **config) -> Tenant:
        """创建租户"""
        with self._lock:
            if tenant_id in self._tenants:
                raise ValueError(f"Tenant '{tenant_id}' already exists")
            tenant = Tenant(
                tenant_id=tenant_id,
                name=name,
                config=config,
            )
            self._tenants[tenant_id] = tenant
            return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户"""
        with self._lock:
            return self._tenants.get(tenant_id)

    def update_tenant(self, tenant_id: str, **updates) -> bool:
        """更新租户"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None:
                return False
            for key, value in updates.items():
                if hasattr(tenant, key):
                    setattr(tenant, key, value)
                elif key in tenant.config:
                    tenant.config[key] = value
            return True

    def delete_tenant(self, tenant_id: str) -> bool:
        """删除租户"""
        with self._lock:
            if tenant_id not in self._tenants:
                return False
            del self._tenants[tenant_id]
            return True

    def list_tenants(self) -> List[Tenant]:
        """列出所有租户"""
        with self._lock:
            return list(self._tenants.values())

    def set_quota(self, tenant_id: str, resource: str, limit: float) -> bool:
        """设置租户配额"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None:
                return False
            tenant.quotas[resource] = limit
            return True

    def get_quota(self, tenant_id: str, resource: str) -> Optional[float]:
        """获取租户配额"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None:
                return None
            return tenant.quotas.get(resource)

    def check_access(self, tenant_id: str) -> bool:
        """检查租户访问权限"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None:
                return False
            return tenant.status == TenantStatus.ACTIVE

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "total_tenants": len(self._tenants),
                "active": sum(1 for t in self._tenants.values() if t.status == TenantStatus.ACTIVE),
                "suspended": sum(1 for t in self._tenants.values() if t.status == TenantStatus.SUSPENDED),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_tenant_manager() -> TenantManager:
    """创建租户管理器"""
    return TenantManager()


def with_tenant(tenant_id: str):
    """租户上下文装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            TenantContext.set_current_tenant(tenant_id)
            try:
                return func(*args, **kwargs)
            finally:
                TenantContext.clear()
        return wrapper
    return decorator
