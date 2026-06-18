"""
阶段86-90: 核心引擎整合
阶段97: 拆分为职责内聚的协调器（消除 God Object）

第一性原理:
1. 整体大于部分之和：整合产生涌现能力
2. 单一职责：每个协调器只负责一个领域
3. 统一接口简化使用：UnifiedFirstPrinciplesEngine 退化为容器 + 周期编排

设计原则:
- UnifiedFirstPrinciplesEngine: 统一引擎（容器 + 编排，不再包含领域逻辑）
- 4 个协调器：
  - PerceptionCoordinator  — 感知层
  - MotivationCoordinator — 动机层
  - DecisionCoordinator    — 决策层
  - ExplorationCoordinator — 探索层
- 子引擎属性保留（向后兼容）：engine.predictive_coding, engine.drive, ...
"""

import threading
from typing import Any, Dict, List, Optional

# 导入协调器
try:
    from .engine_coordinators import (
        PerceptionCoordinator,
        MotivationCoordinator,
        DecisionCoordinator,
        ExplorationCoordinator,
    )
    from .drive_first_principles import DriveGap, DriveType
    from .evolution_first_principles import GoalType
    from .efficiency_first_principles import ResourceType
    from .consciousness_first_principles import ContentType, WorkspaceContent
    from .free_will_first_principles import ChoiceSet
except ImportError:
    from engine_coordinators import (
        PerceptionCoordinator,
        MotivationCoordinator,
        DecisionCoordinator,
        ExplorationCoordinator,
    )
    from drive_first_principles import DriveGap, DriveType
    from evolution_first_principles import GoalType
    from efficiency_first_principles import ResourceType
    from consciousness_first_principles import ContentType, WorkspaceContent
    from free_will_first_principles import ChoiceSet


class UnifiedFirstPrinciplesEngine:
    """
    统一第一性原理引擎（容器 + 周期编排）

    阶段97 重构后：
    - 不再直接持有/协调 15 个子引擎的领域逻辑
    - 委托给 4 个职责内聚的协调器
    - 保留子引擎属性访问（向后兼容）

    核心循环（编排）:
    1. 感知 -> PerceptionCoordinator.perceive_and_predict
    2. 误差 -> MotivationCoordinator.process_prediction_error
    3. 驱力 -> MotivationCoordinator.evaluate_drives
    4. 决策 -> DecisionCoordinator.make_decision
    5. 学习 -> PerceptionCoordinator.store_outcome + MotivationCoordinator.update_evolution
    6. 因果 -> ExplorationCoordinator.record_outcome
    """

    def __init__(self, engine_id: str = "unified_engine"):
        self.engine_id = engine_id

        # 4 个职责内聚的协调器
        self._perception = PerceptionCoordinator()
        self._motivation = MotivationCoordinator()
        self._decision = DecisionCoordinator()
        self._exploration = ExplorationCoordinator()

        self._lock = threading.RLock()
        self._cycle_count = 0
        self._running = False

    # ============================================================
    # 向后兼容：暴露 15 个子引擎属性
    # ============================================================

    @property
    def predictive_coding(self):
        return self._perception.predictive_coding

    @property
    def learning(self):
        return self._perception.learning

    @property
    def memory(self):
        return self._perception.memory

    @property
    def drive(self):
        return self._motivation.drive

    @property
    def emotion(self):
        return self._motivation.emotion

    @property
    def evolution(self):
        return self._motivation.evolution

    @property
    def metacognition(self):
        return self._decision.metacognition

    @property
    def consciousness(self):
        return self._decision.consciousness

    @property
    def free_will(self):
        return self._decision.free_will

    @property
    def safety(self):
        return self._decision.safety

    @property
    def efficiency(self):
        return self._decision.efficiency

    @property
    def exploration(self):
        return self._exploration.exploration

    @property
    def creativity(self):
        return self._exploration.creativity

    @property
    def social(self):
        return self._exploration.social

    @property
    def causal(self):
        return self._exploration.causal

    # ============================================================
    # 协调器直接访问（推荐）
    # ============================================================

    @property
    def perception_coordinator(self) -> PerceptionCoordinator:
        return self._perception

    @property
    def motivation_coordinator(self) -> MotivationCoordinator:
        return self._motivation

    @property
    def decision_coordinator(self) -> DecisionCoordinator:
        return self._decision

    @property
    def exploration_coordinator(self) -> ExplorationCoordinator:
        return self._exploration

    # ============================================================
    # 编排方法（委托给协调器）
    # ============================================================

    def perceive_and_predict(
        self,
        module_id: str,
        current_state: Dict[str, Any],
        actual_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """感知与预测（委托给 PerceptionCoordinator）"""
        result = self._perception.perceive_and_predict(module_id, current_state, actual_state)

        # 误差驱动情感（跨协调器协作）
        error = result.get("error")
        if error:
            self._motivation.process_prediction_error(
                surprise=error.surprise,
                information_value=error.precision.value,
            )

        return result

    def evaluate_drives(self) -> List[DriveGap]:
        """评估驱力（委托给 MotivationCoordinator + DecisionCoordinator）"""
        gaps = self._motivation.evaluate_drives()

        # 主导缺口进入意识（跨协调器协作）
        dominant = self._motivation.drive.get_dominant_gap()
        self._decision.broadcast_drive_gap(dominant)

        return gaps

    def make_consolidated_decision(self, choice_set: ChoiceSet) -> Dict[str, Any]:
        """做出整合决策（委托给 DecisionCoordinator）"""
        return self._decision.make_decision(choice_set, self._motivation)

    def learn_and_evolve(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """学习与进化（委托给 Perception + Motivation + Exploration）"""
        # 因果记录
        self._exploration.record_outcome(outcome)

        # 高价值信息存入记忆
        memory_stored = self._perception.store_outcome(
            f"outcome_{self._cycle_count}",
            outcome,
            context={"error_reduction_potential": outcome.get("error_reduction", 0.0)},
        )

        # 更新进化目标
        drift = self._motivation.update_evolution(outcome)

        return {
            "memory_stored": memory_stored,
            "drift_detected": drift.value if drift else None,
        }

    def run_integration_cycle(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """运行整合周期（编排 4 个协调器）"""
        with self._lock:
            self._cycle_count += 1

        # 1. 评估驱力
        gaps = self.evaluate_drives()

        # 2. 如果有显著缺口，做出决策
        decision_result = None
        if self._motivation.drive.is_action_required():
            choices = ChoiceSet(
                choice_id=f"cycle_{self._cycle_count}",
                options=context.get("available_actions", ["wait", "explore", "exploit"]),
                context=context,
            )
            decision_result = self.make_consolidated_decision(choices)

        # 3. 学习与进化
        learn_result = self.learn_and_evolve(context.get("outcome", {}))

        # 4. 更新安全边界
        self._decision.analyze_stability()

        # 5. 记录能效
        if "resources_used" in context:
            self._decision.record_resource_usage(
                f"usage_{self._cycle_count}",
                context["resources_used"],
                context.get("output_value", 0.0),
            )

        dominant = self._motivation.drive.get_dominant_gap()
        return {
            "cycle": self._cycle_count,
            "gaps": len(gaps),
            "dominant_drive": dominant.drive_type.value if dominant else None,
            "decision": decision_result["decision"].chosen_action if decision_result else None,
            "consciousness_contents": len(self._decision.consciousness.get_conscious_contents()),
            "learn_result": learn_result,
        }

    def get_full_stats(self) -> Dict[str, Any]:
        """获取完整统计（聚合 4 个协调器）"""
        return {
            "engine_id": self.engine_id,
            "cycle_count": self._cycle_count,
            **self._perception.get_stats(),
            **self._motivation.get_stats(),
            **self._decision.get_stats(),
            **self._exploration.get_stats(),
        }


# ============================================================
# 便捷函数
# ============================================================

def create_unified_engine(engine_id: str = "unified_engine") -> UnifiedFirstPrinciplesEngine:
    """创建统一引擎"""
    return UnifiedFirstPrinciplesEngine(engine_id=engine_id)
