"""
阶段129: 真实业务场景2 — 文档生成模块

第一性原理:
1. 文档 = 提取 + 格式化 + 渲染
2. 提取：使用Python ast模块解析源代码结构（零依赖）
3. 格式化：结构化模板填充
4. 渲染：多格式输出（Markdown/HTML/Text/RST）
5. LLM可增强自然语言描述（可选）

提供:
- FunctionDoc/ClassDoc/ModuleDoc: 文档数据结构
- DocumentationReport: 文档生成报告
- DocumentationGenerator: 文档生成器
- 多格式渲染器: Markdown/HTML/Text
"""

import ast
import os
import time
import threading
import inspect
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Type
from enum import Enum

# 向后兼容：阶段22的接口文档生成器依赖
from .interfaces import BaseModule, MessageType


# ============================================================
# 数据结构
# ============================================================

class DocFormat(Enum):
    """文档格式"""
    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"
    RST = "rst"


@dataclass
class ArgDoc:
    """参数文档"""
    name: str
    type_hint: str = ""
    default: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type_hint": self.type_hint,
            "default": self.default,
            "description": self.description,
        }


@dataclass
class FunctionDoc:
    """函数文档"""
    name: str
    signature: str                           # 完整签名
    docstring: str = ""                      # 文档字符串
    args: List[ArgDoc] = field(default_factory=list)
    returns: str = ""                        # 返回值描述
    return_type: str = ""                    # 返回值类型
    raises: List[str] = field(default_factory=list)  # 抛出异常
    line: int = 0
    end_line: int = 0
    is_async: bool = False
    is_private: bool = False
    is_method: bool = False
    decorators: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "signature": self.signature,
            "docstring": self.docstring,
            "args": [a.to_dict() for a in self.args],
            "returns": self.returns,
            "return_type": self.return_type,
            "raises": list(self.raises),
            "line": self.line,
            "is_async": self.is_async,
            "is_private": self.is_private,
            "is_method": self.is_method,
            "decorators": list(self.decorators),
        }


@dataclass
class ClassDoc:
    """类文档"""
    name: str
    docstring: str = ""
    methods: List[FunctionDoc] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    bases: List[str] = field(default_factory=list)
    line: int = 0
    is_private: bool = False
    decorators: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "docstring": self.docstring,
            "methods": [m.to_dict() for m in self.methods],
            "attributes": list(self.attributes),
            "bases": list(self.bases),
            "line": self.line,
            "is_private": self.is_private,
            "decorators": list(self.decorators),
        }


@dataclass
class ModuleDoc:
    """模块文档"""
    name: str
    file_path: str = ""
    docstring: str = ""                      # 模块级文档字符串
    functions: List[FunctionDoc] = field(default_factory=list)
    classes: List[ClassDoc] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    constants: List[Tuple[str, str]] = field(default_factory=list)  # (name, value_repr)
    line_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "file_path": self.file_path,
            "docstring": self.docstring,
            "functions": [f.to_dict() for f in self.functions],
            "classes": [c.to_dict() for c in self.classes],
            "imports": list(self.imports),
            "constants": [{"name": n, "value": v} for n, v in self.constants],
            "line_count": self.line_count,
        }


@dataclass
class DocumentationReport:
    """文档生成报告"""
    module: ModuleDoc
    format: DocFormat
    content: str                             # 生成的文档内容
    generated_at: float = field(default_factory=time.time)
    generation_duration_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": self.module.to_dict(),
            "format": self.format.value,
            "content_length": len(self.content),
            "generated_at": self.generated_at,
            "generation_duration_ms": self.generation_duration_ms,
            "error": self.error,
        }


# ============================================================
# 文档提取器
# ============================================================

class DocExtractor:
    """
    文档提取器

    第一性原理：
    - 从AST提取结构化信息
    - 保留源代码中的位置信息
    - 提取docstring、签名、类型注解
    """

    def extract(self, code: str, file_path: str = "<string>") -> ModuleDoc:
        """提取模块文档"""
        # 防御：空代码
        if not code:
            return ModuleDoc(name=self._module_name(file_path), file_path=file_path)

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return ModuleDoc(name=self._module_name(file_path), file_path=file_path)

        module_name = self._module_name(file_path)
        lines = code.splitlines()

        module_doc = ModuleDoc(
            name=module_name,
            file_path=file_path,
            docstring=ast.get_docstring(tree) or "",
            line_count=len(lines),
        )

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_doc = self._extract_function(node, is_method=False)
                module_doc.functions.append(func_doc)
            elif isinstance(node, ast.ClassDef):
                class_doc = self._extract_class(node)
                module_doc.classes.append(class_doc)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                module_doc.imports.extend(self._extract_imports(node))
            elif isinstance(node, ast.Assign):
                # 模块级常量
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        try:
                            value = ast.unparse(node.value)
                            module_doc.constants.append((target.id, value[:100]))
                        except Exception:
                            module_doc.constants.append((target.id, "<complex>"))

        return module_doc

    def _module_name(self, file_path: str) -> str:
        """从文件路径提取模块名"""
        if file_path == "<string>":
            return "<string>"
        basename = os.path.basename(file_path)
        return os.path.splitext(basename)[0]

    def _extract_function(
        self,
        node: ast.FunctionDef,
        is_method: bool = False,
    ) -> FunctionDoc:
        """提取函数文档"""
        # 签名
        try:
            signature = ast.unparse(node)
            # 只取签名行
            signature = signature.split(":")[0].split("\n")[0]
            if "def " in signature:
                signature = signature[signature.index("def "):]
        except Exception:
            signature = f"def {node.name}(...)"

        # 参数
        args: List[ArgDoc] = []
        for arg in node.args.args:
            arg_doc = ArgDoc(name=arg.arg)
            if arg.annotation:
                try:
                    arg_doc.type_hint = ast.unparse(arg.annotation)
                except Exception:
                    arg_doc.type_hint = ""
            args.append(arg_doc)

        # 默认值
        defaults = node.args.defaults
        if defaults:
            num_defaults = len(defaults)
            num_args = len(args)
            for i, default in enumerate(defaults):
                idx = num_args - num_defaults + i
                if idx < num_args:
                    try:
                        args[idx].default = ast.unparse(default)
                    except Exception:
                        args[idx].default = "<complex>"

        # 返回类型
        return_type = ""
        if node.returns:
            try:
                return_type = ast.unparse(node.returns)
            except Exception:
                return_type = ""

        # 装饰器
        decorators = []
        for dec in node.decorator_list:
            try:
                decorators.append(ast.unparse(dec))
            except Exception:
                decorators.append("<decorator>")

        # 解析docstring中的参数和返回值
        docstring = ast.get_docstring(node) or ""
        parsed_args, parsed_returns, raises = self._parse_docstring(docstring)

        # 合并解析结果
        for i, arg in enumerate(args):
            if i < len(parsed_args) and parsed_args[i].description:
                arg.description = parsed_args[i].description

        return FunctionDoc(
            name=node.name,
            signature=signature,
            docstring=docstring,
            args=args,
            returns=parsed_returns or "",
            return_type=return_type,
            raises=raises,
            line=node.lineno,
            end_line=getattr(node, 'end_lineno', node.lineno),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_private=node.name.startswith("_"),
            is_method=is_method,
            decorators=decorators,
        )

    def _extract_class(self, node: ast.ClassDef) -> ClassDoc:
        """提取类文档"""
        # 基类
        bases = []
        for base in node.bases:
            try:
                bases.append(ast.unparse(base))
            except Exception:
                bases.append("<base>")

        # 装饰器
        decorators = []
        for dec in node.decorator_list:
            try:
                decorators.append(ast.unparse(dec))
            except Exception:
                decorators.append("<decorator>")

        class_doc = ClassDoc(
            name=node.name,
            docstring=ast.get_docstring(node) or "",
            bases=bases,
            line=node.lineno,
            is_private=node.name.startswith("_"),
            decorators=decorators,
        )

        # 方法和属性
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_doc = self._extract_function(item, is_method=True)
                class_doc.methods.append(method_doc)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_doc.attributes.append(target.id)

        return class_doc

    def _extract_imports(self, node: ast.AST) -> List[str]:
        """提取导入"""
        imports = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if alias.asname:
                    name += f" as {alias.asname}"
                imports.append(f"import {name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                name = alias.name
                if alias.asname:
                    name += f" as {alias.asname}"
                imports.append(f"from {module} import {name}")
        return imports

    def _parse_docstring(self, docstring: str) -> Tuple[List[ArgDoc], str, List[str]]:
        """解析docstring中的参数、返回值、异常"""
        if not docstring:
            return [], "", []

        args: List[ArgDoc] = []
        returns = ""
        raises: List[str] = []

        lines = docstring.splitlines()
        current_section = None

        for line in lines:
            stripped = line.strip()
            lower = stripped.lower()

            if lower in ("args:", "arguments:", "parameters:", "params:"):
                current_section = "args"
                continue
            elif lower in ("returns:", "return:"):
                current_section = "returns"
                continue
            elif lower in ("raises:", "raise:", "exceptions:"):
                current_section = "raises"
                continue
            elif lower in ("yields:", "yield:"):
                current_section = "yields"
                continue

            if not stripped:
                continue

            if current_section == "args":
                # 格式: name (type): description 或 name: description
                if ":" in stripped:
                    parts = stripped.split(":", 1)
                    name_part = parts[0].strip()
                    desc = parts[1].strip() if len(parts) > 1 else ""

                    # 提取名称和类型
                    if "(" in name_part and ")" in name_part:
                        name = name_part[:name_part.index("(")].strip()
                        type_hint = name_part[name_part.index("(")+1:name_part.index(")")].strip()
                    else:
                        name = name_part
                        type_hint = ""

                    args.append(ArgDoc(name=name, type_hint=type_hint, description=desc))

            elif current_section == "returns":
                if returns:
                    returns += " " + stripped
                else:
                    returns = stripped

            elif current_section == "raises":
                if ":" in stripped:
                    parts = stripped.split(":", 1)
                    raises.append(parts[0].strip())

        return args, returns, raises


# ============================================================
# 文档渲染器
# ============================================================

class DocRenderer:
    """文档渲染器基类"""

    def render(self, module: ModuleDoc) -> str:
        """渲染模块文档"""
        raise NotImplementedError


class MarkdownRenderer(DocRenderer):
    """Markdown渲染器"""

    def render(self, module: ModuleDoc) -> str:
        parts: List[str] = []

        # 标题
        parts.append(f"# {module.name}")
        parts.append("")

        # 模块文档字符串
        if module.docstring:
            parts.append(module.docstring)
            parts.append("")

        # 文件信息
        if module.file_path and module.file_path != "<string>":
            parts.append(f"**文件**: `{module.file_path}`")
            parts.append(f"**行数**: {module.line_count}")
            parts.append("")

        # 导入
        if module.imports:
            parts.append("## 导入")
            parts.append("")
            parts.append("```python")
            for imp in module.imports:
                parts.append(imp)
            parts.append("```")
            parts.append("")

        # 常量
        if module.constants:
            parts.append("## 常量")
            parts.append("")
            for name, value in module.constants:
                parts.append(f"- `{name}` = `{value}`")
            parts.append("")

        # 类
        if module.classes:
            parts.append("## 类")
            parts.append("")
            for cls in module.classes:
                parts.append(self._render_class(cls))
                parts.append("")

        # 函数
        if module.functions:
            parts.append("## 函数")
            parts.append("")
            for func in module.functions:
                parts.append(self._render_function(func))
                parts.append("")

        return "\n".join(parts)

    def _render_class(self, cls: ClassDoc) -> str:
        parts: List[str] = []

        # 类标题
        prefix = "### "
        if cls.bases:
            bases_str = f"({', '.join(cls.bases)})"
        else:
            bases_str = ""
        parts.append(f"{prefix}class `{cls.name}`{bases_str}")
        parts.append("")

        # 文档字符串
        if cls.docstring:
            parts.append(cls.docstring)
            parts.append("")

        # 属性
        if cls.attributes:
            parts.append("**属性**:")
            parts.append("")
            for attr in cls.attributes:
                parts.append(f"- `{attr}`")
            parts.append("")

        # 方法
        if cls.methods:
            parts.append("**方法**:")
            parts.append("")
            for method in cls.methods:
                if not method.is_private or method.name.startswith("__"):
                    parts.append(self._render_function(method, level=4))
                    parts.append("")

        return "\n".join(parts)

    def _render_function(self, func: FunctionDoc, level: int = 4) -> str:
        parts: List[str] = []
        header = "#" * level

        # 函数标题
        async_prefix = "async " if func.is_async else ""
        parts.append(f"{header} {async_prefix}def `{func.name}`")
        parts.append("")

        # 签名
        parts.append("```python")
        parts.append(func.signature)
        parts.append("```")
        parts.append("")

        # 文档字符串
        if func.docstring:
            parts.append(func.docstring)
            parts.append("")

        # 参数
        if func.args:
            parts.append("**参数**:")
            parts.append("")
            parts.append("| 名称 | 类型 | 默认值 | 描述 |")
            parts.append("|------|------|--------|------|")
            for arg in func.args:
                default = arg.default or "-"
                type_hint = arg.type_hint or "-"
                desc = arg.description or "-"
                parts.append(f"| `{arg.name}` | `{type_hint}` | `{default}` | {desc} |")
            parts.append("")

        # 返回值
        if func.returns or func.return_type:
            parts.append("**返回值**:")
            parts.append("")
            if func.return_type:
                parts.append(f"- 类型: `{func.return_type}`")
            if func.returns:
                parts.append(f"- 描述: {func.returns}")
            parts.append("")

        # 异常
        if func.raises:
            parts.append("**抛出**:")
            parts.append("")
            for exc in func.raises:
                parts.append(f"- `{exc}`")
            parts.append("")

        return "\n".join(parts)


class HTMLRenderer(DocRenderer):
    """HTML渲染器"""

    def render(self, module: ModuleDoc) -> str:
        parts: List[str] = []
        parts.append("<!DOCTYPE html>")
        parts.append("<html lang='zh-CN'>")
        parts.append("<head>")
        parts.append("<meta charset='UTF-8'>")
        parts.append(f"<title>{module.name} - 文档</title>")
        parts.append("<style>")
        parts.append("body { font-family: sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }")
        parts.append("pre { background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }")
        parts.append("table { border-collapse: collapse; width: 100%; }")
        parts.append("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
        parts.append("th { background: #f2f2f2; }")
        parts.append("</style>")
        parts.append("</head>")
        parts.append("<body>")

        parts.append(f"<h1>{module.name}</h1>")

        if module.docstring:
            parts.append(f"<p>{module.docstring}</p>")

        if module.file_path and module.file_path != "<string>":
            parts.append(f"<p><strong>文件</strong>: <code>{module.file_path}</code></p>")
            parts.append(f"<p><strong>行数</strong>: {module.line_count}</p>")

        if module.imports:
            parts.append("<h2>导入</h2>")
            parts.append("<pre><code>")
            parts.append("\n".join(module.imports))
            parts.append("</code></pre>")

        if module.classes:
            parts.append("<h2>类</h2>")
            for cls in module.classes:
                parts.append(self._render_class_html(cls))

        if module.functions:
            parts.append("<h2>函数</h2>")
            for func in module.functions:
                parts.append(self._render_function_html(func))

        parts.append("</body>")
        parts.append("</html>")

        return "\n".join(parts)

    def _render_class_html(self, cls: ClassDoc) -> str:
        parts: List[str] = []
        bases = f"({', '.join(cls.bases)})" if cls.bases else ""
        parts.append(f"<h3>class {cls.name}{bases}</h3>")
        if cls.docstring:
            parts.append(f"<p>{cls.docstring}</p>")
        if cls.attributes:
            parts.append("<p><strong>属性</strong>:</p>")
            parts.append("<ul>")
            for attr in cls.attributes:
                parts.append(f"<li><code>{attr}</code></li>")
            parts.append("</ul>")
        if cls.methods:
            parts.append("<p><strong>方法</strong>:</p>")
            for method in cls.methods:
                parts.append(self._render_function_html(method))
        return "\n".join(parts)

    def _render_function_html(self, func: FunctionDoc) -> str:
        parts: List[str] = []
        async_prefix = "async " if func.is_async else ""
        parts.append(f"<h4>{async_prefix}def {func.name}</h4>")
        parts.append(f"<pre><code>{func.signature}</code></pre>")
        if func.docstring:
            parts.append(f"<p>{func.docstring}</p>")
        if func.args:
            parts.append("<table>")
            parts.append("<tr><th>名称</th><th>类型</th><th>默认值</th><th>描述</th></tr>")
            for arg in func.args:
                parts.append(
                    f"<tr><td><code>{arg.name}</code></td>"
                    f"<td><code>{arg.type_hint or '-'}</code></td>"
                    f"<td><code>{arg.default or '-'}</code></td>"
                    f"<td>{arg.description or '-'}</td></tr>"
                )
            parts.append("</table>")
        return "\n".join(parts)


class TextRenderer(DocRenderer):
    """纯文本渲染器"""

    def render(self, module: ModuleDoc) -> str:
        parts: List[str] = []
        parts.append(f"{'=' * 60}")
        parts.append(f"Module: {module.name}")
        parts.append(f"{'=' * 60}")
        parts.append("")

        if module.docstring:
            parts.append(module.docstring)
            parts.append("")

        if module.file_path and module.file_path != "<string>":
            parts.append(f"File: {module.file_path}")
            parts.append(f"Lines: {module.line_count}")
            parts.append("")

        if module.imports:
            parts.append("-" * 40)
            parts.append("Imports:")
            parts.append("-" * 40)
            for imp in module.imports:
                parts.append(f"  {imp}")
            parts.append("")

        if module.constants:
            parts.append("-" * 40)
            parts.append("Constants:")
            parts.append("-" * 40)
            for name, value in module.constants:
                parts.append(f"  {name} = {value}")
            parts.append("")

        if module.classes:
            parts.append("-" * 40)
            parts.append("Classes:")
            parts.append("-" * 40)
            for cls in module.classes:
                parts.append(f"  class {cls.name}")
                if cls.bases:
                    parts.append(f"    bases: {', '.join(cls.bases)}")
                if cls.docstring:
                    parts.append(f"    {cls.docstring[:100]}")
                if cls.attributes:
                    parts.append(f"    attributes: {', '.join(cls.attributes)}")
                for method in cls.methods:
                    parts.append(f"      def {method.name}(...)")
                parts.append("")

        if module.functions:
            parts.append("-" * 40)
            parts.append("Functions:")
            parts.append("-" * 40)
            for func in module.functions:
                parts.append(f"  def {func.name}(...)")
                if func.docstring:
                    parts.append(f"    {func.docstring[:100]}")
                parts.append("")

        return "\n".join(parts)


# ============================================================
# 文档生成器
# ============================================================

class DocumentationGenerator:
    """
    文档生成器

    第一性原理：
    1. 文档生成 = 提取 + 渲染
    2. 提取使用AST（零依赖）
    3. 渲染支持多格式
    4. LLM可增强描述（可选）
    5. 线程安全
    """

    RENDERERS: Dict[DocFormat, DocRenderer] = {
        DocFormat.MARKDOWN: MarkdownRenderer(),
        DocFormat.HTML: HTMLRenderer(),
        DocFormat.TEXT: TextRenderer(),
    }

    def __init__(self, llm_coordinator=None):
        self._llm_coordinator = llm_coordinator
        self._extractor = DocExtractor()
        self._lock = threading.RLock()
        self._history: List[DocumentationReport] = []
        self._max_history = 1000

    def generate(
        self,
        code: str,
        format: DocFormat = DocFormat.MARKDOWN,
        file_path: str = "<string>",
    ) -> DocumentationReport:
        """
        生成文档

        第一性原理：
        - 提取 → 渲染
        - 每个步骤独立
        """
        start = time.time()

        # 防御：空代码
        if not code:
            return DocumentationReport(
                module=ModuleDoc(name="empty", file_path=file_path),
                format=format,
                content="",
                error="Empty code",
                generation_duration_ms=0.0,
            )

        # 提取
        module_doc = self._extractor.extract(code, file_path)

        # 渲染
        renderer = self.RENDERERS.get(format)
        if renderer is None:
            return DocumentationReport(
                module=module_doc,
                format=format,
                content="",
                error=f"Unsupported format: {format}",
                generation_duration_ms=(time.time() - start) * 1000,
            )

        content = renderer.render(module_doc)

        duration = (time.time() - start) * 1000

        report = DocumentationReport(
            module=module_doc,
            format=format,
            content=content,
            generation_duration_ms=duration,
        )

        with self._lock:
            self._history.append(report)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        return report

    def generate_file(
        self,
        file_path: str,
        format: DocFormat = DocFormat.MARKDOWN,
    ) -> DocumentationReport:
        """从文件生成文档"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            return self.generate(code, format, file_path)
        except IOError as e:
            return DocumentationReport(
                module=ModuleDoc(name="error", file_path=file_path),
                format=format,
                content="",
                error=f"无法读取文件: {e}",
            )

    def generate_directory(
        self,
        dir_path: str,
        format: DocFormat = DocFormat.MARKDOWN,
        pattern: str = "*.py",
    ) -> List[DocumentationReport]:
        """从目录生成文档"""
        import glob
        reports = []
        for filepath in glob.glob(os.path.join(dir_path, "**", pattern), recursive=True):
            reports.append(self.generate_file(filepath, format))
        return reports

    def save_documentation(
        self,
        report: DocumentationReport,
        output_path: str,
    ) -> bool:
        """保存文档到文件"""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report.content)
            return True
        except IOError:
            return False

    def get_history(self, limit: int = 100) -> List[DocumentationReport]:
        """获取生成历史"""
        with self._lock:
            return list(self._history[-limit:])

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total = len(self._history)
            if total == 0:
                return {"total_docs": 0}
            total_content = sum(len(r.content) for r in self._history)
            avg_duration = sum(r.generation_duration_ms for r in self._history) / total
            return {
                "total_docs": total,
                "total_content_chars": total_content,
                "avg_duration_ms": round(avg_duration, 2),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_doc_generator(llm_coordinator=None) -> DocumentationGenerator:
    """创建文档生成器"""
    return DocumentationGenerator(llm_coordinator=llm_coordinator)


def generate_docs(
    code: str,
    format: DocFormat = DocFormat.MARKDOWN,
    file_path: str = "<string>",
) -> DocumentationReport:
    """快速生成文档"""
    generator = create_doc_generator()
    return generator.generate(code, format, file_path)


def generate_file_docs(
    file_path: str,
    format: DocFormat = DocFormat.MARKDOWN,
) -> DocumentationReport:
    """快速从文件生成文档"""
    generator = create_doc_generator()
    return generator.generate_file(file_path, format)


# ============================================================
# 向后兼容：阶段22 接口文档生成器（运行时反射）
# ============================================================
# 以下类保留用于 mlops 等子包的运行时接口文档生成，
# 与阶段129的源代码AST文档生成器互补。

@dataclass
class ParameterDoc:
    """参数文档"""
    name: str
    type: str
    default: Any = None
    description: str = ""


@dataclass
class MethodDoc:
    """方法文档"""
    name: str
    description: str = ""
    parameters: List[ParameterDoc] = field(default_factory=list)
    return_type: str = ""
    return_description: str = ""


@dataclass
class InterfaceDoc:
    """接口文档"""
    name: str
    module_path: str = ""
    description: str = ""
    version: str = "1.0.0"
    methods: List[MethodDoc] = field(default_factory=list)
    message_types: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


class InterfaceDocGenerator:
    """
    接口文档生成器

    自动从代码中提取接口信息（运行时反射）
    """

    def __init__(self):
        self._docs: Dict[str, InterfaceDoc] = {}

    def scan_module(self, module_class: Type[BaseModule]) -> InterfaceDoc:
        """扫描模块类，提取接口文档"""
        doc = InterfaceDoc(
            name=module_class.__name__,
            module_path=f"{module_class.__module__}.{module_class.__name__}",
            description=module_class.__doc__ or "",
        )

        for name, method in inspect.getmembers(module_class, predicate=inspect.isfunction):
            if name.startswith('_'):
                continue
            method_doc = self._extract_method_doc(method, name)
            if method_doc:
                doc.methods.append(method_doc)

        doc.message_types = self._extract_message_types(module_class)
        self._docs[doc.name] = doc
        return doc

    def _extract_method_doc(self, method, name: str) -> Optional[MethodDoc]:
        """提取方法文档"""
        sig = inspect.signature(method)
        docstring = method.__doc__ or ""

        params = []
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            param_type = "Any"
            if param.annotation != inspect.Parameter.empty:
                param_type = str(param.annotation).replace("<class '", "").replace("'>", "")
            param_default = None
            if param.default != inspect.Parameter.empty:
                param_default = param.default
            params.append(ParameterDoc(name=param_name, type=param_type, default=param_default))

        return_type = ""
        if sig.return_annotation != inspect.Signature.empty:
            return_type = str(sig.return_annotation).replace("<class '", "").replace("'>", "")

        return MethodDoc(name=name, description=docstring.strip(), parameters=params, return_type=return_type)

    def _extract_message_types(self, module_class: Type) -> List[str]:
        """提取模块处理的消息类型"""
        types = []
        if hasattr(module_class, 'handle_message'):
            try:
                source = inspect.getsource(module_class.handle_message)
                for msg_type in MessageType:
                    if msg_type.name in source:
                        types.append(msg_type.name)
            except (OSError, TypeError):
                pass
        return types

    def generate_markdown(self, interface_name: str) -> str:
        """生成Markdown格式文档"""
        doc = self._docs.get(interface_name)
        if not doc:
            return f"# Interface Not Found: {interface_name}"

        lines = [
            f"# {doc.name}",
            "",
            f"**模块路径**: `{doc.module_path}`",
            "",
            f"**版本**: {doc.version}",
            "",
            f"**描述**: {doc.description}",
            "",
        ]

        if doc.message_types:
            lines.extend(["## 消息类型", ""])
            for msg_type in doc.message_types:
                lines.append(f"- {msg_type}")
            lines.append("")

        if doc.methods:
            lines.extend(["## 方法", ""])
            for method in doc.methods:
                lines.extend([f"### {method.name}", "", method.description, ""])
                if method.parameters:
                    lines.extend([
                        "**参数**:", "",
                        "| 名称 | 类型 | 默认值 | 描述 |",
                        "|------|------|--------|------|",
                    ])
                    for param in method.parameters:
                        default_str = str(param.default) if param.default is not None else "-"
                        lines.append(f"| {param.name} | {param.type} | {default_str} | {param.description} |")
                    lines.append("")
                if method.return_type:
                    lines.extend([f"**返回**: `{method.return_type}`", ""])

        return "\n".join(lines)

    def generate_json(self, interface_name: str) -> str:
        """生成JSON格式文档"""
        doc = self._docs.get(interface_name)
        if not doc:
            return json.dumps({"error": f"Interface {interface_name} not found"}, indent=2)

        data = {
            "name": doc.name,
            "module_path": doc.module_path,
            "version": doc.version,
            "description": doc.description,
            "message_types": doc.message_types,
            "methods": [
                {
                    "name": m.name,
                    "description": m.description,
                    "parameters": [
                        {"name": p.name, "type": p.type, "default": str(p.default) if p.default is not None else None}
                        for p in m.parameters
                    ],
                    "return_type": m.return_type,
                }
                for m in doc.methods
            ],
            "generated_at": datetime.now().isoformat(),
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def generate_all_docs(self, format: str = "markdown") -> Dict[str, str]:
        """生成所有接口文档"""
        result = {}
        for name in self._docs:
            if format == "markdown":
                result[name] = self.generate_markdown(name)
            elif format == "json":
                result[name] = self.generate_json(name)
        return result

    def list_interfaces(self) -> List[str]:
        """列出所有已扫描的接口"""
        return list(self._docs.keys())

    def get_doc(self, interface_name: str) -> Optional[InterfaceDoc]:
        """获取接口文档"""
        return self._docs.get(interface_name)


class SystemDocGenerator:
    """
    系统文档生成器

    生成整个系统的接口文档
    """

    def __init__(self):
        self._interface_generator = InterfaceDocGenerator()

    def scan_all_modules(self, module_classes: List[Type[BaseModule]]) -> None:
        """扫描所有模块"""
        for module_class in module_classes:
            self._interface_generator.scan_module(module_class)

    def generate_system_doc(self) -> str:
        """生成系统级文档"""
        lines = [
            "# 自驱永续进化Agent系统 — 接口文档",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 模块列表",
            "",
        ]

        for name in sorted(self._interface_generator.list_interfaces()):
            doc = self._interface_generator.get_doc(name)
            lines.append(f"- **{name}**: {doc.description[:50]}...")

        lines.extend(["", "## 详细接口", ""])

        for name in sorted(self._interface_generator.list_interfaces()):
            lines.append(self._interface_generator.generate_markdown(name))
            lines.append("---\n")

        return "\n".join(lines)

    def save_docs(self, output_dir: str, format: str = "markdown") -> None:
        """保存文档到文件"""
        os.makedirs(output_dir, exist_ok=True)

        if format == "markdown":
            system_doc = self.generate_system_doc()
            with open(os.path.join(output_dir, "system_api.md"), "w", encoding="utf-8") as f:
                f.write(system_doc)
            for name in self._interface_generator.list_interfaces():
                doc = self._interface_generator.generate_markdown(name)
                filename = f"{name.lower()}_api.md"
                with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                    f.write(doc)
        elif format == "json":
            docs = self._interface_generator.generate_all_docs("json")
            with open(os.path.join(output_dir, "api_docs.json"), "w", encoding="utf-8") as f:
                json.dump(docs, f, indent=2, ensure_ascii=False)
