"""
阶段178: ProgressIndicator 接入耗时操作验证

验证 CLI 耗时命令接入 ProgressIndicator：
- cmd_cycle (run_cycle)
- cmd_task execute (execute_task)
- cmd_review code/file/dir (review_code/review_file/review_directory)
- cmd_docs generate/file (generate_docs/generate_file_docs)
- cmd_plugin discover (discover_plugins)

验证方法：inspect.getsource() 检查源码包含 self.fmt.progress 调用
"""

import os
import sys
import inspect

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestProgressIndicatorModule:
    """ProgressIndicator 模块验证"""

    def test_progress_indicator_importable(self):
        """ProgressIndicator 可导入"""
        from self_evolving_agent.core.output_enhanced import ProgressIndicator
        assert ProgressIndicator is not None

    def test_progress_indicator_context_manager(self):
        """ProgressIndicator 支持上下文管理器"""
        from self_evolving_agent.core.output_enhanced import ProgressIndicator
        pi = ProgressIndicator("test")
        # 应支持 with 语句
        assert hasattr(pi, "__enter__")
        assert hasattr(pi, "__exit__")

    def test_progress_indicator_non_tty_degrades(self):
        """非 TTY 环境自动降级"""
        from self_evolving_agent.core.output_enhanced import ProgressIndicator
        import io
        stream = io.StringIO()  # 非 TTY
        pi = ProgressIndicator("test", stream=stream)
        assert pi._use_output is False  # 非TTY不输出spinner

    def test_progress_indicator_start_stop(self):
        """ProgressIndicator start/stop 不抛异常"""
        from self_evolving_agent.core.output_enhanced import ProgressIndicator
        import io
        stream = io.StringIO()
        pi = ProgressIndicator("test", stream=stream)
        pi.start()
        pi.stop("完成")


class TestOutputFormatterProgressMethod:
    """OutputFormatter.progress 方法验证"""

    def test_progress_method_exists(self):
        """OutputFormatter 有 progress 方法"""
        from cli import OutputFormatter
        assert hasattr(OutputFormatter, "progress")

    def test_progress_method_returns_context_manager(self):
        """progress 方法返回上下文管理器"""
        from cli import OutputFormatter
        fmt = OutputFormatter()
        pi = fmt.progress("test")
        assert hasattr(pi, "__enter__")
        assert hasattr(pi, "__exit__")

    def test_progress_method_source(self):
        """progress 方法源码使用 ProgressIndicator"""
        from cli import OutputFormatter
        source = inspect.getsource(OutputFormatter.progress)
        assert "ProgressIndicator" in source


class TestCLICommandsUseProgress:
    """CLI 命令接入 progress 验证"""

    def test_cmd_cycle_uses_progress(self):
        """cmd_cycle 使用 progress"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_cycle)
        assert "self.fmt.progress" in source

    def test_cmd_task_execute_uses_progress(self):
        """cmd_task execute 分支使用 progress"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_task)
        assert "self.fmt.progress" in source

    def test_cmd_review_uses_progress(self):
        """cmd_review 使用 progress"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_review)
        assert "self.fmt.progress" in source

    def test_cmd_review_code_branch_uses_progress(self):
        """cmd_review code 分支使用 progress"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_review)
        # code 分支应有进度提示
        assert "正在审查代码" in source or "self.fmt.progress" in source

    def test_cmd_review_file_branch_uses_progress(self):
        """cmd_review file 分支使用 progress"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_review)
        assert "正在审查文件" in source

    def test_cmd_review_dir_branch_uses_progress(self):
        """cmd_review dir 分支使用 progress"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_review)
        assert "正在审查目录" in source

    def test_cmd_docs_uses_progress(self):
        """cmd_docs 使用 progress"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_docs)
        assert "self.fmt.progress" in source

    def test_cmd_docs_generate_uses_progress(self):
        """cmd_docs generate 分支使用 progress"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_docs)
        assert "正在生成文档" in source

    def test_cmd_plugin_discover_uses_progress(self):
        """cmd_plugin discover 分支使用 progress"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_plugin)
        assert "self.fmt.progress" in source


class TestProgressIntegration:
    """进度提示器集成测试"""

    def test_progress_with_block_executes(self):
        """with progress 块内代码正常执行"""
        from cli import OutputFormatter
        fmt = OutputFormatter()
        executed = []
        with fmt.progress("测试操作..."):
            executed.append("inside")
        assert "inside" in executed

    def test_progress_with_block_exception(self):
        """with progress 块内异常不丢失"""
        from cli import OutputFormatter
        fmt = OutputFormatter()
        with pytest.raises(ValueError):
            with fmt.progress("测试异常操作..."):
                raise ValueError("测试异常")

    def test_progress_count_in_cli(self):
        """CLI 中 progress 调用数量 >= 5（cycle/task/review/docs/plugin）"""
        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "cli.py"
        )
        with open(cli_path, "r") as f:
            content = f.read()
        count = content.count("self.fmt.progress(")
        assert count >= 5, f"CLI中应有至少5处progress调用，实际{count}处"


class TestNoRegression:
    """验证不引入回归"""

    def test_cli_help_still_works(self):
        """CLI --help 仍正常"""
        import subprocess
        result = subprocess.run(
            [sys.executable, "cli.py", "--help"],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0

    def test_cmd_cycle_still_returns_int(self):
        """cmd_cycle 仍返回 int"""
        from cli import CommandHandler
        source = inspect.getsource(CommandHandler.cmd_cycle)
        assert "return 0" in source or "return 1" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
