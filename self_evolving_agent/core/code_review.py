"""
阶段128: 真实业务场景1 — 代码审查模块

第一性原理:
1. 代码审查 = 解析 + 分析 + 报告
2. 解析：使用Python ast模块（零依赖）
3. 分析：基于规则的静态分析（确定性）+ LLM增强（语义性，可选）
4. 报告：结构化输出，可量化、可追溯

提供:
- CodeIssue: 代码问题
- ReviewReport: 审查报告
- CodeMetrics: 代码度量
- CodeReviewModule: 代码审查模块
- 分析规则: 语法、安全、复杂度、风格、最佳实践
"""

import ast
import os
import time
import threading
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum


# ============================================================
# 数据结构
# ============================================================

class IssueSeverity(Enum):
    """问题严重程度"""
    ERROR = "error"          # 错误（必须修复）
    WARNING = "warning"      # 警告（建议修复）
    INFO = "info"            # 信息（可选改进）
    STYLE = "style"          # 风格（格式问题）


class IssueCategory(Enum):
    """问题类别"""
    SYNTAX = "syntax"                  # 语法错误
    SECURITY = "security"              # 安全漏洞
    COMPLEXITY = "complexity"          # 复杂度
    STYLE = "style"                    # 代码风格
    BEST_PRACTICE = "best_practice"    # 最佳实践
    PERFORMANCE = "performance"        # 性能问题
    MAINTAINABILITY = "maintainability"  # 可维护性


@dataclass
class CodeIssue:
    """代码问题"""
    issue_id: str
    severity: IssueSeverity
    category: IssueCategory
    message: str
    line: int                                # 行号（1-based）
    column: int = 0                          # 列号（0-based）
    rule: str = ""                           # 规则名称
    suggestion: str = ""                     # 修复建议

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "rule": self.rule,
            "suggestion": self.suggestion,
        }


@dataclass
class CodeMetrics:
    """代码度量"""
    lines_total: int = 0
    lines_code: int = 0
    lines_comment: int = 0
    lines_blank: int = 0
    functions_count: int = 0
    classes_count: int = 0
    imports_count: int = 0
    max_complexity: int = 0
    avg_complexity: float = 0.0
    max_line_length: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lines_total": self.lines_total,
            "lines_code": self.lines_code,
            "lines_comment": self.lines_comment,
            "lines_blank": self.lines_blank,
            "functions_count": self.functions_count,
            "classes_count": self.classes_count,
            "imports_count": self.imports_count,
            "max_complexity": self.max_complexity,
            "avg_complexity": self.avg_complexity,
            "max_line_length": self.max_line_length,
        }


@dataclass
class ReviewReport:
    """审查报告"""
    file_path: str
    language: str
    issues: List[CodeIssue] = field(default_factory=list)
    metrics: CodeMetrics = field(default_factory=CodeMetrics)
    score: float = 0.0                       # 质量评分 (0-100)
    summary: str = ""
    reviewed_at: float = field(default_factory=time.time)
    review_duration_ms: float = 0.0
    error: Optional[str] = None              # 审查过程中的错误

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.INFO)

    @property
    def style_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.STYLE)

    @property
    def passed(self) -> bool:
        """无错误时通过"""
        return self.error_count == 0 and self.error is None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "language": self.language,
            "issues": [i.to_dict() for i in self.issues],
            "metrics": self.metrics.to_dict(),
            "score": self.score,
            "summary": self.summary,
            "reviewed_at": self.reviewed_at,
            "review_duration_ms": self.review_duration_ms,
            "error": self.error,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "style_count": self.style_count,
            "passed": self.passed,
        }


# ============================================================
# 分析规则
# ============================================================

class AnalysisRule:
    """
    分析规则基类

    第一性原理：
    - 每条规则关注一个特定问题
    - 规则是确定性的（相同输入→相同输出）
    - 规则可独立启用/禁用
    """

    def __init__(self, rule_id: str, severity: IssueSeverity, category: IssueCategory):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.enabled = True

    def analyze(
        self,
        code: str,
        tree: Optional[ast.AST],
        lines: List[str],
    ) -> List[CodeIssue]:
        """分析代码，返回问题列表"""
        raise NotImplementedError

    def _make_issue(
        self,
        message: str,
        line: int,
        column: int = 0,
        suggestion: str = "",
    ) -> CodeIssue:
        return CodeIssue(
            issue_id=f"{self.rule_id}_{line}_{column}_{hashlib.md5(message.encode()).hexdigest()[:8]}",
            severity=self.severity,
            category=self.category,
            message=message,
            line=line,
            column=column,
            rule=self.rule_id,
            suggestion=suggestion,
        )


class SyntaxErrorRule(AnalysisRule):
    """语法错误检查"""

    def __init__(self):
        super().__init__("SY001", IssueSeverity.ERROR, IssueCategory.SYNTAX)

    def analyze(self, code, tree, lines):
        issues = []
        if tree is None:
            # 尝试解析获取错误位置
            try:
                ast.parse(code)
            except SyntaxError as e:
                issues.append(self._make_issue(
                    message=f"语法错误: {e.msg}",
                    line=e.lineno or 1,
                    column=(e.offset or 1) - 1,
                    suggestion="修复语法错误后重试",
                ))
        return issues


class LineLengthRule(AnalysisRule):
    """行长度检查"""

    def __init__(self, max_length: int = 120):
        super().__init__("ST001", IssueSeverity.STYLE, IssueCategory.STYLE)
        self.max_length = max_length

    def analyze(self, code, tree, lines):
        issues = []
        for i, line in enumerate(lines, 1):
            length = len(line.rstrip("\n\r"))
            if length > self.max_length:
                issues.append(self._make_issue(
                    message=f"行过长 ({length} > {self.max_length} 字符)",
                    line=i,
                    suggestion=f"缩短行长度至 {self.max_length} 字符以内",
                ))
        return issues


class BareExceptRule(AnalysisRule):
    """裸except检查"""

    def __init__(self):
        super().__init__("BP001", IssueSeverity.WARNING, IssueCategory.BEST_PRACTICE)

    def analyze(self, code, tree, lines):
        issues = []
        if tree is None:
            return issues
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append(self._make_issue(
                        message="裸except捕获所有异常，包括SystemExit和KeyboardInterrupt",
                        line=node.lineno,
                        suggestion="使用 `except Exception:` 替代裸except",
                    ))
        return issues


class EvalExecRule(AnalysisRule):
    """eval/exec安全检查"""

    def __init__(self):
        super().__init__("SE001", IssueSeverity.ERROR, IssueCategory.SECURITY)

    def analyze(self, code, tree, lines):
        issues = []
        if tree is None:
            return issues
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in ("eval", "exec", "compile"):
                    issues.append(self._make_issue(
                        message=f"使用 {func_name}() 存在安全风险",
                        line=node.lineno,
                        suggestion=f"避免使用 {func_name}()，考虑更安全的替代方案",
                    ))
        return issues


class HardcodedSecretRule(AnalysisRule):
    """硬编码密钥检查"""

    SECRET_PATTERNS = [
        "password", "passwd", "pwd", "secret", "api_key", "apikey",
        "access_key", "private_key", "token", "credential",
    ]

    def __init__(self):
        super().__init__("SE002", IssueSeverity.WARNING, IssueCategory.SECURITY)

    def analyze(self, code, tree, lines):
        issues = []
        if tree is None:
            return issues
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id.lower()
                        if any(p in var_name for p in self.SECRET_PATTERNS):
                            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                if len(node.value.value) > 3:
                                    issues.append(self._make_issue(
                                        message=f"疑似硬编码密钥: {target.id}",
                                        line=node.lineno,
                                        suggestion="从环境变量或配置文件读取敏感信息",
                                    ))
        return issues


class FunctionComplexityRule(AnalysisRule):
    """函数复杂度检查"""

    def __init__(self, max_complexity: int = 10):
        super().__init__("CX001", IssueSeverity.WARNING, IssueCategory.COMPLEXITY)
        self.max_complexity = max_complexity

    def analyze(self, code, tree, lines):
        issues = []
        if tree is None:
            return issues
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._calculate_complexity(node)
                if complexity > self.max_complexity:
                    issues.append(self._make_issue(
                        message=f"函数 {node.name} 圈复杂度过高 ({complexity} > {self.max_complexity})",
                        line=node.lineno,
                        suggestion="拆分函数或简化条件逻辑",
                    ))
        return issues

    def _calculate_complexity(self, node: ast.AST) -> int:
        """计算圈复杂度"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.ExceptHandler,)):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
        return complexity


class TooManyArgsRule(AnalysisRule):
    """参数过多检查"""

    def __init__(self, max_args: int = 7):
        super().__init__("BP002", IssueSeverity.WARNING, IssueCategory.BEST_PRACTICE)
        self.max_args = max_args

    def analyze(self, code, tree, lines):
        issues = []
        if tree is None:
            return issues
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args_count = len(node.args.args)
                if args_count > self.max_args:
                    issues.append(self._make_issue(
                        message=f"函数 {node.name} 参数过多 ({args_count} > {self.max_args})",
                        line=node.lineno,
                        suggestion="考虑使用参数对象或 *args/**kwargs",
                    ))
        return issues


class MissingDocstringRule(AnalysisRule):
    """缺少文档字符串检查"""

    def __init__(self):
        super().__init__("BP003", IssueSeverity.INFO, IssueCategory.BEST_PRACTICE)

    def analyze(self, code, tree, lines):
        issues = []
        if tree is None:
            return issues
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # 跳过私有方法（以_开头）
                if node.name.startswith("_") and not node.name.startswith("__"):
                    continue
                docstring = ast.get_docstring(node)
                if not docstring:
                    issues.append(self._make_issue(
                        message=f"{type(node).__name__.replace('Def','').replace('AsyncFunction','Function')} {node.name} 缺少文档字符串",
                        line=node.lineno,
                        suggestion="添加文档字符串说明用途",
                    ))
        return issues


class UnusedImportRule(AnalysisRule):
    """未使用导入检查"""

    def __init__(self):
        super().__init__("BP004", IssueSeverity.WARNING, IssueCategory.BEST_PRACTICE)

    def analyze(self, code, tree, lines):
        issues = []
        if tree is None:
            return issues

        imports: Dict[str, Tuple[int, str]] = {}  # name → (line, module)
        used_names: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    imports[name] = (node.lineno, alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    name = alias.asname or alias.name
                    imports[name] = (node.lineno, f"{node.module}.{alias.name}")
            elif isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        for name, (line, module) in imports.items():
            if name not in used_names:
                issues.append(self._make_issue(
                    message=f"未使用的导入: {module}",
                    line=line,
                    suggestion="移除未使用的导入",
                ))
        return issues


class DeepNestingRule(AnalysisRule):
    """深层嵌套检查"""

    def __init__(self, max_depth: int = 4):
        super().__init__("CX002", IssueSeverity.WARNING, IssueCategory.COMPLEXITY)
        self.max_depth = max_depth

    def analyze(self, code, tree, lines):
        issues = []
        if tree is None:
            return issues

        def check_depth(node: ast.AST, depth: int = 0, line: int = 0):
            nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try,
                             ast.AsyncFor, ast.AsyncWith)
            if isinstance(node, nesting_nodes):
                depth += 1
                if depth > self.max_depth and node.lineno != line:
                    issues.append(self._make_issue(
                        message=f"嵌套过深 ({depth} > {self.max_depth})",
                        line=node.lineno,
                        suggestion="提取嵌套逻辑到独立函数",
                    ))
                    line = node.lineno
            for child in ast.iter_child_nodes(node):
                check_depth(child, depth, line)

        check_depth(tree)
        return issues


class MutableDefaultArgRule(AnalysisRule):
    """可变默认参数检查"""

    def __init__(self):
        super().__init__("BP005", IssueSeverity.WARNING, IssueCategory.BEST_PRACTICE)

    def analyze(self, code, tree, lines):
        issues = []
        if tree is None:
            return issues
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append(self._make_issue(
                            message=f"函数 {node.name} 使用可变默认参数",
                            line=node.lineno,
                            suggestion="使用 None 作为默认值，在函数内初始化",
                        ))
        return issues


# ============================================================
# 代码审查模块
# ============================================================

class CodeReviewModule:
    """
    代码审查模块

    第一性原理：
    1. 代码审查 = 解析 + 规则分析 + 评分 + 报告
    2. 解析使用Python ast（零依赖）
    3. 规则可插拔，可独立启用/禁用
    4. 评分基于问题数量和严重程度
    5. LLM可增强语义分析（可选）
    """

    def __init__(self, llm_coordinator=None):
        self._llm_coordinator = llm_coordinator
        self._lock = threading.RLock()
        self._rules: List[AnalysisRule] = self._default_rules()
        self._review_history: List[ReviewReport] = []
        self._max_history = 1000

    def _default_rules(self) -> List[AnalysisRule]:
        """默认规则集"""
        return [
            SyntaxErrorRule(),
            LineLengthRule(max_length=120),
            BareExceptRule(),
            EvalExecRule(),
            HardcodedSecretRule(),
            FunctionComplexityRule(max_complexity=10),
            TooManyArgsRule(max_args=7),
            MissingDocstringRule(),
            UnusedImportRule(),
            DeepNestingRule(max_depth=4),
            MutableDefaultArgRule(),
        ]

    def add_rule(self, rule: AnalysisRule) -> None:
        """添加规则"""
        with self._lock:
            self._rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """移除规则"""
        with self._lock:
            before = len(self._rules)
            self._rules = [r for r in self._rules if r.rule_id != rule_id]
            return len(self._rules) < before

    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        with self._lock:
            for r in self._rules:
                if r.rule_id == rule_id:
                    r.enabled = True
                    return True
            return False

    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        with self._lock:
            for r in self._rules:
                if r.rule_id == rule_id:
                    r.enabled = False
                    return True
            return False

    def get_rules(self) -> List[Dict[str, Any]]:
        """获取所有规则"""
        with self._lock:
            return [
                {
                    "rule_id": r.rule_id,
                    "severity": r.severity.value,
                    "category": r.category.value,
                    "enabled": r.enabled,
                }
                for r in self._rules
            ]

    def review(self, code: str, file_path: str = "<string>") -> ReviewReport:
        """
        审查代码

        第一性原理：
        - 解析 → 分析 → 评分 → 报告
        - 每个步骤独立，可单独测试
        """
        start = time.time()

        # 防御：空代码
        if not code:
            return ReviewReport(
                file_path=file_path,
                language="python",
                error="Empty code",
                review_duration_ms=0.0,
            )

        lines = code.splitlines()
        tree = self._parse_code(code)
        issues: List[CodeIssue] = []
        metrics = CodeMetrics()

        # 计算度量
        metrics = self._calculate_metrics(code, tree, lines)

        # 运行规则
        with self._lock:
            active_rules = [r for r in self._rules if r.enabled]

        for rule in active_rules:
            try:
                rule_issues = rule.analyze(code, tree, lines)
                issues.extend(rule_issues)
            except Exception:
                pass  # 规则异常不应中断审查

        # 排序问题（按行号）
        issues.sort(key=lambda i: (i.line, i.column))

        # 计算评分
        score = self._calculate_score(issues, metrics)

        # 生成摘要
        summary = self._generate_summary(issues, metrics, score)

        duration = (time.time() - start) * 1000

        report = ReviewReport(
            file_path=file_path,
            language="python",
            issues=issues,
            metrics=metrics,
            score=score,
            summary=summary,
            review_duration_ms=duration,
        )

        with self._lock:
            self._review_history.append(report)
            if len(self._review_history) > self._max_history:
                self._review_history = self._review_history[-self._max_history:]

        return report

    def review_file(self, file_path: str) -> ReviewReport:
        """审查文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            return self.review(code, file_path)
        except IOError as e:
            return ReviewReport(
                file_path=file_path,
                language="python",
                error=f"无法读取文件: {e}",
            )

    def review_directory(
        self,
        dir_path: str,
        pattern: str = "*.py",
    ) -> List[ReviewReport]:
        """审查目录下所有Python文件"""
        import glob
        reports = []
        for filepath in glob.glob(os.path.join(dir_path, "**", pattern), recursive=True):
            reports.append(self.review_file(filepath))
        return reports

    def get_history(self, limit: int = 100) -> List[ReviewReport]:
        """获取审查历史"""
        with self._lock:
            return list(self._review_history[-limit:])

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total = len(self._review_history)
            if total == 0:
                return {"total_reviews": 0}
            avg_score = sum(r.score for r in self._review_history) / total
            passed = sum(1 for r in self._review_history if r.passed)
            return {
                "total_reviews": total,
                "avg_score": round(avg_score, 2),
                "pass_rate": round(passed / total * 100, 2),
                "rules_count": len(self._rules),
                "active_rules": sum(1 for r in self._rules if r.enabled),
            }

    # ============================================================
    # 内部实现
    # ============================================================

    def _parse_code(self, code: str) -> Optional[ast.AST]:
        """解析代码"""
        try:
            return ast.parse(code)
        except SyntaxError:
            return None

    def _calculate_metrics(
        self,
        code: str,
        tree: Optional[ast.AST],
        lines: List[str],
    ) -> CodeMetrics:
        """计算代码度量"""
        metrics = CodeMetrics()
        metrics.lines_total = len(lines)

        for line in lines:
            stripped = line.strip()
            if not stripped:
                metrics.lines_blank += 1
            elif stripped.startswith("#"):
                metrics.lines_comment += 1
            else:
                metrics.lines_code += 1
            length = len(line.rstrip("\n\r"))
            if length > metrics.max_line_length:
                metrics.max_line_length = length

        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    metrics.functions_count += 1
                    complexity = self._calc_func_complexity(node)
                    if complexity > metrics.max_complexity:
                        metrics.max_complexity = complexity
                elif isinstance(node, ast.ClassDef):
                    metrics.classes_count += 1
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    metrics.imports_count += 1

            # 平均复杂度
            complexities = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    complexities.append(self._calc_func_complexity(node))
            if complexities:
                metrics.avg_complexity = round(sum(complexities) / len(complexities), 2)

        return metrics

    def _calc_func_complexity(self, node: ast.AST) -> int:
        """计算函数圈复杂度"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
        return complexity

    def _calculate_score(self, issues: List[CodeIssue], metrics: CodeMetrics) -> float:
        """
        计算质量评分

        第一性原理：
        - 起始100分，按问题严重程度扣分
        - 错误扣分最多，风格扣分最少
        - 复杂度过高额外扣分
        - 最低0分
        """
        score = 100.0

        # 按严重程度扣分
        penalties = {
            IssueSeverity.ERROR: 15,
            IssueSeverity.WARNING: 5,
            IssueSeverity.INFO: 1,
            IssueSeverity.STYLE: 0.5,
        }

        for issue in issues:
            score -= penalties.get(issue.severity, 1)

        # 复杂度额外扣分
        if metrics.max_complexity > 15:
            score -= (metrics.max_complexity - 15) * 2

        # 钳制到0-100
        return max(0.0, min(100.0, round(score, 2)))

    def _generate_summary(
        self,
        issues: List[CodeIssue],
        metrics: CodeMetrics,
        score: float,
    ) -> str:
        """生成摘要"""
        parts = []
        parts.append(f"代码质量评分: {score}/100")
        parts.append(f"代码行数: {metrics.lines_code} (总{metrics.lines_total})")
        parts.append(f"函数: {metrics.functions_count}, 类: {metrics.classes_count}")

        if issues:
            error_count = sum(1 for i in issues if i.severity == IssueSeverity.ERROR)
            warning_count = sum(1 for i in issues if i.severity == IssueSeverity.WARNING)
            parts.append(f"问题: {len(issues)}个 ({error_count}错误, {warning_count}警告)")

            if error_count > 0:
                parts.append("状态: 需要修复错误")
            elif warning_count > 0:
                parts.append("状态: 建议改进")
            else:
                parts.append("状态: 良好")
        else:
            parts.append("问题: 无")
            parts.append("状态: 优秀")

        return " | ".join(parts)


# ============================================================
# 便捷函数
# ============================================================

def create_code_reviewer(llm_coordinator=None) -> CodeReviewModule:
    """创建代码审查器"""
    return CodeReviewModule(llm_coordinator=llm_coordinator)


def review_code(code: str, file_path: str = "<string>") -> ReviewReport:
    """快速审查代码"""
    reviewer = create_code_reviewer()
    return reviewer.review(code, file_path)


def review_file(file_path: str) -> ReviewReport:
    """快速审查文件"""
    reviewer = create_code_reviewer()
    return reviewer.review_file(file_path)
