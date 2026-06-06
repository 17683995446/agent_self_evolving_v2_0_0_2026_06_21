"""
阶段23验证：输入验证中间件
"""
import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.validation import (
    InputValidator, ValidationRule, ValidationError, ValidationException,
    ValidationErrorType, validate_state, validate_drive_gaps, validate_task
)


def test_type_validation():
    """测试类型验证"""
    print("=" * 60)
    print("测试: 类型验证")
    print("=" * 60)

    validator = InputValidator()
    validator.add_rule("test", ValidationRule(
        field="age",
        required=True,
        field_type=int,
    ))

    # 有效数据
    errors = validator.validate("test", {"age": 25})
    assert len(errors) == 0
    print("有效数据通过验证")

    # 无效类型
    errors = validator.validate("test", {"age": "25"})
    assert len(errors) == 1
    assert errors[0].error_type == ValidationErrorType.TYPE_ERROR
    print(f"无效类型正确检测: {errors[0].message}")

    print("\n类型验证测试通过!")
    return True


def test_range_validation():
    """测试范围验证"""
    print("\n" + "=" * 60)
    print("测试: 范围验证")
    print("=" * 60)

    validator = InputValidator()
    validator.add_rule("test", ValidationRule(
        field="score",
        required=True,
        field_type=(int, float),
        min_value=0.0,
        max_value=100.0,
    ))

    # 有效数据
    errors = validator.validate("test", {"score": 50})
    assert len(errors) == 0

    # 超出范围
    errors = validator.validate("test", {"score": 150})
    assert len(errors) == 1
    assert errors[0].error_type == ValidationErrorType.RANGE_ERROR
    print(f"超出范围正确检测: {errors[0].message}")

    # 低于范围
    errors = validator.validate("test", {"score": -10})
    assert len(errors) == 1

    print("\n范围验证测试通过!")
    return True


def test_required_validation():
    """测试必填验证"""
    print("\n" + "=" * 60)
    print("测试: 必填验证")
    print("=" * 60)

    validator = InputValidator()
    validator.add_rule("test", ValidationRule(
        field="name",
        required=True,
        field_type=str,
    ))

    # 缺少字段
    errors = validator.validate("test", {})
    assert len(errors) == 1
    assert errors[0].error_type == ValidationErrorType.MISSING_FIELD
    print(f"缺少字段正确检测: {errors[0].message}")

    # 提供字段
    errors = validator.validate("test", {"name": "test"})
    assert len(errors) == 0

    # None值视为缺失
    errors = validator.validate("test", {"name": None})
    assert len(errors) == 1

    print("\n必填验证测试通过!")
    return True


def test_pattern_validation():
    """测试模式验证"""
    print("\n" + "=" * 60)
    print("测试: 模式验证")
    print("=" * 60)

    validator = InputValidator()
    validator.add_rule("test", ValidationRule(
        field="email",
        required=True,
        field_type=str,
        pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$",
    ))

    # 有效邮箱
    errors = validator.validate("test", {"email": "test@example.com"})
    assert len(errors) == 0

    # 无效邮箱
    errors = validator.validate("test", {"email": "invalid"})
    assert len(errors) == 1
    assert errors[0].error_type == ValidationErrorType.FORMAT_ERROR
    print(f"无效格式正确检测: {errors[0].message}")

    print("\n模式验证测试通过!")
    return True


def test_allowed_values():
    """测试允许值验证"""
    print("\n" + "=" * 60)
    print("测试: 允许值验证")
    print("=" * 60)

    validator = InputValidator()
    validator.add_rule("test", ValidationRule(
        field="status",
        required=True,
        field_type=str,
        allowed_values=["active", "inactive", "pending"],
    ))

    # 有效值
    errors = validator.validate("test", {"status": "active"})
    assert len(errors) == 0

    # 无效值
    errors = validator.validate("test", {"status": "deleted"})
    assert len(errors) == 1
    assert errors[0].error_type == ValidationErrorType.CONSTRAINT_ERROR
    print(f"无效值正确检测: {errors[0].message}")

    print("\n允许值验证测试通过!")
    return True


def test_custom_validator():
    """测试自定义验证器"""
    print("\n" + "=" * 60)
    print("测试: 自定义验证器")
    print("=" * 60)

    validator = InputValidator()
    validator.add_rule("test", ValidationRule(
        field="even_number",
        required=True,
        field_type=int,
        custom_validator=lambda x: x % 2 == 0,
        error_message="Must be even",
    ))

    # 有效值
    errors = validator.validate("test", {"even_number": 4})
    assert len(errors) == 0

    # 无效值
    errors = validator.validate("test", {"even_number": 3})
    assert len(errors) == 1
    assert "even" in errors[0].message
    print(f"自定义验证正确: {errors[0].message}")

    print("\n自定义验证器测试通过!")
    return True


def test_validate_or_raise():
    """测试验证或抛出异常"""
    print("\n" + "=" * 60)
    print("测试: 验证或抛出异常")
    print("=" * 60)

    validator = InputValidator()
    validator.add_rule("test", ValidationRule(
        field="required_field",
        required=True,
    ))

    # 有效数据
    validator.validate_or_raise("test", {"required_field": "value"})
    print("有效数据不抛出异常")

    # 无效数据
    try:
        validator.validate_or_raise("test", {})
        assert False, "应抛出异常"
    except ValidationException as e:
        print(f"无效数据正确抛出异常: {e}")
        assert len(e.errors) == 1

    print("\n验证或抛出异常测试通过!")
    return True


def test_state_validator():
    """测试状态验证器"""
    print("\n" + "=" * 60)
    print("测试: 状态验证器")
    print("=" * 60)

    # 有效状态
    errors = validate_state({"cpu_usage": 0.5, "memory_usage": 0.3})
    assert len(errors) == 0
    print("有效状态通过验证")

    # 无效范围
    errors = validate_state({"cpu_usage": 1.5})
    assert len(errors) == 1
    print(f"无效范围正确检测: {errors[0].message}")

    print("\n状态验证器测试通过!")
    return True


def test_drive_gaps_validator():
    """测试驱力缺口验证器"""
    print("\n" + "=" * 60)
    print("测试: 驱力缺口验证器")
    print("=" * 60)

    # 有效数据
    errors = validate_drive_gaps({"safe_gap": 0.3, "gain_gap": 0.5, "eff_gap": 0.2})
    assert len(errors) == 0
    print("有效驱力缺口通过验证")

    # 缺少字段
    errors = validate_drive_gaps({"safe_gap": 0.3})
    assert len(errors) == 2  # gain_gap 和 eff_gap 缺失
    print(f"缺少字段正确检测: {len(errors)} 个错误")

    # 超出范围
    errors = validate_drive_gaps({"safe_gap": 1.5, "gain_gap": 0.5, "eff_gap": 0.2})
    assert len(errors) == 1
    print(f"超出范围正确检测: {errors[0].message}")

    print("\n驱力缺口验证器测试通过!")
    return True


def test_multiple_errors():
    """测试多个错误"""
    print("\n" + "=" * 60)
    print("测试: 多个错误")
    print("=" * 60)

    validator = InputValidator()
    validator.add_rule("test", ValidationRule(field="field1", required=True))
    validator.add_rule("test", ValidationRule(field="field2", required=True, field_type=int))

    errors = validator.validate("test", {})
    assert len(errors) == 2
    print(f"检测到 {len(errors)} 个错误")

    for e in errors:
        print(f"  - {e.field}: {e.message}")

    print("\n多个错误测试通过!")
    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("阶段23: 输入验证中间件 — 验证测试")
    print("=" * 60)

    tests = [
        ("类型验证", test_type_validation),
        ("范围验证", test_range_validation),
        ("必填验证", test_required_validation),
        ("模式验证", test_pattern_validation),
        ("允许值验证", test_allowed_values),
        ("自定义验证器", test_custom_validator),
        ("验证或抛出异常", test_validate_or_raise),
        ("状态验证器", test_state_validator),
        ("驱力缺口验证器", test_drive_gaps_validator),
        ("多个错误", test_multiple_errors),
    ]

    passed = 0
    failed = 0
    for name, test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"\n测试 {name} 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
