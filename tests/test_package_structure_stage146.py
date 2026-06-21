"""
阶段146: 包结构完善测试

验证core/和modules/的__init__.py正确创建并规范导出。
"""

import importlib
import pytest


# ============================================================
# core/__init__.py 测试
# ============================================================

class TestCoreInit:
    """core包__init__.py测试"""

    def test_core_package_importable(self):
        import self_evolving_agent.core as core_pkg
        assert core_pkg is not None

    def test_core_exports_system_coordinator(self):
        from self_evolving_agent.core import SystemCoordinator
        assert SystemCoordinator is not None

    def test_core_exports_create_coordinator(self):
        from self_evolving_agent.core import create_coordinator
        assert callable(create_coordinator)

    def test_core_exports_unified_engine(self):
        from self_evolving_agent.core import UnifiedFirstPrinciplesEngine
        assert UnifiedFirstPrinciplesEngine is not None

    def test_core_exports_create_unified_engine(self):
        from self_evolving_agent.core import create_unified_engine
        assert callable(create_unified_engine)

    def test_core_has_all(self):
        import self_evolving_agent.core as core_pkg
        assert hasattr(core_pkg, "__all__")
        assert len(core_pkg.__all__) >= 4

    def test_core_all_contains_key_names(self):
        import self_evolving_agent.core as core_pkg
        assert "SystemCoordinator" in core_pkg.__all__
        assert "UnifiedFirstPrinciplesEngine" in core_pkg.__all__

    def test_core_init_file_exists(self):
        import self_evolving_agent.core
        assert hasattr(self_evolving_agent.core, "__file__")
        assert self_evolving_agent.core.__file__.endswith("__init__.py")


# ============================================================
# modules/__init__.py 测试
# ============================================================

class TestModulesInit:
    """modules包__init__.py测试"""

    def test_modules_package_importable(self):
        import self_evolving_agent.modules as modules_pkg
        assert modules_pkg is not None

    def test_modules_exports_memory(self):
        """memory模块不依赖numpy，应始终可导入"""
        from self_evolving_agent.modules import ShortTermMemory, LongTermMemory, MemoryCoordinator
        assert ShortTermMemory is not None
        assert LongTermMemory is not None
        assert MemoryCoordinator is not None

    def test_modules_exports_memory_entry(self):
        from self_evolving_agent.modules import MemoryEntry
        assert MemoryEntry is not None

    def test_modules_has_all(self):
        import self_evolving_agent.modules as modules_pkg
        assert hasattr(modules_pkg, "__all__")
        assert len(modules_pkg.__all__) >= 4

    def test_modules_all_contains_memory(self):
        import self_evolving_agent.modules as modules_pkg
        assert "ShortTermMemory" in modules_pkg.__all__
        assert "MemoryCoordinator" in modules_pkg.__all__

    def test_modules_init_file_exists(self):
        import self_evolving_agent.modules
        assert hasattr(self_evolving_agent.modules, "__file__")
        assert self_evolving_agent.modules.__file__.endswith("__init__.py")

    def test_modules_graceful_numpy_degradation(self):
        """numpy依赖模块应优雅降级（不崩溃）"""
        # 即使numpy不存在，modules包本身应可导入
        import self_evolving_agent.modules as modules_pkg
        assert modules_pkg is not None


# ============================================================
# 子包__init__.py完整性测试
# ============================================================

class TestSubpackageInit:
    """子包__init__.py完整性测试"""

    def test_engines_init_exists(self):
        from self_evolving_agent.core import engines
        assert hasattr(engines, "__all__")

    def test_data_init_exists(self):
        """data子包依赖numpy，可能不可用，但__init__.py应存在"""
        import os
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        init_path = os.path.join(base, "self_evolving_agent", "core", "data", "__init__.py")
        assert os.path.exists(init_path)

    def test_devops_init_exists(self):
        from self_evolving_agent.core import devops
        assert devops is not None

    def test_infra_init_exists(self):
        from self_evolving_agent.core import infra
        assert infra is not None

    def test_mlops_init_exists(self):
        from self_evolving_agent.core import mlops
        assert mlops is not None


# ============================================================
# 包结构一致性测试
# ============================================================

class TestPackageConsistency:
    """包结构一致性测试"""

    def test_all_packages_have_init(self):
        """所有Python包目录都应有__init__.py"""
        import os
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pkg_dirs = [
            "self_evolving_agent",
            "self_evolving_agent/core",
            "self_evolving_agent/core/engines",
            "self_evolving_agent/core/data",
            "self_evolving_agent/core/devops",
            "self_evolving_agent/core/infra",
            "self_evolving_agent/core/mlops",
            "self_evolving_agent/modules",
            "tests",
            "examples",
        ]
        for d in pkg_dirs:
            init_path = os.path.join(base, d, "__init__.py")
            assert os.path.exists(init_path), f"缺少__init__.py: {d}"

    def test_top_level_package_exports(self):
        """顶层包应导出核心类"""
        import self_evolving_agent as sea
        assert hasattr(sea, "SelfEvolvingAgent")
        assert hasattr(sea, "__version__")

    def test_no_circular_import_core(self):
        """core包导入不应产生循环依赖"""
        # 如果有循环依赖，import会失败
        importlib.reload(importlib.import_module("self_evolving_agent.core"))

    def test_no_circular_import_modules(self):
        """modules包导入不应产生循环依赖"""
        importlib.reload(importlib.import_module("self_evolving_agent.modules"))


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_completeness_principle(self):
        """第一性原理: 完整性 — 所有包应有__init__.py"""
        import self_evolving_agent.core
        import self_evolving_agent.modules
        assert self_evolving_agent.core.__file__
        assert self_evolving_agent.modules.__file__

    def test_explicitness_principle(self):
        """第一性原理: 显式性 — 包应通过__all__声明公开API"""
        import self_evolving_agent.core as core_pkg
        import self_evolving_agent.modules as modules_pkg
        assert hasattr(core_pkg, "__all__")
        assert hasattr(modules_pkg, "__all__")

    def test_resilience_principle(self):
        """第一性原理: 韧性 — numpy缺失不应导致包导入崩溃"""
        import self_evolving_agent.modules as modules_pkg
        # memory类应始终可用
        assert hasattr(modules_pkg, "ShortTermMemory")

    def test_minimal_namespace_principle(self):
        """第一性原理: 最小命名空间 — core/__init__.py不应导出过多符号"""
        import self_evolving_agent.core as core_pkg
        # core/__init__.py应保持轻量，只导出最核心的组件
        assert len(core_pkg.__all__) <= 10
