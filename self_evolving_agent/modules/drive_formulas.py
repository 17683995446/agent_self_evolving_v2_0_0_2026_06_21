"""
自驱永续进化Agent系统 — 驱力计算数学公式
阶段14：驱力计算数学化

第一性原理：驱力是标量差距，动机只负责产生驱力，不负责选择行为

数学定义：
- 安全驱力：Safe = 1 - exp(-λ * max(0, z_score - threshold))
- 收益驱力：Gain = 1 - exp(-μ * uncertainty)
- 能效驱力：Eff = max(0, target_efficiency - actual_efficiency)

归一化：所有驱力输出严格在 [0, 1] 区间
"""

import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import deque

from ..core.interfaces import DriveEngine, DriveGaps, BaseModule, AgentMessage, MessageType


@dataclass
class DriveFormula:
    """
    驱力公式定义

    每个驱力有明确的数学公式和物理意义
    """
    name: str
    formula: str
    parameters: Dict[str, float]
    physical_meaning: str


class SafeDriveEngine(DriveEngine, BaseModule):
    """
    安全驱力引擎（数学化）

    数学公式：
    Safe = 1 - exp(-λ * max(0, z_max - z_threshold))

    其中：
    - z_max = max(|(x_i - μ_i) / σ_i|)  — 最大z-score
    - z_threshold = 异常检测阈值（默认2.0）
    - λ = 敏感度参数（默认1.0）

    物理意义：
    - z_max < z_threshold 时，Safe = 0（无安全缺口）
    - z_max 增大时，Safe 指数增长趋近于1
    """

    def __init__(self, module_id: str = "safe_drive",
                 z_threshold: float = 2.0,
                 lambda_param: float = 1.0,
                 window_size: int = 50):
        BaseModule.__init__(self, module_id)
        self.z_threshold = z_threshold
        self.lambda_param = lambda_param
        self._history: deque = deque(maxlen=window_size)
        self._formula = DriveFormula(
            name="Safe",
            formula="Safe = 1 - exp(-λ * max(0, z_max - z_threshold))",
            parameters={"z_threshold": z_threshold, "lambda": lambda_param},
            physical_meaning="异常检测：状态偏离正常范围的程度",
        )

    def compute_gaps(self, state: Dict[str, Any]) -> float:
        """
        计算安全驱力缺口

        严格遵循数学公式
        """
        # 提取数值
        values = self._extract_values(state)
        if not values:
            return 0.0

        self._history.append(values)

        if len(self._history) < 10:
            # 数据不足，返回微小缺口
            return 0.05

        # 计算历史统计量
        history_array = np.array(list(self._history))
        mean = np.mean(history_array, axis=0)
        std = np.std(history_array, axis=0)

        # 防止除零
        std = np.where(std < 1e-6, 1e-6, std)

        # 计算当前状态的z-score
        current = np.array(values)
        z_scores = np.abs((current - mean) / std)
        z_max = np.max(z_scores)

        # 应用公式：Safe = 1 - exp(-λ * max(0, z_max - z_threshold))
        excess = max(0.0, z_max - self.z_threshold)
        safe_gap = 1.0 - np.exp(-self.lambda_param * excess)

        # 确保在 [0, 1] 区间
        return float(np.clip(safe_gap, 0.0, 1.0))

    def update_targets(self, new_targets: Dict[str, float]) -> None:
        self.z_threshold = new_targets.get("z_threshold", self.z_threshold)
        self.lambda_param = new_targets.get("lambda", self.lambda_param)
        self._formula.parameters.update({
            "z_threshold": self.z_threshold,
            "lambda": self.lambda_param,
        })

    def get_formula(self) -> DriveFormula:
        """获取公式定义"""
        return self._formula

    def initialize(self, config: Dict[str, Any]) -> None:
        self.z_threshold = config.get("z_threshold", self.z_threshold)
        self.lambda_param = config.get("lambda", self.lambda_param)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.STATE_UPDATE:
            state = message.payload.get("state", {})
            gap = self.compute_gaps(state)
            return AgentMessage(
                msg_type=MessageType.DRIVE_SIGNAL,
                source=self.module_id,
                payload={
                    "drive_type": "safe",
                    "gap": gap,
                    "formula": self._formula.formula,
                }
            )
        return None

    @staticmethod
    def _extract_values(state: Dict[str, Any]) -> List[float]:
        """提取数值特征"""
        values = []
        for v in state.values():
            try:
                values.append(float(v))
            except (ValueError, TypeError):
                pass
        return values


class GainDriveEngine(DriveEngine, BaseModule):
    """
    收益驱力引擎（数学化）

    数学公式：
    Gain = 1 - exp(-μ * uncertainty)

    其中：
    - uncertainty = H(q) = -Σ p(x) log p(x)  — 信息熵
    - μ = 信息敏感度（默认2.0）

    物理意义：
    - uncertainty = 0 时，Gain = 0（已有足够信息）
    - uncertainty 增大时，Gain 指数增长趋近于1
    """

    def __init__(self, module_id: str = "gain_drive",
                 mu_param: float = 2.0,
                 target_uncertainty: float = 0.05):
        BaseModule.__init__(self, module_id)
        self.mu_param = mu_param
        self.target_uncertainty = target_uncertainty
        self._formula = DriveFormula(
            name="Gain",
            formula="Gain = 1 - exp(-μ * uncertainty)",
            parameters={"mu": mu_param, "target_uncertainty": target_uncertainty},
            physical_meaning="信息缺口：当前不确定性与目标不确定性的差距",
        )

    def compute_gaps(self, state: Dict[str, Any]) -> float:
        """
        计算收益驱力缺口

        严格遵循数学公式
        """
        # 从不确定性估计中获取
        uncertainty = state.get("uncertainty", 0.5)
        if isinstance(uncertainty, (list, dict)):
            uncertainty = np.mean(list(uncertainty.values()) if isinstance(uncertainty, dict) else uncertainty)

        uncertainty = float(uncertainty)

        # 应用公式：Gain = 1 - exp(-μ * max(0, uncertainty - target))
        excess = max(0.0, uncertainty - self.target_uncertainty)
        gain_gap = 1.0 - np.exp(-self.mu_param * excess)

        return float(np.clip(gain_gap, 0.0, 1.0))

    def update_targets(self, new_targets: Dict[str, float]) -> None:
        self.mu_param = new_targets.get("mu", self.mu_param)
        self.target_uncertainty = new_targets.get("target_uncertainty", self.target_uncertainty)
        self._formula.parameters.update({
            "mu": self.mu_param,
            "target_uncertainty": self.target_uncertainty,
        })

    def get_formula(self) -> DriveFormula:
        return self._formula

    def initialize(self, config: Dict[str, Any]) -> None:
        self.mu_param = config.get("mu", self.mu_param)
        self.target_uncertainty = config.get("target_uncertainty", self.target_uncertainty)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.STATE_UPDATE:
            state = message.payload.get("state", {})
            gap = self.compute_gaps(state)
            return AgentMessage(
                msg_type=MessageType.DRIVE_SIGNAL,
                source=self.module_id,
                payload={
                    "drive_type": "gain",
                    "gap": gap,
                    "formula": self._formula.formula,
                }
            )
        return None


class EffDriveEngine(DriveEngine, BaseModule):
    """
    能效驱力引擎（数学化）

    数学公式：
    Eff = max(0, target_efficiency - actual_efficiency)

    其中：
    - actual_efficiency = output / input  — 实际能效比
    - target_efficiency = 目标能效比（默认0.8）

    物理意义：
    - actual >= target 时，Eff = 0（能效达标）
    - actual < target 时，Eff 线性增长
    """

    def __init__(self, module_id: str = "eff_drive",
                 target_efficiency: float = 0.8):
        BaseModule.__init__(self, module_id)
        self.target_efficiency = target_efficiency
        self._formula = DriveFormula(
            name="Eff",
            formula="Eff = max(0, target_efficiency - actual_efficiency)",
            parameters={"target_efficiency": target_efficiency},
            physical_meaning="能效缺口：目标能效与实际能效的差距",
        )

    def compute_gaps(self, state: Dict[str, Any]) -> float:
        """
        计算能效驱力缺口

        严格遵循数学公式
        """
        # 计算实际能效
        cpu_usage = float(state.get("cpu_usage", 0.5))
        memory_usage = float(state.get("memory_usage", 0.5))
        task_completion = float(state.get("task_completion_rate", 0.5))

        # 能效 = 产出 / 资源消耗
        resource_input = (cpu_usage + memory_usage) / 2.0
        if resource_input < 0.01:
            resource_input = 0.01

        actual_efficiency = task_completion / (resource_input * 2.0)
        actual_efficiency = min(1.0, actual_efficiency)

        # 应用公式：Eff = max(0, target - actual)
        eff_gap = max(0.0, self.target_efficiency - actual_efficiency)

        return float(np.clip(eff_gap, 0.0, 1.0))

    def update_targets(self, new_targets: Dict[str, float]) -> None:
        self.target_efficiency = new_targets.get("target_efficiency", self.target_efficiency)
        self._formula.parameters["target_efficiency"] = self.target_efficiency

    def get_formula(self) -> DriveFormula:
        return self._formula

    def initialize(self, config: Dict[str, Any]) -> None:
        self.target_efficiency = config.get("target_efficiency", self.target_efficiency)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.STATE_UPDATE:
            state = message.payload.get("state", {})
            gap = self.compute_gaps(state)
            return AgentMessage(
                msg_type=MessageType.DRIVE_SIGNAL,
                source=self.module_id,
                payload={
                    "drive_type": "eff",
                    "gap": gap,
                    "formula": self._formula.formula,
                }
            )
        return None


class UnifiedDriveSystem(BaseModule):
    """
    统一驱力系统

    整合三个数学化的驱力引擎
    """

    def __init__(self, module_id: str = "drive_system"):
        super().__init__(module_id)
        self._safe = SafeDriveEngine()
        self._gain = GainDriveEngine()
        self._eff = EffDriveEngine()

    def compute_all_gaps(self, state: Dict[str, Any]) -> DriveGaps:
        """计算所有驱力缺口"""
        return DriveGaps(
            safe_gap=self._safe.compute_gaps(state),
            gain_gap=self._gain.compute_gaps(state),
            eff_gap=self._eff.compute_gaps(state),
        )

    def get_formulas(self) -> List[DriveFormula]:
        """获取所有驱力公式"""
        return [
            self._safe.get_formula(),
            self._gain.get_formula(),
            self._eff.get_formula(),
        ]

    def initialize(self, config: Dict[str, Any]) -> None:
        self._safe.initialize(config.get("safe", {}))
        self._gain.initialize(config.get("gain", {}))
        self._eff.initialize(config.get("eff", {}))
        self._initialized = True

    def start(self) -> None:
        self._running = True
        self._safe.start()
        self._gain.start()
        self._eff.start()

    def stop(self) -> None:
        self._running = False
        self._safe.stop()
        self._gain.stop()
        self._eff.stop()

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.STATE_UPDATE:
            state = message.payload.get("state", {})
            gaps = self.compute_all_gaps(state)
            return AgentMessage(
                msg_type=MessageType.DRIVE_SIGNAL,
                source=self.module_id,
                payload={
                    "gaps": {
                        "safe_gap": gaps.safe_gap,
                        "gain_gap": gaps.gain_gap,
                        "eff_gap": gaps.eff_gap,
                    },
                    "formulas": [
                        f.formula for f in self.get_formulas()
                    ],
                    "validated": gaps.validate(),
                }
            )
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        base.update({
            "safe": self._safe.get_state(),
            "gain": self._gain.get_state(),
            "eff": self._eff.get_state(),
        })
        return base
