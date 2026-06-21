"""
阶段142: 多租户支持 — 租户隔离 测试

第一性原理验证:
1. 隔离性 — 租户间数据、资源、配置相互隔离
2. 公平性 — 资源分配应公平，防止单一租户耗尽资源
3. 可管理性 — 租户可被创建、配置、暂停、删除
4. 可观测性 — 租户活动可被监控和审计
5. 可扩展性 — 支持大量租户，性能不显著下降
"""

import time
import threading
import pytest

from self_evolving_agent.core.multi_tenant import (
    TenantState,
    ResourceQuota,
    Tenant,
    ResourceUsage,
    TenantContext,
    tenant_scope,
    TenantIsolation,
    TenantManager,
    create_tenant_manager,
    create_resource_quota,
    get_global_tenant_manager,
    get_current_tenant_id,
    get_current_tenant_context,
    set_tenant_context,
    clear_tenant_context,
)


# ============================================================
# TenantState 测试
# ============================================================

class TestTenantState:
    """租户状态枚举测试"""

    def test_states_exist(self):
        assert TenantState.ACTIVE
        assert TenantState.SUSPENDED
        assert TenantState.TERMINATED
        assert TenantState.PENDING

    def test_state_values(self):
        assert TenantState.ACTIVE.value == "active"
        assert TenantState.SUSPENDED.value == "suspended"
        assert TenantState.TERMINATED.value == "terminated"
        assert TenantState.PENDING.value == "pending"

    def test_state_distinct(self):
        states = {TenantState.ACTIVE, TenantState.SUSPENDED, TenantState.TERMINATED, TenantState.PENDING}
        assert len(states) == 4

    def test_state_from_value(self):
        assert TenantState("active") == TenantState.ACTIVE
        assert TenantState("suspended") == TenantState.SUSPENDED


# ============================================================
# ResourceQuota 测试
# ============================================================

class TestResourceQuota:
    """资源配额测试"""

    def test_default_quota(self):
        q = ResourceQuota()
        assert q.max_requests_per_minute == 1000
        assert q.max_concurrent_tasks == 10
        assert q.max_storage_mb == 1024
        assert q.max_users == 50
        assert q.max_plugins == 20
        assert q.custom == {}

    def test_custom_quota(self):
        q = ResourceQuota(
            max_requests_per_minute=100,
            max_concurrent_tasks=5,
            max_storage_mb=512,
            max_users=10,
            max_plugins=5,
        )
        assert q.max_requests_per_minute == 100
        assert q.max_concurrent_tasks == 5
        assert q.max_storage_mb == 512
        assert q.max_users == 10
        assert q.max_plugins == 5

    def test_quota_to_dict(self):
        q = ResourceQuota(max_requests_per_minute=200)
        d = q.to_dict()
        assert d["max_requests_per_minute"] == 200
        assert d["max_concurrent_tasks"] == 10
        assert "custom" in d

    def test_quota_from_dict(self):
        d = {
            "max_requests_per_minute": 500,
            "max_concurrent_tasks": 20,
            "max_storage_mb": 2048,
            "max_users": 100,
            "max_plugins": 40,
        }
        q = ResourceQuota.from_dict(d)
        assert q.max_requests_per_minute == 500
        assert q.max_concurrent_tasks == 20
        assert q.max_storage_mb == 2048
        assert q.max_users == 100
        assert q.max_plugins == 40

    def test_quota_from_dict_partial(self):
        d = {"max_requests_per_minute": 500}
        q = ResourceQuota.from_dict(d)
        assert q.max_requests_per_minute == 500
        assert q.max_concurrent_tasks == 10  # default

    def test_quota_roundtrip(self):
        q1 = ResourceQuota(max_requests_per_minute=300, max_users=15)
        d = q1.to_dict()
        q2 = ResourceQuota.from_dict(d)
        assert q2.max_requests_per_minute == 300
        assert q2.max_users == 15

    def test_quota_custom_field(self):
        q = ResourceQuota(custom={"feature_x": True})
        assert q.custom["feature_x"] is True

    def test_create_resource_quota_helper(self):
        q = create_resource_quota(
            max_requests_per_minute=100,
            max_concurrent_tasks=5,
        )
        assert q.max_requests_per_minute == 100
        assert q.max_concurrent_tasks == 5
        assert q.max_storage_mb == 1024  # default


# ============================================================
# Tenant 测试
# ============================================================

class TestTenant:
    """租户定义测试"""

    def test_tenant_creation(self):
        t = Tenant(tenant_id="t1", name="Acme")
        assert t.tenant_id == "t1"
        assert t.name == "Acme"
        assert t.state == TenantState.PENDING
        assert isinstance(t.quota, ResourceQuota)
        assert t.metadata == {}

    def test_tenant_active_property(self):
        t = Tenant(tenant_id="t1", name="Acme", state=TenantState.ACTIVE)
        assert t.active is True

    def test_tenant_inactive_property(self):
        t = Tenant(tenant_id="t1", name="Acme", state=TenantState.SUSPENDED)
        assert t.active is False

        t2 = Tenant(tenant_id="t2", name="Acme", state=TenantState.TERMINATED)
        assert t2.active is False

        t3 = Tenant(tenant_id="t3", name="Acme", state=TenantState.PENDING)
        assert t3.active is False

    def test_tenant_to_dict(self):
        t = Tenant(tenant_id="t1", name="Acme", state=TenantState.ACTIVE)
        d = t.to_dict()
        assert d["tenant_id"] == "t1"
        assert d["name"] == "Acme"
        assert d["state"] == "active"
        assert "quota" in d
        assert "metadata" in d
        assert "created_at" in d

    def test_tenant_with_custom_quota(self):
        q = ResourceQuota(max_requests_per_minute=100)
        t = Tenant(tenant_id="t1", name="Acme", quota=q)
        assert t.quota.max_requests_per_minute == 100

    def test_tenant_with_metadata(self):
        t = Tenant(tenant_id="t1", name="Acme", metadata={"plan": "enterprise"})
        assert t.metadata["plan"] == "enterprise"

    def test_tenant_timestamps(self):
        before = time.time()
        t = Tenant(tenant_id="t1", name="Acme")
        after = time.time()
        assert before <= t.created_at <= after
        assert t.suspended_at is None
        assert t.terminated_at is None


# ============================================================
# ResourceUsage 测试
# ============================================================

class TestResourceUsage:
    """资源使用统计测试"""

    def test_default_usage(self):
        u = ResourceUsage(tenant_id="t1")
        assert u.tenant_id == "t1"
        assert u.requests_this_minute == 0
        assert u.concurrent_tasks == 0
        assert u.storage_used_mb == 0
        assert u.user_count == 0
        assert u.plugin_count == 0

    def test_usage_to_dict(self):
        u = ResourceUsage(tenant_id="t1", concurrent_tasks=5, user_count=10)
        d = u.to_dict()
        assert d["tenant_id"] == "t1"
        assert d["concurrent_tasks"] == 5
        assert d["user_count"] == 10


# ============================================================
# TenantContext 测试
# ============================================================

class TestTenantContext:
    """租户上下文测试"""

    def test_empty_context(self):
        ctx = TenantContext()
        assert ctx.tenant_id is None
        assert ctx.tenant is None
        assert ctx.has_tenant is False

    def test_context_with_tenant_id(self):
        ctx = TenantContext(tenant_id="t1")
        assert ctx.tenant_id == "t1"
        assert ctx.has_tenant is True

    def test_context_with_tenant(self):
        tenant = Tenant(tenant_id="t1", name="Acme")
        ctx = TenantContext(tenant_id="t1", tenant=tenant)
        assert ctx.tenant is not None
        assert ctx.tenant.name == "Acme"

    def test_context_to_dict(self):
        ctx = TenantContext(tenant_id="t1")
        d = ctx.to_dict()
        assert d["tenant_id"] == "t1"
        assert d["has_tenant"] is True


class TestTenantContextFunctions:
    """租户上下文函数测试"""

    def setup_method(self):
        clear_tenant_context()

    def teardown_method(self):
        clear_tenant_context()

    def test_get_current_tenant_id_no_context(self):
        assert get_current_tenant_id() is None

    def test_get_current_tenant_context_no_context(self):
        ctx = get_current_tenant_context()
        assert ctx.has_tenant is False

    def test_set_and_get_context(self):
        ctx = TenantContext(tenant_id="t1")
        set_tenant_context(ctx)
        assert get_current_tenant_id() == "t1"

    def test_clear_context(self):
        ctx = TenantContext(tenant_id="t1")
        set_tenant_context(ctx)
        clear_tenant_context()
        assert get_current_tenant_id() is None


class TestTenantScope:
    """租户作用域测试"""

    def setup_method(self):
        clear_tenant_context()

    def teardown_method(self):
        clear_tenant_context()

    def test_scope_sets_context(self):
        with tenant_scope("t1"):
            assert get_current_tenant_id() == "t1"

    def test_scope_clears_after_exit(self):
        with tenant_scope("t1"):
            assert get_current_tenant_id() == "t1"
        assert get_current_tenant_id() is None

    def test_scope_returns_context(self):
        with tenant_scope("t1") as ctx:
            assert ctx.tenant_id == "t1"
            assert ctx.has_tenant is True

    def test_scope_with_tenant(self):
        tenant = Tenant(tenant_id="t1", name="Acme")
        with tenant_scope("t1", tenant) as ctx:
            assert ctx.tenant is not None
            assert ctx.tenant.name == "Acme"

    def test_nested_scopes(self):
        with tenant_scope("t1"):
            assert get_current_tenant_id() == "t1"
            with tenant_scope("t2"):
                assert get_current_tenant_id() == "t2"
            assert get_current_tenant_id() == "t1"
        assert get_current_tenant_id() is None

    def test_scope_restores_previous_context(self):
        outer_ctx = TenantContext(tenant_id="outer")
        set_tenant_context(outer_ctx)
        with tenant_scope("inner"):
            assert get_current_tenant_id() == "inner"
        assert get_current_tenant_id() == "outer"

    def test_scope_exception_still_clears(self):
        with pytest.raises(ValueError):
            with tenant_scope("t1"):
                raise ValueError("test error")
        assert get_current_tenant_id() is None


# ============================================================
# TenantIsolation 测试
# ============================================================

class TestTenantIsolation:
    """租户隔离器测试"""

    def test_set_and_get_data(self):
        iso = TenantIsolation()
        iso.set_data("t1", "key1", "value1")
        assert iso.get_data("t1", "key1") == "value1"

    def test_get_data_default(self):
        iso = TenantIsolation()
        assert iso.get_data("t1", "missing") is None
        assert iso.get_data("t1", "missing", "default") == "default"

    def test_delete_data(self):
        iso = TenantIsolation()
        iso.set_data("t1", "key1", "value1")
        assert iso.delete_data("t1", "key1") is True
        assert iso.get_data("t1", "key1") is None

    def test_delete_nonexistent_data(self):
        iso = TenantIsolation()
        assert iso.delete_data("t1", "missing") is False

    def test_get_all_data(self):
        iso = TenantIsolation()
        iso.set_data("t1", "key1", "value1")
        iso.set_data("t1", "key2", "value2")
        all_data = iso.get_all_data("t1")
        assert all_data == {"key1": "value1", "key2": "value2"}

    def test_get_all_data_empty(self):
        iso = TenantIsolation()
        assert iso.get_all_data("t1") == {}

    def test_clear_tenant(self):
        iso = TenantIsolation()
        iso.set_data("t1", "key1", "value1")
        iso.increment_counter("t1", "counter1")
        iso.clear_tenant("t1")
        assert iso.get_all_data("t1") == {}
        assert iso.get_counter("t1", "counter1") == 0

    def test_increment_counter(self):
        iso = TenantIsolation()
        assert iso.increment_counter("t1", "counter1") == 1
        assert iso.increment_counter("t1", "counter1") == 2
        assert iso.increment_counter("t1", "counter1", 5) == 7

    def test_get_counter_default(self):
        iso = TenantIsolation()
        assert iso.get_counter("t1", "missing") == 0

    def test_reset_counter(self):
        iso = TenantIsolation()
        iso.increment_counter("t1", "counter1", 5)
        iso.reset_counter("t1", "counter1")
        assert iso.get_counter("t1", "counter1") == 0

    def test_get_all_counters(self):
        iso = TenantIsolation()
        iso.increment_counter("t1", "c1", 5)
        iso.increment_counter("t1", "c2", 10)
        counters = iso.get_all_counters("t1")
        assert counters == {"c1": 5, "c2": 10}

    def test_list_tenants(self):
        iso = TenantIsolation()
        iso.set_data("t1", "k", "v")
        iso.increment_counter("t2", "c")
        tenants = set(iso.list_tenants())
        assert "t1" in tenants
        assert "t2" in tenants

    def test_get_stats(self):
        iso = TenantIsolation()
        iso.set_data("t1", "k1", "v1")
        iso.set_data("t2", "k1", "v1")
        iso.increment_counter("t1", "c1")
        stats = iso.get_stats()
        assert stats["tenant_count"] == 2
        assert stats["total_data_keys"] == 2
        assert stats["total_counters"] == 1

    def test_isolation_between_tenants(self):
        """第一性原理: 隔离性 — 租户间数据隔离"""
        iso = TenantIsolation()
        iso.set_data("t1", "key", "value_t1")
        iso.set_data("t2", "key", "value_t2")
        assert iso.get_data("t1", "key") == "value_t1"
        assert iso.get_data("t2", "key") == "value_t2"

    def test_counter_isolation_between_tenants(self):
        """第一性原理: 隔离性 — 计数器隔离"""
        iso = TenantIsolation()
        iso.increment_counter("t1", "calls", 10)
        iso.increment_counter("t2", "calls", 20)
        assert iso.get_counter("t1", "calls") == 10
        assert iso.get_counter("t2", "calls") == 20

    def test_delete_t1_does_not_affect_t2(self):
        iso = TenantIsolation()
        iso.set_data("t1", "key", "value1")
        iso.set_data("t2", "key", "value2")
        iso.clear_tenant("t1")
        assert iso.get_data("t2", "key") == "value2"


# ============================================================
# TenantManager 生命周期测试
# ============================================================

class TestTenantManagerLifecycle:
    """租户管理器生命周期测试"""

    def test_create_tenant(self):
        mgr = create_tenant_manager()
        t = mgr.create_tenant("Acme")
        assert t.name == "Acme"
        assert t.tenant_id.startswith("tenant_")
        assert t.state == TenantState.ACTIVE
        assert mgr.exists(t.tenant_id)

    def test_create_tenant_pending(self):
        mgr = create_tenant_manager()
        t = mgr.create_tenant("Acme", activate=False)
        assert t.state == TenantState.PENDING

    def test_create_tenant_with_custom_id(self):
        mgr = create_tenant_manager()
        t = mgr.create_tenant("Acme", tenant_id="custom_id")
        assert t.tenant_id == "custom_id"

    def test_create_tenant_duplicate_id_raises(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        with pytest.raises(ValueError):
            mgr.create_tenant("Acme2", tenant_id="t1")

    def test_create_tenant_with_quota(self):
        mgr = create_tenant_manager()
        q = create_resource_quota(max_requests_per_minute=100)
        t = mgr.create_tenant("Acme", quota=q)
        assert t.quota.max_requests_per_minute == 100

    def test_create_tenant_with_metadata(self):
        mgr = create_tenant_manager()
        t = mgr.create_tenant("Acme", metadata={"plan": "pro"})
        assert t.metadata["plan"] == "pro"

    def test_get_tenant(self):
        mgr = create_tenant_manager()
        t = mgr.create_tenant("Acme", tenant_id="t1")
        fetched = mgr.get_tenant("t1")
        assert fetched is not None
        assert fetched.name == "Acme"

    def test_get_nonexistent_tenant(self):
        mgr = create_tenant_manager()
        assert mgr.get_tenant("missing") is None

    def test_list_tenants(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("A", tenant_id="t1")
        mgr.create_tenant("B", tenant_id="t2")
        tenants = mgr.list_tenants()
        assert len(tenants) == 2

    def test_list_tenants_by_state(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("A", tenant_id="t1")
        mgr.create_tenant("B", tenant_id="t2")
        mgr.suspend_tenant("t2")
        active = mgr.list_tenants(state=TenantState.ACTIVE)
        suspended = mgr.list_tenants(state=TenantState.SUSPENDED)
        assert len(active) == 1
        assert len(suspended) == 1

    def test_update_tenant_name(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        t = mgr.update_tenant("t1", name="NewName")
        assert t.name == "NewName"

    def test_update_tenant_quota(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        new_quota = create_resource_quota(max_requests_per_minute=500)
        t = mgr.update_tenant("t1", quota=new_quota)
        assert t.quota.max_requests_per_minute == 500

    def test_update_tenant_metadata(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1", metadata={"a": 1})
        t = mgr.update_tenant("t1", metadata={"b": 2})
        assert t.metadata["a"] == 1
        assert t.metadata["b"] == 2

    def test_update_nonexistent_tenant(self):
        mgr = create_tenant_manager()
        assert mgr.update_tenant("missing", name="X") is None

    def test_suspend_tenant(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        assert mgr.suspend_tenant("t1") is True
        t = mgr.get_tenant("t1")
        assert t.state == TenantState.SUSPENDED
        assert t.suspended_at is not None

    def test_suspend_nonexistent(self):
        mgr = create_tenant_manager()
        assert mgr.suspend_tenant("missing") is False

    def test_resume_tenant(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.suspend_tenant("t1")
        assert mgr.resume_tenant("t1") is True
        t = mgr.get_tenant("t1")
        assert t.state == TenantState.ACTIVE
        assert t.suspended_at is None

    def test_resume_nonexistent(self):
        mgr = create_tenant_manager()
        assert mgr.resume_tenant("missing") is False

    def test_terminate_tenant(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        assert mgr.terminate_tenant("t1") is True
        t = mgr.get_tenant("t1")
        assert t.state == TenantState.TERMINATED
        assert t.terminated_at is not None

    def test_terminate_clears_isolation(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.set_tenant_data("t1", "key", "value")
        mgr.terminate_tenant("t1")
        # 数据应被清理
        assert mgr.get_tenant_data("t1", "key") is None

    def test_terminate_nonexistent(self):
        mgr = create_tenant_manager()
        assert mgr.terminate_tenant("missing") is False

    def test_delete_tenant(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        assert mgr.delete_tenant("t1") is True
        assert not mgr.exists("t1")

    def test_delete_nonexistent(self):
        mgr = create_tenant_manager()
        assert mgr.delete_tenant("missing") is False

    def test_is_active(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        assert mgr.is_active("t1") is True
        mgr.suspend_tenant("t1")
        assert mgr.is_active("t1") is False

    def test_is_active_nonexistent(self):
        mgr = create_tenant_manager()
        assert mgr.is_active("missing") is False

    def test_exists(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        assert mgr.exists("t1") is True
        assert mgr.exists("missing") is False


# ============================================================
# TenantManager 配额检查测试
# ============================================================

class TestTenantManagerQuota:
    """租户管理器配额检查测试"""

    def test_check_quota_unknown_tenant(self):
        mgr = create_tenant_manager()
        allowed, msg = mgr.check_quota("missing", "requests_per_minute")
        assert allowed is False
        assert "not found" in msg.lower()

    def test_check_quota_inactive_tenant(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.suspend_tenant("t1")
        allowed, msg = mgr.check_quota("t1", "requests_per_minute")
        assert allowed is False
        assert "not active" in msg.lower()

    def test_check_quota_requests_allowed(self):
        mgr = create_tenant_manager()
        q = create_resource_quota(max_requests_per_minute=100)
        mgr.create_tenant("Acme", tenant_id="t1", quota=q)
        allowed, msg = mgr.check_quota("t1", "requests_per_minute")
        assert allowed is True
        assert msg is None

    def test_check_quota_requests_exceeded(self):
        mgr = create_tenant_manager()
        q = create_resource_quota(max_requests_per_minute=5)
        mgr.create_tenant("Acme", tenant_id="t1", quota=q)
        for _ in range(5):
            mgr.record_request("t1")
        allowed, msg = mgr.check_quota("t1", "requests_per_minute")
        assert allowed is False
        assert "rate limit" in msg.lower()

    def test_check_quota_concurrent_tasks(self):
        mgr = create_tenant_manager()
        q = create_resource_quota(max_concurrent_tasks=2)
        mgr.create_tenant("Acme", tenant_id="t1", quota=q)
        mgr.record_task_start("t1")
        mgr.record_task_start("t1")
        allowed, msg = mgr.check_quota("t1", "concurrent_tasks")
        assert allowed is False
        assert "concurrent" in msg.lower()

    def test_check_quota_storage(self):
        mgr = create_tenant_manager()
        q = create_resource_quota(max_storage_mb=100)
        mgr.create_tenant("Acme", tenant_id="t1", quota=q)
        mgr.record_storage_use("t1", 95)
        allowed, msg = mgr.check_quota("t1", "storage", amount=10)
        assert allowed is False
        assert "storage" in msg.lower()

    def test_check_quota_users(self):
        mgr = create_tenant_manager()
        q = create_resource_quota(max_users=5)
        mgr.create_tenant("Acme", tenant_id="t1", quota=q)
        mgr.record_user_count("t1", 5)
        allowed, msg = mgr.check_quota("t1", "users")
        assert allowed is False
        assert "user" in msg.lower()

    def test_check_quota_plugins(self):
        mgr = create_tenant_manager()
        q = create_resource_quota(max_plugins=3)
        mgr.create_tenant("Acme", tenant_id="t1", quota=q)
        mgr.record_plugin_count("t1", 3)
        allowed, msg = mgr.check_quota("t1", "plugins")
        assert allowed is False
        assert "plugin" in msg.lower()

    def test_check_quota_unknown_resource(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        # 未知资源类型默认允许
        allowed, msg = mgr.check_quota("t1", "unknown_resource")
        assert allowed is True

    def test_record_request_updates_usage(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.record_request("t1")
        mgr.record_request("t1")
        usage = mgr.get_usage("t1")
        assert usage.last_request_time > 0

    def test_record_task_start_end(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.record_task_start("t1")
        mgr.record_task_start("t1")
        usage = mgr.get_usage("t1")
        assert usage.concurrent_tasks == 2
        mgr.record_task_end("t1")
        usage = mgr.get_usage("t1")
        assert usage.concurrent_tasks == 1

    def test_record_task_end_below_zero(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.record_task_end("t1")  # 不应变为负
        usage = mgr.get_usage("t1")
        assert usage.concurrent_tasks == 0

    def test_record_storage_use(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.record_storage_use("t1", 50.5)
        usage = mgr.get_usage("t1")
        assert usage.storage_used_mb == 50.5

    def test_record_user_count(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.record_user_count("t1", 10)
        usage = mgr.get_usage("t1")
        assert usage.user_count == 10

    def test_record_plugin_count(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.record_plugin_count("t1", 5)
        usage = mgr.get_usage("t1")
        assert usage.plugin_count == 5

    def test_get_usage_nonexistent(self):
        mgr = create_tenant_manager()
        assert mgr.get_usage("missing") is None

    def test_rate_limit_window_expires(self):
        """第一性原理: 公平性 — 限流窗口过期后允许新请求"""
        mgr = create_tenant_manager()
        q = create_resource_quota(max_requests_per_minute=3)
        mgr.create_tenant("Acme", tenant_id="t1", quota=q)
        # 填满配额
        for _ in range(3):
            mgr.record_request("t1")
        allowed, _ = mgr.check_quota("t1", "requests_per_minute")
        assert allowed is False
        # 手动修改历史记录，模拟过期
        with mgr._lock:
            mgr._request_history["t1"] = [time.time() - 120]  # 2分钟前
        allowed, _ = mgr.check_quota("t1", "requests_per_minute")
        assert allowed is True


# ============================================================
# TenantManager 数据隔离测试
# ============================================================

class TestTenantManagerIsolation:
    """租户管理器数据隔离测试"""

    def test_set_and_get_tenant_data(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        assert mgr.set_tenant_data("t1", "key", "value") is True
        assert mgr.get_tenant_data("t1", "key") == "value"

    def test_get_tenant_data_default(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        assert mgr.get_tenant_data("t1", "missing", "default") == "default"

    def test_delete_tenant_data(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.set_tenant_data("t1", "key", "value")
        assert mgr.delete_tenant_data("t1", "key") is True
        assert mgr.get_tenant_data("t1", "key") is None

    def test_set_data_nonexistent_tenant(self):
        mgr = create_tenant_manager()
        assert mgr.set_tenant_data("missing", "key", "value") is False

    def test_get_data_nonexistent_tenant(self):
        mgr = create_tenant_manager()
        assert mgr.get_tenant_data("missing", "key", "default") == "default"

    def test_delete_data_nonexistent_tenant(self):
        mgr = create_tenant_manager()
        assert mgr.delete_tenant_data("missing", "key") is False

    def test_data_isolation_between_tenants(self):
        """第一性原理: 隔离性 — 不同租户数据隔离"""
        mgr = create_tenant_manager()
        mgr.create_tenant("A", tenant_id="t1")
        mgr.create_tenant("B", tenant_id="t2")
        mgr.set_tenant_data("t1", "secret", "t1_secret")
        mgr.set_tenant_data("t2", "secret", "t2_secret")
        assert mgr.get_tenant_data("t1", "secret") == "t1_secret"
        assert mgr.get_tenant_data("t2", "secret") == "t2_secret"

    def test_get_isolation(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        iso = mgr.get_isolation("t1")
        assert iso is not None

    def test_get_isolation_nonexistent(self):
        mgr = create_tenant_manager()
        assert mgr.get_isolation("missing") is None

    def test_terminate_clears_data(self):
        """第一性原理: 隔离性 — 终止租户清理数据"""
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.set_tenant_data("t1", "key", "value")
        mgr.terminate_tenant("t1")
        assert mgr.get_tenant_data("t1", "key") is None


# ============================================================
# TenantManager 上下文测试
# ============================================================

class TestTenantManagerContext:
    """租户管理器上下文测试"""

    def setup_method(self):
        clear_tenant_context()

    def teardown_method(self):
        clear_tenant_context()

    def test_create_context(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        ctx = mgr.create_context("t1")
        assert ctx.tenant_id == "t1"
        assert ctx.tenant is not None

    def test_create_context_nonexistent(self):
        mgr = create_tenant_manager()
        ctx = mgr.create_context("missing")
        assert ctx.tenant_id == "missing"
        assert ctx.tenant is None

    def test_execute_in_tenant_scope(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")

        def get_tid():
            return get_current_tenant_id()

        result = mgr.execute_in_tenant_scope("t1", get_tid)
        assert result == "t1"

    def test_execute_in_tenant_scope_nonexistent(self):
        mgr = create_tenant_manager()
        with pytest.raises(ValueError):
            mgr.execute_in_tenant_scope("missing", lambda: None)

    def test_execute_in_tenant_scope_inactive(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.suspend_tenant("t1")
        with pytest.raises(RuntimeError):
            mgr.execute_in_tenant_scope("t1", lambda: None)

    def test_execute_in_tenant_scope_with_args(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")

        def add(a, b):
            return a + b

        result = mgr.execute_in_tenant_scope("t1", add, 3, 4)
        assert result == 7

    def test_execute_in_tenant_scope_clears_after(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.execute_in_tenant_scope("t1", lambda: None)
        assert get_current_tenant_id() is None


# ============================================================
# TenantManager 回调测试
# ============================================================

class TestTenantManagerCallbacks:
    """租户管理器回调测试"""

    def test_on_create_callback(self):
        mgr = create_tenant_manager()
        events = []
        mgr.set_callbacks(on_create=lambda t: events.append(("create", t.tenant_id)))
        mgr.create_tenant("Acme", tenant_id="t1")
        assert events == [("create", "t1")]

    def test_on_suspend_callback(self):
        mgr = create_tenant_manager()
        events = []
        mgr.set_callbacks(on_suspend=lambda t: events.append(("suspend", t.tenant_id)))
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.suspend_tenant("t1")
        assert events == [("suspend", "t1")]

    def test_on_terminate_callback(self):
        mgr = create_tenant_manager()
        events = []
        mgr.set_callbacks(on_terminate=lambda t: events.append(("terminate", t.tenant_id)))
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.terminate_tenant("t1")
        assert events == [("terminate", "t1")]

    def test_callback_exception_swallowed(self):
        """回调异常不应影响主流程"""
        mgr = create_tenant_manager()
        def bad_callback(t):
            raise RuntimeError("callback error")
        mgr.set_callbacks(on_create=bad_callback)
        t = mgr.create_tenant("Acme", tenant_id="t1")
        assert t.tenant_id == "t1"

    def test_callback_properties(self):
        mgr = create_tenant_manager()
        cb = lambda t: None
        mgr.set_callbacks(on_create=cb, on_suspend=cb, on_terminate=cb)
        assert mgr.on_create is cb
        assert mgr.on_suspend is cb
        assert mgr.on_terminate is cb


# ============================================================
# TenantManager 统计测试
# ============================================================

class TestTenantManagerStats:
    """租户管理器统计测试"""

    def test_get_stats_empty(self):
        mgr = create_tenant_manager()
        stats = mgr.get_stats()
        assert stats["total_tenants"] == 0
        assert stats["by_state"] == {}

    def test_get_stats_with_tenants(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("A", tenant_id="t1")
        mgr.create_tenant("B", tenant_id="t2")
        mgr.suspend_tenant("t2")
        stats = mgr.get_stats()
        assert stats["total_tenants"] == 2
        assert stats["by_state"]["active"] == 1
        assert stats["by_state"]["suspended"] == 1

    def test_get_tenant_summary(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.set_tenant_data("t1", "key1", "value1")
        mgr.set_tenant_data("t1", "key2", "value2")
        summary = mgr.get_tenant_summary("t1")
        assert summary is not None
        assert summary["name"] == "Acme"
        assert summary["data_keys"] == 2
        assert "usage" in summary

    def test_get_tenant_summary_nonexistent(self):
        mgr = create_tenant_manager()
        assert mgr.get_tenant_summary("missing") is None


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_isolation_principle(self):
        """第一性原理: 隔离性 — 租户间数据、资源、配置相互隔离"""
        mgr = create_tenant_manager()
        mgr.create_tenant("A", tenant_id="t1", quota=create_resource_quota(max_requests_per_minute=10))
        mgr.create_tenant("B", tenant_id="t2", quota=create_resource_quota(max_requests_per_minute=100))

        # 数据隔离
        mgr.set_tenant_data("t1", "config", {"x": 1})
        mgr.set_tenant_data("t2", "config", {"x": 2})
        assert mgr.get_tenant_data("t1", "config") == {"x": 1}
        assert mgr.get_tenant_data("t2", "config") == {"x": 2}

        # 配额隔离
        for _ in range(10):
            mgr.record_request("t1")
        allowed_t1, _ = mgr.check_quota("t1", "requests_per_minute")
        allowed_t2, _ = mgr.check_quota("t2", "requests_per_minute")
        assert allowed_t1 is False  # t1已满
        assert allowed_t2 is True   # t2未受影响

    def test_fairness_principle(self):
        """第一性原理: 公平性 — 资源分配应公平"""
        mgr = create_tenant_manager()
        # 不同租户不同配额
        mgr.create_tenant("Free", tenant_id="free", quota=create_resource_quota(max_requests_per_minute=10))
        mgr.create_tenant("Pro", tenant_id="pro", quota=create_resource_quota(max_requests_per_minute=1000))

        # 每个租户都被自己的配额约束
        for _ in range(10):
            mgr.record_request("free")
        allowed_free, _ = mgr.check_quota("free", "requests_per_minute")
        assert allowed_free is False

        for _ in range(10):
            mgr.record_request("pro")
        allowed_pro, _ = mgr.check_quota("pro", "requests_per_minute")
        assert allowed_pro is True

    def test_manageability_principle(self):
        """第一性原理: 可管理性 — 租户可被创建、配置、暂停、删除"""
        mgr = create_tenant_manager()
        # 创建
        t = mgr.create_tenant("Acme", tenant_id="t1")
        assert mgr.exists("t1")
        # 配置
        mgr.update_tenant("t1", name="NewName", quota=create_resource_quota(max_users=100))
        t = mgr.get_tenant("t1")
        assert t.name == "NewName"
        assert t.quota.max_users == 100
        # 暂停
        mgr.suspend_tenant("t1")
        assert not mgr.is_active("t1")
        # 恢复
        mgr.resume_tenant("t1")
        assert mgr.is_active("t1")
        # 终止
        mgr.terminate_tenant("t1")
        t = mgr.get_tenant("t1")
        assert t.state == TenantState.TERMINATED
        # 删除
        mgr.delete_tenant("t1")
        assert not mgr.exists("t1")

    def test_observability_principle(self):
        """第一性原理: 可观测性 — 租户活动可被监控和审计"""
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.record_request("t1")
        mgr.record_task_start("t1")
        mgr.record_storage_use("t1", 50)

        usage = mgr.get_usage("t1")
        assert usage.concurrent_tasks == 1
        assert usage.storage_used_mb == 50
        assert usage.last_request_time > 0

        summary = mgr.get_tenant_summary("t1")
        assert summary is not None
        assert "usage" in summary

        stats = mgr.get_stats()
        assert stats["total_tenants"] == 1

    def test_scalability_principle(self):
        """第一性原理: 可扩展性 — 支持大量租户"""
        mgr = create_tenant_manager()
        # 创建100个租户
        for i in range(100):
            mgr.create_tenant(f"Tenant_{i}", tenant_id=f"t{i}")
        assert len(mgr.list_tenants()) == 100
        # 每个租户独立操作
        for i in range(100):
            mgr.set_tenant_data(f"t{i}", "id", i)
        for i in range(100):
            assert mgr.get_tenant_data(f"t{i}", "id") == i
        # 统计正确
        stats = mgr.get_stats()
        assert stats["total_tenants"] == 100


# ============================================================
# 线程安全测试
# ============================================================

class TestThreadSafety:
    """线程安全测试"""

    def test_concurrent_create_different_tenants(self):
        mgr = create_tenant_manager()
        errors = []

        def create_tenant(tid):
            try:
                mgr.create_tenant(f"Tenant_{tid}", tenant_id=f"t{tid}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_tenant, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(mgr.list_tenants()) == 20

    def test_concurrent_data_access(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")

        def increment():
            for _ in range(100):
                iso = mgr.get_isolation("t1")
                if iso:
                    iso.increment_counter("t1", "counter")

        threads = [threading.Thread(target=increment) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        iso = mgr.get_isolation("t1")
        assert iso.get_counter("t1", "counter") == 500

    def test_concurrent_scope_context(self):
        """不同线程的租户上下文互不干扰"""
        mgr = create_tenant_manager()
        mgr.create_tenant("A", tenant_id="t1")
        mgr.create_tenant("B", tenant_id="t2")

        results = {}
        barrier = threading.Barrier(2)

        def worker(tid):
            barrier.wait()
            with tenant_scope(tid):
                time.sleep(0.05)
                results[tid] = get_current_tenant_id()

        t1 = threading.Thread(target=worker, args=("t1",))
        t2 = threading.Thread(target=worker, args=("t2",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results["t1"] == "t1"
        assert results["t2"] == "t2"


# ============================================================
# 边界条件测试
# ============================================================

class TestEdgeCases:
    """边界条件测试"""

    def test_empty_tenant_name(self):
        mgr = create_tenant_manager()
        t = mgr.create_tenant("", tenant_id="t1")
        assert t.name == ""

    def test_tenant_with_special_chars(self):
        mgr = create_tenant_manager()
        t = mgr.create_tenant("Acme Corp. LLC!", tenant_id="t1")
        assert t.name == "Acme Corp. LLC!"

    def test_quota_zero_values(self):
        mgr = create_tenant_manager()
        q = create_resource_quota(
            max_requests_per_minute=0,
            max_concurrent_tasks=0,
            max_storage_mb=0,
            max_users=0,
            max_plugins=0,
        )
        mgr.create_tenant("Acme", tenant_id="t1", quota=q)
        allowed, _ = mgr.check_quota("t1", "requests_per_minute")
        assert allowed is False

    def test_large_metadata(self):
        mgr = create_tenant_manager()
        large_meta = {f"key_{i}": f"value_{i}" for i in range(100)}
        t = mgr.create_tenant("Acme", tenant_id="t1", metadata=large_meta)
        assert len(t.metadata) == 100

    def test_data_with_none_value(self):
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")
        mgr.set_tenant_data("t1", "none_key", None)
        # None值应能被正确读取
        assert mgr.get_tenant_data("t1", "none_key") is None
        # 但与默认值无法区分
        assert mgr.get_tenant_data("t1", "missing") is None

    def test_counter_negative_increment(self):
        iso = TenantIsolation()
        iso.increment_counter("t1", "c1", 10)
        iso.increment_counter("t1", "c1", -3)
        assert iso.get_counter("t1", "c1") == 7

    def test_global_tenant_manager_singleton(self):
        mgr1 = get_global_tenant_manager()
        mgr2 = get_global_tenant_manager()
        assert mgr1 is mgr2


# ============================================================
# 集成场景测试
# ============================================================

class TestIntegrationScenarios:
    """集成场景测试"""

    def test_full_tenant_lifecycle(self):
        """完整租户生命周期"""
        mgr = create_tenant_manager()
        # 1. 创建
        t = mgr.create_tenant("Acme", tenant_id="t1", quota=create_resource_quota(max_users=10))
        assert mgr.is_active("t1")

        # 2. 配置数据
        mgr.set_tenant_data("t1", "theme", "dark")
        mgr.set_tenant_data("t1", "locale", "zh-CN")

        # 3. 使用资源
        mgr.record_user_count("t1", 5)
        mgr.record_request("t1")
        mgr.record_task_start("t1")

        # 4. 检查配额
        allowed, _ = mgr.check_quota("t1", "users")
        assert allowed is True

        # 5. 暂停
        mgr.suspend_tenant("t1")
        allowed, _ = mgr.check_quota("t1", "users")
        assert allowed is False  # 暂停后不允许

        # 6. 恢复
        mgr.resume_tenant("t1")
        allowed, _ = mgr.check_quota("t1", "users")
        assert allowed is True

        # 7. 终止
        mgr.terminate_tenant("t1")
        assert not mgr.is_active("t1")
        # 数据被清理
        assert mgr.get_tenant_data("t1", "theme") is None

    def test_multi_tenant_resource_sharing(self):
        """多租户资源共享场景"""
        mgr = create_tenant_manager()
        mgr.create_tenant("A", tenant_id="t1", quota=create_resource_quota(max_concurrent_tasks=2))
        mgr.create_tenant("B", tenant_id="t2", quota=create_resource_quota(max_concurrent_tasks=5))

        # t1用满2个并发
        mgr.record_task_start("t1")
        mgr.record_task_start("t1")
        allowed_t1, _ = mgr.check_quota("t1", "concurrent_tasks")
        assert allowed_t1 is False

        # t2还能用5个
        for _ in range(5):
            mgr.record_task_start("t2")
        allowed_t2, _ = mgr.check_quota("t2", "concurrent_tasks")
        assert allowed_t2 is False

        # 释放t1的一个任务
        mgr.record_task_end("t1")
        allowed_t1, _ = mgr.check_quota("t1", "concurrent_tasks")
        assert allowed_t1 is True

    def test_tenant_context_workflow(self):
        """租户上下文工作流"""
        mgr = create_tenant_manager()
        mgr.create_tenant("Acme", tenant_id="t1")

        # 在租户作用域内执行操作
        def workflow():
            tid = get_current_tenant_id()
            assert tid == "t1"
            # 在作用域内访问租户数据
            mgr.set_tenant_data("t1", "workflow_done", True)
            return "success"

        result = mgr.execute_in_tenant_scope("t1", workflow)
        assert result == "success"
        assert mgr.get_tenant_data("t1", "workflow_done") is True

    def test_audit_via_callbacks(self):
        """通过回调实现审计"""
        mgr = create_tenant_manager()
        audit_log = []
        mgr.set_callbacks(
            on_create=lambda t: audit_log.append(f"created:{t.tenant_id}"),
            on_suspend=lambda t: audit_log.append(f"suspended:{t.tenant_id}"),
            on_terminate=lambda t: audit_log.append(f"terminated:{t.tenant_id}"),
        )
        mgr.create_tenant("A", tenant_id="t1")
        mgr.suspend_tenant("t1")
        mgr.resume_tenant("t1")
        mgr.terminate_tenant("t1")

        assert "created:t1" in audit_log
        assert "suspended:t1" in audit_log
        assert "terminated:t1" in audit_log
