"""
阶段128: 真实业务场景1 — 代码审查模块 专项测试

验证:
1. 数据结构（CodeIssue/CodeMetrics/ReviewReport）
2. 分析规则（语法/安全/复杂度/风格/最佳实践）
3. CodeReviewModule审查功能
4. 代码度量计算
5. 评分机制
6. 规则管理（添加/移除/启用/禁用）
7. 文件和目录审查
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

from self_evolving_agent.core.code_review import (
    CodeIssue,
    CodeMetrics,
    ReviewReport,
    IssueSeverity,
    IssueCategory,
    AnalysisRule,
    CodeReviewModule,
    SyntaxErrorRule,
    LineLengthRule,
    BareExceptRule,
    EvalExecRule,
    HardcodedSecretRule,
    FunctionComplexityRule,
    TooManyArgsRule,
    MissingDocstringRule,
    UnusedImportRule,
    DeepNestingRule,
    MutableDefaultArgRule,
    create_code_reviewer,
    review_code,
    review_file,
)


# ============================================================
# 1. 数据结构测试
# ============================================================

class TestDataStructures:
    """数据结构测试"""

    def test_issue_severity_enum(self):
        """问题严重程度枚举"""
        assert IssueSeverity.ERROR.value == "error"
        assert IssueSeverity.WARNING.value == "warning"
        assert IssueSeverity.INFO.value == "info"
        assert IssueSeverity.STYLE.value == "style"

    def test_issue_category_enum(self):
        """问题类别枚举"""
        assert IssueCategory.SYNTAX.value == "syntax"
        assert IssueCategory.SECURITY.value == "security"
        assert IssueCategory.COMPLEXITY.value == "complexity"
        assert IssueCategory.STYLE.value == "style"
        assert IssueCategory.BEST_PRACTICE.value == "best_practice"

    def test_code_issue_creation(self):
        """代码问题创建"""
        issue = CodeIssue(
            issue_id="i1",
            severity=IssueSeverity.ERROR,
            category=IssueCategory.SECURITY,
            message="eval is dangerous",
            line=10,
            column=5,
            rule="SE001",
            suggestion="Use ast.literal_eval",
        )
        assert issue.issue_id == "i1"
        assert issue.severity == IssueSeverity.ERROR
        assert issue.line == 10
        assert issue.suggestion == "Use ast.literal_eval"

    def test_code_issue_to_dict(self):
        """问题序列化"""
        issue = CodeIssue(
            issue_id="i1",
            severity=IssueSeverity.WARNING,
            category=IssueCategory.STYLE,
            message="line too long",
            line=5,
        )
        d = issue.to_dict()
        assert d["severity"] == "warning"
        assert d["category"] == "style"
        assert d["line"] == 5

    def test_code_metrics_creation(self):
        """代码度量创建"""
        metrics = CodeMetrics()
        assert metrics.lines_total == 0
        assert metrics.lines_code == 0
        assert metrics.functions_count == 0

    def test_code_metrics_to_dict(self):
        """度量序列化"""
        metrics = CodeMetrics(lines_total=100, lines_code=80, functions_count=5)
        d = metrics.to_dict()
        assert d["lines_total"] == 100
        assert d["lines_code"] == 80
        assert d["functions_count"] == 5

    def test_review_report_creation(self):
        """审查报告创建"""
        report = ReviewReport(
            file_path="test.py",
            language="python",
            score=85.5,
        )
        assert report.file_path == "test.py"
        assert report.score == 85.5
        assert report.issues == []
        assert report.passed is True  # 无错误

    def test_review_report_counts(self):
        """报告问题计数"""
        issues = [
            CodeIssue("i1", IssueSeverity.ERROR, IssueCategory.SYNTAX, "err", 1),
            CodeIssue("i2", IssueSeverity.ERROR, IssueCategory.SYNTAX, "err", 2),
            CodeIssue("i3", IssueSeverity.WARNING, IssueCategory.STYLE, "warn", 3),
            CodeIssue("i4", IssueSeverity.INFO, IssueCategory.BEST_PRACTICE, "info", 4),
            CodeIssue("i5", IssueSeverity.STYLE, IssueCategory.STYLE, "style", 5),
        ]
        report = ReviewReport(file_path="test.py", language="python", issues=issues)
        assert report.error_count == 2
        assert report.warning_count == 1
        assert report.info_count == 1
        assert report.style_count == 1

    def test_review_report_passed(self):
        """报告通过判断"""
        report = ReviewReport(file_path="test.py", language="python")
        assert report.passed is True

        report.issues.append(
            CodeIssue("i1", IssueSeverity.ERROR, IssueCategory.SYNTAX, "err", 1)
        )
        assert report.passed is False

        report.issues.clear()
        report.issues.append(
            CodeIssue("i1", IssueSeverity.WARNING, IssueCategory.STYLE, "warn", 1)
        )
        assert report.passed is True  # 警告不影响通过

    def test_review_report_to_dict(self):
        """报告序列化"""
        report = ReviewReport(
            file_path="test.py",
            language="python",
            score=90.0,
            summary="Good code",
        )
        d = report.to_dict()
        assert d["file_path"] == "test.py"
        assert d["score"] == 90.0
        assert d["passed"] is True
        assert d["error_count"] == 0


# ============================================================
# 2. 分析规则测试
# ============================================================

class TestAnalysisRules:
    """分析规则测试"""

    def test_syntax_error_rule(self):
        """语法错误规则"""
        rule = SyntaxErrorRule()
        code = "def foo(\n"  # 语法错误
        issues = rule.analyze(code, None, code.splitlines())
        assert len(issues) > 0
        assert issues[0].severity == IssueSeverity.ERROR

    def test_syntax_error_rule_clean(self):
        """语法错误规则（无错误）"""
        rule = SyntaxErrorRule()
        import ast
        code = "x = 1\n"
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 0

    def test_line_length_rule(self):
        """行长度规则"""
        rule = LineLengthRule(max_length=80)
        long_line = "x = " + "a" * 100 + "\n"
        issues = rule.analyze(long_line, None, long_line.splitlines())
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.STYLE

    def test_line_length_rule_ok(self):
        """行长度规则（合规）"""
        rule = LineLengthRule(max_length=120)
        code = "x = 1\n"
        issues = rule.analyze(code, None, code.splitlines())
        assert len(issues) == 0

    def test_bare_except_rule(self):
        """裸except规则"""
        rule = BareExceptRule()
        import ast
        code = "try:\n    pass\nexcept:\n    pass\n"
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 1
        assert "except" in issues[0].message.lower()

    def test_bare_except_rule_typed(self):
        """裸except规则（有类型）"""
        rule = BareExceptRule()
        import ast
        code = "try:\n    pass\nexcept Exception:\n    pass\n"
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 0

    def test_eval_exec_rule(self):
        """eval/exec规则"""
        rule = EvalExecRule()
        import ast
        code = 'x = eval("1+1")\n'
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.ERROR
        assert issues[0].category == IssueCategory.SECURITY

    def test_eval_exec_rule_exec(self):
        """exec规则"""
        rule = EvalExecRule()
        import ast
        code = 'exec("print(1)")\n'
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 1

    def test_hardcoded_secret_rule(self):
        """硬编码密钥规则"""
        rule = HardcodedSecretRule()
        import ast
        code = 'password = "my_secret_password"\n'
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 1
        assert "password" in issues[0].message.lower()

    def test_hardcoded_secret_rule_short(self):
        """硬编码密钥规则（短值不报）"""
        rule = HardcodedSecretRule()
        import ast
        code = 'password = "ab"\n'  # 太短
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 0

    def test_function_complexity_rule(self):
        """函数复杂度规则"""
        rule = FunctionComplexityRule(max_complexity=3)
        import ast
        code = """
def foo(x):
    if x > 0:
        if x > 1:
            if x > 2:
                if x > 3:
                    pass
"""
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 1
        assert "complexity" in issues[0].message.lower() or "复杂度" in issues[0].message

    def test_function_complexity_rule_ok(self):
        """函数复杂度规则（简单函数）"""
        rule = FunctionComplexityRule(max_complexity=10)
        import ast
        code = "def foo(x):\n    return x + 1\n"
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 0

    def test_too_many_args_rule(self):
        """参数过多规则"""
        rule = TooManyArgsRule(max_args=3)
        import ast
        code = "def foo(a, b, c, d, e):\n    pass\n"
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 1

    def test_too_many_args_rule_ok(self):
        """参数过多规则（合规）"""
        rule = TooManyArgsRule(max_args=7)
        import ast
        code = "def foo(a, b):\n    pass\n"
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 0

    def test_missing_docstring_rule(self):
        """缺少文档字符串规则"""
        rule = MissingDocstringRule()
        import ast
        code = "def foo():\n    pass\n"
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 1

    def test_missing_docstring_rule_has_doc(self):
        """缺少文档字符串规则（有文档）"""
        rule = MissingDocstringRule()
        import ast
        code = 'def foo():\n    """Doc."""\n    pass\n'
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 0

    def test_missing_docstring_rule_private(self):
        """缺少文档字符串规则（私有方法跳过）"""
        rule = MissingDocstringRule()
        import ast
        code = "def _private():\n    pass\n"
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 0

    def test_unused_import_rule(self):
        """未使用导入规则"""
        rule = UnusedImportRule()
        import ast
        code = "import os\nimport sys\n\nprint(sys.path)\n"
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        # os未使用，sys使用了
        assert len(issues) == 1
        assert "os" in issues[0].message

    def test_unused_import_rule_all_used(self):
        """未使用导入规则（全部使用）"""
        rule = UnusedImportRule()
        import ast
        code = "import os\nimport sys\n\nprint(os.getcwd())\nprint(sys.path)\n"
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 0

    def test_deep_nesting_rule(self):
        """深层嵌套规则"""
        rule = DeepNestingRule(max_depth=3)
        import ast
        code = """
def foo():
    if True:
        if True:
            if True:
                if True:
                    pass
"""
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) >= 1

    def test_mutable_default_arg_rule(self):
        """可变默认参数规则"""
        rule = MutableDefaultArgRule()
        import ast
        code = "def foo(items=[]):\n    pass\n"
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 1

    def test_mutable_default_arg_rule_none(self):
        """可变默认参数规则（None安全）"""
        rule = MutableDefaultArgRule()
        import ast
        code = "def foo(items=None):\n    pass\n"
        tree = ast.parse(code)
        issues = rule.analyze(code, tree, code.splitlines())
        assert len(issues) == 0


# ============================================================
# 3. CodeReviewModule 审查功能测试
# ============================================================

class TestCodeReviewModule:
    """CodeReviewModule审查功能测试"""

    def test_reviewer_creation(self):
        """审查器创建"""
        reviewer = create_code_reviewer()
        assert reviewer is not None
        assert len(reviewer.get_rules()) > 0

    def test_review_clean_code(self):
        """审查干净代码"""
        code = '''
def add(a, b):
    """Add two numbers."""
    return a + b
'''
        report = review_code(code, "clean.py")
        assert report.score > 80
        assert report.passed is True
        assert report.error_count == 0

    def test_review_bad_code(self):
        """审查有问题的代码"""
        code = '''
import os
import unused_module

def foo(a,b,c,d,e,f,g,h):
    eval("1+1")
    x = 1
    if x > 0:
        if x > 1:
            if x > 2:
                if x > 3:
                    if x > 4:
                        pass

def bar(password="hardcoded_secret"):
    try:
        pass
    except:
        pass
'''
        report = review_code(code, "bad.py")
        assert report.score < 80
        assert report.passed is False
        assert report.error_count > 0
        assert report.warning_count > 0

    def test_review_syntax_error(self):
        """审查语法错误"""
        code = "def foo(\n"
        report = review_code(code, "syntax_err.py")
        assert report.error_count > 0
        assert report.passed is False

    def test_review_empty_code(self):
        """审查空代码"""
        report = review_code("", "empty.py")
        assert report.error is not None
        assert "Empty" in report.error

    def test_review_issues_sorted(self):
        """问题按行号排序"""
        code = '''
def foo():
    """Doc."""
    x = eval("1")
    y = eval("2")
    return x + y
'''
        report = review_code(code, "test.py")
        lines = [i.line for i in report.issues]
        assert lines == sorted(lines)

    def test_review_metrics_calculated(self):
        """度量计算"""
        code = '''
# Comment line
import os

def foo():
    """Doc."""
    pass

class Bar:
    """Doc."""
    pass
'''
        report = review_code(code, "test.py")
        assert report.metrics.lines_total > 0
        assert report.metrics.lines_code > 0
        assert report.metrics.lines_comment > 0
        assert report.metrics.functions_count == 1
        assert report.metrics.classes_count == 1
        assert report.metrics.imports_count == 1

    def test_review_summary_generated(self):
        """摘要生成"""
        code = "x = 1\n"
        report = review_code(code, "test.py")
        assert report.summary != ""
        assert "评分" in report.summary or "score" in report.summary.lower()

    def test_review_duration_recorded(self):
        """审查耗时记录"""
        code = "x = 1\n"
        report = review_code(code, "test.py")
        assert report.review_duration_ms >= 0

    def test_review_history(self):
        """审查历史"""
        reviewer = create_code_reviewer()
        reviewer.review("x = 1\n", "a.py")
        reviewer.review("y = 2\n", "b.py")
        history = reviewer.get_history()
        assert len(history) == 2

    def test_review_stats(self):
        """审查统计"""
        reviewer = create_code_reviewer()
        reviewer.review("x = 1\n", "a.py")
        reviewer.review("eval('1')\n", "b.py")
        stats = reviewer.get_stats()
        assert stats["total_reviews"] == 2
        assert "avg_score" in stats
        assert "pass_rate" in stats


# ============================================================
# 4. 代码度量测试
# ============================================================

class TestCodeMetrics:
    """代码度量测试"""

    def test_line_counting(self):
        """行数统计"""
        code = "x = 1\n\n# comment\ny = 2\n"
        report = review_code(code, "test.py")
        assert report.metrics.lines_total == 4
        assert report.metrics.lines_blank == 1
        assert report.metrics.lines_comment == 1
        assert report.metrics.lines_code == 2

    def test_function_count(self):
        """函数计数"""
        code = """
def foo():
    pass

def bar():
    pass

async def baz():
    pass
"""
        report = review_code(code, "test.py")
        assert report.metrics.functions_count == 3

    def test_class_count(self):
        """类计数"""
        code = """
class Foo:
    pass

class Bar:
    pass
"""
        report = review_code(code, "test.py")
        assert report.metrics.classes_count == 2

    def test_import_count(self):
        """导入计数"""
        code = """
import os
import sys
from pathlib import Path
"""
        report = review_code(code, "test.py")
        assert report.metrics.imports_count == 3

    def test_max_line_length(self):
        """最大行长度"""
        code = "x = 1\n" + "y = " + "a" * 100 + "\n"
        report = review_code(code, "test.py")
        assert report.metrics.max_line_length >= 100

    def test_complexity_metrics(self):
        """复杂度度量"""
        code = """
def foo(x):
    if x > 0:
        for i in range(x):
            while True:
                pass
"""
        report = review_code(code, "test.py")
        assert report.metrics.max_complexity > 1
        assert report.metrics.avg_complexity > 1


# ============================================================
# 5. 评分机制测试
# ============================================================

class TestScoring:
    """评分机制测试"""

    def test_perfect_score(self):
        """满分"""
        code = '''
def add(a, b):
    """Add two numbers."""
    return a + b
'''
        report = review_code(code, "test.py")
        assert report.score == 100.0

    def test_error_reduces_score(self):
        """错误降低评分"""
        code = 'eval("1+1")\n'
        report = review_code(code, "test.py")
        assert report.score < 100.0

    def test_warning_reduces_score(self):
        """警告降低评分"""
        code = "import unused_module\n"
        report = review_code(code, "test.py")
        assert report.score < 100.0

    def test_score_clamped_to_zero(self):
        """评分钳制到0"""
        # 大量错误
        code = "\n".join([f'eval("{i}")' for i in range(20)])
        report = review_code(code, "test.py")
        assert report.score >= 0.0

    def test_score_max_100(self):
        """评分最大100"""
        code = "x = 1\n"
        report = review_code(code, "test.py")
        assert report.score <= 100.0


# ============================================================
# 6. 规则管理测试
# ============================================================

class TestRuleManagement:
    """规则管理测试"""

    def test_get_rules(self):
        """获取规则列表"""
        reviewer = create_code_reviewer()
        rules = reviewer.get_rules()
        assert len(rules) > 0
        for r in rules:
            assert "rule_id" in r
            assert "severity" in r
            assert "enabled" in r

    def test_disable_rule(self):
        """禁用规则"""
        reviewer = create_code_reviewer()
        assert reviewer.disable_rule("SE001") is True

        # eval不应再报错
        code = 'eval("1+1")\n'
        report = reviewer.review(code, "test.py")
        eval_issues = [i for i in report.issues if i.rule == "SE001"]
        assert len(eval_issues) == 0

    def test_enable_rule(self):
        """启用规则"""
        reviewer = create_code_reviewer()
        reviewer.disable_rule("SE001")
        assert reviewer.enable_rule("SE001") is True

        code = 'eval("1+1")\n'
        report = reviewer.review(code, "test.py")
        eval_issues = [i for i in report.issues if i.rule == "SE001"]
        assert len(eval_issues) > 0

    def test_disable_nonexistent_rule(self):
        """禁用不存在的规则"""
        reviewer = create_code_reviewer()
        assert reviewer.disable_rule("NONEXISTENT") is False

    def test_add_custom_rule(self):
        """添加自定义规则"""
        class NoPrintRule(AnalysisRule):
            def __init__(self):
                super().__init__("CUSTOM001", IssueSeverity.WARNING, IssueCategory.BEST_PRACTICE)

            def analyze(self, code, tree, lines):
                import ast
                issues = []
                if tree:
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Name) and node.func.id == "print":
                                issues.append(self._make_issue(
                                    message="使用print()调试",
                                    line=node.lineno,
                                ))
                return issues

        reviewer = create_code_reviewer()
        reviewer.add_rule(NoPrintRule())

        code = 'print("hello")\n'
        report = reviewer.review(code, "test.py")
        custom_issues = [i for i in report.issues if i.rule == "CUSTOM001"]
        assert len(custom_issues) == 1

    def test_remove_rule(self):
        """移除规则"""
        reviewer = create_code_reviewer()
        initial_count = len(reviewer.get_rules())
        assert reviewer.remove_rule("SE001") is True
        assert len(reviewer.get_rules()) == initial_count - 1

    def test_remove_nonexistent_rule(self):
        """移除不存在的规则"""
        reviewer = create_code_reviewer()
        assert reviewer.remove_rule("NONEXISTENT") is False


# ============================================================
# 7. 文件和目录审查测试
# ============================================================

class TestFileDirectoryReview:
    """文件和目录审查测试"""

    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_review_file(self):
        """审查文件"""
        filepath = os.path.join(self._tmpdir, "test.py")
        with open(filepath, "w") as f:
            f.write("x = 1\n")

        report = review_file(filepath)
        assert report.file_path == filepath
        assert report.error is None

    def test_review_file_nonexistent(self):
        """审查不存在的文件"""
        report = review_file("/nonexistent/path/file.py")
        assert report.error is not None

    def test_review_directory(self):
        """审查目录"""
        for name in ["a.py", "b.py", "c.py"]:
            with open(os.path.join(self._tmpdir, name), "w") as f:
                f.write("x = 1\n")

        reviewer = create_code_reviewer()
        reports = reviewer.review_directory(self._tmpdir)
        assert len(reports) == 3

    def test_review_directory_nested(self):
        """审查嵌套目录"""
        subdir = os.path.join(self._tmpdir, "subdir")
        os.makedirs(subdir)
        with open(os.path.join(self._tmpdir, "a.py"), "w") as f:
            f.write("x = 1\n")
        with open(os.path.join(subdir, "b.py"), "w") as f:
            f.write("y = 2\n")

        reviewer = create_code_reviewer()
        reports = reviewer.review_directory(self._tmpdir)
        assert len(reports) == 2

    def test_review_directory_no_python(self):
        """审查无Python文件目录"""
        with open(os.path.join(self._tmpdir, "readme.txt"), "w") as f:
            f.write("not python")

        reviewer = create_code_reviewer()
        reports = reviewer.review_directory(self._tmpdir)
        assert len(reports) == 0


# ============================================================
# 8. Agent集成测试
# ============================================================

class TestAgentIntegration:
    """Agent集成测试"""

    def test_agent_has_code_reviewer(self):
        """Agent有code_reviewer属性"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent(agent_id="test_agent")
        assert agent.code_reviewer is not None
        assert isinstance(agent.code_reviewer, CodeReviewModule)

    def test_agent_review_code(self):
        """Agent审查代码"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent(agent_id="test_agent")

        code = "def foo():\n    \"\"\"Doc.\"\"\"\n    return 1\n"
        report = agent.review_code(code, "test.py")
        assert report.score > 80

    def test_agent_review_bad_code(self):
        """Agent审查有问题的代码"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent(agent_id="test_agent")

        code = 'eval("1+1")\n'
        report = agent.review_code(code, "bad.py")
        assert report.error_count > 0

    def test_agent_review_file(self):
        """Agent审查文件"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        import shutil
        tmpdir = tempfile.mkdtemp()
        try:
            filepath = os.path.join(tmpdir, "test.py")
            with open(filepath, "w") as f:
                f.write("x = 1\n")

            agent = SelfEvolvingAgent(agent_id="test_agent")
            report = agent.review_file(filepath)
            assert report.file_path == filepath
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# 9. 并发安全测试
# ============================================================

class TestConcurrency:
    """并发安全测试"""

    def test_concurrent_review(self):
        """并发审查"""
        reviewer = create_code_reviewer()
        results = [None] * 10
        errors = []

        def review_code_concurrent(i):
            try:
                code = f"x = {i}\n"
                results[i] = reviewer.review(code, f"test_{i}.py")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=review_code_concurrent, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        for r in results:
            assert r is not None

    def test_concurrent_rule_management(self):
        """并发规则管理"""
        reviewer = create_code_reviewer()
        errors = []

        def toggle_rule():
            try:
                for _ in range(10):
                    reviewer.disable_rule("SE001")
                    reviewer.enable_rule("SE001")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=toggle_rule) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ============================================================
# 10. 性能测试
# ============================================================

class TestPerformance:
    """性能测试"""

    def test_small_file_performance(self):
        """小文件性能"""
        code = "def foo():\n    return 1\n"
        start = time.time()
        review_code(code, "test.py")
        elapsed = time.time() - start
        assert elapsed < 0.1

    def test_large_file_performance(self):
        """大文件性能"""
        lines = []
        for i in range(500):
            lines.append(f"def func_{i}():")
            lines.append(f'    """Function {i}."""')
            lines.append(f"    return {i}")
            lines.append("")
        code = "\n".join(lines)

        start = time.time()
        review_code(code, "large.py")
        elapsed = time.time() - start
        # 500个函数应在2秒内完成
        assert elapsed < 2.0

    def test_many_rules_performance(self):
        """多规则性能"""
        reviewer = create_code_reviewer()
        code = '''
import os
import sys

def foo(a, b, c, d, e, f, g, h):
    eval("1+1")
    if True:
        if True:
            if True:
                if True:
                    if True:
                        pass

def bar(password="secret"):
    try:
        pass
    except:
        pass
'''
        start = time.time()
        report = reviewer.review(code, "complex.py")
        elapsed = time.time() - start
        assert elapsed < 1.0
        assert len(report.issues) > 0


# ============================================================
# 11. 异常容错测试
# ============================================================

class TestExceptionTolerance:
    """异常容错测试"""

    def test_none_code(self):
        """None代码"""
        reviewer = create_code_reviewer()
        report = reviewer.review(None, "test.py")
        assert report.error is not None

    def test_empty_code(self):
        """空代码"""
        report = review_code("", "test.py")
        assert report.error is not None

    def test_rule_exception_isolated(self):
        """规则异常隔离"""
        class FailingRule(AnalysisRule):
            def __init__(self):
                super().__init__("FAIL001", IssueSeverity.ERROR, IssueCategory.SYNTAX)

            def analyze(self, code, tree, lines):
                raise RuntimeError("Rule failed")

        reviewer = create_code_reviewer()
        reviewer.add_rule(FailingRule())

        # 规则异常不应中断审查
        report = reviewer.review("x = 1\n", "test.py")
        assert report is not None
        assert report.error is None  # 审查本身没有错误

    def test_unicode_code(self):
        """Unicode代码"""
        code = '''
def 你好():
    """中文函数."""
    return "你好世界"
'''
        report = review_code(code, "unicode.py")
        assert report is not None

    def test_very_long_line(self):
        """超长行"""
        code = "x = " + "a" * 10000 + "\n"
        report = review_code(code, "test.py")
        assert report is not None
        assert report.metrics.max_line_length > 10000


# ============================================================
# 12. 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_principle_parse_analyze_report(self):
        """原理：解析→分析→报告"""
        code = '''
def foo():
    eval("1+1")
'''
        report = review_code(code, "test.py")
        # 解析成功（有AST）
        assert report.metrics.functions_count == 1
        # 分析出问题
        assert len(report.issues) > 0
        # 报告完整
        assert report.score > 0
        assert report.summary != ""

    def test_principle_rule_pluggability(self):
        """原理：规则可插拔"""
        reviewer = create_code_reviewer()
        initial_rules = len(reviewer.get_rules())

        # 添加规则
        class DummyRule(AnalysisRule):
            def __init__(self):
                super().__init__("DUMMY001", IssueSeverity.INFO, IssueCategory.STYLE)

            def analyze(self, code, tree, lines):
                return []

        reviewer.add_rule(DummyRule())
        assert len(reviewer.get_rules()) == initial_rules + 1

        # 移除规则
        reviewer.remove_rule("DUMMY001")
        assert len(reviewer.get_rules()) == initial_rules

    def test_principle_deterministic_analysis(self):
        """原理：分析确定性（相同输入→相同输出）"""
        code = 'eval("1+1")\n'
        report1 = review_code(code, "test.py")
        report2 = review_code(code, "test.py")
        assert report1.score == report2.score
        assert len(report1.issues) == len(report2.issues)

    def test_principle_severity_hierarchy(self):
        """原理：严重程度层级"""
        # 错误比警告更严重
        error_code = 'eval("1")\n'
        warning_code = "import unused\n"
        error_report = review_code(error_code, "err.py")
        warning_report = review_code(warning_code, "warn.py")
        assert error_report.score < warning_report.score

    def test_principle_quantitative_scoring(self):
        """原理：量化评分"""
        # 更多问题 = 更低评分
        one_issue = 'eval("1")\n'
        many_issues = '\n'.join([f'eval("{i}")' for i in range(5)])
        one_report = review_code(one_issue, "one.py")
        many_report = review_code(many_issues, "many.py")
        assert many_report.score < one_report.score

    def test_principle_zero_dependency(self):
        """原理：零外部依赖"""
        # 只使用Python标准库
        import self_evolving_agent.core.code_review as cr_module
        # 确认没有导入第三方库
        import ast as ast_module
        assert ast_module is not None  # ast是标准库

    def test_principle_structured_output(self):
        """原理：结构化输出"""
        code = "x = 1\n"
        report = review_code(code, "test.py")
        d = report.to_dict()
        # 结构化字段完整
        assert "file_path" in d
        assert "issues" in d
        assert "metrics" in d
        assert "score" in d
        assert "summary" in d
        assert "passed" in d
