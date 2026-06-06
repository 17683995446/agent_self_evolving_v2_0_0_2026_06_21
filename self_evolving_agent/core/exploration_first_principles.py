"""
阶段74: 探索第一性原理化

第一性原理:
1. 环境永远存在未知：完美知识不可能达到
2. 探索的价值源于不确定性：已知区域无需探索
3. 探索-利用权衡必须基于信息增益，而非固定比例

设计原则:
- UncertaintyEstimate: 不确定性估计
- InformationGain: 信息增益计算
- ExplorationFirstPrinciplesEngine: 探索引擎
- 探索比例 = f(不确定性)，而非固定值
"""

import threading
import time
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class ExplorationStrategy(Enum):
    """探索策略"""
    UNCERTAINTY_DRIVEN = "uncertainty_driven"   # 不确定性驱动
    INFORMATION_GAIN = "information_gain"       # 信息增益驱动
    BAYESIAN = "bayesian"                       # 贝叶斯不确定性
    THOMPSON_SAMPLING = "thompson_sampling"     # Thompson采样


@dataclass
class UncertaintyEstimate:
    """不确定性估计"""
    estimate_id: str
    domain: str                           # 领域/状态空间区域
    mean_estimate: float = 0.0            # 均值估计
    variance: float = 1.0                 # 方差（不确定性）
    sample_count: int = 0                 # 样本数
    last_updated: float = field(default_factory=time.time)

    @property
    def uncertainty(self) -> float:
        """不确定性度量：方差越大越不确定"""
        return math.sqrt(self.variance)

    @property
    def confidence(self) -> float:
        """置信度：样本越多越自信"""
        return min(1.0, self.sample_count / 100.0)


@dataclass
class InformationGain:
    """信息增益"""
    gain_id: str
    domain: str
    expected_gain: float = 0.0            # 期望信息增益
    exploration_value: float = 0.0        # 探索价值
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 探索第一性原理引擎
# ============================================================

class ExplorationFirstPrinciplesEngine:
    """
    探索第一性原理引擎

    核心原则：探索比例基于不确定性，而非固定值

    第一性原理推导:
    1. 系统对环境有信念分布（均值 + 方差）
    2. 方差 = 不确定性
    3. 不确定性高的区域值得探索
    4. 探索比例 ∝ 不确定性 / 总不确定性
    5. 随着样本增加，不确定性降低，探索自然减少
    """

    def __init__(self, engine_id: str = "exploration_engine"):
        self.engine_id = engine_id
        self._uncertainties: Dict[str, UncertaintyEstimate] = {}
        self._exploration_history: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._cycle_count = 0
        self._min_exploration_rate = 0.05   # 最小探索率（永远保持一点探索）
        self._max_exploration_rate = 0.8    # 最大探索率

    def register_domain(
        self,
        domain: str,
        initial_variance: float = 1.0,
    ) -> UncertaintyEstimate:
        """注册探索领域"""
        estimate = UncertaintyEstimate(
            estimate_id=f"unc_{domain}_{int(time.time() * 1000)}",
            domain=domain,
            variance=initial_variance,
        )
        with self._lock:
            self._uncertainties[domain] = estimate
        return estimate

    def update_observation(
        self,
        domain: str,
        observed_value: float,
        observation_variance: float = 0.1,
    ) -> Optional[UncertaintyEstimate]:
        """
        更新观测

        使用简单贝叶斯更新：
        - 新均值 = (旧均值 * 旧精度 + 观测 * 观测精度) / 总精度
        - 新方差 = 1 / 总精度
        """
        with self._lock:
            estimate = self._uncertainties.get(domain)

        if estimate is None:
            estimate = self.register_domain(domain)

        # 精度 = 1 / 方差
        prior_precision = 1.0 / max(0.001, estimate.variance)
        obs_precision = 1.0 / max(0.001, observation_variance)
        total_precision = prior_precision + obs_precision

        new_mean = (estimate.mean_estimate * prior_precision + observed_value * obs_precision) / total_precision
        new_variance = 1.0 / total_precision

        with self._lock:
            estimate.mean_estimate = new_mean
            estimate.variance = max(0.001, new_variance)  # 最小方差保护
            estimate.sample_count += 1
            estimate.last_updated = time.time()

        return estimate

    def get_exploration_rate(self, domain: Optional[str] = None) -> float:
        """
        获取探索率

        第一性原理：探索率 ∝ 不确定性 / 总不确定性
        """
        with self._lock:
            estimates = list(self._uncertainties.values())

        if not estimates:
            return self._max_exploration_rate  # 完全未知时最大探索

        if domain:
            target = self._uncertainties.get(domain)
            if target is None:
                return self._max_exploration_rate
            total_uncertainty = sum(e.uncertainty for e in estimates)
            if total_uncertainty == 0:
                return self._min_exploration_rate
            rate = target.uncertainty / total_uncertainty
        else:
            # 全局探索率：平均不确定性
            avg_uncertainty = sum(e.uncertainty for e in estimates) / len(estimates)
            rate = avg_uncertainty / (1.0 + avg_uncertainty)  # 归一化到 [0,1)

        return max(self._min_exploration_rate, min(self._max_exploration_rate, rate))

    def select_action(self, domain_options: List[str]) -> str:
        """
        选择探索领域

        第一性原理：选择不确定性最高的领域
        """
        with self._lock:
            uncertainties = {
                domain: self._uncertainties.get(domain)
                for domain in domain_options
            }

        # 未注册领域赋予最大不确定性
        max_uncertainty = -1.0
        selected = domain_options[0]
        for domain in domain_options:
            estimate = uncertainties.get(domain)
            if estimate is None:
                return domain  # 未知领域优先探索
            if estimate.uncertainty > max_uncertainty:
                max_uncertainty = estimate.uncertainty
                selected = domain

        return selected

    def should_explore(self, domain: str, threshold: Optional[float] = None) -> bool:
        """
        是否应该探索

        基于探索率和随机采样
        """
        rate = self.get_exploration_rate(domain)
        if threshold is not None:
            rate = threshold
        # 使用当前时间作为简单随机源
        import random
        return random.random() < rate

    def get_information_gain(self, domain: str) -> InformationGain:
        """
        计算期望信息增益

        信息增益 ∝ 不确定性
        """
        with self._lock:
            estimate = self._uncertainties.get(domain)

        if estimate is None:
            return InformationGain(
                gain_id=f"ig_{domain}_{int(time.time() * 1000)}",
                domain=domain,
                expected_gain=1.0,  # 完全未知时最大信息增益
                exploration_value=1.0,
            )

        # 信息增益近似为方差减少的期望
        expected_gain = estimate.variance * 0.5  # 一次观测大约减少一半方差
        exploration_value = estimate.uncertainty * (1.0 - estimate.confidence)

        return InformationGain(
            gain_id=f"ig_{domain}_{int(time.time() * 1000)}",
            domain=domain,
            expected_gain=expected_gain,
            exploration_value=exploration_value,
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            estimates = list(self._uncertainties.values())
            return {
                "engine_id": self.engine_id,
                "domains_count": len(estimates),
                "cycle_count": self._cycle_count,
                "avg_uncertainty": sum(e.uncertainty for e in estimates) / len(estimates) if estimates else 1.0,
                "global_exploration_rate": self.get_exploration_rate(),
                "domains": {e.domain: {"uncertainty": e.uncertainty, "samples": e.sample_count} for e in estimates},
            }

    def clear_history(self) -> None:
        """清除历史"""
        with self._lock:
            self._exploration_history.clear()


# ============================================================
# 便捷函数
# ============================================================

def create_exploration_engine(engine_id: str = "exploration_engine") -> ExplorationFirstPrinciplesEngine:
    """创建探索引擎"""
    return ExplorationFirstPrinciplesEngine(engine_id=engine_id)


def create_uncertainty_estimate(
    domain: str,
    mean_estimate: float = 0.0,
    variance: float = 1.0,
) -> UncertaintyEstimate:
    """创建不确定性估计"""
    return UncertaintyEstimate(
        estimate_id=f"unc_{domain}_{int(time.time() * 1000)}",
        domain=domain,
        mean_estimate=mean_estimate,
        variance=variance,
    )
