"""
阶段143: 端到端完整工作流示例

本示例演示如何将阶段134-142的所有功能整合到一个完整的工作流中：
- Agent初始化与核心循环（observe/act/reflect）
- 多租户管理（阶段142）
- 安全认证与授权（阶段139）
- 配置热更新（阶段138）
- 错误恢复策略（阶段140）
- 性能基准测试（阶段141）
- 插件系统（阶段135）
- HTTP API（阶段134）

运行方式:
    python -m examples.full_workflow
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from self_evolving_agent.agent import SelfEvolvingAgent
from self_evolving_agent.core.multi_tenant import (
    ResourceQuota,
    TenantState,
    create_resource_quota,
    tenant_scope,
    get_current_tenant_id,
)
from self_evolving_agent.core.security import (
    Permission,
    SecurityManager,
    create_security_manager,
)
from self_evolving_agent.core.recovery import (
    RecoveryManager,
    create_recovery_manager,
    create_retry_policy,
)
from self_evolving_agent.core.benchmark import (
    FunctionBenchmark,
    create_benchmark_runner,
)
from self_evolving_agent.core.config_hot_reload import create_hot_reload_manager


# ============================================================
# 示例1: 基础Agent工作流
# ============================================================

def example_basic_agent_workflow() -> Dict[str, Any]:
    """
    基础Agent工作流示例

    演示:
    1. 创建Agent
    2. 初始化配置
    3. 执行observe/act/reflect循环
    4. 获取状态
    """
    print("\n[示例1] 基础Agent工作流")
    print("-" * 50)

    # 1. 创建Agent
    agent = SelfEvolvingAgent(agent_id="example_agent")

    # 2. 初始化配置
    agent.initialize({
        "cycle_interval": 0.1,
        "goals": {"safe": 0.9, "gain": 0.7, "eff": 0.8},
    })

    # 3. 执行循环
    results = []
    for i in range(3):
        state = {"iteration": i, "input": f"test_{i}"}
        obs = agent.observe(state)
        act_result = agent.act("process", {"data": state})
        reflection = agent.reflect()
        cycle = agent.run_cycle({"step": i})
        results.append({
            "iteration": i,
            "observed": bool(obs),
            "acted": bool(act_result),
            "reflected": bool(reflection),
            "cycle_completed": bool(cycle),
        })
        print(f"  循环 {i}: observe={bool(obs)}, act={bool(act_result)}, reflect={bool(reflection)}")

    # 4. 获取状态
    state = agent.get_state()

    print(f"  总循环数: {agent._cycle_count}")
    print(f"  状态键: {list(state.keys())[:5]}...")

    return {
        "cycles_executed": len(results),
        "results": results,
        "agent_id": agent.agent_id,
    }


# ============================================================
# 示例2: 多租户管理
# ============================================================

def example_multi_tenant_workflow() -> Dict[str, Any]:
    """
    多租户管理工作流示例

    演示:
    1. 创建不同配额的租户
    2. 租户数据隔离
    3. 配额检查与限流
    4. 租户生命周期管理
    5. 租户作用域执行
    """
    print("\n[示例2] 多租户管理")
    print("-" * 50)

    agent = SelfEvolvingAgent(agent_id="tenant_demo")

    # 1. 创建不同配额的租户
    free_quota = create_resource_quota(
        max_requests_per_minute=10,
        max_concurrent_tasks=2,
        max_storage_mb=100,
        max_users=5,
    )
    pro_quota = create_resource_quota(
        max_requests_per_minute=1000,
        max_concurrent_tasks=20,
        max_storage_mb=10240,
        max_users=100,
    )

    free_tenant = agent.create_tenant(
        "Free User",
        tenant_id="tenant_free",
        quota=free_quota,
        metadata={"plan": "free"},
    )
    pro_tenant = agent.create_tenant(
        "Pro User",
        tenant_id="tenant_pro",
        quota=pro_quota,
        metadata={"plan": "pro"},
    )
    print(f"  创建租户: {free_tenant.name} (plan={free_tenant.metadata['plan']})")
    print(f"  创建租户: {pro_tenant.name} (plan={pro_tenant.metadata['plan']})")

    # 2. 数据隔离
    agent.set_tenant_data("tenant_free", "api_key", "free_key_123")
    agent.set_tenant_data("tenant_pro", "api_key", "pro_key_456")
    agent.set_tenant_data("tenant_free", "settings", {"theme": "light"})
    agent.set_tenant_data("tenant_pro", "settings", {"theme": "dark"})

    free_key = agent.get_tenant_data("tenant_free", "api_key")
    pro_key = agent.get_tenant_data("tenant_pro", "api_key")
    print(f"  Free租户API Key: {free_key}")
    print(f"  Pro租户API Key: {pro_key}")
    assert free_key != pro_key, "租户数据应隔离"

    # 3. 配额检查
    for _ in range(10):
        agent.tenants.record_request("tenant_free")
    free_allowed, free_msg = agent.check_tenant_quota("tenant_free", "requests_per_minute")
    pro_allowed, pro_msg = agent.check_tenant_quota("tenant_pro", "requests_per_minute")
    print(f"  Free配额检查: allowed={free_allowed} ({free_msg or 'OK'})")
    print(f"  Pro配额检查: allowed={pro_allowed} ({pro_msg or 'OK'})")

    # 4. 租户作用域执行
    def tenant_operation():
        tid = get_current_tenant_id()
        return {"executed_in": tid, "success": True}

    free_result = agent.execute_in_tenant("tenant_free", tenant_operation)
    pro_result = agent.execute_in_tenant("tenant_pro", tenant_operation)
    print(f"  Free作用域执行: {free_result}")
    print(f"  Pro作用域执行: {pro_result}")

    # 5. 生命周期管理
    agent.suspend_tenant("tenant_free")
    print(f"  Free租户暂停后活跃: {agent.is_tenant_active('tenant_free')}")
    agent.resume_tenant("tenant_free")
    print(f"  Free租户恢复后活跃: {agent.is_tenant_active('tenant_free')}")

    # 6. 统计
    stats = agent.get_tenant_stats()
    print(f"  租户统计: total={stats['total_tenants']}, by_state={stats['by_state']}")

    # 清理
    agent.terminate_tenant("tenant_free")
    agent.delete_tenant("tenant_pro")

    return {
        "tenants_created": 2,
        "free_allowed": free_allowed,
        "pro_allowed": pro_allowed,
        "free_scope": free_result,
        "pro_scope": pro_result,
        "stats": stats,
    }


# ============================================================
# 示例3: 安全认证与授权
# ============================================================

def example_security_workflow() -> Dict[str, Any]:
    """
    安全认证与授权工作流示例

    演示:
    1. 创建用户与角色
    2. API Key认证
    3. 权限检查
    4. 审计日志
    """
    print("\n[示例3] 安全认证与授权")
    print("-" * 50)

    agent = SelfEvolvingAgent(agent_id="security_demo")

    # 1. 创建用户（roles为set类型）
    admin = agent.create_user("admin", roles={"admin"})
    operator = agent.create_user("operator", roles={"operator"})
    viewer = agent.create_user("viewer", roles={"viewer"})
    print(f"  创建用户: admin({admin.user_id}), operator({operator.user_id}), viewer({viewer.user_id})")

    # 2. API Key认证
    admin_key = agent.create_api_key(admin.user_id)
    print(f"  Admin API Key: {admin_key[:20]}...")

    authenticated = agent.authenticate("api_key", {"api_key": admin_key})
    print(f"  Admin认证: {authenticated.success}")
    if authenticated.success and authenticated.user:
        print(f"  认证用户: {authenticated.user.username}")

    # 3. 权限检查
    admin_can_delete = agent.check_permission(admin, Permission.PRODUCTION_MANAGE)
    viewer_can_delete = agent.check_permission(viewer, Permission.PRODUCTION_MANAGE)
    print(f"  Admin生产管理权限: {admin_can_delete}")
    print(f"  Viewer生产管理权限: {viewer_can_delete}")

    # 4. 审计日志
    audit_events = agent.get_audit_events(limit=5)
    print(f"  审计事件数: {len(audit_events)}")

    security_stats = agent.get_security_stats()
    print(f"  安全统计: {list(security_stats.keys())[:5]}")

    return {
        "users_created": 3,
        "admin_authenticated": authenticated.success,
        "admin_can_delete": admin_can_delete,
        "viewer_can_delete": viewer_can_delete,
        "audit_events": len(audit_events),
    }


# ============================================================
# 示例4: 配置热更新
# ============================================================

def example_config_hot_reload_workflow() -> Dict[str, Any]:
    """
    配置热更新工作流示例

    演示:
    1. 设置配置项
    2. 订阅配置变更
    3. 更新配置触发回调
    4. 配置历史与回滚
    """
    print("\n[示例4] 配置热更新")
    print("-" * 50)

    agent = SelfEvolvingAgent(agent_id="config_demo")

    # 1. 设置配置
    agent.set_config("app.name", "SelfEvolvingAgent")
    agent.set_config("app.version", "1.0.0")
    agent.set_config("app.feature_flags.new_ui", False)
    print(f"  app.name = {agent.get_config('app.name')}")
    print(f"  app.version = {agent.get_config('app.version')}")

    # 2. 订阅配置变更（回调签名: key, old_value, new_value）
    changes: List[Dict[str, Any]] = []

    def on_config_change(key, old_value, new_value):
        changes.append({"key": key, "old": old_value, "new": new_value})
        print(f"  [回调] 配置变更: {key} = {new_value}")

    agent.subscribe_config("app.feature_flags.new_ui", on_config_change)

    # 3. 更新配置（update_config接受字典）
    agent.update_config({"app.feature_flags.new_ui": True})
    print(f"  app.feature_flags.new_ui = {agent.get_config('app.feature_flags.new_ui')}")

    # 4. 配置历史
    history = agent.get_config_history("app.feature_flags.new_ui")
    print(f"  配置历史记录数: {len(history)}")

    # 5. 配置快照
    snapshot = agent.get_config_snapshot()
    print(f"  配置快照键数: {len(snapshot)}")

    config_stats = agent.get_config_stats()
    print(f"  配置统计: {list(config_stats.keys())[:5]}")

    return {
        "config_set": True,
        "changes_received": len(changes),
        "history_records": len(history),
        "snapshot_keys": len(snapshot),
    }


# ============================================================
# 示例5: 错误恢复策略
# ============================================================

def example_recovery_workflow() -> Dict[str, Any]:
    """
    错误恢复工作流示例

    演示:
    1. 注册恢复策略
    2. 执行带恢复的操作
    3. 错误历史记录
    4. 健康检查
    """
    print("\n[示例5] 错误恢复策略")
    print("-" * 50)

    from self_evolving_agent.core.recovery import HealthCheckResult

    agent = SelfEvolvingAgent(agent_id="recovery_demo")

    # 1. 模拟失败操作
    call_count = {"n": 0}

    def flaky_operation():
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise ConnectionError(f"连接失败 (尝试 {call_count['n']})")
        return {"success": True, "attempts": call_count["n"]}

    # 2. 执行带恢复的操作（签名: operation_name, func）
    try:
        result, error = agent.execute_with_recovery("flaky_op", flaky_operation)
        print(f"  操作结果: {result}")
    except Exception as e:
        result = {"error": str(e)}
        print(f"  操作失败: {e}")

    # 3. 错误历史
    error_count = agent.get_error_count()
    print(f"  错误计数: {error_count}")

    # 4. 注册健康检查（必须返回HealthCheckResult）
    def database_health_check():
        return HealthCheckResult(
            component="database",
            healthy=True,
            message="Database is responsive",
            timestamp=time.time(),
            details={"latency_ms": 5},
        )

    agent.register_health_check("database", database_health_check)
    health = agent.check_recovery_health("database")
    print(f"  数据库健康: {health.get('healthy') if health else 'N/A'}")

    # 5. 系统健康
    system_health = agent.get_system_health()
    print(f"  系统健康组件数: {len(system_health)}")

    recovery_stats = agent.get_recovery_stats()
    print(f"  恢复统计: {list(recovery_stats.keys())[:5]}")

    return {
        "operation_result": result,
        "error_count": error_count,
        "health_check_passed": bool(health) and health.get("healthy", False),
        "system_components": len(system_health),
    }


# ============================================================
# 示例6: 性能基准测试
# ============================================================

def example_benchmark_workflow() -> Dict[str, Any]:
    """
    性能基准测试工作流示例

    演示:
    1. 运行快速基准测试
    2. 设置性能基线
    3. 获取测试摘要
    """
    print("\n[示例6] 性能基准测试")
    print("-" * 50)

    from self_evolving_agent.core.benchmark import FunctionBenchmark

    agent = SelfEvolvingAgent(agent_id="benchmark_demo")

    # 1. 快速基准测试（签名: name, func）
    def sample_function(n=100):
        return sum(range(n))

    result = agent.run_quick_benchmark("sum_range_100", sample_function)
    print(f"  基准测试: {result.name}")
    print(f"  平均耗时: {result.avg_time:.6f}s")
    print(f"  每秒操作数: {result.ops_per_second:.2f}")
    print(f"  状态: {result.status.value}")

    # 2. 使用FunctionBenchmark + run_benchmark（结果会被存储）
    bench = FunctionBenchmark("stored_benchmark", sample_function, iterations=50)
    stored_result = agent.run_benchmark(bench)
    print(f"  存储的基准测试: {stored_result.name}")

    # 3. 获取结果
    all_results = agent.get_benchmark_results()
    print(f"  总结果数: {len(all_results)}")

    # 4. 摘要
    summary = agent.get_benchmark_summary()
    print(f"  摘要键: {list(summary.keys())[:5]}")

    # 5. 清理
    agent.clear_benchmark_results()
    print(f"  清理后结果数: {len(agent.get_benchmark_results())}")

    return {
        "benchmark_name": result.name,
        "benchmark_status": result.status.value,
        "ops_per_second": result.ops_per_second,
        "results_count": len(all_results),
    }


# ============================================================
# 示例7: 完整集成工作流
# ============================================================

def example_full_integration_workflow() -> Dict[str, Any]:
    """
    完整集成工作流示例

    演示所有功能的协同工作:
    1. 创建Agent并初始化
    2. 设置多租户环境
    3. 配置安全认证
    4. 在租户作用域内执行带恢复的操作
    5. 监控性能
    6. 审计与统计
    """
    print("\n[示例7] 完整集成工作流")
    print("-" * 50)

    # 1. 创建Agent
    agent = SelfEvolvingAgent(agent_id="full_integration")
    agent.initialize({
        "cycle_interval": 0.05,
        "goals": {"safe": 0.95, "gain": 0.8, "eff": 0.85},
    })
    print("  1. Agent初始化完成")

    # 2. 多租户设置
    quota = create_resource_quota(
        max_requests_per_minute=100,
        max_concurrent_tasks=5,
        max_users=20,
    )
    agent.create_tenant(
        "Enterprise Customer",
        tenant_id="ent_001",
        quota=quota,
        metadata={"industry": "tech", "tier": "enterprise"},
    )
    print("  2. 创建企业租户: ent_001")

    # 3. 安全设置
    admin_user = agent.create_user("admin_ent_001", roles={"admin"})
    admin_key = agent.create_api_key(admin_user.user_id)
    print(f"  3. 创建管理员用户与API Key")

    # 4. 配置
    agent.set_config("tenant.ent_001.feature_x", True)
    agent.set_config("tenant.ent_001.rate_limit", 100)
    print("  4. 配置租户特定参数")

    # 5. 在租户作用域内执行带恢复的操作
    operation_log = []

    def business_operation():
        tid = get_current_tenant_id()
        operation_log.append({"tenant": tid, "action": "process", "ts": time.time()})
        # 执行Agent循环
        agent.observe({"tenant": tid, "input": "business_data"})
        agent.act("process", {"tenant": tid})
        return {"processed": True, "tenant": tid}

    result = agent.execute_in_tenant("ent_001", business_operation)
    print(f"  5. 租户作用域执行: {result}")

    # 6. 性能监控
    bench_result = agent.run_quick_benchmark("tenant_operation", business_operation)
    print(f"  6. 性能基准: {bench_result.ops_per_second:.2f} ops/s")

    # 7. 审计与统计
    audit_events = agent.get_audit_events(limit=10)
    tenant_stats = agent.get_tenant_stats()
    config_stats = agent.get_config_stats()
    recovery_stats = agent.get_recovery_stats()
    print(f"  7. 审计事件: {len(audit_events)}")
    print(f"     租户统计: {tenant_stats['total_tenants']} 个租户")
    print(f"     配置项数: {config_stats.get('total_keys', 'N/A')}")

    # 8. 清理
    agent.terminate_tenant("ent_001")
    print("  8. 清理完成")

    return {
        "agent_id": agent.agent_id,
        "tenant_created": True,
        "user_created": admin_user is not None,
        "operation_result": result,
        "benchmark_ops": bench_result.ops_per_second,
        "audit_events": len(audit_events),
        "tenant_stats": tenant_stats,
    }


# ============================================================
# 主入口
# ============================================================

def run_all_examples() -> Dict[str, Any]:
    """运行所有示例"""
    print("=" * 60)
    print("阶段143: 端到端完整工作流示例")
    print("=" * 60)

    results = {}

    # 运行所有示例
    examples = [
        ("basic_agent", example_basic_agent_workflow),
        ("multi_tenant", example_multi_tenant_workflow),
        ("security", example_security_workflow),
        ("config_hot_reload", example_config_hot_reload_workflow),
        ("recovery", example_recovery_workflow),
        ("benchmark", example_benchmark_workflow),
        ("full_integration", example_full_integration_workflow),
    ]

    for name, func in examples:
        try:
            results[name] = func()
        except Exception as e:
            results[name] = {"error": str(e)}
            print(f"  [错误] {name}: {e}")

    print("\n" + "=" * 60)
    print("所有示例执行完成")
    print("=" * 60)

    # 汇总
    success_count = sum(1 for r in results.values() if "error" not in r)
    print(f"成功: {success_count}/{len(examples)}")

    return results


if __name__ == "__main__":
    run_all_examples()
