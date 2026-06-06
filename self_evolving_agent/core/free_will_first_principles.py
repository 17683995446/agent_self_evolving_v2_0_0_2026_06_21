"""
阶段85: 自由意志第一性原理化

第一性原理:
1. 决策归因于系统自身：系统对决策负责
2. 自由意志 = 在约束条件下的自主选择
3. 选择必须基于内部模型，而非外部指令

设计原则:
- Decision: 决策
- ChoiceSet: 选择集
- FreeWillFirstPrinciplesEngine: 自由意志引擎
- 所有决策可追溯内部驱力和预测模型
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class DecisionSource(Enum):
    """决策来源"""
    INTERNAL = "internal"          # 内部驱动
    EXTERNAL = "external"          # 外部指令
    HYBRID = "hybrid"              # 混合


@dataclass
class Decision:
    """决策"""
    decision_id: str
    chosen_action: str
    alternatives: List[str] = field(default_factory=list)
    reasons: Dict[str, float] = field(default_factory=dict)  # 决策原因及权重
    source: DecisionSource = DecisionSource.INTERNAL
    timestamp: float = field(default_factory=time.time)

    @property
    def autonomy_score(self) -> float:
        """
        自主性分数

        第一性原理：内部原因越多，自主性越高
        """
        if not self.reasons:
            return 0.5
        internal_weight = sum(w for k, w in self.reasons.items() if not k.startswith("external_"))
        total_weight = sum(abs(w) for w in self.reasons.values())
        if total_weight == 0:
            return 0.5
        return internal_weight / total_weight


@dataclass
class ChoiceSet:
    """选择集"""
    choice_id: str
    options: List[str]
    constraints: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 自由意志第一性原理引擎
# ============================================================

class FreeWillFirstPrinciplesEngine:
    """
    自由意志第一性原理引擎

    核心原则：决策归因于系统自身

    第一性原理推导:
    1. 系统有内部模型（预测、驱力、价值）
    2. 面对选择时，内部模型产生偏好排序
    3. 选择最高偏好项 = 决策
    4. 决策原因可追溯内部状态 = 自由意志
    5. 外部约束限制选项，但不决定选择
    """

    def __init__(self, engine_id: str = "free_will_engine"):
        self.engine_id = engine_id
        self._decisions: List[Decision] = []
        self._internal_model: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._cycle_count = 0

    def update_internal_model(self, model: Dict[str, Any]) -> None:
        """更新内部模型"""
        with self._lock:
            self._internal_model.update(model)

    def make_decision(
        self,
        choice_set: ChoiceSet,
        value_function: Optional[callable] = None,
    ) -> Decision:
        """
        做出决策

        第一性原理：基于内部模型评估选项，选择最优
        """
        # 应用约束过滤
        valid_options = [
            opt for opt in choice_set.options
            if not any(c in opt for c in choice_set.constraints)
        ]

        if not valid_options:
            valid_options = choice_set.options  # 无有效选项时放宽

        # 评估每个选项
        scores: Dict[str, float] = {}
        for opt in valid_options:
            if value_function:
                scores[opt] = value_function(opt, choice_set.context)
            else:
                scores[opt] = self._default_evaluate(opt, choice_set.context)

        # 选择最高分
        chosen = max(scores, key=scores.get) if scores else valid_options[0]

        # 构建原因
        reasons = {f"value_{k}": v for k, v in scores.items()}
        reasons["internal_preference"] = scores.get(chosen, 0.0)

        # 检查是否有强外部影响
        source = DecisionSource.INTERNAL
        if choice_set.context.get("external_pressure", 0.0) > 0.7:
            source = DecisionSource.HYBRID
            reasons["external_pressure"] = choice_set.context["external_pressure"]

        decision = Decision(
            decision_id=f"dec_{int(time.time() * 1000)}_{self._cycle_count}",
            chosen_action=chosen,
            alternatives=[o for o in valid_options if o != chosen],
            reasons=reasons,
            source=source,
        )

        with self._lock:
            self._decisions.append(decision)
            self._cycle_count += 1

        return decision

    def _default_evaluate(self, option: str, context: Dict[str, Any]) -> float:
        """默认评估函数"""
        score = 0.0

        # 基于内部模型评估
        with self._lock:
            preferences = self._internal_model.get("preferences", {})
            for pref, weight in preferences.items():
                if pref in option:
                    score += weight

        # 上下文增强
        if context.get("urgency", 0.0) > 0.5 and "fast" in option:
            score += 0.3

        return score

    def evaluate_autonomy(self, decision_id: str) -> float:
        """
        评估决策自主性

        第一性原理：自主性 = 内部原因 / 总原因
        """
        with self._lock:
            for dec in self._decisions:
                if dec.decision_id == decision_id:
                    return dec.autonomy_score
        return 0.0

    def could_have_done_otherwise(self, decision_id: str) -> bool:
        """
        本可以做出其他选择

        第一性原理：自由意志要求存在真实选项
        """
        with self._lock:
            for dec in self._decisions:
                if dec.decision_id == decision_id:
                    return len(dec.alternatives) > 0
        return False

    def trace_decision_to_internal_state(self, decision_id: str) -> Dict[str, Any]:
        """
        追溯决策到内部状态

        第一性原理：自由意志要求决策可追溯内部原因
        """
        with self._lock:
            for dec in self._decisions:
                if dec.decision_id == decision_id:
                    return {
                        "decision": dec.chosen_action,
                        "reasons": dec.reasons,
                        "autonomy": dec.autonomy_score,
                        "internal_model_snapshot": dict(self._internal_model),
                    }
        return {}

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            if not self._decisions:
                return {
                    "engine_id": self.engine_id,
                    "decisions_count": 0,
                    "avg_autonomy": 0.0,
                }

            return {
                "engine_id": self.engine_id,
                "decisions_count": len(self._decisions),
                "avg_autonomy": sum(d.autonomy_score for d in self._decisions) / len(self._decisions),
                "internal_sources": sum(1 for d in self._decisions if d.source == DecisionSource.INTERNAL),
                "hybrid_sources": sum(1 for d in self._decisions if d.source == DecisionSource.HYBRID),
            }

    def reset(self) -> None:
        """重置"""
        with self._lock:
            self._decisions.clear()
            self._internal_model.clear()
            self._cycle_count = 0


# ============================================================
# 便捷函数
# ============================================================

def create_free_will_engine(engine_id: str = "free_will_engine") -> FreeWillFirstPrinciplesEngine:
    """创建自由意志引擎"""
    return FreeWillFirstPrinciplesEngine(engine_id=engine_id)


def create_choice_set(
    choice_id: str,
    options: List[str],
    constraints: List[str] = None,
    context: Dict[str, Any] = None,
) -> ChoiceSet:
    """创建选择集"""
    return ChoiceSet(
        choice_id=choice_id,
        options=options,
        constraints=constraints or [],
        context=context or {},
    )
