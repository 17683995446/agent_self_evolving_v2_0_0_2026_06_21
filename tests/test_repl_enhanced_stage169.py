"""
阶段169测试：REPL增强

验证 readline 集成、命令历史、Tab补全、help <command>
"""

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestREPLEnhancement:
    """验证 REPL 增强"""

    def test_repl_uses_readline(self):
        """REPL 应尝试导入 readline"""
        import inspect
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_repl)
        assert "import readline" in source, "REPL 未集成 readline"

    def test_repl_has_history_persistence(self):
        """REPL 应有命令历史持久化"""
        import inspect
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_repl)
        assert "read_history_file" in source or "write_history_file" in source

    def test_repl_has_tab_completion(self):
        """REPL 应有 Tab 补全"""
        import inspect
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_repl)
        assert "set_completer" in source
        assert "tab: complete" in source

    def test_repl_has_completer_function(self):
        """REPL 应有补全器函数"""
        import inspect
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_repl)
        assert "completer" in source
        assert "COMMANDS" in source

    def test_repl_completes_all_commands(self):
        """补全器应包含所有命令"""
        import inspect
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_repl)
        # 验证补全列表包含新命令
        for cmd in ["doctor", "config", "logs", "init", "errors"]:
            assert cmd in source, f"补全列表缺少 {cmd}"

    def test_repl_has_help_command(self):
        """REPL 应支持 help <command>"""
        import inspect
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_repl)
        assert "help " in source or "startswith" in source

    def test_repl_history_file_path(self):
        """REPL 历史文件应在项目目录"""
        import inspect
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_repl)
        assert ".cli_history" in source

    def test_repl_graceful_degradation(self):
        """REPL 在 readline 不可用时应优雅降级"""
        import inspect
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_repl)
        assert "ImportError" in source
        assert "readline 不可用" in source


class TestREPLExecution:
    """验证 REPL 执行"""

    def test_repl_quit_immediately(self):
        """REPL 输入 quit 应立即退出"""
        result = subprocess.run(
            [sys.executable, "cli.py", "repl"],
            input="quit\n",
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "交互模式" in result.stdout

    def test_repl_exit_immediately(self):
        """REPL 输入 exit 应立即退出"""
        result = subprocess.run(
            [sys.executable, "cli.py", "repl"],
            input="exit\n",
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0

    def test_repl_eof_exits(self):
        """REPL 收到 EOF 应退出"""
        result = subprocess.run(
            [sys.executable, "cli.py", "repl"],
            input="",
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0

    def test_repl_shows_readline_status(self):
        """REPL 应显示 readline 状态"""
        result = subprocess.run(
            [sys.executable, "cli.py", "repl"],
            input="quit\n",
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        # 应显示"已启用"或"不可用"
        assert "命令历史" in result.stdout or "readline" in result.stdout
