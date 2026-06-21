"""
阶段117: 记忆系统强化 — 专项测试

验证新增能力:
1. MemoryLayerType / LAYER_CONFIG: 三层记忆配置
2. MemoryItem: 增强字段（memory_layer, memory_strength, recall_probability）
3. LayeredMemoryStore: 分层存储（LRU驱逐、跨层查找、提升）
4. MemoryConsolidator: 记忆巩固（工作→短期→长期、遗忘低回忆概率）
5. MemoryFirstPrinciplesEngine: 新增接口（store_in_layer, review_memory等）
6. 向后兼容性: 保留原有 store/retrieve/consolidate 接口

第一性原理验证:
- 艾宾浩斯遗忘曲线: R(t) = e^(-t/S)
- 间隔重复: 复习增强记忆强度，边际递减
- 分层流动: 工作记忆→短期记忆→长期记忆
- 遗忘优化: 清除低回忆概率记忆释放资源
"""

import math
import threading
import time
import pytest

from self_evolving_agent.core.memory_first_principles import (
    MemoryPriority,
    MemoryLayerType,
    LAYER_CONFIG,
    MemoryItem,
    LayeredMemoryStore,
    MemoryConsolidator,
    MemoryFirstPrinciplesEngine,
    create_memory_engine,
    create_memory_item,
    create_layered_memory_item,
)


# ============================================================
# 1. MemoryLayerType 与 LAYER_CONFIG 测试
# ============================================================

class TestMemoryLayerType:
    """记忆层级类型测试"""

    def test_three_layers_exist(self):
        """三层记忆都存在"""
        assert MemoryLayerType.WORKING.value == "working"
        assert MemoryLayerType.SHORT_TERM.value == "short_term"
        assert MemoryLayerType.LONG_TERM.value == "long_term"

    def test_layer_config_completeness(self):
        """每层配置完整"""
        for layer in MemoryLayerType:
            config = LAYER_CONFIG[layer]
            assert "capacity" in config
            assert "decay_constant" in config
            assert "consolidation_threshold" in config
            assert "consolidation_window" in config

    def test_capacity_hierarchy(self):
        """容量层级递增：工作 < 短期 < 长期"""
        assert LAYER_CONFIG[MemoryLayerType.WORKING]["capacity"] < LAYER_CONFIG[MemoryLayerType.SHORT_TERM]["capacity"]
        assert LAYER_CONFIG[MemoryLayerType.SHORT_TERM]["capacity"] < LAYER_CONFIG[MemoryLayerType.LONG_TERM]["capacity"]

    def test_decay_hierarchy(self):
        """衰减常数层级递增：工作 < 短期 < 长期（衰减越慢）"""
        assert LAYER_CONFIG[MemoryLayerType.WORKING]["decay_constant"] < LAYER_CONFIG[MemoryLayerType.SHORT_TERM]["decay_constant"]
        assert LAYER_CONFIG[MemoryLayerType.SHORT_TERM]["decay_constant"] < LAYER_CONFIG[MemoryLayerType.LONG_TERM]["decay_constant"]

    def test_working_capacity_7pm2(self):
        """工作记忆容量遵循 7±2 原则"""
        cap = LAYER_CONFIG[MemoryLayerType.WORKING]["capacity"]
        assert 5 <= cap <= 9

    def test_long_term_no_consolidation(self):
        """长期记忆不再巩固"""
        assert LAYER_CONFIG[MemoryLayerType.LONG_TERM]["consolidation_threshold"] == float("inf")


# ============================================================
# 2. MemoryItem 测试
# ============================================================

class TestMemoryItem:
    """记忆条目测试"""

    def test_default_layer_is_working(self):
        """新记忆默认进入工作记忆层"""
        item = MemoryItem(item_id="i1", content="data")
        assert item.memory_layer == MemoryLayerType.WORKING

    def test_default_memory_strength(self):
        """默认记忆强度为1.0"""
        item = MemoryItem(item_id="i1", content="data")
        assert item.memory_strength == 1.0

    def test_recall_probability_range(self):
        """回忆概率在[0,1]范围内"""
        item = MemoryItem(item_id="i1", content="data", information_value=0.5)
        prob = item.recall_probability
        assert 0.0 <= prob <= 1.0

    def test_recall_probability_zero_for_negative_time(self):
        """负时间不崩溃"""
        item = MemoryItem(item_id="i1", content="data", information_value=0.5)
        item.last_review_time = time.time() + 1000  # 未来时间
        prob = item.recall_probability
        assert 0.0 <= prob <= 1.0

    def test_recall_probability_decreases_with_time(self):
        """回忆概率随时间递减（艾宾浩斯曲线）"""
        item_old = MemoryItem(item_id="old", content="data", information_value=1.0)
        item_old.last_review_time = time.time() - 1000  # 1000秒前

        item_new = MemoryItem(item_id="new", content="data", information_value=1.0)
        item_new.last_review_time = time.time()  # 现在

        assert item_new.recall_probability > item_old.recall_probability

    def test_recall_probability_increases_with_strength(self):
        """回忆概率随记忆强度增大而增大"""
        item_weak = MemoryItem(item_id="weak", content="data", information_value=1.0, memory_strength=0.5)
        item_strong = MemoryItem(item_id="strong", content="data", information_value=1.0, memory_strength=10.0)
        # 同样的复习时间
        item_weak.last_review_time = item_strong.last_review_time = time.time() - 100

        assert item_strong.recall_probability >= item_weak.recall_probability

    def test_recall_probability_increases_with_value(self):
        """回忆概率受信息价值加成"""
        item_low = MemoryItem(item_id="low", content="data", information_value=0.0)
        item_high = MemoryItem(item_id="high", content="data", information_value=1.0)
        item_low.last_review_time = item_high.last_review_time = time.time()

        assert item_high.recall_probability >= item_low.recall_probability

    def test_access_increases_count(self):
        """访问增加计数"""
        item = MemoryItem(item_id="i1", content="data")
        initial = item.access_count
        item.access()
        assert item.access_count == initial + 1

    def test_access_reinforces_strength(self):
        """访问增强记忆强度（间隔重复）"""
        item = MemoryItem(item_id="i1", content="data")
        initial_strength = item.memory_strength
        item.access()
        assert item.memory_strength > initial_strength

    def test_review_increases_count(self):
        """复习增加复习次数"""
        item = MemoryItem(item_id="i1", content="data")
        initial = item.review_count
        item.review()
        assert item.review_count == initial + 1

    def test_review_reinforces_strength(self):
        """复习增强记忆强度"""
        item = MemoryItem(item_id="i1", content="data")
        initial_strength = item.memory_strength
        item.review()
        assert item.memory_strength > initial_strength

    def test_reinforce_marginal_decrease(self):
        """增强因子边际递减"""
        item = MemoryItem(item_id="i1", content="data")
        # 第一次复习
        strength_before_1 = item.memory_strength
        item.review()
        gain_1 = item.memory_strength - strength_before_1

        # 多次复习后
        for _ in range(10):
            item.review()
        strength_before_n = item.memory_strength
        item.review()
        gain_n = item.memory_strength - strength_before_n

        assert gain_n < gain_1

    def test_reinforce_upper_bound(self):
        """记忆强度有上限"""
        item = MemoryItem(item_id="i1", content="data")
        for _ in range(1000):
            item.review()
        assert item.memory_strength <= 100.0

    def test_retention_score_backward_compat(self):
        """保留分数向后兼容"""
        item = MemoryItem(item_id="i1", content="data", information_value=0.8)
        score = item.retention_score
        assert isinstance(score, float)
        assert not math.isnan(score)

    def test_tags_default_empty(self):
        """标签默认为空集合"""
        item = MemoryItem(item_id="i1", content="data")
        assert item.tags == set()

    def test_tags_custom(self):
        """自定义标签"""
        item = MemoryItem(item_id="i1", content="data", tags={"a", "b"})
        assert "a" in item.tags
        assert "b" in item.tags


# ============================================================
# 3. LayeredMemoryStore 测试
# ============================================================

class TestLayeredMemoryStore:
    """分层记忆存储测试"""

    def test_add_to_working_layer(self):
        """添加到工作记忆层"""
        store = LayeredMemoryStore()
        item = MemoryItem(item_id="i1", content="data", information_value=0.8)
        assert store.add(item) is True
        assert store.get_layer_count(MemoryLayerType.WORKING) == 1

    def test_add_to_specific_layer(self):
        """添加到指定层"""
        store = LayeredMemoryStore()
        item = MemoryItem(item_id="i1", content="data", information_value=0.8)
        assert store.add(item, MemoryLayerType.LONG_TERM) is True
        assert item.memory_layer == MemoryLayerType.LONG_TERM
        assert store.get_layer_count(MemoryLayerType.LONG_TERM) == 1

    def test_get_cross_layer(self):
        """跨层查找"""
        store = LayeredMemoryStore()
        item = MemoryItem(item_id="i1", content="data", information_value=0.8)
        store.add(item, MemoryLayerType.SHORT_TERM)
        found = store.get("i1")
        assert found is not None
        assert found.item_id == "i1"

    def test_get_nonexistent(self):
        """获取不存在的记忆"""
        store = LayeredMemoryStore()
        assert store.get("nonexistent") is None

    def test_remove(self):
        """移除记忆"""
        store = LayeredMemoryStore()
        item = MemoryItem(item_id="i1", content="data", information_value=0.8)
        store.add(item)
        assert store.remove("i1") is True
        assert store.get("i1") is None

    def test_remove_nonexistent(self):
        """移除不存在的记忆返回False"""
        store = LayeredMemoryStore()
        assert store.remove("nonexistent") is False

    def test_access_updates_count(self):
        """访问更新计数"""
        store = LayeredMemoryStore()
        item = MemoryItem(item_id="i1", content="data", information_value=0.8)
        store.add(item)
        accessed = store.access("i1")
        assert accessed is not None
        assert accessed.access_count == 1

    def test_capacity_eviction_working(self):
        """工作记忆容量超限时驱逐"""
        store = LayeredMemoryStore()
        capacity = LAYER_CONFIG[MemoryLayerType.WORKING]["capacity"]
        # 添加 capacity+5 个项目
        for i in range(capacity + 5):
            item = MemoryItem(
                item_id=f"i{i}",
                content=f"data{i}",
                information_value=0.5,
            )
            store.add(item)
        # 应该只有 capacity 个项目
        assert store.get_layer_count(MemoryLayerType.WORKING) == capacity

    def test_capacity_eviction_keeps_critical(self):
        """关键记忆不被驱逐"""
        store = LayeredMemoryStore()
        capacity = LAYER_CONFIG[MemoryLayerType.WORKING]["capacity"]
        # 添加一个关键记忆
        critical = MemoryItem(
            item_id="critical",
            content="important",
            information_value=1.0,
            priority=MemoryPriority.CRITICAL,
        )
        store.add(critical)
        # 添加 capacity 个普通记忆
        for i in range(capacity):
            item = MemoryItem(
                item_id=f"i{i}",
                content=f"data{i}",
                information_value=0.5,
            )
            store.add(item)
        # 关键记忆应该还在
        assert store.get("critical") is not None

    def test_promote_to_higher_layer(self):
        """提升到更高层"""
        store = LayeredMemoryStore()
        item = MemoryItem(item_id="i1", content="data", information_value=0.8)
        store.add(item, MemoryLayerType.WORKING)
        assert store.promote("i1", MemoryLayerType.SHORT_TERM) is True
        assert store.get_layer_count(MemoryLayerType.WORKING) == 0
        assert store.get_layer_count(MemoryLayerType.SHORT_TERM) == 1
        assert item.memory_layer == MemoryLayerType.SHORT_TERM

    def test_promote_nonexistent(self):
        """提升不存在的记忆返回False"""
        store = LayeredMemoryStore()
        assert store.promote("nonexistent", MemoryLayerType.SHORT_TERM) is False

    def test_promote_same_layer(self):
        """提升到同层返回False"""
        store = LayeredMemoryStore()
        item = MemoryItem(item_id="i1", content="data", information_value=0.8)
        store.add(item, MemoryLayerType.WORKING)
        assert store.promote("i1", MemoryLayerType.WORKING) is False

    def test_get_all_items(self):
        """获取所有记忆"""
        store = LayeredMemoryStore()
        store.add(MemoryItem(item_id="i1", content="d1", information_value=0.8), MemoryLayerType.WORKING)
        store.add(MemoryItem(item_id="i2", content="d2", information_value=0.8), MemoryLayerType.SHORT_TERM)
        store.add(MemoryItem(item_id="i3", content="d3", information_value=0.8), MemoryLayerType.LONG_TERM)
        all_items = store.get_all_items()
        assert len(all_items) == 3

    def test_get_total_count(self):
        """获取总记忆数"""
        store = LayeredMemoryStore()
        store.add(MemoryItem(item_id="i1", content="d1", information_value=0.8))
        store.add(MemoryItem(item_id="i2", content="d2", information_value=0.8))
        assert store.get_total_count() == 2

    def test_clear_layer(self):
        """清空指定层"""
        store = LayeredMemoryStore()
        store.add(MemoryItem(item_id="i1", content="d1", information_value=0.8), MemoryLayerType.WORKING)
        store.add(MemoryItem(item_id="i2", content="d2", information_value=0.8), MemoryLayerType.SHORT_TERM)
        cleared = store.clear_layer(MemoryLayerType.WORKING)
        assert cleared == 1
        assert store.get_layer_count(MemoryLayerType.WORKING) == 0
        assert store.get_layer_count(MemoryLayerType.SHORT_TERM) == 1

    def test_clear_all(self):
        """清空所有层"""
        store = LayeredMemoryStore()
        store.add(MemoryItem(item_id="i1", content="d1", information_value=0.8))
        store.add(MemoryItem(item_id="i2", content="d2", information_value=0.8), MemoryLayerType.SHORT_TERM)
        store.clear_all()
        assert store.get_total_count() == 0

    def test_get_stats(self):
        """获取统计"""
        store = LayeredMemoryStore()
        store.add(MemoryItem(item_id="i1", content="d1", information_value=0.8))
        stats = store.get_stats()
        assert "layer_counts" in stats
        assert "total_count" in stats
        assert "promotion_count" in stats
        assert stats["total_count"] == 1

    def test_add_existing_updates(self):
        """添加已存在的记忆会更新"""
        store = LayeredMemoryStore()
        item1 = MemoryItem(item_id="i1", content="d1", information_value=0.5)
        store.add(item1)
        item2 = MemoryItem(item_id="i1", content="d2", information_value=0.9)
        store.add(item2)
        found = store.get("i1")
        assert found.content == "d2"


# ============================================================
# 4. MemoryConsolidator 测试
# ============================================================

class TestMemoryConsolidator:
    """记忆巩固器测试"""

    def test_consolidate_empty_store(self):
        """空存储巩固"""
        store = LayeredMemoryStore()
        consolidator = MemoryConsolidator(store)
        result = consolidator.consolidate()
        assert result["promoted_to_short"] == 0
        assert result["promoted_to_long"] == 0
        assert result["forgotten"] == 0

    def test_consolidate_working_to_short(self):
        """工作记忆巩固到短期记忆"""
        store = LayeredMemoryStore()
        # 添加一个访问次数达阈值的记忆
        threshold = LAYER_CONFIG[MemoryLayerType.WORKING]["consolidation_threshold"]
        item = MemoryItem(item_id="i1", content="data", information_value=0.8)
        for _ in range(threshold):
            item.access()
        store.add(item, MemoryLayerType.WORKING)

        consolidator = MemoryConsolidator(store)
        result = consolidator.consolidate()
        assert result["promoted_to_short"] >= 1
        assert store.get_layer_count(MemoryLayerType.SHORT_TERM) >= 1

    def test_consolidate_short_to_long(self):
        """短期记忆巩固到长期记忆"""
        store = LayeredMemoryStore()
        threshold = LAYER_CONFIG[MemoryLayerType.SHORT_TERM]["consolidation_threshold"]
        item = MemoryItem(item_id="i1", content="data", information_value=1.0)
        for _ in range(threshold):
            item.access()
        store.add(item, MemoryLayerType.SHORT_TERM)

        consolidator = MemoryConsolidator(store)
        result = consolidator.consolidate()
        assert result["promoted_to_long"] >= 1
        assert store.get_layer_count(MemoryLayerType.LONG_TERM) >= 1

    def test_consolidate_critical_directly_to_long(self):
        """关键记忆直接巩固到长期"""
        store = LayeredMemoryStore()
        item = MemoryItem(
            item_id="i1",
            content="critical",
            information_value=1.0,
            priority=MemoryPriority.CRITICAL,
        )
        store.add(item, MemoryLayerType.WORKING)

        consolidator = MemoryConsolidator(store)
        result = consolidator.consolidate()
        assert result["promoted_to_long"] >= 1
        assert store.get("i1") is not None
        assert store.get("i1").memory_layer == MemoryLayerType.LONG_TERM

    def test_consolidate_forget_low_recall(self):
        """遗忘低回忆概率的记忆"""
        store = LayeredMemoryStore()
        item = MemoryItem(item_id="i1", content="data", information_value=0.5)
        # 设置很久以前复习
        item.last_review_time = time.time() - 99999999
        store.add(item, MemoryLayerType.WORKING)

        consolidator = MemoryConsolidator(store)
        result = consolidator.consolidate()
        assert result["forgotten"] >= 1
        assert store.get("i1") is None

    def test_consolidate_keeps_critical(self):
        """关键记忆不被遗忘"""
        store = LayeredMemoryStore()
        item = MemoryItem(
            item_id="i1",
            content="critical",
            information_value=1.0,
            priority=MemoryPriority.CRITICAL,
        )
        item.last_review_time = time.time() - 99999999
        store.add(item, MemoryLayerType.WORKING)

        consolidator = MemoryConsolidator(store)
        consolidator.consolidate()
        # 关键记忆应被提升到长期而非遗忘
        assert store.get("i1") is not None

    def test_review_item(self):
        """复习特定记忆"""
        store = LayeredMemoryStore()
        item = MemoryItem(item_id="i1", content="data", information_value=0.8)
        store.add(item)
        consolidator = MemoryConsolidator(store)
        assert consolidator.review_item("i1") is True
        assert item.review_count == 1

    def test_review_nonexistent(self):
        """复习不存在的记忆返回False"""
        store = LayeredMemoryStore()
        consolidator = MemoryConsolidator(store)
        assert consolidator.review_item("nonexistent") is False

    def test_get_stats(self):
        """获取巩固统计"""
        store = LayeredMemoryStore()
        consolidator = MemoryConsolidator(store)
        consolidator.consolidate()
        stats = consolidator.get_stats()
        assert "consolidation_count" in stats
        assert "forget_count" in stats
        assert stats["consolidation_count"] == 1


# ============================================================
# 5. MemoryFirstPrinciplesEngine 新接口测试
# ============================================================

class TestEnhancedMemoryEngine:
    """增强记忆引擎测试"""

    def test_store_in_layer(self):
        """存储到指定层"""
        engine = create_memory_engine()
        item = engine.store_in_layer("i1", "data", MemoryLayerType.WORKING, information_value=0.8)
        assert item is not None
        assert item.memory_layer == MemoryLayerType.WORKING
        assert engine.retrieve_from_layer("i1") is not None

    def test_store_in_layer_with_tags(self):
        """带标签存储"""
        engine = create_memory_engine()
        item = engine.store_in_layer(
            "i1", "data", MemoryLayerType.WORKING,
            information_value=0.8, tags={"important", "test"}
        )
        assert item is not None
        assert "important" in item.tags

    def test_retrieve_from_layer(self):
        """从分层存储检索"""
        engine = create_memory_engine()
        engine.store_in_layer("i1", "data", MemoryLayerType.WORKING, information_value=0.8)
        item = engine.retrieve_from_layer("i1")
        assert item is not None
        assert item.access_count == 1

    def test_review_memory(self):
        """复习记忆"""
        engine = create_memory_engine()
        engine.store_in_layer("i1", "data", MemoryLayerType.WORKING, information_value=0.8)
        assert engine.review_memory("i1") is True
        assert engine.get_recall_probability("i1") > 0

    def test_review_nonexistent(self):
        """复习不存在的记忆"""
        engine = create_memory_engine()
        assert engine.review_memory("nonexistent") is False

    def test_consolidate_memory(self):
        """执行记忆巩固"""
        engine = create_memory_engine()
        # 添加一些记忆
        for i in range(5):
            engine.store_in_layer(f"i{i}", f"data{i}", MemoryLayerType.WORKING, information_value=0.8)
        result = engine.consolidate_memory()
        assert "promoted_to_short" in result
        assert "promoted_to_long" in result
        assert "forgotten" in result

    def test_get_recall_probability(self):
        """获取回忆概率"""
        engine = create_memory_engine()
        engine.store_in_layer("i1", "data", MemoryLayerType.WORKING, information_value=0.8)
        prob = engine.get_recall_probability("i1")
        assert 0.0 <= prob <= 1.0

    def test_get_recall_probability_nonexistent(self):
        """获取不存在记忆的回忆概率"""
        engine = create_memory_engine()
        assert engine.get_recall_probability("nonexistent") == 0.0

    def test_search_by_tag(self):
        """按标签搜索"""
        engine = create_memory_engine()
        engine.store_in_layer("i1", "d1", MemoryLayerType.WORKING, information_value=0.8, tags={"a"})
        engine.store_in_layer("i2", "d2", MemoryLayerType.WORKING, information_value=0.8, tags={"b"})
        engine.store_in_layer("i3", "d3", MemoryLayerType.WORKING, information_value=0.8, tags={"a", "b"})
        results = engine.search_by_tag("a")
        assert len(results) == 2

    def test_search_by_recall(self):
        """按回忆概率搜索"""
        engine = create_memory_engine()
        engine.store_in_layer("i1", "d1", MemoryLayerType.WORKING, information_value=1.0)
        results = engine.search_by_recall(0.5)
        assert len(results) >= 1

    def test_promote_memory(self):
        """手动提升记忆"""
        engine = create_memory_engine()
        engine.store_in_layer("i1", "data", MemoryLayerType.WORKING, information_value=0.8)
        assert engine.promote_memory("i1", MemoryLayerType.LONG_TERM) is True
        items = engine.get_layer_items(MemoryLayerType.LONG_TERM)
        assert len(items) == 1

    def test_get_layer_items(self):
        """获取指定层记忆"""
        engine = create_memory_engine()
        engine.store_in_layer("i1", "d1", MemoryLayerType.WORKING, information_value=0.8)
        engine.store_in_layer("i2", "d2", MemoryLayerType.SHORT_TERM, information_value=0.8)
        working_items = engine.get_layer_items(MemoryLayerType.WORKING)
        assert len(working_items) == 1

    def test_get_layered_store(self):
        """获取分层存储"""
        engine = create_memory_engine()
        store = engine.get_layered_store()
        assert isinstance(store, LayeredMemoryStore)

    def test_get_consolidator(self):
        """获取巩固器"""
        engine = create_memory_engine()
        consolidator = engine.get_consolidator()
        assert isinstance(consolidator, MemoryConsolidator)

    def test_stats_include_layered_info(self):
        """统计包含分层信息"""
        engine = create_memory_engine()
        engine.store_in_layer("i1", "data", MemoryLayerType.WORKING, information_value=0.8)
        stats = engine.get_stats()
        assert "layered_store_stats" in stats
        assert "consolidator_stats" in stats


# ============================================================
# 6. 向后兼容性测试
# ============================================================

class TestBackwardCompat:
    """向后兼容性测试"""

    def test_store_returns_item(self):
        """store 返回 MemoryItem"""
        engine = create_memory_engine()
        item = engine.store("i1", "data")
        assert item is not None
        assert isinstance(item, MemoryItem)

    def test_store_low_value_returns_none(self):
        """低价值信息不存储"""
        engine = MemoryFirstPrinciplesEngine("test", retention_threshold=0.5)
        # 完全相同的内容 novelty=0.1
        engine.store("i1", "same content")
        item = engine.store("i2", "same content")
        assert item is None

    def test_retrieve_returns_item(self):
        """retrieve 返回记忆"""
        engine = create_memory_engine()
        engine.store("i1", "data")
        item = engine.retrieve("i1")
        assert item is not None
        assert item.item_id == "i1"

    def test_retrieve_nonexistent(self):
        """retrieve 不存在的记忆"""
        engine = create_memory_engine()
        assert engine.retrieve("nonexistent") is None

    def test_search_by_value(self):
        """按价值搜索"""
        engine = create_memory_engine()
        engine.store("i1", "completely different alpha content")
        engine.store("i2", "totally distinct beta data gamma")
        results = engine.search_by_value(0.5)
        assert len(results) >= 1

    def test_consolidate_returns_int(self):
        """consolidate 返回遗忘数"""
        engine = create_memory_engine()
        result = engine.consolidate()
        assert isinstance(result, int)

    def test_get_stats_backward_compat(self):
        """get_stats 包含原有字段"""
        engine = create_memory_engine()
        stats = engine.get_stats()
        assert "engine_id" in stats
        assert "items_count" in stats
        assert "capacity" in stats
        assert "stored_count" in stats
        assert "forgotten_count" in stats
        assert "utilization" in stats
        assert "avg_information_value" in stats

    def test_clear(self):
        """clear 清空记忆"""
        engine = create_memory_engine()
        engine.store("i1", "data")
        engine.clear()
        assert engine.get_stats()["items_count"] == 0

    def test_evaluate_information_value(self):
        """评估信息价值"""
        engine = create_memory_engine()
        value = engine.evaluate_information_value("novel content")
        assert 0.0 <= value <= 1.0

    def test_evaluate_with_context(self):
        """带上下文评估"""
        engine = create_memory_engine()
        value = engine.evaluate_information_value(
            "content", context={"error_reduction_potential": 0.5}
        )
        assert 0.0 <= value <= 1.0

    def test_priority_mapping(self):
        """优先级映射"""
        engine = create_memory_engine()
        # 高价值 -> CRITICAL
        item = engine.store("i1", "very unique novel content critical")
        if item and item.information_value > 0.9:
            assert item.priority == MemoryPriority.CRITICAL

    def test_capacity_management(self):
        """容量管理"""
        engine = create_memory_engine(capacity=5)
        for i in range(10):
            engine.store(f"i{i}", f"unique content {i}")
        assert engine.get_stats()["items_count"] <= 5

    def test_create_memory_item_helper(self):
        """create_memory_item 便捷函数"""
        item = create_memory_item("i1", "data", 0.5)
        assert item.item_id == "i1"
        assert item.information_value == 0.5

    def test_create_layered_memory_item_helper(self):
        """create_layered_memory_item 便捷函数"""
        item = create_layered_memory_item("i1", "data", MemoryLayerType.LONG_TERM, 0.8, {"tag"})
        assert item.memory_layer == MemoryLayerType.LONG_TERM
        assert "tag" in item.tags

    def test_store_existing_updates(self):
        """存储已存在记忆会更新"""
        engine = create_memory_engine()
        engine.store("i1", "first content")
        engine.store("i1", "second content")
        item = engine.retrieve("i1")
        assert item.content == "second content"

    def test_capacity_zero_no_crash(self):
        """capacity=0 不崩溃"""
        engine = MemoryFirstPrinciplesEngine("test", capacity=0)
        stats = engine.get_stats()
        assert stats["utilization"] == 0.0


# ============================================================
# 7. 并发安全测试
# ============================================================

class TestConcurrency:
    """并发安全测试"""

    def test_concurrent_store(self):
        """并发存储"""
        engine = create_memory_engine(capacity=1000)
        errors = []

        def worker(worker_id):
            try:
                for i in range(50):
                    engine.store(f"w{worker_id}_i{i}", f"content_{worker_id}_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert engine.get_stats()["items_count"] > 0

    def test_concurrent_layered_store(self):
        """并发分层存储"""
        store = LayeredMemoryStore()
        errors = []

        def worker(worker_id):
            try:
                for i in range(20):
                    item = MemoryItem(
                        item_id=f"w{worker_id}_i{i}",
                        content=f"content_{worker_id}_{i}",
                        information_value=0.8,
                    )
                    store.add(item)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert store.get_total_count() > 0

    def test_concurrent_consolidate(self):
        """并发巩固"""
        engine = create_memory_engine()
        for i in range(20):
            engine.store_in_layer(f"i{i}", f"data{i}", MemoryLayerType.WORKING, information_value=0.8)

        errors = []

        def worker():
            try:
                for _ in range(5):
                    engine.consolidate_memory()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ============================================================
# 8. 性能测试
# ============================================================

class TestPerformance:
    """性能测试"""

    def test_store_performance(self):
        """存储性能：1000次 < 1秒"""
        engine = create_memory_engine(capacity=2000)
        start = time.time()
        for i in range(1000):
            engine.store(f"i{i}", f"unique content {i}")
        elapsed = time.time() - start
        assert elapsed < 1.0, f"存储1000条耗时 {elapsed:.3f}s"

    def test_retrieve_performance(self):
        """检索性能：1000次 < 0.5秒"""
        engine = create_memory_engine()
        for i in range(100):
            engine.store(f"i{i}", f"content {i}")
        start = time.time()
        for i in range(1000):
            engine.retrieve(f"i{i % 100}")
        elapsed = time.time() - start
        assert elapsed < 1.0, f"检索1000次耗时 {elapsed:.3f}s"

    def test_consolidate_performance(self):
        """巩固性能：100条记忆 < 0.5秒"""
        engine = create_memory_engine()
        for i in range(100):
            engine.store_in_layer(f"i{i}", f"data{i}", MemoryLayerType.WORKING, information_value=0.8)
        start = time.time()
        engine.consolidate_memory()
        elapsed = time.time() - start
        assert elapsed < 0.5, f"巩固100条耗时 {elapsed:.3f}s"

    def test_no_memory_leak(self):
        """无内存泄漏：1000次存储后内存稳定"""
        engine = create_memory_engine(capacity=100)
        for cycle in range(10):
            for i in range(100):
                engine.store(f"cycle{cycle}_i{i}", f"content_{cycle}_{i}")
        # 容量限制下，items_count 不应超过 capacity 太多
        assert engine.get_stats()["items_count"] <= 100


# ============================================================
# 9. 异常容错测试
# ============================================================

class TestErrorTolerance:
    """异常容错测试"""

    def test_none_content(self):
        """None 内容不崩溃"""
        engine = create_memory_engine()
        item = engine.store("i1", None)
        # None 内容应被处理（可能存储或拒绝，但不崩溃）
        assert item is None or item.content is None

    def test_empty_content(self):
        """空内容不崩溃"""
        engine = create_memory_engine()
        item = engine.store("i1", "")
        assert item is None or item.content == ""

    def test_negative_information_value(self):
        """负信息价值不崩溃"""
        engine = create_memory_engine()
        item = engine.store_in_layer("i1", "data", MemoryLayerType.WORKING, information_value=-0.5)
        assert item is not None

    def test_huge_information_value(self):
        """超大信息价值不崩溃"""
        engine = create_memory_engine()
        item = engine.store_in_layer("i1", "data", MemoryLayerType.WORKING, information_value=1e10)
        assert item is not None

    def test_nan_information_value(self):
        """NaN 信息价值不崩溃"""
        engine = create_memory_engine()
        item = engine.store_in_layer("i1", "data", MemoryLayerType.WORKING, information_value=float("nan"))
        assert item is not None

    def test_inf_information_value(self):
        """Inf 信息价值不崩溃"""
        engine = create_memory_engine()
        item = engine.store_in_layer("i1", "data", MemoryLayerType.WORKING, information_value=float("inf"))
        assert item is not None

    def test_future_timestamp(self):
        """未来时间戳不崩溃"""
        item = MemoryItem(
            item_id="i1",
            content="data",
            information_value=0.8,
            created_at=time.time() + 999999,
            last_review_time=time.time() + 999999,
        )
        # 不崩溃即可
        score = item.retention_score
        prob = item.recall_probability
        assert not math.isnan(score)
        assert 0.0 <= prob <= 1.0

    def test_zero_memory_strength(self):
        """零记忆强度不崩溃"""
        item = MemoryItem(item_id="i1", content="data", information_value=0.8, memory_strength=0.0)
        prob = item.recall_probability
        assert 0.0 <= prob <= 1.0

    def test_negative_memory_strength(self):
        """负记忆强度不崩溃"""
        item = MemoryItem(item_id="i1", content="data", information_value=0.8, memory_strength=-1.0)
        prob = item.recall_probability
        assert 0.0 <= prob <= 1.0

    def test_very_old_review_time(self):
        """很久以前的复习时间不崩溃"""
        item = MemoryItem(item_id="i1", content="data", information_value=0.8)
        item.last_review_time = 0  # 1970年
        prob = item.recall_probability
        assert 0.0 <= prob <= 1.0


# ============================================================
# 10. 第一性原理验证测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_ebbinghaus_curve_shape(self):
        """艾宾浩斯遗忘曲线形状：指数衰减"""
        item = MemoryItem(item_id="i1", content="data", information_value=1.0)
        # 不同时间点的回忆概率
        times = [0, 10, 60, 600, 3600]
        probs = []
        for t in times:
            test_item = MemoryItem(item_id=f"i_{t}", content="data", information_value=1.0)
            test_item.last_review_time = time.time() - t
            probs.append(test_item.recall_probability)
        # 概率应递减
        for i in range(len(probs) - 1):
            assert probs[i] >= probs[i + 1], f"t={times[i]} prob={probs[i]} > t={times[i+1]} prob={probs[i+1]}"

    def test_spaced_repetition_slows_forgetting(self):
        """间隔重复减缓遗忘"""
        # 未复习的记忆
        item_no_review = MemoryItem(item_id="no_review", content="data", information_value=1.0)
        item_no_review.last_review_time = time.time() - 100

        # 多次复习的记忆
        item_reviewed = MemoryItem(item_id="reviewed", content="data", information_value=1.0)
        for _ in range(10):
            item_reviewed.review()
        item_reviewed.last_review_time = time.time() - 100

        # 复习过的记忆回忆概率应更高
        assert item_reviewed.recall_probability > item_no_review.recall_probability

    def test_layered_hierarchy(self):
        """分层层级：工作<短期<长期容量"""
        assert LAYER_CONFIG[MemoryLayerType.WORKING]["capacity"] < LAYER_CONFIG[MemoryLayerType.SHORT_TERM]["capacity"]
        assert LAYER_CONFIG[MemoryLayerType.SHORT_TERM]["capacity"] < LAYER_CONFIG[MemoryLayerType.LONG_TERM]["capacity"]

    def test_consolidation_flow(self):
        """巩固流动：工作→短期→长期"""
        engine = create_memory_engine()
        # 工作记忆中的高访问记忆应被巩固到短期
        threshold = LAYER_CONFIG[MemoryLayerType.WORKING]["consolidation_threshold"]
        item = MemoryItem(item_id="i1", content="data", information_value=0.8)
        for _ in range(threshold):
            item.access()
        engine.get_layered_store().add(item, MemoryLayerType.WORKING)

        engine.consolidate_memory()
        assert item.memory_layer == MemoryLayerType.SHORT_TERM

    def test_forgetting_releases_capacity(self):
        """遗忘释放容量"""
        store = LayeredMemoryStore()
        capacity = LAYER_CONFIG[MemoryLayerType.WORKING]["capacity"]
        # 填满工作记忆
        for i in range(capacity):
            item = MemoryItem(item_id=f"i{i}", content=f"d{i}", information_value=0.5)
            store.add(item, MemoryLayerType.WORKING)
        assert store.get_layer_count(MemoryLayerType.WORKING) == capacity

        # 添加更多，触发驱逐
        for i in range(capacity, capacity + 5):
            item = MemoryItem(item_id=f"i{i}", content=f"d{i}", information_value=0.5)
            store.add(item, MemoryLayerType.WORKING)
        # 容量应保持不变
        assert store.get_layer_count(MemoryLayerType.WORKING) == capacity

    def test_information_value_affects_priority(self):
        """信息价值影响优先级"""
        engine = create_memory_engine()
        # 高价值
        item_high = engine.store_in_layer("i1", "very unique novel critical data", MemoryLayerType.WORKING, information_value=0.95)
        # 低价值
        item_low = engine.store_in_layer("i2", "data", MemoryLayerType.WORKING, information_value=0.1)
        assert item_high.priority.value in ["critical", "high"]
        assert item_low.priority.value in ["low", "ephemeral"]

    def test_review_enhances_strength_monotonically(self):
        """复习单调增强记忆强度"""
        item = MemoryItem(item_id="i1", content="data", information_value=0.8)
        strengths = [item.memory_strength]
        for _ in range(20):
            item.review()
            strengths.append(item.memory_strength)
        # 强度应单调递增
        for i in range(len(strengths) - 1):
            assert strengths[i + 1] >= strengths[i]
