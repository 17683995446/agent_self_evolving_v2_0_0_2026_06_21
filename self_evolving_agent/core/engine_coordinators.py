"""
阶段97: 拆分 God Engine 为职责内聚的协调器

第一性原理：单一职责 + 高内聚低耦合
- UnifiedFirstPrinciplesEngine 原本持有 15 个子引擎并直接协调（God Object）
- 现按职责拆分为 4 个协调器：
  1. PerceptionCoordinator  — 感知层：预测编码、学习、记忆
  2. MotivationCoordinator — 动机层：驱力、情感、进化
  3. DecisionCoordinator    — 决策层：元认知、意识、自由意志、安全、能效
  4. ExplorationCoordinator — 探索层：探索、创造、社交、因果

每个协调器只持有自己负责的子引擎，对外提供内聚的接口。
UnifiedFirstPrinciplesEngine 退化为容器 + 周期编排，不再包含领域逻辑。
"""

import threading
from typing import Any, Dict, List, Optional

# 子引擎导入（统一使用相对导入 + 回退）
try:
    from .predictive_coding_engine import PredictiveCodingEngine, create_predictive_coding_engine
    from .drive_first_principles import DriveFirstPrinciplesEngine, create_drive_engine, DriveGap, DriveType
    from .learning_first_principles import LearningFirstPrinciplesEngine, create_learning_engine
    from .exploration_first_principles import ExplorationFirstPrinciplesEngine, create_exploration_engine
    from .memory_first_principles import MemoryFirstPrinciplesEngine, create_memory_engine
    from .evolution_first_principles import EvolutionFirstPrinciplesEngine, create_evolution_engine, GoalType
    from .safety_first_principles import SafetyFirstPrinciplesEngine, create_safety_engine
    from .efficiency_first_principles import EfficiencyFirstPrinciplesEngine, create_efficiency_engine, ResourceType
    from .social_first_principles import SocialFirstPrinciplesEngine, create_social_engine
    from .creativity_first_principles import CreativityFirstPrinciplesEngine, create_creativity_engine
    from .causal_first_principles import CausalFirstPrinciplesEngine, create_causal_engine
    from .metacognition_first_principles import MetacognitionFirstPrinciplesEngine, create_metacognition_engine
    from .emotion_first_principles import EmotionFirstPrinciplesEngine, create_emotion_engine
    from .consciousness_first_principles import (
        ConsciousnessFirstPrinciplesEngine, create_consciousness_engine,
        ContentType, WorkspaceContent,
    )
    from .free_will_first_principles import FreeWillFirstPrinciplesEngine, create_free_will_engine, ChoiceSet
except ImportError:
    from predictive_coding_engine import PredictiveCodingEngine, create_predictive_coding_engine
    from drive_first_principles import DriveFirstPrinciplesEngine, create_drive_engine, DriveGap, DriveType
    from learning_first_principles import LearningFirstPrinciplesEngine, create_learning_engine
    from exploration_first_principles import ExplorationFirstPrinciplesEngine, create_exploration_engine
    from memory_first_principles import MemoryFirstPrinciplesEngine, create_memory_engine
    from evolution_first_principles import EvolutionFirstPrinciplesEngine, create_evolution_engine, GoalType
    from safety_first_principles import SafetyFirstPrinciplesEngine, create_safety_engine
    from efficiency_first_principles import EfficiencyFirstPrinciplesEngine, create_efficiency_engine, ResourceType
    from social_first_principles import SocialFirstPrinciplesEngine, create_social_engine
    from creativity_first_principles import CreativityFirstPrinciplesEngine, create_creativity_engine
    from causal_first_principles import CausalFirstPrinciplesEngine, create_causal_engine
    from metacognition_first_principles import MetacognitionFirstPrinciplesEngine, create_metacognition_engine
    from emotion_first_principles import EmotionFirstPrinciplesEngine, create_emotion_engine
    from consciousness_first_principles import (
        ConsciousnessFirstPrinciplesEngine, create_consciousness_engine,
        ContentType, WorkspaceContent,
    )
    from free_will_first_principles import FreeWillFirstPrinciplesEngine, create_free_will_engine, ChoiceSet


# ============================================================
# 1. 感知层协调器：预测编码 + 学习 + 记忆
# ============================================================

class PerceptionCoordinator:
    """
    感知层协调器

    职责：感知环境 -> 生成预测 -> 计算误差 -> 驱动学习 -> 存储记忆
    持有子引擎：predictive_coding, learning, memory
    """

    def __init__(
        self,
        predictive_coding: Optional[PredictiveCodingEngine] = None,
        learning: Optional[LearningFirstPrinciplesEngine] = None,
        memory: Optional[MemoryFirstPrinciplesEngine] = None,
    ):
        self.predictive_coding = predictive_coding or create_predictive_coding_engine("predictive_coding")
        self.learning = learning or create_learning_engine("learning")
        self.memory = memory or create_memory_engine("memory", capacity=1000)

    def perceive_and_predict(
        self,
        module_id: str,
        current_state: Dict[str, Any],
        actual_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """感知与预测：生成预测、计算误差、驱动学习"""
        prediction, error, correction = self.predictive_coding.run_cycle(
            module_id, current_state, actual_state
        )

        # 误差驱动学习
        if error:
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

    def store_outcome(self, key: str, outcome: Dict[str, Any], context: Dict[str, Any] = None) -> bool:
        """存储高价值结果到记忆"""
        if outcome.get("information_value", 0.0) > 0.5:
            self.memory.store(key, outcome, context=context or {})
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "predictive_coding": self.predictive_coding.get_stats(),
            "learning": self.learning.get_stats(),
            "memory": self.memory.get_stats(),
        }


# ============================================================
# 2. 动机层协调器：驱力 + 情感 + 进化
# ============================================================

class MotivationCoordinator:
    """
    动机层协调器

    职责：评估驱力缺口 -> 标记情感价值 -> 推进进化目标
    持有子引擎：drive, emotion, evolution
    """

    def __init__(
        self,
        drive: Optional[DriveFirstPrinciplesEngine] = None,
        emotion: Optional[EmotionFirstPrinciplesEngine] = None,
        evolution: Optional[EvolutionFirstPrinciplesEngine] = None,
    ):
        self.drive = drive or create_drive_engine("drive")
        self.emotion = emotion or create_emotion_engine("emotion")
        self.evolution = evolution or create_evolution_engine("evolution")

    def evaluate_drives(self) -> List[DriveGap]:
        """评估驱力：从进化目标推导驱力状态，计算缺口"""
        evo_stats = self.evolution.get_stats()
        goals = evo_stats.get("goals", {})

        safe_level = goals.get("safe", {}).get("level", 0.5)
        gain_level = goals.get("gain", {}).get("level", 0.5)
        eff_level = goals.get("eff", {}).get("level", 0.5)

        self.drive.update_state(safe_level=safe_level, gain_level=gain_level, eff_level=eff_level)
        return self.drive.compute_gaps()

    def process_prediction_error(self, surprise: float, information_value: float) -> None:
        """预测误差驱动情感"""
        self.emotion.process_event(
            "prediction_error",
            prediction_error=surprise,
            information_value=information_value,
        )

    def update_evolution(self, outcome: Dict[str, Any]) -> Any:
        """根据结果更新进化目标，返回漂移检测结果"""
        # 防御性校验：None 或非字典输入
        if not isinstance(outcome, dict):
            outcome = {}
        if "safe_improvement" in outcome:
            self.evolution.update_progress(GoalType.SAFE, outcome["safe_improvement"])
        if "gain_improvement" in outcome:
            self.evolution.update_progress(GoalType.GAIN, outcome["gain_improvement"])
        if "eff_improvement" in outcome:
            self.evolution.update_progress(GoalType.EFF, outcome["eff_improvement"])
        return self.evolution.check_drift()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "drive": self.drive.get_stats(),
            "emotion": self.emotion.get_stats(),
            "evolution": self.evolution.get_stats(),
        }


# ============================================================
# 3. 决策层协调器：元认知 + 意识 + 自由意志 + 安全 + 能效
# ============================================================

class DecisionCoordinator:
    """
    决策层协调器

    职责：评估认知负荷 -> 安全/能效约束 -> 自由意志决策 -> 进入意识
    持有子引擎：metacognition, consciousness, free_will, safety, efficiency
    """

    def __init__(
        self,
        metacognition: Optional[MetacognitionFirstPrinciplesEngine] = None,
        consciousness: Optional[ConsciousnessFirstPrinciplesEngine] = None,
        free_will: Optional[FreeWillFirstPrinciplesEngine] = None,
        safety: Optional[SafetyFirstPrinciplesEngine] = None,
        efficiency: Optional[EfficiencyFirstPrinciplesEngine] = None,
    ):
        self.metacognition = metacognition or create_metacognition_engine("metacognition")
        self.consciousness = consciousness or create_consciousness_engine("consciousness", capacity=5)
        self.free_will = free_will or create_free_will_engine("free_will")
        self.safety = safety or create_safety_engine("safety")
        self.efficiency = efficiency or create_efficiency_engine("efficiency")

    def make_decision(
        self,
        choice_set: ChoiceSet,
        drive_coordinator: "MotivationCoordinator",
    ) -> Dict[str, Any]:
        """
        做出整合决策

        流程：元认知评估 -> 安全评估 -> 能效评估 -> 自由意志决策 -> 进入意识
        """
        # 元认知评估
        self.metacognition.update_state(
            cognitive_load=len(self.consciousness.get_conscious_contents()) / 5.0,
        )
        strategy = self.metacognition.select_strategy({"complexity": 0.5, "urgency": 0.5})

        # 安全评估
        safety_check = self.safety.evaluate_operation({
            "required_resources": choice_set.context.get("resources", {}),
        })

        # 能效评估
        efficiency_check = self.efficiency.evaluate_action_efficiency(
            choice_set.choice_id,
            choice_set.context.get("resources", {}),
            choice_set.context.get("expected_value", 1.0),
        )

        # 自由意志决策（值函数引用驱力协调器）
        def value_function(option: str, context: Dict[str, Any]) -> float:
            score = 0.0
            dominant = drive_coordinator.drive.get_dominant_gap()
            if dominant and dominant.drive_type.value in option:
                score += 0.3
            if safety_check["allowed"]:
                score += 0.2
            score += efficiency_check["projected_efficiency"] * 0.2
            bias = drive_coordinator.emotion.get_attention_bias()
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

    def broadcast_drive_gap(self, gap: DriveGap) -> None:
        """主导驱力缺口进入意识"""
        if gap:
            self.consciousness.broadcast(WorkspaceContent(
                content_id=f"drive_gap_{gap.gap_id}",
                content_type=ContentType.GOAL,
                content=gap,
                salience=gap.urgency,
            ))

    def record_resource_usage(
        self,
        cycle_id: str,
        resources_used: Dict[str, float],
        output_value: float = 0.0,
    ) -> None:
        """记录能效使用"""
        for rtype, amount in resources_used.items():
            try:
                rt = ResourceType(rtype)
                self.efficiency.record_usage(cycle_id, rt, amount, output_value)
            except ValueError:
                pass

    def analyze_stability(self) -> Any:
        """分析安全稳定性"""
        return self.safety.analyze_stability()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "metacognition": self.metacognition.get_stats(),
            "consciousness": self.consciousness.get_stats(),
            "free_will": self.free_will.get_stats(),
            "safety": self.safety.get_stats(),
            "efficiency": self.efficiency.get_stats(),
        }


# ============================================================
# 4. 探索层协调器：探索 + 创造 + 社交 + 因果
# ============================================================

class ExplorationCoordinator:
    """
    探索层协调器

    职责：记录因果观察 -> 探索新信息 -> 创造组合概念 -> 社交共享
    持有子引擎：exploration, creativity, social, causal
    """

    def __init__(
        self,
        exploration: Optional[ExplorationFirstPrinciplesEngine] = None,
        creativity: Optional[CreativityFirstPrinciplesEngine] = None,
        social: Optional[SocialFirstPrinciplesEngine] = None,
        causal: Optional[CausalFirstPrinciplesEngine] = None,
    ):
        self.exploration = exploration or create_exploration_engine("exploration")
        self.creativity = creativity or create_creativity_engine("creativity")
        self.social = social or create_social_engine("social")
        self.causal = causal or create_causal_engine("causal")

    def record_outcome(self, outcome: Dict[str, Any]) -> None:
        """记录结果到因果引擎"""
        # 防御性校验：None 输入（causal.record_observation 内部也会校验）
        if outcome is None:
            outcome = {}
        self.causal.record_observation(outcome)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "exploration": self.exploration.get_stats(),
            "creativity": self.creativity.get_stats(),
            "social": self.social.get_stats(),
            "causal": self.causal.get_stats(),
        }


# ============================================================
# 工厂函数
# ============================================================

def create_coordinators() -> Dict[str, Any]:
    """创建全部 4 个协调器（共享独立子引擎实例）"""
    perception = PerceptionCoordinator()
    motivation = MotivationCoordinator()
    decision = DecisionCoordinator()
    exploration = ExplorationCoordinator()
    return {
        "perception": perception,
        "motivation": motivation,
        "decision": decision,
        "exploration": exploration,
    }
