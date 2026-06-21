"""插件系统Mixin — 阶段149从agent.py拆分"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from ..core.plugin_system import (
    Plugin, EnhancedPlugin, PluginConfig, PluginManifest, PluginHealthResult,
)


class PluginsMixin:
    """插件系统接口（阶段135）"""

    def load_plugin(
        self,
        plugin: Plugin,
        config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """加载插件（阶段135新增）"""
        if isinstance(plugin, EnhancedPlugin):
            return self._plugin_manager.load_enhanced(plugin, config)
        return self._plugin_manager.load(plugin)

    def unload_plugin(self, name: str) -> bool:
        """卸载插件（阶段135新增）"""
        return self._plugin_manager.unload(name)

    def reload_plugin(self, name: str) -> bool:
        """热重载插件（阶段135新增）"""
        return self._plugin_manager.reload(name)

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取插件实例（阶段135新增）"""
        return self._plugin_manager.registry.get(name)

    def list_plugins(self) -> Dict[str, str]:
        """列出所有插件及状态（阶段135新增）"""
        states = self._plugin_manager.registry.list_plugins()
        return {name: state.value for name, state in states.items()}

    def get_plugin_status(self, name: str) -> Optional[str]:
        """获取插件状态（阶段135新增）"""
        state = self._plugin_manager.registry.get_state(name)
        return state.value if state else None

    def get_plugin_health(self, name: str) -> PluginHealthResult:
        """获取插件健康状态（阶段135新增）"""
        return self._plugin_manager.check_health(name)

    def get_all_plugin_health(self) -> Dict[str, PluginHealthResult]:
        """获取所有插件健康状态（阶段135新增）"""
        return self._plugin_manager.check_all_health()

    def discover_plugins(self, directory: str) -> Dict[str, bool]:
        """发现并加载目录中的插件（阶段135新增）"""
        return self._plugin_manager.discover_and_load(directory)

    def emit_plugin_event(
        self,
        event_type: str,
        payload: Any,
        source: str = "",
    ) -> List[Any]:
        """发布插件事件（阶段135新增）"""
        return self._plugin_manager.publish_event(event_type, payload, source)

    def subscribe_plugin_event(
        self,
        event_type: str,
        handler: Callable,
        subscriber_name: str = "",
    ) -> None:
        """订阅插件事件（阶段135新增）"""
        self._plugin_manager.subscribe_event(event_type, handler, subscriber_name)

    def get_plugin_config(self, name: str) -> Optional[PluginConfig]:
        """获取插件配置（阶段135新增）"""
        return self._plugin_manager.get_config(name)

    def update_plugin_config(
        self,
        name: str,
        values: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """更新插件配置（阶段135新增）"""
        return self._plugin_manager.update_config(name, values)

    def get_plugin_manifest(self, name: str) -> Optional[PluginManifest]:
        """获取插件清单（阶段135新增）"""
        return self._plugin_manager.get_manifest(name)

    def get_plugin_stats(self) -> Dict[str, Any]:
        """获取插件系统统计（阶段135新增）"""
        return self._plugin_manager.get_stats()
