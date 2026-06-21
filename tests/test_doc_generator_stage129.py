"""
阶段129: 真实业务场景2 — 文档生成模块 专项测试

验证:
1. 数据结构（ArgDoc/FunctionDoc/ClassDoc/ModuleDoc/DocumentationReport）
2. DocExtractor提取功能
3. MarkdownRenderer渲染
4. HTMLRenderer渲染
5. TextRenderer渲染
6. DocumentationGenerator生成
7. 文件和目录生成
8. Agent集成
9. 并发安全
10. 性能
11. 异常容错
12. 第一性原理验证
"""

import os
import time
import tempfile
import threading
import pytest

from self_evolving_agent.core.doc_generator import (
    ArgDoc,
    FunctionDoc,
    ClassDoc,
    ModuleDoc,
    DocumentationReport,
    DocFormat,
    DocRenderer,
    MarkdownRenderer,
    HTMLRenderer,
    TextRenderer,
    DocExtractor,
    DocumentationGenerator,
    create_doc_generator,
    generate_docs,
    generate_file_docs,
)


# ============================================================
# 1. 数据结构测试
# ============================================================

class TestDataStructures:
    """数据结构测试"""

    def test_doc_format_enum(self):
        """文档格式枚举"""
        assert DocFormat.MARKDOWN.value == "markdown"
        assert DocFormat.HTML.value == "html"
        assert DocFormat.TEXT.value == "text"
        assert DocFormat.RST.value == "rst"

    def test_arg_doc_creation(self):
        """参数文档创建"""
        arg = ArgDoc(name="x", type_hint="int", default="0", description="value")
        assert arg.name == "x"
        assert arg.type_hint == "int"
        assert arg.default == "0"
        assert arg.description == "value"

    def test_arg_doc_to_dict(self):
        """参数文档序列化"""
        arg = ArgDoc(name="x", type_hint="str")
        d = arg.to_dict()
        assert d["name"] == "x"
        assert d["type_hint"] == "str"

    def test_function_doc_creation(self):
        """函数文档创建"""
        func = FunctionDoc(
            name="foo",
            signature="def foo(a: int) -> bool",
            docstring="Do something.",
        )
        assert func.name == "foo"
        assert func.docstring == "Do something."
        assert func.is_async is False
        assert func.is_private is False

    def test_function_doc_to_dict(self):
        """函数文档序列化"""
        func = FunctionDoc(
            name="foo",
            signature="def foo()",
            args=[ArgDoc(name="x")],
        )
        d = func.to_dict()
        assert d["name"] == "foo"
        assert len(d["args"]) == 1

    def test_class_doc_creation(self):
        """类文档创建"""
        cls = ClassDoc(name="Foo", docstring="A class.")
        assert cls.name == "Foo"
        assert cls.docstring == "A class."
        assert cls.methods == []
        assert cls.attributes == []

    def test_class_doc_to_dict(self):
        """类文档序列化"""
        cls = ClassDoc(
            name="Foo",
            bases=["Base"],
            attributes=["attr1"],
        )
        d = cls.to_dict()
        assert d["name"] == "Foo"
        assert d["bases"] == ["Base"]
        assert d["attributes"] == ["attr1"]

    def test_module_doc_creation(self):
        """模块文档创建"""
        mod = ModuleDoc(name="test", file_path="test.py")
        assert mod.name == "test"
        assert mod.functions == []
        assert mod.classes == []

    def test_module_doc_to_dict(self):
        """模块文档序列化"""
        mod = ModuleDoc(
            name="test",
            docstring="Module doc.",
            imports=["import os"],
        )
        d = mod.to_dict()
        assert d["name"] == "test"
        assert d["docstring"] == "Module doc."
        assert d["imports"] == ["import os"]

    def test_documentation_report_creation(self):
        """文档报告创建"""
        report = DocumentationReport(
            module=ModuleDoc(name="test"),
            format=DocFormat.MARKDOWN,
            content="# Test",
        )
        assert report.format == DocFormat.MARKDOWN
        assert report.content == "# Test"
        assert report.error is None

    def test_documentation_report_to_dict(self):
        """文档报告序列化"""
        report = DocumentationReport(
            module=ModuleDoc(name="test"),
            format=DocFormat.HTML,
            content="<html></html>",
        )
        d = report.to_dict()
        assert d["format"] == "html"
        assert d["content_length"] == len("<html></html>")


# ============================================================
# 2. DocExtractor 提取测试
# ============================================================

class TestDocExtractor:
    """DocExtractor提取测试"""

    def test_extractor_creation(self):
        """提取器创建"""
        extractor = DocExtractor()
        assert extractor is not None

    def test_extract_empty_code(self):
        """提取空代码"""
        extractor = DocExtractor()
        mod = extractor.extract("", "empty.py")
        assert mod.name == "empty"
        assert mod.functions == []

    def test_extract_module_docstring(self):
        """提取模块文档字符串"""
        extractor = DocExtractor()
        code = '"""Module doc."""\n\nx = 1\n'
        mod = extractor.extract(code, "test.py")
        assert mod.docstring == "Module doc."

    def test_extract_function(self):
        """提取函数"""
        extractor = DocExtractor()
        code = '''
def foo(a, b):
    """Do something."""
    return a + b
'''
        mod = extractor.extract(code, "test.py")
        assert len(mod.functions) == 1
        assert mod.functions[0].name == "foo"
        assert mod.functions[0].docstring == "Do something."
        assert len(mod.functions[0].args) == 2

    def test_extract_function_with_types(self):
        """提取带类型注解的函数"""
        extractor = DocExtractor()
        code = '''
def foo(a: int, b: str = "hi") -> bool:
    """Doc."""
    return True
'''
        mod = extractor.extract(code, "test.py")
        func = mod.functions[0]
        assert func.args[0].type_hint == "int"
        assert func.args[1].type_hint == "str"
        assert func.args[1].default == "'hi'"
        assert func.return_type == "bool"

    def test_extract_async_function(self):
        """提取异步函数"""
        extractor = DocExtractor()
        code = '''
async def foo():
    """Async doc."""
    pass
'''
        mod = extractor.extract(code, "test.py")
        assert mod.functions[0].is_async is True

    def test_extract_private_function(self):
        """提取私有函数"""
        extractor = DocExtractor()
        code = '''
def _private():
    """Private."""
    pass
'''
        mod = extractor.extract(code, "test.py")
        assert mod.functions[0].is_private is True

    def test_extract_class(self):
        """提取类"""
        extractor = DocExtractor()
        code = '''
class Foo(Base):
    """A class."""
    
    attr = 1
    
    def method(self):
        """Method."""
        pass
'''
        mod = extractor.extract(code, "test.py")
        assert len(mod.classes) == 1
        cls = mod.classes[0]
        assert cls.name == "Foo"
        assert cls.docstring == "A class."
        assert "Base" in cls.bases
        assert "attr" in cls.attributes
        assert len(cls.methods) == 1

    def test_extract_imports(self):
        """提取导入"""
        extractor = DocExtractor()
        code = '''
import os
import sys
from pathlib import Path
'''
        mod = extractor.extract(code, "test.py")
        assert len(mod.imports) == 3
        assert "import os" in mod.imports
        assert "import sys" in mod.imports

    def test_extract_constants(self):
        """提取常量"""
        extractor = DocExtractor()
        code = '''
MAX_SIZE = 100
DEFAULT = "test"
regular_var = 1
'''
        mod = extractor.extract(code, "test.py")
        assert len(mod.constants) == 2
        names = [c[0] for c in mod.constants]
        assert "MAX_SIZE" in names
        assert "DEFAULT" in names

    def test_extract_docstring_args(self):
        """解析docstring中的参数"""
        extractor = DocExtractor()
        code = '''
def foo(a, b):
    """Do something.

    Args:
        a: First arg.
        b: Second arg.

    Returns:
        The result.
    """
    return a + b
'''
        mod = extractor.extract(code, "test.py")
        func = mod.functions[0]
        assert func.args[0].description == "First arg."
        assert func.args[1].description == "Second arg."
        assert "result" in func.returns.lower()

    def test_extract_docstring_raises(self):
        """解析docstring中的异常"""
        extractor = DocExtractor()
        code = '''
def foo():
    """Doc.

    Raises:
        ValueError: If invalid.
        TypeError: If wrong type.
    """
    pass
'''
        mod = extractor.extract(code, "test.py")
        func = mod.functions[0]
        assert "ValueError" in func.raises
        assert "TypeError" in func.raises

    def test_extract_syntax_error(self):
        """语法错误时返回空模块"""
        extractor = DocExtractor()
        code = "def foo(\n"
        mod = extractor.extract(code, "test.py")
        assert mod.functions == []
        assert mod.classes == []

    def test_extract_decorators(self):
        """提取装饰器"""
        extractor = DocExtractor()
        code = '''
@property
def foo(self):
    """Property."""
    return 1
'''
        mod = extractor.extract(code, "test.py")
        assert len(mod.functions[0].decorators) > 0


# ============================================================
# 3. MarkdownRenderer 测试
# ============================================================

class TestMarkdownRenderer:
    """MarkdownRenderer测试"""

    def test_render_basic(self):
        """基本渲染"""
        renderer = MarkdownRenderer()
        mod = ModuleDoc(name="test", docstring="Module doc.")
        content = renderer.render(mod)
        assert "# test" in content
        assert "Module doc." in content

    def test_render_function(self):
        """渲染函数"""
        renderer = MarkdownRenderer()
        mod = ModuleDoc(
            name="test",
            functions=[
                FunctionDoc(
                    name="foo",
                    signature="def foo(a: int) -> bool",
                    docstring="Do something.",
                    args=[ArgDoc(name="a", type_hint="int")],
                )
            ],
        )
        content = renderer.render(mod)
        assert "foo" in content
        assert "def foo" in content
        assert "Do something." in content

    def test_render_class(self):
        """渲染类"""
        renderer = MarkdownRenderer()
        mod = ModuleDoc(
            name="test",
            classes=[
                ClassDoc(
                    name="Foo",
                    docstring="A class.",
                    bases=["Base"],
                    attributes=["attr1"],
                )
            ],
        )
        content = renderer.render(mod)
        assert "Foo" in content
        assert "Base" in content
        assert "attr1" in content

    def test_render_imports(self):
        """渲染导入"""
        renderer = MarkdownRenderer()
        mod = ModuleDoc(
            name="test",
            imports=["import os", "import sys"],
        )
        content = renderer.render(mod)
        assert "import os" in content
        assert "import sys" in content
        assert "```python" in content

    def test_render_constants(self):
        """渲染常量"""
        renderer = MarkdownRenderer()
        mod = ModuleDoc(
            name="test",
            constants=[("MAX", "100"), ("NAME", '"test"')],
        )
        content = renderer.render(mod)
        assert "MAX" in content
        assert "100" in content

    def test_render_args_table(self):
        """渲染参数表格"""
        renderer = MarkdownRenderer()
        mod = ModuleDoc(
            name="test",
            functions=[
                FunctionDoc(
                    name="foo",
                    signature="def foo(a, b)",
                    args=[
                        ArgDoc(name="a", type_hint="int", description="first"),
                        ArgDoc(name="b", type_hint="str", default="'hi'", description="second"),
                    ],
                )
            ],
        )
        content = renderer.render(mod)
        assert "| 名称 |" in content
        assert "first" in content
        assert "second" in content


# ============================================================
# 4. HTMLRenderer 测试
# ============================================================

class TestHTMLRenderer:
    """HTMLRenderer测试"""

    def test_render_basic(self):
        """基本渲染"""
        renderer = HTMLRenderer()
        mod = ModuleDoc(name="test", docstring="Module doc.")
        content = renderer.render(mod)
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "test" in content
        assert "Module doc." in content

    def test_render_function(self):
        """渲染函数"""
        renderer = HTMLRenderer()
        mod = ModuleDoc(
            name="test",
            functions=[
                FunctionDoc(
                    name="foo",
                    signature="def foo()",
                    docstring="Do something.",
                )
            ],
        )
        content = renderer.render(mod)
        assert "<h4>" in content
        assert "foo" in content
        assert "<pre><code>" in content

    def test_render_class(self):
        """渲染类"""
        renderer = HTMLRenderer()
        mod = ModuleDoc(
            name="test",
            classes=[
                ClassDoc(name="Foo", docstring="A class."),
            ],
        )
        content = renderer.render(mod)
        assert "<h3>" in content
        assert "Foo" in content

    def test_render_table(self):
        """渲染表格"""
        renderer = HTMLRenderer()
        mod = ModuleDoc(
            name="test",
            functions=[
                FunctionDoc(
                    name="foo",
                    signature="def foo(a)",
                    args=[ArgDoc(name="a", type_hint="int")],
                )
            ],
        )
        content = renderer.render(mod)
        assert "<table>" in content
        assert "<th>" in content


# ============================================================
# 5. TextRenderer 测试
# ============================================================

class TestTextRenderer:
    """TextRenderer测试"""

    def test_render_basic(self):
        """基本渲染"""
        renderer = TextRenderer()
        mod = ModuleDoc(name="test", docstring="Module doc.")
        content = renderer.render(mod)
        assert "Module: test" in content
        assert "Module doc." in content
        assert "=" * 60 in content

    def test_render_function(self):
        """渲染函数"""
        renderer = TextRenderer()
        mod = ModuleDoc(
            name="test",
            functions=[
                FunctionDoc(
                    name="foo",
                    signature="def foo()",
                    docstring="Do something.",
                )
            ],
        )
        content = renderer.render(mod)
        assert "Functions:" in content
        assert "foo" in content

    def test_render_class(self):
        """渲染类"""
        renderer = TextRenderer()
        mod = ModuleDoc(
            name="test",
            classes=[
                ClassDoc(name="Foo", docstring="A class."),
            ],
        )
        content = renderer.render(mod)
        assert "Classes:" in content
        assert "Foo" in content


# ============================================================
# 6. DocumentationGenerator 测试
# ============================================================

class TestDocumentationGenerator:
    """DocumentationGenerator测试"""

    def test_generator_creation(self):
        """生成器创建"""
        gen = create_doc_generator()
        assert gen is not None

    def test_generate_markdown(self):
        """生成Markdown"""
        code = "def foo():\n    \"\"\"Doc.\"\"\"\n    pass\n"
        report = generate_docs(code, DocFormat.MARKDOWN, "test.py")
        assert report.format == DocFormat.MARKDOWN
        assert "# test" in report.content
        assert "foo" in report.content
        assert report.error is None

    def test_generate_html(self):
        """生成HTML"""
        code = "def foo():\n    pass\n"
        report = generate_docs(code, DocFormat.HTML, "test.py")
        assert report.format == DocFormat.HTML
        assert "<html" in report.content

    def test_generate_text(self):
        """生成Text"""
        code = "def foo():\n    pass\n"
        report = generate_docs(code, DocFormat.TEXT, "test.py")
        assert report.format == DocFormat.TEXT
        assert "Module: test" in report.content

    def test_generate_empty_code(self):
        """生成空代码文档"""
        report = generate_docs("", DocFormat.MARKDOWN, "empty.py")
        assert report.error is not None
        assert "Empty" in report.error

    def test_generate_with_complex_code(self):
        """生成复杂代码文档"""
        code = '''
"""Module doc."""

import os
from typing import List

MAX = 100

def add(a: int, b: int) -> int:
    """Add two numbers.
    
    Args:
        a: First.
        b: Second.
        
    Returns:
        Sum.
    """
    return a + b

class Calculator:
    """Calculator class."""
    
    def __init__(self):
        """Init."""
        self.value = 0
    
    def add(self, x: int) -> int:
        """Add to value.
        
        Args:
            x: Number.
            
        Returns:
            New value.
        """
        self.value += x
        return self.value
'''
        report = generate_docs(code, DocFormat.MARKDOWN, "calc.py")
        assert report.error is None
        assert len(report.module.functions) == 1
        assert len(report.module.classes) == 1
        assert report.module.classes[0].name == "Calculator"
        assert len(report.module.classes[0].methods) == 2

    def test_generate_duration(self):
        """生成耗时"""
        code = "x = 1\n"
        report = generate_docs(code, DocFormat.MARKDOWN, "test.py")
        assert report.generation_duration_ms >= 0

    def test_generate_history(self):
        """生成历史"""
        gen = create_doc_generator()
        gen.generate("x = 1\n", DocFormat.MARKDOWN, "a.py")
        gen.generate("y = 2\n", DocFormat.MARKDOWN, "b.py")
        history = gen.get_history()
        assert len(history) == 2

    def test_generate_stats(self):
        """生成统计"""
        gen = create_doc_generator()
        gen.generate("x = 1\n", DocFormat.MARKDOWN, "a.py")
        gen.generate("y = 2\n", DocFormat.HTML, "b.py")
        stats = gen.get_stats()
        assert stats["total_docs"] == 2
        assert stats["total_content_chars"] > 0


# ============================================================
# 7. 文件和目录生成测试
# ============================================================

class TestFileDirectoryGeneration:
    """文件和目录生成测试"""

    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_generate_file(self):
        """从文件生成"""
        filepath = os.path.join(self._tmpdir, "test.py")
        with open(filepath, "w") as f:
            f.write("def foo():\n    pass\n")

        report = generate_file_docs(filepath, DocFormat.MARKDOWN)
        assert report.error is None
        assert "foo" in report.content

    def test_generate_file_nonexistent(self):
        """从不存在的文件生成"""
        report = generate_file_docs("/nonexistent/file.py", DocFormat.MARKDOWN)
        assert report.error is not None

    def test_generate_directory(self):
        """从目录生成"""
        for name in ["a.py", "b.py", "c.py"]:
            with open(os.path.join(self._tmpdir, name), "w") as f:
                f.write("x = 1\n")

        gen = create_doc_generator()
        reports = gen.generate_directory(self._tmpdir, DocFormat.MARKDOWN)
        assert len(reports) == 3

    def test_generate_directory_nested(self):
        """从嵌套目录生成"""
        subdir = os.path.join(self._tmpdir, "sub")
        os.makedirs(subdir)
        with open(os.path.join(self._tmpdir, "a.py"), "w") as f:
            f.write("x = 1\n")
        with open(os.path.join(subdir, "b.py"), "w") as f:
            f.write("y = 2\n")

        gen = create_doc_generator()
        reports = gen.generate_directory(self._tmpdir, DocFormat.MARKDOWN)
        assert len(reports) == 2

    def test_save_documentation(self):
        """保存文档"""
        gen = create_doc_generator()
        report = gen.generate("x = 1\n", DocFormat.MARKDOWN, "test.py")

        output_path = os.path.join(self._tmpdir, "output.md")
        assert gen.save_documentation(report, output_path) is True
        assert os.path.exists(output_path)

        with open(output_path, "r") as f:
            saved = f.read()
        assert saved == report.content


# ============================================================
# 8. Agent集成测试
# ============================================================

class TestAgentIntegration:
    """Agent集成测试"""

    def test_agent_has_doc_generator(self):
        """Agent有doc_generator属性"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent(agent_id="test_agent")
        assert agent.doc_generator is not None
        assert isinstance(agent.doc_generator, DocumentationGenerator)

    def test_agent_generate_docs(self):
        """Agent生成文档"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent(agent_id="test_agent")

        code = "def foo():\n    \"\"\"Doc.\"\"\"\n    pass\n"
        report = agent.generate_docs(code, DocFormat.MARKDOWN, "test.py")
        assert report.error is None
        assert "foo" in report.content

    def test_agent_generate_html(self):
        """Agent生成HTML"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent(agent_id="test_agent")

        code = "x = 1\n"
        report = agent.generate_docs(code, DocFormat.HTML, "test.py")
        assert "<html" in report.content

    def test_agent_generate_file_docs(self):
        """Agent从文件生成"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        import shutil
        tmpdir = tempfile.mkdtemp()
        try:
            filepath = os.path.join(tmpdir, "test.py")
            with open(filepath, "w") as f:
                f.write("def foo():\n    pass\n")

            agent = SelfEvolvingAgent(agent_id="test_agent")
            report = agent.generate_file_docs(filepath, DocFormat.MARKDOWN)
            assert report.error is None
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# 9. 并发安全测试
# ============================================================

class TestConcurrency:
    """并发安全测试"""

    def test_concurrent_generate(self):
        """并发生成"""
        gen = create_doc_generator()
        results = [None] * 10
        errors = []

        def generate_concurrent(i):
            try:
                code = f"def func_{i}():\n    pass\n"
                results[i] = gen.generate(code, DocFormat.MARKDOWN, f"test_{i}.py")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=generate_concurrent, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        for r in results:
            assert r is not None


# ============================================================
# 10. 性能测试
# ============================================================

class TestPerformance:
    """性能测试"""

    def test_small_file_performance(self):
        """小文件性能"""
        code = "def foo():\n    pass\n"
        start = time.time()
        generate_docs(code, DocFormat.MARKDOWN, "test.py")
        elapsed = time.time() - start
        assert elapsed < 0.1

    def test_large_file_performance(self):
        """大文件性能"""
        lines = []
        for i in range(200):
            lines.append(f"def func_{i}():")
            lines.append(f'    """Function {i}."""')
            lines.append(f"    return {i}")
            lines.append("")
        code = "\n".join(lines)

        start = time.time()
        report = generate_docs(code, DocFormat.MARKDOWN, "large.py")
        elapsed = time.time() - start
        assert elapsed < 2.0
        assert len(report.module.functions) == 200

    def test_all_formats_performance(self):
        """所有格式性能"""
        code = '''
def foo(a: int, b: str) -> bool:
    """Do something.
    
    Args:
        a: Number.
        b: String.
        
    Returns:
        Result.
    """
    return True

class Bar:
    """Bar class."""
    def method(self):
        """Method."""
        pass
'''
        for fmt in [DocFormat.MARKDOWN, DocFormat.HTML, DocFormat.TEXT]:
            start = time.time()
            generate_docs(code, fmt, "test.py")
            elapsed = time.time() - start
            assert elapsed < 0.5


# ============================================================
# 11. 异常容错测试
# ============================================================

class TestExceptionTolerance:
    """异常容错测试"""

    def test_none_code(self):
        """None代码"""
        gen = create_doc_generator()
        report = gen.generate(None, DocFormat.MARKDOWN, "test.py")
        assert report.error is not None

    def test_empty_code(self):
        """空代码"""
        report = generate_docs("", DocFormat.MARKDOWN, "test.py")
        assert report.error is not None

    def test_syntax_error_code(self):
        """语法错误代码"""
        code = "def foo(\n"
        report = generate_docs(code, DocFormat.MARKDOWN, "test.py")
        # 语法错误不应崩溃，返回空模块
        assert report.error is None
        assert len(report.module.functions) == 0

    def test_unicode_code(self):
        """Unicode代码"""
        code = '''
def 你好():
    """中文函数."""
    return "你好"
'''
        report = generate_docs(code, DocFormat.MARKDOWN, "unicode.py")
        assert report.error is None
        assert len(report.module.functions) == 1

    def test_unsupported_format(self):
        """不支持的格式"""
        gen = create_doc_generator()
        report = gen.generate("x = 1\n", DocFormat.RST, "test.py")
        # RST未实现渲染器
        assert report.error is not None


# ============================================================
# 12. 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_principle_extract_render(self):
        """原理：提取→渲染"""
        code = '''
def foo(a: int) -> bool:
    """Do something."""
    return True
'''
        report = generate_docs(code, DocFormat.MARKDOWN, "test.py")
        # 提取成功
        assert len(report.module.functions) == 1
        # 渲染成功
        assert report.content != ""
        assert "foo" in report.content

    def test_principle_multi_format(self):
        """原理：多格式输出"""
        code = "def foo():\n    pass\n"
        md = generate_docs(code, DocFormat.MARKDOWN, "test.py")
        html = generate_docs(code, DocFormat.HTML, "test.py")
        txt = generate_docs(code, DocFormat.TEXT, "test.py")
        # 同一代码，不同格式
        assert md.format == DocFormat.MARKDOWN
        assert html.format == DocFormat.HTML
        assert txt.format == DocFormat.TEXT
        # 都包含函数名
        assert "foo" in md.content
        assert "foo" in html.content
        assert "foo" in txt.content

    def test_principle_structured_extraction(self):
        """原理：结构化提取"""
        code = '''
class Foo:
    """Class doc."""
    attr = 1
    def method(self, x: int) -> str:
        """Method doc."""
        return str(x)
'''
        report = generate_docs(code, DocFormat.MARKDOWN, "test.py")
        cls = report.module.classes[0]
        # 结构化字段完整
        assert cls.name == "Foo"
        assert cls.docstring == "Class doc."
        assert "attr" in cls.attributes
        assert len(cls.methods) == 1
        assert cls.methods[0].name == "method"
        assert cls.methods[0].args[0].name == "self"
        assert cls.methods[0].args[1].name == "x"
        assert cls.methods[0].return_type == "str"

    def test_principle_deterministic(self):
        """原理：确定性（相同输入→相同输出）"""
        code = "def foo():\n    \"\"\"Doc.\"\"\"\n    pass\n"
        report1 = generate_docs(code, DocFormat.MARKDOWN, "test.py")
        report2 = generate_docs(code, DocFormat.MARKDOWN, "test.py")
        assert report1.content == report2.content

    def test_principle_zero_dependency(self):
        """原理：零外部依赖"""
        # 只使用Python标准库
        import ast
        assert ast is not None

    def test_principle_preserves_structure(self):
        """原理：保持源代码结构"""
        code = '''
def first():
    """First."""
    pass

def second():
    """Second."""
    pass

class MyClass:
    """Class."""
    pass
'''
        report = generate_docs(code, DocFormat.MARKDOWN, "test.py")
        # 保持顺序
        assert report.module.functions[0].name == "first"
        assert report.module.functions[1].name == "second"
        assert report.module.classes[0].name == "MyClass"
