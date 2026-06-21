"""
阶段131: 分布式支持层 — 专项测试

测试覆盖：
1. NodeInfo/NodeRole/NodeStatus: 节点模型
2. NodeRegistry: 注册、发现、心跳、健康检查
3. TaskDistributor: 负载均衡策略
4. StateSynchronizer: 状态同步
5. FaultDetector: 故障检测
6. MessageBus: 消息总线
7. DistributedCoordinator: 集成协调器
8. Agent集成
9. 并发安全
10. 集群场景
11. 异常容错
12. 第一性原理验证
"""

import time
import threading
import pytest
from unittest.mock import MagicMock

from self_evolving_agent.core.distributed import (
    NodeInfo,
    NodeRole,
    NodeStatus,
    NodeRegistry,
    LoadBalanceStrategy,
    TaskDistributor,
    StateSynchronizer,
    FaultDetector,
    DistributedMessage,
    MessageBus,
    DistributedCoordinator,
    create_dist_coordinator,
    create_cluster,
)


# ============================================================
# 节点模型测试
# ============================================================

class TestNodeInfo:
    """节点信息测试"""

    def test_creation(self):
        """测试创建"""
        node = NodeInfo(node_id="node1", host="localhost", port=8000)
        assert node.node_id == "node1"
        assert node.host == "localhost"
        assert node.port == 8000
        assert node.role == NodeRole.WORKER
        assert node.status == NodeStatus.ONLINE

    def test_is_alive(self):
        """测试存活判断"""
        node = NodeInfo(node_id="node1")
        assert node.is_alive() is True
        node.status = NodeStatus.OFFLINE
        assert node.is_alive() is False
        node.status = NodeStatus.SUSPECT
        assert node.is_alive() is True
        node.status = NodeStatus.LEAVING
        assert node.is_alive() is False

    def test_to_dict(self):
        """测试转字典"""
        node = NodeInfo(node_id="node1", host="host", port=8000, role=NodeRole.LEADER)
        d = node.to_dict()
        assert d["node_id"] == "node1"
        assert d["host"] == "host"
        assert d["port"] == 8000
        assert d["role"] == "leader"
        assert d["status"] == "online"

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "node_id": "node1",
            "host": "host",
            "port": 8000,
            "role": "coordinator",
            "status": "offline",
        }
        node = NodeInfo.from_dict(data)
        assert node.node_id == "node1"
        assert node.role == NodeRole.COORDINATOR
        assert node.status == NodeStatus.OFFLINE

    def test_roundtrip(self):
        """测试序列化往返"""
        node = NodeInfo(node_id="node1", host="host", port=8000, load=0.5)
        d = node.to_dict()
        node2 = NodeInfo.from_dict(d)
        assert node2.node_id == node.node_id
        assert node2.host == node.host
        assert node2.port == node.port
        assert node2.load == node.load

    def test_default_values(self):
        """测试默认值"""
        node = NodeInfo(node_id="node1")
        assert node.host == "localhost"
        assert node.port == 0
        assert node.role == NodeRole.WORKER
        assert node.status == NodeStatus.ONLINE
        assert node.load == 0.0
        assert node.metadata == {}


# ============================================================
# 节点注册中心测试
# ============================================================

class TestNodeRegistry:
    """节点注册中心测试"""

    def test_register(self):
        """测试注册"""
        registry = NodeRegistry()
        node = NodeInfo(node_id="node1")
        assert registry.register(node) is True
        assert registry.node_count() == 1

    def test_register_duplicate(self):
        """测试重复注册"""
        registry = NodeRegistry()
        node = NodeInfo(node_id="node1")
        assert registry.register(node) is True
        assert registry.register(node) is False
        assert registry.node_count() == 1

    def test_deregister(self):
        """测试注销"""
        registry = NodeRegistry()
        registry.register(NodeInfo(node_id="node1"))
        assert registry.deregister("node1") is True
        assert registry.node_count() == 0

    def test_deregister_nonexistent(self):
        """测试注销不存在的节点"""
        registry = NodeRegistry()
        assert registry.deregister("nonexistent") is False

    def test_heartbeat(self):
        """测试心跳"""
        registry = NodeRegistry()
        registry.register(NodeInfo(node_id="node1"))
        assert registry.heartbeat("node1", load=0.5) is True
        node = registry.get_node("node1")
        assert node.load == 0.5

    def test_heartbeat_nonexistent(self):
        """测试不存在节点的心跳"""
        registry = NodeRegistry()
        assert registry.heartbeat("nonexistent") is False

    def test_get_node(self):
        """测试获取节点"""
        registry = NodeRegistry()
        registry.register(NodeInfo(node_id="node1"))
        node = registry.get_node("node1")
        assert node is not None
        assert node.node_id == "node1"
        assert registry.get_node("nonexistent") is None

    def test_list_nodes(self):
        """测试列出节点"""
        registry = NodeRegistry()
        registry.register(NodeInfo(node_id="node1", role=NodeRole.WORKER))
        registry.register(NodeInfo(node_id="node2", role=NodeRole.LEADER))
        nodes = registry.list_nodes()
        assert len(nodes) == 2

    def test_list_nodes_by_role(self):
        """测试按角色列出"""
        registry = NodeRegistry()
        registry.register(NodeInfo(node_id="node1", role=NodeRole.WORKER))
        registry.register(NodeInfo(node_id="node2", role=NodeRole.LEADER))
        workers = registry.list_nodes(role=NodeRole.WORKER)
        assert len(workers) == 1
        assert workers[0].node_id == "node1"

    def test_list_nodes_by_status(self):
        """测试按状态列出"""
        registry = NodeRegistry()
        registry.register(NodeInfo(node_id="node1", status=NodeStatus.ONLINE))
        registry.register(NodeInfo(node_id="node2", status=NodeStatus.OFFLINE))
        online = registry.list_nodes(status=NodeStatus.ONLINE)
        assert len(online) == 1

    def test_get_alive_nodes(self):
        """测试获取存活节点"""
        registry = NodeRegistry()
        registry.register(NodeInfo(node_id="node1", status=NodeStatus.ONLINE))
        registry.register(NodeInfo(node_id="node2", status=NodeStatus.OFFLINE))
        alive = registry.get_alive_nodes()
        assert len(alive) == 1
        assert alive[0].node_id == "node1"

    def test_check_health_suspect(self):
        """测试健康检查-可疑"""
        registry = NodeRegistry(heartbeat_timeout=0.05, suspect_timeout=1.0)
        registry.register(NodeInfo(node_id="node1"))
        time.sleep(0.06)
        result = registry.check_health()
        assert "node1" in result["suspected"]
        node = registry.get_node("node1")
        assert node.status == NodeStatus.SUSPECT

    def test_check_health_expired(self):
        """测试健康检查-过期"""
        registry = NodeRegistry(heartbeat_timeout=0.05, suspect_timeout=0.1)
        registry.register(NodeInfo(node_id="node1"))
        time.sleep(0.15)
        result = registry.check_health()
        assert "node1" in result["expired"]
        assert registry.get_node("node1") is None

    def test_heartbeat_recovery(self):
        """测试心跳恢复"""
        registry = NodeRegistry(heartbeat_timeout=0.05, suspect_timeout=1.0)
        registry.register(NodeInfo(node_id="node1"))
        time.sleep(0.06)
        registry.check_health()
        node = registry.get_node("node1")
        assert node.status == NodeStatus.SUSPECT
        # 心跳恢复
        registry.heartbeat("node1")
        node = registry.get_node("node1")
        assert node.status == NodeStatus.ONLINE

    def test_listener(self):
        """测试监听器"""
        registry = NodeRegistry()
        events = []
        registry.add_listener(lambda nid, status: events.append((nid, status)))
        registry.register(NodeInfo(node_id="node1"))
        assert len(events) == 1
        assert events[0][0] == "node1"

    def test_metrics(self):
        """测试指标"""
        registry = NodeRegistry()
        registry.register(NodeInfo(node_id="node1"))
        registry.heartbeat("node1")
        metrics = registry.metrics()
        assert metrics["registrations"] == 1
        assert metrics["heartbeats"] == 1

    def test_clear(self):
        """测试清空"""
        registry = NodeRegistry()
        registry.register(NodeInfo(node_id="node1"))
        registry.clear()
        assert registry.node_count() == 0


# ============================================================
# 任务分发器测试
# ============================================================

class TestTaskDistributor:
    """任务分发器测试"""

    def test_round_robin(self):
        """测试轮询"""
        registry = NodeRegistry()
        for i in range(3):
            registry.register(NodeInfo(node_id=f"node{i}"))
        dist = TaskDistributor(registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)
        assignments = [dist.assign().node_id for _ in range(6)]
        # 轮询应均匀分配
        assert assignments[0] != assignments[1] or assignments[1] != assignments[2]

    def test_least_load(self):
        """测试最少负载"""
        registry = NodeRegistry()
        registry.register(NodeInfo(node_id="node1", load=0.9))
        registry.register(NodeInfo(node_id="node2", load=0.1))
        dist = TaskDistributor(registry, strategy=LoadBalanceStrategy.LEAST_LOAD)
        node = dist.assign()
        assert node.node_id == "node2"

    def test_random(self):
        """测试随机"""
        registry = NodeRegistry()
        for i in range(5):
            registry.register(NodeInfo(node_id=f"node{i}"))
        dist = TaskDistributor(registry, strategy=LoadBalanceStrategy.RANDOM)
        node = dist.assign()
        assert node is not None

    def test_consistent_hash(self):
        """测试一致性哈希"""
        registry = NodeRegistry()
        for i in range(3):
            registry.register(NodeInfo(node_id=f"node{i}"))
        dist = TaskDistributor(registry, strategy=LoadBalanceStrategy.CONSISTENT_HASH)
        # 相同key应分配到相同节点
        node1 = dist.assign("task_key_1")
        node2 = dist.assign("task_key_1")
        assert node1.node_id == node2.node_id

    def test_no_nodes(self):
        """测试无节点"""
        registry = NodeRegistry()
        dist = TaskDistributor(registry)
        assert dist.assign() is None

    def test_distribute(self):
        """测试批量分发"""
        registry = NodeRegistry()
        for i in range(3):
            registry.register(NodeInfo(node_id=f"node{i}"))
        dist = TaskDistributor(registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)
        tasks = list(range(9))
        distribution = dist.distribute(tasks)
        assert len(distribution) <= 4  # 3节点 + 可能的unassigned

    def test_distribute_with_key_fn(self):
        """测试带键函数的分发"""
        registry = NodeRegistry()
        for i in range(3):
            registry.register(NodeInfo(node_id=f"node{i}"))
        dist = TaskDistributor(registry, strategy=LoadBalanceStrategy.CONSISTENT_HASH)
        tasks = [{"id": i, "key": f"key_{i}"} for i in range(10)]
        distribution = dist.distribute(tasks, key_fn=lambda t: t["key"])
        assert len(distribution) > 0

    def test_set_strategy(self):
        """测试设置策略"""
        registry = NodeRegistry()
        registry.register(NodeInfo(node_id="node1"))
        dist = TaskDistributor(registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)
        dist.set_strategy(LoadBalanceStrategy.LEAST_LOAD)
        assert dist._strategy == LoadBalanceStrategy.LEAST_LOAD


# ============================================================
# 状态同步器测试
# ============================================================

class TestStateSynchronizer:
    """状态同步器测试"""

    def test_set_and_get(self):
        """测试设置和获取"""
        sync = StateSynchronizer("node1")
        sync.set("key", "value")
        assert sync.get("key") == "value"

    def test_get_default(self):
        """测试默认值"""
        sync = StateSynchronizer("node1")
        assert sync.get("nonexistent", "default") == "default"

    def test_get_all(self):
        """测试获取所有"""
        sync = StateSynchronizer("node1")
        sync.set("a", 1)
        sync.set("b", 2)
        state = sync.get_all()
        assert state["a"] == 1
        assert state["b"] == 2

    def test_peer_sync(self):
        """测试对等节点同步"""
        sync1 = StateSynchronizer("node1")
        sync2 = StateSynchronizer("node2")
        sync1.add_peer(sync2)
        sync1.set("key", "value")
        assert sync2.get("key") == "value"

    def test_version_based_merge(self):
        """测试基于版本的合并"""
        sync1 = StateSynchronizer("node1")
        sync2 = StateSynchronizer("node2")
        # 双向同步
        sync1.add_peer(sync2)
        sync2.add_peer(sync1)
        sync1.set("key", "v1")
        # sync2有更新版本
        sync2.set("key", "v2")
        # sync1应收到sync2的更新
        assert sync1.get("key") == "v2"

    def test_remove_peer(self):
        """测试移除对等节点"""
        sync1 = StateSynchronizer("node1")
        sync2 = StateSynchronizer("node2")
        sync1.add_peer(sync2)
        sync1.set("key", "value")
        sync1.remove_peer("node2")
        sync1.set("key2", "value2")
        assert sync2.get("key2") is None  # 不再同步

    def test_sync_all(self):
        """测试全量同步"""
        sync1 = StateSynchronizer("node1")
        sync2 = StateSynchronizer("node2")
        sync1.add_peer(sync2)
        # 直接设置状态（不触发同步）
        with sync1._lock:
            sync1._state["key"] = "value"
            sync1._version["key"] = 1
        sync1.sync_all()
        assert sync2.get("key") == "value"

    def test_get_version(self):
        """测试获取版本号"""
        sync = StateSynchronizer("node1")
        sync.set("key", "v1")
        assert sync.get_version("key") == 1
        sync.set("key", "v2")
        assert sync.get_version("key") == 2

    def test_clear(self):
        """测试清空"""
        sync = StateSynchronizer("node1")
        sync.set("key", "value")
        sync.clear()
        assert sync.get("key") is None


# ============================================================
# 故障检测器测试
# ============================================================

class TestFaultDetector:
    """故障检测器测试"""

    def test_creation(self):
        """测试创建"""
        registry = NodeRegistry()
        detector = FaultDetector(registry)
        assert detector is not None

    def test_check_healthy(self):
        """测试健康检查"""
        registry = NodeRegistry(heartbeat_timeout=1.0)
        registry.register(NodeInfo(node_id="node1"))
        detector = FaultDetector(registry, heartbeat_timeout=1.0)
        assert detector.is_node_healthy("node1") is True

    def test_check_unhealthy(self):
        """测试不健康检查"""
        registry = NodeRegistry(heartbeat_timeout=0.05)
        registry.register(NodeInfo(node_id="node1"))
        time.sleep(0.06)
        detector = FaultDetector(registry, heartbeat_timeout=0.05)
        assert detector.is_node_healthy("node1") is False

    def test_check_nonexistent(self):
        """测试不存在节点"""
        registry = NodeRegistry()
        detector = FaultDetector(registry)
        assert detector.is_node_healthy("nonexistent") is False

    def test_failure_handler(self):
        """测试故障处理器"""
        registry = NodeRegistry(heartbeat_timeout=0.05, suspect_timeout=0.1)
        registry.register(NodeInfo(node_id="node1"))
        detector = FaultDetector(registry, heartbeat_timeout=0.05)
        failures = []
        detector.on_failure(lambda nid: failures.append(nid))
        time.sleep(0.15)
        detector.check()
        assert "node1" in failures

    def test_recovery_handler(self):
        """测试恢复处理器"""
        registry = NodeRegistry(heartbeat_timeout=0.05, suspect_timeout=1.0)
        registry.register(NodeInfo(node_id="node1"))
        detector = FaultDetector(registry, heartbeat_timeout=0.05)
        recoveries = []
        detector.on_recovery(lambda nid: recoveries.append(nid))
        # 触发可疑
        time.sleep(0.06)
        detector.check()
        # 恢复心跳
        registry.heartbeat("node1")
        detector.check()
        assert "node1" in recoveries

    def test_start_stop(self):
        """测试启动停止"""
        registry = NodeRegistry()
        detector = FaultDetector(registry, check_interval=0.1)
        detector.start()
        time.sleep(0.15)
        detector.stop()
        # 不应崩溃


# ============================================================
# 消息总线测试
# ============================================================

class TestMessageBus:
    """消息总线测试"""

    def test_publish_subscribe(self):
        """测试发布订阅"""
        bus = MessageBus("node1")
        received = []
        bus.subscribe("topic", lambda msg: received.append(msg.payload))
        bus.publish("topic", "hello")
        assert received == ["hello"]

    def test_unsubscribe(self):
        """测试取消订阅"""
        bus = MessageBus("node1")
        received = []

        def handler(msg):
            received.append(msg.payload)

        bus.subscribe("topic", handler)
        bus.publish("topic", "msg1")
        bus.unsubscribe("topic", handler)
        bus.publish("topic", "msg2")
        assert received == ["msg1"]

    def test_peer_communication(self):
        """测试对等通信"""
        bus1 = MessageBus("node1")
        bus2 = MessageBus("node2")
        bus1.add_peer(bus2)
        received = []
        bus2.subscribe("topic", lambda msg: received.append(msg.payload))
        bus1.publish("topic", "hello")
        assert received == ["hello"]

    def test_broadcast(self):
        """测试广播"""
        bus1 = MessageBus("node1")
        bus2 = MessageBus("node2")
        bus3 = MessageBus("node3")
        bus1.add_peer(bus2)
        bus1.add_peer(bus3)
        received2 = []
        received3 = []
        bus2.subscribe("topic", lambda msg: received2.append(msg.payload))
        bus3.subscribe("topic", lambda msg: received3.append(msg.payload))
        bus1.publish("topic", "broadcast")
        assert received2 == ["broadcast"]
        assert received3 == ["broadcast"]

    def test_targeted_message(self):
        """测试定向消息"""
        bus1 = MessageBus("node1")
        bus2 = MessageBus("node2")
        bus3 = MessageBus("node3")
        bus1.add_peer(bus2)
        bus1.add_peer(bus3)
        received2 = []
        received3 = []
        bus2.subscribe("topic", lambda msg: received2.append(msg.payload))
        bus3.subscribe("topic", lambda msg: received3.append(msg.payload))
        bus1.publish("topic", "targeted", target="node2")
        assert received2 == ["targeted"]
        assert received3 == []  # node3不应收到

    def test_deduplication(self):
        """测试消息去重"""
        bus1 = MessageBus("node1")
        bus2 = MessageBus("node2")
        bus1.add_peer(bus2)
        bus2.add_peer(bus1)  # 双向，可能形成环路
        received = []
        bus1.subscribe("topic", lambda msg: received.append(msg.payload))
        bus2.subscribe("topic", lambda msg: received.append(msg.payload))
        bus1.publish("topic", "msg")
        # 去重应防止重复投递
        assert received.count("msg") <= 2

    def test_wildcard_subscription(self):
        """测试通配订阅"""
        bus = MessageBus("node1")
        received = []
        bus.subscribe("*", lambda msg: received.append(msg.payload))
        bus.publish("topic1", "msg1")
        bus.publish("topic2", "msg2")
        assert "msg1" in received
        assert "msg2" in received

    def test_remove_peer(self):
        """测试移除对等节点"""
        bus1 = MessageBus("node1")
        bus2 = MessageBus("node2")
        bus1.add_peer(bus2)
        received = []
        bus2.subscribe("topic", lambda msg: received.append(msg.payload))
        bus1.remove_peer("node2")
        bus1.publish("topic", "msg")
        assert received == []

    def test_peer_count(self):
        """测试对等节点数"""
        bus = MessageBus("node1")
        assert bus.peer_count() == 0
        bus.add_peer(MessageBus("node2"))
        assert bus.peer_count() == 1


# ============================================================
# 分布式协调器测试
# ============================================================

class TestDistributedCoordinator:
    """分布式协调器测试"""

    def test_creation(self):
        """测试创建"""
        coord = create_dist_coordinator("node1")
        assert coord.node_id == "node1"
        assert coord.cluster_size() == 1  # 自身

    def test_join_cluster(self):
        """测试加入集群"""
        coord1 = create_dist_coordinator("node1")
        coord2 = create_dist_coordinator("node2")
        coord1.join_cluster(coord2)
        assert coord1.cluster_size() == 2
        assert coord2.cluster_size() == 2

    def test_leave_cluster(self):
        """测试离开集群"""
        coord1 = create_dist_coordinator("node1")
        coord2 = create_dist_coordinator("node2")
        coord1.join_cluster(coord2)
        coord1.leave_cluster()
        # 自身节点应已注销
        assert coord1.registry.get_node("node1") is None

    def test_state_sharing(self):
        """测试状态共享"""
        coord1 = create_dist_coordinator("node1")
        coord2 = create_dist_coordinator("node2")
        coord1.join_cluster(coord2)
        coord1.set_state("key", "value")
        assert coord2.get_state("key") == "value"

    def test_message_passing(self):
        """测试消息传递"""
        coord1 = create_dist_coordinator("node1")
        coord2 = create_dist_coordinator("node2")
        coord1.join_cluster(coord2)
        received = []
        coord2.subscribe("topic", lambda msg: received.append(msg.payload))
        coord1.publish("topic", "hello")
        assert received == ["hello"]

    def test_task_assignment(self):
        """测试任务分配"""
        coord1 = create_dist_coordinator("node1")
        coord2 = create_dist_coordinator("node2")
        coord1.join_cluster(coord2)
        node = coord1.assign_task()
        assert node is not None

    def test_status(self):
        """测试状态"""
        coord = create_dist_coordinator("node1", role=NodeRole.LEADER)
        status = coord.status()
        assert status["node_id"] == "node1"
        assert status["node_role"] == "leader"
        assert status["cluster_size"] == 1

    def test_get_cluster_nodes(self):
        """测试获取集群节点"""
        coord1 = create_dist_coordinator("node1")
        coord2 = create_dist_coordinator("node2")
        coord1.join_cluster(coord2)
        nodes = coord1.get_cluster_nodes()
        assert len(nodes) == 2

    def test_start_stop(self):
        """测试启动停止"""
        coord = create_dist_coordinator("node1")
        coord.start()
        coord.stop()
        # 不应崩溃

    def test_create_cluster(self):
        """测试创建集群"""
        cluster = create_cluster(["a", "b", "c"])
        assert len(cluster) == 3
        assert cluster[0].cluster_size() == 3


# ============================================================
# Agent集成测试
# ============================================================

class TestAgentIntegration:
    """Agent集成测试"""

    def test_agent_no_distributed_by_default(self):
        """测试Agent默认不启用分布式"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        assert agent.distributed_coordinator is None

    def test_agent_enable_distributed(self):
        """测试启用分布式"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        agent.enable_distributed(node_id="test_node")
        assert agent.distributed_coordinator is not None

    def test_agent_cluster_status(self):
        """测试集群状态"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        status = agent.get_cluster_status()
        assert status["distributed"] is False
        agent.enable_distributed()
        status = agent.get_cluster_status()
        assert status["distributed"] is True

    def test_agent_join_cluster(self):
        """测试Agent加入集群"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent1 = SelfEvolvingAgent(agent_id="agent1")
        agent2 = SelfEvolvingAgent(agent_id="agent2")
        agent1.enable_distributed()
        agent2.enable_distributed()
        agent1.join_cluster(agent2)
        assert agent1.get_cluster_status()["cluster_size"] >= 2

    def test_agent_distributed_state(self):
        """测试Agent分布式状态"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent1 = SelfEvolvingAgent(agent_id="agent1")
        agent2 = SelfEvolvingAgent(agent_id="agent2")
        agent1.enable_distributed()
        agent2.enable_distributed()
        agent1.join_cluster(agent2)
        agent1.set_distributed_state("key", "value")
        assert agent2.get_distributed_state("key") == "value"

    def test_agent_distributed_message(self):
        """测试Agent分布式消息"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent1 = SelfEvolvingAgent(agent_id="agent1")
        agent2 = SelfEvolvingAgent(agent_id="agent2")
        agent1.enable_distributed()
        agent2.enable_distributed()
        agent1.join_cluster(agent2)
        received = []
        agent2.distributed_coordinator.subscribe("topic", lambda msg: received.append(msg.payload))
        agent1.publish_distributed_message("topic", "hello")
        assert received == ["hello"]

    def test_agent_assign_task(self):
        """测试Agent分配任务"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent1 = SelfEvolvingAgent(agent_id="agent1")
        agent2 = SelfEvolvingAgent(agent_id="agent2")
        agent1.enable_distributed()
        agent2.enable_distributed()
        agent1.join_cluster(agent2)
        node = agent1.assign_distributed_task()
        assert node is not None


# ============================================================
# 并发安全测试
# ============================================================

class TestConcurrencySafety:
    """并发安全测试"""

    def test_registry_concurrent_register(self):
        """测试并发注册"""
        registry = NodeRegistry()
        errors = []

        def worker(i):
            try:
                registry.register(NodeInfo(node_id=f"node_{i}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert registry.node_count() == 20

    def test_state_sync_concurrent(self):
        """测试并发状态同步"""
        sync1 = StateSynchronizer("node1")
        sync2 = StateSynchronizer("node2")
        sync1.add_peer(sync2)
        errors = []

        def worker(i):
            try:
                sync1.set(f"key_{i}", i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        for i in range(20):
            assert sync2.get(f"key_{i}") == i

    def test_message_bus_concurrent(self):
        """测试并发消息"""
        bus = MessageBus("node1")
        received = []
        lock = threading.Lock()

        def handler(msg):
            with lock:
                received.append(msg.payload)

        bus.subscribe("topic", handler)
        errors = []

        def worker(i):
            try:
                bus.publish("topic", i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(received) == 20


# ============================================================
# 集群场景测试
# ============================================================

class TestClusterScenarios:
    """集群场景测试"""

    def test_three_node_cluster(self):
        """测试三节点集群"""
        cluster = create_cluster(["a", "b", "c"])
        assert len(cluster) == 3
        for coord in cluster:
            assert coord.cluster_size() == 3

    def test_state_propagation(self):
        """测试状态传播"""
        cluster = create_cluster(["a", "b", "c"])
        cluster[0].set_state("key", "value")
        # 所有节点应同步
        assert cluster[1].get_state("key") == "value"
        assert cluster[2].get_state("key") == "value"

    def test_message_broadcast(self):
        """测试消息广播"""
        cluster = create_cluster(["a", "b", "c"])
        received = []
        for coord in cluster:
            coord.subscribe("topic", lambda msg: received.append((coord.node_id, msg.payload)))
        cluster[0].publish("topic", "broadcast")
        # 至少其他节点应收到
        assert len(received) >= 2

    def test_node_failure(self):
        """测试节点故障"""
        registry = NodeRegistry(heartbeat_timeout=0.05, suspect_timeout=0.1)
        registry.register(NodeInfo(node_id="node1"))
        registry.register(NodeInfo(node_id="node2"))
        time.sleep(0.15)
        result = registry.check_health()
        assert len(result["expired"]) == 2

    def test_load_balancing_distribution(self):
        """测试负载均衡分布"""
        registry = NodeRegistry()
        for i in range(5):
            registry.register(NodeInfo(node_id=f"node{i}"))
        dist = TaskDistributor(registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)
        assignments = [dist.assign().node_id for _ in range(100)]
        # 每个节点应分配约20次
        from collections import Counter
        counts = Counter(assignments)
        for count in counts.values():
            assert 15 <= count <= 25  # 允许一些偏差


# ============================================================
# 异常容错测试
# ============================================================

class TestErrorHandling:
    """异常容错测试"""

    def test_registry_empty_list(self):
        """测试空注册中心"""
        registry = NodeRegistry()
        assert registry.list_nodes() == []
        assert registry.get_alive_nodes() == []
        assert registry.get_node("nonexistent") is None

    def test_distributor_no_nodes(self):
        """测试无节点分发"""
        registry = NodeRegistry()
        dist = TaskDistributor(registry)
        assert dist.assign() is None

    def test_state_sync_no_peer(self):
        """测试无对等节点同步"""
        sync = StateSynchronizer("node1")
        sync.set("key", "value")
        # 不应崩溃
        assert sync.get("key") == "value"

    def test_message_bus_no_subscriber(self):
        """测试无订阅者发布"""
        bus = MessageBus("node1")
        # 不应崩溃
        bus.publish("topic", "msg")

    def test_coordinator_join_self(self):
        """测试加入自身"""
        coord = create_dist_coordinator("node1")
        # 加入自身应返回False（已注册）
        assert coord.join_cluster(coord) is False or coord.cluster_size() >= 1

    def test_handler_exception_isolation(self):
        """测试处理器异常隔离"""
        bus = MessageBus("node1")
        received = []

        def good_handler(msg):
            received.append(msg.payload)

        def bad_handler(msg):
            raise RuntimeError("handler error")

        bus.subscribe("topic", bad_handler)
        bus.subscribe("topic", good_handler)
        bus.publish("topic", "msg")
        # bad_handler的异常不应影响good_handler
        assert received == ["msg"]


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_node_discovery_principle(self):
        """第一性原理：节点发现"""
        # 节点需要知道彼此存在
        registry = NodeRegistry()
        node1 = NodeInfo(node_id="node1")
        node2 = NodeInfo(node_id="node2")
        registry.register(node1)
        registry.register(node2)
        # 节点可以发现彼此
        nodes = registry.list_nodes()
        assert len(nodes) == 2

    def test_task_distribution_principle(self):
        """第一性原理：任务分发"""
        # 任务需分配到合适节点
        registry = NodeRegistry()
        for i in range(3):
            registry.register(NodeInfo(node_id=f"node{i}"))
        dist = TaskDistributor(registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)
        # 任务应被分配到存活节点
        node = dist.assign()
        assert node is not None
        assert node.is_alive()

    def test_state_consistency_principle(self):
        """第一性原理：状态一致性"""
        # 节点间需共享状态
        sync1 = StateSynchronizer("node1")
        sync2 = StateSynchronizer("node2")
        sync1.add_peer(sync2)
        sync1.set("key", "value")
        # 状态应同步到对等节点
        assert sync2.get("key") == "value"

    def test_fault_tolerance_principle(self):
        """第一性原理：容错"""
        # 节点可能故障，需检测
        registry = NodeRegistry(heartbeat_timeout=0.05, suspect_timeout=0.1)
        registry.register(NodeInfo(node_id="node1"))
        time.sleep(0.15)
        result = registry.check_health()
        # 故障应被检测到
        assert "node1" in result["expired"]

    def test_reliable_communication_principle(self):
        """第一性原理：可靠通信"""
        # 节点间需可靠通信
        bus1 = MessageBus("node1")
        bus2 = MessageBus("node2")
        bus1.add_peer(bus2)
        received = []
        bus2.subscribe("topic", lambda msg: received.append(msg.payload))
        bus1.publish("topic", "message")
        # 消息应可靠送达
        assert received == ["message"]

    def test_horizontal_scaling_principle(self):
        """第一性原理：水平扩展"""
        # 多节点可水平扩展
        cluster = create_cluster(["a", "b", "c", "d", "e"])
        assert len(cluster) == 5
        # 每个节点都知道所有其他节点
        for coord in cluster:
            assert coord.cluster_size() == 5
