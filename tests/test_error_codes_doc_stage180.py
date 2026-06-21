"""
阶段180: 生成 docs/error_codes.md 静态文档验证

验证:
1. docs/error_codes.md 文件存在
2. 文档包含错误码表格
3. 文档包含场景映射表
4. 文档包含分类和严重级别说明
5. README 引用的链接不再404
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestErrorCodesDocExists:
    """docs/error_codes.md 文件存在性验证"""

    def test_doc_file_exists(self):
        """docs/error_codes.md 文件存在"""
        doc_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs", "error_codes.md"
        )
        assert os.path.exists(doc_path), "docs/error_codes.md 应存在"

    def test_doc_file_not_empty(self):
        """文档非空"""
        doc_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs", "error_codes.md"
        )
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 100, "文档应有实质内容"


class TestDocContent:
    """文档内容验证"""

    @property
    def doc_path(self):
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs", "error_codes.md"
        )

    @property
    def doc_content(self):
        with open(self.doc_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_has_title(self):
        """文档有标题"""
        assert "# 错误码参考文档" in self.doc_content

    def test_has_error_code_table(self):
        """文档包含错误码表格"""
        assert "| 错误码 |" in self.doc_content
        assert "CFG_001" in self.doc_content
        assert "VAL_002" in self.doc_content
        assert "SYS_001" in self.doc_content

    def test_has_scenario_mapping(self):
        """文档包含场景映射表"""
        assert "错误场景映射" in self.doc_content
        assert "missing_field" in self.doc_content
        assert "not_found" in self.doc_content
        assert "unknown" in self.doc_content

    def test_has_category_description(self):
        """文档包含分类说明"""
        assert "错误分类" in self.doc_content
        assert "SYS" in self.doc_content
        assert "VAL" in self.doc_content
        assert "SEC" in self.doc_content

    def test_has_severity_description(self):
        """文档包含严重级别说明"""
        assert "严重级别" in self.doc_content
        assert "error" in self.doc_content
        assert "critical" in self.doc_content
        assert "warning" in self.doc_content

    def test_has_response_format_example(self):
        """文档包含错误响应格式示例"""
        assert "error_code" in self.doc_content
        assert "suggested_action" in self.doc_content
        assert "recoverable" in self.doc_content

    def test_has_http_status_mapping(self):
        """文档包含HTTP状态码映射"""
        assert "HTTP状态码" in self.doc_content or "HTTP" in self.doc_content

    def test_covers_all_error_codes(self):
        """文档覆盖所有已注册的错误码"""
        from self_evolving_agent.core.error_codes import get_error_registry
        registry = get_error_registry()
        for code in registry._codes.values():
            assert code.code in self.doc_content, \
                f"文档应包含错误码: {code.code}"


class TestReadmeReferenceValid:
    """README 引用验证"""

    def test_readme_references_doc(self):
        """README 引用 docs/error_codes.md"""
        readme_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "README.md"
        )
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        # README 应引用 error_codes.md
        assert "error_codes.md" in content or "错误码" in content

    def test_referenced_doc_exists(self):
        """README 引用的文档实际存在"""
        readme_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "README.md"
        )
        docs_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs"
        )
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        # 检查 README 中引用的 docs/*.md 都存在
        import re
        refs = re.findall(r'docs/(\w+\.md)', content)
        for ref in refs:
            ref_path = os.path.join(docs_dir, ref)
            assert os.path.exists(ref_path), \
                f"README引用的文档应存在: docs/{ref}"


class TestDocGenerationConsistency:
    """文档与代码一致性验证"""

    def test_doc_matches_generate_error_docs(self):
        """文档内容与 generate_error_docs() 输出一致"""
        from self_evolving_agent.core.error_response import generate_error_docs
        generated = generate_error_docs()
        doc_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs", "error_codes.md"
        )
        with open(doc_path, "r", encoding="utf-8") as f:
            static_doc = f.read()
        # 静态文档应包含动态生成的错误码表格内容
        # 检查几个关键错误码都在
        for code in ["CFG_001", "VAL_002", "SYS_001", "SEC_001", "RES_001"]:
            assert code in static_doc
            assert code in generated


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
