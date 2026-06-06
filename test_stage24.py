"""
阶段24: 错误码标准化 — 验证测试

验证目标:
1. 错误码格式正确且唯一
2. 错误注册表可查询、可分类
3. 错误实例包含完整上下文
4. 错误链可追踪
5. 文档可自动生成
6. 异常类可正确捕获和处理
"""

import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.error_codes import (
    ErrorSeverity, ErrorCategory, ErrorCode, AgentError,
    ErrorRegistry, AgentException, ValidationException,
    SYS_UNKNOWN_ERROR, VAL_INVALID_TYPE, VAL_MISSING_REQUIRED_FIELD,
    VAL_OUT_OF_RANGE, IFC_VERSION_INCOMPATIBLE, RES_MEMORY_LIMIT_EXCEEDED,
    LOG_PREDICTION_FAILED, CFG_KEY_NOT_FOUND, SEC_UNAUTHORIZED_ACCESS,
    create_error, get_error_registry
)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print('='*60)


def test_error_code_format():
    """测试错误码格式和属性"""
    print_section("错误码格式和属性")
    
    # 测试 VAL_001
    assert VAL_INVALID_TYPE.code == "VAL_001"
    assert VAL_INVALID_TYPE.category == ErrorCategory.VALIDATION
    assert VAL_INVALID_TYPE.severity == ErrorSeverity.ERROR
    assert VAL_INVALID_TYPE.recoverable == True
    assert "{field}" in VAL_INVALID_TYPE.message_template
    print(f"错误码: {VAL_INVALID_TYPE.code}")
    print(f"分类: {VAL_INVALID_TYPE.category.value}")
    print(f"严重级别: {VAL_INVALID_TYPE.severity.value}")
    print(f"可恢复: {VAL_INVALID_TYPE.recoverable}")
    
    # 测试格式化消息
    msg = VAL_INVALID_TYPE.format_message(field="age", expected="int", actual="str")
    assert "age" in msg
    assert "int" in msg
    assert "str" in msg
    print(f"格式化消息: {msg}")
    
    # 测试 to_dict
    d = VAL_INVALID_TYPE.to_dict()
    assert d["code"] == "VAL_001"
    assert d["category"] == "VAL"
    print(f"字典表示: {d}")
    
    print("\n错误码格式测试通过!")
    return True


def test_error_registry():
    """测试错误注册表"""
    print_section("错误注册表")
    
    registry = ErrorRegistry()
    
    # 测试查询
    code = registry.get("VAL_001")
    assert code is not None
    assert code.code == "VAL_001"
    print(f"查询 VAL_001: {code.description}")
    
    # 测试查询不存在的
    assert registry.get("XXX_999") is None
    print("查询不存在的错误码: None")
    
    # 测试按分类查找
    val_codes = registry.find_by_category(ErrorCategory.VALIDATION)
    assert len(val_codes) >= 7  # 至少有7个验证错误
    print(f"验证类错误数量: {len(val_codes)}")
    
    # 测试按严重级别查找
    fatal_codes = registry.find_by_severity(ErrorSeverity.FATAL)
    assert len(fatal_codes) >= 1
    print(f"致命错误数量: {len(fatal_codes)}")
    
    # 测试列出所有
    all_codes = registry.list_all()
    assert len(all_codes) >= 20  # 至少有20个内置错误
    print(f"总错误码数量: {len(all_codes)}")
    
    # 测试注册新错误码
    new_code = ErrorCode(
        code="TST_001",
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.INFO,
        message_template="Test error: {detail}",
        recoverable=True,
        description="测试错误",
        suggested_action="无需操作"
    )
    registry.register(new_code)
    assert registry.get("TST_001") is not None
    print("注册新错误码 TST_001: 成功")
    
    # 测试重复注册
    try:
        registry.register(new_code)
        assert False, "应该抛出异常"
    except ValueError as e:
        print(f"重复注册正确抛出异常: {e}")
    
    print("\n错误注册表测试通过!")
    return True


def test_agent_error():
    """测试错误实例创建"""
    print_section("错误实例创建")
    
    # 使用快捷函数创建
    error = create_error(
        "VAL_003",
        source="test_module",
        trace_id="trace-123",
        field="score",
        value=150,
        min=0,
        max=100
    )
    
    assert error.error_code.code == "VAL_003"
    assert error.source == "test_module"
    assert error.trace_id == "trace-123"
    assert error.is_recoverable() == True
    assert error.is_fatal() == False
    assert "score" in error.message
    assert "150" in error.message
    print(f"错误消息: {error.message}")
    print(f"来源: {error.source}")
    print(f"可恢复: {error.is_recoverable()}")
    print(f"严重级别数值: {error.get_severity_level()}")
    
    # 测试 to_dict
    d = error.to_dict()
    assert d["error_code"] == "VAL_003"
    assert d["source"] == "test_module"
    assert d["trace_id"] == "trace-123"
    assert "context" in d
    print(f"字典表示包含上下文: {d['context']}")
    
    print("\n错误实例测试通过!")
    return True


def test_error_chain():
    """测试错误链"""
    print_section("错误链")
    
    # 创建根错误
    root_error = create_error(
        "SYS_003",
        source="module_loader",
        module_name="predictor_v2"
    )
    
    # 创建派生错误
    derived_error = AgentError(
        error_code=LOG_PREDICTION_FAILED,
        message="Prediction failed because module not found",
        source="predictor",
        trace_id="trace-456",
        caused_by=root_error
    )
    
    assert derived_error.caused_by is not None
    assert derived_error.caused_by.error_code.code == "SYS_003"
    
    d = derived_error.to_dict()
    assert "caused_by" in d
    assert d["caused_by"]["error_code"] == "SYS_003"
    
    print(f"派生错误: {derived_error.message}")
    print(f"根错误: {derived_error.caused_by.message}")
    print(f"错误链字典包含 caused_by: True")
    
    print("\n错误链测试通过!")
    return True


def test_unknown_error_code():
    """测试未知错误码处理"""
    print_section("未知错误码处理")
    
    error = create_error(
        "UNKNOWN_999",
        source="test",
        detail="something went wrong"
    )
    
    # 未知错误码应该回退到 SYS_001
    assert error.error_code.code == "SYS_001"
    assert "Unknown error code" in error.message
    assert "UNKNOWN_999" in error.message
    print(f"未知错误码回退到: {error.error_code.code}")
    print(f"消息: {error.message}")
    
    print("\n未知错误码测试通过!")
    return True


def test_exception_classes():
    """测试异常类"""
    print_section("异常类")
    
    # 创建错误
    error = create_error(
        "VAL_002",
        source="validator",
        field="name"
    )
    
    # 创建异常
    exc = AgentException(error)
    
    assert str(exc) == error.message
    assert exc.error is error
    assert exc.is_recoverable() == True
    
    # 测试捕获
    try:
        raise exc
    except AgentException as caught:
        print(f"捕获到异常: {caught}")
        assert caught.error.error_code.code == "VAL_002"
    
    # 测试子类
    val_error = create_error("VAL_001", source="test", field="x", expected="int", actual="str")
    val_exc = ValidationException(val_error)
    
    try:
        raise val_exc
    except AgentException as caught:
        # 子类可以被父类捕获
        print(f"ValidationException 被 AgentException 捕获: True")
    
    # 测试 to_dict
    d = exc.to_dict()
    assert d["error_code"] == "VAL_002"
    print(f"异常字典表示: {d}")
    
    print("\n异常类测试通过!")
    return True


def test_error_severity_levels():
    """测试严重级别比较"""
    print_section("严重级别比较")
    
    debug_error = AgentError(
        error_code=ErrorCode(
            code="TST_D01", category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.DEBUG, message_template="debug",
            recoverable=True, description="d", suggested_action="a"
        ),
        message="debug"
    )
    
    fatal_error = AgentError(
        error_code=ErrorCode(
            code="TST_F01", category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.FATAL, message_template="fatal",
            recoverable=False, description="f", suggested_action="a"
        ),
        message="fatal"
    )
    
    assert debug_error.get_severity_level() == 0
    assert fatal_error.get_severity_level() == 5
    assert debug_error.get_severity_level() < fatal_error.get_severity_level()
    
    print(f"DEBUG 级别: {debug_error.get_severity_level()}")
    print(f"FATAL 级别: {fatal_error.get_severity_level()}")
    print(f"DEBUG < FATAL: True")
    
    print("\n严重级别比较测试通过!")
    return True


def test_documentation_generation():
    """测试文档生成"""
    print_section("文档生成")
    
    registry = get_error_registry()
    doc = registry.to_documentation()
    
    assert "# 错误码参考文档" in doc
    assert "| 错误码 |" in doc
    assert "VAL_001" in doc
    assert "SYS_001" in doc
    
    # 检查是否包含表格行
    lines = doc.split("\n")
    table_lines = [l for l in lines if l.startswith("|") and "SYS" in l or "VAL" in l]
    assert len(table_lines) > 0
    
    print(f"文档长度: {len(doc)} 字符")
    print(f"文档前200字符:\n{doc[:200]}...")
    
    print("\n文档生成测试通过!")
    return True


def test_all_categories_present():
    """测试所有错误分类都有代表"""
    print_section("错误分类覆盖")
    
    registry = get_error_registry()
    
    categories = [
        ErrorCategory.SYSTEM,
        ErrorCategory.VALIDATION,
        ErrorCategory.RESOURCE,
        ErrorCategory.INTERFACE,
        ErrorCategory.CONFIG,
        ErrorCategory.LOGIC,
        ErrorCategory.SECURITY,
    ]
    
    for cat in categories:
        codes = registry.find_by_category(cat)
        assert len(codes) > 0, f"分类 {cat.value} 没有错误码"
        print(f"分类 {cat.value}: {len(codes)} 个错误码")
    
    print("\n错误分类覆盖测试通过!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("阶段24: 错误码标准化 — 验证测试")
    print("="*60)
    
    tests = [
        test_error_code_format,
        test_error_registry,
        test_agent_error,
        test_error_chain,
        test_unknown_error_code,
        test_exception_classes,
        test_error_severity_levels,
        test_documentation_generation,
        test_all_categories_present,
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
