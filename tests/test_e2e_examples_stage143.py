"""
阶段143: 端到端示例 测试

验证examples目录下的所有示例能正确运行。
"""

import pytest

from examples.full_workflow import (
    example_basic_agent_workflow,
    example_multi_tenant_workflow,
    example_security_workflow,
    example_config_hot_reload_workflow,
    example_recovery_workflow,
    example_benchmark_workflow,
    example_full_integration_workflow,
    run_all_examples,
)


# ============================================================
# 基础Agent工作流测试
# ============================================================

class TestBasicAgentWorkflow:
    """基础Agent工作流示例测试"""

    def test_basic_workflow_runs(self):
        result = example_basic_agent_workflow()
        assert "cycles_executed" in result
        assert result["cycles_executed"] == 3

    def test_basic_workflow_results_structure(self):
        result = example_basic_agent_workflow()
        assert "results" in result
        assert len(result["results"]) == 3
        for r in result["results"]:
            assert "iteration" in r
            assert "observed" in r
            assert "acted" in r
            assert "reflected" in r

    def test_basic_workflow_agent_id(self):
        result = example_basic_agent_workflow()
        assert result["agent_id"] == "example_agent"


# ============================================================
# 多租户工作流测试
# ============================================================

class TestMultiTenantWorkflow:
    """多租户工作流示例测试"""

    def test_multi_tenant_workflow_runs(self):
        result = example_multi_tenant_workflow()
        assert result["tenants_created"] == 2

    def test_multi_tenant_data_isolation(self):
        result = example_multi_tenant_workflow()
        assert result["free_scope"]["executed_in"] == "tenant_free"
        assert result["pro_scope"]["executed_in"] == "tenant_pro"

    def test_multi_tenant_quota_enforcement(self):
        result = example_multi_tenant_workflow()
        # Free租户应被限流
        assert result["free_allowed"] is False
        # Pro租户应被允许
        assert result["pro_allowed"] is True

    def test_multi_tenant_stats(self):
        result = example_multi_tenant_workflow()
        assert "stats" in result
        assert result["stats"]["total_tenants"] >= 2


# ============================================================
# 安全工作流测试
# ============================================================

class TestSecurityWorkflow:
    """安全工作流示例测试"""

    def test_security_workflow_runs(self):
        result = example_security_workflow()
        assert result["users_created"] == 3

    def test_security_authentication(self):
        result = example_security_workflow()
        assert result["admin_authenticated"] is True

    def test_security_permission_check(self):
        result = example_security_workflow()
        assert result["admin_can_delete"] is True
        assert result["viewer_can_delete"] is False

    def test_security_audit_events(self):
        result = example_security_workflow()
        assert result["audit_events"] >= 0


# ============================================================
# 配置热更新工作流测试
# ============================================================

class TestConfigHotReloadWorkflow:
    """配置热更新工作流示例测试"""

    def test_config_workflow_runs(self):
        result = example_config_hot_reload_workflow()
        assert result["config_set"] is True

    def test_config_change_callback(self):
        result = example_config_hot_reload_workflow()
        assert result["changes_received"] >= 1

    def test_config_history(self):
        result = example_config_hot_reload_workflow()
        assert result["history_records"] >= 1

    def test_config_snapshot(self):
        result = example_config_hot_reload_workflow()
        assert result["snapshot_keys"] > 0


# ============================================================
# 错误恢复工作流测试
# ============================================================

class TestRecoveryWorkflow:
    """错误恢复工作流示例测试"""

    def test_recovery_workflow_runs(self):
        result = example_recovery_workflow()
        assert "operation_result" in result

    def test_recovery_health_check(self):
        result = example_recovery_workflow()
        assert result["health_check_passed"] is True

    def test_recovery_system_health(self):
        result = example_recovery_workflow()
        assert result["system_components"] >= 0


# ============================================================
# 性能基准测试工作流测试
# ============================================================

class TestBenchmarkWorkflow:
    """性能基准测试工作流示例测试"""

    def test_benchmark_workflow_runs(self):
        result = example_benchmark_workflow()
        assert result["benchmark_name"] == "sum_range_100"

    def test_benchmark_status(self):
        result = example_benchmark_workflow()
        assert result["benchmark_status"] == "passed"

    def test_benchmark_ops_per_second(self):
        result = example_benchmark_workflow()
        assert result["ops_per_second"] > 0

    def test_benchmark_results_count(self):
        result = example_benchmark_workflow()
        assert result["results_count"] >= 1


# ============================================================
# 完整集成工作流测试
# ============================================================

class TestFullIntegrationWorkflow:
    """完整集成工作流示例测试"""

    def test_full_integration_runs(self):
        result = example_full_integration_workflow()
        assert result["agent_id"] == "full_integration"

    def test_full_integration_tenant(self):
        result = example_full_integration_workflow()
        assert result["tenant_created"] is True

    def test_full_integration_user(self):
        result = example_full_integration_workflow()
        assert result["user_created"] is True

    def test_full_integration_operation(self):
        result = example_full_integration_workflow()
        assert result["operation_result"]["processed"] is True
        assert result["operation_result"]["tenant"] == "ent_001"

    def test_full_integration_benchmark(self):
        result = example_full_integration_workflow()
        assert result["benchmark_ops"] > 0

    def test_full_integration_audit(self):
        result = example_full_integration_workflow()
        assert result["audit_events"] >= 0

    def test_full_integration_tenant_stats(self):
        result = example_full_integration_workflow()
        assert "total_tenants" in result["tenant_stats"]


# ============================================================
# 全部示例运行测试
# ============================================================

class TestRunAllExamples:
    """运行所有示例的测试"""

    def test_run_all_examples_returns_results(self):
        results = run_all_examples()
        assert isinstance(results, dict)
        assert len(results) == 7

    def test_run_all_examples_keys(self):
        results = run_all_examples()
        expected_keys = {
            "basic_agent",
            "multi_tenant",
            "security",
            "config_hot_reload",
            "recovery",
            "benchmark",
            "full_integration",
        }
        assert set(results.keys()) == expected_keys

    def test_run_all_examples_no_errors(self):
        results = run_all_examples()
        for name, result in results.items():
            if "error" in result:
                pytest.fail(f"示例 {name} 失败: {result['error']}")


# ============================================================
# API客户端测试（不依赖网络）
# ============================================================

class TestAPIClientStructure:
    """API客户端结构测试（不实际调用）"""

    def test_api_client_importable(self):
        try:
            from examples.api_workflow import AgentAPIClient
            client = AgentAPIClient("http://localhost:8080")
            assert client.base_url == "http://localhost:8080"
        except ImportError:
            pytest.skip("requests库未安装")

    def test_api_client_methods_exist(self):
        try:
            from examples.api_workflow import AgentAPIClient
            client = AgentAPIClient()
            # 验证所有方法存在
            assert hasattr(client, "health")
            assert hasattr(client, "list_tenants")
            assert hasattr(client, "create_tenant")
            assert hasattr(client, "get_tenant")
            assert hasattr(client, "delete_tenant")
            assert hasattr(client, "suspend_tenant")
            assert hasattr(client, "resume_tenant")
            assert hasattr(client, "terminate_tenant")
            assert hasattr(client, "check_tenant_quota")
            assert hasattr(client, "get_tenant_usage")
            assert hasattr(client, "get_tenant_data")
            assert hasattr(client, "set_tenant_data")
            assert hasattr(client, "delete_tenant_data")
            assert hasattr(client, "execute_in_tenant")
            assert hasattr(client, "get_tenant_stats")
            assert hasattr(client, "get_config")
            assert hasattr(client, "set_config")
            assert hasattr(client, "list_users")
            assert hasattr(client, "create_user")
            assert hasattr(client, "get_audit_events")
            assert hasattr(client, "get_recovery_stats")
            assert hasattr(client, "get_system_health")
            assert hasattr(client, "get_benchmark_results")
            assert hasattr(client, "get_benchmark_summary")
        except ImportError:
            pytest.skip("requests库未安装")

    def test_api_client_base_url_normalization(self):
        try:
            from examples.api_workflow import AgentAPIClient
            client = AgentAPIClient("http://localhost:8080/")
            assert client.base_url == "http://localhost:8080"
        except ImportError:
            pytest.skip("requests库未安装")


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_completeness_principle(self):
        """第一性原理: 完整性 — 示例覆盖所有阶段134-142的功能"""
        results = run_all_examples()
        # 每个示例都应成功执行
        for name, result in results.items():
            assert "error" not in result, f"示例 {name} 失败"

    def test_usability_principle(self):
        """第一性原理: 可用性 — 示例应易于理解和运行"""
        # 基础工作流应能简单运行
        result = example_basic_agent_workflow()
        assert result["cycles_executed"] == 3
        # 结果应包含足够的信息
        assert len(result["results"]) == 3

    def test_integration_principle(self):
        """第一性原理: 集成性 — 所有功能应能协同工作"""
        result = example_full_integration_workflow()
        # 集成工作流应成功
        assert result["tenant_created"] is True
        assert result["user_created"] is True
        assert result["operation_result"]["processed"] is True
        assert result["benchmark_ops"] > 0

    def test_isolation_principle(self):
        """第一性原理: 隔离性 — 多租户数据应隔离"""
        result = example_multi_tenant_workflow()
        assert result["free_scope"]["executed_in"] != result["pro_scope"]["executed_in"]

    def test_resilience_principle(self):
        """第一性原理: 韧性 — 系统应能从错误中恢复"""
        result = example_recovery_workflow()
        assert result["health_check_passed"] is True
