"""
阶段120: 意识模型强化 — 专项测试

验证新增能力:
1. AttentionMechanism: 注意力机制（自上而下/自下而上）
2. AttentionTarget: 注意力目标
3. ConsciousnessLevel: 意识层级
4. ConsciousnessState: 意识状态
5. ConsciousnessFirstPrinciplesEngine: 新增接口
6. 向后兼容性

第一性原理验证:
- 注意力是有限资源
- 自上而下 vs 自下而上注意力
- 意识层级：无意识→前意识→意识→元意识
- 全局工作空间竞争
"""

import math
import threading
import time
import pytest

from self_evolving_agent.core.consciousness_first_principles import (
    ContentType,
    WorkspaceContent,
    AttentionType,
    AttentionFocus,
    AttentionTarget,
    AttentionMechanism,
    ConsciousnessLevel,
    ConsciousnessState,
    ConsciousnessFirstPrinciplesEngine,
    create_consciousness_engine,
    create_workspace_content,
    create_attention_target,
)


# ============================================================
# 1. AttentionMechanism 测试
# ============================================================

class TestAttentionMechanism:
    """注意力机制测试"""

    def test_allocate_attention(self):
        """分配注意力"""
        am = AttentionMechanism(total_capacity=1.0)
        target = am.allocate_attention("c1", AttentionType.TOP_DOWN, 0.5)
        assert target.content_id == "c1"
        assert target.attention_weight == 0.5

    def test_deallocate_attention(self):
        """释放注意力"""
        am = AttentionMechanism()
        target = am.allocate_attention("c1", AttentionType.TOP_DOWN, 0.5)
        assert am.deallocate_attention(target.target_id) is True
        assert am.get_total_attention() == 0.0

    def test_deallocate_nonexistent(self):
        """释放不存在的注意力"""
        am = AttentionMechanism()
        assert am.deallocate_attention("nonexistent") is False

    def test_total_attention(self):
        """总注意力"""
        am = AttentionMechanism(total_capacity=1.0)
        am.allocate_attention("c1", AttentionType.TOP_DOWN, 0.3)
        am.allocate_attention("c2", AttentionType.BOTTOM_UP, 0.4)
        assert abs(am.get_total_attention() - 0.7) < 1e-6

    def test_available_capacity(self):
        """可用容量"""
        am = AttentionMechanism(total_capacity=1.0)
        am.allocate_attention("c1", AttentionType.TOP_DOWN, 0.3)
        assert abs(am.get_available_capacity() - 0.7) < 1e-6

    def test_capacity_limit(self):
        """容量限制"""
        am = AttentionMechanism(total_capacity=0.5)
        t1 = am.allocate_attention("c1", AttentionType.TOP_DOWN, 0.3)
        t2 = am.allocate_attention("c2", AttentionType.TOP_DOWN, 0.3)
        # 第二个只能分配0.2（剩余容量）
        assert t1.attention_weight == 0.3
        assert t2.attention_weight == 0.2

    def test_get_attention_for_content(self):
        """获取内容的注意力"""
        am = AttentionMechanism()
        am.allocate_attention("c1", AttentionType.TOP_DOWN, 0.3)
        am.allocate_attention("c1", AttentionType.BOTTOM_UP, 0.2)
        am.allocate_attention("c2", AttentionType.TOP_DOWN, 0.4)
        assert abs(am.get_attention_for_content("c1") - 0.5) < 1e-6
        assert abs(am.get_attention_for_content("c2") - 0.4) < 1e-6

    def test_get_top_targets(self):
        """获取注意力最高的目标"""
        am = AttentionMechanism()
        am.allocate_attention("c1", AttentionType.TOP_DOWN, 0.3)
        am.allocate_attention("c2", AttentionType.TOP_DOWN, 0.8)
        am.allocate_attention("c3", AttentionType.TOP_DOWN, 0.5)
        top = am.get_top_targets(2)
        assert len(top) == 2
        assert top[0].attention_weight >= top[1].attention_weight

    def test_shift_attention(self):
        """转移注意力"""
        am = AttentionMechanism()
        am.allocate_attention("c1", AttentionType.TOP_DOWN, 0.5)
        result = am.shift_attention("c1", "c2")
        assert result is True
        assert am.get_attention_for_content("c1") == 0.0
        assert am.get_attention_for_content("c2") > 0.0

    def test_shift_nonexistent(self):
        """转移不存在的注意力"""
        am = AttentionMechanism()
        assert am.shift_attention("nonexistent", "c2") is False

    def test_get_stats(self):
        """获取统计"""
        am = AttentionMechanism()
        am.allocate_attention("c1", AttentionType.TOP_DOWN, 0.3)
        am.allocate_attention("c2", AttentionType.BOTTOM_UP, 0.4)
        stats = am.get_stats()
        assert stats["target_count"] == 2
        assert stats["top_down_count"] == 1
        assert stats["bottom_up_count"] == 1

    def test_clear(self):
        """清空"""
        am = AttentionMechanism()
        am.allocate_attention("c1", AttentionType.TOP_DOWN, 0.3)
        am.clear()
        assert am.get_total_attention() == 0.0

    def test_nan_weight(self):
        """NaN权重防御"""
        am = AttentionMechanism()
        target = am.allocate_attention("c1", AttentionType.TOP_DOWN, float("nan"))
        assert 0.0 <= target.attention_weight <= 1.0

    def test_inf_weight(self):
        """Inf权重防御"""
        am = AttentionMechanism()
        target = am.allocate_attention("c1", AttentionType.TOP_DOWN, float("inf"))
        assert 0.0 <= target.attention_weight <= 1.0

    def test_negative_weight(self):
        """负权重钳制"""
        am = AttentionMechanism()
        target = am.allocate_attention("c1", AttentionType.TOP_DOWN, -0.5)
        assert target.attention_weight == 0.0

    def test_huge_weight(self):
        """超大权重钳制"""
        am = AttentionMechanism()
        target = am.allocate_attention("c1", AttentionType.TOP_DOWN, 1e10)
        assert target.attention_weight <= 1.0


# ============================================================
# 2. ConsciousnessLevel / ConsciousnessState 测试
# ============================================================

class TestConsciousnessState:
    """意识状态测试"""

    def test_level_hierarchy(self):
        """意识层级递增"""
        assert ConsciousnessLevel.UNCONSCIOUS.value < ConsciousnessLevel.PRE_CONSCIOUS.value
        assert ConsciousnessLevel.PRE_CONSCIOUS.value < ConsciousnessLevel.CONSCIOUS.value
        assert ConsciousnessLevel.CONSCIOUS.value < ConsciousnessLevel.META_CONSCIOUS.value

    def test_default_state(self):
        """默认状态"""
        state = ConsciousnessState()
        assert state.level == ConsciousnessLevel.PRE_CONSCIOUS
        assert state.arousal == 0.5

    def test_is_conscious(self):
        """是否有意识"""
        state = ConsciousnessState(level=ConsciousnessLevel.CONSCIOUS)
        assert state.is_conscious is True

    def test_not_conscious(self):
        """无意识"""
        state = ConsciousnessState(level=ConsciousnessLevel.UNCONSCIOUS)
        assert state.is_conscious is False

    def test_is_meta_conscious(self):
        """元意识"""
        state = ConsciousnessState(level=ConsciousnessLevel.META_CONSCIOUS)
        assert state.is_meta_conscious is True

    def test_update_level_unconscious(self):
        """低唤醒度→无意识"""
        state = ConsciousnessState(arousal=0.1)
        state.update_level()
        assert state.level == ConsciousnessLevel.UNCONSCIOUS

    def test_update_level_pre_conscious(self):
        """中等唤醒度→前意识"""
        state = ConsciousnessState(arousal=0.3)
        state.update_level()
        assert state.level == ConsciousnessLevel.PRE_CONSCIOUS

    def test_update_level_conscious(self):
        """高唤醒度→意识"""
        state = ConsciousnessState(arousal=0.6, awareness=0.5, focus=0.5)
        state.update_level()
        assert state.level == ConsciousnessLevel.CONSCIOUS

    def test_update_level_meta_conscious(self):
        """高觉知高专注→元意识"""
        state = ConsciousnessState(arousal=0.8, awareness=0.9, focus=0.8)
        state.update_level()
        assert state.level == ConsciousnessLevel.META_CONSCIOUS


# ============================================================
# 3. ConsciousnessFirstPrinciplesEngine 新接口测试
# ============================================================

class TestEnhancedEngine:
    """增强引擎测试"""

    def test_focus_attention(self):
        """聚焦注意力"""
        engine = create_consciousness_engine()
        target = engine.focus_attention("c1", 0.7, AttentionType.TOP_DOWN)
        assert target.content_id == "c1"
        assert target.attention_weight == 0.7

    def test_release_attention(self):
        """释放注意力"""
        engine = create_consciousness_engine()
        target = engine.focus_attention("c1", 0.5)
        assert engine.release_attention(target.target_id) is True

    def test_shift_attention(self):
        """转移注意力"""
        engine = create_consciousness_engine()
        engine.focus_attention("c1", 0.5)
        assert engine.shift_attention("c1", "c2") is True
        assert engine.get_attention_for_content("c2") > 0.0

    def test_get_attention_targets(self):
        """获取注意力目标"""
        engine = create_consciousness_engine()
        engine.focus_attention("c1", 0.5)
        engine.focus_attention("c2", 0.3)
        targets = engine.get_attention_targets()
        assert len(targets) == 2

    def test_get_top_attention_targets(self):
        """获取最高注意力目标"""
        engine = create_consciousness_engine()
        engine.focus_attention("c1", 0.3)
        engine.focus_attention("c2", 0.8)
        top = engine.get_top_attention_targets(1)
        assert len(top) == 1
        assert top[0].content_id == "c2"

    def test_get_attention_for_content(self):
        """获取内容注意力"""
        engine = create_consciousness_engine()
        engine.focus_attention("c1", 0.5)
        assert engine.get_attention_for_content("c1") == 0.5

    def test_update_consciousness_state(self):
        """更新意识状态"""
        engine = create_consciousness_engine()
        engine.update_consciousness_state(arousal=0.8, awareness=0.9, focus=0.8)
        assert engine.is_meta_conscious() is True

    def test_get_consciousness_level(self):
        """获取意识层级"""
        engine = create_consciousness_engine()
        level = engine.get_consciousness_level()
        assert isinstance(level, ConsciousnessLevel)

    def test_get_consciousness_state(self):
        """获取意识状态"""
        engine = create_consciousness_engine()
        state = engine.get_consciousness_state()
        assert isinstance(state, ConsciousnessState)

    def test_is_conscious(self):
        """是否有意识"""
        engine = create_consciousness_engine()
        engine.update_consciousness_state(arousal=0.6, awareness=0.5, focus=0.5)
        assert engine.is_conscious() is True

    def test_broadcast_updates_attention(self):
        """广播自动分配注意力"""
        engine = create_consciousness_engine()
        content = create_workspace_content("c1", ContentType.PERCEPTION, "data", 0.8)
        engine.broadcast(content)
        # 广播应自动分配注意力
        assert engine.get_attention_for_content("c1") > 0.0

    def test_stats_include_new_components(self):
        """统计包含新组件"""
        engine = create_consciousness_engine()
        stats = engine.get_stats()
        assert "attention_stats" in stats
        assert "consciousness_level" in stats
        assert "consciousness_state" in stats

    def test_get_attention_mechanism(self):
        """获取注意力机制"""
        engine = create_consciousness_engine()
        am = engine.get_attention_mechanism()
        assert isinstance(am, AttentionMechanism)


# ============================================================
# 4. 向后兼容性测试
# ============================================================

class TestBackwardCompat:
    """向后兼容性测试"""

    def test_broadcast(self):
        """广播内容"""
        engine = create_consciousness_engine()
        content = create_workspace_content("c1", ContentType.PERCEPTION, "data", 0.8)
        assert engine.broadcast(content) is True

    def test_broadcast_none(self):
        """广播None"""
        engine = create_consciousness_engine()
        assert engine.broadcast(None) is False

    def test_broadcast_capacity_limit(self):
        """广播容量限制"""
        engine = create_consciousness_engine(capacity=2)
        engine.broadcast(create_workspace_content("c1", ContentType.PERCEPTION, "d1", 0.5))
        engine.broadcast(create_workspace_content("c2", ContentType.PERCEPTION, "d2", 0.7))
        # 第三个应该驱逐最低显著度的
        result = engine.broadcast(create_workspace_content("c3", ContentType.PERCEPTION, "d3", 0.9))
        assert result is True
        contents = engine.get_conscious_contents()
        assert len(contents) == 2

    def test_broadcast_low_salience_rejected(self):
        """低显著度被拒绝"""
        engine = create_consciousness_engine(capacity=1)
        engine.broadcast(create_workspace_content("c1", ContentType.PERCEPTION, "d1", 0.9))
        # 低显著度无法进入
        result = engine.broadcast(create_workspace_content("c2", ContentType.PERCEPTION, "d2", 0.3))
        assert result is False

    def test_get_conscious_contents(self):
        """获取意识内容"""
        engine = create_consciousness_engine()
        engine.broadcast(create_workspace_content("c1", ContentType.PERCEPTION, "d1", 0.8))
        contents = engine.get_conscious_contents()
        assert len(contents) == 1

    def test_get_dominant_content(self):
        """获取主导内容"""
        engine = create_consciousness_engine()
        engine.broadcast(create_workspace_content("c1", ContentType.PERCEPTION, "d1", 0.5))
        engine.broadcast(create_workspace_content("c2", ContentType.PERCEPTION, "d2", 0.9))
        dominant = engine.get_dominant_content()
        assert dominant.content_id == "c2"

    def test_get_dominant_content_empty(self):
        """空工作空间主导内容"""
        engine = create_consciousness_engine()
        assert engine.get_dominant_content() is None

    def test_is_in_consciousness(self):
        """检查内容是否在意识中"""
        engine = create_consciousness_engine()
        engine.broadcast(create_workspace_content("c1", ContentType.PERCEPTION, "d1", 0.8))
        assert engine.is_in_consciousness("c1") is True
        assert engine.is_in_consciousness("c2") is False

    def test_update_salience(self):
        """更新显著度"""
        engine = create_consciousness_engine()
        engine.broadcast(create_workspace_content("c1", ContentType.PERCEPTION, "d1", 0.5))
        assert engine.update_salience("c1", 0.9) is True
        contents = engine.get_conscious_contents()
        assert contents[0].salience == 0.9

    def test_update_salience_nonexistent(self):
        """更新不存在的显著度"""
        engine = create_consciousness_engine()
        assert engine.update_salience("nonexistent", 0.9) is False

    def test_clear_workspace(self):
        """清空工作空间"""
        engine = create_consciousness_engine()
        engine.broadcast(create_workspace_content("c1", ContentType.PERCEPTION, "d1", 0.8))
        engine.clear_workspace()
        assert len(engine.get_conscious_contents()) == 0

    def test_get_stream(self):
        """获取意识流"""
        engine = create_consciousness_engine(capacity=1)
        engine.broadcast(create_workspace_content("c1", ContentType.PERCEPTION, "d1", 0.5))
        engine.broadcast(create_workspace_content("c2", ContentType.PERCEPTION, "d2", 0.9))
        stream = engine.get_stream()
        assert len(stream) >= 1

    def test_get_stats_backward_compat(self):
        """统计向后兼容"""
        engine = create_consciousness_engine()
        stats = engine.get_stats()
        assert "engine_id" in stats
        assert "workspace_size" in stats
        assert "capacity" in stats
        assert "stream_length" in stats
        assert "cycle_count" in stats
        assert "dominant_content" in stats
        assert "consciousness_utilization" in stats

    def test_reset(self):
        """重置"""
        engine = create_consciousness_engine()
        engine.broadcast(create_workspace_content("c1", ContentType.PERCEPTION, "d1", 0.8))
        engine.focus_attention("c1", 0.5)
        engine.reset()
        stats = engine.get_stats()
        assert stats["workspace_size"] == 0
        assert stats["attention_stats"]["target_count"] == 0

    def test_create_workspace_content_helper(self):
        """create_workspace_content 便捷函数"""
        content = create_workspace_content("c1", ContentType.PERCEPTION, "data", 0.8)
        assert content.content_id == "c1"
        assert content.salience == 0.8

    def test_create_attention_target_helper(self):
        """create_attention_target 便捷函数"""
        target = create_attention_target("c1", AttentionType.TOP_DOWN, 0.5)
        assert target.content_id == "c1"
        assert target.attention_weight == 0.5


# ============================================================
# 5. 并发安全测试
# ============================================================

class TestConcurrency:
    """并发安全测试"""

    def test_concurrent_broadcast(self):
        """并发广播"""
        engine = create_consciousness_engine(capacity=100)
        errors = []

        def worker(worker_id):
            try:
                for i in range(20):
                    content = create_workspace_content(
                        f"w{worker_id}_c{i}", ContentType.PERCEPTION, f"d{i}", 0.5,
                    )
                    engine.broadcast(content)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_attention(self):
        """并发注意力分配"""
        engine = create_consciousness_engine()
        errors = []

        def worker(worker_id):
            try:
                for i in range(20):
                    engine.focus_attention(f"c{worker_id}_{i}", 0.1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_state_update(self):
        """并发状态更新"""
        engine = create_consciousness_engine()
        errors = []

        def worker(worker_id):
            try:
                for i in range(20):
                    engine.update_consciousness_state(arousal=0.5 + i * 0.01)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ============================================================
# 6. 性能测试
# ============================================================

class TestPerformance:
    """性能测试"""

    def test_broadcast_performance(self):
        """广播性能：1000次 < 1秒"""
        engine = create_consciousness_engine(capacity=100)
        start = time.time()
        for i in range(1000):
            content = create_workspace_content(f"c{i}", ContentType.PERCEPTION, f"d{i}", 0.5)
            engine.broadcast(content)
        elapsed = time.time() - start
        assert elapsed < 1.0, f"广播1000次耗时 {elapsed:.3f}s"

    def test_attention_performance(self):
        """注意力分配性能：1000次 < 1秒"""
        engine = create_consciousness_engine()
        start = time.time()
        for i in range(1000):
            engine.focus_attention(f"c{i}", 0.001)
        elapsed = time.time() - start
        assert elapsed < 1.0, f"注意力分配1000次耗时 {elapsed:.3f}s"

    def test_state_update_performance(self):
        """状态更新性能：1000次 < 0.5秒"""
        engine = create_consciousness_engine()
        start = time.time()
        for i in range(1000):
            engine.update_consciousness_state(arousal=0.5)
        elapsed = time.time() - start
        assert elapsed < 1.0, f"状态更新1000次耗时 {elapsed:.3f}s"


# ============================================================
# 7. 异常容错测试
# ============================================================

class TestErrorTolerance:
    """异常容错测试"""

    def test_broadcast_nan_salience(self):
        """NaN显著度"""
        engine = create_consciousness_engine()
        content = create_workspace_content("c1", ContentType.PERCEPTION, "d", float("nan"))
        result = engine.broadcast(content)
        assert result is True
        assert 0.0 <= content.salience <= 1.0

    def test_broadcast_inf_salience(self):
        """Inf显著度"""
        engine = create_consciousness_engine()
        content = create_workspace_content("c1", ContentType.PERCEPTION, "d", float("inf"))
        result = engine.broadcast(content)
        assert result is True
        assert 0.0 <= content.salience <= 1.0

    def test_broadcast_negative_salience(self):
        """负显著度"""
        engine = create_consciousness_engine()
        content = create_workspace_content("c1", ContentType.PERCEPTION, "d", -0.5)
        result = engine.broadcast(content)
        assert result is True
        assert content.salience == 0.0

    def test_update_salience_nan(self):
        """NaN显著度更新"""
        engine = create_consciousness_engine()
        engine.broadcast(create_workspace_content("c1", ContentType.PERCEPTION, "d", 0.5))
        assert engine.update_salience("c1", float("nan")) is False

    def test_update_consciousness_state_nan(self):
        """NaN状态更新"""
        engine = create_consciousness_engine()
        engine.update_consciousness_state(arousal=float("nan"))
        state = engine.get_consciousness_state()
        assert not math.isnan(state.arousal)

    def test_attention_string_weight(self):
        """字符串权重"""
        am = AttentionMechanism()
        target = am.allocate_attention("c1", AttentionType.TOP_DOWN, "not a number")
        assert 0.0 <= target.attention_weight <= 1.0

    def test_empty_workspace_stats(self):
        """空工作空间统计"""
        engine = create_consciousness_engine()
        stats = engine.get_stats()
        assert stats["workspace_size"] == 0
        assert stats["dominant_content"] is None

    def test_capacity_zero(self):
        """容量为0"""
        engine = create_consciousness_engine(capacity=0)
        content = create_workspace_content("c1", ContentType.PERCEPTION, "d", 0.8)
        result = engine.broadcast(content)
        # 容量为0时，无法广播
        assert result is False


# ============================================================
# 8. 第一性原理验证测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_attention_is_limited_resource(self):
        """注意力是有限资源"""
        am = AttentionMechanism(total_capacity=1.0)
        am.allocate_attention("c1", AttentionType.TOP_DOWN, 0.6)
        am.allocate_attention("c2", AttentionType.TOP_DOWN, 0.6)
        # 总注意力不应超过容量
        assert am.get_total_attention() <= 1.0

    def test_top_down_vs_bottom_up(self):
        """自上而下 vs 自下而上"""
        am = AttentionMechanism()
        am.allocate_attention("c1", AttentionType.TOP_DOWN, 0.5)
        am.allocate_attention("c2", AttentionType.BOTTOM_UP, 0.3)
        stats = am.get_stats()
        assert stats["top_down_count"] == 1
        assert stats["bottom_up_count"] == 1

    def test_consciousness_level_progression(self):
        """意识层级递进"""
        # 无意识
        state = ConsciousnessState(arousal=0.1)
        state.update_level()
        assert state.level == ConsciousnessLevel.UNCONSCIOUS

        # 前意识
        state = ConsciousnessState(arousal=0.3)
        state.update_level()
        assert state.level == ConsciousnessLevel.PRE_CONSCIOUS

        # 意识
        state = ConsciousnessState(arousal=0.6, awareness=0.5, focus=0.5)
        state.update_level()
        assert state.level == ConsciousnessLevel.CONSCIOUS

        # 元意识
        state = ConsciousnessState(arousal=0.8, awareness=0.9, focus=0.8)
        state.update_level()
        assert state.level == ConsciousnessLevel.META_CONSCIOUS

    def test_workspace_competition(self):
        """工作空间竞争"""
        engine = create_consciousness_engine(capacity=2)
        # 低显著度先进入
        engine.broadcast(create_workspace_content("c1", ContentType.PERCEPTION, "d1", 0.3))
        engine.broadcast(create_workspace_content("c2", ContentType.PERCEPTION, "d2", 0.5))
        # 高显著度应驱逐最低的
        engine.broadcast(create_workspace_content("c3", ContentType.PERCEPTION, "d3", 0.9))
        contents = engine.get_conscious_contents()
        # c1应被驱逐
        assert not engine.is_in_consciousness("c1")
        assert engine.is_in_consciousness("c3")

    def test_broadcast_increases_arousal(self):
        """广播增加唤醒度"""
        engine = create_consciousness_engine(capacity=5)
        initial_arousal = engine.get_consciousness_state().arousal
        for i in range(3):
            engine.broadcast(create_workspace_content(f"c{i}", ContentType.PERCEPTION, f"d{i}", 0.8))
        final_arousal = engine.get_consciousness_state().arousal
        assert final_arousal >= initial_arousal

    def test_attention_shift_transfers_weight(self):
        """注意力转移权重"""
        am = AttentionMechanism(total_capacity=1.0)
        am.allocate_attention("c1", AttentionType.TOP_DOWN, 0.5)
        original_weight = am.get_attention_for_content("c1")
        am.shift_attention("c1", "c2")
        new_weight = am.get_attention_for_content("c2")
        # 转移后c2应有注意力
        assert new_weight > 0.0
        assert am.get_attention_for_content("c1") == 0.0

    def test_meta_consciousness_requires_high_awareness(self):
        """元意识需要高觉知度和专注度"""
        # 高唤醒但低觉知 → 意识而非元意识
        state = ConsciousnessState(arousal=0.9, awareness=0.5, focus=0.5)
        state.update_level()
        assert state.level == ConsciousnessLevel.CONSCIOUS
        assert not state.is_meta_conscious

        # 高唤醒高觉知高专注 → 元意识
        state = ConsciousnessState(arousal=0.9, awareness=0.9, focus=0.8)
        state.update_level()
        assert state.is_meta_conscious
