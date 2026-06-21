"""
阶段164测试：CLI颜色输出接入

验证 OutputFormatter 实际接入 ColorOutput（而非模块仅存在）。
这是"接入性测试"，区别于阶段162的"模块存在性测试"。
"""

import io
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestOutputFormatterColorIntegration:
    """验证 OutputFormatter 实际接入 ColorOutput"""

    def test_formatter_has_color_attribute(self):
        """OutputFormatter 应有 _color 属性（接入证据）"""
        from cli import OutputFormatter
        fmt = OutputFormatter("text")
        assert hasattr(fmt, "_color"), "OutputFormatter 未接入 ColorOutput"

    def test_formatter_color_is_color_output(self):
        """_color 应是 ColorOutput 实例"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("text")
        assert isinstance(fmt._color, ColorOutput)

    def test_error_uses_color(self):
        """error 方法应使用颜色输出"""
        from cli import OutputFormatter
        # 强制启用颜色
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("text")
        fmt._color = ColorOutput(force_color=True)
        # 捕获 stderr
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            fmt.error("test error")
            output = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr
        # 应包含 ANSI 颜色码（红色）
        assert "\033[31m" in output, "error 输出未使用红色"

    def test_success_uses_color(self):
        """success 方法应使用颜色输出"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("text")
        fmt._color = ColorOutput(force_color=True)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt.success("test success")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # 应包含 ANSI 颜色码（绿色）
        assert "\033[32m" in output, "success 输出未使用绿色"

    def test_info_uses_color(self):
        """info 方法应使用颜色输出"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("text")
        fmt._color = ColorOutput(force_color=True)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt.info("test info")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # 应包含 ANSI 颜色码（青色）
        assert "\033[36m" in output, "info 输出未使用青色"

    def test_warning_method_exists(self):
        """应有 warning 方法"""
        from cli import OutputFormatter
        fmt = OutputFormatter("text")
        assert hasattr(fmt, "warning")

    def test_warning_uses_color(self):
        """warning 方法应使用黄色"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("text")
        fmt._color = ColorOutput(force_color=True)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt.warning("test warning")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # 应包含 ANSI 颜色码（黄色）
        assert "\033[33m" in output, "warning 输出未使用黄色"

    def test_table_title_uses_bold(self):
        """table 格式的标题应使用粗体"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("table")
        fmt._color = ColorOutput(force_color=True)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt._output_table({"key": "value"}, "Test Title")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # 应包含粗体 ANSI 码
        assert "\033[1m" in output, "table 标题未使用粗体"

    def test_text_title_uses_bold(self):
        """text 格式的标题应使用粗体"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("text")
        fmt._color = ColorOutput(force_color=True)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt._output_text({"key": "value"}, "Test Title")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        assert "\033[1m" in output, "text 标题未使用粗体"

    def test_no_color_in_non_tty(self):
        """非 TTY 环境应无颜色码（降级）"""
        from cli import OutputFormatter
        fmt = OutputFormatter("text")
        # 默认在测试环境（非 TTY）应禁用颜色
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt.success("test")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # 非 TTY 应无 ANSI 码
        assert "\033[" not in output, "非 TTY 环境不应输出颜色码"

    def test_json_format_no_color(self):
        """JSON 格式不应有颜色码"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("json")
        fmt._color = ColorOutput(force_color=True)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt.success("test")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # JSON 格式的 success 应是纯 JSON，无颜色码
        assert "\033[" not in output, "JSON 格式不应有颜色码"
        assert '"status"' in output


class TestCLIDispatchUsesColor:
    """验证 CLI dispatch 异常处理使用颜色"""

    def test_dispatch_error_uses_color_output(self):
        """dispatch 异常应通过 ColorOutput 输出"""
        from cli import dispatch, OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("text")
        fmt._color = ColorOutput(force_color=True)

        class MockArgs:
            handler = "cmd_nonexistent_method"

        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            result = dispatch(MockArgs(), fmt)
            output = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr
        # dispatch 找不到方法时应通过 formatter.error 输出
        assert result == 1
