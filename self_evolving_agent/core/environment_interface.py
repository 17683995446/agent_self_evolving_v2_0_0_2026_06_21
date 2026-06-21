"""
阶段124: 真实环境接入层

第一性原理:
1. Agent通过感知环境获取状态，通过执行动作影响环境
2. 环境是Agent的外部世界，应通过统一抽象支持多种类型
3. 感知-行动闭环：observe → state → decide → act → environment_change
4. 环境适配器遵循开闭原则：对扩展开放，对修改关闭

提供:
- EnvironmentInterface: 环境抽象接口
- EnvironmentState: 标准化环境状态
- EnvironmentAction: 标准化环境动作
- FilesystemEnvironment: 文件系统环境适配器
- HTTPEnvironment: HTTP API环境适配器
- CommandEnvironment: 命令行环境适配器
- SimulatedEnvironment: 模拟环境（向后兼容）
- EnvironmentManager: 环境管理器（多环境组合）
"""

import os
import json
import time
import threading
import subprocess
import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


# ============================================================
# 标准化数据结构
# ============================================================

class EnvironmentType(Enum):
    """环境类型"""
    SIMULATED = "simulated"        # 模拟环境
    FILESYSTEM = "filesystem"      # 文件系统
    HTTP = "http"                  # HTTP API
    COMMAND = "command"            # 命令行
    COMPOSITE = "composite"        # 组合环境


@dataclass
class EnvironmentState:
    """标准化环境状态"""
    env_type: EnvironmentType
    source: str                          # 状态来源标识
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "env_type": self.env_type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class EnvironmentAction:
    """标准化环境动作"""
    action_type: str                     # 动作类型
    target: str                          # 动作目标
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ActionResult:
    """动作执行结果"""
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 环境抽象接口
# ============================================================

class EnvironmentInterface(ABC):
    """
    环境抽象接口

    第一性原理：
    - 所有环境都支持感知（observe）和行动（act）
    - 环境状态标准化为EnvironmentState
    - 动作标准化为EnvironmentAction
    """

    def __init__(self, env_id: str = "env"):
        self.env_id = env_id
        self._lock = threading.RLock()
        self._observers: List[Callable[[EnvironmentState], None]] = []
        self._action_history: List[ActionResult] = []
        self._max_history = 1000

    @abstractmethod
    def observe(self) -> EnvironmentState:
        """感知环境，返回当前状态"""
        pass

    @abstractmethod
    def act(self, action: EnvironmentAction) -> ActionResult:
        """执行动作，返回结果"""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """获取环境支持的能力列表"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查环境是否可用"""
        pass

    def register_observer(self, observer: Callable[[EnvironmentState], None]) -> None:
        """注册状态观察者"""
        with self._lock:
            self._observers.append(observer)

    def _notify_observers(self, state: EnvironmentState) -> None:
        """通知观察者"""
        observers = list(self._observers)
        for observer in observers:
            try:
                observer(state)
            except Exception:
                pass

    def _record_action(self, result: ActionResult) -> None:
        """记录动作历史"""
        with self._lock:
            self._action_history.append(result)
            if len(self._action_history) > self._max_history:
                self._action_history = self._action_history[-self._max_history:]

    def get_action_history(self, limit: int = 100) -> List[ActionResult]:
        """获取动作历史"""
        with self._lock:
            return list(self._action_history[-limit:])

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total = len(self._action_history)
            success = sum(1 for r in self._action_history if r.success)
            return {
                "env_id": self.env_id,
                "total_actions": total,
                "successful_actions": success,
                "success_rate": success / total if total > 0 else 0.0,
                "observer_count": len(self._observers),
            }

    def clear_history(self) -> None:
        """清除历史"""
        with self._lock:
            self._action_history.clear()


# ============================================================
# 模拟环境（向后兼容）
# ============================================================

class SimulatedEnvironment(EnvironmentInterface):
    """
    模拟环境

    第一性原理：提供可预测的测试环境，向后兼容原有_sense_environment
    """

    def __init__(self, env_id: str = "simulated_env"):
        super().__init__(env_id)
        self._cycle_count = 0
        self._state_data: Dict[str, Any] = {}

    def observe(self) -> EnvironmentState:
        """感知模拟环境"""
        with self._lock:
            self._cycle_count += 1
            t = self._cycle_count * 0.1
            base_value = math.sin(t) * 0.5 + 0.5
            actual_value = base_value + random.gauss(0, 0.05)

            state = EnvironmentState(
                env_type=EnvironmentType.SIMULATED,
                source=self.env_id,
                data={
                    "module_id": "env",
                    "predicted": {"value": base_value},
                    "actual": {"value": actual_value},
                    "cycle": self._cycle_count,
                },
                metadata={"cycle_count": self._cycle_count},
            )
            self._state_data = state.data

        self._notify_observers(state)
        return state

    def act(self, action: EnvironmentAction) -> ActionResult:
        """执行模拟动作"""
        start = time.time()
        result = ActionResult(
            success=True,
            output={"acknowledged": True, "action": action.action_type},
            duration=time.time() - start,
        )
        self._record_action(result)
        return result

    def get_capabilities(self) -> List[str]:
        """获取能力"""
        return ["observe", "simulate"]

    def is_available(self) -> bool:
        """始终可用"""
        return True


# ============================================================
# 文件系统环境适配器
# ============================================================

class FilesystemEnvironment(EnvironmentInterface):
    """
    文件系统环境适配器

    第一性原理：
    - 文件系统是Agent最直接的真实环境
    - 感知 = 读取文件/目录状态
    - 行动 = 创建/修改/删除文件
    """

    def __init__(
        self,
        root_path: str,
        env_id: str = "filesystem_env",
        max_file_size: int = 1024 * 1024,  # 1MB
    ):
        super().__init__(env_id)
        # 防御：root_path必须存在
        if not os.path.exists(root_path):
            raise ValueError(f"Root path does not exist: {root_path}")
        self._root_path = os.path.abspath(root_path)
        self._max_file_size = max_file_size

    def _safe_path(self, relative_path: str) -> str:
        """安全路径：防止路径穿越"""
        # 防御：None输入
        if relative_path is None:
            relative_path = ""
        full_path = os.path.abspath(os.path.join(self._root_path, relative_path))
        # 确保路径在root_path内
        if not full_path.startswith(self._root_path):
            raise ValueError(f"Path traversal detected: {relative_path}")
        return full_path

    def observe(self) -> EnvironmentState:
        """感知文件系统状态"""
        try:
            entries = []
            for entry in os.listdir(self._root_path):
                entry_path = os.path.join(self._root_path, entry)
                stat = os.stat(entry_path)
                entries.append({
                    "name": entry,
                    "path": entry,
                    "is_dir": os.path.isdir(entry_path),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                })

            state = EnvironmentState(
                env_type=EnvironmentType.FILESYSTEM,
                source=self.env_id,
                data={
                    "root_path": self._root_path,
                    "entries": entries,
                    "entry_count": len(entries),
                },
                metadata={"root_path": self._root_path},
            )
            self._notify_observers(state)
            return state
        except Exception as e:
            return EnvironmentState(
                env_type=EnvironmentType.FILESYSTEM,
                source=self.env_id,
                data={"error": str(e)},
            )

    def act(self, action: EnvironmentAction) -> ActionResult:
        """执行文件系统动作"""
        start = time.time()
        try:
            if action.action_type == "read":
                return self._act_read(action, start)
            elif action.action_type == "write":
                return self._act_write(action, start)
            elif action.action_type == "delete":
                return self._act_delete(action, start)
            elif action.action_type == "list":
                return self._act_list(action, start)
            elif action.action_type == "mkdir":
                return self._act_mkdir(action, start)
            else:
                result = ActionResult(
                    success=False,
                    error=f"Unknown action type: {action.action_type}",
                    duration=time.time() - start,
                )
                self._record_action(result)
                return result
        except Exception as e:
            result = ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start,
            )
            self._record_action(result)
            return result

    def _act_read(self, action: EnvironmentAction, start: float) -> ActionResult:
        """读取文件"""
        path = self._safe_path(action.target)
        if not os.path.exists(path):
            result = ActionResult(
                success=False,
                error=f"File not found: {action.target}",
                duration=time.time() - start,
            )
            self._record_action(result)
            return result

        stat = os.stat(path)
        if stat.st_size > self._max_file_size:
            result = ActionResult(
                success=False,
                error=f"File too large: {stat.st_size} > {self._max_file_size}",
                duration=time.time() - start,
            )
            self._record_action(result)
            return result

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        result = ActionResult(
            success=True,
            output={"content": content, "size": len(content)},
            duration=time.time() - start,
        )
        self._record_action(result)
        return result

    def _act_write(self, action: EnvironmentAction, start: float) -> ActionResult:
        """写入文件"""
        path = self._safe_path(action.target)
        content = action.parameters.get("content", "")

        # 确保目录存在
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        result = ActionResult(
            success=True,
            output={"path": action.target, "size": len(content)},
            duration=time.time() - start,
        )
        self._record_action(result)
        return result

    def _act_delete(self, action: EnvironmentAction, start: float) -> ActionResult:
        """删除文件"""
        path = self._safe_path(action.target)
        if not os.path.exists(path):
            result = ActionResult(
                success=False,
                error=f"File not found: {action.target}",
                duration=time.time() - start,
            )
            self._record_action(result)
            return result

        if os.path.isdir(path):
            os.rmdir(path)  # 只删除空目录
        else:
            os.remove(path)

        result = ActionResult(
            success=True,
            output={"deleted": action.target},
            duration=time.time() - start,
        )
        self._record_action(result)
        return result

    def _act_list(self, action: EnvironmentAction, start: float) -> ActionResult:
        """列出目录"""
        path = self._safe_path(action.target)
        if not os.path.isdir(path):
            result = ActionResult(
                success=False,
                error=f"Not a directory: {action.target}",
                duration=time.time() - start,
            )
            self._record_action(result)
            return result

        entries = os.listdir(path)
        result = ActionResult(
            success=True,
            output={"entries": entries, "count": len(entries)},
            duration=time.time() - start,
        )
        self._record_action(result)
        return result

    def _act_mkdir(self, action: EnvironmentAction, start: float) -> ActionResult:
        """创建目录"""
        path = self._safe_path(action.target)
        os.makedirs(path, exist_ok=True)
        result = ActionResult(
            success=True,
            output={"created": action.target},
            duration=time.time() - start,
        )
        self._record_action(result)
        return result

    def get_capabilities(self) -> List[str]:
        """获取能力"""
        return ["read", "write", "delete", "list", "mkdir"]

    def is_available(self) -> bool:
        """检查可用性"""
        return os.path.exists(self._root_path) and os.path.isdir(self._root_path)


# ============================================================
# HTTP环境适配器
# ============================================================

class HTTPEnvironment(EnvironmentInterface):
    """
    HTTP API环境适配器

    第一性原理：
    - HTTP是互联网最通用的接口
    - 感知 = GET请求
    - 行动 = POST/PUT/DELETE请求
    """

    def __init__(
        self,
        base_url: str,
        env_id: str = "http_env",
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ):
        super().__init__(env_id)
        # 防御：base_url验证
        if not base_url:
            raise ValueError("base_url is required")
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}
        self._timeout = timeout
        self._available = True

    def _import_urllib(self):
        """延迟导入urllib"""
        import urllib.request
        import urllib.error
        import urllib.parse
        return urllib.request, urllib.error, urllib.parse

    def observe(self) -> EnvironmentState:
        """感知HTTP环境（GET base_url）"""
        try:
            urllib_request, urllib_error, urllib_parse = self._import_urllib()
            url = self._base_url
            req = urllib_request.Request(url, headers=self._headers)
            with urllib_request.urlopen(req, timeout=self._timeout) as response:
                status = response.status
                body = response.read().decode("utf-8", errors="replace")

                # 尝试解析JSON
                try:
                    data = json.loads(body)
                except (json.JSONDecodeError, ValueError):
                    data = {"raw": body}

                state = EnvironmentState(
                    env_type=EnvironmentType.HTTP,
                    source=self.env_id,
                    data={
                        "url": url,
                        "status": status,
                        "data": data,
                    },
                    metadata={"base_url": self._base_url},
                )
                self._notify_observers(state)
                return state
        except Exception as e:
            self._available = False
            return EnvironmentState(
                env_type=EnvironmentType.HTTP,
                source=self.env_id,
                data={"error": str(e)},
            )

    def act(self, action: EnvironmentAction) -> ActionResult:
        """执行HTTP动作"""
        start = time.time()
        try:
            urllib_request, urllib_error, urllib_parse = self._import_urllib()

            method = action.action_type.upper()
            path = action.target
            params = action.parameters

            url = f"{self._base_url}/{path.lstrip('/')}"

            data = None
            headers = dict(self._headers)

            if method in ("POST", "PUT", "PATCH"):
                if "json" in params:
                    data = json.dumps(params["json"]).encode("utf-8")
                    headers["Content-Type"] = "application/json"
                elif "data" in params:
                    data = str(params["data"]).encode("utf-8")

            req = urllib_request.Request(url, data=data, headers=headers, method=method)

            with urllib_request.urlopen(req, timeout=self._timeout) as response:
                status = response.status
                body = response.read().decode("utf-8", errors="replace")

                try:
                    output = json.loads(body)
                except (json.JSONDecodeError, ValueError):
                    output = {"raw": body}

                result = ActionResult(
                    success=200 <= status < 300,
                    output={"status": status, "data": output},
                    duration=time.time() - start,
                )
                self._record_action(result)
                return result

        except urllib_error.HTTPError as e:
            result = ActionResult(
                success=False,
                error=f"HTTP {e.code}: {e.reason}",
                output={"status": e.code},
                duration=time.time() - start,
            )
            self._record_action(result)
            return result
        except Exception as e:
            result = ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start,
            )
            self._record_action(result)
            return result

    def get_capabilities(self) -> List[str]:
        """获取能力"""
        return ["GET", "POST", "PUT", "PATCH", "DELETE"]

    def is_available(self) -> bool:
        """检查可用性"""
        return self._available


# ============================================================
# 命令行环境适配器
# ============================================================

class CommandEnvironment(EnvironmentInterface):
    """
    命令行环境适配器

    第一性原理：
    - 命令行是系统级交互的最直接方式
    - 感知 = 执行查询命令获取系统状态
    - 行动 = 执行命令改变系统状态
    """

    def __init__(
        self,
        env_id: str = "command_env",
        allowed_commands: Optional[List[str]] = None,
        timeout: float = 30.0,
        cwd: Optional[str] = None,
    ):
        super().__init__(env_id)
        self._allowed_commands = allowed_commands  # None表示允许所有
        self._timeout = timeout
        self._cwd = cwd
        self._available = True

    def _is_allowed(self, command: str) -> bool:
        """检查命令是否允许"""
        if self._allowed_commands is None:
            return True
        # 防御：None输入
        if not command:
            return False
        cmd_base = command.strip().split()[0] if command.strip() else ""
        return cmd_base in self._allowed_commands

    def observe(self) -> EnvironmentState:
        """感知命令行环境（执行预设查询命令）"""
        try:
            # 执行基本系统查询
            import platform
            state = EnvironmentState(
                env_type=EnvironmentType.COMMAND,
                source=self.env_id,
                data={
                    "platform": platform.platform(),
                    "python_version": platform.python_version(),
                    "hostname": platform.node(),
                },
                metadata={"cwd": self._cwd or os.getcwd()},
            )
            self._notify_observers(state)
            return state
        except Exception as e:
            return EnvironmentState(
                env_type=EnvironmentType.COMMAND,
                source=self.env_id,
                data={"error": str(e)},
            )

    def act(self, action: EnvironmentAction) -> ActionResult:
        """执行命令"""
        start = time.time()
        try:
            command = action.target

            # 防御：空命令
            if not command or not command.strip():
                result = ActionResult(
                    success=False,
                    error="Empty command",
                    duration=time.time() - start,
                )
                self._record_action(result)
                return result

            # 防御：命令白名单检查
            if not self._is_allowed(command):
                result = ActionResult(
                    success=False,
                    error=f"Command not allowed: {command}",
                    duration=time.time() - start,
                )
                self._record_action(result)
                return result

            # 执行命令
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=self._cwd,
            )

            result = ActionResult(
                success=proc.returncode == 0,
                output={
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "returncode": proc.returncode,
                },
                error=proc.stderr if proc.returncode != 0 else None,
                duration=time.time() - start,
            )
            self._record_action(result)
            return result

        except subprocess.TimeoutExpired:
            result = ActionResult(
                success=False,
                error=f"Command timed out after {self._timeout}s",
                duration=time.time() - start,
            )
            self._record_action(result)
            return result
        except Exception as e:
            result = ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start,
            )
            self._record_action(result)
            return result

    def get_capabilities(self) -> List[str]:
        """获取能力"""
        if self._allowed_commands is None:
            return ["execute_any"]
        return list(self._allowed_commands)

    def is_available(self) -> bool:
        """检查可用性"""
        return self._available


# ============================================================
# 环境管理器（多环境组合）
# ============================================================

class EnvironmentManager:
    """
    环境管理器

    第一性原理：
    - Agent可能需要同时感知多个环境
    - 统一管理多个环境的感知和行动
    - 路由动作到正确的环境
    """

    def __init__(self, manager_id: str = "env_manager"):
        self.manager_id = manager_id
        self._environments: Dict[str, EnvironmentInterface] = {}
        self._lock = threading.RLock()
        self._default_env_id: Optional[str] = None

    def register_environment(
        self,
        env_id: str,
        environment: EnvironmentInterface,
        is_default: bool = False,
    ) -> None:
        """注册环境"""
        with self._lock:
            self._environments[env_id] = environment
            if is_default or self._default_env_id is None:
                self._default_env_id = env_id

    def unregister_environment(self, env_id: str) -> bool:
        """注销环境"""
        with self._lock:
            if env_id in self._environments:
                del self._environments[env_id]
                if self._default_env_id == env_id:
                    self._default_env_id = next(iter(self._environments), None)
                return True
            return False

    def get_environment(self, env_id: str) -> Optional[EnvironmentInterface]:
        """获取环境"""
        with self._lock:
            return self._environments.get(env_id)

    def get_default_environment(self) -> Optional[EnvironmentInterface]:
        """获取默认环境"""
        with self._lock:
            if self._default_env_id is None:
                return None
            return self._environments.get(self._default_env_id)

    def observe_all(self) -> Dict[str, EnvironmentState]:
        """感知所有环境"""
        with self._lock:
            env_ids = list(self._environments.keys())

        results = {}
        for env_id in env_ids:
            env = self._environments.get(env_id)
            if env and env.is_available():
                try:
                    results[env_id] = env.observe()
                except Exception:
                    pass
        return results

    def observe(self, env_id: Optional[str] = None) -> Optional[EnvironmentState]:
        """感知指定环境或默认环境"""
        with self._lock:
            if env_id is None:
                env_id = self._default_env_id
            env = self._environments.get(env_id)

        if env is None:
            return None
        if not env.is_available():
            return None
        return env.observe()

    def act(
        self,
        action: EnvironmentAction,
        env_id: Optional[str] = None,
    ) -> Optional[ActionResult]:
        """在指定环境或默认环境执行动作"""
        with self._lock:
            if env_id is None:
                env_id = self._default_env_id
            env = self._environments.get(env_id)

        if env is None:
            return ActionResult(success=False, error=f"Environment not found: {env_id}")
        return env.act(action)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有环境统计"""
        with self._lock:
            env_ids = list(self._environments.keys())

        stats = {}
        for env_id in env_ids:
            env = self._environments.get(env_id)
            if env:
                stats[env_id] = env.get_stats()
        return stats

    def get_environment_ids(self) -> List[str]:
        """获取所有环境ID"""
        with self._lock:
            return list(self._environments.keys())

    def clear_all_history(self) -> None:
        """清除所有环境历史"""
        with self._lock:
            envs = list(self._environments.values())
        for env in envs:
            env.clear_history()


# ============================================================
# 便捷函数
# ============================================================

def create_simulated_environment(env_id: str = "simulated_env") -> SimulatedEnvironment:
    """创建模拟环境"""
    return SimulatedEnvironment(env_id)


def create_filesystem_environment(
    root_path: str,
    env_id: str = "filesystem_env",
) -> FilesystemEnvironment:
    """创建文件系统环境"""
    return FilesystemEnvironment(root_path, env_id)


def create_http_environment(
    base_url: str,
    env_id: str = "http_env",
    headers: Optional[Dict[str, str]] = None,
) -> HTTPEnvironment:
    """创建HTTP环境"""
    return HTTPEnvironment(base_url, env_id, headers)


def create_command_environment(
    env_id: str = "command_env",
    allowed_commands: Optional[List[str]] = None,
) -> CommandEnvironment:
    """创建命令行环境"""
    return CommandEnvironment(env_id, allowed_commands)


def create_environment_manager(manager_id: str = "env_manager") -> EnvironmentManager:
    """创建环境管理器"""
    return EnvironmentManager(manager_id)


def create_environment_action(
    action_type: str,
    target: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> EnvironmentAction:
    """创建环境动作"""
    return EnvironmentAction(
        action_type=action_type,
        target=target,
        parameters=parameters or {},
    )
