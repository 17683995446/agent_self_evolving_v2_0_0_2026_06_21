"""
阶段155测试：CLI帮助与版本信息增强

验证:
1. --version 参数可用
2. epilog 示例存在
3. 子命令 help 详细
4. 帮助信息可正常输出
"""

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestCLIVersion:
    """验证 --version 参数"""

    def test_version_flag_exists(self):
        """--version 参数应存在"""
        from cli import build_parser
        parser = build_parser()
        # 检查 parser 有 version action
        has_version = False
        for action in parser._actions:
            if "--version" in action.option_strings or "-V" in action.option_strings:
                has_version = True
                break
        assert has_version, "应有 --version 或 -V 参数"

    def test_version_output(self):
        """--version 应输出版本号"""
        result = subprocess.run(
            [sys.executable, "cli.py", "--version"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "agent-cli" in result.stdout
        # 应包含版本号格式
        assert any(c.isdigit() for c in result.stdout)

    def test_version_short_flag(self):
        """-V 短选项应可用"""
        result = subprocess.run(
            [sys.executable, "cli.py", "-V"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "agent-cli" in result.stdout


class TestCLIEpilog:
    """验证 epilog 示例"""

    def test_epilog_exists(self):
        """epilog 应存在"""
        from cli import build_parser, EPILOG
        assert EPILOG is not None
        assert len(EPILOG) > 100  # 应有足够内容

    def test_epilog_has_examples(self):
        """epilog 应包含使用示例"""
        from cli import EPILOG
        assert "示例" in EPILOG or "example" in EPILOG.lower()
        assert "agent-cli" in EPILOG

    def test_epilog_has_env_vars(self):
        """epilog 应包含环境变量说明"""
        from cli import EPILOG
        assert "SILICONFLOW_API_KEY" in EPILOG
        assert "PORT" in EPILOG

    def test_help_shows_epilog(self):
        """--help 应显示 epilog"""
        result = subprocess.run(
            [sys.executable, "cli.py", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "示例" in result.stdout or "example" in result.stdout.lower()

    def test_epilog_has_json_example(self):
        """epilog 应包含 JSON 输出示例"""
        from cli import EPILOG
        assert "--format json" in EPILOG


class TestSubcommandHelp:
    """验证子命令 help 详细"""

    def test_status_help_detailed(self):
        """status 命令 help 应详细"""
        result = subprocess.run(
            [sys.executable, "cli.py", "status", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        # help 应比单纯的"显示Agent状态"更详细
        assert "状态" in result.stdout

    def test_task_help_has_choices_desc(self):
        """task 子命令的 choices 应有描述"""
        result = subprocess.run(
            [sys.executable, "cli.py", "task", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        # 应有 submit/status/result/execute 的描述
        assert "submit" in result.stdout
        assert "execute" in result.stdout

    def test_review_help_has_choices_desc(self):
        """review 子命令的 choices 应有描述"""
        result = subprocess.run(
            [sys.executable, "cli.py", "review", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "code" in result.stdout
        assert "file" in result.stdout
        assert "dir" in result.stdout

    def test_perf_help_has_choices_desc(self):
        """perf 子命令的 choices 应有描述"""
        result = subprocess.run(
            [sys.executable, "cli.py", "perf", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "report" in result.stdout
        assert "cache" in result.stdout

    def test_plugin_help_has_choices_desc(self):
        """plugin 子命令的 choices 应有描述"""
        result = subprocess.run(
            [sys.executable, "cli.py", "plugin", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "list" in result.stdout
        assert "health" in result.stdout

    def test_chat_help_mentions_api_key(self):
        """chat 命令 help 应提及 API Key"""
        result = subprocess.run(
            [sys.executable, "cli.py", "chat", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "SILICONFLOW_API_KEY" in result.stdout or "API" in result.stdout

    def test_format_help_has_default(self):
        """--format help 应说明默认值"""
        result = subprocess.run(
            [sys.executable, "cli.py", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "text" in result.stdout  # 默认格式


class TestCLIHelpConsistency:
    """验证 CLI 帮助一致性"""

    def test_all_subcommands_have_help(self):
        """所有子命令都应有 help 文本"""
        from cli import build_parser
        parser = build_parser()
        # 找到 subparsers action（通过 _SubParsersAction 类型识别）
        import argparse
        subparsers_action = None
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparsers_action = action
                break
        assert subparsers_action is not None
        # choices 是 dict（子命令名 -> parser）
        subcommands = list(subparsers_action.choices.keys())
        # 每个子命令都应有 help
        for name in subcommands:
            result = subprocess.run(
                [sys.executable, "cli.py", name, "--help"],
                capture_output=True, text=True, cwd=str(PROJECT_ROOT)
            )
            assert result.returncode == 0, f"子命令 {name} --help 失败"
            assert len(result.stdout) > 50, f"子命令 {name} 的 help 输出过短"

    def test_no_empty_help(self):
        """不应有空 help 文本"""
        from cli import build_parser
        import argparse
        parser = build_parser()
        subparsers_action = None
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparsers_action = action
                break
        subcommands = list(subparsers_action.choices.keys())
        for name in subcommands:
            result = subprocess.run(
                [sys.executable, "cli.py", name, "--help"],
                capture_output=True, text=True, cwd=str(PROJECT_ROOT)
            )
            assert result.returncode == 0
            assert len(result.stdout) > 50, f"子命令 {name} 的 help 输出过短"
