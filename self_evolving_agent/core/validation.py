"""
自驱永续进化Agent系统 — 输入验证中间件
阶段23：输入验证中间件

第一性原理：模块不应信任外部输入，验证是防御性编程的基础

验证规则：
1. 类型检查：确保数据类型正确
2. 范围检查：确保数值在有效范围内
3. 结构检查：确保数据结构完整
4. 依赖检查：确保相关字段一致
"""

import re
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum


class ValidationErrorType(Enum):
    """验证错误类型"""
    TYPE_ERROR = "type_error"
    RANGE_ERROR = "range_error"
    MISSING_FIELD = "missing_field"
    FORMAT_ERROR = "format_error"
    CONSTRAINT_ERROR = "constraint_error"


@dataclass
class ValidationError:
    """验证错误"""
    field: str
    error_type: ValidationErrorType
    message: str
    value: Any = None


@dataclass
class ValidationRule:
    """验证规则"""
    field: str
    required: bool = True
    field_type: type = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    custom_validator: Optional[Callable[[Any], bool]] = None
    error_message: Optional[str] = None


class InputValidator:
    """
    输入验证器

    统一的输入验证中间件
    """

    def __init__(self):
        self._rules: Dict[str, List[ValidationRule]] = {}
        self._global_validators: List[Callable[[Dict[str, Any]], List[ValidationError]]] = []

    def add_rule(self, schema_name: str, rule: ValidationRule) -> None:
        """添加验证规则"""
        if schema_name not in self._rules:
            self._rules[schema_name] = []
        self._rules[schema_name].append(rule)

    def add_global_validator(self, validator: Callable[[Dict[str, Any]], List[ValidationError]]) -> None:
        """添加全局验证器"""
        self._global_validators.append(validator)

    def validate(self, schema_name: str, data: Dict[str, Any]) -> List[ValidationError]:
        """
        验证数据

        Returns:
            验证错误列表，空列表表示验证通过
        """
        errors = []
        rules = self._rules.get(schema_name, [])

        for rule in rules:
            field_errors = self._validate_field(rule, data)
            errors.extend(field_errors)

        # 全局验证
        for validator in self._global_validators:
            try:
                global_errors = validator(data)
                errors.extend(global_errors)
            except Exception as e:
                errors.append(ValidationError(
                    field="_global",
                    error_type=ValidationErrorType.CONSTRAINT_ERROR,
                    message=f"Global validation error: {e}",
                ))

        return errors

    def validate_or_raise(self, schema_name: str, data: Dict[str, Any]) -> None:
        """验证数据，如果失败则抛出异常"""
        errors = self.validate(schema_name, data)
        if errors:
            raise ValidationException(errors)

    def is_valid(self, schema_name: str, data: Dict[str, Any]) -> bool:
        """检查数据是否有效"""
        return len(self.validate(schema_name, data)) == 0

    def _validate_field(self, rule: ValidationRule, data: Dict[str, Any]) -> List[ValidationError]:
        """验证单个字段"""
        errors = []
        value = data.get(rule.field)

        # 必填检查
        if rule.required and value is None:
            errors.append(ValidationError(
                field=rule.field,
                error_type=ValidationErrorType.MISSING_FIELD,
                message=rule.error_message or f"Field '{rule.field}' is required",
            ))
            return errors

        # 如果值为None且不是必填，跳过其他检查
        if value is None:
            return errors

        # 类型检查
        if rule.field_type is not None and not isinstance(value, rule.field_type):
            errors.append(ValidationError(
                field=rule.field,
                error_type=ValidationErrorType.TYPE_ERROR,
                message=rule.error_message or f"Field '{rule.field}' must be of type {rule.field_type.__name__}",
                value=value,
            ))

        # 数值范围检查
        if isinstance(value, (int, float)):
            if rule.min_value is not None and value < rule.min_value:
                errors.append(ValidationError(
                    field=rule.field,
                    error_type=ValidationErrorType.RANGE_ERROR,
                    message=rule.error_message or f"Field '{rule.field}' must be >= {rule.min_value}",
                    value=value,
                ))
            if rule.max_value is not None and value > rule.max_value:
                errors.append(ValidationError(
                    field=rule.field,
                    error_type=ValidationErrorType.RANGE_ERROR,
                    message=rule.error_message or f"Field '{rule.field}' must be <= {rule.max_value}",
                    value=value,
                ))

        # 字符串模式检查
        if isinstance(value, str) and rule.pattern is not None:
            if not re.match(rule.pattern, value):
                errors.append(ValidationError(
                    field=rule.field,
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    message=rule.error_message or f"Field '{rule.field}' does not match pattern {rule.pattern}",
                    value=value,
                ))

        # 允许值检查
        if rule.allowed_values is not None and value not in rule.allowed_values:
            errors.append(ValidationError(
                field=rule.field,
                error_type=ValidationErrorType.CONSTRAINT_ERROR,
                message=rule.error_message or f"Field '{rule.field}' must be one of {rule.allowed_values}",
                value=value,
            ))

        # 自定义验证器
        if rule.custom_validator is not None:
            try:
                if not rule.custom_validator(value):
                    errors.append(ValidationError(
                        field=rule.field,
                        error_type=ValidationErrorType.CONSTRAINT_ERROR,
                        message=rule.error_message or f"Field '{rule.field}' failed custom validation",
                        value=value,
                    ))
            except Exception as e:
                errors.append(ValidationError(
                    field=rule.field,
                    error_type=ValidationErrorType.CONSTRAINT_ERROR,
                    message=f"Custom validation error for '{rule.field}': {e}",
                    value=value,
                ))

        return errors


class ValidationException(Exception):
    """验证异常"""

    def __init__(self, errors: List[ValidationError]):
        self.errors = errors
        messages = [f"{e.field}: {e.message}" for e in errors]
        super().__init__("; ".join(messages))

    def to_dict(self) -> List[Dict[str, Any]]:
        """转换为字典"""
        return [
            {
                "field": e.field,
                "error_type": e.error_type.value,
                "message": e.message,
                "value": str(e.value) if e.value is not None else None,
            }
            for e in self.errors
        ]


# ============================================================================
# 预定义验证Schema
# ============================================================================

def create_state_validator() -> InputValidator:
    """创建状态数据验证器"""
    validator = InputValidator()

    # 状态数据规则
    validator.add_rule("state", ValidationRule(
        field="value",
        required=False,
        field_type=(int, float),
        min_value=-1e6,
        max_value=1e6,
    ))
    validator.add_rule("state", ValidationRule(
        field="cpu_usage",
        required=False,
        field_type=(int, float),
        min_value=0.0,
        max_value=1.0,
    ))
    validator.add_rule("state", ValidationRule(
        field="memory_usage",
        required=False,
        field_type=(int, float),
        min_value=0.0,
        max_value=1.0,
    ))

    return validator


def create_drive_gaps_validator() -> InputValidator:
    """创建驱力缺口验证器"""
    validator = InputValidator()

    for field_name in ["safe_gap", "gain_gap", "eff_gap"]:
        validator.add_rule("drive_gaps", ValidationRule(
            field=field_name,
            required=True,
            field_type=(int, float),
            min_value=0.0,
            max_value=1.0,
        ))

    return validator


def create_task_validator() -> InputValidator:
    """创建任务验证器"""
    validator = InputValidator()

    validator.add_rule("task", ValidationRule(
        field="action",
        required=True,
        field_type=str,
        min_value=1,  # 最小长度通过自定义验证器
    ))
    validator.add_rule("task", ValidationRule(
        field="success_probability",
        required=False,
        field_type=(int, float),
        min_value=0.0,
        max_value=1.0,
    ))
    validator.add_rule("task", ValidationRule(
        field="cost",
        required=False,
        field_type=(int, float),
        min_value=0.0,
    ))

    return validator


# ============================================================================
# 便捷函数
# ============================================================================

def validate_state(data: Dict[str, Any]) -> List[ValidationError]:
    """便捷函数：验证状态数据"""
    validator = create_state_validator()
    return validator.validate("state", data)


def validate_drive_gaps(data: Dict[str, Any]) -> List[ValidationError]:
    """便捷函数：验证驱力缺口"""
    validator = create_drive_gaps_validator()
    return validator.validate("drive_gaps", data)


def validate_task(data: Dict[str, Any]) -> List[ValidationError]:
    """便捷函数：验证任务"""
    validator = create_task_validator()
    return validator.validate("task", data)
