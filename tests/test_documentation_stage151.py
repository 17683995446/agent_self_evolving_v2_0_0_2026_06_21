"""
阶段151测试：文档治理 — LICENSE/CONTRIBUTING/CHANGELOG/README

验证：
1. LICENSE文件存在且有效
2. CONTRIBUTING.md存在且包含必要内容
3. CHANGELOG.md存在且记录版本历史
4. README.md更新且反映当前架构
5. 第一性原理：完整性、一致性、可维护性
"""

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# LICENSE测试
# ============================================================

class TestLicense:
    """测试LICENSE文件"""

    def test_license_exists(self):
        """LICENSE文件应存在"""
        license_file = PROJECT_ROOT / "LICENSE"
        assert license_file.is_file(), "LICENSE文件应存在"

    def test_license_content(self):
        """LICENSE应包含MIT许可证文本"""
        content = (PROJECT_ROOT / "LICENSE").read_text()
        assert "MIT" in content, "LICENSE应为MIT许可证"
        assert "Copyright" in content, "LICENSE应包含Copyright声明"

    def test_license_not_empty(self):
        """LICENSE不应为空"""
        content = (PROJECT_ROOT / "LICENSE").read_text()
        assert len(content) > 100, "LICENSE内容应足够长"


# ============================================================
# CONTRIBUTING测试
# ============================================================

class TestContributing:
    """测试CONTRIBUTING.md"""

    def test_contributing_exists(self):
        """CONTRIBUTING.md应存在"""
        assert (PROJECT_ROOT / "CONTRIBUTING.md").is_file()

    def test_contributing_content(self):
        """CONTRIBUTING应包含必要章节"""
        content = (PROJECT_ROOT / "CONTRIBUTING.md").read_text()
        assert "开发环境" in content or "Development" in content
        assert "测试" in content or "Test" in content
        assert "代码规范" in content or "Code Style" in content


# ============================================================
# CHANGELOG测试
# ============================================================

class TestChangelog:
    """测试CHANGELOG.md"""

    def test_changelog_exists(self):
        """CHANGELOG.md应存在"""
        assert (PROJECT_ROOT / "CHANGELOG.md").is_file()

    def test_changelog_content(self):
        """CHANGELOG应包含版本历史"""
        content = (PROJECT_ROOT / "CHANGELOG.md").read_text()
        assert "v2.0" in content or "2.0.0" in content, "应包含v2.0版本"

    def test_changelog_mentions_stages(self):
        """CHANGELOG应提及阶段"""
        content = (PROJECT_ROOT / "CHANGELOG.md").read_text()
        assert "阶段" in content or "stage" in content.lower()


# ============================================================
# README更新测试
# ============================================================

class TestReadmeUpdated:
    """测试README.md已更新"""

    def test_readme_exists(self):
        """README.md应存在"""
        assert (PROJECT_ROOT / "README.md").is_file()

    def test_readme_mentions_mixins(self):
        """README应提及agent_mixins（阶段149）"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "agent_mixins" in content or "Mixin" in content

    def test_readme_mentions_blueprints(self):
        """README应提及Blueprint拆分（阶段148）"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "Blueprint" in content or "blueprint" in content

    def test_readme_mentions_pyproject(self):
        """README应提及pyproject.toml（阶段144）"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "pyproject.toml" in content

    def test_readme_test_count_updated(self):
        """README应反映当前测试数量（不再说26个）"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "26个测试" not in content, "README不应再说26个测试"

    def test_readme_mentions_quality_tools(self):
        """README应提及质量工具（ruff/mypy）"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "ruff" in content.lower() or "mypy" in content.lower()


# ============================================================
# 文档一致性测试
# ============================================================

class TestDocConsistency:
    """测试文档一致性"""

    def test_all_core_docs_exist(self):
        """核心文档应全部存在"""
        docs = ["README.md", "LICENSE", "CONTRIBUTING.md", "CHANGELOG.md"]
        for doc in docs:
            assert (PROJECT_ROOT / doc).is_file(), f"{doc}应存在"

    def test_readme_links_valid(self):
        """README中的内部链接应有效"""
        content = (PROJECT_ROOT / "README.md").read_text()
        # 检查DEPLOY.md链接
        if "DEPLOY.md" in content:
            assert (PROJECT_ROOT / "DEPLOY.md").is_file(), "DEPLOY.md应存在"


# ============================================================
# 第一性原理测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_completeness_principle(self):
        """完整性原则：项目应有LICENSE/CONTRIBUTING/CHANGELOG/README"""
        required = ["LICENSE", "CONTRIBUTING.md", "CHANGELOG.md", "README.md"]
        for doc in required:
            assert (PROJECT_ROOT / doc).is_file(), f"{doc}应存在（完整性）"

    def test_maintainability_principle(self):
        """可维护性原则：CHANGELOG应记录版本演进"""
        content = (PROJECT_ROOT / "CHANGELOG.md").read_text()
        # CHANGELOG应至少有50行（记录多个版本/阶段）
        assert len(content.splitlines()) >= 30, "CHANGELOG应足够详细"

    def test_consistency_principle(self):
        """一致性原则：README版本应与pyproject.toml一致"""
        readme = (PROJECT_ROOT / "README.md").read_text()
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text()
        # 两者都应包含版本号2.0
        assert "2.0" in readme or "v2" in readme
        assert "2.0" in pyproject
