"""
阶段42: 插件系统接口标准化

第一性原理:
1. 系统功能不可能一次性完备，必须允许外部扩展
2. 插件是独立的生命周期单元：加载->初始化->运行->卸载
3. 插件之间必须解耦，通过标准接口交互

设计原则:
- 插件接口定义：标准入口点和生命周期钩子
- 插件注册表：名称->插件实例的映射
- 依赖管理：插件可以声明依赖，系统按拓扑顺序初始化
- 热插拔：支持运行时加载和卸载
- 隔离性：插件异常不影响主系统
"""

import importlib
import inspect
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from enum import Enum


class PluginState(Enum):
    """插件状态"""
    REGISTERED = "registered"    # 已注册
    LOADING = "loading"          # 加载中
    ACTIVE = "active"            # 运行中
    FAILED = "failed"            # 失败
    UNLOADING = "unloading"      # 卸载中
    UNLOADED = "unloaded"        # 已卸载


@dataclass
class PluginInfo:
    """插件元信息"""
    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)


# ============================================================
# 插件接口（抽象基类）
# ============================================================

class Plugin(ABC):
    """
    插件接口

    第一性原理：插件必须有明确的生命周期和标准化的交互方式
    """

    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """插件元信息"""
        pass

    def initialize(self, context: Dict[str, Any]) -> bool:
        """
        初始化插件

        Args:
            context: 系统上下文，包含配置、服务接口等

        Returns:
            是否初始化成功
        """
        return True

    def start(self) -> bool:
        """启动插件"""
        return True

    def stop(self) -> bool:
        """停止插件"""
        return True

    def unload(self) -> bool:
        """卸载插件"""
        return True

    def on_event(self, event_type: str, payload: Any) -> Optional[Any]:
        """
        接收事件

        Args:
            event_type: 事件类型
            payload: 事件数据

        Returns:
            可选的响应数据
        """
        return None


# ============================================================
# 插件注册表
# ============================================================

class PluginRegistry:
    """
    插件注册表

    管理所有已注册插件的状态和实例
    """

    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._states: Dict[str, PluginState] = {}
        self._errors: Dict[str, Exception] = {}
        self._lock = threading.Lock()
        self._hooks: Dict[str, List[str]] = {}  # hook_name -> plugin_names

    def register(self, plugin: Plugin) -> bool:
        """注册插件"""
        name = plugin.info.name
        with self._lock:
            if name in self._plugins:
                raise ValueError(f"Plugin '{name}' already registered")
            self._plugins[name] = plugin
            self._states[name] = PluginState.REGISTERED
            self._errors[name] = None

            # 注册钩子
            for hook in plugin.info.hooks:
                if hook not in self._hooks:
                    self._hooks[hook] = []
                self._hooks[hook].append(name)

            return True

    def unregister(self, name: str) -> bool:
        """注销插件"""
        with self._lock:
            if name not in self._plugins:
                return False
            plugin = self._plugins[name]

            # 从钩子中移除
            for hook in plugin.info.hooks:
                if hook in self._hooks and name in self._hooks[hook]:
                    self._hooks[hook].remove(name)

            del self._plugins[name]
            del self._states[name]
            del self._errors[name]
            return True

    def get(self, name: str) -> Optional[Plugin]:
        """获取插件实例"""
        with self._lock:
            return self._plugins.get(name)

    def get_state(self, name: str) -> Optional[PluginState]:
        """获取插件状态"""
        with self._lock:
            return self._states.get(name)

    def set_state(self, name: str, state: PluginState) -> None:
        """设置插件状态"""
        with self._lock:
            if name in self._states:
                self._states[name] = state

    def set_error(self, name: str, error: Exception) -> None:
        """设置插件错误"""
        with self._lock:
            self._errors[name] = error
            self._states[name] = PluginState.FAILED

    def list_plugins(self) -> Dict[str, PluginState]:
        """列出所有插件及其状态"""
        with self._lock:
            return dict(self._states)

    def get_plugins_for_hook(self, hook: str) -> List[str]:
        """获取订阅某钩子的插件列表"""
        with self._lock:
            return list(self._hooks.get(hook, []))

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            state_counts = {}
            for state in self._states.values():
                state_counts[state.value] = state_counts.get(state.value, 0) + 1
            return {
                "total_plugins": len(self._plugins),
                "state_counts": state_counts,
                "hooks": {k: len(v) for k, v in self._hooks.items()},
            }


# ============================================================
# 插件管理器
# ============================================================

class PluginManager:
    """
    插件管理器

    负责插件的完整生命周期管理和依赖解析
    """

    def __init__(self):
        self.registry = PluginRegistry()
        self._context: Dict[str, Any] = {}

    def set_context(self, context: Dict[str, Any]) -> None:
        """设置系统上下文"""
        self._context = context

    def load(self, plugin: Plugin) -> bool:
        """
        加载并初始化插件

        自动解析和加载依赖
        """
        info = plugin.info
        name = info.name

        # 检查依赖
        for dep in info.dependencies:
            dep_plugin = self.registry.get(dep)
            if dep_plugin is None:
                self.registry.register(plugin)
                self.registry.set_error(name, RuntimeError(f"Dependency '{dep}' not found"))
                return False
            dep_state = self.registry.get_state(dep)
            if dep_state != PluginState.ACTIVE:
                self.registry.register(plugin)
                self.registry.set_error(name, RuntimeError(f"Dependency '{dep}' not active"))
                return False

        # 注册
        self.registry.register(plugin)
        self.registry.set_state(name, PluginState.LOADING)

        try:
            # 初始化
            if not plugin.initialize(self._context):
                self.registry.set_error(name, RuntimeError("Initialize returned False"))
                return False

            # 启动
            if not plugin.start():
                self.registry.set_error(name, RuntimeError("Start returned False"))
                return False

            self.registry.set_state(name, PluginState.ACTIVE)
            return True
        except Exception as e:
            self.registry.set_error(name, e)
            return False

    def unload(self, name: str) -> bool:
        """卸载插件"""
        plugin = self.registry.get(name)
        if plugin is None:
            return False

        self.registry.set_state(name, PluginState.UNLOADING)
        try:
            plugin.stop()
            plugin.unload()
            self.registry.set_state(name, PluginState.UNLOADED)
            self.registry.unregister(name)
            return True
        except Exception as e:
            self.registry.set_error(name, e)
            return False

    def emit(self, hook: str, payload: Any) -> List[Any]:
        """
        触发钩子，调用所有订阅的插件

        Returns:
            所有插件的响应列表
        """
        responses = []
        plugin_names = self.registry.get_plugins_for_hook(hook)

        for name in plugin_names:
            plugin = self.registry.get(name)
            if plugin is None:
                continue
            if self.registry.get_state(name) != PluginState.ACTIVE:
                continue

            try:
                response = plugin.on_event(hook, payload)
                if response is not None:
                    responses.append(response)
            except Exception:
                # 插件异常隔离
                pass

        return responses

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.registry.get_stats()


# ============================================================
# 便捷函数
# ============================================================

def create_plugin_manager() -> PluginManager:
    """创建插件管理器"""
    return PluginManager()


# ============================================================
# 阶段135: 生产级插件系统扩展
# ============================================================
#
# 第一性原理:
# 1. 可扩展性 — 系统必须允许第三方在不修改核心代码的情况下添加功能
# 2. 隔离性 — 插件故障不能传播到宿主系统
# 3. 可发现性 — 插件应能被自动发现和加载
# 4. 可配置性 — 每个插件应有独立的配置和配置校验
# 5. 可观测性 — 插件状态、健康度、指标应可被监控
# 6. 热更新 — 运行时重载插件无需重启系统
#
# 新增能力:
# - PluginManifest: 扩展元信息（许可证、主页、配置schema、优先级）
# - PluginConfig: 插件配置管理（schema校验、动态更新）
# - PluginContext: 受控系统访问（服务注册、日志、事件发布）
# - PluginLoader: 从目录/文件/模块发现和加载插件
# - PluginEventBus: 发布/订阅事件总线
# - PluginHealthMonitor: 插件健康监控
# - EnhancedPluginManager: 增强管理器（热重载、发现、健康检查）
# ============================================================


class PluginPriority(Enum):
    """插件优先级（影响钩子调用顺序）"""
    LOWEST = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    HIGHEST = 4


class PluginHealthStatus(Enum):
    """插件健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class PluginManifest:
    """
    插件清单 — 扩展的元信息

    第一性原理：插件的自描述信息必须完整，使系统能自动校验兼容性和配置
    """
    name: str
    version: str
    description: str = ""
    author: str = ""
    license: str = ""
    homepage: str = ""
    min_system_version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    priority: PluginPriority = PluginPriority.NORMAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "homepage": self.homepage,
            "min_system_version": self.min_system_version,
            "dependencies": list(self.dependencies),
            "optional_dependencies": list(self.optional_dependencies),
            "hooks": list(self.hooks),
            "config_schema": dict(self.config_schema),
            "priority": self.priority.name,
        }

    @staticmethod
    def from_plugin_info(info: "PluginInfo") -> "PluginManifest":
        """从旧版PluginInfo转换"""
        return PluginManifest(
            name=info.name,
            version=info.version,
            description=info.description,
            author=info.author,
            dependencies=list(info.dependencies),
            hooks=list(info.hooks),
        )


def _parse_version(version_str: str) -> tuple:
    """解析语义化版本号为可比较的元组"""
    parts = []
    for part in version_str.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            # 非数字部分取0
            parts.append(0)
    return tuple(parts)


class VersionChecker:
    """版本兼容性检查器"""

    @staticmethod
    def is_compatible(plugin_version: str, min_system_version: str, system_version: str = "1.0.0") -> bool:
        """
        检查插件是否与系统版本兼容

        第一性原理：版本兼容性是系统稳定性的前提
        """
        try:
            plugin_min = _parse_version(min_system_version)
            sys_ver = _parse_version(system_version)
            return sys_ver >= plugin_min
        except Exception:
            return False

    @staticmethod
    def satisfies_dependency(available_version: str, required_version: str) -> bool:
        """检查可用版本是否满足依赖要求"""
        try:
            return _parse_version(available_version) >= _parse_version(required_version)
        except Exception:
            return False


class PluginConfig:
    """
    插件配置管理

    第一性原理：配置是插件行为的声明式控制，必须有schema校验
    """

    def __init__(
        self,
        schema: Optional[Dict[str, Any]] = None,
        values: Optional[Dict[str, Any]] = None,
    ):
        self._schema = schema or {}
        self._values: Dict[str, Any] = dict(values) if values else {}
        self._lock = threading.RLock()
        self._listeners: List[Callable[[str, Any, Any], None]] = []

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        with self._lock:
            return self._values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置值（触发监听器）"""
        with self._lock:
            old_value = self._values.get(key)
            self._values[key] = value
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(key, old_value, value)
            except Exception:
                pass

    def update(self, values: Dict[str, Any]) -> None:
        """批量更新配置"""
        with self._lock:
            for key, value in values.items():
                old_value = self._values.get(key)
                self._values[key] = value
                listeners = list(self._listeners)
                for listener in listeners:
                    try:
                        listener(key, old_value, value)
                    except Exception:
                        pass

    def validate(self) -> Tuple[bool, List[str]]:
        """
        根据schema校验配置

        Returns:
            (是否有效, 错误消息列表)
        """
        errors = []
        if not self._schema:
            return True, []

        for key, spec in self._schema.items():
            if spec.get("required", False) and key not in self._values:
                errors.append(f"Missing required config: {key}")
                continue

            if key in self._values:
                value = self._values[key]
                expected_type = spec.get("type")
                if expected_type and not PluginConfig._check_type(value, expected_type):
                    errors.append(f"Config '{key}' expected type {expected_type}, got {type(value).__name__}")

                if "choices" in spec and value not in spec["choices"]:
                    errors.append(f"Config '{key}' must be one of {spec['choices']}")

                if "min" in spec and isinstance(value, (int, float)) and value < spec["min"]:
                    errors.append(f"Config '{key}' must be >= {spec['min']}")

                if "max" in spec and isinstance(value, (int, float)) and value > spec["max"]:
                    errors.append(f"Config '{key}' must be <= {spec['max']}")

        return len(errors) == 0, errors

    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        type_map = {
            "string": str, "str": str,
            "int": int, "integer": int,
            "float": float, "number": (int, float),
            "bool": bool, "boolean": bool,
            "list": list, "array": list,
            "dict": dict, "object": dict,
        }
        python_type = type_map.get(expected_type)
        if python_type is None:
            return True
        # bool是int的子类，需特殊处理
        if expected_type in ("int", "integer") and isinstance(value, bool):
            return False
        return isinstance(value, python_type)

    def on_change(self, listener: Callable[[str, Any, Any], None]) -> None:
        """注册配置变更监听器"""
        with self._lock:
            self._listeners.append(listener)

    def to_dict(self) -> Dict[str, Any]:
        """导出配置"""
        with self._lock:
            return dict(self._values)

    @property
    def schema(self) -> Dict[str, Any]:
        return self._schema


class PluginContext:
    """
    插件上下文 — 提供受控的系统访问

    第一性原理：插件不应直接访问宿主内部，通过上下文提供最小权限接口
    """

    def __init__(
        self,
        plugin_name: str,
        config: PluginConfig,
        services: Optional[Dict[str, Any]] = None,
    ):
        self._plugin_name = plugin_name
        self._config = config
        self._services: Dict[str, Any] = dict(services) if services else {}
        self._lock = threading.RLock()
        self._log_entries: List[Dict[str, Any]] = []
        self._event_publisher: Optional[Callable[[str, Any, str], None]] = None

    @property
    def name(self) -> str:
        return self._plugin_name

    @property
    def config(self) -> PluginConfig:
        return self._config

    def get_service(self, name: str) -> Any:
        """获取系统服务"""
        with self._lock:
            return self._services.get(name)

    def register_service(self, name: str, service: Any) -> None:
        """注册服务供其他插件使用"""
        with self._lock:
            self._services[name] = service

    def unregister_service(self, name: str) -> None:
        """注销服务"""
        with self._lock:
            self._services.pop(name, None)

    def list_services(self) -> List[str]:
        """列出可用服务"""
        with self._lock:
            return list(self._services.keys())

    def log(self, level: str, message: str, **kwargs: Any) -> None:
        """记录日志"""
        entry = {
            "plugin": self._plugin_name,
            "level": level,
            "message": message,
            "timestamp": time.time(),
            "extra": kwargs,
        }
        with self._lock:
            self._log_entries.append(entry)
            if len(self._log_entries) > 1000:
                self._log_entries = self._log_entries[-500:]

    def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取日志"""
        with self._lock:
            return list(self._log_entries[-limit:])

    def set_event_publisher(self, publisher: Callable[[str, Any, str], None]) -> None:
        """设置事件发布器（由管理器注入）"""
        self._event_publisher = publisher

    def emit_event(self, event_type: str, payload: Any) -> None:
        """发布事件"""
        if self._event_publisher:
            self._event_publisher(event_type, payload, self._plugin_name)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_name": self._plugin_name,
            "services": self.list_services(),
            "log_count": len(self._log_entries),
            "config": self._config.to_dict(),
        }


@dataclass
class PluginEvent:
    """插件事件"""
    event_type: str
    source: str
    payload: Any = None
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


class PluginEventBus:
    """
    插件事件总线 — 发布/订阅模式

    第一性原理：插件间解耦通信通过事件总线，而非直接调用
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Tuple[str, Callable]]] = {}
        self._lock = threading.RLock()
        self._event_history: List[PluginEvent] = []
        self._max_history = 1000

    def subscribe(self, event_type: str, handler: Callable, subscriber_name: str = "") -> None:
        """订阅事件"""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append((subscriber_name, handler))

    def unsubscribe(self, event_type: str, handler: Callable) -> bool:
        """取消订阅"""
        with self._lock:
            if event_type not in self._subscribers:
                return False
            subs = self._subscribers[event_type]
            for i, (_, h) in enumerate(subs):
                if h == handler:
                    subs.pop(i)
                    return True
            return False

    def publish(self, event: PluginEvent) -> List[Any]:
        """
        发布事件（同步调用所有订阅者）

        Returns:
            订阅者的响应列表（异常的订阅者返回None）
        """
        responses = []
        with self._lock:
            subs = list(self._subscribers.get(event.event_type, []))
            # 也通知通配符订阅者
            wildcard_subs = list(self._subscribers.get("*", []))
            all_subs = subs + wildcard_subs
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history // 2:]

        for _, handler in all_subs:
            try:
                result = handler(event)
                if result is not None:
                    responses.append(result)
            except Exception:
                responses.append(None)
        return responses

    def publish_simple(self, event_type: str, payload: Any, source: str = "") -> List[Any]:
        """简化发布"""
        event = PluginEvent(event_type=event_type, source=source, payload=payload)
        return self.publish(event)

    def get_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[PluginEvent]:
        """获取事件历史"""
        with self._lock:
            events = list(self._event_history)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "event_types": len(self._subscribers),
                "total_subscribers": sum(len(v) for v in self._subscribers.values()),
                "events_published": len(self._event_history),
                "subscriptions": {k: len(v) for k, v in self._subscribers.items()},
            }

    def clear(self) -> None:
        """清空"""
        with self._lock:
            self._subscribers.clear()
            self._event_history.clear()


@dataclass
class PluginHealthResult:
    """插件健康检查结果"""
    plugin_name: str
    status: PluginHealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_name": self.plugin_name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class PluginLoader:
    """
    插件加载器 — 从目录、文件、模块发现和加载插件

    第一性原理：插件发现应自动化，支持多种来源
    """

    def __init__(self):
        self._search_paths: List[str] = []

    def add_search_path(self, path: str) -> None:
        """添加搜索路径"""
        import os
        if os.path.isdir(path):
            self._search_paths.append(path)

    def discover_directory(self, directory: str) -> List[str]:
        """
        发现目录中的插件模块

        Returns:
            发现的模块路径列表
        """
        import os
        discovered = []
        if not os.path.isdir(directory):
            return discovered
        for entry in os.listdir(directory):
            if entry.endswith(".py") and not entry.startswith("_"):
                file_path = os.path.join(directory, entry)
                discovered.append(file_path)
            elif os.path.isdir(os.path.join(directory, entry)):
                init_file = os.path.join(directory, entry, "__init__.py")
                if os.path.isfile(init_file):
                    discovered.append(os.path.join(directory, entry))
        return discovered

    def load_from_file(self, file_path: str) -> Optional[Plugin]:
        """
        从Python文件加载插件

        查找文件中所有Plugin子类实例
        """
        import os
        if not os.path.isfile(file_path):
            return None
        try:
            import importlib.util
            module_name = f"_plugin_{os.path.basename(file_path).replace('.py', '')}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找Plugin子类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and issubclass(attr, Plugin)
                        and attr is not Plugin and attr is not EnhancedPlugin):
                    try:
                        instance = attr()
                        return instance
                    except Exception:
                        continue
            return None
        except Exception:
            return None

    def load_from_module(self, module_path: str) -> Optional[Plugin]:
        """从模块路径加载插件"""
        try:
            module = importlib.import_module(module_path)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and issubclass(attr, Plugin)
                        and attr is not Plugin and attr is not EnhancedPlugin):
                    try:
                        return attr()
                    except Exception:
                        continue
            return None
        except Exception:
            return None

    def discover_and_load(self, directory: str) -> Dict[str, Plugin]:
        """发现并加载目录中所有插件"""
        results = {}
        files = self.discover_directory(directory)
        for file_path in files:
            plugin = self.load_from_file(file_path)
            if plugin is not None:
                results[plugin.info.name] = plugin
        return results


class EnhancedPlugin(Plugin):
    """
    增强插件基类 — 支持清单、配置、上下文

    第一性原理：插件应自描述其能力和需求
    """

    def __init__(self):
        self._manifest: Optional[PluginManifest] = None
        self._config: Optional[PluginConfig] = None
        self._context: Optional[PluginContext] = None

    @property
    @abstractmethod
    def manifest(self) -> PluginManifest:
        """插件清单（增强元信息）"""
        pass

    @property
    def info(self) -> PluginInfo:
        """向后兼容：从manifest生成PluginInfo"""
        m = self.manifest
        return PluginInfo(
            name=m.name,
            version=m.version,
            description=m.description,
            author=m.author,
            dependencies=list(m.dependencies),
            hooks=list(m.hooks),
        )

    def initialize_with_context(self, context: PluginContext) -> bool:
        """
        使用上下文初始化（增强版）

        子类可重写此方法实现自定义初始化
        """
        self._context = context
        self._config = context.config
        return True

    def initialize(self, context: Dict[str, Any]) -> bool:
        """向后兼容：标准初始化"""
        return True

    def health_check(self) -> PluginHealthResult:
        """健康检查（子类可重写）"""
        return PluginHealthResult(
            plugin_name=self.manifest.name,
            status=PluginHealthStatus.HEALTHY,
            message="OK",
        )


# 导入Tuple已在文件顶部完成


class EnhancedPluginManager(PluginManager):
    """
    增强插件管理器

    第一性原理：插件管理应覆盖完整生命周期 — 发现→加载→配置→运行→监控→重载→卸载
    """

    def __init__(self, system_version: str = "1.0.0"):
        super().__init__()
        self._system_version = system_version
        self._configs: Dict[str, PluginConfig] = {}
        self._contexts: Dict[str, PluginContext] = {}
        self._manifests: Dict[str, PluginManifest] = {}
        self._loader = PluginLoader()
        self._event_bus = PluginEventBus()
        self._health_checks: Dict[str, Callable[[], PluginHealthResult]] = {}
        self._load_order: List[str] = []
        self._global_services: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def set_system_version(self, version: str) -> None:
        """设置系统版本"""
        self._system_version = version

    def register_global_service(self, name: str, service: Any) -> None:
        """注册全局服务（所有插件可访问）"""
        with self._lock:
            self._global_services[name] = service

    def get_global_service(self, name: str) -> Any:
        """获取全局服务"""
        with self._lock:
            return self._global_services.get(name)

    def load_enhanced(
        self,
        plugin: EnhancedPlugin,
        config_values: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        加载增强插件（带配置和上下文）

        第一性原理：加载过程必须校验兼容性、依赖、配置
        """
        manifest = plugin.manifest
        name = manifest.name

        # 如果已注册（可能是之前失败的尝试），先注销以便重试
        if self.registry.get(name) is not None:
            self.registry.unregister(name)

        # 版本兼容性检查
        if not VersionChecker.is_compatible(
            manifest.version, manifest.min_system_version, self._system_version
        ):
            self.registry.register(plugin)
            self.registry.set_error(
                name,
                RuntimeError(
                    f"Plugin requires system >= {manifest.min_system_version}, "
                    f"current: {self._system_version}"
                ),
            )
            return False

        # 依赖检查
        for dep in manifest.dependencies:
            dep_plugin = self.registry.get(dep)
            if dep_plugin is None:
                self.registry.register(plugin)
                self.registry.set_error(name, RuntimeError(f"Missing dependency: {dep}"))
                return False
            if self.registry.get_state(dep) != PluginState.ACTIVE:
                self.registry.register(plugin)
                self.registry.set_error(name, RuntimeError(f"Dependency not active: {dep}"))
                return False

        # 创建配置
        config = PluginConfig(
            schema=manifest.config_schema,
            values=config_values or {},
        )
        valid, errors = config.validate()
        if not valid:
            self.registry.register(plugin)
            self.registry.set_error(name, RuntimeError(f"Config validation failed: {errors}"))
            return False

        # 创建上下文
        context = PluginContext(
            plugin_name=name,
            config=config,
            services=dict(self._global_services),
        )
        context.set_event_publisher(self._event_bus.publish_simple)

        # 注册
        self.registry.register(plugin)
        self.registry.set_state(name, PluginState.LOADING)

        try:
            # 增强初始化
            if not plugin.initialize_with_context(context):
                self.registry.set_error(name, RuntimeError("Initialize returned False"))
                return False

            # 标准初始化（向后兼容）
            if not plugin.initialize({"config": config.to_dict(), "system_version": self._system_version}):
                self.registry.set_error(name, RuntimeError("Legacy initialize returned False"))
                return False

            # 启动
            if not plugin.start():
                self.registry.set_error(name, RuntimeError("Start returned False"))
                return False

            self._configs[name] = config
            self._contexts[name] = context
            self._manifests[name] = manifest
            with self._lock:
                self._load_order.append(name)

            self.registry.set_state(name, PluginState.ACTIVE)
            return True
        except Exception as e:
            self.registry.set_error(name, e)
            return False

    def load(self, plugin: Plugin) -> bool:
        """加载插件（向后兼容，自动检测增强插件）"""
        if isinstance(plugin, EnhancedPlugin):
            return self.load_enhanced(plugin)
        result = super().load(plugin)
        if result:
            with self._lock:
                self._load_order.append(plugin.info.name)
        return result

    def unload(self, name: str) -> bool:
        """卸载插件"""
        result = super().unload(name)
        if result:
            with self._lock:
                if name in self._load_order:
                    self._load_order.remove(name)
                self._configs.pop(name, None)
                self._contexts.pop(name, None)
                self._manifests.pop(name, None)
                self._health_checks.pop(name, None)
        return result

    def reload(self, name: str) -> bool:
        """
        热重载插件

        第一性原理：热重载使系统无需重启即可更新插件
        """
        plugin = self.registry.get(name)
        if plugin is None:
            return False

        # 保存配置
        old_config = self._configs.get(name)
        config_values = old_config.to_dict() if old_config else {}

        # 卸载
        if not self.unload(name):
            return False

        # 重新加载
        if isinstance(plugin, EnhancedPlugin):
            # 创建新实例（通过类型）
            plugin_class = type(plugin)
            try:
                new_instance = plugin_class()
                return self.load_enhanced(new_instance, config_values)
            except Exception:
                return False
        else:
            return self.load(plugin)

    def discover_and_load(self, directory: str) -> Dict[str, bool]:
        """发现并加载目录中所有插件"""
        results = {}
        plugins = self._loader.discover_and_load(directory)
        for name, plugin in plugins.items():
            if isinstance(plugin, EnhancedPlugin):
                results[name] = self.load_enhanced(plugin)
            else:
                results[name] = self.load(plugin)
        return results

    def get_config(self, name: str) -> Optional[PluginConfig]:
        """获取插件配置"""
        with self._lock:
            return self._configs.get(name)

    def update_config(self, name: str, values: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        更新插件配置

        Returns:
            (是否成功, 错误列表)
        """
        config = self._configs.get(name)
        if config is None:
            return False, ["Plugin config not found"]
        config.update(values)
        return config.validate()

    def get_context(self, name: str) -> Optional[PluginContext]:
        """获取插件上下文"""
        with self._lock:
            return self._contexts.get(name)

    def get_manifest(self, name: str) -> Optional[PluginManifest]:
        """获取插件清单"""
        with self._lock:
            return self._manifests.get(name)

    def register_health_check(self, name: str, check_fn: Callable[[], PluginHealthResult]) -> None:
        """注册健康检查函数"""
        with self._lock:
            self._health_checks[name] = check_fn

    def check_health(self, name: str) -> PluginHealthResult:
        """检查单个插件健康状态"""
        plugin = self.registry.get(name)
        if plugin is None:
            return PluginHealthResult(
                plugin_name=name,
                status=PluginHealthStatus.UNKNOWN,
                message="Plugin not found",
            )

        state = self.registry.get_state(name)
        if state != PluginState.ACTIVE:
            return PluginHealthResult(
                plugin_name=name,
                status=PluginHealthStatus.UNHEALTHY,
                message=f"Plugin state: {state.value}",
            )

        # 自定义健康检查
        check_fn = self._health_checks.get(name)
        if check_fn:
            try:
                return check_fn()
            except Exception as e:
                return PluginHealthResult(
                    plugin_name=name,
                    status=PluginHealthStatus.UNHEALTHY,
                    message=f"Health check error: {e}",
                )

        # EnhancedPlugin自带健康检查
        if isinstance(plugin, EnhancedPlugin):
            try:
                return plugin.health_check()
            except Exception as e:
                return PluginHealthResult(
                    plugin_name=name,
                    status=PluginHealthStatus.UNHEALTHY,
                    message=f"Health check error: {e}",
                )

        return PluginHealthResult(
            plugin_name=name,
            status=PluginHealthStatus.HEALTHY,
            message="OK",
        )

    def check_all_health(self) -> Dict[str, PluginHealthResult]:
        """检查所有插件健康状态"""
        results = {}
        for name in self.registry.list_plugins():
            results[name] = self.check_health(name)
        return results

    def publish_event(self, event_type: str, payload: Any, source: str = "") -> List[Any]:
        """发布事件"""
        return self._event_bus.publish_simple(event_type, payload, source)

    def subscribe_event(
        self, event_type: str, handler: Callable, subscriber_name: str = ""
    ) -> None:
        """订阅事件"""
        self._event_bus.subscribe(event_type, handler, subscriber_name)

    def unsubscribe_event(self, event_type: str, handler: Callable) -> bool:
        """取消订阅"""
        return self._event_bus.unsubscribe(event_type, handler)

    def get_event_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[PluginEvent]:
        """获取事件历史"""
        return self._event_bus.get_history(event_type, limit)

    def get_event_bus_stats(self) -> Dict[str, Any]:
        """获取事件总线统计"""
        return self._event_bus.get_stats()

    def get_load_order(self) -> List[str]:
        """获取加载顺序"""
        with self._lock:
            return list(self._load_order)

    def get_manifests(self) -> Dict[str, PluginManifest]:
        """获取所有清单"""
        with self._lock:
            return dict(self._manifests)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        base_stats = super().get_stats()
        with self._lock:
            base_stats["system_version"] = self._system_version
            base_stats["load_order"] = list(self._load_order)
            base_stats["event_bus"] = self._event_bus.get_stats()
            base_stats["global_services"] = list(self._global_services.keys())
            base_stats["enhanced_plugins"] = len(self._manifests)
        return base_stats

    def shutdown(self) -> None:
        """关闭所有插件（按加载逆序）"""
        with self._lock:
            order = list(reversed(self._load_order))
        for name in order:
            self.unload(name)
        self._event_bus.clear()


def create_enhanced_plugin_manager(system_version: str = "1.0.0") -> EnhancedPluginManager:
    """创建增强插件管理器"""
    return EnhancedPluginManager(system_version=system_version)
