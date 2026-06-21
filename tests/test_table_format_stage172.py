"""
阶段172测试：CLI table格式增强

验证 _output_table 接入 format_table
"""

import io
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestTableFormatIntegration:
    """验证 table 格式接入 format_table"""

    def test_output_table_uses_format_table(self):
        """_output_table 应使用 format_table"""
        import inspect
        from cli import OutputFormatter
        source = inspect.getsource(OutputFormatter._output_table)
        assert "format_table" in source, "_output_table 未接入 format_table"

    def test_table_has_headers(self):
        """table 输出应有表头"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("table")
        fmt._color = ColorOutput(force_color=False)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt._output_table({"name": "test", "value": "123"}, "Test")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # 应有表头 Key 和 Value
        assert "Key" in output
        assert "Value" in output

    def test_table_has_separator(self):
        """table 输出应有分隔线"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("table")
        fmt._color = ColorOutput(force_color=False)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt._output_table({"a": "1", "b": "2"}, "Test")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # 应有分隔线（-+- 格式）
        assert "-+-" in output or "---" in output

    def test_table_dict_alignment(self):
        """table dict 输出应对齐"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("table")
        fmt._color = ColorOutput(force_color=False)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt._output_table({"short": "1", "very_long_key": "2"}, "Test")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # 两个值都应在输出中
        assert "short" in output
        assert "very_long_key" in output

    def test_table_list_of_dicts(self):
        """table 应能处理 dict 列表"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("table")
        fmt._color = ColorOutput(force_color=False)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt._output_table([
                {"name": "a", "value": "1"},
                {"name": "b", "value": "2"},
            ], "Test")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # 应有表头 name 和 value
        assert "name" in output
        assert "value" in output

    def test_table_nested_dict(self):
        """table 应能处理嵌套 dict"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("table")
        fmt._color = ColorOutput(force_color=False)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt._output_table({"outer": {"inner": "value"}}, "Test")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # 应显示嵌套内容
        assert "outer" in output
        assert "inner" in output

    def test_table_list_truncation(self):
        """table 应截断长列表"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("table")
        fmt._color = ColorOutput(force_color=False)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt._output_table({"items": list(range(15))}, "Test")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # 应显示截断提示
        assert "more" in output

    def test_table_title_bold(self):
        """table 标题应使用粗体"""
        from cli import OutputFormatter
        from self_evolving_agent.core.output_enhanced import ColorOutput
        fmt = OutputFormatter("table")
        fmt._color = ColorOutput(force_color=True)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fmt._output_table({"a": "1"}, "My Title")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # 应有粗体 ANSI 码
        assert "\033[1m" in output
        assert "My Title" in output
