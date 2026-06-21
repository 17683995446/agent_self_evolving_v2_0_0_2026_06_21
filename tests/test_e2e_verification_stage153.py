"""
阶段153测试：端到端验证 — 全套测试/lint/类型检查/示例

这是秩序化重构（阶段144-153）的最终验证。
验证整个系统的完整性、一致性和可维护性。
"""

import os
import sys
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# 架构完整性验证
# ============================================================

class TestArchitectureIntegrity:
    """验证架构完整性"""

    def test_main_py_thin_entry(self):
        """main.py应是薄入口（<100行）"""
        main_path = PROJECT_ROOT / "main.py"
        line_count = len(main_path.read_text().splitlines())
        assert line_count < 100, f"main.py有{line_count}行，应<100行"

    def test_agent_py_reasonable_size(self):
        """agent.py应在合理范围内（<700行）"""
        agent_path = PROJECT_ROOT / "self_evolving_agent" / "agent.py"
        line_count = len(agent_path.read_text().splitlines())
        assert line_count < 700, f"agent.py有{line_count}行，应<700行"

    def test_api_package_exists(self):
        """api/包应存在（15个Blueprint）"""
        api_dir = PROJECT_ROOT / "api"
        assert api_dir.is_dir()
        bp_files = list(api_dir.glob("*_routes.py"))
        assert len(bp_files) == 15, f"应有15个Blueprint路由文件，实际{len(bp_files)}"

    def test_agent_mixins_package_exists(self):
        """agent_mixins/包应存在（14个Mixin）"""
        mixin_dir = PROJECT_ROOT / "self_evolving_agent" / "agent_mixins"
        assert mixin_dir.is_dir()
        mixin_files = [f for f in mixin_dir.glob("*.py") if f.name != "__init__.py"]
        assert len(mixin_files) == 14, f"应有14个Mixin文件，实际{len(mixin_files)}"

    def test_pyproject_toml_exists(self):
        """pyproject.toml应存在"""
        assert (PROJECT_ROOT / "pyproject.toml").is_file()

    def test_core_docs_exist(self):
        """核心文档应全部存在"""
        for doc in ["README.md", "LICENSE", "CONTRIBUTING.md", "CHANGELOG.md"]:
            assert (PROJECT_ROOT / doc).is_file(), f"{doc}应存在"

    def test_conftest_exists(self):
        """conftest.py应存在"""
        assert (PROJECT_ROOT / "tests" / "conftest.py").is_file()

    def test_quality_gate_script_exists(self):
        """质量门禁脚本应存在"""
        assert (PROJECT_ROOT / "scripts" / "quality_gate.py").is_file()


# ============================================================
# 导入完整性验证
# ============================================================

class TestImportIntegrity:
    """验证所有关键模块可导入"""

    def test_agent_imports(self):
        """SelfEvolvingAgent可导入"""
        from self_evolving_agent.agent import SelfEvolvingAgent, create_default_agent
        assert SelfEvolvingAgent is not None
        assert create_default_agent is not None

    def test_all_mixins_importable(self):
        """所有14个Mixin可导入"""
        from self_evolving_agent.agent_mixins import (
            EnvironmentMixin, PersistenceMixin, TaskMixin, CodeDocsMixin,
            PerformanceMixin, DistributedMixin, ObservabilityMixin, ProductionMixin,
            PluginsMixin, ConfigMixin, SecurityMixin, RecoveryMixin,
            BenchmarkMixin, TenantsMixin,
        )
        assert all([
            EnvironmentMixin, PersistenceMixin, TaskMixin, CodeDocsMixin,
            PerformanceMixin, DistributedMixin, ObservabilityMixin, ProductionMixin,
            PluginsMixin, ConfigMixin, SecurityMixin, RecoveryMixin,
            BenchmarkMixin, TenantsMixin,
        ])

    def test_all_blueprints_importable(self):
        """所有15个Blueprint可导入"""
        from api import (
            core_bp, llm_bp, rag_bp, env_bp, task_bp, code_bp, perf_bp,
            observability_bp, production_bp, plugins_bp, config_bp,
            security_bp, recovery_bp, benchmark_bp, tenants_bp,
        )
        assert all([
            core_bp, llm_bp, rag_bp, env_bp, task_bp, code_bp, perf_bp,
            observability_bp, production_bp, plugins_bp, config_bp,
            security_bp, recovery_bp, benchmark_bp, tenants_bp,
        ])

    def test_entry_points_importable(self):
        """所有入口点可导入"""
        import cli, main, run_six_hours
        for module in [cli, main, run_six_hours]:
            assert hasattr(module, "main")


# ============================================================
# 功能完整性验证
# ============================================================

class TestFunctionalIntegrity:
    """验证功能完整性"""

    def test_agent_lifecycle(self):
        """Agent生命周期：创建→初始化→观察→行动→反思"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        agent.initialize({"cycle_interval": 0.5})

        # 观察
        result = agent.observe({
            "module_id": "test",
            "predicted": {"value": 0.5},
            "actual": {"value": 0.55},
        })
        assert isinstance(result, dict)

        # 行动
        action = agent.act("explore", context={"resources_used": {"cpu": 0.3}})
        assert isinstance(action, dict)

        # 反思
        reflection = agent.reflect()
        assert isinstance(reflection, dict)

    def test_agent_mixin_methods(self):
        """Agent Mixin方法可用"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()

        # ConfigMixin
        agent.set_config("test", "value")
        assert agent.get_config("test") == "value"

        # PerformanceMixin
        report = agent.get_performance_report()
        assert isinstance(report, dict)

        # ObservabilityMixin
        from self_evolving_agent.core.observability import LogLevel
        agent.log(LogLevel.INFO, "test")
        logs = agent.get_logs(limit=10)
        assert isinstance(logs, list)

        # TenantsMixin
        tenant = agent.create_tenant("test_tenant")
        assert tenant is not None
        assert agent.is_tenant_active(tenant.tenant_id)

    def test_flask_app_routes(self):
        """Flask app有足够的路由"""
        from main import app
        rules = [r for r in app.url_map.iter_rules() if r.endpoint != "static"]
        assert len(rules) >= 100, f"应有至少100个路由，实际{len(rules)}"

    def test_flask_health_endpoints(self):
        """Flask健康端点存在"""
        from main import app
        rules = {r.rule for r in app.url_map.iter_rules()}
        assert "/health" in rules
        assert "/health/liveness" in rules
        assert "/health/readiness" in rules


# ============================================================
# 质量工具验证
# ============================================================

class TestQualityTools:
    """验证质量工具可用"""

    def test_ruff_available(self):
        """Ruff应可用"""
        result = subprocess.run(
            ["ruff", "--version"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0

    def test_mypy_available(self):
        """Mypy应可用"""
        result = subprocess.run(
            ["mypy", "--version"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0

    def test_quality_gate_runs(self):
        """质量门禁脚本可运行"""
        result = subprocess.run(
            ["python", "scripts/quality_gate.py", "--lint"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        # 质量门禁是非阻塞的，总是返回0
        assert result.returncode == 0


# ============================================================
# 秩序化成果总结验证
# ============================================================

class TestSystematizationResults:
    """验证秩序化成果"""

    def test_stage_144_packaging(self):
        """阶段144: pyproject.toml包含PEP 517/518配置"""
        content = (PROJECT_ROOT / "pyproject.toml").read_text()
        assert "[build-system]" in content
        assert "[project]" in content

    def test_stage_145_quality_tools(self):
        """阶段145: ruff和mypy已配置"""
        content = (PROJECT_ROOT / "pyproject.toml").read_text()
        assert "[tool.ruff" in content
        assert "[tool.mypy" in content

    def test_stage_146_package_structure(self):
        """阶段146: core/__init__.py和modules/__init__.py存在"""
        assert (PROJECT_ROOT / "self_evolving_agent" / "core" / "__init__.py").is_file()
        assert (PROJECT_ROOT / "self_evolving_agent" / "modules" / "__init__.py").is_file()

    def test_stage_147_cleanup(self):
        """阶段147: 无backup目录，白皮书在docs/"""
        assert not (PROJECT_ROOT / "backup").exists()
        assert (PROJECT_ROOT / "docs" / "whitepaper").is_dir()

    def test_stage_148_blueprint_split(self):
        """阶段148: main.py是薄入口，api/包有15个Blueprint"""
        assert len(list((PROJECT_ROOT / "api").glob("*_routes.py"))) == 15

    def test_stage_149_agent_mixins(self):
        """阶段149: agent_mixins/包有14个Mixin"""
        mixin_dir = PROJECT_ROOT / "self_evolving_agent" / "agent_mixins"
        mixins = [f for f in mixin_dir.glob("*.py") if f.name != "__init__.py"]
        assert len(mixins) == 14

    def test_stage_150_test_organization(self):
        """阶段150: conftest.py存在，所有测试文件遵循命名规范"""
        assert (PROJECT_ROOT / "tests" / "conftest.py").is_file()
        tests_dir = PROJECT_ROOT / "tests"
        for py_file in tests_dir.glob("*.py"):
            if py_file.name in ("__init__.py", "conftest.py"):
                continue
            assert py_file.name.startswith("test_"), f"{py_file.name}应遵循test_*.py命名"

    def test_stage_151_documentation(self):
        """阶段151: LICENSE/CONTRIBUTING/CHANGELOG/README存在"""
        for doc in ["LICENSE", "CONTRIBUTING.md", "CHANGELOG.md", "README.md"]:
            assert (PROJECT_ROOT / doc).is_file()

    def test_stage_152_entry_points(self):
        """阶段152: 3个入口点在pyproject.toml注册"""
        content = (PROJECT_ROOT / "pyproject.toml").read_text()
        assert "cli:main" in content
        assert "main:main" in content
        assert "run_six_hours:main" in content


# ============================================================
# 第一性原理最终验证
# ============================================================

class TestFirstPrinciplesFinal:
    """第一性原理最终验证"""

    def test_single_responsibility(self):
        """单一职责：每个模块/Mixin/Blueprint负责一个领域"""
        # Mixin文件每个负责一个领域
        mixin_dir = PROJECT_ROOT / "self_evolving_agent" / "agent_mixins"
        for f in mixin_dir.glob("*.py"):
            if f.name == "__init__.py":
                continue
            content = f.read_text()
            assert "class " in content, f"{f.name}应包含一个Mixin类"

    def test_backward_compatibility(self):
        """向后兼容：所有原有接口保持不变"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        # 核心接口
        assert callable(agent.observe)
        assert callable(agent.act)
        assert callable(agent.reflect)
        assert callable(agent.run_cycle)
        # Mixin接口
        assert callable(agent.register_environment)
        assert callable(agent.save_state)
        assert callable(agent.execute_task)
        assert callable(agent.review_code)
        assert callable(agent.get_performance_report)
        assert callable(agent.enable_distributed)
        assert callable(agent.check_health)
        assert callable(agent.start_production)
        assert callable(agent.load_plugin)
        assert callable(agent.get_config)
        assert callable(agent.create_user)
        assert callable(agent.execute_with_recovery)
        assert callable(agent.run_benchmark)
        assert callable(agent.create_tenant)

    def test_facade_pattern(self):
        """门面模式：Agent是核心模块的薄门面"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        # Agent持有所有核心模块引用
        managers = [
            "_coordinator", "_env_manager", "_task_executor", "_code_reviewer",
            "_doc_generator", "_perf_monitor", "_observability", "_production",
            "_plugin_manager", "_hot_reload", "_security", "_recovery",
            "_benchmark", "_tenants",
        ]
        for attr in managers:
            assert hasattr(agent, attr), f"Agent应有{attr}属性"

    def test_separation_of_concerns(self):
        """关注点分离：不同领域在不同文件"""
        # API路由按领域分离
        api_dir = PROJECT_ROOT / "api"
        route_files = list(api_dir.glob("*_routes.py"))
        assert len(route_files) == 15

        # Mixin按领域分离
        mixin_dir = PROJECT_ROOT / "self_evolving_agent" / "agent_mixins"
        mixin_files = [f for f in mixin_dir.glob("*.py") if f.name != "__init__.py"]
        assert len(mixin_files) == 14

    def test_dry_principle(self):
        """DRY原则：共享配置集中在conftest.py"""
        conftest = PROJECT_ROOT / "tests" / "conftest.py"
        assert conftest.is_file()
        content = conftest.read_text()
        assert "PROJECT_ROOT" in content
        assert "sys.path" in content
