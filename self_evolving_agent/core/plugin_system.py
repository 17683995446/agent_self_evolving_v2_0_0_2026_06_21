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
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type
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
