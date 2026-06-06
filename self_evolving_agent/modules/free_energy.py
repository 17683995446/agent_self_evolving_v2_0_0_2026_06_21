"""
自驱永续进化Agent系统 — 自由能计算
阶段12：自由能计算精确化

第一性原理：自由能 = 能量（预测准确度）+ 复杂度（模型代价）
F = E_q[log q(s) - log p(o,s)] = D_KL(q(s)||p(s|o)) - log p(o)

变分自由能的两种等价形式：
1. 精度形式：F = -E_q[log p(o|s)] + D_KL(q(s)||p(s))
   - 第一项：预测误差的期望（能量项）
   - 第二项：近似后验与先验的KL散度（复杂度项）

2. 信息论形式：F = 复杂度 - 准确度
   - 复杂度：模型需要多少额外信息来解释数据
   - 准确度：模型对数据的预测能力
"""

import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import deque

from ..core.interfaces import BaseModule, AgentMessage, MessageType


@dataclass
class EnergyTerm:
    """
    能量项

    数学：E_q[log p(o|s)] — 对数似然的期望
    物理意义：预测误差的期望，反映模型对观测数据的解释能力
    """
    accuracy: float           # 准确度（负的预测误差）
    log_likelihood: float     # 对数似然
    prediction_error: float   # 预测误差（MSE）

    def value(self) -> float:
        """能量项的值（越小越好）"""
        return -self.accuracy


@dataclass
class ComplexityTerm:
    """
    复杂度项

    数学：D_KL(q(s)||p(s)) — 近似后验与先验的KL散度
    物理意义：模型偏离先验假设的程度，反映模型的复杂度
    """
    kl_divergence: float      # KL散度
    parameter_count: int      # 参数数量
    effective_params: float   # 有效参数数（考虑权重衰减）

    def value(self) -> float:
        """复杂度项的值（越小越好）"""
        return self.kl_divergence


@dataclass
class FreeEnergy:
    """
    自由能

    数学：F = 能量 + 复杂度
    物理意义：模型对数据的解释成本
    """
    total: float              # 总自由能
    energy: EnergyTerm        # 能量项
    complexity: ComplexityTerm # 复杂度项
    surprise: float           # 惊奇度（不可约误差）

    def decompose(self) -> Dict[str, float]:
        """分解为可解释的分量"""
        return {
            "total": self.total,
            "energy": self.energy.value(),
            "complexity": self.complexity.value(),
            "accuracy": self.energy.accuracy,
            "prediction_error": self.energy.prediction_error,
            "kl_divergence": self.complexity.kl_divergence,
            "surprise": self.surprise,
        }


class FreeEnergyCalculator(BaseModule):
    """
    自由能计算器

    精确计算变分自由能的各个分量
    """

    def __init__(self, module_id: str = "free_energy_calculator"):
        super().__init__(module_id)
        self._history: deque = deque(maxlen=100)
        self._prior_variance = 1.0  # 先验方差
        self._likelihood_variance = 0.1  # 似然方差

    def compute_energy(self, predicted: Dict[str, float],
                       actual: Dict[str, float]) -> EnergyTerm:
        """
        计算能量项

        数学：
        - 预测误差 ε = o - g(s)
        - 对数似然 log p(o|s) = -0.5 * (ε^T * Σ^{-1} * ε + log|Σ| + d*log(2π))
        - 准确度 = E_q[log p(o|s)]

        简化计算（假设各维度独立，方差相同）：
        - accuracy = -0.5 * Σ(ε_i^2) / σ^2
        """
        errors = []
        for key in actual:
            if key in predicted:
                try:
                    pred_val = float(predicted[key])
                    act_val = float(actual[key])
                    errors.append(pred_val - act_val)
                except (ValueError, TypeError):
                    pass

        if not errors:
            return EnergyTerm(
                accuracy=0.0,
                log_likelihood=0.0,
                prediction_error=0.0,
            )

        errors = np.array(errors)
        mse = np.mean(errors ** 2)

        # 对数似然（假设高斯噪声）
        log_likelihood = -0.5 * (
            np.sum(errors ** 2) / self._likelihood_variance +
            len(errors) * np.log(2 * np.pi * self._likelihood_variance)
        )

        # 准确度（归一化到 [-1, 0] 范围）
        accuracy = -mse / (1.0 + mse)

        return EnergyTerm(
            accuracy=accuracy,
            log_likelihood=log_likelihood,
            prediction_error=mse,
        )

    def compute_complexity(self, posterior_mean: Dict[str, float],
                           posterior_var: Dict[str, float],
                           prior_mean: Dict[str, float] = None) -> ComplexityTerm:
        """
        计算复杂度项

        数学：D_KL(q(s)||p(s)) = 0.5 * [tr(Σ_p^{-1} * Σ_q) + (μ_p - μ_q)^T * Σ_p^{-1} * (μ_p - μ_q)
                                         - d + log(|Σ_p| / |Σ_q|)]

        简化计算（假设先验为 N(0, I)，后验为对角高斯）：
        - KL = 0.5 * Σ(σ_q^2 + μ_q^2 - 1 - log(σ_q^2))
        """
        if prior_mean is None:
            prior_mean = {k: 0.0 for k in posterior_mean}

        kl_terms = []
        param_count = 0

        for key in posterior_mean:
            if key in prior_mean:
                mu_q = float(posterior_mean[key])
                mu_p = float(prior_mean[key])

                # 后验方差（如果提供，否则使用默认值）
                sigma_q_sq = float(posterior_var.get(key, 0.1))
                sigma_p_sq = self._prior_variance

                # 防止数值问题
                sigma_q_sq = max(sigma_q_sq, 1e-6)

                # KL散度项
                kl_term = 0.5 * (
                    sigma_q_sq / sigma_p_sq +
                    (mu_p - mu_q) ** 2 / sigma_p_sq -
                    1.0 +
                    np.log(sigma_p_sq / sigma_q_sq)
                )
                kl_terms.append(kl_term)
                param_count += 1

        kl_divergence = np.sum(kl_terms) if kl_terms else 0.0

        # 有效参数数（考虑后验方差）
        effective_params = param_count * np.mean([
            1.0 - float(posterior_var.get(k, 0.1))
            for k in posterior_mean
        ]) if posterior_mean else 0.0

        return ComplexityTerm(
            kl_divergence=kl_divergence,
            parameter_count=param_count,
            effective_params=effective_params,
        )

    def compute(self, predicted: Dict[str, float],
                actual: Dict[str, float],
                posterior_var: Dict[str, float] = None) -> FreeEnergy:
        """
        计算总自由能

        F = -accuracy + complexity
        """
        energy = self.compute_energy(predicted, actual)

        # 使用后验均值作为预测值
        posterior_mean = predicted
        if posterior_var is None:
            posterior_var = {k: 0.1 for k in predicted}

        complexity = self.compute_complexity(posterior_mean, posterior_var)

        # 总自由能
        total = energy.value() + complexity.value()

        # 惊奇度（不可约误差，近似为能量项的残差）
        surprise = max(0.0, energy.prediction_error - complexity.kl_divergence)

        free_energy = FreeEnergy(
            total=total,
            energy=energy,
            complexity=complexity,
            surprise=surprise,
        )

        self._history.append(free_energy)
        return free_energy

    def get_average(self, window: int = 10) -> Optional[Dict[str, float]]:
        """获取最近窗口的平均自由能"""
        if len(self._history) < window:
            return None

        recent = list(self._history)[-window:]
        return {
            "mean_total": np.mean([fe.total for fe in recent]),
            "mean_energy": np.mean([fe.energy.value() for fe in recent]),
            "mean_complexity": np.mean([fe.complexity.value() for fe in recent]),
            "mean_surprise": np.mean([fe.surprise for fe in recent]),
        }

    def initialize(self, config: Dict[str, Any]) -> None:
        self._prior_variance = config.get("prior_variance", self._prior_variance)
        self._likelihood_variance = config.get("likelihood_variance", self._likelihood_variance)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.PREDICTION:
            payload = message.payload
            if "prediction" in payload:
                pred = payload["prediction"].get("predicted_state", {})
                actual = payload.get("actual", {})
                if actual:
                    fe = self.compute(pred, actual)
                    return AgentMessage(
                        msg_type=MessageType.ERROR_SIGNAL,
                        source=self.module_id,
                        payload={
                            "free_energy": fe.total,
                            "energy": fe.energy.value(),
                            "complexity": fe.complexity.value(),
                            "surprise": fe.surprise,
                            "prediction_error": fe.energy.prediction_error,
                        }
                    )
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        avg = self.get_average()
        base.update({
            "history_size": len(self._history),
            "average": avg,
            "prior_variance": self._prior_variance,
            "likelihood_variance": self._likelihood_variance,
        })
        return base
