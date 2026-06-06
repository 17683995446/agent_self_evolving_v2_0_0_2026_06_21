"""
阶段25: 接口契约测试框架 — 验证测试

验证目标:
1. 契约定义可声明、可描述
2. 输入/输出/前置/后置条件可检查
3. 契约测试执行器可运行测试用例
4. 违反契约时生成精确报告
5. 契约模板可复用
6. 运行时强制器可拦截违反
"""

import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.contract_testing import (
    ContractAspect, ContractTestResult, ContractViolation,
    ContractTestReport, InputSchemaContract, OutputSchemaContract,
    PreconditionContract, PostconditionContract, ErrorResponseContract,
    InterfaceContract, ContractTestExecutor, ContractEnforcer,
    create_numeric_input_contract, create_list_output_contract,
    create_dict_output_contract,
)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print('='*60)


def test_input_schema_contract():
    """测试输入Schema契约"""
    print_section("输入Schema契约")
    
    contract = InputSchemaContract(
        param_name="score",
        expected_type=(int, float),
        constraints=[lambda x: x >= 0, lambda x: x <= 100],
        constraint_descriptions=[">= 0", "<= 100"]
    )
    
    # 有效输入
    result = contract.check(50)
    assert result is None
    print("有效输入 50: 通过")
    
    # 类型错误
    result = contract.check("50")
    assert result is not None
    assert result.aspect == ContractAspect.INPUT_SCHEMA
    assert "type mismatch" in result.message
    print(f"类型错误 '50': {result.message}")
    
    # 范围错误
    result = contract.check(150)
    assert result is not None
    assert "<= 100" in result.message
    print(f"范围错误 150: {result.message}")
    
    # 描述
    desc = contract.describe()
    assert "score" in desc
    print(f"契约描述: {desc}")
    
    print("\n输入Schema契约测试通过!")
    return True


def test_output_schema_contract():
    """测试输出Schema契约"""
    print_section("输出Schema契约")
    
    contract = OutputSchemaContract(
        expected_type=dict,
        validator=lambda x: "status" in x,
        validator_desc="has 'status' key"
    )
    
    # 有效输出
    result = contract.check({"status": "ok", "data": 42})
    assert result is None
    print("有效输出: 通过")
    
    # 类型错误
    result = contract.check([1, 2, 3])
    assert result is not None
    assert "type mismatch" in result.message
    print(f"类型错误: {result.message}")
    
    # 验证失败
    result = contract.check({"data": 42})
    assert result is not None
    assert "validation failed" in result.message
    print(f"验证失败: {result.message}")
    
    print("\n输出Schema契约测试通过!")
    return True


def test_precondition_contract():
    """测试前置条件契约"""
    print_section("前置条件契约")
    
    contract = PreconditionContract(
        condition=lambda x: x > 0,
        description="x must be positive"
    )
    
    # 满足条件
    result = contract.check(5)
    assert result is None
    print("x=5 满足前置条件")
    
    # 违反条件
    result = contract.check(-1)
    assert result is not None
    assert "Precondition violated" in result.message
    print(f"x=-1 违反: {result.message}")
    
    # 描述
    assert "requires" in contract.describe()
    print(f"描述: {contract.describe()}")
    
    print("\n前置条件契约测试通过!")
    return True


def test_postcondition_contract():
    """测试后置条件契约"""
    print_section("后置条件契约")
    
    contract = PostconditionContract(
        condition=lambda result: result >= 0,
        description="result must be non-negative"
    )
    
    # 满足条件
    result = contract.check(10)
    assert result is None
    print("result=10 满足后置条件")
    
    # 违反条件
    result = contract.check(-5)
    assert result is not None
    assert "Postcondition violated" in result.message
    print(f"result=-5 违反: {result.message}")
    
    print("\n后置条件契约测试通过!")
    return True


def test_interface_contract_definition():
    """测试接口契约定义"""
    print_section("接口契约定义")
    
    interface = InterfaceContract(
        interface_name="DriveEngine",
        method_name="compute_gaps",
    )
    
    interface.add_input_contract(
        InputSchemaContract(
            param_name="state",
            expected_type=dict,
        )
    ).set_output_contract(
        OutputSchemaContract(
            expected_type=dict,
            validator=lambda x: all(k in x for k in ["safe_gap", "gain_gap", "eff_gap"]),
            validator_desc="has all gap fields"
        )
    ).add_precondition(
        PreconditionContract(
            condition=lambda state: state is not None,
            description="state must not be None"
        )
    ).add_postcondition(
        PostconditionContract(
            condition=lambda result: all(0 <= v <= 1 for v in result.values()),
            description="all gaps in [0, 1]"
        )
    )
    
    desc = interface.describe()
    assert "DriveEngine.compute_gaps" in desc
    assert "Input:" in desc
    assert "Output:" in desc
    assert "Pre:" in desc
    assert "Post:" in desc
    print(f"接口契约描述:\n{desc}")
    
    print("\n接口契约定义测试通过!")
    return True


def test_contract_test_executor():
    """测试契约测试执行器"""
    print_section("契约测试执行器")
    
    executor = ContractTestExecutor()
    
    # 定义契约
    contract = InterfaceContract(
        interface_name="Calculator",
        method_name="divide",
    ).add_input_contract(
        create_numeric_input_contract("divisor", min_value=0.001)
    ).set_output_contract(
        OutputSchemaContract(expected_type=(int, float))
    ).add_precondition(
        PreconditionContract(
            condition=lambda dividend, divisor: divisor != 0,
            description="divisor must not be zero"
        )
    )
    
    executor.register_contract(contract)
    
    # 实现
    def divide(dividend, divisor):
        return dividend / divisor
    
    # 测试用例
    test_cases = [
        {"args": [10, 2]},           # 正常
        {"args": [10, 0]},           # 除零
        {"args": [10, -1]},          # 负数（违反输入契约）
        {"args": [10, 0.001]},       # 边界值
    ]
    
    reports = executor.test_interface(
        "Calculator", "divide", divide, test_cases
    )
    
    assert len(reports) == 4
    
    # 用例1: 正常
    assert reports[0].is_passed
    print(f"用例1 (10/2): {'通过' if reports[0].is_passed else '失败'}")
    
    # 用例2: 除零 - 前置条件违反
    assert not reports[1].is_passed
    assert any("Precondition" in v.message for v in reports[1].violations)
    print(f"用例2 (10/0): 违反 - {reports[1].violations[0].message}")
    
    # 用例3: 负数 - 输入契约违反（数值范围约束）
    assert not reports[2].is_passed
    assert any("Parameter" in v.message or "precondition" in v.message.lower() for v in reports[2].violations)
    print(f"用例3 (10/-1): 违反 - {reports[2].violations[0].message}")
    
    # 用例4: 边界值
    assert reports[3].is_passed
    print(f"用例4 (10/0.001): {'通过' if reports[3].is_passed else '失败'}")
    
    print("\n契约测试执行器测试通过!")
    return True


def test_contract_templates():
    """测试契约模板"""
    print_section("契约模板")
    
    # 数值输入契约
    num_contract = create_numeric_input_contract("age", min_value=0, max_value=150)
    assert num_contract.check(25) is None
    assert num_contract.check(-1) is not None
    assert num_contract.check(200) is not None
    print("数值输入契约: 通过")
    
    # 列表输出契约
    list_contract = create_list_output_contract(min_length=1, max_length=5)
    assert list_contract.check([1, 2, 3]) is None
    assert list_contract.check([]) is not None
    assert list_contract.check([1]*10) is not None
    print("列表输出契约: 通过")
    
    # 字典输出契约
    dict_contract = create_dict_output_contract(required_keys=["id", "name"])
    assert dict_contract.check({"id": 1, "name": "test"}) is None
    assert dict_contract.check({"id": 1}) is not None
    print("字典输出契约: 通过")
    
    print("\n契约模板测试通过!")
    return True


def test_contract_enforcer():
    """测试运行时契约强制器"""
    print_section("运行时契约强制器")
    
    executor = ContractTestExecutor()
    
    contract = InterfaceContract(
        interface_name="Greeter",
        method_name="greet",
    ).add_input_contract(
        InputSchemaContract(
            param_name="name",
            expected_type=str,
        )
    ).set_output_contract(
        OutputSchemaContract(
            expected_type=str,
            validator=lambda x: x.startswith("Hello"),
            validator_desc="starts with 'Hello'"
        )
    )
    
    executor.register_contract(contract)
    enforcer = ContractEnforcer(executor)
    
    @enforcer.enforce("Greeter", "greet")
    def greet(name):
        return f"Hello, {name}"
    
    # 正常调用
    result = greet("World")
    assert result == "Hello, World"
    print(f"正常调用: {result}")
    
    # 输入类型错误
    try:
        greet(123)
        assert False, "应该抛出异常"
    except AssertionError as e:
        assert "Contract violation" in str(e)
        print(f"输入类型错误被拦截: {e}")
    
    # 修改实现使其违反输出契约
    @enforcer.enforce("Greeter", "greet")
    def greet_bad(name):
        return f"Hi, {name}"  # 不以 Hello 开头
    
    try:
        greet_bad("World")
        assert False, "应该抛出异常"
    except AssertionError as e:
        assert "Contract violation" in str(e)
        print(f"输出契约违反被拦截: {e}")
    
    # 禁用强制器
    enforcer.enabled = False
    result = greet_bad("World")
    assert result == "Hi, World"  # 不检查契约
    print(f"禁用后正常执行: {result}")
    
    print("\n运行时契约强制器测试通过!")
    return True


def test_error_response_contract():
    """测试错误响应契约"""
    print_section("错误响应契约")
    
    contract = ErrorResponseContract(
        error_trigger=lambda x: x < 0,
        expected_error_type=ValueError,
    )
    
    desc = contract.describe()
    assert "ValueError" in desc
    print(f"错误响应契约描述: {desc}")
    
    # 检查不直接执行，只描述
    result = contract.check(-1)
    assert result is None
    print("错误响应契约检查: 通过（仅描述）")
    
    print("\n错误响应契约测试通过!")
    return True


def test_report_generation():
    """测试报告生成"""
    print_section("报告生成")
    
    executor = ContractTestExecutor()
    
    contract = InterfaceContract(
        interface_name="Math",
        method_name="sqrt",
    ).add_input_contract(
        create_numeric_input_contract("x", min_value=0)
    ).set_output_contract(
        OutputSchemaContract(expected_type=(int, float))
    )
    
    executor.register_contract(contract)
    
    def sqrt(x):
        import math
        return math.sqrt(x)
    
    reports = executor.test_interface(
        "Math", "sqrt", sqrt,
        [
            {"args": [4]},
            {"args": [-1]},
        ]
    )
    
    markdown = executor.generate_test_report(reports)
    assert "# 接口契约测试报告" in markdown
    assert "总用例数" in markdown
    assert "Math.sqrt" in markdown
    print(f"报告预览 (前300字符):\n{markdown[:300]}...")
    
    # 检查报告字典
    report_dict = reports[0].to_dict()
    assert "interface_name" in report_dict
    assert "violations" in report_dict
    print(f"报告字典键: {list(report_dict.keys())}")
    
    print("\n报告生成测试通过!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("阶段25: 接口契约测试框架 — 验证测试")
    print("="*60)
    
    tests = [
        test_input_schema_contract,
        test_output_schema_contract,
        test_precondition_contract,
        test_postcondition_contract,
        test_interface_contract_definition,
        test_contract_test_executor,
        test_contract_templates,
        test_contract_enforcer,
        test_error_response_contract,
        test_report_generation,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"\n[失败] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("="*60)
