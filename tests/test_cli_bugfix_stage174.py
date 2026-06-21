"""
阶段174: 修复CLI两处阻断性Bug

P0 Bug 1: cmd_logs 使用 self.format / self._output_json（CommandHandler无此属性）
   --format json logs 会抛 AttributeError

P0 Bug 2: cmd_repl 使用 subprocess 但文件顶部未 import subprocess
   REPL 中输入 help <command> 会抛 NameError

验证方法：实际执行命令路径，确认不抛异常
"""

import os
import sys
import subprocess

import pytest

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCmdLogsBugFix:
    """Bug 1: cmd_logs 属性引用错误修复"""

    def test_command_handler_has_no_format_attr(self):
        """CommandHandler 不应有 format 属性（确认Bug存在的前提）"""
        from cli import CommandHandler
        ch = CommandHandler.__new__(CommandHandler)
        # CommandHandler 本身不定义 format 属性
        assert not hasattr(CommandHandler, "format"), \
            "CommandHandler 类不应直接定义 format 属性"

    def test_output_formatter_has_format_attr(self):
        """OutputFormatter 应有 format 属性"""
        from cli import OutputFormatter
        fmt = OutputFormatter(format="json")
        assert fmt.format == "json"

    def test_cmd_logs_source_uses_self_fmt(self):
        """验证 cmd_logs 源码使用 self.fmt.format 而非 self.format"""
        import inspect
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_logs)
        # 修复后应使用 self.fmt.format
        assert "self.fmt.format" in source, \
            "cmd_logs 应使用 self.fmt.format（而非 self.format）"
        # 不应直接使用 self.format == "json"
        assert 'self.format ==' not in source or 'self.fmt.format ==' in source

    def test_cmd_logs_json_format_no_attribute_error(self):
        """实际执行: --format json logs 不应抛 AttributeError"""
        result = subprocess.run(
            [sys.executable, "cli.py", "--format", "json", "logs", "--limit", "5"],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        # 不应因 AttributeError 崩溃
        assert "AttributeError" not in result.stderr, \
            f"cmd_logs json格式不应抛AttributeError: {result.stderr}"

    def test_cmd_logs_text_format_works(self):
        """实际执行: text格式 logs 正常工作"""
        result = subprocess.run(
            [sys.executable, "cli.py", "logs", "--limit", "5"],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        # 应正常退出（0）或因日志系统返回0
        assert result.returncode in (0, 1), \
            f"logs命令应正常执行，returncode={result.returncode}, stderr={result.stderr}"


class TestCmdReplBugFix:
    """Bug 2: cmd_repl 未导入 subprocess 修复"""

    def test_subprocess_imported_in_cli(self):
        """cli.py 顶部应导入 subprocess"""
        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "cli.py"
        )
        with open(cli_path, "r") as f:
            content = f.read()
        # 检查 import subprocess 存在
        assert "import subprocess" in content, \
            "cli.py 应导入 subprocess"

    def test_subprocess_module_accessible(self):
        """导入 cli 模块后 subprocess 应可访问"""
        import cli
        assert hasattr(cli, "subprocess"), \
            "cli 模块应能访问 subprocess"

    def test_cmd_repl_source_uses_subprocess(self):
        """验证 cmd_repl 源码使用 subprocess.run"""
        import inspect
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_repl)
        assert "subprocess.run" in source, \
            "cmd_repl 应使用 subprocess.run"

    def test_repl_help_command_no_name_error(self):
        """实际执行: REPL 中 help <command> 不应抛 NameError"""
        # 通过 stdin 向 REPL 发送 help status 命令
        result = subprocess.run(
            [sys.executable, "cli.py", "repl"],
            input="help status\nquit\n",
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        # 不应因 NameError 崩溃
        assert "NameError" not in result.stderr, \
            f"REPL help命令不应抛NameError: {result.stderr}"
        # 应有输出（help status 的帮助信息）
        assert len(result.stdout) > 0 or result.returncode == 0


class TestNoRegression:
    """验证修复不引入回归"""

    def test_cli_help_still_works(self):
        """CLI --help 仍正常工作"""
        result = subprocess.run(
            [sys.executable, "cli.py", "--help"],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower()

    def test_cli_logs_command_registered(self):
        """logs 子命令仍注册"""
        result = subprocess.run(
            [sys.executable, "cli.py", "logs", "--help"],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "logs" in result.stdout.lower()

    def test_cli_repl_command_registered(self):
        """repl 子命令仍注册"""
        result = subprocess.run(
            [sys.executable, "cli.py", "repl", "--help"],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "repl" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
