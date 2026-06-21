"""
阶段126: 持久化存储层 — 专项测试

验证:
1. StorageInterface抽象
2. MemoryStorage内存存储
3. JSONStorage文件存储（原子写入）
4. MemoryPersistence记忆持久化
5. CausalGraphPersistence因果图持久化
6. PersistenceManager管理器
7. Agent集成
8. 并发安全、性能、异常容错
9. 第一性原理验证
"""

import os
import json
import tempfile
import threading
import time
import pytest

from self_evolving_agent.core.persistence import (
    StorageType,
    StorageRecord,
    StorageInterface,
    MemoryStorage,
    JSONStorage,
    MemoryPersistence,
    CausalGraphPersistence,
    PersistenceManager,
    create_memory_storage,
    create_json_storage,
    create_persistence_manager,
)


# ============================================================
# 1. 数据结构测试
# ============================================================

class TestDataStructures:
    """数据结构测试"""

    def test_storage_type_enum(self):
        """存储类型枚举"""
        assert StorageType.JSON.value == "json"
        assert StorageType.MEMORY.value == "memory"
        assert StorageType.SQLITE.value == "sqlite"

    def test_storage_record_creation(self):
        """存储记录创建"""
        record = StorageRecord(key="k1", value="v1")
        assert record.key == "k1"
        assert record.value == "v1"
        assert record.namespace == "default"
        assert record.timestamp > 0

    def test_storage_record_to_dict(self):
        """记录转字典"""
        record = StorageRecord(key="k1", value="v1", namespace="ns1")
        d = record.to_dict()
        assert d["key"] == "k1"
        assert d["value"] == "v1"
        assert d["namespace"] == "ns1"

    def test_storage_record_from_dict(self):
        """字典转记录"""
        d = {"key": "k1", "value": "v1", "namespace": "ns1"}
        record = StorageRecord.from_dict(d)
        assert record.key == "k1"
        assert record.value == "v1"
        assert record.namespace == "ns1"


# ============================================================
# 2. MemoryStorage 测试
# ============================================================

class TestMemoryStorage:
    """内存存储测试"""

    def test_creation(self):
        """创建"""
        storage = MemoryStorage()
        assert storage.storage_id is not None

    def test_save_and_load(self):
        """保存和加载"""
        storage = MemoryStorage()
        assert storage.save("k1", "v1") is True
        assert storage.load("k1") == "v1"

    def test_save_complex_value(self):
        """保存复杂值"""
        storage = MemoryStorage()
        value = {"list": [1, 2, 3], "nested": {"a": 1}}
        assert storage.save("k1", value) is True
        assert storage.load("k1") == value

    def test_load_nonexistent(self):
        """加载不存在键"""
        storage = MemoryStorage()
        assert storage.load("nonexistent") is None

    def test_delete(self):
        """删除"""
        storage = MemoryStorage()
        storage.save("k1", "v1")
        assert storage.delete("k1") is True
        assert storage.load("k1") is None

    def test_delete_nonexistent(self):
        """删除不存在键"""
        storage = MemoryStorage()
        assert storage.delete("nonexistent") is False

    def test_list_keys(self):
        """列出键"""
        storage = MemoryStorage()
        storage.save("k1", "v1")
        storage.save("k2", "v2")
        keys = storage.list_keys()
        assert "k1" in keys
        assert "k2" in keys

    def test_list_keys_empty(self):
        """空命名空间"""
        storage = MemoryStorage()
        assert storage.list_keys() == []

    def test_namespaces(self):
        """命名空间"""
        storage = MemoryStorage()
        storage.save("k1", "v1", "ns1")
        storage.save("k2", "v2", "ns2")
        namespaces = storage.list_namespaces()
        assert "ns1" in namespaces
        assert "ns2" in namespaces

    def test_exists(self):
        """检查存在"""
        storage = MemoryStorage()
        storage.save("k1", "v1")
        assert storage.exists("k1") is True
        assert storage.exists("nonexistent") is False

    def test_clear_namespace(self):
        """清除命名空间"""
        storage = MemoryStorage()
        storage.save("k1", "v1", "ns1")
        storage.save("k2", "v2", "ns1")
        count = storage.clear_namespace("ns1")
        assert count == 2
        assert storage.list_keys("ns1") == []

    def test_clear_namespace_nonexistent(self):
        """清除不存在命名空间"""
        storage = MemoryStorage()
        assert storage.clear_namespace("nonexistent") == 0

    def test_clear_all(self):
        """清除所有"""
        storage = MemoryStorage()
        storage.save("k1", "v1", "ns1")
        storage.save("k2", "v2", "ns2")
        count = storage.clear_all()
        assert count == 2
        assert storage.list_namespaces() == []

    def test_save_empty_key(self):
        """空键防御"""
        storage = MemoryStorage()
        assert storage.save("", "v1") is False

    def test_get_stats(self):
        """获取统计"""
        storage = MemoryStorage()
        storage.save("k1", "v1")
        stats = storage.get_stats()
        assert stats["type"] == "memory"
        assert stats["total_keys"] == 1


# ============================================================
# 3. JSONStorage 测试
# ============================================================

class TestJSONStorage:
    """JSON文件存储测试"""

    def test_creation(self):
        """创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            assert storage.storage_id is not None

    def test_creation_empty_path(self):
        """空路径创建失败"""
        with pytest.raises(ValueError):
            JSONStorage("")

    def test_save_and_load(self):
        """保存和加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            assert storage.save("k1", "v1") is True
            assert storage.load("k1") == "v1"

    def test_save_complex_value(self):
        """保存复杂值"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            value = {"list": [1, 2, 3], "nested": {"a": 1}}
            storage.save("k1", value)
            assert storage.load("k1") == value

    def test_persistence_across_instances(self):
        """跨实例持久化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage1 = JSONStorage(tmpdir)
            storage1.save("k1", "v1")

            # 新实例应该能加载
            storage2 = JSONStorage(tmpdir)
            assert storage2.load("k1") == "v1"

    def test_delete(self):
        """删除"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            storage.save("k1", "v1")
            assert storage.delete("k1") is True
            assert storage.load("k1") is None

    def test_list_keys(self):
        """列出键"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            storage.save("k1", "v1")
            storage.save("k2", "v2")
            keys = storage.list_keys()
            assert "k1" in keys
            assert "k2" in keys

    def test_namespaces(self):
        """命名空间"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            storage.save("k1", "v1", "ns1")
            storage.save("k2", "v2", "ns2")
            namespaces = storage.list_namespaces()
            assert "ns1" in namespaces
            assert "ns2" in namespaces

    def test_exists(self):
        """检查存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            storage.save("k1", "v1")
            assert storage.exists("k1") is True
            assert storage.exists("nonexistent") is False

    def test_clear_namespace(self):
        """清除命名空间"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            storage.save("k1", "v1", "ns1")
            storage.save("k2", "v2", "ns1")
            count = storage.clear_namespace("ns1")
            assert count == 2

    def test_clear_all(self):
        """清除所有"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            storage.save("k1", "v1", "ns1")
            storage.save("k2", "v2", "ns2")
            count = storage.clear_all()
            assert count == 2

    def test_namespace_path_safety(self):
        """命名空间路径安全"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            # 特殊字符命名空间
            storage.save("k1", "v1", "ns/../dangerous")
            # 不应穿越目录
            assert not os.path.exists(os.path.join(tmpdir, "..", "dangerous.json"))

    def test_get_stats(self):
        """获取统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            storage.save("k1", "v1")
            stats = storage.get_stats()
            assert stats["type"] == "json"
            assert stats["total_keys"] == 1


# ============================================================
# 4. MemoryPersistence 测试
# ============================================================

class TestMemoryPersistence:
    """记忆持久化测试"""

    def test_creation(self):
        """创建"""
        storage = MemoryStorage()
        mp = MemoryPersistence(storage)
        assert mp is not None

    def test_save_and_load_memory(self):
        """保存和加载记忆"""
        storage = MemoryStorage()
        mp = MemoryPersistence(storage)
        assert mp.save_memory("m1", {"content": "hello"}) is True
        assert mp.load_memory("m1") == {"content": "hello"}

    def test_load_nonexistent(self):
        """加载不存在记忆"""
        storage = MemoryStorage()
        mp = MemoryPersistence(storage)
        assert mp.load_memory("nonexistent") is None

    def test_save_all_memories(self):
        """批量保存"""
        storage = MemoryStorage()
        mp = MemoryPersistence(storage)
        memories = {
            "m1": {"content": "1"},
            "m2": {"content": "2"},
            "m3": {"content": "3"},
        }
        count = mp.save_all_memories(memories)
        assert count == 3

    def test_load_all_memories(self):
        """加载所有"""
        storage = MemoryStorage()
        mp = MemoryPersistence(storage)
        mp.save_memory("m1", {"content": "1"})
        mp.save_memory("m2", {"content": "2"})
        all_mem = mp.load_all_memories()
        assert len(all_mem) == 2
        assert "m1" in all_mem

    def test_delete_memory(self):
        """删除记忆"""
        storage = MemoryStorage()
        mp = MemoryPersistence(storage)
        mp.save_memory("m1", {"content": "1"})
        assert mp.delete_memory("m1") is True
        assert mp.load_memory("m1") is None

    def test_list_memory_ids(self):
        """列出记忆ID"""
        storage = MemoryStorage()
        mp = MemoryPersistence(storage)
        mp.save_memory("m1", {"content": "1"})
        mp.save_memory("m2", {"content": "2"})
        ids = mp.list_memory_ids()
        assert "m1" in ids
        assert "m2" in ids

    def test_clear_all(self):
        """清除所有"""
        storage = MemoryStorage()
        mp = MemoryPersistence(storage)
        mp.save_memory("m1", {"content": "1"})
        count = mp.clear_all()
        assert count == 1
        assert mp.list_memory_ids() == []

    def test_save_empty_id(self):
        """空ID防御"""
        storage = MemoryStorage()
        mp = MemoryPersistence(storage)
        assert mp.save_memory("", {"content": "1"}) is False

    def test_save_none_data(self):
        """None数据防御"""
        storage = MemoryStorage()
        mp = MemoryPersistence(storage)
        assert mp.save_memory("m1", None) is False


# ============================================================
# 5. CausalGraphPersistence 测试
# ============================================================

class TestCausalGraphPersistence:
    """因果图持久化测试"""

    def test_creation(self):
        """创建"""
        storage = MemoryStorage()
        cgp = CausalGraphPersistence(storage)
        assert cgp is not None

    def test_save_and_load_node(self):
        """保存和加载节点"""
        storage = MemoryStorage()
        cgp = CausalGraphPersistence(storage)
        assert cgp.save_node("A", {"name": "nodeA"}) is True
        assert cgp.load_node("A") == {"name": "nodeA"}

    def test_delete_node(self):
        """删除节点"""
        storage = MemoryStorage()
        cgp = CausalGraphPersistence(storage)
        cgp.save_node("A", {"name": "nodeA"})
        assert cgp.delete_node("A") is True
        assert cgp.load_node("A") is None

    def test_list_nodes(self):
        """列出节点"""
        storage = MemoryStorage()
        cgp = CausalGraphPersistence(storage)
        cgp.save_node("A", {"name": "A"})
        cgp.save_node("B", {"name": "B"})
        nodes = cgp.list_nodes()
        assert "A" in nodes
        assert "B" in nodes

    def test_save_and_load_edge(self):
        """保存和加载边"""
        storage = MemoryStorage()
        cgp = CausalGraphPersistence(storage)
        assert cgp.save_edge("A->B", {"strength": 0.8}) is True
        assert cgp.load_edge("A->B") == {"strength": 0.8}

    def test_delete_edge(self):
        """删除边"""
        storage = MemoryStorage()
        cgp = CausalGraphPersistence(storage)
        cgp.save_edge("A->B", {"strength": 0.8})
        assert cgp.delete_edge("A->B") is True

    def test_list_edges(self):
        """列出边"""
        storage = MemoryStorage()
        cgp = CausalGraphPersistence(storage)
        cgp.save_edge("A->B", {"strength": 0.8})
        cgp.save_edge("B->C", {"strength": 0.5})
        edges = cgp.list_edges()
        assert "A->B" in edges
        assert "B->C" in edges

    def test_save_graph(self):
        """保存整个图"""
        storage = MemoryStorage()
        cgp = CausalGraphPersistence(storage)
        nodes = {"A": {"name": "A"}, "B": {"name": "B"}}
        edges = {"A->B": {"strength": 0.8}}
        count = cgp.save_graph(nodes, edges)
        assert count == 3  # 2节点 + 1边

    def test_load_graph(self):
        """加载整个图"""
        storage = MemoryStorage()
        cgp = CausalGraphPersistence(storage)
        cgp.save_node("A", {"name": "A"})
        cgp.save_edge("A->B", {"strength": 0.8})
        graph = cgp.load_graph()
        assert "A" in graph["nodes"]
        assert "A->B" in graph["edges"]

    def test_clear_all(self):
        """清除所有"""
        storage = MemoryStorage()
        cgp = CausalGraphPersistence(storage)
        cgp.save_node("A", {"name": "A"})
        cgp.save_edge("A->B", {"strength": 0.8})
        count = cgp.clear_all()
        assert count == 2


# ============================================================
# 6. PersistenceManager 测试
# ============================================================

class TestPersistenceManager:
    """持久化管理器测试"""

    def test_creation(self):
        """创建"""
        pm = create_persistence_manager()
        assert pm.manager_id is not None

    def test_save_and_load_state(self):
        """保存和加载状态"""
        storage = MemoryStorage()
        pm = PersistenceManager(storage)
        assert pm.save_state("key1", {"data": "value"}) is True
        assert pm.load_state("key1") == {"data": "value"}

    def test_save_and_load_checkpoint(self):
        """保存和加载检查点"""
        storage = MemoryStorage()
        pm = PersistenceManager(storage)
        assert pm.save_checkpoint("cp1", {"state": "ok"}) is True
        assert pm.load_checkpoint("cp1") == {"state": "ok"}

    def test_list_checkpoints(self):
        """列出检查点"""
        storage = MemoryStorage()
        pm = PersistenceManager(storage)
        pm.save_checkpoint("cp1", {"state": "1"})
        pm.save_checkpoint("cp2", {"state": "2"})
        checkpoints = pm.list_checkpoints()
        assert "cp1" in checkpoints
        assert "cp2" in checkpoints

    def test_memory_property(self):
        """记忆属性"""
        storage = MemoryStorage()
        pm = PersistenceManager(storage)
        assert isinstance(pm.memory, MemoryPersistence)

    def test_causal_graph_property(self):
        """因果图属性"""
        storage = MemoryStorage()
        pm = PersistenceManager(storage)
        assert isinstance(pm.causal_graph, CausalGraphPersistence)

    def test_get_stats(self):
        """获取统计"""
        storage = MemoryStorage()
        pm = PersistenceManager(storage)
        pm.memory.save_memory("m1", {"content": "1"})
        pm.causal_graph.save_node("A", {"name": "A"})
        stats = pm.get_stats()
        assert stats["memory_count"] == 1
        assert stats["causal_nodes"] == 1

    def test_clear_all(self):
        """清除所有"""
        storage = MemoryStorage()
        pm = PersistenceManager(storage)
        pm.memory.save_memory("m1", {"content": "1"})
        pm.save_state("k1", {"data": "v1"})
        count = pm.clear_all()
        assert count >= 2


# ============================================================
# 7. Agent集成测试
# ============================================================

class TestAgentIntegration:
    """Agent集成测试"""

    def test_agent_has_persistence(self):
        """Agent有持久化管理器"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        assert agent.persistence is not None

    def test_agent_save_and_load_state(self):
        """Agent保存和加载状态"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        assert agent.save_state("key1", {"data": "value"}) is True
        assert agent.load_state("key1") == {"data": "value"}

    def test_agent_save_checkpoint(self):
        """Agent保存检查点"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        cp_id = agent.save_checkpoint()
        assert cp_id is not None
        state = agent.load_checkpoint(cp_id)
        assert state is not None
        assert "cycle_count" in state

    def test_agent_load_nonexistent_checkpoint(self):
        """Agent加载不存在检查点"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        assert agent.load_checkpoint("nonexistent") is None

    def test_agent_set_persistence_storage(self):
        """Agent设置存储后端"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            agent.set_persistence_storage(storage)
            assert agent.save_state("key1", {"data": "value"}) is True
            assert agent.load_state("key1") == {"data": "value"}


# ============================================================
# 8. 并发安全测试
# ============================================================

class TestConcurrency:
    """并发安全测试"""

    def test_concurrent_save_memory_storage(self):
        """并发保存内存存储"""
        storage = MemoryStorage()
        errors = []

        def worker(idx):
            try:
                for i in range(20):
                    storage.save(f"k_{idx}_{i}", f"v_{idx}_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(storage.list_keys()) == 100

    def test_concurrent_save_json_storage(self):
        """并发保存JSON存储"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            errors = []

            def worker(idx):
                try:
                    for i in range(10):
                        storage.save(f"k_{idx}_{i}", f"v_{idx}_{i}")
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0
            assert len(storage.list_keys()) == 50

    def test_concurrent_memory_persistence(self):
        """并发记忆持久化"""
        storage = MemoryStorage()
        mp = MemoryPersistence(storage)
        errors = []

        def worker(idx):
            try:
                for i in range(20):
                    mp.save_memory(f"m_{idx}_{i}", {"content": str(i)})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(mp.list_memory_ids()) == 100


# ============================================================
# 9. 性能测试
# ============================================================

class TestPerformance:
    """性能测试"""

    def test_memory_storage_performance(self):
        """内存存储性能"""
        storage = MemoryStorage()
        start = time.time()
        for i in range(1000):
            storage.save(f"k{i}", f"v{i}")
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_json_storage_performance(self):
        """JSON存储性能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            start = time.time()
            for i in range(100):
                storage.save(f"k{i}", f"v{i}")
            elapsed = time.time() - start
            assert elapsed < 10.0

    def test_load_performance(self):
        """加载性能"""
        storage = MemoryStorage()
        for i in range(1000):
            storage.save(f"k{i}", f"v{i}")
        start = time.time()
        for i in range(1000):
            storage.load(f"k{i}")
        elapsed = time.time() - start
        assert elapsed < 5.0


# ============================================================
# 10. 异常容错测试
# ============================================================

class TestErrorTolerance:
    """异常容错测试"""

    def test_json_storage_corrupted_file(self):
        """JSON存储损坏文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            # 写入损坏的JSON
            with open(os.path.join(tmpdir, "default.json"), "w") as f:
                f.write("{corrupted json")
            # 加载不应崩溃
            assert storage.load("any_key") is None

    def test_json_storage_nonexistent_namespace(self):
        """JSON存储不存在命名空间"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            assert storage.list_keys("nonexistent") == []
            assert storage.load("k1", "nonexistent") is None

    def test_memory_storage_empty_key(self):
        """内存存储空键"""
        storage = MemoryStorage()
        assert storage.save("", "v1") is False

    def test_memory_persistence_none_data(self):
        """记忆持久化None数据"""
        storage = MemoryStorage()
        mp = MemoryPersistence(storage)
        assert mp.save_memory("m1", None) is False

    def test_causal_persistence_empty_id(self):
        """因果图持久化空ID"""
        storage = MemoryStorage()
        cgp = CausalGraphPersistence(storage)
        assert cgp.save_node("", {"name": "A"}) is False
        assert cgp.save_edge("", {"strength": 0.8}) is False

    def test_clear_nonexistent_namespace(self):
        """清除不存在命名空间"""
        storage = MemoryStorage()
        assert storage.clear_namespace("nonexistent") == 0


# ============================================================
# 11. 第一性原理验证测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证测试"""

    def test_persistence_survives_restart(self):
        """第一性原理：持久化跨重启"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 第一个实例保存
            storage1 = JSONStorage(tmpdir)
            storage1.save("k1", "v1")

            # 第二个实例加载（模拟重启）
            storage2 = JSONStorage(tmpdir)
            assert storage2.load("k1") == "v1"

    def test_atomic_write(self):
        """第一性原理：原子写入"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            storage.save("k1", "v1")
            # 不应有临时文件残留
            files = os.listdir(tmpdir)
            assert not any(f.endswith(".tmp") for f in files)

    def test_namespace_isolation(self):
        """第一性原理：命名空间隔离"""
        storage = MemoryStorage()
        storage.save("k1", "v1", "ns1")
        storage.save("k1", "v2", "ns2")
        # 同名键在不同命名空间互不影响
        assert storage.load("k1", "ns1") == "v1"
        assert storage.load("k1", "ns2") == "v2"

    def test_crud_completeness(self):
        """第一性原理：CRUD完整性"""
        storage = MemoryStorage()
        # Create
        assert storage.save("k1", "v1") is True
        # Read
        assert storage.load("k1") == "v1"
        # Update
        assert storage.save("k1", "v2") is True
        assert storage.load("k1") == "v2"
        # Delete
        assert storage.delete("k1") is True
        assert storage.load("k1") is None

    def test_serialization_reversibility(self):
        """第一性原理：序列化可逆"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(tmpdir)
            original = {
                "string": "hello",
                "number": 42,
                "float": 3.14,
                "list": [1, 2, 3],
                "nested": {"a": 1, "b": [4, 5]},
                "bool": True,
                "none": None,
            }
            storage.save("k1", original)
            loaded = storage.load("k1")
            assert loaded == original

    def test_storage_abstraction(self):
        """第一性原理：存储抽象（可替换后端）"""
        # 内存存储和JSON存储应该有相同接口
        memory_storage = MemoryStorage()
        with tempfile.TemporaryDirectory() as tmpdir:
            json_storage = JSONStorage(tmpdir)

            # 相同操作
            for storage in [memory_storage, json_storage]:
                assert storage.save("k1", "v1") is True
                assert storage.load("k1") == "v1"
                assert storage.exists("k1") is True
                assert storage.delete("k1") is True
                assert storage.exists("k1") is False
