"""
阶段167测试：CLI config配置管理命令

验证 config 命令的5个子操作: get/set/delete/list/validate
"""

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestConfigCommand:
    """验证 config 命令存在"""

    def test_config_in_subcommands(self):
        """config 应是 CLI 子命令"""
        from cli import build_parser
        import argparse
        parser = build_parser()
        subparsers_action = None
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparsers_action = action
                break
        assert "config" in subparsers_action.choices

    def test_config_has_handler(self):
        """config 命令应有处理器"""
        from cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["config", "list"])
        assert args.handler == "cmd_config"

    def test_config_help(self):
        """config --help 应正常输出"""
        result = subprocess.run(
            [sys.executable, "cli.py", "config", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "配置" in result.stdout

    def test_config_has_5_actions(self):
        """config 应有5个子操作"""
        result = subprocess.run(
            [sys.executable, "cli.py", "config", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for action in ["get", "set", "delete", "list", "validate"]:
            assert action in result.stdout, f"config 命令缺少 {action} 操作"


class TestConfigList:
    """验证 config list"""

    def test_config_list_runs(self):
        """config list 应能正常运行"""
        result = subprocess.run(
            [sys.executable, "cli.py", "config", "list"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0
        assert "配置快照" in result.stdout


class TestConfigSetGet:
    """验证 config set 和 get（同一进程内，配置存储在内存）"""

    def test_config_set_returns_success(self):
        """config set 应返回成功"""
        result = subprocess.run(
            [sys.executable, "cli.py", "config", "set", "test_key_167", "test_value"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0
        assert "已设置" in result.stdout

    def test_config_set_and_get_same_process(self):
        """config set 后在同一进程 get 应能获取到"""
        from cli import build_parser, dispatch, OutputFormatter
        parser = build_parser()
        fmt = OutputFormatter("text")

        # set
        args = parser.parse_args(["config", "set", "test_key_167", "test_value"])
        result = dispatch(args, fmt)
        assert result == 0

        # get（同一进程，同一 agent 实例）
        args = parser.parse_args(["config", "get", "test_key_167"])
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            result = dispatch(args, fmt)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        assert result == 0
        assert "test_value" in output

    def test_config_set_json_value(self):
        """config set 应支持 JSON 值"""
        result = subprocess.run(
            [sys.executable, "cli.py", "config", "set", "test_json_167", '{"a": 1}'],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0


class TestConfigDelete:
    """验证 config delete（同一进程内）"""

    def test_config_delete_runs(self):
        """config delete 应能运行"""
        from cli import build_parser, dispatch, OutputFormatter
        parser = build_parser()
        fmt = OutputFormatter("text")

        # 先设置
        args = parser.parse_args(["config", "set", "test_del_167", "val"])
        dispatch(args, fmt)

        # 再删除
        args = parser.parse_args(["config", "delete", "test_del_167"])
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            result = dispatch(args, fmt)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        assert result == 0
        assert "已删除" in output


class TestConfigValidate:
    """验证 config validate"""

    def test_config_validate_runs(self):
        """config validate 应能运行"""
        result = subprocess.run(
            [sys.executable, "cli.py", "config", "validate"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode in (0, 1)
        assert "配置校验结果" in result.stdout

    def test_config_validate_shows_counts(self):
        """config validate 应显示错误和警告数量"""
        result = subprocess.run(
            [sys.executable, "cli.py", "config", "validate"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert "错误:" in result.stdout
        assert "警告:" in result.stdout
        assert "配置项总数" in result.stdout
