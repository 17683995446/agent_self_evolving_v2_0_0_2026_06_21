"""
阶段138: 配置热更新 — 运行时配置

第一性原理:
1. 可配置性 — 系统行为应可在运行时调整，无需重启
2. 无中断性 — 配置变更不应中断正在运行的服务
3. 一致性 — 配置变更应原子性地传播到所有相关组件
4. 可追溯性 — 配置变更应被记录，支持审计和回滚
5. 安全性 — 配置变更应经过验证，防止无效配置破坏系统

组件:
- ConfigChangeRecord — 配置变更记录（用于审计和回滚）
- ConfigHistory — 配置历史管理（支持回滚到任意版本）
- ConfigTransaction — 原子事务（批量更新，全部成功或全部回滚）
- ConfigWatcher — 文件监视器（轮询mtime，跨平台兼容）
- ConfigReloadHandler — 组件重载接口（组件实现以响应配置变更）
- HotReloadManager — 热更新管理器（协调所有组件）
"""

import os
import json
import time
import threading
import hashlib
import copy
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


# ============================================================
# 配置变更记录
# ============================================================

class ConfigChangeType(Enum):
    """配置变更类型"""
    SET = "set"           # 设置
    DELETE = "delete"     # 删除
    UPDATE = "update"     # 批量更新
    ROLLBACK = "rollback" # 回滚
    RELOAD = "reload"     # 文件重载


@dataclass
class ConfigChangeRecord:
    """配置变更记录"""
    change_id: str
    change_type: ConfigChangeType
    key: str
    old_value: Any
    new_value: Any
    timestamp: float
    source: str = "manual"  # manual / file_watcher / env / api
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type.value,
            "key": self.key,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp,
            "source": self.source,
            "success": self.success,
            "error": self.error,
        }


# ============================================================
# 配置历史管理
# ============================================================

class ConfigHistory:
    """
    配置历史管理器

    记录所有配置变更，支持：
    - 查询历史
    - 回滚到指定记录
    - 回滚到指定时间点
    """

    def __init__(self, max_records: int = 1000):
        self._records: List[ConfigChangeRecord] = []
        self._max_records = max_records
        self._lock = threading.RLock()
        self._counter = 0

    def record(self, change: ConfigChangeRecord) -> None:
        """记录变更"""
        with self._lock:
            self._records.append(change)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]

    def get_records(
        self,
        key: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> List[ConfigChangeRecord]:
        """查询历史记录"""
        with self._lock:
            results = list(self._records)
        if key:
            results = [r for r in results if r.key == key]
        if source:
            results = [r for r in results if r.source == source]
        return results[-limit:]

    def get_record(self, change_id: str) -> Optional[ConfigChangeRecord]:
        """按ID查询记录"""
        with self._lock:
            for r in self._records:
                if r.change_id == change_id:
                    return r
        return None

    def get_latest(self, key: Optional[str] = None) -> Optional[ConfigChangeRecord]:
        """获取最新记录"""
        records = self.get_records(key=key, limit=1)
        return records[0] if records else None

    def next_id(self) -> str:
        """生成下一个变更ID"""
        with self._lock:
            self._counter += 1
            return f"chg_{int(time.time())}_{self._counter}"

    def clear(self) -> None:
        """清空历史"""
        with self._lock:
            self._records.clear()

    def count(self) -> int:
        """记录数"""
        with self._lock:
            return len(self._records)


# ============================================================
# 配置事务
# ============================================================

class ConfigTransaction:
    """
    配置事务 — 原子批量更新

    所有变更在commit时一次性应用，任一失败则全部回滚。
    """

    def __init__(self, manager: "HotReloadManager"):
        self._manager = manager
        self._operations: List[Tuple[str, str, Any]] = []  # (op, key, value)
        self._committed = False
        self._rolled_back = False

    def set(self, key: str, value: Any) -> "ConfigTransaction":
        """添加设置操作"""
        if self._committed or self._rolled_back:
            raise RuntimeError("Transaction already finished")
        self._operations.append(("set", key, value))
        return self

    def delete(self, key: str) -> "ConfigTransaction":
        """添加删除操作"""
        if self._committed or self._rolled_back:
            raise RuntimeError("Transaction already finished")
        self._operations.append(("delete", key, None))
        return self

    def commit(self) -> Tuple[bool, List[str]]:
        """
        提交事务

        Returns:
            (success, errors)
        """
        if self._committed or self._rolled_back:
            raise RuntimeError("Transaction already finished")

        # 先验证所有变更
        errors = []
        snapshot = self._manager.snapshot()

        for op, key, value in self._operations:
            if op == "set":
                validation_error = self._manager.validate(key, value)
                if validation_error:
                    errors.append(f"Validation failed for '{key}': {validation_error}")

        if errors:
            self._rolled_back = True
            return False, errors

        # 应用所有变更
        applied = []
        try:
            for op, key, value in self._operations:
                if op == "set":
                    old = self._manager.get(key)
                    self._manager._apply_set(key, value, source="transaction")
                    applied.append(("set", key, old, value))
                elif op == "delete":
                    old = self._manager.get(key)
                    self._manager._apply_delete(key, source="transaction")
                    applied.append(("delete", key, old, None))
        except Exception as e:
            # 回滚已应用的变更
            for op, key, old, new in reversed(applied):
                try:
                    if op == "set":
                        self._manager._apply_set(key, old, source="transaction_rollback")
                    elif op == "delete":
                        if old is not None:
                            self._manager._apply_set(key, old, source="transaction_rollback")
                except Exception:
                    pass
            self._rolled_back = True
            return False, [f"Transaction failed: {e}"]

        self._committed = True
        return True, []

    def rollback(self) -> None:
        """手动回滚（未commit时丢弃操作）"""
        self._rolled_back = True
        self._operations.clear()


# ============================================================
# 配置验证器
# ============================================================

class ConfigValidator:
    """
    配置验证器

    支持类型检查、范围约束、自定义规则。
    """

    def __init__(self):
        self._rules: Dict[str, List[Callable[[Any], Optional[str]]]] = {}
        self._lock = threading.RLock()

    def add_rule(self, key: str, rule: Callable[[Any], Optional[str]]) -> None:
        """
        添加验证规则

        规则签名: rule(value) -> error_message or None
        """
        with self._lock:
            if key not in self._rules:
                self._rules[key] = []
            self._rules[key].append(rule)

    def add_type_rule(self, key: str, expected_type: type) -> None:
        """添加类型检查规则"""
        def type_check(value: Any) -> Optional[str]:
            if not isinstance(value, expected_type):
                return f"Expected {expected_type.__name__}, got {type(value).__name__}"
            return None
        self.add_rule(key, type_check)

    def add_range_rule(self, key: str, min_val: Optional[float] = None, max_val: Optional[float] = None) -> None:
        """添加范围检查规则"""
        def range_check(value: Any) -> Optional[str]:
            try:
                num = float(value)
            except (TypeError, ValueError):
                return f"Value must be numeric, got {type(value).__name__}"
            if min_val is not None and num < min_val:
                return f"Value {num} < minimum {min_val}"
            if max_val is not None and num > max_val:
                return f"Value {num} > maximum {max_val}"
            return None
        self.add_rule(key, range_check)

    def add_choice_rule(self, key: str, choices: List[Any]) -> None:
        """添加枚举选择规则"""
        def choice_check(value: Any) -> Optional[str]:
            if value not in choices:
                return f"Value '{value}' not in allowed choices: {choices}"
            return None
        self.add_rule(key, choice_check)

    def validate(self, key: str, value: Any) -> Optional[str]:
        """验证单个值"""
        with self._lock:
            rules = self._rules.get(key, [])
        for rule in rules:
            try:
                error = rule(value)
                if error:
                    return error
            except Exception as e:
                return f"Validation rule error: {e}"
        return None

    def validate_all(self, values: Dict[str, Any]) -> List[str]:
        """验证多个值"""
        errors = []
        for key, value in values.items():
            error = self.validate(key, value)
            if error:
                errors.append(f"{key}: {error}")
        return errors

    def get_rules(self) -> Dict[str, int]:
        """获取规则统计"""
        with self._lock:
            return {k: len(v) for k, v in self._rules.items()}


# ============================================================
# 配置文件监视器
# ============================================================

class ConfigWatcher:
    """
    配置文件监视器

    基于轮询的文件变更检测（跨平台兼容，不依赖inotify/watchdog）。
    检测文件mtime和内容hash的变化。
    """

    def __init__(self, poll_interval: float = 1.0):
        self._poll_interval = poll_interval
        self._files: Dict[str, Dict[str, Any]] = {}  # path -> {mtime, hash, content}
        self._callbacks: Dict[str, Callable[[str, Dict[str, Any]], None]] = {}
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def watch(self, file_path: str, callback: Callable[[str, Dict[str, Any]], None]) -> bool:
        """
        开始监视文件

        Args:
            file_path: 文件路径
            callback: 变更回调 (path, new_content)

        Returns:
            是否成功开始监视
        """
        file_path = os.path.abspath(file_path)
        if not os.path.exists(file_path):
            return False

        with self._lock:
            self._files[file_path] = self._read_file_info(file_path)
            self._callbacks[file_path] = callback

        # 自动启动轮询线程
        if not self._running:
            self._start()

        return True

    def unwatch(self, file_path: str) -> None:
        """停止监视文件"""
        file_path = os.path.abspath(file_path)
        with self._lock:
            self._files.pop(file_path, None)
            self._callbacks.pop(file_path, None)

    def _read_file_info(self, file_path: str) -> Dict[str, Any]:
        """读取文件信息"""
        try:
            stat = os.stat(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "hash": hashlib.md5(content.encode("utf-8")).hexdigest(),
                "content": content,
            }
        except Exception:
            return {"mtime": 0, "size": 0, "hash": "", "content": ""}

    def _start(self) -> None:
        """启动轮询线程"""
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="config-watcher")
        self._thread.start()

    def stop(self) -> None:
        """停止监视"""
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _poll_loop(self) -> None:
        """轮询循环"""
        while self._running and not self._stop_event.is_set():
            try:
                self._check_files()
            except Exception:
                pass
            self._stop_event.wait(self._poll_interval)

    def _check_files(self) -> None:
        """检查所有文件"""
        with self._lock:
            files = dict(self._files)
            callbacks = dict(self._callbacks)

        for path, old_info in files.items():
            if not os.path.exists(path):
                continue
            new_info = self._read_file_info(path)
            if new_info["hash"] != old_info["hash"]:
                # 文件已变更
                callback = callbacks.get(path)
                if callback:
                    try:
                        content = new_info.get("content", "")
                        try:
                            data = json.loads(content) if content.strip() else {}
                        except (json.JSONDecodeError, ValueError):
                            data = {"raw": content}
                        callback(path, data)
                    except Exception:
                        pass
                with self._lock:
                    if path in self._files:
                        self._files[path] = new_info

    def is_watching(self, file_path: str) -> bool:
        """是否正在监视"""
        file_path = os.path.abspath(file_path)
        with self._lock:
            return file_path in self._files

    def get_watched_files(self) -> List[str]:
        """获取正在监视的文件列表"""
        with self._lock:
            return list(self._files.keys())

    def check_once(self) -> int:
        """
        手动触发一次检查

        Returns:
            检测到变更的文件数
        """
        with self._lock:
            files = dict(self._files)
            callbacks = dict(self._callbacks)

        changed = 0
        for path, old_info in files.items():
            if not os.path.exists(path):
                continue
            new_info = self._read_file_info(path)
            if new_info["hash"] != old_info["hash"]:
                changed += 1
                callback = callbacks.get(path)
                if callback:
                    try:
                        content = new_info.get("content", "")
                        try:
                            data = json.loads(content) if content.strip() else {}
                        except (json.JSONDecodeError, ValueError):
                            data = {"raw": content}
                        callback(path, data)
                    except Exception:
                        pass
                with self._lock:
                    if path in self._files:
                        self._files[path] = new_info
        return changed


# ============================================================
# 组件重载接口
# ============================================================

class ConfigReloadHandler(ABC):
    """
    组件配置重载接口

    组件实现此接口以响应配置变更。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """组件名称"""
        ...

    @abstractmethod
    def on_config_change(self, key: str, old_value: Any, new_value: Any) -> Tuple[bool, Optional[str]]:
        """
        处理配置变更

        Returns:
            (success, error_message)
        """
        ...

    def on_reload_all(self) -> Tuple[bool, Optional[str]]:
        """
        处理全量重载（可选实现）

        Returns:
            (success, error_message)
        """
        return True, None


# ============================================================
# 热更新管理器
# ============================================================

class HotReloadManager:
    """
    热更新管理器

    协调配置的运行时更新，整合：
    - 配置存储（线程安全）
    - 验证器
    - 历史记录
    - 文件监视
    - 组件通知
    - 事务支持
    """

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._validator = ConfigValidator()
        self._history = ConfigHistory()
        self._watcher = ConfigWatcher()
        self._handlers: Dict[str, ConfigReloadHandler] = {}
        self._subscribers: Dict[str, List[Callable[[str, Any, Any], None]]] = {}
        self._watched_files: Dict[str, str] = {}  # path -> namespace

    @property
    def validator(self) -> ConfigValidator:
        return self._validator

    @property
    def history(self) -> ConfigHistory:
        return self._history

    @property
    def watcher(self) -> ConfigWatcher:
        return self._watcher

    # ---------- 基本配置操作 ----------

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（支持点号路径）"""
        with self._lock:
            keys = key.split(".")
            value = self._config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return copy.deepcopy(value)

    def has(self, key: str) -> bool:
        """检查配置项是否存在"""
        with self._lock:
            keys = key.split(".")
            value = self._config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return False
            return True

    def snapshot(self) -> Dict[str, Any]:
        """获取配置快照"""
        with self._lock:
            return copy.deepcopy(self._config)

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self.snapshot()

    def validate(self, key: str, value: Any) -> Optional[str]:
        """验证配置值"""
        return self._validator.validate(key, value)

    # ---------- 变更操作 ----------

    def set(self, key: str, value: Any, source: str = "manual") -> Tuple[bool, Optional[str]]:
        """
        设置配置值

        Returns:
            (success, error_message)
        """
        # 验证
        error = self.validate(key, value)
        if error:
            return False, error

        return self._apply_set(key, value, source=source)

    def _apply_set(self, key: str, value: Any, source: str = "manual") -> Tuple[bool, Optional[str]]:
        """内部应用设置"""
        with self._lock:
            old_value = self.get(key)

            # 导航到目标位置
            keys = key.split(".")
            target = self._config
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                elif not isinstance(target[k], dict):
                    target[k] = {}
                target = target[k]
            target[keys[-1]] = copy.deepcopy(value)

        # 记录历史
        record = ConfigChangeRecord(
            change_id=self._history.next_id(),
            change_type=ConfigChangeType.SET,
            key=key,
            old_value=old_value,
            new_value=copy.deepcopy(value),
            timestamp=time.time(),
            source=source,
        )
        self._history.record(record)

        # 通知订阅者和处理器
        self._notify(key, old_value, value)

        return True, None

    def delete(self, key: str, source: str = "manual") -> Tuple[bool, Optional[str]]:
        """
        删除配置项

        Returns:
            (success, error_message)
        """
        return self._apply_delete(key, source=source)

    def _apply_delete(self, key: str, source: str = "manual") -> Tuple[bool, Optional[str]]:
        """内部应用删除"""
        with self._lock:
            old_value = self.get(key)
            if old_value is None:
                return False, f"Key '{key}' not found"

            keys = key.split(".")
            target = self._config
            for k in keys[:-1]:
                if k not in target:
                    return False, f"Key '{key}' not found"
                target = target[k]
            if keys[-1] in target:
                del target[keys[-1]]
            else:
                return False, f"Key '{key}' not found"

        record = ConfigChangeRecord(
            change_id=self._history.next_id(),
            change_type=ConfigChangeType.DELETE,
            key=key,
            old_value=old_value,
            new_value=None,
            timestamp=time.time(),
            source=source,
        )
        self._history.record(record)

        self._notify(key, old_value, None)
        return True, None

    def update(self, values: Dict[str, Any], source: str = "manual") -> Tuple[bool, List[str]]:
        """
        批量更新配置

        Returns:
            (success, errors)
        """
        # 先验证所有值
        errors = self._validator.validate_all(values)
        if errors:
            return False, errors

        # 应用
        applied = []
        for key, value in values.items():
            old = self.get(key)
            ok, err = self._apply_set(key, value, source=source)
            if ok:
                applied.append((key, old))
            else:
                # 回滚
                for k, old_v in reversed(applied):
                    if old_v is not None:
                        self._apply_set(k, old_v, source=f"{source}_rollback")
                return False, [f"Failed to set '{key}': {err}"]

        return True, []

    def transaction(self) -> ConfigTransaction:
        """创建事务"""
        return ConfigTransaction(self)

    # ---------- 回滚 ----------

    def rollback(self, change_id: str) -> Tuple[bool, Optional[str]]:
        """
        回滚到指定变更之前的状态

        Returns:
            (success, error_message)
        """
        record = self._history.get_record(change_id)
        if record is None:
            return False, f"Change '{change_id}' not found"

        if record.change_type == ConfigChangeType.SET:
            if record.old_value is None:
                return self._apply_delete(record.key, source="rollback")
            else:
                return self._apply_set(record.key, record.old_value, source="rollback")
        elif record.change_type == ConfigChangeType.DELETE:
            if record.old_value is not None:
                return self._apply_set(record.key, record.old_value, source="rollback")
        return False, "Cannot rollback this change type"

    def rollback_to(self, timestamp: float) -> int:
        """
        回滚到指定时间点

        Returns:
            回滚的变更数
        """
        records = self._history.get_records(limit=10000)
        to_rollback = [r for r in records if r.timestamp > timestamp]
        count = 0
        for record in reversed(to_rollback):
            ok, _ = self.rollback(record.change_id)
            if ok:
                count += 1
        return count

    # ---------- 订阅 ----------

    def subscribe(self, key: str, callback: Callable[[str, Any, Any], None]) -> None:
        """
        订阅配置变更

        callback签名: callback(key, old_value, new_value)
        """
        with self._lock:
            if key not in self._subscribers:
                self._subscribers[key] = []
            self._subscribers[key].append(callback)

    def unsubscribe(self, key: str, callback: Callable[[str, Any, Any], None]) -> None:
        """取消订阅"""
        with self._lock:
            if key in self._subscribers and callback in self._subscribers[key]:
                self._subscribers[key].remove(callback)

    def _notify(self, key: str, old_value: Any, new_value: Any) -> None:
        """通知订阅者和处理器"""
        # 通知精确匹配的订阅者
        with self._lock:
            subs = list(self._subscribers.get(key, []))
        for callback in subs:
            try:
                callback(key, old_value, new_value)
            except Exception:
                pass

        # 通知父级命名空间订阅者
        parts = key.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[:i])
            with self._lock:
                parent_subs = list(self._subscribers.get(parent, []))
            for callback in parent_subs:
                try:
                    callback(key, old_value, new_value)
                except Exception:
                    pass

        # 通知注册的处理器
        with self._lock:
            handlers = list(self._handlers.values())
        for handler in handlers:
            try:
                handler.on_config_change(key, old_value, new_value)
            except Exception:
                pass

    # ---------- 组件注册 ----------

    def register_handler(self, handler: ConfigReloadHandler) -> None:
        """注册配置重载处理器"""
        with self._lock:
            self._handlers[handler.name] = handler

    def unregister_handler(self, name: str) -> None:
        """注销处理器"""
        with self._lock:
            self._handlers.pop(name, None)

    def reload_all(self) -> Dict[str, Tuple[bool, Optional[str]]]:
        """
        通知所有处理器重新加载配置

        Returns:
            {handler_name: (success, error)}
        """
        results = {}
        with self._lock:
            handlers = list(self._handlers.items())
        for name, handler in handlers:
            try:
                ok, err = handler.on_reload_all()
                results[name] = (ok, err)
            except Exception as e:
                results[name] = (False, str(e))
        return results

    # ---------- 文件监视 ----------

    def watch_file(self, file_path: str, namespace: str = "") -> bool:
        """
        监视配置文件变更

        文件变更时自动重载配置。

        Args:
            file_path: 配置文件路径
            namespace: 命名空间前缀（变更会加载到该命名空间下）

        Returns:
            是否成功开始监视
        """
        file_path = os.path.abspath(file_path)
        if not os.path.exists(file_path):
            return False

        # 首次加载
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            data = json.loads(content) if content.strip() else {}
            if namespace:
                data = {namespace: data} if isinstance(data, dict) else data
            if isinstance(data, dict):
                self.update(data, source=f"file:{file_path}")
        except Exception:
            pass

        with self._lock:
            self._watched_files[file_path] = namespace

        def on_change(path: str, new_data: Dict[str, Any]) -> None:
            ns = self._watched_files.get(path, "")
            if ns and isinstance(new_data, dict):
                new_data = {ns: new_data}
            if isinstance(new_data, dict):
                self.update(new_data, source=f"file_watcher:{path}")

        return self._watcher.watch(file_path, on_change)

    def unwatch_file(self, file_path: str) -> None:
        """停止监视文件"""
        file_path = os.path.abspath(file_path)
        with self._lock:
            self._watched_files.pop(file_path, None)
        self._watcher.unwatch(file_path)

    def stop_watcher(self) -> None:
        """停止所有文件监视"""
        self._watcher.stop()

    # ---------- 导入导出 ----------

    def load_from_dict(self, data: Dict[str, Any], source: str = "dict") -> Tuple[bool, List[str]]:
        """从字典加载配置"""
        return self.update(data, source=source)

    def load_from_file(self, file_path: str, source: str = "file") -> Tuple[bool, List[str]]:
        """从JSON文件加载配置"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return False, [f"Failed to load file: {e}"]
        return self.update(data, source=f"{source}:{file_path}")

    def save_to_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """保存配置到JSON文件"""
        try:
            with self._lock:
                data = copy.deepcopy(self._config)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            return True, None
        except Exception as e:
            return False, str(e)

    # ---------- 统计 ----------

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            flat = self._flatten(self._config)
            return {
                "total_keys": len(flat),
                "history_count": self._history.count(),
                "watched_files": len(self._watched_files),
                "registered_handlers": list(self._handlers.keys()),
                "subscriber_count": sum(len(s) for s in self._subscribers.values()),
                "validation_rules": self._validator.get_rules(),
            }

    def get_history(
        self,
        key: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """获取变更历史"""
        records = self._history.get_records(key=key, source=source, limit=limit)
        return [r.to_dict() for r in records]

    @staticmethod
    def _flatten(d: Dict, parent: str = "") -> Dict[str, Any]:
        """扁平化嵌套字典"""
        items = {}
        for k, v in d.items():
            new_key = f"{parent}.{k}" if parent else k
            if isinstance(v, dict):
                items.update(HotReloadManager._flatten(v, new_key))
            else:
                items[new_key] = v
        return items


# ============================================================
# 便捷函数
# ============================================================

def create_hot_reload_manager() -> HotReloadManager:
    """创建热更新管理器"""
    return HotReloadManager()


# 默认全局实例（可选使用）
_global_manager: Optional[HotReloadManager] = None
_global_lock = threading.Lock()


def get_global_hot_reload_manager() -> HotReloadManager:
    """获取全局热更新管理器实例"""
    global _global_manager
    with _global_lock:
        if _global_manager is None:
            _global_manager = HotReloadManager()
        return _global_manager
