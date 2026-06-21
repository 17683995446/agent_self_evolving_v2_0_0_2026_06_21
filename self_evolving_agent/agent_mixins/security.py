"""安全管理Mixin — 阶段149从agent.py拆分"""

from typing import Any, Dict, List, Optional

from ..core.security import (
    Permission, User, SecurityContext, AuditEventType,
)


class SecurityMixin:
    """安全管理接口（阶段139）"""

    def create_user(
        self,
        username: str,
        roles: set,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> User:
        """创建用户（阶段139新增）"""
        return self._security.create_user(username, roles, password=password, api_key=api_key)

    def delete_user(self, user_id: str) -> bool:
        """删除用户（阶段139新增）"""
        return self._security.delete_user(user_id)

    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户（阶段139新增）"""
        return self._security.get_user(user_id)

    def list_users(self) -> List[User]:
        """列出所有用户（阶段139新增）"""
        return self._security.list_users()

    def authenticate(self, method: str, credentials: Dict[str, Any]):
        """认证用户（阶段139新增）"""
        return self._security.authenticate(method, credentials)

    def check_permission(self, user: User, permission: Permission) -> bool:
        """检查权限（阶段139新增）"""
        return self._security.check_permission(user, permission)

    def require_permission(self, user: User, permission: Permission) -> None:
        """要求权限（阶段139新增）"""
        self._security.require_permission(user, permission)

    def create_security_context(self, user: User) -> SecurityContext:
        """创建安全上下文（阶段139新增）"""
        return self._security.create_context(user)

    def assign_role(self, user_id: str, role_name: str) -> bool:
        """分配角色（阶段139新增）"""
        return self._security.assign_role(user_id, role_name)

    def revoke_role(self, user_id: str, role_name: str) -> bool:
        """撤销角色（阶段139新增）"""
        return self._security.revoke_role(user_id, role_name)

    def create_api_key(self, user_id: str) -> Optional[str]:
        """为用户创建API Key（阶段139新增）"""
        return self._security.create_api_key_for_user(user_id)

    def revoke_api_key(self, api_key: str) -> bool:
        """撤销API Key（阶段139新增）"""
        return self._security.revoke_api_key(api_key)

    def issue_token(self, user_id: str, expires_in: float = 3600) -> Optional[str]:
        """发放Bearer Token（阶段139新增）"""
        return self._security.issue_token(user_id, expires_in=expires_in)

    def get_audit_events(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """获取审计事件（阶段139新增）"""
        return self._security.get_audit_events(
            event_type=event_type, user_id=user_id, success=success, limit=limit
        )

    def get_security_stats(self) -> Dict[str, Any]:
        """获取安全统计（阶段139新增）"""
        return self._security.get_stats()

    def add_public_path(self, path: str) -> None:
        """添加公开路径（阶段139新增）"""
        self._security.add_public_path(path)

    def check_security_rate_limit(self, identifier: str) -> bool:
        """检查安全限流（阶段139新增）"""
        return self._security.check_rate_limit(identifier)
