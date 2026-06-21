"""
阶段131: 分布式支持层 — 节点协作、任务分发、容错

第一性原理:
1. 分布式 = 多节点协作：单机能力有限，多节点可水平扩展（Scale-Out）
2. 节点发现：节点需要知道彼此存在 → 注册中心 + 心跳机制
3. 任务分发：任务需分配到合适节点 → 负载均衡策略（轮询/最少连接/一致性哈希）
4. 状态同步：节点间需共享状态 → 最终一致性 / 强一致性协议
5. 容错：节点可能故障 → 心跳超时检测、自动重试、故障转移
6. 通信：节点间需可靠通信 → 消息队列 / RPC抽象

设计原则:
- 接口抽象：通信层可替换（模拟/HTTP/gRPC）
- 单机可测试：默认使用模拟网络，无需真实多机
- 渐进式：从单机到分布式平滑过渡

提供:
- NodeInfo/NodeRole/NodeStatus: 节点信息模型
- NodeRegistry: 节点注册中心（注册、发现、心跳）
- TaskDistributor: 任务分发器（多种负载均衡策略）
- StateSynchronizer: 状态同步器
- FaultDetector: 故障检测器
- MessageBus: 节点间消息总线
- DistributedCoordinator: 分布式协调器（集成）
"""

import time
import threading
import hashlib
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque


# ============================================================
# 节点模型
# ============================================================

class NodeRole(Enum):
    """节点角色"""
    LEADER = "leader"
    FOLLOWER = "follower"
    WORKER = "worker"
    COORDINATOR = "coordinator"


class NodeStatus(Enum):
    """节点状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    SUSPECT = "suspect"  # 可疑（心跳超时但未确认故障）
    LEAVING = "leaving"  # 正在离开


@dataclass
class NodeInfo:
    """节点信息"""
    node_id: str
    host: str = "localhost"
    port: int = 0
    role: NodeRole = NodeRole.WORKER
    status: NodeStatus = NodeStatus.ONLINE
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    load: float = 0.0  # 负载指标 0-1

    def is_alive(self) -> bool:
        """节点是否存活"""
        return self.status in (NodeStatus.ONLINE, NodeStatus.SUSPECT)

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port,
            "role": self.role.value,
            "status": self.status.value,
            "metadata": self.metadata,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "load": self.load,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeInfo":
        """从字典创建"""
        return cls(
            node_id=data["node_id"],
            host=data.get("host", "localhost"),
            port=data.get("port", 0),
            role=NodeRole(data.get("role", "worker")),
            status=NodeStatus(data.get("status", "online")),
            metadata=data.get("metadata", {}),
            registered_at=data.get("registered_at", time.time()),
            last_heartbeat=data.get("last_heartbeat", time.time()),
            load=data.get("load", 0.0),
        )


# ============================================================
# 节点注册中心
# ============================================================

class NodeRegistry:
    """
    节点注册中心

    管理节点注册、发现、心跳。
    线程安全。
    """

    def __init__(self, heartbeat_timeout: float = 30.0, suspect_timeout: float = 60.0):
        self._nodes: Dict[str, NodeInfo] = {}
        self._heartbeat_timeout = heartbeat_timeout
        self._suspect_timeout = suspect_timeout
        self._lock = threading.RLock()
        self._listeners: List[Callable[[str, NodeStatus], None]] = []
        self._metrics = {
            "registrations": 0,
            "heartbeats": 0,
            "failures": 0,
            "evictions": 0,
        }

    def register(self, node: NodeInfo) -> bool:
        """注册节点"""
        with self._lock:
            if node.node_id in self._nodes:
                return False
            node.registered_at = time.time()
            node.last_heartbeat = time.time()
            self._nodes[node.node_id] = node
            self._metrics["registrations"] += 1
            self._notify_listeners(node.node_id, node.status)
            return True

    def deregister(self, node_id: str) -> bool:
        """注销节点"""
        with self._lock:
            if node_id not in self._nodes:
                return False
            node = self._nodes.pop(node_id)
            node.status = NodeStatus.OFFLINE
            self._notify_listeners(node_id, NodeStatus.OFFLINE)
            return True

    def heartbeat(self, node_id: str, load: float = 0.0) -> bool:
        """更新节点心跳"""
        with self._lock:
            if node_id not in self._nodes:
                return False
            node = self._nodes[node_id]
            node.last_heartbeat = time.time()
            node.load = max(0.0, min(1.0, load))
            if node.status == NodeStatus.SUSPECT:
                node.status = NodeStatus.ONLINE
                self._notify_listeners(node_id, NodeStatus.ONLINE)
            self._metrics["heartbeats"] += 1
            return True

    def get_node(self, node_id: str) -> Optional[NodeInfo]:
        """获取节点信息"""
        with self._lock:
            return self._nodes.get(node_id)

    def list_nodes(
        self,
        status: Optional[NodeStatus] = None,
        role: Optional[NodeRole] = None,
    ) -> List[NodeInfo]:
        """列出节点"""
        with self._lock:
            nodes = list(self._nodes.values())
            if status:
                nodes = [n for n in nodes if n.status == status]
            if role:
                nodes = [n for n in nodes if n.role == role]
            return nodes

    def get_alive_nodes(self) -> List[NodeInfo]:
        """获取存活节点"""
        with self._lock:
            return [n for n in self._nodes.values() if n.is_alive()]

    def check_health(self) -> Dict[str, List[str]]:
        """
        检查节点健康状态

        标记心跳超时的节点为SUSPECT，超时过久的节点为OFFLINE。
        """
        now = time.time()
        result = {"suspected": [], "expired": []}
        with self._lock:
            to_remove = []
            for node_id, node in self._nodes.items():
                elapsed = now - node.last_heartbeat
                if elapsed > self._suspect_timeout:
                    node.status = NodeStatus.OFFLINE
                    result["expired"].append(node_id)
                    to_remove.append(node_id)
                    self._metrics["evictions"] += 1
                    self._notify_listeners(node_id, NodeStatus.OFFLINE)
                elif elapsed > self._heartbeat_timeout:
                    if node.status != NodeStatus.SUSPECT:
                        node.status = NodeStatus.SUSPECT
                        result["suspected"].append(node_id)
                        self._metrics["failures"] += 1
                        self._notify_listeners(node_id, NodeStatus.SUSPECT)

            for node_id in to_remove:
                self._nodes.pop(node_id, None)

        return result

    def add_listener(self, callback: Callable[[str, NodeStatus], None]) -> None:
        """添加状态变更监听器"""
        with self._lock:
            self._listeners.append(callback)

    def _notify_listeners(self, node_id: str, status: NodeStatus) -> None:
        """通知监听器"""
        for listener in self._listeners:
            try:
                listener(node_id, status)
            except Exception:
                pass

    def node_count(self) -> int:
        """节点数量"""
        with self._lock:
            return len(self._nodes)

    def metrics(self) -> Dict[str, int]:
        """获取指标"""
        with self._lock:
            return dict(self._metrics)

    def clear(self) -> None:
        """清空注册中心"""
        with self._lock:
            self._nodes.clear()


# ============================================================
# 任务分发器
# ============================================================

class LoadBalanceStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOAD = "least_load"
    RANDOM = "random"
    CONSISTENT_HASH = "consistent_hash"


class TaskDistributor:
    """
    任务分发器

    根据负载均衡策略将任务分配到节点。
    """

    def __init__(
        self,
        registry: NodeRegistry,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
    ):
        self._registry = registry
        self._strategy = strategy
        self._rr_index = 0
        self._lock = threading.RLock()
        self._consistent_hash_ring: Dict[int, str] = {}
        self._hash_ring_lock = threading.RLock()

    def assign(self, task_key: Optional[str] = None) -> Optional[NodeInfo]:
        """分配节点"""
        nodes = self._registry.get_alive_nodes()
        if not nodes:
            return None

        if self._strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._round_robin(nodes)
        elif self._strategy == LoadBalanceStrategy.LEAST_LOAD:
            return self._least_load(nodes)
        elif self._strategy == LoadBalanceStrategy.RANDOM:
            return random.choice(nodes)
        elif self._strategy == LoadBalanceStrategy.CONSISTENT_HASH:
            return self._consistent_hash(nodes, task_key or "")
        return nodes[0]

    def _round_robin(self, nodes: List[NodeInfo]) -> NodeInfo:
        """轮询"""
        with self._lock:
            node = nodes[self._rr_index % len(nodes)]
            self._rr_index = (self._rr_index + 1) % len(nodes)
            return node

    def _least_load(self, nodes: List[NodeInfo]) -> NodeInfo:
        """最少负载"""
        return min(nodes, key=lambda n: n.load)

    def _consistent_hash(self, nodes: List[NodeInfo], key: str) -> NodeInfo:
        """一致性哈希"""
        with self._hash_ring_lock:
            # 重建哈希环
            self._consistent_hash_ring.clear()
            for node in nodes:
                # 每个节点虚拟150个节点
                for i in range(150):
                    hash_val = self._hash(f"{node.node_id}:{i}")
                    self._consistent_hash_ring[hash_val] = node.node_id

            if not self._consistent_hash_ring:
                return nodes[0]

            # 查找key对应的节点
            key_hash = self._hash(key)
            sorted_hashes = sorted(self._consistent_hash_ring.keys())
            for h in sorted_hashes:
                if h >= key_hash:
                    node_id = self._consistent_hash_ring[h]
                    node = self._registry.get_node(node_id)
                    if node and node.is_alive():
                        return node

            # 回到环起点
            node_id = self._consistent_hash_ring[sorted_hashes[0]]
            node = self._registry.get_node(node_id)
            return node if node else nodes[0]

    @staticmethod
    def _hash(key: str) -> int:
        """哈希函数"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def distribute(self, tasks: List[Any], key_fn: Optional[Callable] = None) -> Dict[str, List[Any]]:
        """
        批量分发任务

        返回 {node_id: [tasks]} 映射。
        """
        distribution: Dict[str, List[Any]] = defaultdict(list)
        for task in tasks:
            key = key_fn(task) if key_fn else None
            node = self.assign(key)
            if node:
                distribution[node.node_id].append(task)
            else:
                distribution["__unassigned__"].append(task)
        return dict(distribution)

    def set_strategy(self, strategy: LoadBalanceStrategy) -> None:
        """设置负载均衡策略"""
        with self._lock:
            self._strategy = strategy


# ============================================================
# 状态同步器
# ============================================================

class StateSynchronizer:
    """
    状态同步器

    在节点间同步状态。
    支持最终一致性模型。
    """

    def __init__(self, node_id: str):
        self._node_id = node_id
        self._state: Dict[str, Any] = {}
        self._version: Dict[str, int] = {}
        self._lock = threading.RLock()
        self._peers: Dict[str, "StateSynchronizer"] = {}  # 模拟网络中的对等节点
        self._sync_handlers: List[Callable[[Dict[str, Any]], None]] = []

    def set(self, key: str, value: Any) -> None:
        """设置状态并同步"""
        with self._lock:
            self._state[key] = value
            self._version[key] = self._version.get(key, 0) + 1
            self._sync_to_peers(key, value, self._version[key])

    def get(self, key: str, default: Any = None) -> Any:
        """获取状态"""
        with self._lock:
            return self._state.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """获取所有状态"""
        with self._lock:
            return dict(self._state)

    def merge(self, remote_state: Dict[str, Any], remote_versions: Dict[str, int]) -> None:
        """合并远程状态（基于版本号）"""
        with self._lock:
            for key, value in remote_state.items():
                remote_ver = remote_versions.get(key, 0)
                local_ver = self._version.get(key, 0)
                if remote_ver > local_ver:
                    self._state[key] = value
                    self._version[key] = remote_ver

    def add_peer(self, peer: "StateSynchronizer") -> None:
        """添加对等节点"""
        with self._lock:
            self._peers[peer._node_id] = peer

    def remove_peer(self, node_id: str) -> None:
        """移除对等节点"""
        with self._lock:
            self._peers.pop(node_id, None)

    def _sync_to_peers(self, key: str, value: Any, version: int) -> None:
        """同步到对等节点"""
        for peer in self._peers.values():
            try:
                peer.merge({key: value}, {key: version})
            except Exception:
                pass

    def sync_all(self) -> None:
        """全量同步"""
        with self._lock:
            state = dict(self._state)
            versions = dict(self._version)
        for peer in self._peers.values():
            try:
                peer.merge(state, versions)
            except Exception:
                pass

    def add_sync_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """添加同步处理器"""
        with self._lock:
            self._sync_handlers.append(handler)

    def get_version(self, key: str) -> int:
        """获取键的版本号"""
        with self._lock:
            return self._version.get(key, 0)

    def clear(self) -> None:
        """清空状态"""
        with self._lock:
            self._state.clear()
            self._version.clear()


# ============================================================
# 故障检测器
# ============================================================

class FaultDetector:
    """
    故障检测器

    基于心跳超时检测节点故障。
    支持Phi Accrual故障检测算法的简化版。
    """

    def __init__(
        self,
        registry: NodeRegistry,
        check_interval: float = 5.0,
        heartbeat_timeout: float = 15.0,
        max_retries: int = 3,
    ):
        self._registry = registry
        self._check_interval = check_interval
        self._heartbeat_timeout = heartbeat_timeout
        self._max_retries = max_retries
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._retry_count: Dict[str, int] = defaultdict(int)
        self._failure_handlers: List[Callable[[str], None]] = []
        self._recovery_handlers: List[Callable[[str], None]] = []

    def start(self) -> None:
        """启动故障检测"""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """停止故障检测"""
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)

    def _run(self) -> None:
        """运行检测循环"""
        while self._running:
            try:
                self.check()
            except Exception:
                pass
            time.sleep(self._check_interval)

    def check(self) -> Dict[str, List[str]]:
        """执行一次健康检查"""
        result = self._registry.check_health()
        for node_id in result.get("expired", []):
            self._handle_failure(node_id)
        for node_id in result.get("suspected", []):
            self._handle_suspect(node_id)
        # 检查恢复
        for node in self._registry.list_nodes(status=NodeStatus.ONLINE):
            if self._retry_count[node.node_id] > 0:
                self._retry_count[node.node_id] = 0
                self._handle_recovery(node.node_id)
        return result

    def _handle_failure(self, node_id: str) -> None:
        """处理故障"""
        self._retry_count[node_id] += 1
        for handler in self._failure_handlers:
            try:
                handler(node_id)
            except Exception:
                pass

    def _handle_suspect(self, node_id: str) -> None:
        """处理可疑节点"""
        # 标记为可疑，增加重试计数以便恢复检测
        self._retry_count[node_id] += 1

    def _handle_recovery(self, node_id: str) -> None:
        """处理节点恢复"""
        for handler in self._recovery_handlers:
            try:
                handler(node_id)
            except Exception:
                pass

    def on_failure(self, handler: Callable[[str], None]) -> None:
        """注册故障处理器"""
        with self._lock:
            self._failure_handlers.append(handler)

    def on_recovery(self, handler: Callable[[str], None]) -> None:
        """注册恢复处理器"""
        with self._lock:
            self._recovery_handlers.append(handler)

    def is_node_healthy(self, node_id: str) -> bool:
        """检查节点是否健康"""
        node = self._registry.get_node(node_id)
        if not node:
            return False
        elapsed = time.time() - node.last_heartbeat
        return elapsed < self._heartbeat_timeout and node.status == NodeStatus.ONLINE


# ============================================================
# 消息总线
# ============================================================

@dataclass
class DistributedMessage:
    """分布式消息"""
    source: str
    target: str  # "*" 表示广播
    topic: str
    payload: Any
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: f"msg_{int(time.time()*1000000)}")


class MessageBus:
    """
    节点间消息总线

    发布/订阅模式，支持点对点和广播。
    """

    def __init__(self, node_id: str):
        self._node_id = node_id
        self._subscribers: Dict[str, List[Callable[[DistributedMessage], None]]] = defaultdict(list)
        self._message_queue: deque = deque()
        self._lock = threading.RLock()
        self._peers: Dict[str, "MessageBus"] = {}
        self._delivered: Set[str] = set()  # 已投递消息ID（去重）
        self._max_delivered = 10000

    def publish(self, topic: str, payload: Any, target: str = "*") -> str:
        """发布消息"""
        msg = DistributedMessage(
            source=self._node_id,
            target=target,
            topic=topic,
            payload=payload,
        )
        self._deliver(msg)
        # 转发给对等节点
        for peer_id, peer in self._peers.items():
            if target == "*" or target == peer_id:
                try:
                    peer._receive(msg)
                except Exception:
                    pass
        return msg.message_id

    def subscribe(self, topic: str, handler: Callable[[DistributedMessage], None]) -> None:
        """订阅主题"""
        with self._lock:
            self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Callable[[DistributedMessage], None]) -> None:
        """取消订阅"""
        with self._lock:
            if topic in self._subscribers:
                self._subscribers[topic] = [
                    h for h in self._subscribers[topic] if h != handler
                ]

    def _receive(self, msg: DistributedMessage) -> None:
        """接收来自对等节点的消息"""
        with self._lock:
            if msg.message_id in self._delivered:
                return  # 去重
            self._delivered.add(msg.message_id)
            # 限制去重集合大小
            if len(self._delivered) > self._max_delivered:
                # 移除最早的一半
                to_remove = list(self._delivered)[:self._max_delivered // 2]
                for mid in to_remove:
                    self._delivered.discard(mid)
        self._deliver(msg)

    def _deliver(self, msg: DistributedMessage) -> None:
        """投递消息给订阅者"""
        with self._lock:
            handlers = list(self._subscribers.get(msg.topic, []))
            handlers.extend(self._subscribers.get("*", []))  # 通配订阅
        for handler in handlers:
            try:
                handler(msg)
            except Exception:
                pass

    def add_peer(self, peer: "MessageBus") -> None:
        """添加对等节点"""
        with self._lock:
            self._peers[peer._node_id] = peer

    def remove_peer(self, node_id: str) -> None:
        """移除对等节点"""
        with self._lock:
            self._peers.pop(node_id, None)

    def peer_count(self) -> int:
        """对等节点数"""
        with self._lock:
            return len(self._peers)


# ============================================================
# 分布式协调器
# ============================================================

class DistributedCoordinator:
    """
    分布式协调器

    集成节点注册、任务分发、状态同步、故障检测、消息总线。
    提供统一的分布式协调接口。
    """

    def __init__(
        self,
        node_id: str,
        role: NodeRole = NodeRole.WORKER,
        host: str = "localhost",
        port: int = 0,
        heartbeat_timeout: float = 30.0,
    ):
        self._node_info = NodeInfo(
            node_id=node_id,
            host=host,
            port=port,
            role=role,
        )
        self._registry = NodeRegistry(heartbeat_timeout=heartbeat_timeout)
        self._distributor = TaskDistributor(self._registry)
        self._state_sync = StateSynchronizer(node_id)
        self._fault_detector = FaultDetector(self._registry)
        self._message_bus = MessageBus(node_id)
        self._lock = threading.RLock()
        self._started = False

        # 注册自身
        self._registry.register(self._node_info)

    @property
    def node_id(self) -> str:
        return self._node_info.node_id

    @property
    def node_info(self) -> NodeInfo:
        return self._node_info

    @property
    def registry(self) -> NodeRegistry:
        return self._registry

    @property
    def distributor(self) -> TaskDistributor:
        return self._distributor

    @property
    def state_sync(self) -> StateSynchronizer:
        return self._state_sync

    @property
    def fault_detector(self) -> FaultDetector:
        return self._fault_detector

    @property
    def message_bus(self) -> MessageBus:
        return self._message_bus

    def start(self) -> None:
        """启动协调器"""
        with self._lock:
            if self._started:
                return
            self._started = True
            self._fault_detector.start()

    def stop(self) -> None:
        """停止协调器"""
        with self._lock:
            if not self._started:
                return
            self._started = False
            self._fault_detector.stop()
            self._registry.deregister(self.node_id)

    def heartbeat(self, load: float = 0.0) -> None:
        """发送心跳"""
        self._registry.heartbeat(self.node_id, load)

    def join_cluster(self, peer: "DistributedCoordinator") -> bool:
        """加入集群（连接到对等节点）"""
        # 注册对等节点
        peer_node = peer.node_info
        self._registry.register(NodeInfo(
            node_id=peer_node.node_id,
            host=peer_node.host,
            port=peer_node.port,
            role=peer_node.role,
        ))
        # 互相注册
        peer._registry.register(NodeInfo(
            node_id=self._node_info.node_id,
            host=self._node_info.host,
            port=self._node_info.port,
            role=self._node_info.role,
        ))
        # 建立通信通道
        self._state_sync.add_peer(peer._state_sync)
        peer._state_sync.add_peer(self._state_sync)
        self._message_bus.add_peer(peer._message_bus)
        peer._message_bus.add_peer(self._message_bus)
        return True

    def leave_cluster(self) -> None:
        """离开集群"""
        self._node_info.status = NodeStatus.LEAVING
        self._registry.deregister(self.node_id)
        self._state_sync._peers.clear()
        self._message_bus._peers.clear()

    def assign_task(self, task_key: Optional[str] = None) -> Optional[NodeInfo]:
        """分配任务到节点"""
        return self._distributor.assign(task_key)

    def set_state(self, key: str, value: Any) -> None:
        """设置分布式状态"""
        self._state_sync.set(key, value)

    def get_state(self, key: str, default: Any = None) -> Any:
        """获取分布式状态"""
        return self._state_sync.get(key, default)

    def publish(self, topic: str, payload: Any, target: str = "*") -> str:
        """发布消息"""
        return self._message_bus.publish(topic, payload, target)

    def subscribe(self, topic: str, handler: Callable[[DistributedMessage], None]) -> None:
        """订阅消息"""
        self._message_bus.subscribe(topic, handler)

    def cluster_size(self) -> int:
        """集群大小"""
        return self._registry.node_count()

    def get_cluster_nodes(self) -> List[NodeInfo]:
        """获取集群所有节点"""
        return self._registry.list_nodes()

    def status(self) -> Dict[str, Any]:
        """获取协调器状态"""
        return {
            "node_id": self.node_id,
            "node_status": self._node_info.status.value,
            "node_role": self._node_info.role.value,
            "cluster_size": self.cluster_size(),
            "alive_nodes": len(self._registry.get_alive_nodes()),
            "registry_metrics": self._registry.metrics(),
            "started": self._started,
        }


# ============================================================
# 便捷函数
# ============================================================

def create_dist_coordinator(
    node_id: str,
    role: NodeRole = NodeRole.WORKER,
    host: str = "localhost",
    port: int = 0,
) -> DistributedCoordinator:
    """创建分布式协调器"""
    return DistributedCoordinator(
        node_id=node_id,
        role=role,
        host=host,
        port=port,
    )


def create_cluster(
    node_ids: List[str],
    role: NodeRole = NodeRole.WORKER,
) -> List[DistributedCoordinator]:
    """创建集群（模拟多节点）"""
    coordinators = [
        create_dist_coordinator(node_id=nid, role=role)
        for nid in node_ids
    ]
    # 互相连接
    for i, coord in enumerate(coordinators):
        for j, peer in enumerate(coordinators):
            if i != j:
                coord.join_cluster(peer)
    return coordinators
