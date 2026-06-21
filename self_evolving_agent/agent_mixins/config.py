"""配置热更新Mixin — 阶段149从agent.py拆分"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from ..core.config_hot_reload import ConfigReloadHandler


class ConfigMixin:
    """配置热更新接口（阶段138）"""

    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值（阶段138新增）"""
        return self._hot_reload.get(key, default)

    def set_config(self, key: str, value: Any) -> Tuple[bool, Optional[str]]:
        """设置配置值（阶段138新增）"""
        return self._hot_reload.set(key, value)

    def delete_config(self, key: str) -> Tuple[bool, Optional[str]]:
        """删除配置项（阶段138新增）"""
        return self._hot_reload.delete(key)

    def update_config(self, values: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """批量更新配置（阶段138新增）"""
        return self._hot_reload.update(values)

    def has_config(self, key: str) -> bool:
        """检查配置项是否存在（阶段138新增）"""
        return self._hot_reload.has(key)

    def get_config_snapshot(self) -> Dict[str, Any]:
        """获取配置快照（阶段138新增）"""
        return self._hot_reload.snapshot()

    def subscribe_config(self, key: str, callback: Callable[[str, Any, Any], None]) -> None:
        """订阅配置变更（阶段138新增）"""
        self._hot_reload.subscribe(key, callback)

    def unsubscribe_config(self, key: str, callback: Callable[[str, Any, Any], None]) -> None:
        """取消订阅配置变更（阶段138新增）"""
        self._hot_reload.unsubscribe(key, callback)

    def rollback_config(self, change_id: str) -> Tuple[bool, Optional[str]]:
        """回滚配置变更（阶段138新增）"""
        return self._hot_reload.rollback(change_id)

    def get_config_history(self, key: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取配置变更历史（阶段138新增）"""
        return self._hot_reload.get_history(key=key, limit=limit)

    def watch_config_file(self, file_path: str, namespace: str = "") -> bool:
        """监视配置文件变更（阶段138新增）"""
        return self._hot_reload.watch_file(file_path, namespace=namespace)

    def unwatch_config_file(self, file_path: str) -> None:
        """停止监视配置文件（阶段138新增）"""
        self._hot_reload.unwatch_file(file_path)

    def register_config_handler(self, handler: ConfigReloadHandler) -> None:
        """注册配置重载处理器（阶段138新增）"""
        self._hot_reload.register_handler(handler)

    def reload_all_config(self) -> Dict[str, Tuple[bool, Optional[str]]]:
        """通知所有处理器重新加载配置（阶段138新增）"""
        return self._hot_reload.reload_all()

    def get_config_stats(self) -> Dict[str, Any]:
        """获取配置统计（阶段138新增）"""
        return self._hot_reload.get_stats()

    def save_config(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """保存配置到文件（阶段138新增）"""
        return self._hot_reload.save_to_file(file_path)

    def load_config(self, file_path: str) -> Tuple[bool, List[str]]:
        """从文件加载配置（阶段138新增）"""
        return self._hot_reload.load_from_file(file_path)
