"""
阶段154测试：配置模板与环境变量治理

验证:
1. .env.example 存在且包含所有环境变量
2. docs/configuration.md 存在且文档完整
3. 环境变量清单与代码实际使用一致
"""

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestEnvTemplate:
    """验证 .env.example 配置模板"""

    def test_env_example_exists(self):
        """.env.example 应存在"""
        assert (PROJECT_ROOT / ".env.example").is_file()

    def test_env_example_has_service_config(self):
        """.env.example 应包含服务配置变量"""
        content = (PROJECT_ROOT / ".env.example").read_text()
        assert "PORT=" in content
        assert "HOST=" in content
        assert "DEBUG=" in content

    def test_env_example_has_llm_config(self):
        """.env.example 应包含 LLM 配置变量"""
        content = (PROJECT_ROOT / ".env.example").read_text()
        assert "SILICONFLOW_API_KEY=" in content
        assert "SILICONFLOW_MODEL=" in content
        assert "SILICONFLOW_BASE_URL=" in content

    def test_env_example_has_rag_config(self):
        """.env.example 应包含 RAG 配置变量"""
        content = (PROJECT_ROOT / ".env.example").read_text()
        assert "SILICONFLOW_EMBEDDING_MODEL=" in content

    def test_env_example_has_comments(self):
        """.env.example 应有使用说明注释"""
        content = (PROJECT_ROOT / ".env.example").read_text()
        assert "#" in content  # 有注释
        assert "用法" in content or "usage" in content.lower()

    def test_env_example_api_key_empty(self):
        """API_KEY 默认值应为空（需用户填写）"""
        content = (PROJECT_ROOT / ".env.example").read_text()
        # 找到 SILICONFLOW_API_KEY= 行，确认值为空
        for line in content.splitlines():
            if line.strip().startswith("SILICONFLOW_API_KEY="):
                assert line.strip() == "SILICONFLOW_API_KEY="
                return
        pytest.fail("未找到 SILICONFLOW_API_KEY 行")

    def test_env_example_has_defaults(self):
        """应有合理的默认值"""
        content = (PROJECT_ROOT / ".env.example").read_text()
        assert "PORT=8080" in content
        assert "HOST=0.0.0.0" in content
        assert "DEBUG=false" in content


class TestConfigurationDoc:
    """验证 docs/configuration.md 配置文档"""

    def test_config_doc_exists(self):
        """docs/configuration.md 应存在"""
        assert (PROJECT_ROOT / "docs" / "configuration.md").is_file()

    def test_config_doc_has_quick_start(self):
        """配置文档应有快速开始"""
        content = (PROJECT_ROOT / "docs" / "configuration.md").read_text()
        assert "快速开始" in content or "Quick" in content

    def test_config_doc_has_env_table(self):
        """配置文档应有环境变量清单表格"""
        content = (PROJECT_ROOT / "docs" / "configuration.md").read_text()
        assert "PORT" in content
        assert "SILICONFLOW_API_KEY" in content
        assert "|" in content  # 有表格

    def test_config_doc_has_run_modes(self):
        """配置文档应有运行模式说明"""
        content = (PROJECT_ROOT / "docs" / "configuration.md").read_text()
        assert "无 LLM" in content or "LLM 模式" in content

    def test_config_doc_has_faq(self):
        """配置文档应有常见问题"""
        content = (PROJECT_ROOT / "docs" / "configuration.md").read_text()
        assert "常见问题" in content or "FAQ" in content.upper()

    def test_config_doc_has_priority(self):
        """配置文档应有配置优先级说明"""
        content = (PROJECT_ROOT / "docs" / "configuration.md").read_text()
        assert "优先级" in content


class TestEnvConsistency:
    """验证环境变量清单与代码实际使用一致"""

    def test_all_env_vars_documented(self):
        """代码中使用的环境变量都应在文档中列出"""
        import subprocess
        # 搜索代码中的环境变量使用
        result = subprocess.run(
            ["grep", "-roh", r"os\.environ\.\(get\|setdefault\)(\"[A-Z_]*\"",
             str(PROJECT_ROOT / "main.py"),
             str(PROJECT_ROOT / "api"),
             str(PROJECT_ROOT / "self_evolving_agent")],
            capture_output=True, text=True
        )
        # 提取变量名
        import re
        vars_in_code = set(re.findall(r'"([A-Z_]+)"', result.stdout))
        # 排除非配置变量
        # SKIP_LLM_INIT: 测试用
        # TERM: 终端类型检测（output_enhanced.py），非配置变量
        # NO_COLOR: 颜色控制（output_enhanced.py），非配置变量
        vars_in_code.discard("SKIP_LLM_INIT")
        vars_in_code.discard("TERM")
        vars_in_code.discard("NO_COLOR")

        doc_content = (PROJECT_ROOT / "docs" / "configuration.md").read_text()
        for var in vars_in_code:
            assert var in doc_content, f"环境变量 {var} 未在 configuration.md 中文档化"

    def test_env_example_matches_doc(self):
        """.env.example 和 configuration.md 应一致"""
        env_content = (PROJECT_ROOT / ".env.example").read_text()
        doc_content = (PROJECT_ROOT / "docs" / "configuration.md").read_text()

        # 关键变量都应同时出现在两个文件中
        key_vars = ["PORT", "HOST", "DEBUG", "SILICONFLOW_API_KEY",
                    "SILICONFLOW_MODEL", "SILICONFLOW_BASE_URL",
                    "SILICONFLOW_EMBEDDING_MODEL"]
        for var in key_vars:
            assert var in env_content, f"{var} 不在 .env.example 中"
            assert var in doc_content, f"{var} 不在 configuration.md 中"
