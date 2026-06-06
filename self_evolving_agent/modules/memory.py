"""
自驱永续进化Agent系统 — 记忆系统
阶段6：记忆系统抽象层

第一性原理：工作记忆和长期记忆是不同生理结构
- 短期记忆：快速存取，容量有限，易失
- 长期记忆：慢速存取，容量大，持久
- 协调器：管理信息在两者间的流动
"""

import time
import threading
from typing import Any, Dict, List, Optional
from collections import OrderedDict
from dataclasses import dataclass, field

from ..core.interfaces import Memory, BaseModule, AgentMessage, MessageType


@dataclass
class MemoryEntry:
    """记忆条目"""
    key: str
    data: Any
    timestamp: float
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        """更新访问信息"""
        self.access_count += 1
        self.last_access = time.time()


class ShortTermMemory(Memory, BaseModule):
    """
    短期记忆

    特性：
    - 固定容量（类似人脑的工作记忆7±2）
    - LRU淘汰策略
    - 快速读写
    """

    DEFAULT_CAPACITY = 7

    def __init__(self, module_id: str = "stm", capacity: int = DEFAULT_CAPACITY):
        BaseModule.__init__(self, module_id)
        self._capacity = capacity
        self._storage: OrderedDict[str, MemoryEntry] = OrderedDict()
        self._lock = threading.RLock()

    def store(self, key: str, data: Any, metadata: Dict[str, Any] = None) -> bool:
        """存储到短期记忆"""
        with self._lock:
            entry = MemoryEntry(
                key=key,
                data=data,
                timestamp=time.time(),
                metadata=metadata or {},
            )

            # 如果已存在，移到最新
            if key in self._storage:
                self._storage.move_to_end(key)
                self._storage[key] = entry
                return True

            # 如果满了，淘汰最旧的
            if len(self._storage) >= self._capacity:
                self._evict_oldest()

            self._storage[key] = entry
            return True

    def retrieve(self, key: str) -> Optional[Any]:
        """从短期记忆检索"""
        with self._lock:
            if key in self._storage:
                entry = self._storage[key]
                entry.touch()
                self._storage.move_to_end(key)
                return entry.data
            return None

    def forget(self, key: str) -> bool:
        """遗忘"""
        with self._lock:
            if key in self._storage:
                del self._storage[key]
                return True
            return False

    def query(self, criteria: Dict[str, Any]) -> List[Any]:
        """按条件查询"""
        results = []
        with self._lock:
            for entry in self._storage.values():
                match = True
                for key, value in criteria.items():
                    if key == "since" and entry.timestamp < value:
                        match = False
                        break
                    if key == "before" and entry.timestamp > value:
                        match = False
                        break
                    if key in entry.metadata and entry.metadata[key] != value:
                        match = False
                        break
                if match:
                    results.append(entry.data)
        return results

    def _evict_oldest(self) -> None:
        """淘汰最旧的条目"""
        if self._storage:
            self._storage.popitem(last=False)

    def get_all_keys(self) -> List[str]:
        """获取所有键"""
        with self._lock:
            return list(self._storage.keys())

    def is_full(self) -> bool:
        """是否已满"""
        with self._lock:
            return len(self._storage) >= self._capacity

    def initialize(self, config: Dict[str, Any]) -> None:
        self._capacity = config.get("capacity", self._capacity)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.SYSTEM_EVENT:
            action = message.payload.get("action")
            if action == "store":
                self.store(
                    message.payload.get("key"),
                    message.payload.get("data"),
                    message.payload.get("metadata"),
                )
            elif action == "retrieve":
                data = self.retrieve(message.payload.get("key"))
                return AgentMessage(
                    msg_type=MessageType.SYSTEM_EVENT,
                    source=self.module_id,
                    payload={"data": data},
                )
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        base.update({
            "capacity": self._capacity,
            "size": len(self._storage),
            "keys": list(self._storage.keys()),
        })
        return base


class LongTermMemory(Memory, BaseModule):
    """
    长期记忆

    特性：
    - 大容量
    - 持久化存储
    - 支持复杂查询
    """

    def __init__(self, module_id: str = "ltm"):
        BaseModule.__init__(self, module_id)
        self._storage: Dict[str, MemoryEntry] = {}
        self._lock = threading.RLock()
        self._persist_path: Optional[str] = None

    def store(self, key: str, data: Any, metadata: Dict[str, Any] = None) -> bool:
        """存储到长期记忆"""
        with self._lock:
            entry = MemoryEntry(
                key=key,
                data=data,
                timestamp=time.time(),
                metadata=metadata or {},
            )
            self._storage[key] = entry
            return True

    def retrieve(self, key: str) -> Optional[Any]:
        """从长期记忆检索"""
        with self._lock:
            if key in self._storage:
                entry = self._storage[key]
                entry.touch()
                return entry.data
            return None

    def forget(self, key: str) -> bool:
        """遗忘"""
        with self._lock:
            if key in self._storage:
                del self._storage[key]
                return True
            return False

    def query(self, criteria: Dict[str, Any]) -> List[Any]:
        """按条件查询"""
        results = []
        with self._lock:
            for entry in self._storage.values():
                match = True
                for key, value in criteria.items():
                    if key == "since" and entry.timestamp < value:
                        match = False
                        break
                    if key == "before" and entry.timestamp > value:
                        match = False
                        break
                    if key in entry.metadata and entry.metadata[key] != value:
                        match = False
                        break
                    if key == "min_access" and entry.access_count < value:
                        match = False
                        break
                if match:
                    results.append(entry.data)
        return results

    def get_keys(self) -> List[str]:
        """获取所有键"""
        with self._lock:
            return list(self._storage.keys())

    def get_size(self) -> int:
        """获取存储大小"""
        with self._lock:
            return len(self._storage)

    def initialize(self, config: Dict[str, Any]) -> None:
        self._persist_path = config.get("persist_path")
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.SYSTEM_EVENT:
            action = message.payload.get("action")
            if action == "store":
                self.store(
                    message.payload.get("key"),
                    message.payload.get("data"),
                    message.payload.get("metadata"),
                )
            elif action == "retrieve":
                data = self.retrieve(message.payload.get("key"))
                return AgentMessage(
                    msg_type=MessageType.SYSTEM_EVENT,
                    source=self.module_id,
                    payload={"data": data},
                )
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        base.update({
            "size": len(self._storage),
            "persist_path": self._persist_path,
        })
        return base


class MemoryCoordinator(BaseModule):
    """
    记忆协调器

    第一性原理：工作记忆和长期记忆需要协调，但不应直接耦合
    - 高频访问的数据保留在STM
    - 重要数据迁移到LTM
    - 定期清理和 Consolidation
    """

    def __init__(self, module_id: str = "memory_coordinator"):
        super().__init__(module_id)
        self._stm = ShortTermMemory()
        self._ltm = LongTermMemory()
        self._promotion_threshold = 3  # 访问次数阈值，超过则提升到LTM
        self._consolidation_interval = 60.0  # 秒

    def store(self, key: str, data: Any, metadata: Dict[str, Any] = None) -> bool:
        """统一存储接口"""
        # 默认存入短期记忆
        return self._stm.store(key, data, metadata)

    def retrieve(self, key: str) -> Optional[Any]:
        """统一检索接口"""
        # 先查短期记忆
        data = self._stm.retrieve(key)
        if data is not None:
            return data

        # 再查长期记忆
        data = self._ltm.retrieve(key)
        if data is not None:
            # 从LTM加载到STM（缓存）
            self._stm.store(key, data)
            return data

        return None

    def consolidate(self) -> None:
        """
        记忆巩固

        将STM中频繁访问的数据迁移到LTM
        """
        # 获取STM中所有条目
        for key in self._stm.get_all_keys():
            # 这里简化处理：定期将所有STM数据同步到LTM
            data = self._stm.retrieve(key)
            if data is not None:
                self._ltm.store(key, data)

    def initialize(self, config: Dict[str, Any]) -> None:
        stm_config = config.get("stm", {})
        ltm_config = config.get("ltm", {})
        self._promotion_threshold = config.get("promotion_threshold", self._promotion_threshold)
        self._consolidation_interval = config.get("consolidation_interval", self._consolidation_interval)

        self._stm.initialize(stm_config)
        self._ltm.initialize(ltm_config)
        self._initialized = True

    def start(self) -> None:
        self._running = True
        self._stm.start()
        self._ltm.start()

    def stop(self) -> None:
        self._running = False
        self._stm.stop()
        self._ltm.stop()

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.SYSTEM_EVENT:
            action = message.payload.get("action")
            if action == "store":
                self.store(
                    message.payload.get("key"),
                    message.payload.get("data"),
                    message.payload.get("metadata"),
                )
            elif action == "retrieve":
                data = self.retrieve(message.payload.get("key"))
                return AgentMessage(
                    msg_type=MessageType.SYSTEM_EVENT,
                    source=self.module_id,
                    payload={"data": data},
                )
            elif action == "consolidate":
                self.consolidate()
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        base.update({
            "stm": self._stm.get_state(),
            "ltm": self._ltm.get_state(),
        })
        return base
