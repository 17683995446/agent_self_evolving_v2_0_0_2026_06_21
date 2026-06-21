"""
阶段161测试：用户指南文档

验证 docs/user_guide.md 的完整性和内容覆盖
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestUserGuideExists:
    """验证用户指南存在"""

    def test_user_guide_exists(self):
        """docs/user_guide.md 应存在"""
        assert (PROJECT_ROOT / "docs" / "user_guide.md").is_file()

    def test_user_guide_has_content(self):
        """用户指南应有足够内容"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert len(content) > 5000  # 至少5000字符


class TestUserGuideStructure:
    """验证用户指南结构"""

    def test_has_table_of_contents(self):
        """应有目录"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "目录" in content

    def test_has_install_section(self):
        """应有安装章节"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "安装" in content

    def test_has_configuration_section(self):
        """应有配置章节"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "配置" in content

    def test_has_quickstart_section(self):
        """应有快速开始章节"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "快速开始" in content

    def test_has_cli_section(self):
        """应有 CLI 章节"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "CLI" in content or "命令行" in content

    def test_has_python_api_section(self):
        """应有 Python API 章节"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "Python API" in content

    def test_has_rest_api_section(self):
        """应有 REST API 章节"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "REST API" in content

    def test_has_llm_section(self):
        """应有 LLM 集成章节"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "LLM" in content

    def test_has_rag_section(self):
        """应有 RAG 章节"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "RAG" in content

    def test_has_troubleshooting(self):
        """应有故障排查章节"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "故障排查" in content


class TestUserGuideContent:
    """验证用户指南内容"""

    def test_has_code_examples(self):
        """应有代码示例"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "```python" in content
        assert "```bash" in content

    def test_mentions_init_command(self):
        """应提及 init 命令"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "cli.py init" in content

    def test_mentions_quickstart_example(self):
        """应提及 quickstart 示例"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "quickstart.py" in content

    def test_mentions_api_key(self):
        """应提及 API Key 配置"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "SILICONFLOW_API_KEY" in content

    def test_mentions_openapi_docs(self):
        """应提及 OpenAPI 文档端点"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "openapi" in content.lower()

    def test_has_curl_examples(self):
        """应有 curl 示例"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "curl" in content

    def test_mentions_advanced_features(self):
        """应提及高级功能"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "多租户" in content
        assert "安全" in content

    def test_links_other_docs(self):
        """应链接到其他文档"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "configuration.md" in content
        assert "README.md" in content
