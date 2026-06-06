"""
阶段27: 配置Schema定义

第一性原理:
1. 配置是系统的基因，必须在启动时就确定其结构和约束
2. 没有Schema的配置就像没有类型的变量，错误只能在运行时暴露
3. 配置变更必须可验证、可追溯、可回滚

设计原则:
- 每个配置项有明确的类型、默认值、约束、文档
- 配置分层：系统级 / 模块级 / 环境级
- 配置变更触发验证和事件
- 支持配置继承和覆盖
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional, Type, Union, Tuple
from enum import Enum, auto
from abc import ABC, abstractmethod
import copy


class ConfigValueType(Enum):
    """配置值类型"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    ENUM = "enum"


@dataclass
class ConfigConstraint:
    """配置约束"""
    name: str
    check: Callable[[Any], bool]
    description: str
    
    def validate(self, value: Any) -> Optional[str]:
        try:
            if not self.check(value):
                return f"Constraint '{self.name}' violated: {self.description}"
        except Exception as e:
            return f"Constraint '{self.name}' check error: {e}"
        return None


@dataclass
class ConfigItem:
    """
    配置项定义
    
    第一性原理：配置项是接口的一部分，必须有明确的契约
    """
    key: str
    value_type: ConfigValueType
    default: Any
    description: str
    required: bool = False
    constraints: List[ConfigConstraint] = field(default_factory=list)
    allowed_values: Optional[List[Any]] = None
    env_override: bool = True  # 是否允许环境变量覆盖
    secret: bool = False  # 是否为敏感信息（日志中脱敏）
    
    def validate(self, value: Any) -> List[str]:
        """验证值是否符合配置项定义"""
        errors = []
        
        # 类型检查
        type_valid = self._check_type(value)
        if not type_valid:
            errors.append(
                f"Config '{self.key}': expected {self.value_type.value}, "
                f"got {type(value).__name__}"
            )
            return errors
        
        # 允许值检查
        if self.allowed_values is not None and value not in self.allowed_values:
            errors.append(
                f"Config '{self.key}': value {value} not in allowed values {self.allowed_values}"
            )
        
        # 约束检查
        for constraint in self.constraints:
            error = constraint.validate(value)
            if error:
                errors.append(error)
        
        return errors
    
    def _check_type(self, value: Any) -> bool:
        """检查值类型"""
        if self.value_type == ConfigValueType.STRING:
            return isinstance(value, str)
        elif self.value_type == ConfigValueType.INTEGER:
            return isinstance(value, int) and not isinstance(value, bool)
        elif self.value_type == ConfigValueType.FLOAT:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        elif self.value_type == ConfigValueType.BOOLEAN:
            return isinstance(value, bool)
        elif self.value_type == ConfigValueType.LIST:
            return isinstance(value, list)
        elif self.value_type == ConfigValueType.DICT:
            return isinstance(value, dict)
        elif self.value_type == ConfigValueType.ENUM:
            return self.allowed_values is not None and value in self.allowed_values
        return False
    
    def get_default(self) -> Any:
        """获取默认值（深拷贝防止修改）"""
        return copy.deepcopy(self.default)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "key": self.key,
            "type": self.value_type.value,
            "default": self.default if not self.secret else "***",
            "description": self.description,
            "required": self.required,
            "env_override": self.env_override,
        }
        if self.allowed_values:
            result["allowed_values"] = self.allowed_values
        return result


# ============================================================
# 预定义约束
# ============================================================

def RangeConstraint(min_val: Optional[float] = None, max_val: Optional[float] = None) -> ConfigConstraint:
    """范围约束"""
    desc = []
    if min_val is not None:
        desc.append(f">= {min_val}")
    if max_val is not None:
        desc.append(f"<= {max_val}")
    
    def check(value):
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True
    
    return ConfigConstraint(
        name="range",
        check=check,
        description=f"value must be {' and '.join(desc)}"
    )


def RegexConstraint(pattern: str) -> ConfigConstraint:
    """正则约束"""
    import re
    compiled = re.compile(pattern)
    return ConfigConstraint(
        name="regex",
        check=lambda v: bool(compiled.match(str(v))),
        description=f"value must match pattern: {pattern}"
    )


def NonEmptyConstraint() -> ConfigConstraint:
    """非空约束"""
    return ConfigConstraint(
        name="non_empty",
        check=lambda v: len(v) > 0 if hasattr(v, '__len__') else v is not None,
        description="value must not be empty"
    )


# ============================================================
# 配置Schema
# ============================================================

class ConfigSchema:
    """
    配置Schema
    
    定义一组配置项的结构和约束
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._items: Dict[str, ConfigItem] = {}
        self._sections: Dict[str, 'ConfigSchema'] = {}
    
    def add_item(self, item: ConfigItem) -> 'ConfigSchema':
        """添加配置项"""
        self._items[item.key] = item
        return self
    
    def add_section(self, section_name: str, schema: 'ConfigSchema') -> 'ConfigSchema':
        """添加子配置段"""
        self._sections[section_name] = schema
        return self
    
    def get_item(self, key: str) -> Optional[ConfigItem]:
        """获取配置项"""
        # 支持点号路径，如 "section.subsection.key"
        parts = key.split(".")
        if len(parts) == 1:
            return self._items.get(key)
        
        section = self._sections.get(parts[0])
        if section:
            return section.get_item(".".join(parts[1:]))
        return None
    
    def validate(self, config: Dict[str, Any]) -> List[str]:
        """
        验证配置字典是否符合Schema
        
        Returns:
            错误列表，空列表表示验证通过
        """
        errors = []
        
        # 检查必填项
        for key, item in self._items.items():
            if item.required and key not in config:
                errors.append(f"Config '{key}' is required but missing")
        
        # 验证提供的值
        for key, value in config.items():
            if key in self._items:
                item_errors = self._items[key].validate(value)
                errors.extend(item_errors)
            elif "." in key:
                # 可能是子配置段的路径
                item = self.get_item(key)
                if item:
                    item_errors = item.validate(value)
                    errors.extend(item_errors)
        
        # 验证子配置段
        for section_name, section_schema in self._sections.items():
            if section_name in config:
                section_errors = section_schema.validate(config[section_name])
                errors.extend(section_errors)
        
        return errors
    
    def apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """为缺失的配置项应用默认值"""
        result = copy.deepcopy(config)
        
        for key, item in self._items.items():
            if key not in result:
                result[key] = item.get_default()
        
        # 递归处理子配置段
        for section_name, section_schema in self._sections.items():
            if section_name not in result:
                result[section_name] = {}
            result[section_name] = section_schema.apply_defaults(result[section_name])
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """生成Schema文档"""
        return {
            "name": self.name,
            "description": self.description,
            "items": {k: v.to_dict() for k, v in self._items.items()},
            "sections": {k: v.to_dict() for k, v in self._sections.items()},
        }


# ============================================================
# 配置管理器
# ============================================================

class ConfigManager:
    """
    配置管理器
    
    第一性原理：配置是系统的基因，管理配置就是管理系统行为
    """
    
    def __init__(self):
        self._schemas: Dict[str, ConfigSchema] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._validators: List[Callable[[str, Dict[str, Any]], List[str]]] = []
        self._change_listeners: List[Callable[[str, str, Any, Any], None]] = []
    
    def register_schema(self, name: str, schema: ConfigSchema) -> None:
        """注册配置Schema"""
        self._schemas[name] = schema
        self._configs[name] = {}
    
    def set_config(self, schema_name: str, config: Dict[str, Any]) -> List[str]:
        """
        设置配置
        
        Returns:
            验证错误列表
        """
        schema = self._schemas.get(schema_name)
        if schema is None:
            return [f"Schema '{schema_name}' not found"]
        
        # 应用默认值
        config_with_defaults = schema.apply_defaults(config)
        
        # 验证
        errors = schema.validate(config_with_defaults)
        
        # 运行自定义验证器
        for validator in self._validators:
            try:
                custom_errors = validator(schema_name, config_with_defaults)
                errors.extend(custom_errors)
            except Exception as e:
                errors.append(f"Custom validator error: {e}")
        
        if errors:
            return errors
        
        # 记录变更
        old_config = self._configs.get(schema_name, {})
        self._configs[schema_name] = config_with_defaults
        
        # 通知监听器
        self._notify_changes(schema_name, old_config, config_with_defaults)
        
        return []
    
    def get_config(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """获取配置"""
        return copy.deepcopy(self._configs.get(schema_name))
    
    def get_value(self, schema_name: str, key: str) -> Any:
        """获取单个配置值"""
        config = self._configs.get(schema_name, {})
        parts = key.split(".")
        
        current = config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                # 尝试获取默认值
                schema = self._schemas.get(schema_name)
                if schema:
                    item = schema.get_item(key)
                    if item:
                        return item.get_default()
                return None
        
        return copy.deepcopy(current)
    
    def add_validator(self, validator: Callable[[str, Dict[str, Any]], List[str]]) -> None:
        """添加自定义验证器"""
        self._validators.append(validator)
    
    def add_change_listener(self, listener: Callable[[str, str, Any, Any], None]) -> None:
        """
        添加配置变更监听器
        
        监听器签名: listener(schema_name, key, old_value, new_value)
        """
        self._change_listeners.append(listener)
    
    def _notify_changes(self, schema_name: str, old: Dict[str, Any], new: Dict[str, Any]) -> None:
        """通知配置变更"""
        # 简单比较顶层键
        all_keys = set(old.keys()) | set(new.keys())
        
        for key in all_keys:
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val != new_val:
                for listener in self._change_listeners:
                    try:
                        listener(schema_name, key, old_val, new_val)
                    except Exception:
                        pass
    
    def get_schema_doc(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """获取Schema文档"""
        schema = self._schemas.get(schema_name)
        if schema:
            return schema.to_dict()
        return None


# ============================================================
# 预定义系统配置Schema
# ============================================================

def create_system_config_schema() -> ConfigSchema:
    """创建系统级配置Schema"""
    schema = ConfigSchema("system", "System-wide configuration")
    
    schema.add_item(ConfigItem(
        key="log_level",
        value_type=ConfigValueType.ENUM,
        default="INFO",
        description="Logging level",
        allowed_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )).add_item(ConfigItem(
        key="max_workers",
        value_type=ConfigValueType.INTEGER,
        default=4,
        description="Maximum number of worker threads",
        constraints=[RangeConstraint(1, 64)],
    )).add_item(ConfigItem(
        key="enable_monitoring",
        value_type=ConfigValueType.BOOLEAN,
        default=True,
        description="Enable system monitoring",
    ))
    
    return schema


def create_predictor_config_schema() -> ConfigSchema:
    """创建预测模块配置Schema"""
    schema = ConfigSchema("predictor", "Predictor module configuration")
    
    schema.add_item(ConfigItem(
        key="learning_rate",
        value_type=ConfigValueType.FLOAT,
        default=0.01,
        description="Learning rate for model updates",
        constraints=[RangeConstraint(0.0001, 1.0)],
    )).add_item(ConfigItem(
        key="batch_size",
        value_type=ConfigValueType.INTEGER,
        default=32,
        description="Training batch size",
        constraints=[RangeConstraint(1, 1024)],
    )).add_item(ConfigItem(
        key="model_type",
        value_type=ConfigValueType.ENUM,
        default="simple",
        description="Type of prediction model",
        allowed_values=["simple", "gru", "lstm", "transformer"],
    ))
    
    return schema


def create_drive_engine_config_schema() -> ConfigSchema:
    """创建驱力引擎配置Schema"""
    schema = ConfigSchema("drive_engine", "Drive engine configuration")
    
    schema.add_item(ConfigItem(
        key="safe_threshold",
        value_type=ConfigValueType.FLOAT,
        default=0.3,
        description="Safety threshold for safe drive",
        constraints=[RangeConstraint(0.0, 1.0)],
    )).add_item(ConfigItem(
        key="gain_threshold",
        value_type=ConfigValueType.FLOAT,
        default=0.5,
        description="Gain threshold for gain drive",
        constraints=[RangeConstraint(0.0, 1.0)],
    )).add_item(ConfigItem(
        key="eff_threshold",
        value_type=ConfigValueType.FLOAT,
        default=0.2,
        description="Efficiency threshold for eff drive",
        constraints=[RangeConstraint(0.0, 1.0)],
    ))
    
    return schema
