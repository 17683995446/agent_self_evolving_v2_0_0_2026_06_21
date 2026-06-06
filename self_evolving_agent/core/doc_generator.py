"""
自驱永续进化Agent系统 — 接口文档自动生成
阶段22：接口文档自动生成

第一性原理：文档应与代码同步，手动维护文档容易过时，自动生成确保一致性

从代码中提取：
1. 接口类定义
2. 方法签名
3. 参数类型
4. 返回值类型
5. 文档字符串
"""

import inspect
import json
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime

from .interfaces import BaseModule, MessageType


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

    自动从代码中提取接口信息
    """

    def __init__(self):
        self._docs: Dict[str, InterfaceDoc] = {}

    def scan_module(self, module_class: Type[BaseModule]) -> InterfaceDoc:
        """
        扫描模块类，提取接口文档
        """
        doc = InterfaceDoc(
            name=module_class.__name__,
            module_path=f"{module_class.__module__}.{module_class.__name__}",
            description=module_class.__doc__ or "",
        )

        # 提取方法
        for name, method in inspect.getmembers(module_class, predicate=inspect.isfunction):
            if name.startswith('_'):
                continue

            method_doc = self._extract_method_doc(method, name)
            if method_doc:
                doc.methods.append(method_doc)

        # 提取消息类型（如果类有相关的类属性）
        doc.message_types = self._extract_message_types(module_class)

        self._docs[doc.name] = doc
        return doc

    def _extract_method_doc(self, method, name: str) -> Optional[MethodDoc]:
        """提取方法文档"""
        sig = inspect.signature(method)

        # 获取文档字符串
        docstring = method.__doc__ or ""

        # 解析参数
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

            params.append(ParameterDoc(
                name=param_name,
                type=param_type,
                default=param_default,
            ))

        # 解析返回类型
        return_type = ""
        if sig.return_annotation != inspect.Signature.empty:
            return_type = str(sig.return_annotation).replace("<class '", "").replace("'>", "")

        return MethodDoc(
            name=name,
            description=docstring.strip(),
            parameters=params,
            return_type=return_type,
        )

    def _extract_message_types(self, module_class: Type) -> List[str]:
        """提取模块处理的消息类型"""
        # 从handle_message方法中推断
        types = []
        if hasattr(module_class, 'handle_message'):
            source = inspect.getsource(module_class.handle_message)
            for msg_type in MessageType:
                if msg_type.name in source:
                    types.append(msg_type.name)
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
            lines.extend([
                "## 消息类型",
                "",
            ])
            for msg_type in doc.message_types:
                lines.append(f"- {msg_type}")
            lines.append("")

        if doc.methods:
            lines.extend([
                "## 方法",
                "",
            ])
            for method in doc.methods:
                lines.extend([
                    f"### {method.name}",
                    "",
                    method.description,
                    "",
                ])

                if method.parameters:
                    lines.extend([
                        "**参数**:",
                        "",
                        "| 名称 | 类型 | 默认值 | 描述 |",
                        "|------|------|--------|------|",
                    ])
                    for param in method.parameters:
                        default_str = str(param.default) if param.default is not None else "-"
                        lines.append(f"| {param.name} | {param.type} | {default_str} | {param.description} |")
                    lines.append("")

                if method.return_type:
                    lines.extend([
                        f"**返回**: `{method.return_type}`",
                        "",
                    ])

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
                        {
                            "name": p.name,
                            "type": p.type,
                            "default": str(p.default) if p.default is not None else None,
                        }
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

        lines.extend([
            "",
            "## 详细接口",
            "",
        ])

        for name in sorted(self._interface_generator.list_interfaces()):
            lines.append(self._interface_generator.generate_markdown(name))
            lines.append("---\n")

        return "\n".join(lines)

    def save_docs(self, output_dir: str, format: str = "markdown") -> None:
        """保存文档到文件"""
        import os
        os.makedirs(output_dir, exist_ok=True)

        if format == "markdown":
            # 保存系统文档
            system_doc = self.generate_system_doc()
            with open(os.path.join(output_dir, "system_api.md"), "w", encoding="utf-8") as f:
                f.write(system_doc)

            # 保存单个接口文档
            for name in self._interface_generator.list_interfaces():
                doc = self._interface_generator.generate_markdown(name)
                filename = f"{name.lower()}_api.md"
                with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                    f.write(doc)

        elif format == "json":
            docs = self._interface_generator.generate_all_docs("json")
            with open(os.path.join(output_dir, "api_docs.json"), "w", encoding="utf-8") as f:
                json.dump(docs, f, indent=2, ensure_ascii=False)
