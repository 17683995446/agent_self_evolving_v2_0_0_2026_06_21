"""
阶段126: 持久化存储层

第一性原理:
1. 持久化 = 将内存状态保存到非易失存储
2. 存储抽象应支持多种后端（文件、SQLite等）
3. 序列化/反序列化必须可逆
4. 原子写入：要么全部成功，要么全部失败

提供:
- StorageInterface: 存储抽象接口
- JSONStorage: JSON文件存储（零依赖）
- MemoryPersistence: 记忆持久化
- CausalGraphPersistence: 因果图持久化
- PersistenceManager: 持久化管理器
"""

import os
import json
import time
import threading
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type
from enum import Enum


# ============================================================
# 数据结构
# ============================================================

class StorageType(Enum):
    """存储类型"""
    JSON = "json"
    MEMORY = "memory"          # 纯内存（测试用）
    SQLITE = "sqlite"          # 预留


@dataclass
class StorageRecord:
    """存储记录"""
    key: str
    value: Any
    namespace: str = "default"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "namespace": self.namespace,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StorageRecord":
        return cls(
            key=data.get("key", ""),
            value=data.get("value"),
            namespace=data.get("namespace", "default"),
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


# ============================================================
# 存储抽象接口
# ============================================================

class StorageInterface(ABC):
    """
    存储抽象接口

    第一性原理：
    - 所有存储都支持CRUD
    - 命名空间隔离不同类型数据
    - 原子操作保证一致性
    """

    def __init__(self, storage_id: str = "storage"):
        self.storage_id = storage_id
        self._lock = threading.RLock()

    @abstractmethod
    def save(self, key: str, value: Any, namespace: str = "default") -> bool:
        """保存"""
        pass

    @abstractmethod
    def load(self, key: str, namespace: str = "default") -> Optional[Any]:
        """加载"""
        pass

    @abstractmethod
    def delete(self, key: str, namespace: str = "default") -> bool:
        """删除"""
        pass

    @abstractmethod
    def list_keys(self, namespace: str = "default") -> List[str]:
        """列出键"""
        pass

    @abstractmethod
    def list_namespaces(self) -> List[str]:
        """列出命名空间"""
        pass

    @abstractmethod
    def exists(self, key: str, namespace: str = "default") -> bool:
        """检查存在"""
        pass

    @abstractmethod
    def clear_namespace(self, namespace: str) -> int:
        """清除命名空间，返回删除数量"""
        pass

    @abstractmethod
    def clear_all(self) -> int:
        """清除所有，返回删除数量"""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {"storage_id": self.storage_id, "type": self.__class__.__name__}


# ============================================================
# 内存存储（测试用）
# ============================================================

class MemoryStorage(StorageInterface):
    """内存存储"""

    def __init__(self, storage_id: str = "memory_storage"):
        super().__init__(storage_id)
        self._data: Dict[str, Dict[str, Any]] = {}  # namespace -> {key: value}

    def save(self, key: str, value: Any, namespace: str = "default") -> bool:
        # 防御：None key
        if not key:
            return False
        with self._lock:
            if namespace not in self._data:
                self._data[namespace] = {}
            self._data[namespace][key] = value
        return True

    def load(self, key: str, namespace: str = "default") -> Optional[Any]:
        with self._lock:
            return self._data.get(namespace, {}).get(key)

    def delete(self, key: str, namespace: str = "default") -> bool:
        with self._lock:
            if namespace in self._data and key in self._data[namespace]:
                del self._data[namespace][key]
                return True
            return False

    def list_keys(self, namespace: str = "default") -> List[str]:
        with self._lock:
            return list(self._data.get(namespace, {}).keys())

    def list_namespaces(self) -> List[str]:
        with self._lock:
            return list(self._data.keys())

    def exists(self, key: str, namespace: str = "default") -> bool:
        with self._lock:
            return namespace in self._data and key in self._data[namespace]

    def clear_namespace(self, namespace: str) -> int:
        with self._lock:
            if namespace in self._data:
                count = len(self._data[namespace])
                del self._data[namespace]
                return count
            return 0

    def clear_all(self) -> int:
        with self._lock:
            total = sum(len(ns) for ns in self._data.values())
            self._data.clear()
            return total

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "storage_id": self.storage_id,
                "type": "memory",
                "namespaces": len(self._data),
                "total_keys": sum(len(ns) for ns in self._data.values()),
            }


# ============================================================
# JSON文件存储
# ============================================================

class JSONStorage(StorageInterface):
    """
    JSON文件存储

    第一性原理：
    - 每个命名空间一个JSON文件
    - 原子写入：先写临时文件，再重命名
    - 零依赖（仅使用标准库）
    """

    def __init__(self, base_path: str, storage_id: str = "json_storage"):
        super().__init__(storage_id)
        # 防御：base_path必须存在
        if not base_path:
            raise ValueError("base_path is required")
        self._base_path = os.path.abspath(base_path)
        os.makedirs(self._base_path, exist_ok=True)

    def _namespace_path(self, namespace: str) -> str:
        """命名空间文件路径"""
        # 防御：命名空间安全化
        safe_ns = "".join(c if c.isalnum() or c in "._-" else "_" for c in namespace)
        return os.path.join(self._base_path, f"{safe_ns}.json")

    def _load_namespace(self, namespace: str) -> Dict[str, Any]:
        """加载命名空间数据"""
        path = self._namespace_path(namespace)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_namespace(self, namespace: str, data: Dict[str, Any]) -> bool:
        """保存命名空间数据（原子写入）"""
        path = self._namespace_path(namespace)
        tmp_path = f"{path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str, indent=2)
            # 原子重命名
            os.replace(tmp_path, path)
            return True
        except (IOError, OSError):
            # 清理临时文件
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return False

    def save(self, key: str, value: Any, namespace: str = "default") -> bool:
        if not key:
            return False
        with self._lock:
            data = self._load_namespace(namespace)
            data[key] = value
            return self._save_namespace(namespace, data)

    def load(self, key: str, namespace: str = "default") -> Optional[Any]:
        with self._lock:
            data = self._load_namespace(namespace)
            return data.get(key)

    def delete(self, key: str, namespace: str = "default") -> bool:
        with self._lock:
            data = self._load_namespace(namespace)
            if key in data:
                del data[key]
                return self._save_namespace(namespace, data)
            return False

    def list_keys(self, namespace: str = "default") -> List[str]:
        with self._lock:
            data = self._load_namespace(namespace)
            return list(data.keys())

    def list_namespaces(self) -> List[str]:
        with self._lock:
            namespaces = []
            for fname in os.listdir(self._base_path):
                if fname.endswith(".json"):
                    namespaces.append(fname[:-5])
            return namespaces

    def exists(self, key: str, namespace: str = "default") -> bool:
        with self._lock:
            data = self._load_namespace(namespace)
            return key in data

    def clear_namespace(self, namespace: str) -> int:
        with self._lock:
            path = self._namespace_path(namespace)
            if os.path.exists(path):
                data = self._load_namespace(namespace)
                count = len(data)
                os.remove(path)
                return count
            return 0

    def clear_all(self) -> int:
        with self._lock:
            total = 0
            for fname in os.listdir(self._base_path):
                if fname.endswith(".json"):
                    path = os.path.join(self._base_path, fname)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        total += len(data)
                        os.remove(path)
                    except (IOError, json.JSONDecodeError):
                        pass
            return total

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            namespaces = self.list_namespaces()
            total_keys = 0
            for ns in namespaces:
                total_keys += len(self._load_namespace(ns))
            return {
                "storage_id": self.storage_id,
                "type": "json",
                "base_path": self._base_path,
                "namespaces": len(namespaces),
                "total_keys": total_keys,
            }


# ============================================================
# 记忆持久化
# ============================================================

class MemoryPersistence:
    """
    记忆持久化

    第一性原理：
    - 记忆是Agent的核心状态，必须可持久化
    - 保存/恢复分层记忆
    """

    def __init__(self, storage: StorageInterface):
        self._storage = storage
        self._namespace = "memory"
        self._lock = threading.RLock()

    def save_memory(self, memory_id: str, memory_data: Dict[str, Any]) -> bool:
        """保存单条记忆"""
        # 防御：None输入
        if not memory_id or memory_data is None:
            return False
        record = {
            "memory_id": memory_id,
            "data": memory_data,
            "saved_at": time.time(),
        }
        return self._storage.save(memory_id, record, self._namespace)

    def load_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """加载单条记忆"""
        record = self._storage.load(memory_id, self._namespace)
        if record is None:
            return None
        return record.get("data")

    def save_all_memories(self, memories: Dict[str, Dict[str, Any]]) -> int:
        """批量保存记忆"""
        count = 0
        for memory_id, memory_data in memories.items():
            if self.save_memory(memory_id, memory_data):
                count += 1
        return count

    def load_all_memories(self) -> Dict[str, Dict[str, Any]]:
        """加载所有记忆"""
        keys = self._storage.list_keys(self._namespace)
        result = {}
        for key in keys:
            data = self.load_memory(key)
            if data is not None:
                result[key] = data
        return result

    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        return self._storage.delete(memory_id, self._namespace)

    def list_memory_ids(self) -> List[str]:
        """列出记忆ID"""
        return self._storage.list_keys(self._namespace)

    def clear_all(self) -> int:
        """清除所有记忆"""
        return self._storage.clear_namespace(self._namespace)


# ============================================================
# 因果图持久化
# ============================================================

class CausalGraphPersistence:
    """
    因果图持久化

    第一性原理：
    - 因果图是Agent理解世界的核心结构
    - 节点和边需要分别持久化
    """

    def __init__(self, storage: StorageInterface):
        self._storage = storage
        self._nodes_namespace = "causal_nodes"
        self._edges_namespace = "causal_edges"
        self._lock = threading.RLock()

    def save_node(self, node_id: str, node_data: Dict[str, Any]) -> bool:
        """保存节点"""
        if not node_id:
            return False
        return self._storage.save(node_id, node_data, self._nodes_namespace)

    def load_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """加载节点"""
        return self._storage.load(node_id, self._nodes_namespace)

    def delete_node(self, node_id: str) -> bool:
        """删除节点"""
        return self._storage.delete(node_id, self._nodes_namespace)

    def list_nodes(self) -> List[str]:
        """列出节点"""
        return self._storage.list_keys(self._nodes_namespace)

    def save_edge(self, edge_id: str, edge_data: Dict[str, Any]) -> bool:
        """保存边"""
        if not edge_id:
            return False
        return self._storage.save(edge_id, edge_data, self._edges_namespace)

    def load_edge(self, edge_id: str) -> Optional[Dict[str, Any]]:
        """加载边"""
        return self._storage.load(edge_id, self._edges_namespace)

    def delete_edge(self, edge_id: str) -> bool:
        """删除边"""
        return self._storage.delete(edge_id, self._edges_namespace)

    def list_edges(self) -> List[str]:
        """列出边"""
        return self._storage.list_keys(self._edges_namespace)

    def save_graph(self, nodes: Dict[str, Dict[str, Any]], edges: Dict[str, Dict[str, Any]]) -> int:
        """保存整个图"""
        count = 0
        for node_id, node_data in nodes.items():
            if self.save_node(node_id, node_data):
                count += 1
        for edge_id, edge_data in edges.items():
            if self.save_edge(edge_id, edge_data):
                count += 1
        return count

    def load_graph(self) -> Dict[str, Any]:
        """加载整个图"""
        nodes = {}
        for node_id in self.list_nodes():
            data = self.load_node(node_id)
            if data is not None:
                nodes[node_id] = data

        edges = {}
        for edge_id in self.list_edges():
            data = self.load_edge(edge_id)
            if data is not None:
                edges[edge_id] = data

        return {"nodes": nodes, "edges": edges}

    def clear_all(self) -> int:
        """清除所有"""
        count = self._storage.clear_namespace(self._nodes_namespace)
        count += self._storage.clear_namespace(self._edges_namespace)
        return count


# ============================================================
# 持久化管理器
# ============================================================

class PersistenceManager:
    """
    持久化管理器

    第一性原理：
    - 统一管理多种持久化需求
    - 提供save_all/load_all的便捷接口
    """

    def __init__(self, storage: StorageInterface, manager_id: str = "persistence"):
        self.manager_id = manager_id
        self._storage = storage
        self._memory_persistence = MemoryPersistence(storage)
        self._causal_persistence = CausalGraphPersistence(storage)
        self._lock = threading.RLock()

    @property
    def storage(self) -> StorageInterface:
        return self._storage

    @property
    def memory(self) -> MemoryPersistence:
        return self._memory_persistence

    @property
    def causal_graph(self) -> CausalGraphPersistence:
        return self._causal_persistence

    def save_state(self, key: str, state: Dict[str, Any], namespace: str = "state") -> bool:
        """保存通用状态"""
        return self._storage.save(key, state, namespace)

    def load_state(self, key: str, namespace: str = "state") -> Optional[Dict[str, Any]]:
        """加载通用状态"""
        return self._storage.load(key, namespace)

    def save_checkpoint(self, checkpoint_id: str, state: Dict[str, Any]) -> bool:
        """保存检查点"""
        record = {
            "checkpoint_id": checkpoint_id,
            "state": state,
            "timestamp": time.time(),
        }
        return self._storage.save(checkpoint_id, record, "checkpoints")

    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """加载检查点"""
        record = self._storage.load(checkpoint_id, "checkpoints")
        if record is None:
            return None
        return record.get("state")

    def list_checkpoints(self) -> List[str]:
        """列出检查点"""
        return self._storage.list_keys("checkpoints")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "manager_id": self.manager_id,
            "storage_stats": self._storage.get_stats(),
            "memory_count": len(self._memory_persistence.list_memory_ids()),
            "causal_nodes": len(self._causal_persistence.list_nodes()),
            "causal_edges": len(self._causal_persistence.list_edges()),
            "checkpoints": len(self.list_checkpoints()),
        }

    def clear_all(self) -> int:
        """清除所有"""
        return self._storage.clear_all()


# ============================================================
# 便捷函数
# ============================================================

def create_memory_storage(storage_id: str = "memory_storage") -> MemoryStorage:
    """创建内存存储"""
    return MemoryStorage(storage_id)


def create_json_storage(base_path: str, storage_id: str = "json_storage") -> JSONStorage:
    """创建JSON存储"""
    return JSONStorage(base_path, storage_id)


def create_persistence_manager(
    storage: Optional[StorageInterface] = None,
    manager_id: str = "persistence",
) -> PersistenceManager:
    """创建持久化管理器"""
    if storage is None:
        storage = MemoryStorage()
    return PersistenceManager(storage, manager_id)
