"""
阶段171测试：交互式帮助系统

验证 help 命令存在并支持 help <command>
"""

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestHelpCommand:
    """验证 help 命令存在"""

    def test_help_in_subcommands(self):
        """help 应是 CLI 子命令"""
        from cli import build_parser
        import argparse
        parser = build_parser()
        subparsers_action = None
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparsers_action = action
                break
        assert "help" in subparsers_action.choices

    def test_help_has_handler(self):
        """help 命令应有处理器"""
        from cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["help"])
        assert args.handler == "cmd_help"

    def test_help_accepts_command_name(self):
        """help 应接受命令名参数"""
        from cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["help", "status"])
        assert args.command_name == "status"

    def test_help_help(self):
        """help --help 应正常输出"""
        result = subprocess.run(
            [sys.executable, "cli.py", "help", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "帮助" in result.stdout or "help" in result.stdout


class TestHelpExecution:
    """验证 help 命令执行"""

    def test_help_no_args_lists_commands(self):
        """help 不带参数应列出所有命令"""
        result = subprocess.run(
            [sys.executable, "cli.py", "help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0
        assert "命令列表" in result.stdout
        # 应包含多个命令
        for cmd in ["status", "cycle", "task", "config", "doctor"]:
            assert cmd in result.stdout, f"help 输出缺少 {cmd}"

    def test_help_specific_command(self):
        """help <command> 应显示该命令的详细帮助"""
        result = subprocess.run(
            [sys.executable, "cli.py", "help", "status"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0
        assert "status" in result.stdout
        assert "命令帮助" in result.stdout

    def test_help_unknown_command(self):
        """help <unknown> 应报错"""
        result = subprocess.run(
            [sys.executable, "cli.py", "help", "nonexistent_cmd"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 1
        assert "未知命令" in result.stderr or "未知命令" in result.stdout

    def test_help_doctor(self):
        """help doctor 应显示 doctor 命令帮助"""
        result = subprocess.run(
            [sys.executable, "cli.py", "help", "doctor"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0
        assert "doctor" in result.stdout
        assert "诊断" in result.stdout

    def test_help_config(self):
        """help config 应显示 config 命令帮助"""
        result = subprocess.run(
            [sys.executable, "cli.py", "help", "config"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0
        assert "config" in result.stdout
        assert "配置" in result.stdout

    def test_help_shows_usage_hint(self):
        """help 应显示用法提示"""
        result = subprocess.run(
            [sys.executable, "cli.py", "help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert "用法" in result.stdout or "agent-cli" in result.stdout
