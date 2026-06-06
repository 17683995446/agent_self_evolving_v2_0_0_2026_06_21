"""
阶段50测试: 多租户接口标准化
"""
import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.multi_tenant import (
    Tenant, TenantStatus, TenantContext, TenantManager,
    create_tenant_manager, with_tenant
)


def test_create_tenant():
    """测试创建租户"""
    manager = create_tenant_manager()
    tenant = manager.create_tenant("t1", "Tenant One", region="us")

    assert tenant.tenant_id == "t1"
    assert tenant.name == "Tenant One"
    assert tenant.config["region"] == "us"
    assert tenant.status == TenantStatus.ACTIVE
    print("  [test_create_tenant] 创建租户 ✓")


def test_duplicate_tenant():
    """测试重复租户"""
    manager = create_tenant_manager()
    manager.create_tenant("t1", "Tenant One")

    try:
        manager.create_tenant("t1", "Duplicate")
        assert False, "应抛出异常"
    except ValueError as e:
        assert "already exists" in str(e)
    print("  [test_duplicate_tenant] 重复租户 ✓")


def test_tenant_context():
    """测试租户上下文"""
    # 初始为空
    assert TenantContext.get_current_tenant_id() is None

    # 设置租户
    TenantContext.set_current_tenant("t1")
    assert TenantContext.get_current_tenant_id() == "t1"

    # 清除
    TenantContext.clear()
    assert TenantContext.get_current_tenant_id() is None
    print("  [test_tenant_context] 租户上下文 ✓")


def test_tenant_decorator():
    """测试租户装饰器"""
    results = []

    @with_tenant("t1")
    def do_something():
        results.append(TenantContext.get_current_tenant_id())

    do_something()
    assert results[0] == "t1"
    assert TenantContext.get_current_tenant_id() is None  # 已清除
    print("  [test_tenant_decorator] 租户装饰器 ✓")


def test_tenant_quota():
    """测试租户配额"""
    manager = create_tenant_manager()
    manager.create_tenant("t1", "Tenant One")

    manager.set_quota("t1", "cpu", 100.0)
    manager.set_quota("t1", "memory", 1024.0)

    assert manager.get_quota("t1", "cpu") == 100.0
    assert manager.get_quota("t1", "memory") == 1024.0
    assert manager.get_quota("t1", "disk") is None
    print("  [test_tenant_quota] 租户配额 ✓")


def test_check_access():
    """测试访问检查"""
    manager = create_tenant_manager()
    manager.create_tenant("active", "Active Tenant")
    manager.create_tenant("suspended", "Suspended Tenant")

    # 暂停租户
    manager.update_tenant("suspended", status=TenantStatus.SUSPENDED)

    assert manager.check_access("active") is True
    assert manager.check_access("suspended") is False
    assert manager.check_access("nonexistent") is False
    print("  [test_check_access] 访问检查 ✓")


def test_list_tenants():
    """测试列出租户"""
    manager = create_tenant_manager()
    manager.create_tenant("t1", "One")
    manager.create_tenant("t2", "Two")
    manager.create_tenant("t3", "Three")

    tenants = manager.list_tenants()
    assert len(tenants) == 3
    print("  [test_list_tenants] 列出租户 ✓")


def test_delete_tenant():
    """测试删除租户"""
    manager = create_tenant_manager()
    manager.create_tenant("t1", "To Delete")

    assert manager.delete_tenant("t1") is True
    assert manager.get_tenant("t1") is None
    assert manager.delete_tenant("t1") is False
    print("  [test_delete_tenant] 删除租户 ✓")


def test_update_tenant():
    """测试更新租户"""
    manager = create_tenant_manager()
    manager.create_tenant("t1", "Old Name", setting="old")

    manager.update_tenant("t1", name="New Name", setting="new")

    tenant = manager.get_tenant("t1")
    assert tenant.name == "New Name"
    assert tenant.config["setting"] == "new"
    print("  [test_update_tenant] 更新租户 ✓")


def test_tenant_stats():
    """测试租户统计"""
    manager = create_tenant_manager()
    manager.create_tenant("t1", "One")
    manager.create_tenant("t2", "Two")
    manager.create_tenant("t3", "Three")
    manager.update_tenant("t3", status=TenantStatus.SUSPENDED)

    stats = manager.get_stats()
    assert stats["total_tenants"] == 3
    assert stats["active"] == 2
    assert stats["suspended"] == 1
    print("  [test_tenant_stats] 租户统计 ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("阶段50测试: 多租户接口标准化")
    print("=" * 60)

    test_create_tenant()
    test_duplicate_tenant()
    test_tenant_context()
    test_tenant_decorator()
    test_tenant_quota()
    test_check_access()
    test_list_tenants()
    test_delete_tenant()
    test_update_tenant()
    test_tenant_stats()

    print("=" * 60)
    print("全部10项测试通过 ✓")
    print("=" * 60)
