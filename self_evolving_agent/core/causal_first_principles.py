"""
阶段81: 因果第一性原理化

第一性原理:
1. 理解因果才能有效干预：相关不等于因果
2. 干预必须基于因果模型：否则可能适得其反
3. 反事实推理是因果理解的核心

设计原则:
- CausalLink: 因果链接
- CausalModel: 因果模型
- Intervention: 干预
- CausalFirstPrinciplesEngine: 因果引擎
- 支持因果发现、干预评估、反事实推理
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum


class CausalStrength(Enum):
    """因果强度"""
    STRONG = 1.0
    MODERATE = 0.5
    WEAK = 0.2
    UNKNOWN = 0.0


@dataclass
class CausalLink:
    """因果链接"""
    cause: str
    effect: str
    strength: CausalStrength = CausalStrength.MODERATE
    confidence: float = 0.5           # 置信度 [0,1]
    evidence_count: int = 0           # 支持证据数


@dataclass
class Intervention:
    """干预"""
    intervention_id: str
    target_variable: str
    new_value: Any
    expected_effects: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 因果第一性原理引擎
# ============================================================

class CausalFirstPrinciplesEngine:
    """
    因果第一性原理引擎

    核心原则：所有干预必须基于因果理解

    第一性原理推导:
    1. 世界由因果结构构成
    2. 观察数据只能发现相关
    3. 干预（do-operator）才能验证因果
    4. 反事实：如果当时做了X，结果会如何
    5. 有效干预需要因果模型支持
    """

    def __init__(self, engine_id: str = "causal_engine"):
        self.engine_id = engine_id
        self._links: Dict[Tuple[str, str], CausalLink] = {}
        self._interventions: List[Intervention] = []
        self._observations: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._cycle_count = 0

    def add_causal_link(
        self,
        cause: str,
        effect: str,
        strength: CausalStrength = CausalStrength.MODERATE,
        confidence: float = 0.5,
    ) -> CausalLink:
        """添加因果链接"""
        link = CausalLink(
            cause=cause,
            effect=effect,
            strength=strength,
            confidence=confidence,
        )
        with self._lock:
            self._links[(cause, effect)] = link
        return link

    def record_observation(self, variables: Dict[str, Any]) -> None:
        """记录观测"""
        with self._lock:
            self._observations.append({
                "timestamp": time.time(),
                "variables": dict(variables),
            })
            self._cycle_count += 1

    def discover_causal_links(self, min_correlation: float = 0.5) -> List[CausalLink]:
        """
        从观测中发现因果候选

        第一性原理：相关性是因果的必要条件（非充分）
        """
        discovered = []
        with self._lock:
            if len(self._observations) < 2:
                return discovered

            # 简单相关性分析
            vars_history: Dict[str, List[Any]] = {}
            for obs in self._observations:
                for var, val in obs["variables"].items():
                    if var not in vars_history:
                        vars_history[var] = []
                    try:
                        vars_history[var].append(float(val))
                    except (TypeError, ValueError):
                        pass

            var_names = list(vars_history.keys())
            for i, v1 in enumerate(var_names):
                for v2 in var_names[i+1:]:
                    vals1 = vars_history[v1]
                    vals2 = vars_history[v2]
                    if len(vals1) < 2 or len(vals2) < 2:
                        continue

                    # 简单协方差
                    mean1 = sum(vals1) / len(vals1)
                    mean2 = sum(vals2) / len(vals2)
                    cov = sum((a - mean1) * (b - mean2) for a, b in zip(vals1, vals2)) / len(vals1)
                    var1 = sum((a - mean1) ** 2 for a in vals1) / len(vals1)
                    var2 = sum((b - mean2) ** 2 for b in vals2) / len(vals2)

                    if var1 > 0 and var2 > 0:
                        corr = abs(cov / (var1 ** 0.5 * var2 ** 0.5))
                        if corr >= min_correlation:
                            # 假设时间先后决定因果方向（简化）
                            link = CausalLink(
                                cause=v1,
                                effect=v2,
                                strength=CausalStrength.MODERATE if corr > 0.7 else CausalStrength.WEAK,
                                confidence=corr,
                                evidence_count=len(vals1),
                            )
                            self._links[(v1, v2)] = link
                            discovered.append(link)

        return discovered

    def predict_effect(self, cause: str, cause_value: float) -> Dict[str, Any]:
        """
        预测干预效果

        第一性原理：基于因果模型预测do(cause=value)的效果
        """
        effects = {}
        with self._lock:
            for (c, e), link in self._links.items():
                if c == cause:
                    predicted_change = cause_value * link.strength.value * link.confidence
                    effects[e] = {
                        "predicted_change": predicted_change,
                        "strength": link.strength.value,
                        "confidence": link.confidence,
                    }
        return effects

    def evaluate_intervention(self, intervention: Intervention) -> Dict[str, Any]:
        """
        评估干预

        第一性原理：干预前必须评估因果后果
        """
        effects = self.predict_effect(intervention.target_variable, float(intervention.new_value))

        # 检查是否有未预料的副作用
        unanticipated = []
        for effect_var in effects:
            if effect_var not in intervention.expected_effects:
                unanticipated.append(effect_var)

        return {
            "intervention": intervention.intervention_id,
            "predicted_effects": effects,
            "unanticipated_effects": unanticipated,
            "risk_score": len(unanticipated) * 0.2,
            "recommended": len(unanticipated) == 0,
        }

    def counterfactual(self, variable: str, hypothetical_value: Any) -> Dict[str, Any]:
        """
        反事实推理

        第一性原理：如果当时做了不同选择，结果会如何
        """
        # 简化实现：基于因果链接预测差异
        current_effects = self.predict_effect(variable, 1.0)
        hypothetical_effects = self.predict_effect(variable, float(hypothetical_value))

        differences = {}
        all_vars = set(current_effects.keys()) | set(hypothetical_effects.keys())
        for v in all_vars:
            curr = current_effects.get(v, {}).get("predicted_change", 0)
            hypo = hypothetical_effects.get(v, {}).get("predicted_change", 0)
            differences[v] = hypo - curr

        return {
            "variable": variable,
            "hypothetical_value": hypothetical_value,
            "differences": differences,
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "engine_id": self.engine_id,
                "causal_links": len(self._links),
                "interventions": len(self._interventions),
                "observations": len(self._observations),
                "cycle_count": self._cycle_count,
            }

    def clear(self) -> None:
        """清除"""
        with self._lock:
            self._links.clear()
            self._interventions.clear()
            self._observations.clear()
            self._cycle_count = 0


# ============================================================
# 便捷函数
# ============================================================

def create_causal_engine(engine_id: str = "causal_engine") -> CausalFirstPrinciplesEngine:
    """创建因果引擎"""
    return CausalFirstPrinciplesEngine(engine_id=engine_id)


def create_intervention(
    intervention_id: str,
    target_variable: str,
    new_value: Any,
) -> Intervention:
    """创建干预"""
    return Intervention(
        intervention_id=intervention_id,
        target_variable=target_variable,
        new_value=new_value,
    )
