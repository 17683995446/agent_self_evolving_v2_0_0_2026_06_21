"""
阶段168测试：CLI logs日志查看命令

验证 logs 命令存在并支持级别过滤和限制条数
"""

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestLogsCommand:
    """验证 logs 命令存在"""

    def test_logs_in_subcommands(self):
        """logs 应是 CLI 子命令"""
        from cli import build_parser
        import argparse
        parser = build_parser()
        subparsers_action = None
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparsers_action = action
                break
        assert "logs" in subparsers_action.choices

    def test_logs_has_handler(self):
        """logs 命令应有处理器"""
        from cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["logs"])
        assert args.handler == "cmd_logs"

    def test_logs_help(self):
        """logs --help 应正常输出"""
        result = subprocess.run(
            [sys.executable, "cli.py", "logs", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "日志" in result.stdout

    def test_logs_has_level_option(self):
        """logs 应有 --level 选项"""
        result = subprocess.run(
            [sys.executable, "cli.py", "logs", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert "--level" in result.stdout

    def test_logs_has_limit_option(self):
        """logs 应有 --limit 选项"""
        result = subprocess.run(
            [sys.executable, "cli.py", "logs", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert "--limit" in result.stdout

    def test_logs_level_choices(self):
        """logs --level 应支持5个级别"""
        from cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["logs", "--level", "error"])
        assert args.level == "error"


class TestLogsExecution:
    """验证 logs 命令执行"""

    def test_logs_runs(self):
        """logs 命令应能正常运行"""
        result = subprocess.run(
            [sys.executable, "cli.py", "logs"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0

    def test_logs_with_level(self):
        """logs --level error 应能运行"""
        result = subprocess.run(
            [sys.executable, "cli.py", "logs", "--level", "error"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0

    def test_logs_with_limit(self):
        """logs --limit 10 应能运行"""
        result = subprocess.run(
            [sys.executable, "cli.py", "logs", "--limit", "10"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0

    def test_logs_json_format(self):
        """logs --format json 应能运行"""
        result = subprocess.run(
            [sys.executable, "cli.py", "--format", "json", "logs"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0
