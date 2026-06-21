"""
阶段139: 安全加固 — 认证授权 测试

第一性原理验证:
1. 最小权限 — 角色权限边界
2. 纵深防御 — 多层安全
3. 可审计性 — 审计日志
4. 失败安全 — 安全失效时拒绝
5. 身份验证 — 认证机制
"""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from self_evolving_agent.core.security import (
    Permission,
    Role,
    User,
    SecurityContext,
    AuditEventType,
    AuditLogger,
    AuditEvent,
    AuthResult,
    APIKeyAuthenticator,
    BasicAuthAuthenticator,
    BearerTokenAuthenticator,
    Authorizer,
    SecurityManager,
    create_security_manager,
    get_global_security_manager,
    get_current_context,
    set_current_context,
    clear_current_context,
)


# ============================================================
# 1. Permission 和 Role 测试
# ============================================================

class TestPermissionAndRole:
    """权限和角色测试"""

    def test_permission_values(self):
        """测试权限值"""
        assert Permission.AGENT_VIEW.value == "agent:view"
        assert Permission.ADMIN.value == "admin:*"

    def test_role_has_permission(self):
        """测试角色权限检查"""
        role = Role(name="test", permissions={Permission.AGENT_VIEW, Permission.TASK_VIEW})
        assert role.has_permission(Permission.AGENT_VIEW)
        assert role.has_permission(Permission.TASK_VIEW)
        assert not role.has_permission(Permission.AGENT_CONTROL)

    def test_admin_role_has_all(self):
        """测试admin角色拥有所有权限"""
        role = Role(name="admin", permissions={Permission.ADMIN})
        assert role.has_permission(Permission.AGENT_VIEW)
        assert role.has_permission(Permission.CONFIG_EDIT)
        assert role.has_permission(Permission.SECURITY_MANAGE)

    def test_role_from_preset(self):
        """测试从预定义创建角色"""
        viewer = Role.from_preset("viewer")
        assert viewer is not None
        assert viewer.has_permission(Permission.AGENT_VIEW)
        assert not viewer.has_permission(Permission.AGENT_CONTROL)

        operator = Role.from_preset("operator")
        assert operator is not None
        assert operator.has_permission(Permission.TASK_CREATE)
        assert operator.has_permission(Permission.CONFIG_EDIT)

        admin = Role.from_preset("admin")
        assert admin is not None
        assert admin.has_permission(Permission.ADMIN)

    def test_role_from_invalid_preset(self):
        """测试无效预定义角色"""
        role = Role.from_preset("nonexistent")
        assert role is None

    def test_role_create(self):
        """测试创建角色"""
        role = Role.create("custom", {Permission.CODE_REVIEW}, "Custom role")
        assert role.name == "custom"
        assert role.description == "Custom role"
        assert role.has_permission(Permission.CODE_REVIEW)


# ============================================================
# 2. User 测试
# ============================================================

class TestUser:
    """用户测试"""

    def test_create_user(self):
        """测试创建用户"""
        user = User(user_id="u1", username="alice", roles={"viewer"})
        assert user.user_id == "u1"
        assert user.username == "alice"
        assert "viewer" in user.roles
        assert user.active is True

    def test_user_to_dict(self):
        """测试用户转字典"""
        user = User(user_id="u1", username="alice", roles={"viewer"}, api_key="secret")
        d = user.to_dict()
        assert d["user_id"] == "u1"
        assert d["username"] == "alice"
        assert "viewer" in d["roles"]
        assert d["has_api_key"] is True
        assert "api_key" not in d  # 不应暴露API Key

    def test_user_without_api_key(self):
        """测试无API Key用户"""
        user = User(user_id="u1", username="bob")
        d = user.to_dict()
        assert d["has_api_key"] is False


# ============================================================
# 3. SecurityContext 测试
# ============================================================

class TestSecurityContext:
    """安全上下文测试"""

    def test_unauthenticated_context(self):
        """测试未认证上下文"""
        ctx = SecurityContext()
        assert not ctx.authenticated
        assert ctx.user is None
        assert not ctx.has_permission(Permission.AGENT_VIEW)

    def test_authenticated_context(self):
        """测试已认证上下文"""
        user = User(user_id="u1", username="alice", roles={"viewer"})
        role = Role.from_preset("viewer")
        ctx = SecurityContext(user=user, roles={role})
        assert ctx.authenticated
        assert ctx.user_id == "u1"
        assert ctx.username == "alice"
        assert ctx.has_permission(Permission.AGENT_VIEW)
        assert not ctx.has_permission(Permission.AGENT_CONTROL)

    def test_admin_context(self):
        """测试管理员上下文"""
        user = User(user_id="u1", username="admin", roles={"admin"})
        role = Role.from_preset("admin")
        ctx = SecurityContext(user=user, roles={role})
        assert ctx.has_permission(Permission.AGENT_VIEW)
        assert ctx.has_permission(Permission.SECURITY_MANAGE)

    def test_has_any_permission(self):
        """测试任一权限检查"""
        user = User(user_id="u1", username="op", roles={"operator"})
        role = Role.from_preset("operator")
        ctx = SecurityContext(user=user, roles={role})
        assert ctx.has_any_permission({Permission.AGENT_CONTROL, Permission.SECURITY_MANAGE})
        assert not ctx.has_any_permission({Permission.SECURITY_MANAGE})

    def test_has_all_permissions(self):
        """测试所有权限检查"""
        user = User(user_id="u1", username="op", roles={"operator"})
        role = Role.from_preset("operator")
        ctx = SecurityContext(user=user, roles={role})
        assert ctx.has_all_permissions({Permission.AGENT_CONTROL, Permission.TASK_CREATE})
        assert not ctx.has_all_permissions({Permission.AGENT_CONTROL, Permission.SECURITY_MANAGE})

    def test_context_to_dict(self):
        """测试上下文转字典"""
        user = User(user_id="u1", username="alice", roles={"viewer"})
        role = Role.from_preset("viewer")
        ctx = SecurityContext(user=user, roles={role})
        d = ctx.to_dict()
        assert d["authenticated"] is True
        assert d["user_id"] == "u1"
        assert "viewer" in d["roles"]
        assert "agent:view" in d["permissions"]

    def test_thread_local_context(self):
        """测试线程局部上下文"""
        user = User(user_id="u1", username="alice", roles={"viewer"})
        role = Role.from_preset("viewer")
        ctx = SecurityContext(user=user, roles={role})
        set_current_context(ctx)
        assert get_current_context().authenticated
        clear_current_context()
        assert not get_current_context().authenticated


# ============================================================
# 4. AuditLogger 测试
# ============================================================

class TestAuditLogger:
    """审计日志测试"""

    def test_log_event(self):
        """测试记录事件"""
        logger = AuditLogger()
        event = logger.log_event(
            AuditEventType.LOGIN,
            action="login",
            resource="api_key",
            user_id="u1",
            username="alice",
        )
        assert event.event_id is not None
        assert logger.count() == 1

    def test_query_by_type(self):
        """测试按类型查询"""
        logger = AuditLogger()
        logger.log_event(AuditEventType.LOGIN, "login", "api_key")
        logger.log_event(AuditEventType.LOGIN_FAILED, "login", "api_key", success=False)
        logger.log_event(AuditEventType.LOGIN, "login", "api_key")

        logins = logger.get_events(event_type=AuditEventType.LOGIN)
        assert len(logins) == 2

    def test_query_by_user(self):
        """测试按用户查询"""
        logger = AuditLogger()
        logger.log_event(AuditEventType.LOGIN, "login", "r", user_id="u1")
        logger.log_event(AuditEventType.LOGIN, "login", "r", user_id="u2")
        events = logger.get_events(user_id="u1")
        assert len(events) == 1
        assert events[0].user_id == "u1"

    def test_query_by_success(self):
        """测试按成功状态查询"""
        logger = AuditLogger()
        logger.log_event(AuditEventType.LOGIN, "login", "r", success=True)
        logger.log_event(AuditEventType.LOGIN_FAILED, "login", "r", success=False)
        successes = logger.get_events(success=True)
        failures = logger.get_events(success=False)
        assert len(successes) == 1
        assert len(failures) == 1

    def test_max_events_limit(self):
        """测试最大事件限制"""
        logger = AuditLogger(max_events=5)
        for i in range(10):
            logger.log_event(AuditEventType.LOGIN, "login", "r")
        assert logger.count() == 5

    def test_add_handler(self):
        """测试添加处理器"""
        logger = AuditLogger()
        received = []
        logger.add_handler(lambda e: received.append(e))
        logger.log_event(AuditEventType.LOGIN, "login", "r")
        assert len(received) == 1

    def test_clear(self):
        """测试清空"""
        logger = AuditLogger()
        logger.log_event(AuditEventType.LOGIN, "login", "r")
        logger.clear()
        assert logger.count() == 0

    def test_get_stats(self):
        """测试统计"""
        logger = AuditLogger()
        logger.log_event(AuditEventType.LOGIN, "login", "r", success=True)
        logger.log_event(AuditEventType.LOGIN_FAILED, "login", "r", success=False)
        stats = logger.get_stats()
        assert stats["total"] == 2
        assert stats["failed_count"] == 1
        assert "login" in stats["by_type"]

    def test_event_to_dict(self):
        """测试事件转字典"""
        event = AuditEvent(
            event_id="e1",
            event_type=AuditEventType.LOGIN,
            user_id="u1",
            username="alice",
            action="login",
            resource="api_key",
            timestamp=time.time(),
            success=True,
        )
        d = event.to_dict()
        assert d["event_id"] == "e1"
        assert d["event_type"] == "login"
        assert d["username"] == "alice"


# ============================================================
# 5. APIKeyAuthenticator 测试
# ============================================================

class TestAPIKeyAuthenticator:
    """API Key认证器测试"""

    def test_register_and_authenticate(self):
        """测试注册和认证"""
        auth = APIKeyAuthenticator()
        user = User(user_id="u1", username="alice", roles={"viewer"})
        api_key = auth.register_api_key(user)

        result = auth.authenticate({"api_key": api_key})
        assert result.success
        assert result.user.user_id == "u1"

    def test_authenticate_invalid_key(self):
        """测试无效API Key"""
        auth = APIKeyAuthenticator()
        result = auth.authenticate({"api_key": "invalid"})
        assert not result.success
        assert "Invalid" in result.error

    def test_authenticate_missing_key(self):
        """测试缺少API Key"""
        auth = APIKeyAuthenticator()
        result = auth.authenticate({})
        assert not result.success
        assert "Missing" in result.error

    def test_authenticate_inactive_user(self):
        """测试未激活用户"""
        auth = APIKeyAuthenticator()
        user = User(user_id="u1", username="alice", roles={"viewer"}, active=False)
        api_key = auth.register_api_key(user)

        result = auth.authenticate({"api_key": api_key})
        assert not result.success
        assert "inactive" in result.error

    def test_revoke_api_key(self):
        """测试撤销API Key"""
        auth = APIKeyAuthenticator()
        user = User(user_id="u1", username="alice", roles={"viewer"})
        api_key = auth.register_api_key(user)

        assert auth.revoke_api_key(api_key)
        result = auth.authenticate({"api_key": api_key})
        assert not result.success

    def test_revoke_nonexistent_key(self):
        """测试撤销不存在的Key"""
        auth = APIKeyAuthenticator()
        assert not auth.revoke_api_key("nonexistent")

    def test_custom_api_key(self):
        """测试自定义API Key"""
        auth = APIKeyAuthenticator()
        user = User(user_id="u1", username="alice", roles={"viewer"})
        custom_key = "my_custom_key_12345"
        auth.register_api_key(user, api_key=custom_key)
        assert user.api_key == custom_key

        result = auth.authenticate({"api_key": custom_key})
        assert result.success

    def test_list_users(self):
        """测试列出用户"""
        auth = APIKeyAuthenticator()
        u1 = User(user_id="u1", username="alice", roles={"viewer"})
        u2 = User(user_id="u2", username="bob", roles={"operator"})
        auth.register_api_key(u1)
        auth.register_api_key(u2)
        users = auth.list_users()
        assert len(users) == 2


# ============================================================
# 6. BasicAuthAuthenticator 测试
# ============================================================

class TestBasicAuthAuthenticator:
    """Basic Auth认证器测试"""

    def test_register_and_authenticate(self):
        """测试注册和认证"""
        auth = BasicAuthAuthenticator()
        user = User(user_id="u1", username="alice", roles={"viewer"})
        auth.register_user(user, "password123")

        result = auth.authenticate({"username": "alice", "password": "password123"})
        assert result.success
        assert result.user.user_id == "u1"

    def test_authenticate_wrong_password(self):
        """测试错误密码"""
        auth = BasicAuthAuthenticator()
        user = User(user_id="u1", username="alice", roles={"viewer"})
        auth.register_user(user, "password123")

        result = auth.authenticate({"username": "alice", "password": "wrong"})
        assert not result.success

    def test_authenticate_nonexistent_user(self):
        """测试不存在的用户"""
        auth = BasicAuthAuthenticator()
        result = auth.authenticate({"username": "nobody", "password": "pass"})
        assert not result.success

    def test_authenticate_missing_credentials(self):
        """测试缺少凭据"""
        auth = BasicAuthAuthenticator()
        result = auth.authenticate({})
        assert not result.success

    def test_authenticate_inactive_user(self):
        """测试未激活用户"""
        auth = BasicAuthAuthenticator()
        user = User(user_id="u1", username="alice", roles={"viewer"}, active=False)
        auth.register_user(user, "password123")

        result = auth.authenticate({"username": "alice", "password": "password123"})
        assert not result.success

    def test_password_hashed(self):
        """测试密码已哈希"""
        auth = BasicAuthAuthenticator()
        user = User(user_id="u1", username="alice", roles={"viewer"})
        auth.register_user(user, "password123")
        # 存储的应该是哈希值，不是明文
        stored = auth._passwords["alice"]
        assert stored != "password123"
        assert len(stored) == 64  # SHA-256 hex


# ============================================================
# 7. BearerTokenAuthenticator 测试
# ============================================================

class TestBearerTokenAuthenticator:
    """Bearer Token认证器测试"""

    def test_issue_and_authenticate(self):
        """测试发放和认证"""
        auth = BearerTokenAuthenticator()
        user = User(user_id="u1", username="alice", roles={"viewer"})
        token = auth.issue_token(user)

        result = auth.authenticate({"token": token})
        assert result.success
        assert result.user.user_id == "u1"

    def test_authenticate_invalid_token(self):
        """测试无效token"""
        auth = BearerTokenAuthenticator()
        result = auth.authenticate({"token": "invalid"})
        assert not result.success

    def test_authenticate_missing_token(self):
        """测试缺少token"""
        auth = BearerTokenAuthenticator()
        result = auth.authenticate({})
        assert not result.success

    def test_revoke_token(self):
        """测试撤销token"""
        auth = BearerTokenAuthenticator()
        user = User(user_id="u1", username="alice", roles={"viewer"})
        token = auth.issue_token(user)

        assert auth.revoke_token(token)
        result = auth.authenticate({"token": token})
        assert not result.success

    def test_expired_token(self):
        """测试过期token"""
        auth = BearerTokenAuthenticator()
        user = User(user_id="u1", username="alice", roles={"viewer"})
        token = auth.issue_token(user, expires_in=-1)  # 已过期

        result = auth.authenticate({"token": token})
        assert not result.success
        assert "expired" in result.error

    def test_cleanup_expired(self):
        """测试清理过期token"""
        auth = BearerTokenAuthenticator()
        user = User(user_id="u1", username="alice", roles={"viewer"})
        auth.issue_token(user, expires_in=-1)
        auth.issue_token(user, expires_in=3600)

        cleaned = auth.cleanup_expired()
        assert cleaned == 1

    def test_authenticate_inactive_user(self):
        """测试未激活用户"""
        auth = BearerTokenAuthenticator()
        user = User(user_id="u1", username="alice", roles={"viewer"}, active=False)
        token = auth.issue_token(user)

        result = auth.authenticate({"token": token})
        assert not result.success


# ============================================================
# 8. Authorizer 测试
# ============================================================

class TestAuthorizer:
    """授权器测试"""

    def test_check_permission_granted(self):
        """测试权限授予"""
        auth = Authorizer()
        user = User(user_id="u1", username="alice", roles={"viewer"})
        assert auth.check_permission(user, Permission.AGENT_VIEW)

    def test_check_permission_denied(self):
        """测试权限拒绝"""
        auth = Authorizer()
        user = User(user_id="u1", username="alice", roles={"viewer"})
        assert not auth.check_permission(user, Permission.AGENT_CONTROL)

    def test_admin_has_all(self):
        """测试admin拥有所有权限"""
        auth = Authorizer()
        user = User(user_id="u1", username="admin", roles={"admin"})
        assert auth.check_permission(user, Permission.AGENT_VIEW)
        assert auth.check_permission(user, Permission.SECURITY_MANAGE)

    def test_check_any_permission(self):
        """测试任一权限"""
        auth = Authorizer()
        user = User(user_id="u1", username="op", roles={"operator"})
        assert auth.check_any_permission(user, {Permission.AGENT_CONTROL, Permission.SECURITY_MANAGE})
        assert not auth.check_any_permission(user, {Permission.SECURITY_MANAGE})

    def test_inactive_user_denied(self):
        """测试未激活用户被拒绝"""
        auth = Authorizer()
        user = User(user_id="u1", username="alice", roles={"viewer"}, active=False)
        assert not auth.check_permission(user, Permission.AGENT_VIEW)

    def test_add_custom_role(self):
        """测试添加自定义角色"""
        auth = Authorizer()
        role = Role.create("custom", {Permission.CODE_REVIEW})
        auth.add_role(role)
        user = User(user_id="u1", username="alice", roles={"custom"})
        assert auth.check_permission(user, Permission.CODE_REVIEW)
        assert not auth.check_permission(user, Permission.AGENT_VIEW)

    def test_list_roles(self):
        """测试列出角色"""
        auth = Authorizer()
        roles = auth.list_roles()
        assert "viewer" in roles
        assert "operator" in roles
        assert "admin" in roles

    def test_get_permissions_for_user(self):
        """测试获取用户权限"""
        auth = Authorizer()
        user = User(user_id="u1", username="op", roles={"operator"})
        perms = auth.get_permissions_for_user(user)
        assert Permission.TASK_CREATE in perms
        assert Permission.AGENT_CONTROL in perms


# ============================================================
# 9. SecurityManager 测试
# ============================================================

class TestSecurityManager:
    """安全管理器测试"""

    def test_create_user(self):
        """测试创建用户"""
        mgr = create_security_manager()
        user = mgr.create_user("alice", {"viewer"}, password="pass123")
        assert user.user_id is not None
        assert user.username == "alice"
        assert "viewer" in user.roles

    def test_create_user_with_api_key(self):
        """测试创建带API Key的用户"""
        mgr = create_security_manager()
        user = mgr.create_user("alice", {"viewer"}, api_key="custom_key")
        assert user.api_key == "custom_key"

    def test_authenticate_api_key(self):
        """测试API Key认证"""
        mgr = create_security_manager()
        mgr.create_user("alice", {"viewer"}, api_key="test_key")
        result = mgr.authenticate("api_key", {"api_key": "test_key"})
        assert result.success
        assert result.user.username == "alice"

    def test_authenticate_basic(self):
        """测试Basic Auth认证"""
        mgr = create_security_manager()
        mgr.create_user("alice", {"viewer"}, password="pass123")
        result = mgr.authenticate("basic", {"username": "alice", "password": "pass123"})
        assert result.success

    def test_authenticate_bearer(self):
        """测试Bearer Token认证"""
        mgr = create_security_manager()
        user = mgr.create_user("alice", {"viewer"})
        token = mgr.issue_token(user.user_id)
        assert token is not None
        result = mgr.authenticate("bearer", {"token": token})
        assert result.success

    def test_authenticate_invalid_method(self):
        """测试无效认证方法"""
        mgr = create_security_manager()
        result = mgr.authenticate("invalid", {})
        assert not result.success

    def test_check_permission(self):
        """测试权限检查"""
        mgr = create_security_manager()
        user = mgr.create_user("alice", {"viewer"})
        assert mgr.check_permission(user, Permission.AGENT_VIEW)
        assert not mgr.check_permission(user, Permission.AGENT_CONTROL)

    def test_require_permission_granted(self):
        """测试要求权限（通过）"""
        mgr = create_security_manager()
        user = mgr.create_user("alice", {"viewer"})
        mgr.require_permission(user, Permission.AGENT_VIEW)  # 不应抛异常

    def test_require_permission_denied(self):
        """测试要求权限（拒绝）"""
        mgr = create_security_manager()
        user = mgr.create_user("alice", {"viewer"})
        with pytest.raises(PermissionError):
            mgr.require_permission(user, Permission.AGENT_CONTROL)

    def test_create_context(self):
        """测试创建安全上下文"""
        mgr = create_security_manager()
        user = mgr.create_user("alice", {"viewer"})
        ctx = mgr.create_context(user)
        assert ctx.authenticated
        assert ctx.has_permission(Permission.AGENT_VIEW)

    def test_delete_user(self):
        """测试删除用户"""
        mgr = create_security_manager()
        user = mgr.create_user("alice", {"viewer"}, api_key="key1")
        assert mgr.delete_user(user.user_id)
        assert mgr.get_user(user.user_id) is None
        # API Key也应被撤销
        result = mgr.authenticate("api_key", {"api_key": "key1"})
        assert not result.success

    def test_assign_and_revoke_role(self):
        """测试分配和撤销角色"""
        mgr = create_security_manager()
        user = mgr.create_user("alice", {"viewer"})
        assert not mgr.check_permission(user, Permission.TASK_CREATE)

        mgr.assign_role(user.user_id, "operator")
        assert mgr.check_permission(user, Permission.TASK_CREATE)

        mgr.revoke_role(user.user_id, "operator")
        assert not mgr.check_permission(user, Permission.TASK_CREATE)

    def test_public_path(self):
        """测试公开路径"""
        mgr = create_security_manager()
        mgr.add_public_path("/api/status")
        assert mgr.is_public_path("/api/status")
        assert not mgr.is_public_path("/api/config")

    def test_public_path_wildcard(self):
        """测试通配符公开路径"""
        mgr = create_security_manager()
        mgr.add_public_path("/public/*")
        assert mgr.is_public_path("/public/status")
        assert mgr.is_public_path("/public/health")
        assert not mgr.is_public_path("/api/status")

    def test_enable_disable(self):
        """测试启用/禁用"""
        mgr = create_security_manager()
        assert mgr.enabled
        mgr.set_enabled(False)
        assert not mgr.enabled

    def test_rate_limit(self):
        """测试限流"""
        mgr = create_security_manager()
        mgr.set_rate_limit(max_requests=5, window=60)
        for _ in range(5):
            assert mgr.check_rate_limit("test_ip")
        # 第6次应被限流
        assert not mgr.check_rate_limit("test_ip")

    def test_rate_limit_different_identifiers(self):
        """测试不同标识符独立限流"""
        mgr = create_security_manager()
        mgr.set_rate_limit(max_requests=2, window=60)
        assert mgr.check_rate_limit("ip1")
        assert mgr.check_rate_limit("ip1")
        assert not mgr.check_rate_limit("ip1")
        # ip2不受影响
        assert mgr.check_rate_limit("ip2")

    def test_audit_logging(self):
        """测试审计日志"""
        mgr = create_security_manager()
        mgr.create_user("alice", {"viewer"}, api_key="key1")
        mgr.authenticate("api_key", {"api_key": "key1"})
        mgr.authenticate("api_key", {"api_key": "bad_key"})

        events = mgr.get_audit_events()
        assert len(events) >= 3  # user_created + login + login_failed

    def test_create_api_key_for_user(self):
        """测试为用户创建API Key"""
        mgr = create_security_manager()
        user = mgr.create_user("alice", {"viewer"})
        api_key = mgr.create_api_key_for_user(user.user_id)
        assert api_key is not None
        result = mgr.authenticate("api_key", {"api_key": api_key})
        assert result.success

    def test_revoke_api_key(self):
        """测试撤销API Key"""
        mgr = create_security_manager()
        user = mgr.create_user("alice", {"viewer"}, api_key="key1")
        assert mgr.revoke_api_key("key1")
        result = mgr.authenticate("api_key", {"api_key": "key1"})
        assert not result.success

    def test_get_stats(self):
        """测试获取统计"""
        mgr = create_security_manager()
        mgr.create_user("alice", {"viewer"})
        stats = mgr.get_stats()
        assert stats["user_count"] == 1
        assert stats["enabled"] is True
        assert "audit_stats" in stats

    def test_list_users(self):
        """测试列出用户"""
        mgr = create_security_manager()
        mgr.create_user("alice", {"viewer"})
        mgr.create_user("bob", {"operator"})
        users = mgr.list_users()
        assert len(users) == 2


# ============================================================
# 10. 第一性原理测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_least_privilege_principle(self):
        """第一性原理：最小权限 — viewer不能管理"""
        mgr = create_security_manager()
        user = mgr.create_user("viewer_user", {"viewer"})
        # viewer可以查看
        assert mgr.check_permission(user, Permission.AGENT_VIEW)
        # viewer不能管理
        assert not mgr.check_permission(user, Permission.AGENT_CONTROL)
        assert not mgr.check_permission(user, Permission.PLUGIN_MANAGE)
        assert not mgr.check_permission(user, Permission.SECURITY_MANAGE)

    def test_defense_in_depth_principle(self):
        """第一性原理：纵深防御 — 多层检查"""
        mgr = create_security_manager()
        # 第一层：认证
        result = mgr.authenticate("api_key", {"api_key": "invalid"})
        assert not result.success
        # 第二层：即使认证通过，仍需授权
        user = mgr.create_user("limited", {"viewer"})
        ctx = mgr.create_context(user)
        assert ctx.authenticated  # 认证通过
        assert not ctx.has_permission(Permission.ADMIN)  # 但无admin权限

    def test_auditability_principle(self):
        """第一性原理：可审计性 — 所有操作被记录"""
        mgr = create_security_manager()
        user = mgr.create_user("alice", {"viewer"}, api_key="key1")

        # 认证成功
        mgr.authenticate("api_key", {"api_key": "key1"})
        # 认证失败
        mgr.authenticate("api_key", {"api_key": "bad"})
        # 权限检查
        mgr.check_permission(user, Permission.AGENT_CONTROL)

        events = mgr.get_audit_events()
        # 应有: user_created, login, login_failed, permission_denied
        event_types = [e["event_type"] for e in events]
        assert "user_created" in event_types
        assert "login" in event_types
        assert "login_failed" in event_types
        assert "permission_denied" in event_types

    def test_fail_safe_principle(self):
        """第一性原理：失败安全 — 无效凭据拒绝访问"""
        mgr = create_security_manager()
        # 无效API Key
        result = mgr.authenticate("api_key", {"api_key": "invalid"})
        assert not result.success
        assert result.user is None
        # 无效Basic Auth
        result = mgr.authenticate("basic", {"username": "nobody", "password": "bad"})
        assert not result.success
        assert result.user is None

    def test_authentication_principle(self):
        """第一性原理：身份验证 — 未认证无权限"""
        ctx = SecurityContext()  # 未认证
        assert not ctx.has_permission(Permission.AGENT_VIEW)
        assert not ctx.has_permission(Permission.AGENT_CONTROL)
        assert not ctx.has_any_permission({Permission.AGENT_VIEW})

    def test_rate_limiting_principle(self):
        """第一性原理：限流防暴力破解"""
        mgr = create_security_manager()
        mgr.set_rate_limit(max_requests=3, window=60)
        # 正常请求
        for _ in range(3):
            assert mgr.check_rate_limit("attacker_ip")
        # 超出限制
        assert not mgr.check_rate_limit("attacker_ip")

    def test_role_hierarchy_principle(self):
        """第一性原理：角色层次 — admin拥有所有权限"""
        mgr = create_security_manager()
        viewer = mgr.create_user("v", {"viewer"})
        operator = mgr.create_user("o", {"operator"})
        admin = mgr.create_user("a", {"admin"})

        viewer_perms = mgr.authorizer.get_permissions_for_user(viewer)
        operator_perms = mgr.authorizer.get_permissions_for_user(operator)
        admin_perms = mgr.authorizer.get_permissions_for_user(admin)

        # admin是所有权限的超集
        assert viewer_perms < admin_perms
        assert operator_perms < admin_perms
        # admin拥有所有权限
        assert admin_perms == set(Permission)

    def test_global_manager_singleton(self):
        """测试全局管理器单例"""
        mgr1 = get_global_security_manager()
        mgr2 = get_global_security_manager()
        assert mgr1 is mgr2


# ============================================================
# 11. 边界条件测试
# ============================================================

class TestEdgeCases:
    """边界条件测试"""

    def test_empty_roles(self):
        """测试空角色"""
        user = User(user_id="u1", username="alice", roles=set())
        auth = Authorizer()
        assert not auth.check_permission(user, Permission.AGENT_VIEW)

    def test_multiple_roles(self):
        """测试多角色叠加"""
        auth = Authorizer()
        user = User(user_id="u1", username="alice", roles={"viewer", "operator"})
        perms = auth.get_permissions_for_user(user)
        # 应包含viewer和operator的所有权限
        assert Permission.AGENT_VIEW in perms  # from viewer
        assert Permission.TASK_CREATE in perms  # from operator

    def test_user_with_no_roles_has_no_permissions(self):
        """测试无角色用户无权限"""
        user = User(user_id="u1", username="alice", roles=set())
        ctx = SecurityContext(user=user, roles=set())
        assert ctx.authenticated
        assert not ctx.has_permission(Permission.AGENT_VIEW)

    def test_concurrent_user_creation(self):
        """测试并发用户创建"""
        import threading
        mgr = create_security_manager()
        errors = []

        def create_users():
            try:
                for i in range(10):
                    mgr.create_user(f"user_{i}", {"viewer"})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_users) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(mgr.list_users()) == 30

    def test_long_api_key(self):
        """测试长API Key"""
        auth = APIKeyAuthenticator()
        user = User(user_id="u1", username="alice", roles={"viewer"})
        long_key = "x" * 1000
        auth.register_api_key(user, api_key=long_key)
        result = auth.authenticate({"api_key": long_key})
        assert result.success

    def test_unicode_username(self):
        """测试Unicode用户名"""
        mgr = create_security_manager()
        user = mgr.create_user("用户名", {"viewer"}, password="密码")
        result = mgr.authenticate("basic", {"username": "用户名", "password": "密码"})
        assert result.success
