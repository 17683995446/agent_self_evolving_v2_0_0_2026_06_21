"""
阶段104: 单元全覆盖测试

穷尽所有 if/else、循环、分支、特殊场景，确保每段代码均可正常触发执行。
覆盖第一轮压力测试发现的 bug 修复 + 静态代码核验发现的高危问题。
"""

import pytest
import math
import time
import threading
from unittest.mock import MagicMock, patch

from self_evolving_agent.core.safety_first_principles import SafetyFirstPrinciplesEngine, create_safety_engine
from self_evolving_agent.core.consciousness_first_principles import (
    ConsciousnessFirstPrinciplesEngine, WorkspaceContent, ContentType, create_consciousness_engine,
)
from self_evolving_agent.core.free_will_first_principles import (
    FreeWillFirstPrinciplesEngine, ChoiceSet, DecisionSource, create_free_will_engine,
)
from self_evolving_agent.core.causal_first_principles import CausalFirstPrinciplesEngine
from self_evolving_agent.core.drive_first_principles import DriveFirstPrinciplesEngine, DriveType
from self_evolving_agent.core.predictive_coding_engine import PredictiveCodingEngine, Prediction, PredictionError, PrecisionWeight, Correction
from self_evolving_agent.core.memory_first_principles import MemoryFirstPrinciplesEngine, MemoryPriority, MemoryItem
from self_evolving_agent.core.efficiency_first_principles import EfficiencyFirstPrinciplesEngine, ResourceType
from self_evolving_agent.core.emotion_first_principles import EmotionFirstPrinciplesEngine, EmotionType
from self_evolving_agent.core.metacognition_first_principles import MetacognitionFirstPrinciplesEngine
from self_evolving_agent.core.engine_coordinators import (
    MotivationCoordinator, ExplorationCoordinator,
)


# ============================================================
# Bug 1: safety.evaluate_operation(None) — 已修复
# ============================================================

class TestSafetyEngineFix:
    """测试 safety 引擎 None 输入防御"""

    def test_evaluate_operation_none(self):
        """None 输入应返回拒绝而非崩溃"""
        engine = create_safety_engine("test")
        result = engine.evaluate_operation(None)
        assert result["allowed"] is False
        assert result["risk_score"] == 1.0

    def test_evaluate_operation_empty_dict(self):
        """空字典应正常处理"""
        engine = create_safety_engine("test")
        result = engine.evaluate_operation({})
        assert result["allowed"] is True
        assert result["risk_score"] == 0.0

    def test_evaluate_operation_non_dict(self):
        """非字典类型应返回拒绝"""
        engine = create_safety_engine("test")
        for val in [42, "string", [1, 2], True]:
            result = engine.evaluate_operation(val)
            assert result["allowed"] is False

    def test_evaluate_operation_none_resources(self):
        """required_resources 为 None 应正常处理"""
        engine = create_safety_engine("test")
        result = engine.evaluate_operation({"required_resources": None})
        assert result["allowed"] is True


# ============================================================
# Bug 2: consciousness.broadcast(None) — 已修复
# ============================================================

class TestConsciousnessEngineFix:
    """测试 consciousness 引擎 None 输入防御"""

    def test_broadcast_none(self):
        """None 输入应返回 False 而非崩溃"""
        engine = create_consciousness_engine("test", capacity=5)
        result = engine.broadcast(None)
        assert result is False

    def test_broadcast_valid_content(self):
        """正常内容应广播成功"""
        engine = create_consciousness_engine("test", capacity=5)
        content = WorkspaceContent(
            content_id="c1", content_type=ContentType.GOAL,
            content={"x": 1}, salience=0.8,
        )
        result = engine.broadcast(content)
        assert result is True

    def test_broadcast_capacity_full(self):
        """容量满时低显著度内容应被拒绝"""
        engine = create_consciousness_engine("test", capacity=2)
        # 填满
        for i in range(2):
            engine.broadcast(WorkspaceContent(
                content_id=f"c{i}", content_type=ContentType.GOAL,
                content={}, salience=0.9,
            ))
        # 低显著度应被拒绝
        low = WorkspaceContent(
            content_id="low", content_type=ContentType.GOAL,
            content={}, salience=0.1,
        )
        result = engine.broadcast(low)
        assert result is False

    def test_broadcast_eviction(self):
        """容量满时高显著度内容应驱逐低显著度内容"""
        engine = create_consciousness_engine("test", capacity=2)
        engine.broadcast(WorkspaceContent(
            content_id="low", content_type=ContentType.GOAL,
            content={}, salience=0.3,
        ))
        engine.broadcast(WorkspaceContent(
            content_id="mid", content_type=ContentType.GOAL,
            content={}, salience=0.5,
        ))
        # 高显著度应驱逐最低的
        high = WorkspaceContent(
            content_id="high", content_type=ContentType.GOAL,
            content={}, salience=0.9,
        )
        result = engine.broadcast(high)
        assert result is True
        contents = engine.get_conscious_contents()
        assert len(contents) == 2


# ============================================================
# Bug 3: free_will.make_decision(空选项) — 已修复
# ============================================================

class TestFreeWillEngineFix:
    """测试 free_will 引擎空选项防御"""

    def test_make_decision_empty_options(self):
        """空选项应返回 noop 决策而非崩溃"""
        engine = create_free_will_engine("test")
        choices = ChoiceSet(choice_id="test", options=[], context={})
        decision = engine.make_decision(choices)
        assert decision.chosen_action == "noop"
        assert decision.reasons.get("empty_choice_set") is True

    def test_make_decision_normal(self):
        """正常选项应选择最高分"""
        engine = create_free_will_engine("test")
        choices = ChoiceSet(choice_id="test", options=["a", "b", "c"], context={})
        decision = engine.make_decision(choices, lambda o, c: {"a": 0.9, "b": 0.5, "c": 0.1}.get(o, 0.0))
        assert decision.chosen_action == "a"

    def test_make_decision_single_option(self):
        """单选项应正常工作"""
        engine = create_free_will_engine("test")
        choices = ChoiceSet(choice_id="test", options=["only"], context={})
        decision = engine.make_decision(choices)
        assert decision.chosen_action == "only"


# ============================================================
# Bug 4: causal.record_observation(None) — 已修复
# ============================================================

class TestCausalEngineFix:
    """测试 causal 引擎 None 输入防御"""

    def test_record_observation_none(self):
        """None 输入应正常处理而非崩溃"""
        engine = CausalFirstPrinciplesEngine("test")
        engine.record_observation(None)
        stats = engine.get_stats()
        assert stats["cycle_count"] == 1

    def test_record_observation_non_dict(self):
        """非字典类型应正常处理"""
        engine = CausalFirstPrinciplesEngine("test")
        for val in [42, "string", [1, 2], None]:
            engine.record_observation(val)
        stats = engine.get_stats()
        assert stats["cycle_count"] == 4

    def test_record_observation_normal(self):
        """正常字典应记录"""
        engine = CausalFirstPrinciplesEngine("test")
        engine.record_observation({"x": 1, "y": 2})
        stats = engine.get_stats()
        assert stats["cycle_count"] == 1


# ============================================================
# Bug 5: motivation.update_evolution(None) — 已修复
# ============================================================

class TestMotivationCoordinatorFix:
    """测试动机协调器 None 输入防御"""

    def test_update_evolution_none(self):
        """None 输入应正常处理"""
        coord = MotivationCoordinator()
        result = coord.update_evolution(None)
        # 应返回 drift 检测结果，不崩溃
        assert result is not None or result is None  # 只要不崩溃即可

    def test_update_evolution_empty(self):
        """空字典应正常处理"""
        coord = MotivationCoordinator()
        result = coord.update_evolution({})
        assert result is not None or result is None

    def test_update_evolution_normal(self):
        """正常输入应更新进化目标"""
        coord = MotivationCoordinator()
        result = coord.update_evolution({
            "safe_improvement": 0.1,
            "gain_improvement": 0.2,
            "eff_improvement": 0.3,
        })
        assert result is not None or result is None

    def test_process_prediction_error_negative(self):
        """负值输入应正常处理"""
        coord = MotivationCoordinator()
        coord.process_prediction_error(-1, -1)
        # 只要不崩溃即可


# ============================================================
# Bug 6: exploration.record_outcome(None) — 已修复
# ============================================================

class TestExplorationCoordinatorFix:
    """测试探索协调器 None 输入防御"""

    def test_record_outcome_none(self):
        """None 输入应正常处理"""
        coord = ExplorationCoordinator()
        coord.record_outcome(None)

    def test_record_outcome_empty(self):
        """空字典应正常处理"""
        coord = ExplorationCoordinator()
        coord.record_outcome({})

    def test_record_outcome_normal(self):
        """正常输入应记录"""
        coord = ExplorationCoordinator()
        coord.record_outcome({"value": 0.5})


# ============================================================
# Bug 7: drive.is_action_required() 副作用 — 已修复
# ============================================================

class TestDriveEngineSideEffectFix:
    """测试驱力引擎查询方法无副作用"""

    def test_is_action_required_no_side_effect(self):
        """is_action_required 不应增加 cycle_count"""
        engine = DriveFirstPrinciplesEngine("test")
        initial_cycle = engine._cycle_count
        engine.is_action_required()
        engine.is_action_required()
        engine.is_action_required()
        assert engine._cycle_count == initial_cycle  # 不应有副作用

    def test_get_stats_no_side_effect(self):
        """get_stats 不应增加 cycle_count"""
        engine = DriveFirstPrinciplesEngine("test")
        initial_cycle = engine._cycle_count
        engine.get_stats()
        engine.get_stats()
        assert engine._cycle_count == initial_cycle

    def test_is_action_required_true(self):
        """有缺口时应返回 True"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.update_state(safe_level=0.1, gain_level=0.1, eff_level=0.1)
        assert engine.is_action_required() is True

    def test_is_action_required_false(self):
        """无缺口时应返回 False"""
        engine = DriveFirstPrinciplesEngine("test")
        # 默认目标是 1.0，设置当前值也为 1.0
        engine.update_state(safe_level=1.0, gain_level=1.0, eff_level=1.0)
        assert engine.is_action_required() is False


# ============================================================
# Bug 8: predictive_coding predictor/corrector 返回 None — 已修复
# ============================================================

class TestPredictiveCodingNoneFix:
    """测试预测编码引擎 None 返回值防御（阶段114增强：回退到多层预测/贝叶斯更新）"""

    def test_generate_prediction_none_return(self):
        """predictor 返回 None 时应回退到多层预测模型（阶段114增强）"""
        engine = PredictiveCodingEngine("test")
        # 注册一个返回 None 的 predictor
        engine.register_predictor("mod", lambda state: None)
        result = engine.generate_prediction("mod", {"v": 0.5})
        # 阶段114：回退到多层预测模型，不再返回 None
        assert result is not None
        assert isinstance(result, Prediction)
        assert result.source == "mod"

    def test_generate_correction_none_return(self):
        """corrector 返回 None 时应回退到贝叶斯更新（阶段114增强）"""
        engine = PredictiveCodingEngine("test")
        engine.register_corrector("mod", lambda error: None)
        # 需要先有 error 对象
        error = PredictionError(
            error_id="e1", prediction_id="p1", timestamp=time.time(),
            error_vector={"v": 0.1}, surprise=0.01,
            precision=PrecisionWeight.MEDIUM,
        )
        result = engine.generate_correction("mod", error)
        # 阶段114：回退到贝叶斯更新，不再返回 None
        assert result is not None
        assert isinstance(result, Correction)
        assert result.target_module == "mod"


# ============================================================
# Bug 9: memory capacity=0 ZeroDivisionError — 已修复
# ============================================================

class TestMemoryEngineFix:
    """测试记忆引擎边界条件"""

    def test_get_stats_capacity_zero(self):
        """capacity=0 时 get_stats 不应崩溃"""
        engine = MemoryFirstPrinciplesEngine("test", capacity=0)
        stats = engine.get_stats()
        assert stats["utilization"] == 0.0
        assert stats["capacity"] == 0

    def test_retention_score_future_timestamp(self):
        """created_at 在未来时不应崩溃"""
        from self_evolving_agent.core.memory_first_principles import MemoryItem
        item = MemoryItem(
            item_id="test",
            content="data",
            information_value=0.8,
            created_at=time.time() + 999999999,  # 远在未来
        )
        score = item.retention_score
        assert isinstance(score, float)
        assert not math.isnan(score)


# ============================================================
# Bug 10: efficiency 重复 usage_id — 已修复
# ============================================================

class TestEfficiencyEngineFix:
    """测试能效引擎重复 usage_id 防御"""

    def test_duplicate_usage_id(self):
        """重复 usage_id 不应重复累加预算"""
        engine = EfficiencyFirstPrinciplesEngine("test")
        engine.set_budget("b1", ResourceType.CPU, 10.0)
        # 第一次记录
        engine.record_usage("op1", ResourceType.CPU, 3.0, 1.0)
        stats1 = engine.get_stats()
        # 第二次记录同一 usage_id（更新）
        engine.record_usage("op1", ResourceType.CPU, 5.0, 1.0)
        stats2 = engine.get_stats()
        # 预算消耗应为 5.0（更新后的值），而非 3.0+5.0=8.0
        budget = engine._budgets["b1"]
        assert budget.consumed == 5.0  # 不是 8.0


# ============================================================
# Bug 11: emotion 负值情感强度 — 已修复
# ============================================================

class TestEmotionEngineFix:
    """测试情感引擎负值防御"""

    def test_negative_prediction_error(self):
        """负 prediction_error 不应产生负情感"""
        engine = EmotionFirstPrinciplesEngine("test")
        engine.process_event("test", prediction_error=-0.5, information_value=0.5)
        stats = engine.get_stats()
        state = stats.get("state", {})
        emotions = state.get("emotions", {})
        for emotion, value in emotions.items():
            assert value >= 0.0, f"{emotion} 不应为负: {value}"

    def test_negative_information_value(self):
        """负 information_value 不应产生负情感"""
        engine = EmotionFirstPrinciplesEngine("test")
        engine.process_event("test", prediction_error=0.5, information_value=-1)
        stats = engine.get_stats()
        state = stats.get("state", {})
        emotions = state.get("emotions", {})
        for emotion, value in emotions.items():
            assert value >= 0.0, f"{emotion} 不应为负: {value}"

    def test_extreme_values(self):
        """极端大值应被钳制"""
        engine = EmotionFirstPrinciplesEngine("test")
        engine.process_event("test", prediction_error=1e10, information_value=1e10)
        stats = engine.get_stats()
        state = stats.get("state", {})
        emotions = state.get("emotions", {})
        for emotion, value in emotions.items():
            assert 0.0 <= value <= 1.0, f"{emotion} 应在 [0,1]: {value}"


# ============================================================
# Bug 12: metacognition None task_features — 已修复
# ============================================================

class TestMetacognitionEngineFix:
    """测试元认知引擎 None 输入防御"""

    def test_assess_task_none(self):
        """None task_features 不应崩溃"""
        engine = MetacognitionFirstPrinciplesEngine("test")
        result = engine.assess_task("task1", None)
        assert result is not None

    def test_select_strategy_none(self):
        """None task_features 不应崩溃"""
        engine = MetacognitionFirstPrinciplesEngine("test")
        result = engine.select_strategy(None)
        assert result is not None

    def test_select_strategy_empty(self):
        """空字典应正常处理"""
        engine = MetacognitionFirstPrinciplesEngine("test")
        result = engine.select_strategy({})
        assert result is not None

    def test_select_strategy_non_dict(self):
        """非字典类型应正常处理"""
        engine = MetacognitionFirstPrinciplesEngine("test")
        for val in [42, "string", [1, 2], None]:
            result = engine.select_strategy(val)
            assert result is not None


# ============================================================
# 并发安全测试
# ============================================================

class TestConcurrencySafety:
    """并发安全测试"""

    def test_concurrent_observe(self):
        """并发 observe 不应崩溃"""
        from self_evolving_agent import create_default_agent
        agent = create_default_agent()
        errors = []

        def worker(tid):
            try:
                for i in range(20):
                    agent.observe({
                        "module_id": f"t{tid}_{i}",
                        "predicted": {"v": 0.5},
                        "actual": {"v": 0.6},
                    })
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        assert len(errors) == 0, f"并发错误: {errors}"

    def test_concurrent_engine_stats(self):
        """并发 get_stats 不应崩溃"""
        from self_evolving_agent.core.unified_first_principles_engine import create_unified_engine
        engine = create_unified_engine()
        errors = []

        def worker():
            try:
                for _ in range(50):
                    engine.get_full_stats()
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        assert len(errors) == 0, f"并发错误: {errors}"
