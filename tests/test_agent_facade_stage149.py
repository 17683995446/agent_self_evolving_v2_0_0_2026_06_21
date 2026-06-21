"""
阶段149测试：agent.py门面重构 — Mixin模式按领域拆分

验证：
1. Mixin文件结构和导入正确
2. SelfEvolvingAgent继承所有Mixin
3. 所有方法仍然可用（向后兼容）
4. agent.py行数大幅缩减
5. 第一性原理：单一职责、关注点分离
"""

import os
import sys
import inspect
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# Mixin包结构测试
# ============================================================

class TestMixinPackageStructure:
    """测试Mixin包结构"""

    def test_mixin_package_exists(self):
        """agent_mixins包应存在"""
        pkg = PROJECT_ROOT / "self_evolving_agent" / "agent_mixins"
        assert pkg.is_dir(), "agent_mixins/ 目录应存在"
        assert (pkg / "__init__.py").is_file(), "__init__.py应存在"

    def test_mixin_files_exist(self):
        """14个领域mixin文件应存在"""
        mixin_dir = PROJECT_ROOT / "self_evolving_agent" / "agent_mixins"
        expected = [
            "environment.py", "persistence.py", "task.py", "code_docs.py",
            "performance.py", "distributed.py", "observability.py", "production.py",
            "plugins.py", "config.py", "security.py", "recovery.py",
            "benchmark.py", "tenants.py",
        ]
        for name in expected:
            assert (mixin_dir / name).is_file(), f"{name}应存在"

    def test_mixin_package_exports(self):
        """__init__.py应导出所有Mixin类"""
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

    def test_mixin_classes_are_classes(self):
        """所有Mixin应是class类型"""
        from self_evolving_agent.agent_mixins import (
            EnvironmentMixin, PersistenceMixin, TaskMixin, CodeDocsMixin,
            PerformanceMixin, DistributedMixin, ObservabilityMixin, ProductionMixin,
            PluginsMixin, ConfigMixin, SecurityMixin, RecoveryMixin,
            BenchmarkMixin, TenantsMixin,
        )
        for mixin in [EnvironmentMixin, PersistenceMixin, TaskMixin, CodeDocsMixin,
                      PerformanceMixin, DistributedMixin, ObservabilityMixin, ProductionMixin,
                      PluginsMixin, ConfigMixin, SecurityMixin, RecoveryMixin,
                      BenchmarkMixin, TenantsMixin]:
            assert inspect.isclass(mixin), f"{mixin}应是class"


# ============================================================
# 继承关系测试
# ============================================================

class TestInheritance:
    """测试SelfEvolvingAgent继承所有Mixin"""

    def test_agent_inherits_all_mixins(self):
        """SelfEvolvingAgent应继承所有14个Mixin"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        from self_evolving_agent.agent_mixins import (
            EnvironmentMixin, PersistenceMixin, TaskMixin, CodeDocsMixin,
            PerformanceMixin, DistributedMixin, ObservabilityMixin, ProductionMixin,
            PluginsMixin, ConfigMixin, SecurityMixin, RecoveryMixin,
            BenchmarkMixin, TenantsMixin,
        )
        mixins = [
            EnvironmentMixin, PersistenceMixin, TaskMixin, CodeDocsMixin,
            PerformanceMixin, DistributedMixin, ObservabilityMixin, ProductionMixin,
            PluginsMixin, ConfigMixin, SecurityMixin, RecoveryMixin,
            BenchmarkMixin, TenantsMixin,
        ]
        for mixin in mixins:
            assert issubclass(SelfEvolvingAgent, mixin), \
                f"SelfEvolvingAgent应是{mixin.__name__}的子类"

    def test_mixin_methods_on_agent(self):
        """Mixin方法应在SelfEvolvingAgent上可用"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        # 检查每个mixin的代表性方法
        representative_methods = {
            "register_environment": "EnvironmentMixin",
            "save_state": "PersistenceMixin",
            "execute_task": "TaskMixin",
            "review_code": "CodeDocsMixin",
            "get_performance_report": "PerformanceMixin",
            "enable_distributed": "DistributedMixin",
            "check_health": "ObservabilityMixin",
            "start_production": "ProductionMixin",
            "load_plugin": "PluginsMixin",
            "get_config": "ConfigMixin",
            "create_user": "SecurityMixin",
            "execute_with_recovery": "RecoveryMixin",
            "run_benchmark": "BenchmarkMixin",
            "create_tenant": "TenantsMixin",
        }
        for method_name, mixin_name in representative_methods.items():
            assert hasattr(SelfEvolvingAgent, method_name), \
                f"{mixin_name}: {method_name}应在SelfEvolvingAgent上"


# ============================================================
# 功能完整性测试
# ============================================================

class TestFunctionality:
    """测试重构后功能完整"""

    def test_agent_creation(self):
        """Agent应能正常创建"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        assert agent is not None
        assert agent.agent_id == "self_evolving_agent"

    def test_agent_initialize(self):
        """Agent应能初始化"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        agent.initialize({"cycle_interval": 0.5})
        assert agent._cycle_interval == 0.5

    def test_properties_accessible(self):
        """所有属性应可访问"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        assert agent.coordinator is not None
        assert agent.env_manager is not None
        assert agent.task_executor is not None
        assert agent.code_reviewer is not None
        assert agent.doc_generator is not None
        assert agent.performance_monitor is not None
        assert agent.observability is not None
        assert agent.production is not None
        assert agent.plugin_manager is not None
        assert agent.hot_reload is not None
        assert agent.security is not None
        assert agent.recovery is not None
        assert agent.benchmark is not None
        assert agent.tenants is not None

    def test_mixin_method_delegation(self):
        """Mixin方法应正确委托到核心模块"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        # 测试PerformanceMixin
        report = agent.get_performance_report()
        assert isinstance(report, dict)
        # 测试ConfigMixin
        agent.set_config("test_key", "test_value")
        assert agent.get_config("test_key") == "test_value"
        # 测试ObservabilityMixin
        from self_evolving_agent.core.observability import LogLevel
        agent.log(LogLevel.INFO, "test message")
        logs = agent.get_logs(limit=10)
        assert isinstance(logs, list)

    def test_create_default_agent(self):
        """create_default_agent应正常工作"""
        from self_evolving_agent.agent import create_default_agent
        agent = create_default_agent()
        assert agent is not None
        assert agent._cycle_interval == 1.0


# ============================================================
# 代码行数测试
# ============================================================

class TestLineCount:
    """测试代码行数缩减"""

    def test_agent_py_reduced(self):
        """agent.py应大幅缩减（从1478行到<700行）"""
        agent_path = PROJECT_ROOT / "self_evolving_agent" / "agent.py"
        line_count = len(agent_path.read_text().splitlines())
        assert line_count < 700, f"agent.py有{line_count}行，应<700行"

    def test_mixin_files_reasonable_size(self):
        """每个mixin文件应在合理范围内（<200行）"""
        mixin_dir = PROJECT_ROOT / "self_evolving_agent" / "agent_mixins"
        for py_file in mixin_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            line_count = len(py_file.read_text().splitlines())
            assert line_count < 200, f"{py_file.name}有{line_count}行，应<200行"

    def test_total_lines_not_increased(self):
        """总行数不应显著增加"""
        agent_path = PROJECT_ROOT / "self_evolving_agent" / "agent.py"
        mixin_dir = PROJECT_ROOT / "self_evolving_agent" / "agent_mixins"
        agent_lines = len(agent_path.read_text().splitlines())
        mixin_lines = sum(
            len(f.read_text().splitlines())
            for f in mixin_dir.glob("*.py")
        )
        total = agent_lines + mixin_lines
        # 原来是1478行，允许少量增加（文件头/导入重复）
        assert total < 1800, f"总行数{total}，应<1800行"


# ============================================================
# 第一性原理测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_single_responsibility_principle(self):
        """单一职责：每个Mixin只负责一个领域"""
        from self_evolving_agent.agent_mixins import (
            EnvironmentMixin, PersistenceMixin, TaskMixin, CodeDocsMixin,
            PerformanceMixin, DistributedMixin, ObservabilityMixin, ProductionMixin,
            PluginsMixin, ConfigMixin, SecurityMixin, RecoveryMixin,
            BenchmarkMixin, TenantsMixin,
        )
        # 每个mixin应至少有1个方法
        for mixin in [EnvironmentMixin, PersistenceMixin, TaskMixin, CodeDocsMixin,
                      PerformanceMixin, DistributedMixin, ObservabilityMixin, ProductionMixin,
                      PluginsMixin, ConfigMixin, SecurityMixin, RecoveryMixin,
                      BenchmarkMixin, TenantsMixin]:
            methods = [
                m for m in dir(mixin)
                if not m.startswith("_") and callable(getattr(mixin, m))
            ]
            assert len(methods) >= 1, f"{mixin.__name__}应至少有1个公开方法"

    def test_backward_compatibility_principle(self):
        """向后兼容：所有原有方法签名不变"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        # 验证关键方法存在且可调用
        key_methods = [
            "observe", "act", "reflect", "run_cycle",
            "register_environment", "save_state", "execute_task",
            "review_code", "generate_docs", "get_performance_report",
            "enable_distributed", "log", "check_health",
            "start_production", "load_plugin", "get_config",
            "create_user", "execute_with_recovery",
            "run_benchmark", "create_tenant", "get_state",
        ]
        for method_name in key_methods:
            assert callable(getattr(SelfEvolvingAgent, method_name, None)), \
                f"{method_name}应存在且可调用"

    def test_facade_pattern_principle(self):
        """门面模式：Agent是核心模块的薄门面"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        # Agent应持有所有核心模块的引用
        assert hasattr(agent, "_coordinator")
        assert hasattr(agent, "_env_manager")
        assert hasattr(agent, "_task_executor")
        assert hasattr(agent, "_code_reviewer")
        assert hasattr(agent, "_doc_generator")
        assert hasattr(agent, "_perf_monitor")
        assert hasattr(agent, "_observability")
        assert hasattr(agent, "_production")
        assert hasattr(agent, "_plugin_manager")
        assert hasattr(agent, "_hot_reload")
        assert hasattr(agent, "_security")
        assert hasattr(agent, "_recovery")
        assert hasattr(agent, "_benchmark")
        assert hasattr(agent, "_tenants")

    def test_separation_of_concerns_principle(self):
        """关注点分离：不同领域的方法在不同文件"""
        mixin_dir = PROJECT_ROOT / "self_evolving_agent" / "agent_mixins"
        # 每个mixin文件应包含对应的class定义
        file_class_map = {
            "environment.py": "EnvironmentMixin",
            "persistence.py": "PersistenceMixin",
            "task.py": "TaskMixin",
            "code_docs.py": "CodeDocsMixin",
            "performance.py": "PerformanceMixin",
            "distributed.py": "DistributedMixin",
            "observability.py": "ObservabilityMixin",
            "production.py": "ProductionMixin",
            "plugins.py": "PluginsMixin",
            "config.py": "ConfigMixin",
            "security.py": "SecurityMixin",
            "recovery.py": "RecoveryMixin",
            "benchmark.py": "BenchmarkMixin",
            "tenants.py": "TenantsMixin",
        }
        for filename, classname in file_class_map.items():
            content = (mixin_dir / filename).read_text()
            assert f"class {classname}" in content, \
                f"{filename}应包含class {classname}"
