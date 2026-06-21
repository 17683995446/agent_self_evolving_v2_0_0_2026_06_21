"""代码审查与文档生成Mixin — 阶段149从agent.py拆分"""

from typing import List

from ..core.code_review import ReviewReport
from ..core.doc_generator import DocumentationReport, DocFormat


class CodeDocsMixin:
    """代码审查 + 文档生成接口（阶段128-129）"""

    def review_code(self, code: str, file_path: str = "<string>") -> ReviewReport:
        """
        审查代码（阶段128新增）

        Args:
            code: 代码字符串
            file_path: 文件路径标识（用于报告）

        Returns:
            ReviewReport: 审查报告
        """
        return self._code_reviewer.review(code, file_path)

    def review_file(self, file_path: str) -> ReviewReport:
        """审查文件（阶段128新增）"""
        return self._code_reviewer.review_file(file_path)

    def review_directory(self, dir_path: str) -> List[ReviewReport]:
        """审查目录（阶段128新增）"""
        return self._code_reviewer.review_directory(dir_path)

    def generate_docs(
        self,
        code: str,
        format: DocFormat = DocFormat.MARKDOWN,
        file_path: str = "<string>",
    ) -> DocumentationReport:
        """
        生成文档（阶段129新增）

        Args:
            code: 源代码字符串
            format: 文档格式
            file_path: 文件路径标识

        Returns:
            DocumentationReport: 文档生成报告
        """
        return self._doc_generator.generate(code, format, file_path)

    def generate_file_docs(
        self,
        file_path: str,
        format: DocFormat = DocFormat.MARKDOWN,
    ) -> DocumentationReport:
        """从文件生成文档（阶段129新增）"""
        return self._doc_generator.generate_file(file_path, format)

    def generate_directory_docs(
        self,
        dir_path: str,
        format: DocFormat = DocFormat.MARKDOWN,
    ) -> List[DocumentationReport]:
        """从目录生成文档（阶段129新增）"""
        return self._doc_generator.generate_directory(dir_path, format)
