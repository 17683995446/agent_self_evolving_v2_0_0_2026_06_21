"""
自驱永续进化Agent系统 — 驱力引擎
阶段5：驱力系统模块化

第一性原理：动机只负责产生驱力，不负责选择行为
- 安全驱力：检测异常，量化风险
- 收益驱力：评估信息增益
- 能效驱力：衡量资源效率
"""

import numpy as np
from typing import Dict, Any, Optional
from collections import deque

from ..core.interfaces import (
    DriveEngine, DriveGaps, BaseModule, AgentMessage, MessageType
)


class SafeDriveCalculator(DriveEngine, BaseModule):
    """
    安全驱力计算器

    第一性原理：安全 = 1 - 风险
    风险 = 异常程度 × 影响范围
    """

    def __init__(self, module_id: str = "safe_drive"):
        BaseModule.__init__(self, module_id)
        self._target_safety = 0.95
        self._history_buffer: deque = deque(maxlen=100)
        self._anomaly_threshold = 2.0  # 标准差倍数

    def compute_gaps(self, state: Dict[str, Any]) -> float:
        """
        计算安全驱力缺口

        Returns:
            float: 安全缺口 [0, 1]，值越大越不安全
        """
        # 提取数值型状态
        values = self._extract_numeric_values(state)
        if not values:
            return 0.0

        self._history_buffer.append(values)

        if len(self._history_buffer) < 10:
            # 数据不足，假设安全
            return max(0.0, self._target_safety - 0.9)

        # 计算历史均值和标准差
        history_array = np.array(list(self._history_buffer))
        mean = np.mean(history_array, axis=0)
        std = np.std(history_array, axis=0)

        # 避免除零
        std = np.where(std == 0, 1e-6, std)

        # 计算当前状态的z-score（异常程度）
        current = np.array(values)
        z_scores = np.abs((current - mean) / std)

        # 最大异常程度
        max_anomaly = np.max(z_scores)

        # 异常程度超过阈值则产生安全缺口
        if max_anomaly > self._anomaly_threshold:
            # 缺口与异常程度成正比
            gap = min(1.0, (max_anomaly - self._anomaly_threshold) / self._anomaly_threshold)
        else:
            gap = 0.0

        return gap

    def update_targets(self, new_targets: Dict[str, float]) -> None:
        self._target_safety = new_targets.get("safety", self._target_safety)
        self._anomaly_threshold = new_targets.get("threshold", self._anomaly_threshold)

    def initialize(self, config: Dict[str, Any]) -> None:
        self._target_safety = config.get("target_safety", self._target_safety)
        self._anomaly_threshold = config.get("anomaly_threshold", self._anomaly_threshold)
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
                }
            )
        return None

    @staticmethod
    def _extract_numeric_values(state: Dict[str, Any]) -> list:
        """从状态中提取数值"""
        values = []
        for v in state.values():
            try:
                values.append(float(v))
            except (ValueError, TypeError):
                pass
        return values


class GainDriveCalculator(DriveEngine, BaseModule):
    """
    收益驱力计算器

    第一性原理：收益 = 信息增益 = 减少的不确定性
    缺口 = 当前不确定性 - 目标不确定性
    """

    def __init__(self, module_id: str = "gain_drive"):
        BaseModule.__init__(self, module_id)
        self._target_uncertainty = 0.1
        self._uncertainty_history: deque = deque(maxlen=50)

    def compute_gaps(self, state: Dict[str, Any]) -> float:
        """
        计算收益驱力缺口

        基于预测不确定性的信息论度量
        """
        # 从状态中获取不确定性（如果提供）
        uncertainty = state.get("uncertainty", 0.5)
        if isinstance(uncertainty, (list, dict)):
            uncertainty = np.mean(list(uncertainty.values()) if isinstance(uncertainty, dict) else uncertainty)

        self._uncertainty_history.append(uncertainty)

        # 缺口 = 当前不确定性 - 目标不确定性
        gap = max(0.0, uncertainty - self._target_uncertainty)

        # 归一化到 [0, 1]
        return min(1.0, gap / (1.0 - self._target_uncertainty))

    def update_targets(self, new_targets: Dict[str, float]) -> None:
        self._target_uncertainty = new_targets.get("uncertainty", self._target_uncertainty)

    def initialize(self, config: Dict[str, Any]) -> None:
        self._target_uncertainty = config.get("target_uncertainty", self._target_uncertainty)
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
                }
            )
        return None


class EffDriveCalculator(DriveEngine, BaseModule):
    """
    能效驱力计算器

    第一性原理：能效 = 产出 / 消耗
    缺口 = 目标能效 - 当前能效
    """

    def __init__(self, module_id: str = "eff_drive"):
        BaseModule.__init__(self, module_id)
        self._target_efficiency = 0.8
        self._resource_history: deque = deque(maxlen=50)

    def compute_gaps(self, state: Dict[str, Any]) -> float:
        """
        计算能效驱力缺口

        基于资源使用效率
        """
        # 从状态中获取资源使用信息
        cpu_usage = state.get("cpu_usage", 0.5)
        memory_usage = state.get("memory_usage", 0.5)
        task_completion_rate = state.get("task_completion_rate", 0.5)

        # 能效 = 任务完成率 / 资源消耗
        resource_consumption = (cpu_usage + memory_usage) / 2.0
        if resource_consumption < 0.01:
            resource_consumption = 0.01

        efficiency = task_completion_rate / (resource_consumption * 2.0)
        efficiency = min(1.0, efficiency)

        self._resource_history.append(efficiency)

        # 缺口 = 目标 - 当前
        gap = max(0.0, self._target_efficiency - efficiency)

        return gap

    def update_targets(self, new_targets: Dict[str, float]) -> None:
        self._target_efficiency = new_targets.get("efficiency", self._target_efficiency)

    def initialize(self, config: Dict[str, Any]) -> None:
        self._target_efficiency = config.get("target_efficiency", self._target_efficiency)
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
                }
            )
        return None


class UnifiedDriveEngine(BaseModule):
    """
    统一驱力引擎

    协调三个驱力计算器，输出标准的DriveGaps
    """

    def __init__(self, module_id: str = "drive_engine"):
        super().__init__(module_id)
        self._safe_drive = SafeDriveCalculator()
        self._gain_drive = GainDriveCalculator()
        self._eff_drive = EffDriveCalculator()

    def compute_all_gaps(self, state: Dict[str, Any]) -> DriveGaps:
        """计算所有驱力缺口"""
        return DriveGaps(
            safe_gap=self._safe_drive.compute_gaps(state),
            gain_gap=self._gain_drive.compute_gaps(state),
            eff_gap=self._eff_drive.compute_gaps(state),
        )

    def initialize(self, config: Dict[str, Any]) -> None:
        self._safe_drive.initialize(config.get("safe", {}))
        self._gain_drive.initialize(config.get("gain", {}))
        self._eff_drive.initialize(config.get("eff", {}))
        self._initialized = True

    def start(self) -> None:
        self._running = True
        self._safe_drive.start()
        self._gain_drive.start()
        self._eff_drive.start()

    def stop(self) -> None:
        self._running = False
        self._safe_drive.stop()
        self._gain_drive.stop()
        self._eff_drive.stop()

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
                    "validated": gaps.validate(),
                }
            )
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        base.update({
            "safe_drive": self._safe_drive.get_state(),
            "gain_drive": self._gain_drive.get_state(),
            "eff_drive": self._eff_drive.get_state(),
        })
        return base
