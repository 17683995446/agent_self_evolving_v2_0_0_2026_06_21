"""
自驱永续进化Agent系统 — 配置管理器
阶段3：配置系统集中化

第一性原理：系统的行为应由外部规则决定，而非内部固化
"""

import json
import os
import threading
from typing import Any, Dict, Callable, Optional, List
from dataclasses import dataclass, field


@dataclass
class ConfigChangeEvent:
    """配置变更事件"""
    key: str
    old_value: Any
    new_value: Any
    timestamp: float


class ConfigurationManager:
    """
    集中式配置管理器

    特性：
    - 键值对存储
    - 层级命名空间（点号分隔）
    - 变更订阅通知
    - 多源加载（文件、环境变量、字典）
    - 运行时更新
    """

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._callbacks: Dict[str, List[Callable[[Any], None]]] = {}
        self._lock = threading.RLock()
        self._sources: List[str] = []

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        支持层级访问："module.submodule.param"
        """
        with self._lock:
            keys = key.split(".")
            value = self._config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value

    def set(self, key: str, value: Any, notify: bool = True) -> None:
        """
        设置配置项

        支持层级设置："module.submodule.param"
        """
        with self._lock:
            keys = key.split(".")
            old_value = self.get(key)

            # 导航到目标层级
            target = self._config
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]

            target[keys[-1]] = value

            # 通知订阅者
            if notify and old_value != value:
                self._notify(key, old_value, value)

    def load(self, source: str) -> None:
        """
        从外部源加载配置

        支持：
        - JSON文件路径
        - 环境变量前缀
        - 字典对象（通过update）
        """
        if isinstance(source, dict):
            self.update(source)
            return

        if os.path.isfile(source):
            with open(source, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.update(data)
            self._sources.append(f"file:{source}")
        elif source.startswith("env:"):
            prefix = source[4:]
            env_config = self._load_from_env(prefix)
            self.update(env_config)
            self._sources.append(source)
        else:
            raise ValueError(f"Unknown config source: {source}")

    def update(self, config: Dict[str, Any], prefix: str = "") -> None:
        """批量更新配置"""
        with self._lock:
            for key, value in config.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    self.update(value, full_key)
                else:
                    self.set(full_key, value)

    def subscribe(self, key: str, callback: Callable[[Any], None]) -> None:
        """订阅配置变更"""
        with self._lock:
            if key not in self._callbacks:
                self._callbacks[key] = []
            self._callbacks[key].append(callback)

    def unsubscribe(self, key: str, callback: Callable[[Any], None]) -> None:
        """取消订阅"""
        with self._lock:
            if key in self._callbacks:
                if callback in self._callbacks[key]:
                    self._callbacks[key].remove(callback)

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置的副本"""
        with self._lock:
            import copy
            return copy.deepcopy(self._config)

    def has(self, key: str) -> bool:
        """检查配置项是否存在"""
        return self.get(key) is not None

    def delete(self, key: str) -> bool:
        """删除配置项"""
        with self._lock:
            keys = key.split(".")
            target = self._config
            for k in keys[:-1]:
                if k not in target:
                    return False
                target = target[k]
            if keys[-1] in target:
                del target[keys[-1]]
                return True
            return False

    def save(self, filepath: str) -> None:
        """保存配置到文件"""
        with self._lock:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)

    def _notify(self, key: str, old_value: Any, new_value: Any) -> None:
        """通知订阅者"""
        # 通知精确匹配的订阅者
        if key in self._callbacks:
            for callback in self._callbacks[key]:
                try:
                    callback(new_value)
                except Exception:
                    pass

        # 通知父级命名空间的订阅者
        parts = key.split(".")
        for i in range(1, len(parts)):
            parent_key = ".".join(parts[:i])
            if parent_key in self._callbacks:
                for callback in self._callbacks[parent_key]:
                    try:
                        callback({"key": key, "value": new_value})
                    except Exception:
                        pass

    def _load_from_env(self, prefix: str) -> Dict[str, Any]:
        """从环境变量加载配置"""
        result = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lstrip("_").lower()
                # 尝试解析为数字或布尔值
                result[config_key] = self._parse_value(value)
        return result

    @staticmethod
    def _parse_value(value: str) -> Any:
        """尝试将字符串解析为适当类型"""
        # 布尔值
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        # 整数
        try:
            return int(value)
        except ValueError:
            pass
        # 浮点数
        try:
            return float(value)
        except ValueError:
            pass
        # 字符串
        return value

    def get_stats(self) -> Dict[str, Any]:
        """获取配置管理器统计"""
        with self._lock:
            return {
                "total_keys": len(self._flatten(self._config)),
                "sources": self._sources,
                "subscriber_count": sum(len(cbs) for cbs in self._callbacks.values()),
            }

    @staticmethod
    def _flatten(d: Dict, parent: str = "") -> Dict[str, Any]:
        """扁平化嵌套字典"""
        items = {}
        for k, v in d.items():
            new_key = f"{parent}.{k}" if parent else k
            if isinstance(v, dict):
                items.update(ConfigurationManager._flatten(v, new_key))
            else:
                items[new_key] = v
        return items
