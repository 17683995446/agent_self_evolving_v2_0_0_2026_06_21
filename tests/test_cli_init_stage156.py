"""
阶段156测试：CLI初始化向导命令

验证:
1. init 命令存在且可调用
2. 向导包含4个步骤（环境检查、配置、验证、指引）
3. 非交互模式下能正常运行
4. 辅助方法（_prompt_yes_no, _write_env_var）正确工作
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestInitCommand:
    """验证 init 命令存在"""

    def test_init_in_subcommands(self):
        """init 应是 CLI 子命令之一"""
        from cli import build_parser
        import argparse
        parser = build_parser()
        subparsers_action = None
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparsers_action = action
                break
        assert "init" in subparsers_action.choices

    def test_init_has_handler(self):
        """init 命令应有对应处理器"""
        from cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["init"])
        assert args.handler == "cmd_init"

    def test_init_help_shows(self):
        """init --help 应正常输出"""
        result = subprocess.run(
            [sys.executable, "cli.py", "init", "--help"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0
        assert "初始化" in result.stdout

    def test_init_runs_non_interactive(self):
        """init 在非交互模式下应正常运行"""
        result = subprocess.run(
            [sys.executable, "cli.py", "init"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,  # 非交互模式
        )
        assert result.returncode == 0
        assert "初始化向导" in result.stdout


class TestInitWizardSteps:
    """验证向导步骤"""

    def test_init_has_step1_env_check(self):
        """向导应包含步骤1: 环境检查"""
        result = subprocess.run(
            [sys.executable, "cli.py", "init"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert "[1/4]" in result.stdout
        assert "Python" in result.stdout

    def test_init_has_step2_config(self):
        """向导应包含步骤2: 配置检查"""
        result = subprocess.run(
            [sys.executable, "cli.py", "init"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert "[2/4]" in result.stdout
        assert ".env" in result.stdout

    def test_init_has_step3_agent_verify(self):
        """向导应包含步骤3: Agent验证"""
        result = subprocess.run(
            [sys.executable, "cli.py", "init"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert "[3/4]" in result.stdout
        assert "Agent" in result.stdout

    def test_init_has_step4_guidance(self):
        """向导应包含步骤4: 下一步指引"""
        result = subprocess.run(
            [sys.executable, "cli.py", "init"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert "[4/4]" in result.stdout
        assert "agent-cli" in result.stdout

    def test_init_checks_dependencies(self):
        """向导应检查依赖"""
        result = subprocess.run(
            [sys.executable, "cli.py", "init"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        # 应检查 Flask 或 NumPy
        assert "Flask" in result.stdout or "NumPy" in result.stdout

    def test_init_checks_api_key(self):
        """向导应检查 API Key"""
        result = subprocess.run(
            [sys.executable, "cli.py", "init"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert "SILICONFLOW_API_KEY" in result.stdout

    def test_init_shows_next_steps(self):
        """向导应显示常用命令"""
        result = subprocess.run(
            [sys.executable, "cli.py", "init"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
        )
        assert "status" in result.stdout
        assert "cycle" in result.stdout
        assert "repl" in result.stdout


class TestInitHelperMethods:
    """验证辅助方法"""

    def test_prompt_yes_no_non_tty_returns_default(self):
        """非 TTY 模式下 _prompt_yes_no 应返回默认值"""
        from cli import CommandHandler, OutputFormatter
        handler = CommandHandler(OutputFormatter("text"))
        # stdin 不是 tty 时应返回默认值
        # 在测试环境中 stdin 通常不是 tty
        result_true = handler._prompt_yes_no("test?", default=True)
        result_false = handler._prompt_yes_no("test?", default=False)
        # 在非交互环境（CI）中应返回默认值
        if not sys.stdin.isatty():
            assert result_true is True
            assert result_false is False

    def test_write_env_var_creates_new(self):
        """_write_env_var 应能创建新变量"""
        from cli import CommandHandler, OutputFormatter
        handler = CommandHandler(OutputFormatter("text"))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("PORT=8080\n")
            f.flush()
            env_path = f.name

        try:
            handler._write_env_var(env_path, "NEW_VAR", "new_value")
            with open(env_path, "r") as f:
                content = f.read()
            assert "PORT=8080" in content
            assert "NEW_VAR=new_value" in content
        finally:
            os.unlink(env_path)

    def test_write_env_var_updates_existing(self):
        """_write_env_var 应能更新已有变量"""
        from cli import CommandHandler, OutputFormatter
        handler = CommandHandler(OutputFormatter("text"))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("SILICONFLOW_API_KEY=old_key\nPORT=8080\n")
            f.flush()
            env_path = f.name

        try:
            handler._write_env_var(env_path, "SILICONFLOW_API_KEY", "new_key")
            with open(env_path, "r") as f:
                content = f.read()
            assert "SILICONFLOW_API_KEY=new_key" in content
            assert "old_key" not in content
            assert "PORT=8080" in content
        finally:
            os.unlink(env_path)

    def test_write_env_var_creates_file(self):
        """_write_env_var 应能处理不存在的文件"""
        from cli import CommandHandler, OutputFormatter
        handler = CommandHandler(OutputFormatter("text"))

        env_path = os.path.join(tempfile.gettempdir(), "test_env_nonexist.env")
        if os.path.exists(env_path):
            os.unlink(env_path)

        try:
            handler._write_env_var(env_path, "NEW_VAR", "value")
            assert os.path.exists(env_path)
            with open(env_path, "r") as f:
                content = f.read()
            assert "NEW_VAR=value" in content
        finally:
            if os.path.exists(env_path):
                os.unlink(env_path)
