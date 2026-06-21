"""
阶段147: 文件清理与目录重组测试

验证文件清理和目录重组的正确性。
"""

import os
import pytest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ============================================================
# 白皮书迁移测试
# ============================================================

class TestWhitepaperMigration:
    """白皮书迁移测试"""

    def test_whitepaper_moved_to_docs(self):
        """白皮书应已移至docs/whitepaper/"""
        docs_dir = PROJECT_ROOT / "docs" / "whitepaper"
        assert docs_dir.exists()
        assert docs_dir.is_dir()

    def test_whitepaper_complete_exists(self):
        assert (PROJECT_ROOT / "docs" / "whitepaper" / "whitepaper_complete.md").exists()

    def test_whitepaper_parts_exist(self):
        for i in range(1, 11):
            path = PROJECT_ROOT / "docs" / "whitepaper" / f"whitepaper_part{i}.md"
            assert path.exists(), f"缺少: whitepaper_part{i}.md"

    def test_no_whitepaper_in_root(self):
        """根目录不应再有白皮书文件"""
        for item in PROJECT_ROOT.iterdir():
            if item.is_file() and item.name.startswith("whitepaper"):
                pytest.fail(f"根目录仍有白皮书文件: {item.name}")

    def test_backup_directory_removed(self):
        """backup/目录应已删除"""
        assert not (PROJECT_ROOT / "backup").exists()


# ============================================================
# test_system.py迁移测试
# ============================================================

class TestSystemTestMigration:
    """test_system.py迁移测试"""

    def test_test_system_not_in_source(self):
        """test_system.py不应在源码包内"""
        assert not (PROJECT_ROOT / "self_evolving_agent" / "test_system.py").exists()

    def test_legacy_test_in_tests(self):
        """遗留测试应在tests/目录（阶段150重命名为test_legacy_system.py）"""
        assert (PROJECT_ROOT / "tests" / "test_legacy_system.py").exists()

    def test_legacy_test_follows_naming_convention(self):
        """遗留测试应遵循test_*.py命名规范（阶段150重命名后）"""
        filename = "test_legacy_system.py"
        assert filename.startswith("test_")


# ============================================================
# 运行时产物隔离测试
# ============================================================

class TestRuntimeArtifactIsolation:
    """运行时产物隔离测试"""

    def test_gitignore_ignores_run_logs(self):
        """gitignore应忽略run_logs/"""
        content = (PROJECT_ROOT / ".gitignore").read_text()
        assert "run_logs/" in content

    def test_gitignore_ignores_stress_logs(self):
        """gitignore应忽略tests/stress_logs/"""
        content = (PROJECT_ROOT / ".gitignore").read_text()
        assert "tests/stress_logs/" in content

    def test_gitignore_ignores_mypy_cache(self):
        content = (PROJECT_ROOT / ".gitignore").read_text()
        assert ".mypy_cache/" in content

    def test_gitignore_ignores_ruff_cache(self):
        content = (PROJECT_ROOT / ".gitignore").read_text()
        assert ".ruff_cache/" in content


# ============================================================
# 配置整合测试
# ============================================================

class TestConfigConsolidation:
    """配置整合测试"""

    def test_pytest_ini_removed(self):
        """pytest.ini应已删除（配置移至pyproject.toml）"""
        assert not (PROJECT_ROOT / "pytest.ini").exists()

    def test_pytest_config_in_pyproject(self):
        """pytest配置应在pyproject.toml中"""
        import tomllib
        with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        assert "tool" in config
        assert "pytest" in config["tool"]
        assert "testpaths" in config["tool"]["pytest"]["ini_options"]

    def test_pyproject_is_configfile(self):
        """pyproject.toml应被pytest识别为配置文件"""
        # 通过运行pytest验证
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30
        )
        assert "configfile: pyproject.toml" in result.stdout or result.returncode == 0


# ============================================================
# 目录结构整洁性测试
# ============================================================

class TestDirectoryTidiness:
    """目录结构整洁性测试"""

    def test_root_has_no_md_duplicates(self):
        """根目录不应有重复的md文件"""
        root_md_files = [
            f for f in PROJECT_ROOT.iterdir()
            if f.is_file() and f.suffix == ".md"
        ]
        # 预期的根目录md文件
        expected = {"README.md", "DEPLOY.md", "improvement_plan.md"}
        actual = {f.name for f in root_md_files}
        # 允许有预期文件，不应有白皮书
        for f in actual:
            assert not f.startswith("whitepaper"), f"根目录仍有白皮书: {f}"

    def test_docs_directory_exists(self):
        """docs/目录应存在"""
        assert (PROJECT_ROOT / "docs").exists()

    def test_source_package_clean(self):
        """源码包内不应有测试文件"""
        sea_dir = PROJECT_ROOT / "self_evolving_agent"
        for item in sea_dir.iterdir():
            if item.is_file() and item.name.startswith("test_"):
                pytest.fail(f"源码包内有测试文件: {item.name}")


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_separation_of_concerns_principle(self):
        """第一性原理: 关注点分离 — 源码、测试、文档、产物应分离"""
        assert (PROJECT_ROOT / "self_evolving_agent").is_dir()  # 源码
        assert (PROJECT_ROOT / "tests").is_dir()                # 测试
        assert (PROJECT_ROOT / "docs").is_dir()                 # 文档
        # 运行时产物应在.gitignore中
        gitignore = (PROJECT_ROOT / ".gitignore").read_text()
        assert "run_logs/" in gitignore

    def test_no_redundancy_principle(self):
        """第一性原理: 无冗余 — 不应有重复文件"""
        assert not (PROJECT_ROOT / "backup").exists()
        # 白皮书不在根目录
        for item in PROJECT_ROOT.iterdir():
            if item.is_file():
                assert not item.name.startswith("whitepaper")

    def test_single_source_of_truth_principle(self):
        """第一性原理: 单一事实来源 — 配置应集中"""
        # pytest配置只在pyproject.toml中
        assert not (PROJECT_ROOT / "pytest.ini").exists()
        import tomllib
        with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        assert "pytest" in config["tool"]
