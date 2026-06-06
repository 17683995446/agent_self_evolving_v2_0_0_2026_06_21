"""
阶段25: 接口契约测试框架

第一性原理:
1. 接口是模块间的契约，契约必须可验证
2. 没有自动化契约测试，接口变更将无声地破坏依赖方
3. 契约测试应验证：输入约束、输出格式、副作用、边界行为

设计原则:
- 契约定义与实现分离
- 支持消费者驱动契约（CDC）
- 可自动生成、可自动验证
- 失败时提供精确的诊断信息
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional, Type, Tuple, Union
from enum import Enum, auto
from abc import ABC, abstractmethod
import inspect
from datetime import datetime


class ContractAspect(Enum):
    """契约测试的方面"""
    INPUT_SCHEMA = "input_schema"       # 输入参数格式
    OUTPUT_SCHEMA = "output_schema"     # 输出结果格式
    PRECONDITION = "precondition"       # 前置条件
    POSTCONDITION = "postcondition"     # 后置条件
    INVARIANT = "invariant"             # 不变量
    SIDE_EFFECT = "side_effect"         # 副作用
    PERFORMANCE = "performance"         # 性能约束
    ERROR_RESPONSE = "error_response"   # 错误响应


class ContractTestResult(Enum):
    """契约测试结果"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ContractViolation:
    """契约违反记录"""
    aspect: ContractAspect
    message: str
    expected: Any = None
    actual: Any = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "aspect": self.aspect.value,
            "message": self.message,
            "expected": str(self.expected) if self.expected is not None else None,
            "actual": str(self.actual) if self.actual is not None else None,
            "context": self.context,
        }


@dataclass
class ContractTestReport:
    """契约测试报告"""
    interface_name: str
    method_name: str
    result: ContractTestResult
    violations: List[ContractViolation] = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def is_passed(self) -> bool:
        return self.result == ContractTestResult.PASSED and len(self.violations) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "interface_name": self.interface_name,
            "method_name": self.method_name,
            "result": self.result.value,
            "passed": self.is_passed,
            "violations": [v.to_dict() for v in self.violations],
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================================
# 契约定义基类
# ============================================================

class Contract(ABC):
    """
    契约定义抽象基类
    
    第一性原理：契约是对行为的约束，必须可声明、可检查
    """
    
    @abstractmethod
    def check(self, *args, **kwargs) -> Optional[ContractViolation]:
        """检查契约，返回违反记录或None"""
        pass
    
    @abstractmethod
    def describe(self) -> str:
        """返回契约的人类可读描述"""
        pass


@dataclass
class InputSchemaContract(Contract):
    """输入参数Schema契约"""
    param_name: str
    expected_type: Type
    constraints: List[Callable[[Any], bool]] = field(default_factory=list)
    constraint_descriptions: List[str] = field(default_factory=list)
    
    def _type_name(self, t) -> str:
        """获取类型名称，支持联合类型"""
        if isinstance(t, tuple):
            return " | ".join(x.__name__ for x in t)
        return t.__name__
    
    def check(self, value: Any) -> Optional[ContractViolation]:
        # 类型检查
        if not isinstance(value, self.expected_type):
            return ContractViolation(
                aspect=ContractAspect.INPUT_SCHEMA,
                message=f"Parameter '{self.param_name}' type mismatch",
                expected=self._type_name(self.expected_type),
                actual=type(value).__name__,
            )
        
        # 约束检查
        for i, constraint in enumerate(self.constraints):
            if not constraint(value):
                desc = self.constraint_descriptions[i] if i < len(self.constraint_descriptions) else "constraint failed"
                return ContractViolation(
                    aspect=ContractAspect.INPUT_SCHEMA,
                    message=f"Parameter '{self.param_name}' {desc}",
                    actual=value,
                )
        
        return None
    
    def describe(self) -> str:
        constraints = ", ".join(self.constraint_descriptions) if self.constraint_descriptions else "no constraints"
        return f"{self.param_name}: {self._type_name(self.expected_type)} ({constraints})"


@dataclass
class OutputSchemaContract(Contract):
    """输出结果Schema契约"""
    expected_type: Type
    validator: Optional[Callable[[Any], bool]] = None
    validator_desc: str = ""
    
    def check(self, result: Any) -> Optional[ContractViolation]:
        if not isinstance(result, self.expected_type):
            return ContractViolation(
                aspect=ContractAspect.OUTPUT_SCHEMA,
                message="Return type mismatch",
                expected=self.expected_type.__name__,
                actual=type(result).__name__,
            )
        
        if self.validator and not self.validator(result):
            return ContractViolation(
                aspect=ContractAspect.OUTPUT_SCHEMA,
                message=f"Return value validation failed: {self.validator_desc}",
                actual=result,
            )
        
        return None
    
    def describe(self) -> str:
        return f"returns {self.expected_type.__name__}"


@dataclass
class PreconditionContract(Contract):
    """前置条件契约"""
    condition: Callable[..., bool]
    description: str
    
    def check(self, *args, **kwargs) -> Optional[ContractViolation]:
        try:
            if not self.condition(*args, **kwargs):
                return ContractViolation(
                    aspect=ContractAspect.PRECONDITION,
                    message=f"Precondition violated: {self.description}",
                )
        except Exception as e:
            return ContractViolation(
                aspect=ContractAspect.PRECONDITION,
                message=f"Precondition check error: {e}",
            )
        return None
    
    def describe(self) -> str:
        return f"requires: {self.description}"


@dataclass
class PostconditionContract(Contract):
    """后置条件契约"""
    condition: Callable[..., bool]
    description: str
    captures_input: bool = False  # 是否捕获输入用于检查
    _captured_input: Any = None
    
    def check(self, result: Any, *args, **kwargs) -> Optional[ContractViolation]:
        try:
            if self.captures_input:
                if not self.condition(result, self._captured_input):
                    return ContractViolation(
                        aspect=ContractAspect.POSTCONDITION,
                        message=f"Postcondition violated: {self.description}",
                        expected=True,
                        actual=False,
                    )
            else:
                if not self.condition(result):
                    return ContractViolation(
                        aspect=ContractAspect.POSTCONDITION,
                        message=f"Postcondition violated: {self.description}",
                        expected=True,
                        actual=False,
                    )
        except Exception as e:
            return ContractViolation(
                aspect=ContractAspect.POSTCONDITION,
                message=f"Postcondition check error: {e}",
            )
        return None
    
    def describe(self) -> str:
        return f"ensures: {self.description}"


@dataclass
class ErrorResponseContract(Contract):
    """错误响应契约"""
    error_trigger: Callable[..., bool]  # 何时触发错误
    expected_error_type: Type[Exception]
    error_checker: Optional[Callable[[Exception], bool]] = None
    
    def check(self, *args, **kwargs) -> Optional[ContractViolation]:
        # 这个契约在调用方使用，这里只描述
        return None
    
    def describe(self) -> str:
        return f"when error triggered, raises {self.expected_error_type.__name__}"


# ============================================================
# 接口契约定义
# ============================================================

@dataclass
class InterfaceContract:
    """
    接口契约定义
    
    将一组契约与一个接口方法绑定
    """
    interface_name: str
    method_name: str
    input_contracts: List[InputSchemaContract] = field(default_factory=list)
    output_contract: Optional[OutputSchemaContract] = None
    preconditions: List[PreconditionContract] = field(default_factory=list)
    postconditions: List[PostconditionContract] = field(default_factory=list)
    error_contracts: List[ErrorResponseContract] = field(default_factory=list)
    
    def add_input_contract(self, contract: InputSchemaContract) -> 'InterfaceContract':
        self.input_contracts.append(contract)
        return self
    
    def set_output_contract(self, contract: OutputSchemaContract) -> 'InterfaceContract':
        self.output_contract = contract
        return self
    
    def add_precondition(self, contract: PreconditionContract) -> 'InterfaceContract':
        self.preconditions.append(contract)
        return self
    
    def add_postcondition(self, contract: PostconditionContract) -> 'InterfaceContract':
        self.postconditions.append(contract)
        return self
    
    def add_error_contract(self, contract: ErrorResponseContract) -> 'InterfaceContract':
        self.error_contracts.append(contract)
        return self
    
    def describe(self) -> str:
        lines = [f"Interface: {self.interface_name}.{self.method_name}"]
        for c in self.input_contracts:
            lines.append(f"  Input: {c.describe()}")
        for c in self.preconditions:
            lines.append(f"  Pre: {c.describe()}")
        if self.output_contract:
            lines.append(f"  Output: {self.output_contract.describe()}")
        for c in self.postconditions:
            lines.append(f"  Post: {c.describe()}")
        return "\n".join(lines)


# ============================================================
# 契约测试执行器
# ============================================================

class ContractTestExecutor:
    """
    契约测试执行器
    
    执行接口契约测试，验证实现是否满足契约
    """
    
    def __init__(self):
        self._contracts: Dict[str, InterfaceContract] = {}
    
    def register_contract(self, contract: InterfaceContract) -> None:
        """注册接口契约"""
        key = f"{contract.interface_name}.{contract.method_name}"
        self._contracts[key] = contract
    
    def get_contract(self, interface_name: str, method_name: str) -> Optional[InterfaceContract]:
        """获取接口契约"""
        key = f"{interface_name}.{method_name}"
        return self._contracts.get(key)
    
    def test_interface(
        self,
        interface_name: str,
        method_name: str,
        implementation: Callable,
        test_cases: List[Dict[str, Any]],
        capture_exceptions: bool = True
    ) -> List[ContractTestReport]:
        """
        测试接口实现是否满足契约
        
        Args:
            interface_name: 接口名称
            method_name: 方法名称
            implementation: 实现函数
            test_cases: 测试用例列表，每个用例是 {"args": [], "kwargs": {}, "expected_error": None}
            capture_exceptions: 是否捕获异常继续测试
        
        Returns:
            每个测试用例的报告列表
        """
        import time
        
        contract = self.get_contract(interface_name, method_name)
        if contract is None:
            return [ContractTestReport(
                interface_name=interface_name,
                method_name=method_name,
                result=ContractTestResult.SKIPPED,
                violations=[ContractViolation(
                    aspect=ContractAspect.INVARIANT,
                    message=f"No contract defined for {interface_name}.{method_name}"
                )]
            )]
        
        reports = []
        
        for i, test_case in enumerate(test_cases):
            report = ContractTestReport(
                interface_name=interface_name,
                method_name=method_name,
                result=ContractTestResult.PASSED,
            )
            
            args = test_case.get("args", [])
            kwargs = test_case.get("kwargs", {})
            expected_error = test_case.get("expected_error")
            
            start = time.time()
            
            try:
                # 1. 检查前置条件
                for pre in contract.preconditions:
                    violation = pre.check(*args, **kwargs)
                    if violation:
                        report.violations.append(violation)
                
                # 2. 检查输入契约
                for inp in contract.input_contracts:
                    # 从args/kwargs中找到对应参数
                    param_value = self._get_param_value(inp.param_name, args, kwargs, implementation)
                    if param_value is not None:
                        violation = inp.check(param_value)
                        if violation:
                            report.violations.append(violation)
                
                # 3. 执行实现
                result = implementation(*args, **kwargs)
                
                # 4. 检查输出契约
                if contract.output_contract:
                    violation = contract.output_contract.check(result)
                    if violation:
                        report.violations.append(violation)
                
                # 5. 检查后置条件
                for post in contract.postconditions:
                    violation = post.check(result, *args, **kwargs)
                    if violation:
                        report.violations.append(violation)
                
                # 6. 检查是否期望错误但未发生
                if expected_error is not None:
                    report.violations.append(ContractViolation(
                        aspect=ContractAspect.ERROR_RESPONSE,
                        message=f"Expected error {expected_error.__name__} but none raised",
                        expected=expected_error.__name__,
                        actual="None",
                    ))
                
            except Exception as e:
                if expected_error and isinstance(e, expected_error):
                    # 期望的错误发生了
                    pass
                elif capture_exceptions:
                    report.violations.append(ContractViolation(
                        aspect=ContractAspect.ERROR_RESPONSE,
                        message=f"Unexpected exception: {type(e).__name__}: {e}",
                        actual=str(e),
                    ))
                else:
                    raise
            
            report.duration_ms = (time.time() - start) * 1000
            
            if report.violations:
                report.result = ContractTestResult.FAILED
            
            reports.append(report)
        
        return reports
    
    def _get_param_value(
        self,
        param_name: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        func: Callable
    ) -> Any:
        """从args/kwargs中获取参数值"""
        if param_name in kwargs:
            return kwargs[param_name]
        
        # 尝试从args按位置获取
        try:
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            if param_name in params:
                idx = params.index(param_name)
                if idx < len(args):
                    return args[idx]
        except (ValueError, TypeError):
            pass
        
        return None
    
    def generate_test_report(self, reports: List[ContractTestReport]) -> str:
        """生成测试报告"""
        lines = [
            "# 接口契约测试报告",
            "",
            f"**总用例数**: {len(reports)}",
            f"**通过**: {sum(1 for r in reports if r.is_passed)}",
            f"**失败**: {sum(1 for r in reports if not r.is_passed)}",
            "",
        ]
        
        for i, report in enumerate(reports):
            status = "PASS" if report.is_passed else "FAIL"
            lines.append(f"## 用例 {i+1}: {status}")
            lines.append(f"- 接口: {report.interface_name}.{report.method_name}")
            lines.append(f"- 耗时: {report.duration_ms:.2f}ms")
            
            for v in report.violations:
                lines.append(f"- **违反**: [{v.aspect.value}] {v.message}")
                if v.expected is not None:
                    lines.append(f"  - 期望: {v.expected}")
                if v.actual is not None:
                    lines.append(f"  - 实际: {v.actual}")
            
            lines.append("")
        
        return "\n".join(lines)


# ============================================================
# 预定义契约模板
# ============================================================

def create_numeric_input_contract(
    param_name: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    allow_none: bool = False
) -> InputSchemaContract:
    """创建数值输入契约"""
    constraints = []
    descriptions = []
    
    if min_value is not None:
        constraints.append(lambda x, mv=min_value: x >= mv)
        descriptions.append(f">= {min_value}")
    
    if max_value is not None:
        constraints.append(lambda x, mv=max_value: x <= mv)
        descriptions.append(f"<= {max_value}")
    
    return InputSchemaContract(
        param_name=param_name,
        expected_type=(int, float) if not allow_none else (int, float, type(None)),
        constraints=constraints,
        constraint_descriptions=descriptions,
    )


def create_list_output_contract(
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    element_validator: Optional[Callable[[Any], bool]] = None
) -> OutputSchemaContract:
    """创建列表输出契约"""
    def validator(result):
        if not isinstance(result, list):
            return False
        if min_length is not None and len(result) < min_length:
            return False
        if max_length is not None and len(result) > max_length:
            return False
        if element_validator:
            return all(element_validator(e) for e in result)
        return True
    
    desc_parts = []
    if min_length is not None:
        desc_parts.append(f"min_length={min_length}")
    if max_length is not None:
        desc_parts.append(f"max_length={max_length}")
    
    return OutputSchemaContract(
        expected_type=list,
        validator=validator,
        validator_desc=", ".join(desc_parts) if desc_parts else "valid list",
    )


def create_dict_output_contract(
    required_keys: Optional[List[str]] = None
) -> OutputSchemaContract:
    """创建字典输出契约"""
    def validator(result):
        if not isinstance(result, dict):
            return False
        if required_keys:
            return all(k in result for k in required_keys)
        return True
    
    return OutputSchemaContract(
        expected_type=dict,
        validator=validator,
        validator_desc=f"required_keys={required_keys}" if required_keys else "valid dict",
    )


# ============================================================
# 快捷装饰器
# ============================================================

class ContractEnforcer:
    """
    契约强制执行器
    
    在运行时检查契约（用于开发/测试环境）
    """
    
    def __init__(self, executor: ContractTestExecutor):
        self.executor = executor
        self.enabled = True
    
    def enforce(self, interface_name: str, method_name: str):
        """装饰器：强制执行契约"""
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                contract = self.executor.get_contract(interface_name, method_name)
                if contract is None:
                    return func(*args, **kwargs)
                
                # 检查前置条件
                for pre in contract.preconditions:
                    violation = pre.check(*args, **kwargs)
                    if violation:
                        raise AssertionError(f"Contract violation: {violation.message}")
                
                # 检查输入
                for inp in contract.input_contracts:
                    param_value = self.executor._get_param_value(
                        inp.param_name, args, kwargs, func
                    )
                    if param_value is not None:
                        violation = inp.check(param_value)
                        if violation:
                            raise AssertionError(f"Contract violation: {violation.message}")
                
                # 执行
                result = func(*args, **kwargs)
                
                # 检查输出
                if contract.output_contract:
                    violation = contract.output_contract.check(result)
                    if violation:
                        raise AssertionError(f"Contract violation: {violation.message}")
                
                # 检查后置条件
                for post in contract.postconditions:
                    violation = post.check(result, *args, **kwargs)
                    if violation:
                        raise AssertionError(f"Contract violation: {violation.message}")
                
                return result
            
            return wrapper
        return decorator
