"""
阶段86-90: 核心引擎整合

第一性原理:
1. 整体大于部分之和：整合产生涌现能力
2. 各引擎必须协调一致：冲突导致系统失效
3. 统一接口简化使用

设计原则:
- UnifiedFirstPrinciplesEngine: 统一引擎
- 整合预测编码、驱力、学习、探索、记忆、进化、安全、能效、社交、创造、因果、元认知、情感、意识、自由意志
- 提供单一入口和协调机制
"""

import threading
import time
from typing import Any, Dict, List, Optional

# 导入所有第一性原理引擎
try:
    from .predictive_coding_engine import (
        PredictiveCodingEngine, create_predictive_coding_engine,
        PrecisionWeight,
    )
    from .drive_first_principles import (
        DriveFirstPrinciplesEngine, create_drive_engine,
        DriveType, DriveGap,
    )
    from .learning_first_principles import (
        LearningFirstPrinciplesEngine, create_learning_engine,
        UpdateType,
    )
    from .exploration_first_principles import (
        ExplorationFirstPrinciplesEngine, create_exploration_engine,
        ExplorationStrategy,
    )
    from .memory_first_principles import (
        MemoryFirstPrinciplesEngine, create_memory_engine,
        MemoryPriority,
    )
    from .evolution_first_principles import (
        EvolutionFirstPrinciplesEngine, create_evolution_engine,
        GoalType,
    )
    from .safety_first_principles import (
        SafetyFirstPrinciplesEngine, create_safety_engine,
        BoundaryType, RiskLevel,
    )
    from .efficiency_first_principles import (
        EfficiencyFirstPrinciplesEngine, create_efficiency_engine,
        ResourceType,
    )
    from .social_first_principles import (
        SocialFirstPrinciplesEngine, create_social_engine,
        MessageType,
    )
    from .creativity_first_principles import (
        CreativityFirstPrinciplesEngine, create_creativity_engine,
        ConceptType,
    )
    from .causal_first_principles import (
        CausalFirstPrinciplesEngine, create_causal_engine,
        CausalStrength,
    )
    from .metacognition_first_principles import (
        MetacognitionFirstPrinciplesEngine, create_metacognition_engine,
        CognitiveStrategy, ConfidenceLevel,
    )
    from .emotion_first_principles import (
        EmotionFirstPrinciplesEngine, create_emotion_engine,
        EmotionType,
    )
    from .consciousness_first_principles import (
        ConsciousnessFirstPrinciplesEngine, create_consciousness_engine,
        ContentType, WorkspaceContent,
    )
    from .free_will_first_principles import (
        FreeWillFirstPrinciplesEngine, create_free_will_engine,
        DecisionSource, ChoiceSet,
    )
except ImportError:
    # 绝对导入回退（用于独立测试）
    from predictive_coding_engine import (
        PredictiveCodingEngine, create_predictive_coding_engine,
        PrecisionWeight,
    )
    from drive_first_principles import (
        DriveFirstPrinciplesEngine, create_drive_engine,
        DriveType, DriveGap,
    )
    from learning_first_principles import (
        LearningFirstPrinciplesEngine, create_learning_engine,
        UpdateType,
    )
    from exploration_first_principles import (
        ExplorationFirstPrinciplesEngine, create_exploration_engine,
        ExplorationStrategy,
    )
    from memory_first_principles import (
        MemoryFirstPrinciplesEngine, create_memory_engine,
        MemoryPriority,
    )
    from evolution_first_principles import (
        EvolutionFirstPrinciplesEngine, create_evolution_engine,
        GoalType,
    )
    from safety_first_principles import (
        SafetyFirstPrinciplesEngine, create_safety_engine,
        BoundaryType, RiskLevel,
    )
    from efficiency_first_principles import (
        EfficiencyFirstPrinciplesEngine, create_efficiency_engine,
        ResourceType,
    )
    from social_first_principles import (
        SocialFirstPrinciplesEngine, create_social_engine,
        MessageType,
    )
    from creativity_first_principles import (
        CreativityFirstPrinciplesEngine, create_creativity_engine,
        ConceptType,
    )
    from causal_first_principles import (
        CausalFirstPrinciplesEngine, create_causal_engine,
        CausalStrength,
    )
    from metacognition_first_principles import (
        MetacognitionFirstPrinciplesEngine, create_metacognition_engine,
        CognitiveStrategy, ConfidenceLevel,
    )
    from emotion_first_principles import (
        EmotionFirstPrinciplesEngine, create_emotion_engine,
        EmotionType,
    )
    from consciousness_first_principles import (
        ConsciousnessFirstPrinciplesEngine, create_consciousness_engine,
        ContentType, WorkspaceContent,
    )
    from free_will_first_principles import (
        FreeWillFirstPrinciplesEngine, create_free_will_engine,
        DecisionSource, ChoiceSet,
    )


class UnifiedFirstPrinciplesEngine:
    """
    统一第一性原理引擎

    整合所有第一性原理引擎，提供协调一致的系统入口。

    核心循环:
    1. 感知 -> 预测编码（生成预测，计算误差）
    2. 误差 -> 驱力（产生缺口）
    3. 驱力 -> 情感（标记价值）
    4. 情感 -> 意识（进入全局工作空间）
    5. 意识 -> 元认知（评估策略）
    6. 元认知 -> 自由意志（做出决策）
    7. 决策 -> 因果（评估干预效果）
    8. 行动 -> 学习（从误差更新）
    9. 学习 -> 记忆（存储高价值信息）
    10. 记忆 -> 探索（发现新信息）
    11. 探索 -> 创造（组合新概念）
    12. 创造 -> 社交（共享知识）
    13. 社交 -> 进化（推进无限目标）
    14. 进化 -> 安全/能效（约束与优化）
    """

    def __init__(self, engine_id: str = "unified_engine"):
        self.engine_id = engine_id

        # 初始化所有子引擎
        self.predictive_coding = create_predictive_coding_engine("predictive_coding")
        self.drive = create_drive_engine("drive")
        self.learning = create_learning_engine("learning")
        self.exploration = create_exploration_engine("exploration")
        self.memory = create_memory_engine("memory", capacity=1000)
        self.evolution = create_evolution_engine("evolution")
        self.safety = create_safety_engine("safety")
        self.efficiency = create_efficiency_engine("efficiency")
        self.social = create_social_engine("social")
        self.creativity = create_creativity_engine("creativity")
        self.causal = create_causal_engine("causal")
        self.metacognition = create_metacognition_engine("metacognition")
        self.emotion = create_emotion_engine("emotion")
        self.consciousness = create_consciousness_engine("consciousness", capacity=5)
        self.free_will = create_free_will_engine("free_will")

        self._lock = threading.RLock()
        self._cycle_count = 0
        self._running = False

    def perceive_and_predict(
        self,
        module_id: str,
        current_state: Dict[str, Any],
        actual_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        感知与预测

        阶段86: 预测编码整合
        """
        prediction, error, correction = self.predictive_coding.run_cycle(
            module_id, current_state, actual_state
        )

        # 误差驱动情感
        if error:
            self.emotion.process_event(
                "prediction_error",
                prediction_error=error.surprise,
                information_value=error.precision.value,
            )

            # 误差驱动学习
            self.learning.learn_from_error(
                parameter_name=f"{module_id}_params",
                error_magnitude=error.weighted_error,
                delta=-0.1,
                error_source=module_id,
            )

        return {
            "prediction": prediction,
            "error": error,
            "correction": correction,
        }

    def evaluate_drives(self) -> List[DriveGap]:
        """
        评估驱力

        阶段87: 驱力整合
        """
        # 从进化目标推导驱力状态
        evo_stats = self.evolution.get_stats()
        goals = evo_stats.get("goals", {})

        safe_level = goals.get("safe", {}).get("level", 0.5)
        gain_level = goals.get("gain", {}).get("level", 0.5)
        eff_level = goals.get("eff", {}).get("level", 0.5)

        self.drive.update_state(safe_level=safe_level, gain_level=gain_level, eff_level=eff_level)
        gaps = self.drive.compute_gaps()

        # 主导缺口进入意识
        dominant = self.drive.get_dominant_gap()
        if dominant:
            self.consciousness.broadcast(WorkspaceContent(
                content_id=f"drive_gap_{dominant.gap_id}",
                content_type=ContentType.GOAL,
                content=dominant,
                salience=dominant.urgency,
            ))

        return gaps

    def make_consolidated_decision(self, choice_set: ChoiceSet) -> Dict[str, Any]:
        """
        做出整合决策

        阶段88: 决策整合
        """
        # 元认知评估
        self.metacognition.update_state(
            cognitive_load=len(self.consciousness.get_conscious_contents()) / 5.0,
        )
        strategy = self.metacognition.select_strategy({"complexity": 0.5, "urgency": 0.5})

        # 安全评估
        safety_check = self.safety.evaluate_operation({
            "required_resources": choice_set.context.get("resources", {})
        })

        # 能效评估
        efficiency_check = self.efficiency.evaluate_action_efficiency(
            choice_set.choice_id,
            choice_set.context.get("resources", {}),
            choice_set.context.get("expected_value", 1.0),
        )

        # 自由意志决策
        def value_function(option: str, context: Dict[str, Any]) -> float:
            score = 0.0
            # 驱力匹配
            dominant = self.drive.get_dominant_gap()
            if dominant:
                if dominant.drive_type.value in option:
                    score += 0.3
            # 安全
            if safety_check["allowed"]:
                score += 0.2
            # 能效
            score += efficiency_check["projected_efficiency"] * 0.2
            # 情感
            bias = self.emotion.get_attention_bias()
            score += bias.get("exploration", 0.0) * 0.1
            return score

        decision = self.free_will.make_decision(choice_set, value_function)

        # 决策进入意识
        self.consciousness.broadcast(WorkspaceContent(
            content_id=f"decision_{decision.decision_id}",
            content_type=ContentType.ACTION,
            content=decision,
            salience=0.9,
        ))

        return {
            "decision": decision,
            "strategy": strategy,
            "safety_check": safety_check,
            "efficiency_check": efficiency_check,
        }

    def learn_and_evolve(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """
        学习与进化

        阶段89: 学习进化整合
        """
        # 记录结果到因果引擎
        self.causal.record_observation(outcome)

        # 高价值信息存入记忆
        if outcome.get("information_value", 0.0) > 0.5:
            self.memory.store(
                f"outcome_{self._cycle_count}",
                outcome,
                context={"error_reduction_potential": outcome.get("error_reduction", 0.0)},
            )

        # 更新进化目标
        if "safe_improvement" in outcome:
            self.evolution.update_progress(GoalType.SAFE, outcome["safe_improvement"])
        if "gain_improvement" in outcome:
            self.evolution.update_progress(GoalType.GAIN, outcome["gain_improvement"])
        if "eff_improvement" in outcome:
            self.evolution.update_progress(GoalType.EFF, outcome["eff_improvement"])

        # 检查漂移
        drift = self.evolution.check_drift()

        return {
            "memory_stored": outcome.get("information_value", 0.0) > 0.5,
            "drift_detected": drift.value if drift else None,
        }

    def run_integration_cycle(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行整合周期

        阶段90: 完整整合循环
        """
        with self._lock:
            self._cycle_count += 1

        # 1. 评估驱力
        gaps = self.evaluate_drives()

        # 2. 如果有显著缺口，做出决策
        decision_result = None
        if self.drive.is_action_required():
            choices = ChoiceSet(
                choice_id=f"cycle_{self._cycle_count}",
                options=context.get("available_actions", ["wait", "explore", "exploit"]),
                context=context,
            )
            decision_result = self.make_consolidated_decision(choices)

        # 3. 学习与进化
        learn_result = self.learn_and_evolve(context.get("outcome", {}))

        # 4. 更新安全边界
        self.safety.analyze_stability()

        # 5. 记录能效
        if "resources_used" in context:
            for rtype, amount in context["resources_used"].items():
                try:
                    rt = ResourceType(rtype)
                    self.efficiency.record_usage(
                        f"usage_{self._cycle_count}", rt, amount,
                        context.get("output_value", 0.0),
                    )
                except ValueError:
                    pass

        return {
            "cycle": self._cycle_count,
            "gaps": len(gaps),
            "dominant_drive": self.drive.get_dominant_gap().drive_type.value if self.drive.get_dominant_gap() else None,
            "decision": decision_result["decision"].chosen_action if decision_result else None,
            "consciousness_contents": len(self.consciousness.get_conscious_contents()),
            "learn_result": learn_result,
        }

    def get_full_stats(self) -> Dict[str, Any]:
        """获取完整统计"""
        return {
            "engine_id": self.engine_id,
            "cycle_count": self._cycle_count,
            "predictive_coding": self.predictive_coding.get_stats(),
            "drive": self.drive.get_stats(),
            "learning": self.learning.get_stats(),
            "exploration": self.exploration.get_stats(),
            "memory": self.memory.get_stats(),
            "evolution": self.evolution.get_stats(),
            "safety": self.safety.get_stats(),
            "efficiency": self.efficiency.get_stats(),
            "social": self.social.get_stats(),
            "creativity": self.creativity.get_stats(),
            "causal": self.causal.get_stats(),
            "metacognition": self.metacognition.get_stats(),
            "emotion": self.emotion.get_stats(),
            "consciousness": self.consciousness.get_stats(),
            "free_will": self.free_will.get_stats(),
        }


# ============================================================
# 便捷函数
# ============================================================

def create_unified_engine(engine_id: str = "unified_engine") -> UnifiedFirstPrinciplesEngine:
    """创建统一引擎"""
    return UnifiedFirstPrinciplesEngine(engine_id=engine_id)
