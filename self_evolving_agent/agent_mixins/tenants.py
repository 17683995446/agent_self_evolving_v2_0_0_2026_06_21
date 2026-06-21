"""多租户管理Mixin — 阶段149从agent.py拆分"""

from typing import Any, Callable, Dict, List, Optional

from ..core.multi_tenant import (
    Tenant, ResourceQuota, ResourceUsage, TenantState,
)


class TenantsMixin:
    """多租户管理接口（阶段142）"""

    def create_tenant(
        self,
        name: str,
        quota: Optional[ResourceQuota] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
        activate: bool = True,
    ) -> Tenant:
        """创建租户（阶段142新增）"""
        return self._tenants.create_tenant(
            name=name,
            quota=quota,
            metadata=metadata,
            tenant_id=tenant_id,
            activate=activate,
        )

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户（阶段142新增）"""
        return self._tenants.get_tenant(tenant_id)

    def list_tenants(self, state: Optional[TenantState] = None) -> List[Tenant]:
        """列出租户（阶段142新增）"""
        return self._tenants.list_tenants(state=state)

    def update_tenant(
        self,
        tenant_id: str,
        name: Optional[str] = None,
        quota: Optional[ResourceQuota] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tenant]:
        """更新租户（阶段142新增）"""
        return self._tenants.update_tenant(
            tenant_id=tenant_id,
            name=name,
            quota=quota,
            metadata=metadata,
        )

    def suspend_tenant(self, tenant_id: str) -> bool:
        """暂停租户（阶段142新增）"""
        return self._tenants.suspend_tenant(tenant_id)

    def resume_tenant(self, tenant_id: str) -> bool:
        """恢复租户（阶段142新增）"""
        return self._tenants.resume_tenant(tenant_id)

    def terminate_tenant(self, tenant_id: str) -> bool:
        """终止租户（阶段142新增）"""
        return self._tenants.terminate_tenant(tenant_id)

    def delete_tenant(self, tenant_id: str) -> bool:
        """删除租户（阶段142新增）"""
        return self._tenants.delete_tenant(tenant_id)

    def is_tenant_active(self, tenant_id: str) -> bool:
        """租户是否活跃（阶段142新增）"""
        return self._tenants.is_active(tenant_id)

    def check_tenant_quota(
        self, tenant_id: str, resource: str, amount: int = 1
    ) -> tuple:
        """检查租户资源配额（阶段142新增）"""
        return self._tenants.check_quota(tenant_id, resource, amount)

    def get_tenant_usage(self, tenant_id: str) -> Optional[ResourceUsage]:
        """获取租户资源使用（阶段142新增）"""
        return self._tenants.get_usage(tenant_id)

    def set_tenant_data(self, tenant_id: str, key: str, value: Any) -> bool:
        """设置租户数据（阶段142新增）"""
        return self._tenants.set_tenant_data(tenant_id, key, value)

    def get_tenant_data(self, tenant_id: str, key: str, default: Any = None) -> Any:
        """获取租户数据（阶段142新增）"""
        return self._tenants.get_tenant_data(tenant_id, key, default)

    def delete_tenant_data(self, tenant_id: str, key: str) -> bool:
        """删除租户数据（阶段142新增）"""
        return self._tenants.delete_tenant_data(tenant_id, key)

    def execute_in_tenant(self, tenant_id: str, func: Callable, *args, **kwargs) -> Any:
        """在租户作用域内执行函数（阶段142新增）"""
        return self._tenants.execute_in_tenant_scope(tenant_id, func, *args, **kwargs)

    def get_tenant_stats(self) -> Dict[str, Any]:
        """获取租户统计（阶段142新增）"""
        return self._tenants.get_stats()

    def get_tenant_summary(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """获取租户摘要（阶段142新增）"""
        return self._tenants.get_tenant_summary(tenant_id)

    def set_tenant_callbacks(
        self,
        on_create: Optional[Callable] = None,
        on_suspend: Optional[Callable] = None,
        on_terminate: Optional[Callable] = None,
    ) -> None:
        """设置租户生命周期回调（阶段142新增）"""
        self._tenants.set_callbacks(
            on_create=on_create,
            on_suspend=on_suspend,
            on_terminate=on_terminate,
        )
