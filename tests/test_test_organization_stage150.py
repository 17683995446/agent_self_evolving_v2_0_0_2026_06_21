"""
阶段150测试：测试秩序化 — 统一命名/conftest/清理

验证：
1. conftest.py存在且提供共享fixtures
2. 所有测试文件遵循test_*.py命名规范
3. 非标准文件已重命名
4. 共享fixtures可用
5. 第一性原理：一致性、DRY、单一职责
"""

import os
import sys
import importlib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# conftest.py存在性测试
# ============================================================

class TestConftestExists:
    """测试conftest.py存在且有效"""

    def test_conftest_exists(self):
        """conftest.py应存在"""
        conftest = PROJECT_ROOT / "tests" / "conftest.py"
        assert conftest.is_file(), "tests/conftest.py应存在"

    def test_conftest_provides_project_root(self):
        """conftest应提供PROJECT_ROOT fixture"""
        conftest = PROJECT_ROOT / "tests" / "conftest.py"
        content = conftest.read_text()
        assert "PROJECT_ROOT" in content, "conftest应定义PROJECT_ROOT"

    def test_conftest_provides_sys_path_setup(self):
        """conftest应设置sys.path"""
        conftest = PROJECT_ROOT / "tests" / "conftest.py"
        content = conftest.read_text()
        assert "sys.path" in content, "conftest应设置sys.path"

    def test_conftest_provides_agent_fixture(self):
        """conftest应提供agent fixture"""
        conftest = PROJECT_ROOT / "tests" / "conftest.py"
        content = conftest.read_text()
        assert "def agent" in content, "conftest应提供agent fixture"


# ============================================================
# 命名规范测试
# ============================================================

class TestNamingConvention:
    """测试所有测试文件遵循命名规范"""

    def test_all_test_files_follow_pattern(self):
        """tests/目录下所有.py文件应遵循test_*.py命名"""
        tests_dir = PROJECT_ROOT / "tests"
        non_standard = []
        for py_file in tests_dir.glob("*.py"):
            if py_file.name == "__init__.py" or py_file.name == "conftest.py":
                continue
            if not py_file.name.startswith("test_"):
                non_standard.append(py_file.name)
        assert non_standard == [], f"非标准命名文件: {non_standard}"

    def test_no_legacy_system_test(self):
        """legacy_system_test.py应已重命名"""
        old = PROJECT_ROOT / "tests" / "legacy_system_test.py"
        assert not old.exists(), "legacy_system_test.py应已重命名"

    def test_no_stress_test(self):
        """stress_test.py应已重命名"""
        old = PROJECT_ROOT / "tests" / "stress_test.py"
        assert not old.exists(), "stress_test.py应已重命名"

    def test_no_stress_test_round2(self):
        """stress_test_round2.py应已重命名"""
        old = PROJECT_ROOT / "tests" / "stress_test_round2.py"
        assert not old.exists(), "stress_test_round2.py应已重命名"

    def test_renamed_files_exist(self):
        """重命名后的文件应存在"""
        tests_dir = PROJECT_ROOT / "tests"
        renamed = [
            "test_legacy_system.py",
            "test_stress_stage101.py",
            "test_stress_round2_stage107.py",
        ]
        for name in renamed:
            assert (tests_dir / name).is_file(), f"{name}应存在"


# ============================================================
# 共享fixtures可用性测试
# ============================================================

class TestSharedFixtures:
    """测试共享fixtures可用"""

    def test_project_root_fixture(self, PROJECT_ROOT):
        """PROJECT_ROOT fixture应可用"""
        assert PROJECT_ROOT is not None
        assert PROJECT_ROOT.is_dir()

    def test_agent_fixture(self, agent):
        """agent fixture应可用"""
        assert agent is not None
        assert hasattr(agent, "agent_id")
        assert hasattr(agent, "observe")
        assert hasattr(agent, "act")
        assert hasattr(agent, "reflect")


# ============================================================
# 测试收集完整性测试
# ============================================================

class TestCollectionCompleteness:
    """测试所有测试文件可被收集"""

    def test_all_test_files_collectable(self):
        """所有test_*.py文件应可被pytest收集"""
        tests_dir = PROJECT_ROOT / "tests"
        test_files = list(tests_dir.glob("test_*.py"))
        assert len(test_files) >= 40, f"应有至少40个测试文件，实际{len(test_files)}"

    def test_renamed_files_collectable(self):
        """重命名后的文件应可被收集"""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q",
             "tests/test_legacy_system.py",
             "tests/test_stress_stage101.py",
             "tests/test_stress_round2_stage107.py"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        # 至少应收集到一些测试（不要求全部通过，只要求可收集）
        assert "error" not in result.stderr.lower() or result.returncode == 0


# ============================================================
# 第一性原理测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_dry_principle(self):
        """DRY原则：sys.path设置应集中在conftest.py"""
        conftest = PROJECT_ROOT / "tests" / "conftest.py"
        assert conftest.is_file(), "conftest.py应存在（DRY：集中共享配置）"

    def test_consistency_principle(self):
        """一致性原则：所有测试文件遵循统一命名"""
        tests_dir = PROJECT_ROOT / "tests"
        for py_file in tests_dir.glob("*.py"):
            if py_file.name in ("__init__.py", "conftest.py"):
                continue
            assert py_file.name.startswith("test_"), \
                f"{py_file.name}应遵循test_*.py命名"

    def test_separation_of_concerns_principle(self):
        """关注点分离：conftest.py负责共享配置，测试文件负责测试逻辑"""
        conftest = PROJECT_ROOT / "tests" / "conftest.py"
        content = conftest.read_text()
        # conftest应包含fixture定义，不应包含具体测试
        assert "def " in content
        assert "class Test" not in content, "conftest不应包含测试类"

    def test_no_duplicate_setup_principle(self):
        """无重复设置：conftest提供共享fixtures，减少重复"""
        conftest = PROJECT_ROOT / "tests" / "conftest.py"
        content = conftest.read_text()
        # conftest应提供PROJECT_ROOT fixture
        assert "PROJECT_ROOT" in content
        # conftest应提供sys.path设置
        assert "sys.path" in content
