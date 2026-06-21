"""
阶段162测试：输出体验提升

验证:
1. ColorOutput 颜色输出器
2. ProgressIndicator 进度提示器
3. format_status 状态格式化
4. format_table 表格格式化
5. 非 TTY 环境降级
"""

import io
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestColorOutput:
    """验证颜色输出器"""

    def test_color_output_importable(self):
        """ColorOutput 应可导入"""
        from self_evolving_agent.core.output_enhanced import ColorOutput
        assert ColorOutput is not None

    def test_color_output_no_color_in_non_tty(self):
        """非 TTY 环境应禁用颜色"""
        from self_evolving_agent.core.output_enhanced import ColorOutput
        stream = io.StringIO()  # StringIO 不是 TTY
        co = ColorOutput(stream=stream)
        assert co._use_color is False

    def test_color_output_force_color(self):
        """强制启用颜色"""
        from self_evolving_agent.core.output_enhanced import ColorOutput, Colors
        stream = io.StringIO()
        co = ColorOutput(stream=stream, force_color=True)
        assert co._use_color is True
        result = co.colorize("test", Colors.RED)
        assert Colors.RED in result
        assert Colors.RESET in result

    def test_colorize_without_color(self):
        """禁用颜色时应返回原文本"""
        from self_evolving_agent.core.output_enhanced import ColorOutput, Colors
        stream = io.StringIO()
        co = ColorOutput(stream=stream, force_color=False)
        result = co.colorize("test", Colors.RED)
        assert result == "test"

    def test_success_method(self):
        """success 方法应工作"""
        from self_evolving_agent.core.output_enhanced import ColorOutput
        co = ColorOutput(force_color=True)
        result = co.success("done")
        assert "done" in result

    def test_error_method(self):
        """error 方法应工作"""
        from self_evolving_agent.core.output_enhanced import ColorOutput
        co = ColorOutput(force_color=True)
        result = co.error("failed")
        assert "failed" in result

    def test_warning_method(self):
        """warning 方法应工作"""
        from self_evolving_agent.core.output_enhanced import ColorOutput
        co = ColorOutput(force_color=True)
        result = co.warning("caution")
        assert "caution" in result

    def test_info_method(self):
        """info 方法应工作"""
        from self_evolving_agent.core.output_enhanced import ColorOutput
        co = ColorOutput(force_color=True)
        result = co.info("hello")
        assert "hello" in result

    def test_print_success(self):
        """print_success 应输出到流"""
        from self_evolving_agent.core.output_enhanced import ColorOutput
        stream = io.StringIO()
        co = ColorOutput(stream=stream, force_color=False)
        co.print_success("operation done")
        output = stream.getvalue()
        assert "OK" in output
        assert "operation done" in output


class TestProgressIndicator:
    """验证进度提示器"""

    def test_progress_importable(self):
        """ProgressIndicator 应可导入"""
        from self_evolving_agent.core.output_enhanced import ProgressIndicator
        assert ProgressIndicator is not None

    def test_progress_non_tty_no_output(self):
        """非 TTY 环境不应输出进度"""
        from self_evolving_agent.core.output_enhanced import ProgressIndicator
        stream = io.StringIO()
        prog = ProgressIndicator("loading", stream=stream)
        prog.start()
        prog.update("still loading")
        prog.stop("done")
        # 非 TTY 应无 spinner 输出
        output = stream.getvalue()
        assert "⠋" not in output  # 无 spinner 字符

    def test_progress_context_manager(self):
        """进度提示器应支持上下文管理器"""
        from self_evolving_agent.core.output_enhanced import ProgressIndicator
        stream = io.StringIO()
        with ProgressIndicator("working", stream=stream) as prog:
            prog.update("still working")
        # 不应抛出异常

    def test_progress_stop_with_message(self):
        """stop 应能输出最终消息"""
        from self_evolving_agent.core.output_enhanced import ProgressIndicator
        stream = io.StringIO()
        prog = ProgressIndicator("loading", stream=stream)
        prog.start()
        prog.stop("completed")
        # 非 TTY 模式下应输出最终消息
        assert "completed" in stream.getvalue()


class TestFormatStatus:
    """验证状态格式化"""

    def test_format_status_running(self):
        """running 状态应格式化为成功色"""
        from self_evolving_agent.core.output_enhanced import format_status
        result = format_status("running")
        assert "running" in result

    def test_format_status_error(self):
        """error 状态应格式化为错误色"""
        from self_evolving_agent.core.output_enhanced import format_status
        result = format_status("error")
        assert "error" in result

    def test_format_status_warning(self):
        """warning 状态应格式化为警告色"""
        from self_evolving_agent.core.output_enhanced import format_status
        result = format_status("warning")
        assert "warning" in result

    def test_format_status_unknown(self):
        """未知状态应原样返回"""
        from self_evolving_agent.core.output_enhanced import format_status
        result = format_status("custom")
        assert result == "custom"


class TestFormatTable:
    """验证表格格式化"""

    def test_format_table_basic(self):
        """基本表格格式化"""
        from self_evolving_agent.core.output_enhanced import format_table
        result = format_table(
            ["Name", "Value"],
            [["foo", "1"], ["bar", "2"]]
        )
        assert "Name" in result
        assert "Value" in result
        assert "foo" in result
        assert "bar" in result

    def test_format_table_has_separator(self):
        """表格应有分隔线"""
        from self_evolving_agent.core.output_enhanced import format_table
        result = format_table(["A", "B"], [["1", "2"]])
        assert "-" in result  # 有分隔线
        assert "|" in result  # 有列分隔

    def test_format_table_empty(self):
        """空表格应返回空字符串"""
        from self_evolving_agent.core.output_enhanced import format_table
        result = format_table([], [])
        assert result == ""

    def test_format_table_alignment(self):
        """表格应对齐"""
        from self_evolving_agent.core.output_enhanced import format_table
        result = format_table(
            ["Name", "Value"],
            [["a", "100"], ["bbb", "1"]]
        )
        lines = result.split("\n")
        # 表头 + 分隔线 + 2行数据 = 4行
        assert len(lines) == 4
        # 数据行应有列分隔符
        assert "|" in lines[0]  # 表头
        assert "|" in lines[2]  # 第一行数据
        assert "|" in lines[3]  # 第二行数据


class TestGlobalInstance:
    """验证全局实例"""

    def test_global_color_output_exists(self):
        """全局 color_output 应存在"""
        from self_evolving_agent.core.output_enhanced import color_output
        assert color_output is not None

    def test_global_color_output_methods(self):
        """全局 color_output 应有方法"""
        from self_evolving_agent.core.output_enhanced import color_output
        assert hasattr(color_output, "success")
        assert hasattr(color_output, "error")
        assert hasattr(color_output, "info")
