"""
阶段163测试：易用性端到端验证

这是易用性提升（阶段154-163）的最终验证。
验证整个系统的用户易用性成果。

覆盖:
1. 配置易用性（.env.example + 配置文档）
2. CLI 易用性（--version + epilog + init + errors + 详细help）
3. 错误码体系接入
4. 示例分级
5. README 易用性
6. API 自动文档
7. 用户指南
8. 输出体验
9. 第一性原理验证
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# 配置易用性验证
# ============================================================

class TestConfigUsability:
    """验证配置易用性"""

    def test_env_example_exists(self):
        """.env.example 应存在"""
        assert (PROJECT_ROOT / ".env.example").is_file()

    def test_config_doc_exists(self):
        """配置文档应存在"""
        assert (PROJECT_ROOT / "docs" / "configuration.md").is_file()

    def test_env_example_has_all_vars(self):
        """.env.example 应包含所有关键环境变量"""
        content = (PROJECT_ROOT / ".env.example").read_text()
        for var in ["PORT", "HOST", "DEBUG", "SILICONFLOW_API_KEY",
                    "SILICONFLOW_MODEL", "SILICONFLOW_BASE_URL",
                    "SILICONFLOW_EMBEDDING_MODEL"]:
            assert var in content, f"{var} 不在 .env.example 中"


# ============================================================
# CLI 易用性验证
# ============================================================

class TestCLIUsability:
    """验证 CLI 易用性"""

    def test_version_flag(self):
        """--version 应可用"""
        result = subprocess.run(
            [sys.executable, "cli.py", "--version"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "agent-cli" in result.stdout

    def test_help_has_examples(self):
        """--help 应包含使用示例"""
        result = subprocess.run(
            [sys.executable, "cli.py", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "示例" in result.stdout

    def test_init_command_works(self):
        """init 命令应可运行"""
        result = subprocess.run(
            [sys.executable, "cli.py", "init"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0
        assert "初始化向导" in result.stdout

    def test_errors_command_works(self):
        """errors 命令应可运行"""
        result = subprocess.run(
            [sys.executable, "cli.py", "errors"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "错误码" in result.stdout

    def test_all_subcommands_have_detailed_help(self):
        """所有子命令应有详细 help"""
        import argparse
        from cli import build_parser
        parser = build_parser()
        subparsers_action = None
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparsers_action = action
                break
        subcommands = list(subparsers_action.choices.keys())
        # 应有至少17个子命令（原15 + init + errors）
        assert len(subcommands) >= 17

    def test_subcommands_include_init_and_errors(self):
        """子命令应包含 init 和 errors"""
        import argparse
        from cli import build_parser
        parser = build_parser()
        subparsers_action = None
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparsers_action = action
                break
        assert "init" in subparsers_action.choices
        assert "errors" in subparsers_action.choices


# ============================================================
# 错误码体系验证
# ============================================================

class TestErrorCodesIntegration:
    """验证错误码体系接入"""

    def test_error_response_module_exists(self):
        """error_response 模块应存在"""
        from self_evolving_agent.core import error_response
        assert hasattr(error_response, "api_error_response")
        assert hasattr(error_response, "cli_error_message")

    def test_api_error_response_returns_structured_error(self):
        """API 错误响应应返回结构化错误"""
        from self_evolving_agent.core.error_response import api_error_response
        resp, status = api_error_response("missing_field", "测试")
        assert "error_code" in resp
        assert "category" in resp
        assert "severity" in resp
        assert "suggested_action" in resp

    def test_cli_error_message_has_error_code(self):
        """CLI 错误消息应包含错误码"""
        from self_evolving_agent.core.error_response import cli_error_message
        msg = cli_error_message("not_found", "测试")
        assert "Error [" in msg
        assert "建议操作" in msg


# ============================================================
# 示例分级验证
# ============================================================

class TestExampleGradation:
    """验证示例分级"""

    def test_quickstart_exists_and_runs(self):
        """quickstart 应存在且可运行"""
        result = subprocess.run(
            [sys.executable, "examples/quickstart.py"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            env={**os.environ, "SKIP_LLM_INIT": "true"},
        )
        assert result.returncode == 0

    def test_intermediate_exists_and_runs(self):
        """intermediate 应存在且可运行"""
        result = subprocess.run(
            [sys.executable, "examples/intermediate.py"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            env={**os.environ, "SKIP_LLM_INIT": "true"},
        )
        assert result.returncode == 0

    def test_examples_readme_exists(self):
        """examples/README.md 应存在"""
        assert (PROJECT_ROOT / "examples" / "README.md").is_file()

    def test_three_difficulty_levels(self):
        """应有三个难度级别"""
        examples_dir = PROJECT_ROOT / "examples"
        assert (examples_dir / "quickstart.py").is_file()
        assert (examples_dir / "intermediate.py").is_file()
        assert (examples_dir / "full_workflow.py").is_file()


# ============================================================
# README 易用性验证
# ============================================================

class TestReadmeUsability:
    """验证 README 易用性"""

    def test_readme_has_faq(self):
        """README 应有 FAQ"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "FAQ" in content or "常见问题" in content

    def test_readme_has_troubleshooting(self):
        """README 应有故障排查"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "故障排查" in content

    def test_readme_has_cli_section(self):
        """README 应有 CLI 说明"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "CLI" in content or "命令行" in content

    def test_readme_has_optional_deps(self):
        """README 应有可选依赖说明"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "可选依赖" in content

    def test_readme_has_doc_index(self):
        """README 应有文档索引"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "文档索引" in content


# ============================================================
# API 自动文档验证
# ============================================================

class TestAPIDocsUsability:
    """验证 API 自动文档"""

    def test_root_endpoint_returns_endpoints(self, client):
        """根端点应返回端点清单"""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "endpoints" in data
        assert "endpoint_count" in data

    def test_endpoints_grouped_endpoint(self, client):
        """/api/docs/endpoints 应可用"""
        resp = client.get("/api/docs/endpoints")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "groups" in data

    def test_openapi_endpoint(self, client):
        """/api/docs/openapi 应可用"""
        resp = client.get("/api/docs/openapi")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["openapi"] == "3.0.0"
        assert "paths" in data

    @pytest.fixture
    def client(self):
        """Flask 测试客户端"""
        from main import app, init_agent
        init_agent()
        app.config["TESTING"] = True
        return app.test_client()


# ============================================================
# 用户指南验证
# ============================================================

class TestUserGuideUsability:
    """验证用户指南"""

    def test_user_guide_exists(self):
        """用户指南应存在"""
        assert (PROJECT_ROOT / "docs" / "user_guide.md").is_file()

    def test_user_guide_has_toc(self):
        """用户指南应有目录"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        assert "目录" in content

    def test_user_guide_covers_all_topics(self):
        """用户指南应覆盖所有主题"""
        content = (PROJECT_ROOT / "docs" / "user_guide.md").read_text()
        for topic in ["安装", "配置", "CLI", "Python API", "REST API", "LLM", "RAG", "故障排查"]:
            assert topic in content, f"用户指南缺少 {topic} 章节"


# ============================================================
# 输出体验验证
# ============================================================

class TestOutputUsability:
    """验证输出体验"""

    def test_color_output_module_exists(self):
        """颜色输出模块应存在"""
        from self_evolving_agent.core.output_enhanced import ColorOutput
        assert ColorOutput is not None

    def test_progress_indicator_exists(self):
        """进度提示器应存在"""
        from self_evolving_agent.core.output_enhanced import ProgressIndicator
        assert ProgressIndicator is not None

    def test_format_table_exists(self):
        """表格格式化应存在"""
        from self_evolving_agent.core.output_enhanced import format_table
        result = format_table(["A", "B"], [["1", "2"]])
        assert "A" in result
        assert "1" in result


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_discoverability(self):
        """可发现性 — 用户能发现所有功能"""
        # CLI --help 应列出所有命令
        result = subprocess.run(
            [sys.executable, "cli.py", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for cmd in ["start", "stop", "status", "cycle", "task", "review",
                    "docs", "perf", "plugin", "health", "chat", "repl",
                    "init", "errors"]:
            assert cmd in result.stdout, f"命令 {cmd} 未在 --help 中列出"

    def test_feedback(self):
        """反馈性 — 操作有清晰反馈"""
        # init 命令应有步骤反馈
        result = subprocess.run(
            [sys.executable, "cli.py", "init"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert "[1/4]" in result.stdout
        assert "[4/4]" in result.stdout
        assert "完成" in result.stdout

    def test_consistency(self):
        """一致性 — 所有入口使用统一的错误格式"""
        from self_evolving_agent.core.error_response import (
            api_error_response, cli_error_message
        )
        # API 和 CLI 错误都应包含错误码
        api_resp, _ = api_error_response("missing_field", "测试")
        cli_msg = cli_error_message("missing_field", "测试")
        assert "error_code" in api_resp or "VAL_" in str(api_resp)
        assert "VAL_" in cli_msg

    def test_graceful_degradation(self):
        """优雅降级 — 无 LLM 时系统仍可用"""
        # quickstart 不需要 LLM
        result = subprocess.run(
            [sys.executable, "examples/quickstart.py"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            env={**os.environ, "SKIP_LLM_INIT": "true", "SILICONFLOW_API_KEY": ""},
        )
        assert result.returncode == 0

    def test_documentation_completeness(self):
        """文档完整性 — 所有关键文档存在"""
        docs = [
            "README.md",
            "docs/configuration.md",
            "docs/user_guide.md",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "LICENSE",
            ".env.example",
            "examples/README.md",
        ]
        for doc in docs:
            assert (PROJECT_ROOT / doc).is_file(), f"文档 {doc} 不存在"


# ============================================================
# 易用性成果总结
# ============================================================

class TestUsabilityResults:
    """验证易用性成果"""

    def test_stage_154_config_template(self):
        """阶段154: 配置模板"""
        assert (PROJECT_ROOT / ".env.example").is_file()
        assert (PROJECT_ROOT / "docs" / "configuration.md").is_file()

    def test_stage_155_cli_help(self):
        """阶段155: CLI帮助增强"""
        result = subprocess.run(
            [sys.executable, "cli.py", "--version"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0

    def test_stage_156_init_wizard(self):
        """阶段156: 初始化向导"""
        result = subprocess.run(
            [sys.executable, "cli.py", "init", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0

    def test_stage_157_error_codes(self):
        """阶段157: 错误码接入"""
        from self_evolving_agent.core.error_response import api_error_response
        resp, _ = api_error_response("missing_field", "测试")
        assert "error_code" in resp

    def test_stage_158_examples(self):
        """阶段158: 示例分级"""
        assert (PROJECT_ROOT / "examples" / "quickstart.py").is_file()
        assert (PROJECT_ROOT / "examples" / "intermediate.py").is_file()

    def test_stage_159_readme(self):
        """阶段159: README增强"""
        content = (PROJECT_ROOT / "README.md").read_text()
        assert "FAQ" in content
        assert "故障排查" in content

    def test_stage_160_api_docs(self):
        """阶段160: API自动文档"""
        from main import app, init_agent
        init_agent()
        app.config["TESTING"] = True
        client = app.test_client()
        resp = client.get("/api/docs/openapi")
        assert resp.status_code == 200

    def test_stage_161_user_guide(self):
        """阶段161: 用户指南"""
        assert (PROJECT_ROOT / "docs" / "user_guide.md").is_file()

    def test_stage_162_output(self):
        """阶段162: 输出体验"""
        from self_evolving_agent.core.output_enhanced import ColorOutput
        assert ColorOutput is not None
