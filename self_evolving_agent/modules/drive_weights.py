"""
自驱永续进化Agent系统 — 动态权重自适应
阶段15：动态权重自适应

第一性原理：权重分配应反映各驱力的相对重要性
通过历史效果反馈自适应调整

数学：
- 原始权重: w_raw = [w_safe, w_gain, w_eff]
- Softmax归一化: w_i = exp(w_raw_i) / Σ exp(w_raw_j)
- 权重更新: w_raw_new = w_raw + α * (reward - baseline)
"""

import numpy as np
from typing import Dict, Any, List, Optional
from collections import deque
from dataclasses import dataclass

from ..core.interfaces import BaseModule, AgentMessage, MessageType


@dataclass
class WeightConfig:
    """权重配置"""
    safe: float = 0.33
    gain: float = 0.33
    eff: float = 0.34

    def to_array(self) -> np.ndarray:
        return np.array([self.safe, self.gain, self.eff])

    @classmethod
    def from_array(cls, arr: np.ndarray) -> "WeightConfig":
        return cls(safe=arr[0], gain=arr[1], eff=arr[2])


class DynamicWeightAdapter(BaseModule):
    """
    动态权重适配器

    根据历史表现动态调整三个驱力的权重
    """

    def __init__(self, module_id: str = "weight_adapter",
                 learning_rate: float = 0.1,
                 window_size: int = 20):
        super().__init__(module_id)
        self.lr = learning_rate
        self.window_size = window_size

        # 原始权重（未归一化）
        self._raw_weights = np.array([0.0, 0.0, 0.0])

        # 历史表现
        self._safe_history: deque = deque(maxlen=window_size)
        self._gain_history: deque = deque(maxlen=window_size)
        self._eff_history: deque = deque(maxlen=window_size)

        # 基线（平均表现）
        self._baseline = 0.0

    def compute_weights(self) -> WeightConfig:
        """
        计算当前权重

        使用softmax归一化确保权重和为1
        """
        # Softmax
        exp_weights = np.exp(self._raw_weights - np.max(self._raw_weights))
        normalized = exp_weights / np.sum(exp_weights)

        return WeightConfig.from_array(normalized)

    def update(self, drive_type: str, reward: float) -> None:
        """
        根据反馈更新权重

        Args:
            drive_type: 驱力类型 ("safe", "gain", "eff")
            reward: 反馈信号（正数表示该驱力有效）
        """
        # 记录历史
        if drive_type == "safe":
            self._safe_history.append(reward)
        elif drive_type == "gain":
            self._gain_history.append(reward)
        elif drive_type == "eff":
            self._eff_history.append(reward)

        # 更新基线
        all_rewards = list(self._safe_history) + list(self._gain_history) + list(self._eff_history)
        if all_rewards:
            self._baseline = np.mean(all_rewards)

        # 计算优势（reward - baseline）
        advantage = reward - self._baseline

        # 更新原始权重
        idx = {"safe": 0, "gain": 1, "eff": 2}[drive_type]
        self._raw_weights[idx] += self.lr * advantage

        # 防止权重过大
        self._raw_weights = np.clip(self._raw_weights, -5.0, 5.0)

    def get_weighted_gaps(self, safe_gap: float, gain_gap: float,
                          eff_gap: float) -> Dict[str, float]:
        """
        计算加权后的驱力缺口

        返回归一化后的加权缺口
        """
        weights = self.compute_weights()

        # 加权
        weighted_safe = weights.safe * safe_gap
        weighted_gain = weights.gain * gain_gap
        weighted_eff = weights.eff * eff_gap

        # 归一化到 [0, 1]
        total = weighted_safe + weighted_gain + weighted_eff
        if total > 0:
            return {
                "safe": weighted_safe / total,
                "gain": weighted_gain / total,
                "eff": weighted_eff / total,
                "weights": {
                    "safe": weights.safe,
                    "gain": weights.gain,
                    "eff": weights.eff,
                },
            }
        else:
            return {
                "safe": 0.33,
                "gain": 0.33,
                "eff": 0.34,
                "weights": {
                    "safe": weights.safe,
                    "gain": weights.gain,
                    "eff": weights.eff,
                },
            }

    def initialize(self, config: Dict[str, Any]) -> None:
        self.lr = config.get("learning_rate", self.lr)
        self.window_size = config.get("window_size", self.window_size)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.DRIVE_SIGNAL:
            # 可以在这里处理驱力反馈
            pass
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        weights = self.compute_weights()
        base.update({
            "weights": {
                "safe": weights.safe,
                "gain": weights.gain,
                "eff": weights.eff,
            },
            "raw_weights": self._raw_weights.tolist(),
            "baseline": self._baseline,
            "history_sizes": {
                "safe": len(self._safe_history),
                "gain": len(self._gain_history),
                "eff": len(self._eff_history),
            },
        })
        return base


class WeightedDriveSystem(BaseModule):
    """
    加权驱力系统

    整合驱力计算和动态权重适配
    """

    def __init__(self, module_id: str = "weighted_drive_system"):
        super().__init__(module_id)
        from .drive_formulas import UnifiedDriveSystem
        self._drive_system = UnifiedDriveSystem()
        self._weight_adapter = DynamicWeightAdapter()

    def compute_weighted_gaps(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算加权驱力缺口

        1. 计算原始驱力缺口
        2. 应用动态权重
        3. 返回加权结果
        """
        # 计算原始缺口
        gaps = self._drive_system.compute_all_gaps(state)

        # 应用权重
        weighted = self._weight_adapter.get_weighted_gaps(
            gaps.safe_gap, gaps.gain_gap, gaps.eff_gap
        )

        return {
            "raw_gaps": {
                "safe": gaps.safe_gap,
                "gain": gaps.gain_gap,
                "eff": gaps.eff_gap,
            },
            "weighted_gaps": {
                "safe": weighted["safe"],
                "gain": weighted["gain"],
                "eff": weighted["eff"],
            },
            "weights": weighted["weights"],
        }

    def update_weights(self, drive_type: str, reward: float) -> None:
        """更新权重"""
        self._weight_adapter.update(drive_type, reward)

    def initialize(self, config: Dict[str, Any]) -> None:
        self._drive_system.initialize(config.get("drive", {}))
        self._weight_adapter.initialize(config.get("weights", {}))
        self._initialized = True

    def start(self) -> None:
        self._running = True
        self._drive_system.start()
        self._weight_adapter.start()

    def stop(self) -> None:
        self._running = False
        self._drive_system.stop()
        self._weight_adapter.stop()

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.STATE_UPDATE:
            state = message.payload.get("state", {})
            result = self.compute_weighted_gaps(state)
            return AgentMessage(
                msg_type=MessageType.DRIVE_SIGNAL,
                source=self.module_id,
                payload=result
            )
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        base.update({
            "drive_system": self._drive_system.get_state(),
            "weight_adapter": self._weight_adapter.get_state(),
        })
        return base
