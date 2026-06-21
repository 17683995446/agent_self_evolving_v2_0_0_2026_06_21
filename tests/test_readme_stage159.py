"""
阶段159测试：README易用性增强

验证:
1. README 有可选依赖说明
2. README 有 CLI 命令说明
3. README 有示例说明
4. README 有 FAQ 章节
5. README 有故障排查章节
6. README 有环境配置说明
7. README 有文档索引
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestReadmeOptionalDeps:
    """验证可选依赖说明"""

    def test_readme_has_optional_deps(self):
        """README 应有可选依赖说明"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "可选依赖" in content

    def test_readme_has_llm_dep(self):
        """README 应说明 LLM 可选依赖"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "[llm]" in content

    def test_readme_has_dev_dep(self):
        """README 应说明开发依赖"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "[dev]" in content

    def test_readme_has_install_command(self):
        """README 应有可选依赖安装命令"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert 'pip install -e ".[llm]"' in content


class TestReadmeCLI:
    """验证 CLI 说明"""

    def test_readme_has_cli_section(self):
        """README 应有 CLI 章节"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "CLI" in content or "命令行" in content

    def test_readme_has_cli_examples(self):
        """README 应有 CLI 使用示例"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "cli.py" in content
        assert "cli.py init" in content
        assert "cli.py status" in content

    def test_readme_mentions_help(self):
        """README 应提及 --help"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "--help" in content

    def test_readme_mentions_version(self):
        """README 应提及 --version"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "--version" in content


class TestReadmeExamples:
    """验证示例说明"""

    def test_readme_has_examples_section(self):
        """README 应有示例章节"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "示例" in content

    def test_readme_mentions_quickstart(self):
        """README 应提及 quickstart 示例"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "quickstart.py" in content

    def test_readme_mentions_intermediate(self):
        """README 应提及中级示例"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "intermediate.py" in content

    def test_readme_links_examples_readme(self):
        """README 应链接到 examples/README.md"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "examples/README.md" in content


class TestReadmeFAQ:
    """验证 FAQ 章节"""

    def test_readme_has_faq(self):
        """README 应有 FAQ 章节"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "FAQ" in content or "常见问题" in content

    def test_faq_has_llm_question(self):
        """FAQ 应有 LLM 配置问题"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "SILICONFLOW_API_KEY" in content

    def test_faq_has_python_version(self):
        """FAQ 应有 Python 版本问题"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "Python 3.10" in content or "3.10+" in content


class TestReadmeTroubleshooting:
    """验证故障排查章节"""

    def test_readme_has_troubleshooting(self):
        """README 应有故障排查章节"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "故障排查" in content

    def test_troubleshooting_has_module_error(self):
        """故障排查应有模块导入错误"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "ModuleNotFoundError" in content

    def test_troubleshooting_has_port_issue(self):
        """故障排查应有端口问题"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "端口" in content or "PORT" in content


class TestReadmeEnvConfig:
    """验证环境配置说明"""

    def test_readme_has_env_config(self):
        """README 应有环境配置说明"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert ".env.example" in content

    def test_readme_links_config_doc(self):
        """README 应链接到配置文档"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "docs/configuration.md" in content


class TestReadmeDocIndex:
    """验证文档索引"""

    def test_readme_has_doc_index(self):
        """README 应有文档索引"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "文档索引" in content

    def test_doc_index_lists_config(self):
        """文档索引应列出配置指南"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "配置指南" in content

    def test_doc_index_lists_examples(self):
        """文档索引应列出示例索引"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "示例索引" in content
