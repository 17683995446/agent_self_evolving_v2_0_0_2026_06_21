"""
自驱永续进化Agent系统 — 探索-利用自适应
阶段17：探索-利用自适应

第一性原理：探索-利用权衡应基于系统当前的不确定性自适应调整

数学：
- 探索率 ε = ε_min + (ε_max - ε_min) * σ(t)
- 其中 σ(t) = uncertainty(t) / max_uncertainty  — 归一化不确定性
- 温度参数 T = 1 / (1 + ln(t+1))  — 随时间降低

Boltzmann探索：
P(选择i) = exp(Q_i / T) / Σ exp(Q_j / T)
"""

import numpy as np
from typing import Dict, Any, List, Optional
from collections import deque

from ..core.interfaces import BaseModule, AgentMessage, MessageType


class AdaptiveExplorationRate(BaseModule):
    """
    自适应探索率

    根据系统不确定性动态调整探索率
    """

    def __init__(self, module_id: str = "adaptive_exploration",
                 epsilon_min: float = 0.01,
                 epsilon_max: float = 0.5,
                 adaptation_rate: float = 0.1):
        super().__init__(module_id)
        self.epsilon_min = epsilon_min
        self.epsilon_max = epsilon_max
        self.adaptation_rate = adaptation_rate

        # 历史不确定性
        self._uncertainty_history: deque = deque(maxlen=50)
        self._performance_history: deque = deque(maxlen=50)

        # 当前探索率
        self._current_epsilon = epsilon_max

    def compute_exploration_rate(self, uncertainty: float,
                                  performance: float) -> float:
        """
        计算探索率

        公式：
        ε = ε_min + (ε_max - ε_min) * σ(t)
        σ(t) = normalized_uncertainty * (1 - performance)

        不确定性高或性能低时，增加探索
        """
        self._uncertainty_history.append(uncertainty)
        self._performance_history.append(performance)

        # 归一化不确定性
        if len(self._uncertainty_history) > 1:
            mean_unc = np.mean(list(self._uncertainty_history))
            std_unc = np.std(list(self._uncertainty_history))
            if std_unc > 0:
                normalized_unc = min(1.0, uncertainty / (mean_unc + std_unc))
            else:
                normalized_unc = uncertainty
        else:
            normalized_unc = uncertainty

        # 性能因子（性能低时增加探索）
        performance_factor = max(0.0, 1.0 - performance)

        # 计算探索率
        sigma = normalized_unc * performance_factor
        epsilon = self.epsilon_min + (self.epsilon_max - self.epsilon_min) * sigma

        # 平滑更新
        self._current_epsilon += self.adaptation_rate * (epsilon - self._current_epsilon)
        self._current_epsilon = np.clip(self._current_epsilon, self.epsilon_min, self.epsilon_max)

        return float(self._current_epsilon)

    def get_temperature(self, iteration: int) -> float:
        """
        计算温度参数

        公式：T = 1 / (1 + ln(t+1))
        随时间降低，早期高探索，后期低探索
        """
        return 1.0 / (1.0 + np.log(iteration + 1))

    def boltzmann_selection(self, scores: List[float],
                            temperature: float) -> int:
        """
        Boltzmann选择

        公式：P(i) = exp(Q_i / T) / Σ exp(Q_j / T)
        """
        if temperature <= 0:
            return int(np.argmax(scores))

        # 防止数值溢出
        max_score = max(scores)
        exp_scores = [np.exp((s - max_score) / temperature) for s in scores]
        sum_exp = sum(exp_scores)

        if sum_exp == 0:
            return int(np.argmax(scores))

        probabilities = [e / sum_exp for e in exp_scores]
        return int(np.random.choice(len(scores), p=probabilities))

    def initialize(self, config: Dict[str, Any]) -> None:
        self.epsilon_min = config.get("epsilon_min", self.epsilon_min)
        self.epsilon_max = config.get("epsilon_max", self.epsilon_max)
        self.adaptation_rate = config.get("adaptation_rate", self.adaptation_rate)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.SYSTEM_EVENT:
            action = message.payload.get("action")
            if action == "get_exploration_rate":
                return AgentMessage(
                    msg_type=MessageType.SYSTEM_EVENT,
                    source=self.module_id,
                    payload={"exploration_rate": self._current_epsilon},
                )
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        base.update({
            "current_epsilon": self._current_epsilon,
            "epsilon_min": self.epsilon_min,
            "epsilon_max": self.epsilon_max,
            "uncertainty_history_size": len(self._uncertainty_history),
            "performance_history_size": len(self._performance_history),
        })
        return base


class ExplorationStrategy(BaseModule):
    """
    探索策略

    整合多种探索方法
    """

    def __init__(self, module_id: str = "exploration_strategy"):
        super().__init__(module_id)
        self._adaptive_rate = AdaptiveExplorationRate()
        self._iteration = 0

    def select_action(self, action_scores: Dict[str, float],
                      uncertainty: float = 0.5,
                      performance: float = 0.5) -> str:
        """
        选择动作

        策略：
        1. 以 ε 的概率进行探索（随机选择）
        2. 以 1-ε 的概率进行利用（选择得分最高）
        3. 利用时使用Boltzmann分布增加多样性
        """
        self._iteration += 1

        # 计算探索率
        epsilon = self._adaptive_rate.compute_exploration_rate(uncertainty, performance)

        actions = list(action_scores.keys())
        scores = list(action_scores.values())

        # 探索
        if np.random.random() < epsilon:
            return np.random.choice(actions)

        # 利用：Boltzmann选择
        temperature = self._adaptive_rate.get_temperature(self._iteration)
        selected_idx = self._adaptive_rate.boltzmann_selection(scores, temperature)
        return actions[selected_idx]

    def initialize(self, config: Dict[str, Any]) -> None:
        self._adaptive_rate.initialize(config.get("adaptive_rate", {}))
        self._initialized = True

    def start(self) -> None:
        self._running = True
        self._adaptive_rate.start()

    def stop(self) -> None:
        self._running = False
        self._adaptive_rate.stop()

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        return self._adaptive_rate.handle_message(message)

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        base.update({
            "iteration": self._iteration,
            "adaptive_rate": self._adaptive_rate.get_state(),
        })
        return base
