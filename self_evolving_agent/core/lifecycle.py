"""
阶段31: 模块生命周期管理

第一性原理:
1. 模块是有生命周期的实体，必须经历创建→初始化→运行→停止→销毁的完整过程
2. 没有生命周期管理，资源泄漏和状态混乱将不可避免
3. 状态转换必须显式、可追踪、可回滚

设计原则:
- 状态机驱动：所有状态转换通过显式事件触发
- 依赖有序：初始化/销毁遵循依赖拓扑序
- 失败可恢复：某阶段失败可回滚到安全状态
- 事件通知：生命周期事件可被外部监听
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional, Set, Tuple
from enum import Enum, auto
from abc import ABC, abstractmethod
from datetime import datetime
import threading


class LifecycleState(Enum):
    """生命周期状态"""
    CREATED = "created"         # 已创建
    INITIALIZING = "initializing"  # 初始化中
    INITIALIZED = "initialized"    # 已初始化
    STARTING = "starting"       # 启动中
    RUNNING = "running"         # 运行中
    STOPPING = "stopping"       # 停止中
    STOPPED = "stopped"         # 已停止
    DESTROYING = "destroying"   # 销毁中
    DESTROYED = "destroyed"     # 已销毁
    FAILED = "failed"           # 失败


class LifecycleEvent(Enum):
    """生命周期事件"""
    CREATE = auto()
    INITIALIZE = auto()
    START = auto()
    STOP = auto()
    DESTROY = auto()
    FAIL = auto()
    RECOVER = auto()


# 有效的状态转换图
VALID_TRANSITIONS: Dict[LifecycleState, Dict[LifecycleEvent, LifecycleState]] = {
    LifecycleState.CREATED: {
        LifecycleEvent.INITIALIZE: LifecycleState.INITIALIZING,
        LifecycleEvent.DESTROY: LifecycleState.DESTROYING,
    },
    LifecycleState.INITIALIZING: {
        LifecycleEvent.FAIL: LifecycleState.FAILED,
    },
    LifecycleState.INITIALIZED: {
        LifecycleEvent.START: LifecycleState.STARTING,
        LifecycleEvent.DESTROY: LifecycleState.DESTROYING,
    },
    LifecycleState.STARTING: {
        LifecycleEvent.FAIL: LifecycleState.FAILED,
    },
    LifecycleState.RUNNING: {
        LifecycleEvent.STOP: LifecycleState.STOPPING,
        LifecycleEvent.FAIL: LifecycleState.FAILED,
    },
    LifecycleState.STOPPING: {
        LifecycleEvent.FAIL: LifecycleState.FAILED,
    },
    LifecycleState.STOPPED: {
        LifecycleEvent.START: LifecycleState.STARTING,
        LifecycleEvent.DESTROY: LifecycleState.DESTROYING,
    },
    LifecycleState.DESTROYING: {
        LifecycleEvent.FAIL: LifecycleState.FAILED,
    },
    LifecycleState.DESTROYED: {},
    LifecycleState.FAILED: {
        LifecycleEvent.RECOVER: LifecycleState.CREATED,
        LifecycleEvent.DESTROY: LifecycleState.DESTROYING,
    },
}

# 成功完成后的自动转换
COMPLETION_TRANSITIONS: Dict[LifecycleState, LifecycleState] = {
    LifecycleState.INITIALIZING: LifecycleState.INITIALIZED,
    LifecycleState.STARTING: LifecycleState.RUNNING,
    LifecycleState.STOPPING: LifecycleState.STOPPED,
    LifecycleState.DESTROYING: LifecycleState.DESTROYED,
}


@dataclass
class StateTransition:
    """状态转换记录"""
    from_state: LifecycleState
    to_state: LifecycleState
    event: LifecycleEvent
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error: Optional[str] = None


class LifecycleAware(ABC):
    """
    生命周期感知接口

    第一性原理：模块必须显式声明自己在每个生命周期阶段要做什么
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """模块名称"""
        pass

    @property
    def dependencies(self) -> List[str]:
        """依赖的模块名称列表"""
        return []

    def on_initialize(self) -> None:
        """初始化回调"""
        pass

    def on_start(self) -> None:
        """启动回调"""
        pass

    def on_stop(self) -> None:
        """停止回调"""
        pass

    def on_destroy(self) -> None:
        """销毁回调"""
        pass

    def on_fail(self, error: Exception) -> None:
        """失败回调"""
        pass

    def health_check(self) -> Tuple[bool, str]:
        """健康检查，返回(是否健康, 消息)"""
        return True, "OK"


class LifecycleManager:
    """
    生命周期管理器

    管理多个模块的生命周期，处理依赖拓扑和状态转换
    """

    def __init__(self):
        self._modules: Dict[str, LifecycleAware] = {}
        self._states: Dict[str, LifecycleState] = {}
        self._transitions: Dict[str, List[StateTransition]] = {}
        self._listeners: List[Callable[[str, StateTransition], None]] = []
        self._lock = threading.RLock()

    def register(self, module: LifecycleAware) -> None:
        """注册模块"""
        with self._lock:
            self._modules[module.name] = module
            self._states[module.name] = LifecycleState.CREATED
            self._transitions[module.name] = []

    def unregister(self, name: str) -> bool:
        """注销模块"""
        with self._lock:
            if name not in self._modules:
                return False

            # 必须先销毁
            if self._states[name] not in (LifecycleState.DESTROYED, LifecycleState.CREATED):
                return False

            del self._modules[name]
            del self._states[name]
            del self._transitions[name]
            return True

    def get_state(self, name: str) -> Optional[LifecycleState]:
        """获取模块状态"""
        with self._lock:
            return self._states.get(name)

    def get_all_states(self) -> Dict[str, LifecycleState]:
        """获取所有模块状态"""
        with self._lock:
            return self._states.copy()

    def add_listener(self, listener: Callable[[str, StateTransition], None]) -> None:
        """添加状态转换监听器"""
        self._listeners.append(listener)

    def _notify(self, module_name: str, transition: StateTransition) -> None:
        """通知监听器"""
        for listener in self._listeners:
            try:
                listener(module_name, transition)
            except Exception:
                pass

    def _transition(self, name: str, event: LifecycleEvent) -> bool:
        """
        执行状态转换

        Returns:
            是否成功触发转换（不保证回调执行成功）
        """
        with self._lock:
            current = self._states.get(name)
            if current is None:
                return False

            transitions = VALID_TRANSITIONS.get(current, {})
            next_state = transitions.get(event)

            if next_state is None:
                return False

            self._states[name] = next_state
            return True

    def _complete_transition(self, name: str) -> None:
        """完成当前过渡状态"""
        with self._lock:
            current = self._states[name]
            completed = COMPLETION_TRANSITIONS.get(current)
            if completed:
                self._states[name] = completed

    def _record_transition(self, name: str, from_state: LifecycleState,
                           to_state: LifecycleState, event: LifecycleEvent,
                           success: bool = True, error: Optional[str] = None) -> None:
        """记录状态转换"""
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            event=event,
            success=success,
            error=error,
        )
        with self._lock:
            self._transitions[name].append(transition)
        self._notify(name, transition)

    def initialize(self, name: str) -> bool:
        """初始化单个模块"""
        module = self._modules.get(name)
        if module is None:
            return False

        # 先初始化依赖
        for dep in module.dependencies:
            dep_state = self.get_state(dep)
            if dep_state in (LifecycleState.CREATED, LifecycleState.FAILED):
                if not self.initialize(dep):
                    return False
            elif dep_state not in (LifecycleState.INITIALIZED, LifecycleState.RUNNING,
                                   LifecycleState.STARTING, LifecycleState.STOPPED):
                return False

        from_state = self.get_state(name)
        if not self._transition(name, LifecycleEvent.INITIALIZE):
            return False

        try:
            module.on_initialize()
            self._complete_transition(name)
            to_state = self.get_state(name)
            self._record_transition(name, from_state, to_state, LifecycleEvent.INITIALIZE)
            return True
        except Exception as e:
            self._states[name] = LifecycleState.FAILED
            self._record_transition(name, from_state, LifecycleState.FAILED,
                                    LifecycleEvent.INITIALIZE, False, str(e))
            return False

    def start(self, name: str) -> bool:
        """启动单个模块"""
        module = self._modules.get(name)
        if module is None:
            return False

        # 确保已初始化
        state = self.get_state(name)
        if state == LifecycleState.CREATED:
            if not self.initialize(name):
                return False

        from_state = self.get_state(name)
        if not self._transition(name, LifecycleEvent.START):
            return False

        try:
            module.on_start()
            self._complete_transition(name)
            to_state = self.get_state(name)
            self._record_transition(name, from_state, to_state, LifecycleEvent.START)
            return True
        except Exception as e:
            self._states[name] = LifecycleState.FAILED
            self._record_transition(name, from_state, LifecycleState.FAILED,
                                    LifecycleEvent.START, False, str(e))
            return False

    def stop(self, name: str) -> bool:
        """停止单个模块"""
        module = self._modules.get(name)
        if module is None:
            return False

        from_state = self.get_state(name)
        if not self._transition(name, LifecycleEvent.STOP):
            return False

        try:
            module.on_stop()
            self._complete_transition(name)
            to_state = self.get_state(name)
            self._record_transition(name, from_state, to_state, LifecycleEvent.STOP)
            return True
        except Exception as e:
            self._states[name] = LifecycleState.FAILED
            self._record_transition(name, from_state, LifecycleState.FAILED,
                                    LifecycleEvent.STOP, False, str(e))
            return False

    def destroy(self, name: str) -> bool:
        """销毁单个模块"""
        module = self._modules.get(name)
        if module is None:
            return False

        # 先停止
        state = self.get_state(name)
        if state in (LifecycleState.RUNNING, LifecycleState.STARTING):
            self.stop(name)

        from_state = self.get_state(name)
        if not self._transition(name, LifecycleEvent.DESTROY):
            return False

        try:
            module.on_destroy()
            self._complete_transition(name)
            to_state = self.get_state(name)
            self._record_transition(name, from_state, to_state, LifecycleEvent.DESTROY)
            return True
        except Exception as e:
            self._states[name] = LifecycleState.FAILED
            self._record_transition(name, from_state, LifecycleState.FAILED,
                                    LifecycleEvent.DESTROY, False, str(e))
            return False

    def initialize_all(self) -> Dict[str, bool]:
        """初始化所有模块（按依赖拓扑序）"""
        order = self._topological_sort()
        results = {}
        for name in order:
            results[name] = self.initialize(name)
        return results

    def start_all(self) -> Dict[str, bool]:
        """启动所有模块（按依赖拓扑序）"""
        order = self._topological_sort()
        results = {}
        for name in order:
            results[name] = self.start(name)
        return results

    def stop_all(self) -> Dict[str, bool]:
        """停止所有模块（按依赖拓扑逆序）"""
        order = self._topological_sort(reverse=True)
        results = {}
        for name in order:
            results[name] = self.stop(name)
        return results

    def destroy_all(self) -> Dict[str, bool]:
        """销毁所有模块（按依赖拓扑逆序）"""
        order = self._topological_sort(reverse=True)
        results = {}
        for name in order:
            results[name] = self.destroy(name)
        return results

    def _topological_sort(self, reverse: bool = False) -> List[str]:
        """拓扑排序"""
        with self._lock:
            modules = dict(self._modules)

        # Kahn算法
        in_degree: Dict[str, int] = {name: 0 for name in modules}
        adj: Dict[str, List[str]] = {name: [] for name in modules}

        for name, module in modules.items():
            for dep in module.dependencies:
                if dep in modules:
                    adj[dep].append(name)
                    in_degree[name] += 1

        queue = [name for name, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            queue.sort()
            name = queue.pop(0)
            result.append(name)
            for neighbor in adj[name]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if reverse:
            result.reverse()

        return result

    def get_transition_history(self, name: str) -> List[StateTransition]:
        """获取状态转换历史"""
        with self._lock:
            return self._transitions.get(name, [])[:]

    def is_running(self, name: str) -> bool:
        """检查模块是否运行中"""
        return self.get_state(name) == LifecycleState.RUNNING

    def is_healthy(self, name: str) -> Tuple[bool, str]:
        """检查模块健康状态"""
        module = self._modules.get(name)
        if module is None:
            return False, "Module not found"
        state = self.get_state(name)
        if state != LifecycleState.RUNNING:
            return False, f"Module not running, current state: {state.value}"
        return module.health_check()
