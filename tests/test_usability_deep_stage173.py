"""
阶段173测试：易用性深度验证

这是易用性深度提升（阶段164-173）的最终验证。
重点验证"接入性"——模块不仅存在，而且被入口层实际使用。

覆盖:
1. CLI 颜色输出接入验证
2. API 错误响应接入验证
3. CLI 新命令验证（doctor/config/logs/help/discover）
4. REPL 增强验证
5. table 格式增强验证
6. 第一性原理验证
"""

import inspect
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# CLI 颜色输出接入验证
# ============================================================

class TestColorIntegration:
    """验证 CLI 颜色输出实际接入"""

    def test_output_formatter_has_color(self):
        """OutputFormatter 应有 _color 属性"""
        from cli import OutputFormatter
        fmt = OutputFormatter("text")
        assert hasattr(fmt, "_color")

    def test_output_formatter_color_is_color_output(self):
        """_color 应是 ColorOutput 实例"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("text")
        assert isinstance(fmt._color, ColorOutput)

    def test_error_method_uses_color(self):
        """error 方法应使用颜色"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("text")
        fmt._color = ColorOutput(force_color=True)
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            fmt.error("test")
            output = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr
        assert "\033[31m" in output  # 红色

    def test_success_method_uses_color(self):
        """success 方法应使用颜色"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("text")
        fmt._color = ColorOutput(force_color=True)
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt.success("test")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        assert "\033[32m" in output  # 绿色


# ============================================================
# API 错误响应接入验证
# ============================================================

class TestAPIErrorIntegration:
    """验证 API 路由实际接入 api_error_response"""

    def test_tenants_route_uses_error_response(self):
        """tenants_routes 应使用 api_error_response"""
        import api.tenants_routes as mod
        source = inspect.getsource(mod)
        assert "api_error_response" in source

    def test_config_route_uses_error_response(self):
        """config_routes 应使用 api_error_response"""
        import api.config_routes as mod
        source = inspect.getsource(mod)
        assert "api_error_response" in source

    def test_plugins_route_uses_error_response(self):
        """plugins_routes 应使用 api_error_response"""
        import api.plugins_routes as mod
        source = inspect.getsource(mod)
        assert "api_error_response" in source

    def test_security_route_uses_error_response(self):
        """security_routes 应使用 api_error_response"""
        import api.security_routes as mod
        source = inspect.getsource(mod)
        assert "api_error_response" in source

    def test_api_error_returns_error_code(self, client):
        """API 错误响应应包含 error_code"""
        resp = client.post("/api/tenants", json={})
        data = resp.get_json()
        assert "error_code" in data

    @pytest.fixture
    def client(self):
        """Flask 测试客户端"""
        from main import app, init_agent
        init_agent()
        app.config["TESTING"] = True
        return app.test_client()


# ============================================================
# CLI 新命令验证
# ============================================================

class TestCLICommands:
    """验证 CLI 新命令存在且可运行"""

    def test_doctor_command_exists(self):
        """doctor 命令应存在"""
        from cli import build_parser
        import argparse
        parser = build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                assert "doctor" in action.choices
                return
        pytest.fail("未找到 subparsers")

    def test_config_command_exists(self):
        """config 命令应存在"""
        from cli import build_parser
        import argparse
        parser = build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                assert "config" in action.choices
                return

    def test_logs_command_exists(self):
        """logs 命令应存在"""
        from cli import build_parser
        import argparse
        parser = build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                assert "logs" in action.choices
                return

    def test_help_command_exists(self):
        """help 命令应存在"""
        from cli import build_parser
        import argparse
        parser = build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                assert "help" in action.choices
                return

    def test_plugin_discover_exists(self):
        """plugin discover 应存在"""
        from cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["plugin", "discover"])
        assert args.plugin_action == "discover"

    def test_doctor_runs(self):
        """doctor 命令应能运行"""
        result = subprocess.run(
            [sys.executable, "cli.py", "doctor"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode in (0, 1)
        assert "诊断" in result.stdout

    def test_config_list_runs(self):
        """config list 应能运行"""
        result = subprocess.run(
            [sys.executable, "cli.py", "config", "list"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0

    def test_help_runs(self):
        """help 命令应能运行"""
        result = subprocess.run(
            [sys.executable, "cli.py", "help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0
        assert "命令列表" in result.stdout


# ============================================================
# REPL 增强验证
# ============================================================

class TestREPLEnhancement:
    """验证 REPL 增强"""

    def test_repl_uses_readline(self):
        """REPL 应集成 readline"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_repl)
        assert "import readline" in source

    def test_repl_has_tab_completion(self):
        """REPL 应有 Tab 补全"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_repl)
        assert "set_completer" in source
        assert "tab: complete" in source

    def test_repl_has_history_persistence(self):
        """REPL 应有历史持久化"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_repl)
        assert "history_file" in source

    def test_repl_has_help_command(self):
        """REPL 应支持 help <command>"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_repl)
        assert "help " in source


# ============================================================
# table 格式增强验证
# ============================================================

class TestTableFormatEnhancement:
    """验证 table 格式接入 format_table"""

    def test_output_table_uses_format_table(self):
        """_output_table 应使用 format_table"""
        from cli import OutputFormatter
        source = inspect.getsource(OutputFormatter._output_table)
        assert "format_table" in source

    def test_table_has_headers(self):
        """table 输出应有表头"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        import io
        fmt = OutputFormatter("table")
        fmt._color = ColorOutput(force_color=False)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt._output_table({"a": "1"}, "Test")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        assert "Key" in output
        assert "Value" in output


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_discoverability(self):
        """可发现性 — 所有命令可通过 help 发现"""
        result = subprocess.run(
            [sys.executable, "cli.py", "help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        for cmd in ["start", "stop", "status", "cycle", "task", "review",
                    "docs", "perf", "plugin", "health", "chat", "repl",
                    "init", "errors", "doctor", "config", "logs", "help"]:
            assert cmd in result.stdout, f"命令 {cmd} 未在 help 中列出"

    def test_feedback(self):
        """反馈性 — 颜色输出提供视觉反馈"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        import io
        fmt = OutputFormatter("text")
        fmt._color = ColorOutput(force_color=True)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt.success("ok")
            fmt.info("info")
            fmt.warning("warn")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # 应有不同颜色的输出
        assert "\033[32m" in output  # 绿色 success
        assert "\033[36m" in output  # 青色 info
        assert "\033[33m" in output  # 黄色 warning

    def test_consistency(self):
        """一致性 — API 错误响应格式统一"""
        from main import app, init_agent
        init_agent()
        app.config["TESTING"] = True
        client = app.test_client()
        # 触发多个路由的错误
        responses = []
        resp = client.post("/api/tenants", json={})
        responses.append(("tenants", resp.get_json()))
        resp = client.post("/api/config/test_key", json={})
        responses.append(("config", resp.get_json()))
        resp = client.post("/api/security/users", json={})
        responses.append(("security", resp.get_json()))
        # 所有错误响应都应有 error_code
        for name, data in responses:
            assert "error_code" in data, f"{name} 错误响应缺少 error_code"

    def test_graceful_degradation(self):
        """优雅降级 — 非 TTY 环境无颜色码"""
        from cli import OutputFormatter
        import io
        fmt = OutputFormatter("text")  # 默认在测试环境（非 TTY）
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt.success("test")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        assert "\033[" not in output, "非 TTY 环境不应有颜色码"

    def test_self_diagnosis(self):
        """自诊断 — doctor 命令提供系统自检"""
        result = subprocess.run(
            [sys.executable, "cli.py", "doctor"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode in (0, 1)
        assert "[1/6]" in result.stdout
        assert "[6/6]" in result.stdout
        assert "诊断完成" in result.stdout


# ============================================================
# 易用性成果总结
# ============================================================

class TestUsabilityResults:
    """验证易用性深度提升成果"""

    def test_stage_164_color_integration(self):
        """阶段164: CLI颜色输出接入"""
        from cli import OutputFormatter
        fmt = OutputFormatter("text")
        assert hasattr(fmt, "_color")

    def test_stage_165_api_error_integration(self):
        """阶段165: API错误响应接入"""
        import api.tenants_routes as mod
        source = inspect.getsource(mod)
        assert "api_error_response" in source

    def test_stage_166_doctor_command(self):
        """阶段166: doctor诊断命令"""
        from cli import build_parser
        import argparse
        parser = build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                assert "doctor" in action.choices
                return

    def test_stage_167_config_command(self):
        """阶段167: config配置管理命令"""
        from cli import build_parser
        import argparse
        parser = build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                assert "config" in action.choices
                return

    def test_stage_168_logs_command(self):
        """阶段168: logs日志查看命令"""
        from cli import build_parser
        import argparse
        parser = build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                assert "logs" in action.choices
                return

    def test_stage_169_repl_enhancement(self):
        """阶段169: REPL增强"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_repl)
        assert "readline" in source

    def test_stage_170_plugin_discover(self):
        """阶段170: plugin discover命令"""
        from cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["plugin", "discover"])
        assert args.plugin_action == "discover"

    def test_stage_171_help_system(self):
        """阶段171: 交互式帮助系统"""
        from cli import build_parser
        import argparse
        parser = build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                assert "help" in action.choices
                return

    def test_stage_172_table_format(self):
        """阶段172: table格式增强"""
        from cli import OutputFormatter
        source = inspect.getsource(OutputFormatter._output_table)
        assert "format_table" in source
