"""
阶段27: 配置Schema定义 — 验证测试

验证目标:
1. 配置项类型检查正确
2. 约束验证正确（范围、正则、非空）
3. Schema验证完整配置
4. 默认值自动应用
5. 配置管理器可注册、设置、获取
6. 配置变更可监听
7. 子配置段支持
"""

import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.config_schema import (
    ConfigValueType, ConfigItem, ConfigSchema, ConfigManager,
    ConfigConstraint, RangeConstraint, RegexConstraint, NonEmptyConstraint,
    create_system_config_schema, create_predictor_config_schema,
    create_drive_engine_config_schema,
)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print('='*60)


def test_config_item_type_validation():
    """测试配置项类型验证"""
    print_section("配置项类型验证")
    
    # 整数
    int_item = ConfigItem("port", ConfigValueType.INTEGER, 8080, "Server port")
    assert int_item.validate(9090) == []
    assert len(int_item.validate("9090")) > 0  # 字符串不是整数
    assert len(int_item.validate(3.14)) > 0    # 浮点不是整数
    assert len(int_item.validate(True)) > 0    # bool不是整数
    print("整数类型: 通过")
    
    # 浮点数
    float_item = ConfigItem("rate", ConfigValueType.FLOAT, 0.5, "Rate")
    assert float_item.validate(0.8) == []
    assert float_item.validate(1) == []        # 整数可接受
    assert len(float_item.validate("0.8")) > 0
    print("浮点类型: 通过")
    
    # 布尔
    bool_item = ConfigItem("enabled", ConfigValueType.BOOLEAN, True, "Enable flag")
    assert bool_item.validate(False) == []
    assert len(bool_item.validate("true")) > 0
    assert len(bool_item.validate(1)) > 0      # 整数不是bool
    print("布尔类型: 通过")
    
    # 枚举
    enum_item = ConfigItem("level", ConfigValueType.ENUM, "INFO", "Log level",
                           allowed_values=["DEBUG", "INFO", "WARNING"])
    assert enum_item.validate("DEBUG") == []
    assert len(enum_item.validate("TRACE")) > 0
    print("枚举类型: 通过")
    
    print("\n配置项类型验证测试通过!")
    return True


def test_config_constraints():
    """测试配置约束"""
    print_section("配置约束")
    
    # 范围约束
    item = ConfigItem("workers", ConfigValueType.INTEGER, 4, "Workers",
                      constraints=[RangeConstraint(1, 10)])
    assert item.validate(5) == []
    assert len(item.validate(0)) > 0
    assert len(item.validate(11)) > 0
    print("范围约束: 通过")
    
    # 正则约束
    item2 = ConfigItem("email", ConfigValueType.STRING, "", "Email",
                       constraints=[RegexConstraint(r"^[\w\.-]+@[\w\.-]+\.\w+$")])
    assert item2.validate("test@example.com") == []
    assert len(item2.validate("invalid")) > 0
    print("正则约束: 通过")
    
    # 非空约束
    item3 = ConfigItem("name", ConfigValueType.STRING, "", "Name",
                       constraints=[NonEmptyConstraint()])
    assert item3.validate("hello") == []
    assert len(item3.validate("")) > 0
    print("非空约束: 通过")
    
    print("\n配置约束测试通过!")
    return True


def test_config_schema_validation():
    """测试Schema验证"""
    print_section("Schema验证")
    
    schema = ConfigSchema("test", "Test schema")
    schema.add_item(ConfigItem("host", ConfigValueType.STRING, "localhost", "Host", required=True))
    schema.add_item(ConfigItem("port", ConfigValueType.INTEGER, 8080, "Port",
                               constraints=[RangeConstraint(1, 65535)]))
    schema.add_item(ConfigItem("debug", ConfigValueType.BOOLEAN, False, "Debug mode"))
    
    # 有效配置
    valid_config = {"host": "0.0.0.0", "port": 9090, "debug": True}
    errors = schema.validate(valid_config)
    assert errors == []
    print(f"有效配置: 通过")
    
    # 缺少必填项
    invalid_config = {"port": 9090}
    errors = schema.validate(invalid_config)
    assert any("required" in e for e in errors)
    print(f"缺少必填项: {errors}")
    
    # 类型错误
    type_error_config = {"host": "localhost", "port": "9090"}
    errors = schema.validate(type_error_config)
    assert any("expected" in e for e in errors)
    print(f"类型错误: {errors}")
    
    # 约束违反
    range_error_config = {"host": "localhost", "port": 99999}
    errors = schema.validate(range_error_config)
    assert any("range" in e.lower() or "Constraint" in e for e in errors)
    print(f"约束违反: {errors}")
    
    print("\nSchema验证测试通过!")
    return True


def test_default_values():
    """测试默认值应用"""
    print_section("默认值应用")
    
    schema = ConfigSchema("test", "Test schema")
    schema.add_item(ConfigItem("name", ConfigValueType.STRING, "default_name", "Name"))
    schema.add_item(ConfigItem("count", ConfigValueType.INTEGER, 10, "Count"))
    
    # 部分配置
    config = {"name": "custom"}
    full_config = schema.apply_defaults(config)
    
    assert full_config["name"] == "custom"  # 保留提供的值
    assert full_config["count"] == 10       # 应用默认值
    print(f"应用默认值后: {full_config}")
    
    # 空配置
    empty_config = schema.apply_defaults({})
    assert empty_config["name"] == "default_name"
    assert empty_config["count"] == 10
    print(f"空配置默认值: {empty_config}")
    
    print("\n默认值应用测试通过!")
    return True


def test_config_manager():
    """测试配置管理器"""
    print_section("配置管理器")
    
    manager = ConfigManager()
    schema = create_system_config_schema()
    manager.register_schema("system", schema)
    
    # 设置有效配置
    errors = manager.set_config("system", {"log_level": "DEBUG", "max_workers": 8})
    assert errors == []
    print(f"设置有效配置: 通过")
    
    # 获取配置
    config = manager.get_config("system")
    assert config["log_level"] == "DEBUG"
    assert config["max_workers"] == 8
    assert config["enable_monitoring"] == True  # 默认值
    print(f"获取配置: {config}")
    
    # 获取单个值
    assert manager.get_value("system", "log_level") == "DEBUG"
    assert manager.get_value("system", "enable_monitoring") == True  # 默认值
    print(f"获取单个值: log_level={manager.get_value('system', 'log_level')}")
    
    # 设置无效配置
    errors = manager.set_config("system", {"log_level": "INVALID", "max_workers": 100})
    assert len(errors) > 0
    print(f"设置无效配置: {errors}")
    
    # 不存在的Schema
    errors = manager.set_config("nonexistent", {})
    assert len(errors) > 0
    print(f"不存在的Schema: {errors}")
    
    print("\n配置管理器测试通过!")
    return True


def test_config_change_listener():
    """测试配置变更监听"""
    print_section("配置变更监听")
    
    manager = ConfigManager()
    schema = create_predictor_config_schema()
    manager.register_schema("predictor", schema)
    
    changes = []
    
    def listener(schema_name, key, old_val, new_val):
        changes.append((schema_name, key, old_val, new_val))
    
    manager.add_change_listener(listener)
    
    # 初始设置（也会触发变更通知，因为内部从空字典变为有值）
    manager.set_config("predictor", {"learning_rate": 0.01})
    initial_changes = len(changes)
    print(f"初始设置触发变更数: {initial_changes}")
    
    # 修改值
    manager.set_config("predictor", {"learning_rate": 0.05})
    assert len(changes) > initial_changes
    # 找到learning_rate的变更
    lr_changes = [c for c in changes if c[1] == "learning_rate" and c[3] == 0.05]
    assert len(lr_changes) >= 1
    print(f"检测到的变更: {changes}")
    
    print("\n配置变更监听测试通过!")
    return True


def test_nested_schema():
    """测试嵌套Schema"""
    print_section("嵌套Schema")
    
    inner = ConfigSchema("inner", "Inner schema")
    inner.add_item(ConfigItem("value", ConfigValueType.INTEGER, 0, "Value"))
    
    outer = ConfigSchema("outer", "Outer schema")
    outer.add_item(ConfigItem("name", ConfigValueType.STRING, "test", "Name"))
    outer.add_section("nested", inner)
    
    # 验证嵌套配置
    config = {"name": "hello", "nested": {"value": 42}}
    errors = outer.validate(config)
    assert errors == []
    print(f"嵌套配置验证: 通过")
    
    # 应用默认值
    partial = {"name": "hello"}
    full = outer.apply_defaults(partial)
    assert full["nested"]["value"] == 0
    print(f"嵌套默认值: {full}")
    
    # 获取嵌套项定义
    item = outer.get_item("nested.value")
    assert item is not None
    assert item.key == "value"
    print(f"获取嵌套项: {item.key}")
    
    print("\n嵌套Schema测试通过!")
    return True


def test_predefined_schemas():
    """测试预定义Schema"""
    print_section("预定义Schema")
    
    system = create_system_config_schema()
    assert system.get_item("log_level") is not None
    assert system.get_item("max_workers") is not None
    print(f"系统Schema项数: {len(system._items)}")
    
    predictor = create_predictor_config_schema()
    assert predictor.get_item("learning_rate") is not None
    assert predictor.get_item("model_type") is not None
    print(f"预测器Schema项数: {len(predictor._items)}")
    
    drive = create_drive_engine_config_schema()
    assert drive.get_item("safe_threshold") is not None
    assert drive.get_item("gain_threshold") is not None
    assert drive.get_item("eff_threshold") is not None
    print(f"驱力引擎Schema项数: {len(drive._items)}")
    
    # 验证Schema文档生成
    doc = system.to_dict()
    assert "name" in doc
    assert "items" in doc
    print(f"Schema文档包含: {list(doc.keys())}")
    
    print("\n预定义Schema测试通过!")
    return True


def test_secret_config():
    """测试敏感配置脱敏"""
    print_section("敏感配置脱敏")
    
    item = ConfigItem("api_key", ConfigValueType.STRING, "secret123", "API Key", secret=True)
    doc = item.to_dict()
    assert doc["default"] == "***"
    assert item.get_default() == "secret123"  # 实际值不受影响
    print(f"脱敏后的默认值: {doc['default']}")
    print(f"实际默认值: {item.get_default()}")
    
    print("\n敏感配置脱敏测试通过!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("阶段27: 配置Schema定义 — 验证测试")
    print("="*60)
    
    tests = [
        test_config_item_type_validation,
        test_config_constraints,
        test_config_schema_validation,
        test_default_values,
        test_config_manager,
        test_config_change_listener,
        test_nested_schema,
        test_predefined_schemas,
        test_secret_config,
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
