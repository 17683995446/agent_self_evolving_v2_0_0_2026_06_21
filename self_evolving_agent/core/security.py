"""
阶段139: 安全加固 — 认证授权

第一性原理:
1. 最小权限 — 每个主体只应拥有完成其任务所需的最小权限
2. 纵深防御 — 多层安全机制，单层失效不导致系统崩溃
3. 可审计性 — 所有安全相关操作应被记录
4. 失败安全 — 安全机制失效时应拒绝访问而非放行
5. 身份验证 — 每个请求都应验证身份

组件:
- Permission — 权限定义
- Role — 角色定义（权限集合）
- User — 用户定义（角色集合）
- SecurityContext — 安全上下文（当前请求的身份和权限）
- Authenticator — 身份认证（API Key、Basic Auth、Bearer Token）
- Authorizer — 权限授权（RBAC）
- AuditLogger — 审计日志
- SecurityManager — 安全管理器（整合所有组件）
- SecurityMiddleware — Flask中间件
"""

import os
import time
import json
import hmac
import hashlib
import secrets
import threading
import base64
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from collections import defaultdict, deque


# ============================================================
# 权限和角色
# ============================================================

class Permission(Enum):
    """系统权限"""
    # Agent操作
    AGENT_VIEW = "agent:view"
    AGENT_CONTROL = "agent:control"
    AGENT_CONFIG = "agent:config"
    # 任务操作
    TASK_VIEW = "task:view"
    TASK_CREATE = "task:create"
    TASK_MANAGE = "task:manage"
    # 代码质量
    CODE_REVIEW = "code:review"
    CODE_DOCS = "code:docs"
    # 插件
    PLUGIN_VIEW = "plugin:view"
    PLUGIN_MANAGE = "plugin:manage"
    # 生产
    PRODUCTION_VIEW = "production:view"
    PRODUCTION_MANAGE = "production:manage"
    # 配置
    CONFIG_VIEW = "config:view"
    CONFIG_EDIT = "config:edit"
    # 安全
    SECURITY_VIEW = "security:view"
    SECURITY_MANAGE = "security:manage"
    # 超级权限
    ADMIN = "admin:*"


# 预定义角色权限映射
ROLE_PERMISSIONS: Dict[str, Set[Permission]] = {
    "viewer": {
        Permission.AGENT_VIEW, Permission.TASK_VIEW, Permission.PLUGIN_VIEW,
        Permission.PRODUCTION_VIEW, Permission.CONFIG_VIEW, Permission.SECURITY_VIEW,
    },
    "operator": {
        Permission.AGENT_VIEW, Permission.AGENT_CONTROL, Permission.AGENT_CONFIG,
        Permission.TASK_VIEW, Permission.TASK_CREATE, Permission.TASK_MANAGE,
        Permission.CODE_REVIEW, Permission.CODE_DOCS,
        Permission.PLUGIN_VIEW, Permission.PLUGIN_MANAGE,
        Permission.PRODUCTION_VIEW, Permission.PRODUCTION_MANAGE,
        Permission.CONFIG_VIEW, Permission.CONFIG_EDIT,
    },
    "admin": set(Permission),  # 所有权限
}


@dataclass
class Role:
    """角色"""
    name: str
    permissions: Set[Permission]
    description: str = ""

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Role):
            return self.name == other.name
        return False

    def has_permission(self, permission: Permission) -> bool:
        """检查角色是否有指定权限"""
        return permission in self.permissions or Permission.ADMIN in self.permissions

    @classmethod
    def create(cls, name: str, permissions: Set[Permission], description: str = "") -> "Role":
        """创建角色"""
        return cls(name=name, permissions=permissions, description=description)

    @classmethod
    def from_preset(cls, role_name: str) -> Optional["Role"]:
        """从预定义创建角色"""
        perms = ROLE_PERMISSIONS.get(role_name)
        if perms is None:
            return None
        return cls(name=role_name, permissions=perms, description=f"Preset role: {role_name}")


@dataclass
class User:
    """用户"""
    user_id: str
    username: str
    roles: Set[str] = field(default_factory=set)
    api_key: Optional[str] = None
    active: bool = True
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "roles": list(self.roles),
            "active": self.active,
            "created_at": self.created_at,
            "has_api_key": self.api_key is not None,
        }


# ============================================================
# 安全上下文
# ============================================================

class SecurityContext:
    """
    安全上下文

    携带当前请求的身份和权限信息。
    """

    def __init__(self, user: Optional[User] = None, roles: Optional[Set[Role]] = None):
        self._user = user
        self._roles = roles or set()
        self._authenticated = user is not None
        self._permissions: Set[Permission] = set()
        for role in self._roles:
            self._permissions |= role.permissions

    @property
    def user(self) -> Optional[User]:
        return self._user

    @property
    def user_id(self) -> Optional[str]:
        return self._user.user_id if self._user else None

    @property
    def username(self) -> Optional[str]:
        return self._user.username if self._user else None

    @property
    def authenticated(self) -> bool:
        return self._authenticated

    @property
    def roles(self) -> Set[Role]:
        return self._roles

    @property
    def permissions(self) -> Set[Permission]:
        return self._permissions

    def has_permission(self, permission: Permission) -> bool:
        """检查是否有指定权限"""
        if not self._authenticated:
            return False
        if Permission.ADMIN in self._permissions:
            return True
        return permission in self._permissions

    def has_any_permission(self, permissions: Set[Permission]) -> bool:
        """检查是否有任一权限"""
        if not self._authenticated:
            return False
        if Permission.ADMIN in self._permissions:
            return True
        return bool(self._permissions & permissions)

    def has_all_permissions(self, permissions: Set[Permission]) -> bool:
        """检查是否有所有权限"""
        if not self._authenticated:
            return False
        if Permission.ADMIN in self._permissions:
            return True
        return permissions.issubset(self._permissions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authenticated": self._authenticated,
            "user_id": self.user_id,
            "username": self.username,
            "roles": [r.name for r in self._roles],
            "permissions": [p.value for p in self._permissions],
        }


# 线程局部存储当前安全上下文
_context_local = threading.local()


def get_current_context() -> SecurityContext:
    """获取当前线程的安全上下文"""
    ctx = getattr(_context_local, "context", None)
    if ctx is None:
        return SecurityContext()
    return ctx


def set_current_context(context: SecurityContext) -> None:
    """设置当前线程的安全上下文"""
    _context_local.context = context


def clear_current_context() -> None:
    """清除当前线程的安全上下文"""
    if hasattr(_context_local, "context"):
        del _context_local.context


# ============================================================
# 审计日志
# ============================================================

class AuditEventType(Enum):
    """审计事件类型"""
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    CONFIG_CHANGE = "config_change"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"


@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str
    event_type: AuditEventType
    user_id: Optional[str]
    username: Optional[str]
    action: str
    resource: str
    timestamp: float
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "resource": self.resource,
            "timestamp": self.timestamp,
            "success": self.success,
            "details": self.details,
            "ip_address": self.ip_address,
        }


class AuditLogger:
    """
    审计日志记录器

    记录所有安全相关操作，支持查询和过滤。
    """

    def __init__(self, max_events: int = 10000):
        self._events: deque = deque(maxlen=max_events)
        self._lock = threading.RLock()
        self._counter = 0
        self._handlers: List[Callable[[AuditEvent], None]] = []

    def log(self, event: AuditEvent) -> None:
        """记录审计事件"""
        with self._lock:
            self._events.append(event)
        # 通知处理器
        for handler in self._handlers:
            try:
                handler(event)
            except Exception:
                pass

    def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        resource: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditEvent:
        """记录审计事件（便捷方法）"""
        with self._lock:
            self._counter += 1
            event_id = f"audit_{int(time.time())}_{self._counter}"

        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            user_id=user_id,
            username=username,
            action=action,
            resource=resource,
            timestamp=time.time(),
            success=success,
            details=details or {},
            ip_address=ip_address,
        )
        self.log(event)
        return event

    def add_handler(self, handler: Callable[[AuditEvent], None]) -> None:
        """添加事件处理器"""
        self._handlers.append(handler)

    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """查询审计事件"""
        with self._lock:
            events = list(self._events)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if success is not None:
            events = [e for e in events if e.success == success]
        return events[-limit:]

    def count(self) -> int:
        """事件总数"""
        with self._lock:
            return len(self._events)

    def clear(self) -> None:
        """清空审计日志"""
        with self._lock:
            self._events.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            events = list(self._events)
        stats = {
            "total": len(events),
            "by_type": defaultdict(int),
            "failed_count": 0,
        }
        for e in events:
            stats["by_type"][e.event_type.value] += 1
            if not e.success:
                stats["failed_count"] += 1
        stats["by_type"] = dict(stats["by_type"])
        return stats


# ============================================================
# 认证器
# ============================================================

class AuthResult:
    """认证结果"""

    def __init__(self, success: bool, user: Optional[User] = None, error: Optional[str] = None):
        self.success = success
        self.user = user
        self.error = error

    def __bool__(self) -> bool:
        return self.success


class Authenticator(ABC):
    """认证器抽象基类"""

    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """认证"""
        ...


class APIKeyAuthenticator(Authenticator):
    """
    API Key 认证器

    通过API Key识别用户。
    """

    def __init__(self):
        self._api_keys: Dict[str, User] = {}  # api_key -> user
        self._lock = threading.RLock()

    def register_api_key(self, user: User, api_key: Optional[str] = None) -> str:
        """为用户注册API Key"""
        if api_key is None:
            api_key = secrets.token_urlsafe(32)
        user.api_key = api_key
        with self._lock:
            self._api_keys[api_key] = user
        return api_key

    def revoke_api_key(self, api_key: str) -> bool:
        """撤销API Key"""
        with self._lock:
            if api_key in self._api_keys:
                user = self._api_keys.pop(api_key)
                user.api_key = None
                return True
            return False

    def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """通过API Key认证"""
        api_key = credentials.get("api_key")
        if not api_key:
            return AuthResult(False, error="Missing API key")

        with self._lock:
            user = self._api_keys.get(api_key)

        if user is None:
            return AuthResult(False, error="Invalid API key")
        if not user.active:
            return AuthResult(False, error="User inactive")

        return AuthResult(True, user=user)

    def get_user_by_key(self, api_key: str) -> Optional[User]:
        """通过API Key获取用户"""
        with self._lock:
            return self._api_keys.get(api_key)

    def list_users(self) -> List[User]:
        """列出所有注册用户"""
        with self._lock:
            return list(self._api_keys.values())


class BasicAuthAuthenticator(Authenticator):
    """
    Basic Auth 认证器

    通过用户名/密码识别用户。
    """

    def __init__(self):
        self._users: Dict[str, User] = {}  # username -> user
        self._passwords: Dict[str, str] = {}  # username -> password_hash
        self._lock = threading.RLock()

    @staticmethod
    def _hash_password(password: str) -> str:
        """哈希密码"""
        salt = "self_evolving_agent_salt"
        return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()

    def register_user(self, user: User, password: str) -> None:
        """注册用户"""
        with self._lock:
            self._users[user.username] = user
            self._passwords[user.username] = self._hash_password(password)

    def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """通过用户名/密码认证"""
        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            return AuthResult(False, error="Missing username or password")

        with self._lock:
            user = self._users.get(username)
            stored_hash = self._passwords.get(username)

        if user is None or stored_hash is None:
            return AuthResult(False, error="Invalid credentials")
        if not user.active:
            return AuthResult(False, error="User inactive")

        if not hmac.compare_digest(stored_hash, self._hash_password(password)):
            return AuthResult(False, error="Invalid credentials")

        return AuthResult(True, user=user)

    def get_user(self, username: str) -> Optional[User]:
        """获取用户"""
        with self._lock:
            return self._users.get(username)


class BearerTokenAuthenticator(Authenticator):
    """
    Bearer Token 认证器

    通过Bearer Token识别用户（简单的token存储，非JWT）。
    """

    def __init__(self):
        self._tokens: Dict[str, Tuple[User, float]] = {}  # token -> (user, expires_at)
        self._lock = threading.RLock()

    def issue_token(self, user: User, expires_in: float = 3600) -> str:
        """发放token"""
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + expires_in
        with self._lock:
            self._tokens[token] = (user, expires_at)
        return token

    def revoke_token(self, token: str) -> bool:
        """撤销token"""
        with self._lock:
            return self._tokens.pop(token, None) is not None

    def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """通过Bearer Token认证"""
        token = credentials.get("token")
        if not token:
            return AuthResult(False, error="Missing token")

        with self._lock:
            entry = self._tokens.get(token)

        if entry is None:
            return AuthResult(False, error="Invalid token")

        user, expires_at = entry
        if time.time() > expires_at:
            with self._lock:
                self._tokens.pop(token, None)
            return AuthResult(False, error="Token expired")
        if not user.active:
            return AuthResult(False, error="User inactive")

        return AuthResult(True, user=user)

    def cleanup_expired(self) -> int:
        """清理过期token"""
        now = time.time()
        with self._lock:
            expired = [t for t, (_, exp) in self._tokens.items() if now > exp]
            for t in expired:
                self._tokens.pop(t, None)
        return len(expired)


# ============================================================
# 授权器
# ============================================================

class Authorizer:
    """
    授权器

    基于RBAC模型进行权限检查。
    """

    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._lock = threading.RLock()
        # 加载预定义角色
        for name in ROLE_PERMISSIONS:
            role = Role.from_preset(name)
            if role:
                self._roles[name] = role

    def add_role(self, role: Role) -> None:
        """添加角色"""
        with self._lock:
            self._roles[role.name] = role

    def get_role(self, name: str) -> Optional[Role]:
        """获取角色"""
        with self._lock:
            return self._roles.get(name)

    def get_user_roles(self, user: User) -> Set[Role]:
        """获取用户的角色集合"""
        roles = set()
        with self._lock:
            for role_name in user.roles:
                role = self._roles.get(role_name)
                if role:
                    roles.add(role)
        return roles

    def check_permission(self, user: User, permission: Permission) -> bool:
        """检查用户是否有指定权限"""
        if not user.active:
            return False
        roles = self.get_user_roles(user)
        for role in roles:
            if role.has_permission(permission):
                return True
        return False

    def check_any_permission(self, user: User, permissions: Set[Permission]) -> bool:
        """检查用户是否有任一权限"""
        if not user.active:
            return False
        roles = self.get_user_roles(user)
        for role in roles:
            for perm in permissions:
                if role.has_permission(perm):
                    return True
        return False

    def list_roles(self) -> List[str]:
        """列出所有角色名"""
        with self._lock:
            return list(self._roles.keys())

    def get_permissions_for_user(self, user: User) -> Set[Permission]:
        """获取用户的所有权限"""
        perms = set()
        for role in self.get_user_roles(user):
            perms |= role.permissions
        return perms


# ============================================================
# 安全管理器
# ============================================================

class SecurityManager:
    """
    安全管理器

    整合认证、授权、审计，提供统一的安全接口。
    """

    def __init__(self):
        self._authenticators: Dict[str, Authenticator] = {}
        self._authorizer = Authorizer()
        self._audit = AuditLogger()
        self._users: Dict[str, User] = {}  # user_id -> user
        self._lock = threading.RLock()
        self._enabled = True
        self._public_paths: Set[str] = set()
        self._rate_limits: Dict[str, deque] = {}  # ip -> timestamps
        self._rate_limit_window = 60.0  # 60秒窗口
        self._rate_limit_max = 100  # 每窗口最大请求数

        # 注册默认认证器
        self._authenticators["api_key"] = APIKeyAuthenticator()
        self._authenticators["basic"] = BasicAuthAuthenticator()
        self._authenticators["bearer"] = BearerTokenAuthenticator()

    @property
    def authorizer(self) -> Authorizer:
        return self._authorizer

    @property
    def audit(self) -> AuditLogger:
        return self._audit

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """启用/禁用安全"""
        self._enabled = enabled

    def add_public_path(self, path: str) -> None:
        """添加公开路径（不需要认证）"""
        self._public_paths.add(path)

    def is_public_path(self, path: str) -> bool:
        """检查是否是公开路径"""
        if path in self._public_paths:
            return True
        # 支持通配符匹配
        for public in self._public_paths:
            if public.endswith("*") and path.startswith(public[:-1]):
                return True
        return False

    # ---------- 用户管理 ----------

    def create_user(
        self,
        username: str,
        roles: Set[str],
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> User:
        """创建用户"""
        with self._lock:
            if user_id is None:
                user_id = f"user_{int(time.time())}_{secrets.token_hex(4)}"
            user = User(
                user_id=user_id,
                username=username,
                roles=roles,
            )
            self._users[user_id] = user

            # 设置认证凭据
            if api_key:
                self._authenticators["api_key"].register_api_key(user, api_key)
            if password:
                self._authenticators["basic"].register_user(user, password)

        self._audit.log_event(
            AuditEventType.USER_CREATED,
            action="create_user",
            resource=user_id,
            username=username,
            details={"roles": list(roles)},
        )
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        with self._lock:
            return self._users.get(user_id)

    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        with self._lock:
            user = self._users.pop(user_id, None)
            if user is None:
                return False
            # 撤销API Key
            if user.api_key:
                self._authenticators["api_key"].revoke_api_key(user.api_key)

        self._audit.log_event(
            AuditEventType.USER_DELETED,
            action="delete_user",
            resource=user_id,
            username=user.username,
        )
        return True

    def list_users(self) -> List[User]:
        """列出所有用户"""
        with self._lock:
            return list(self._users.values())

    def assign_role(self, user_id: str, role_name: str) -> bool:
        """分配角色"""
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                return False
            user.roles.add(role_name)

        self._audit.log_event(
            AuditEventType.ROLE_ASSIGNED,
            action="assign_role",
            resource=user_id,
            username=user.username if user else None,
            details={"role": role_name},
        )
        return True

    def revoke_role(self, user_id: str, role_name: str) -> bool:
        """撤销角色"""
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                return False
            user.roles.discard(role_name)

        self._audit.log_event(
            AuditEventType.ROLE_REVOKED,
            action="revoke_role",
            resource=user_id,
            username=user.username if user else None,
            details={"role": role_name},
        )
        return True

    # ---------- 认证 ----------

    def authenticate(self, method: str, credentials: Dict[str, Any]) -> AuthResult:
        """认证"""
        authenticator = self._authenticators.get(method)
        if authenticator is None:
            return AuthResult(False, error=f"Unknown auth method: {method}")

        result = authenticator.authenticate(credentials)

        if result.success and result.user:
            self._audit.log_event(
                AuditEventType.LOGIN,
                action="authenticate",
                resource=method,
                user_id=result.user.user_id,
                username=result.user.username,
            )
        else:
            self._audit.log_event(
                AuditEventType.LOGIN_FAILED,
                action="authenticate",
                resource=method,
                success=False,
                details={"error": result.error},
            )

        return result

    def create_context(self, user: User) -> SecurityContext:
        """为用户创建安全上下文"""
        roles = self._authorizer.get_user_roles(user)
        return SecurityContext(user=user, roles=roles)

    # ---------- 授权 ----------

    def check_permission(self, user: User, permission: Permission) -> bool:
        """检查权限"""
        granted = self._authorizer.check_permission(user, permission)
        if not granted:
            self._audit.log_event(
                AuditEventType.PERMISSION_DENIED,
                action="check_permission",
                resource=permission.value,
                user_id=user.user_id,
                username=user.username,
                success=False,
            )
        return granted

    def require_permission(self, user: User, permission: Permission) -> None:
        """要求权限（不满足时抛异常）"""
        if not self.check_permission(user, permission):
            raise PermissionError(f"Permission denied: {permission.value}")

    # ---------- 限流 ----------

    def check_rate_limit(self, identifier: str) -> bool:
        """
        检查限流

        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        with self._lock:
            if identifier not in self._rate_limits:
                self._rate_limits[identifier] = deque()

            timestamps = self._rate_limits[identifier]
            # 清理过期时间戳
            while timestamps and now - timestamps[0] > self._rate_limit_window:
                timestamps.popleft()

            if len(timestamps) >= self._rate_limit_max:
                return False

            timestamps.append(now)
            return True

    def set_rate_limit(self, max_requests: int, window: float) -> None:
        """设置限流参数"""
        self._rate_limit_max = max_requests
        self._rate_limit_window = window

    # ---------- 便捷方法 ----------

    def create_api_key_for_user(self, user_id: str) -> Optional[str]:
        """为用户创建API Key"""
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                return None
        api_key = self._authenticators["api_key"].register_api_key(user)
        self._audit.log_event(
            AuditEventType.API_KEY_CREATED,
            action="create_api_key",
            resource=user_id,
            username=user.username,
        )
        return api_key

    def revoke_api_key(self, api_key: str) -> bool:
        """撤销API Key"""
        revoked = self._authenticators["api_key"].revoke_api_key(api_key)
        if revoked:
            self._audit.log_event(
                AuditEventType.API_KEY_REVOKED,
                action="revoke_api_key",
                resource=api_key[:8] + "...",
            )
        return revoked

    def issue_token(self, user_id: str, expires_in: float = 3600) -> Optional[str]:
        """为用户发放Bearer Token"""
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                return None
        return self._authenticators["bearer"].issue_token(user, expires_in)

    def get_stats(self) -> Dict[str, Any]:
        """获取安全统计"""
        with self._lock:
            return {
                "enabled": self._enabled,
                "user_count": len(self._users),
                "role_count": len(self._authorizer.list_roles()),
                "public_paths": list(self._public_paths),
                "audit_stats": self._audit.get_stats(),
                "rate_limit": {
                    "max": self._rate_limit_max,
                    "window": self._rate_limit_window,
                    "tracked_identifiers": len(self._rate_limits),
                },
            }

    def get_audit_events(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """获取审计事件"""
        events = self._audit.get_events(
            event_type=event_type,
            user_id=user_id,
            success=success,
            limit=limit,
        )
        return [e.to_dict() for e in events]


# ============================================================
# 便捷函数
# ============================================================

def create_security_manager() -> SecurityManager:
    """创建安全管理器"""
    return SecurityManager()


# 默认全局实例
_global_security: Optional[SecurityManager] = None
_global_security_lock = threading.Lock()


def get_global_security_manager() -> SecurityManager:
    """获取全局安全管理器"""
    global _global_security
    with _global_security_lock:
        if _global_security is None:
            _global_security = create_security_manager()
        return _global_security
