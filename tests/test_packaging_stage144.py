"""
阶段144: 项目打包配置测试

验证pyproject.toml配置正确性。
"""

import os
import pytest
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"


# ============================================================
# 配置文件存在性测试
# ============================================================

class TestPyprojectExists:
    """pyproject.toml存在性测试"""

    def test_pyproject_exists(self):
        assert PYPROJECT_PATH.exists(), "pyproject.toml应存在"

    def test_pyproject_is_file(self):
        assert PYPROJECT_PATH.is_file()

    def test_pyproject_readable(self):
        assert os.access(PYPROJECT_PATH, os.R_OK)


# ============================================================
# [project] 元数据测试
# ============================================================

class TestProjectMetadata:
    """项目元数据测试"""

    @pytest.fixture(scope="class")
    def config(self):
        with open(PYPROJECT_PATH, "rb") as f:
            return tomllib.load(f)

    def test_project_section_exists(self, config):
        assert "project" in config

    def test_project_name(self, config):
        assert config["project"]["name"] == "self-evolving-agent"

    def test_project_version(self, config):
        version = config["project"]["version"]
        assert isinstance(version, str)
        # 语义化版本格式
        parts = version.split(".")
        assert len(parts) >= 2, "版本应至少有major.minor"

    def test_project_description(self, config):
        desc = config["project"].get("description", "")
        assert len(desc) > 10, "描述应有意义"

    def test_project_readme(self, config):
        assert config["project"].get("readme") == "README.md"

    def test_project_license(self, config):
        license_info = config["project"].get("license")
        assert license_info is not None

    def test_project_python_requires(self, config):
        py_req = config["project"].get("requires-python", "")
        assert "3." in py_req

    def test_project_authors(self, config):
        authors = config["project"].get("authors", [])
        assert len(authors) >= 1

    def test_project_keywords(self, config):
        keywords = config["project"].get("keywords", [])
        assert len(keywords) >= 1

    def test_project_classifiers(self, config):
        classifiers = config["project"].get("classifiers", [])
        assert len(classifiers) >= 1


# ============================================================
# 依赖配置测试
# ============================================================

class TestDependencies:
    """依赖配置测试"""

    @pytest.fixture(scope="class")
    def config(self):
        with open(PYPROJECT_PATH, "rb") as f:
            return tomllib.load(f)

    def test_dependencies_exist(self, config):
        deps = config["project"].get("dependencies", [])
        assert len(deps) > 0

    def test_flask_dependency(self, config):
        deps = config["project"]["dependencies"]
        assert any("flask" in d.lower() for d in deps)

    def test_optional_dependencies_exist(self, config):
        optional = config["project"].get("optional-dependencies", {})
        assert "dev" in optional

    def test_dev_dependencies_include_test_tools(self, config):
        dev_deps = config["project"]["optional-dependencies"]["dev"]
        assert any("pytest" in d.lower() for d in dev_deps)


# ============================================================
# 构建系统测试
# ============================================================

class TestBuildSystem:
    """构建系统测试"""

    @pytest.fixture(scope="class")
    def config(self):
        with open(PYPROJECT_PATH, "rb") as f:
            return tomllib.load(f)

    def test_build_system_exists(self, config):
        assert "build-system" in config

    def test_build_backend(self, config):
        backend = config["build-system"]["build-backend"]
        assert "setuptools" in backend or "hatchling" in backend

    def test_build_requires(self, config):
        requires = config["build-system"]["requires"]
        assert len(requires) >= 1


# ============================================================
# 工具配置测试
# ============================================================

class TestToolConfig:
    """工具配置测试"""

    @pytest.fixture(scope="class")
    def config(self):
        with open(PYPROJECT_PATH, "rb") as f:
            return tomllib.load(f)

    def test_pytest_config_exists(self, config):
        assert "tool" in config
        assert "pytest" in config["tool"]

    def test_ruff_config_exists(self, config):
        assert "ruff" in config["tool"]

    def test_mypy_config_exists(self, config):
        assert "mypy" in config["tool"]


# ============================================================
# 项目结构测试
# ============================================================

class TestProjectStructure:
    """项目结构配置测试"""

    @pytest.fixture(scope="class")
    def config(self):
        with open(PYPROJECT_PATH, "rb") as f:
            return tomllib.load(f)

    def test_urls_section(self, config):
        urls = config["project"].get("urls", {})
        assert "Homepage" in urls or "Repository" in urls


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_standardization_principle(self):
        """第一性原理: 标准化 — 遵循PEP 517/518规范"""
        with open(PYPROJECT_PATH, "rb") as f:
            config = tomllib.load(f)
        assert "build-system" in config
        assert "project" in config

    def test_completeness_principle(self):
        """第一性原理: 完整性 — 配置应包含必要字段"""
        with open(PYPROJECT_PATH, "rb") as f:
            config = tomllib.load(f)
        project = config["project"]
        required_fields = ["name", "version", "description", "requires-python"]
        for field in required_fields:
            assert field in project, f"缺少必要字段: {field}"

    def test_reproducibility_principle(self):
        """第一性原理: 可复现性 — 依赖应明确"""
        with open(PYPROJECT_PATH, "rb") as f:
            config = tomllib.load(f)
        deps = config["project"]["dependencies"]
        # 每个依赖应有版本约束
        for dep in deps:
            assert any(c in dep for c in [">=", "<=", "==", "~=", ">"]), f"依赖缺少版本约束: {dep}"
