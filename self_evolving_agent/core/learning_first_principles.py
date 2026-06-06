"""
阶段73: 学习第一性原理化

第一性原理:
1. 减小预测误差是学习的唯一动力：没有误差就没有学习
2. 学习是参数空间的梯度下降：沿误差减小的方向更新
3. 所有参数更新必须可追溯到误差信号

设计原则:
- LearningSignal: 学习信号，必须源于误差
- ParameterUpdate: 参数更新，必须有对应的误差来源
- LearningFirstPrinciplesEngine: 学习引擎，拒绝无误差驱动的更新
- 追踪每个更新到其误差根源
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class UpdateType(Enum):
    """更新类型"""
    GRADIENT_DESCENT = "gradient_descent"    # 梯度下降
    ERROR_CORRECTION = "error_correction"    # 误差修正
    PREDICTION_UPDATE = "prediction_update"  # 预测更新
    HEURISTIC = "heuristic"                  # 启发式（必须有误差依据）


@dataclass
class LearningSignal:
    """学习信号"""
    signal_id: str
    error_magnitude: float = 0.0          # 误差幅度
    error_source: str = "unknown"         # 误差来源
    precision: float = 1.0                # 信号精度 [0,1]
    timestamp: float = field(default_factory=time.time)

    @property
    def is_valid(self) -> bool:
        """信号是否有效：必须有非零误差"""
        return self.error_magnitude > 0.0


@dataclass
class ParameterUpdate:
    """参数更新"""
    update_id: str
    parameter_name: str
    delta: float = 0.0                    # 更新量
    learning_rate: float = 0.01           # 学习率
    signal_id: str = ""                   # 关联的学习信号
    update_type: UpdateType = UpdateType.GRADIENT_DESCENT
    timestamp: float = field(default_factory=time.time)

    @property
    def update_magnitude(self) -> float:
        """更新幅度"""
        return abs(self.delta)


# ============================================================
# 学习第一性原理引擎
# ============================================================

class LearningFirstPrinciplesEngine:
    """
    学习第一性原理引擎

    核心原则：所有参数更新必须可追溯到误差信号
    拒绝任何无误差依据的更新

    第一性原理推导:
    1. 系统产生预测
    2. 预测与实际比较产生误差
    3. 误差产生学习信号
    4. 学习信号驱动参数更新
    5. 更新减小未来误差
    """

    def __init__(self, engine_id: str = "learning_engine"):
        self.engine_id = engine_id
        self._signals: Dict[str, LearningSignal] = {}
        self._updates: Dict[str, ParameterUpdate] = {}
        self._parameters: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._cycle_count = 0
        self._rejected_updates = 0

    def create_signal(
        self,
        error_magnitude: float,
        error_source: str = "unknown",
        precision: float = 1.0,
    ) -> Optional[LearningSignal]:
        """
        创建学习信号

        第一性原理：无误差 = 无信号
        """
        if error_magnitude <= 0.0:
            return None

        signal = LearningSignal(
            signal_id=f"sig_{int(time.time() * 1000)}_{self._cycle_count}",
            error_magnitude=error_magnitude,
            error_source=error_source,
            precision=max(0.0, min(1.0, precision)),
        )

        with self._lock:
            self._signals[signal.signal_id] = signal

        return signal

    def propose_update(
        self,
        parameter_name: str,
        delta: float,
        signal_id: str,
        learning_rate: float = 0.01,
        update_type: UpdateType = UpdateType.GRADIENT_DESCENT,
    ) -> Optional[ParameterUpdate]:
        """
        提议参数更新

        第一性原理：无信号 = 无更新
        如果 signal_id 无效或不存在，更新被拒绝
        """
        with self._lock:
            signal = self._signals.get(signal_id)

        if signal is None or not signal.is_valid:
            with self._lock:
                self._rejected_updates += 1
            return None

        update = ParameterUpdate(
            update_id=f"upd_{int(time.time() * 1000)}_{self._cycle_count}",
            parameter_name=parameter_name,
            delta=delta * signal.precision * learning_rate,
            learning_rate=learning_rate,
            signal_id=signal_id,
            update_type=update_type,
        )

        with self._lock:
            self._updates[update.update_id] = update
            self._cycle_count += 1

        return update

    def apply_update(self, update: ParameterUpdate) -> bool:
        """
        应用参数更新

        更新参数值，并记录更新历史
        """
        with self._lock:
            current = self._parameters.get(update.parameter_name, 0.0)
            self._parameters[update.parameter_name] = current + update.delta
            return True

    def learn_from_error(
        self,
        parameter_name: str,
        error_magnitude: float,
        delta: float,
        error_source: str = "unknown",
        learning_rate: float = 0.01,
    ) -> Optional[ParameterUpdate]:
        """
        从误差学习（一站式方法）

        第一性原理：误差 -> 信号 -> 更新
        """
        signal = self.create_signal(error_magnitude, error_source)
        if signal is None:
            return None

        update = self.propose_update(
            parameter_name=parameter_name,
            delta=delta,
            signal_id=signal.signal_id,
            learning_rate=learning_rate,
        )

        if update:
            self.apply_update(update)

        return update

    def get_parameter(self, name: str) -> float:
        """获取参数值"""
        with self._lock:
            return self._parameters.get(name, 0.0)

    def set_parameter(self, name: str, value: float) -> None:
        """
        直接设置参数（绕过误差验证）

        警告：这违反第一性原理，仅用于初始化
        """
        with self._lock:
            self._parameters[name] = value

    def trace_update_to_error(self, update_id: str) -> Optional[LearningSignal]:
        """
        追溯更新到误差信号

        第一性原理：每个更新必须有误差根源
        """
        with self._lock:
            update = self._updates.get(update_id)
            if update is None:
                return None
            return self._signals.get(update.signal_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "engine_id": self.engine_id,
                "signals_count": len(self._signals),
                "updates_count": len(self._updates),
                "parameters_count": len(self._parameters),
                "cycle_count": self._cycle_count,
                "rejected_updates": self._rejected_updates,
                "total_error_processed": sum(s.error_magnitude for s in self._signals.values()),
            }

    def clear_history(self) -> None:
        """清除历史"""
        with self._lock:
            self._signals.clear()
            self._updates.clear()
            self._rejected_updates = 0


# ============================================================
# 便捷函数
# ============================================================

def create_learning_engine(engine_id: str = "learning_engine") -> LearningFirstPrinciplesEngine:
    """创建学习引擎"""
    return LearningFirstPrinciplesEngine(engine_id=engine_id)


def create_learning_signal(
    error_magnitude: float,
    error_source: str = "unknown",
    precision: float = 1.0,
) -> Optional[LearningSignal]:
    """创建学习信号"""
    if error_magnitude <= 0.0:
        return None
    return LearningSignal(
        signal_id=f"sig_{int(time.time() * 1000)}",
        error_magnitude=error_magnitude,
        error_source=error_source,
        precision=precision,
    )


def create_parameter_update(
    parameter_name: str,
    delta: float,
    signal_id: str,
    learning_rate: float = 0.01,
) -> ParameterUpdate:
    """创建参数更新"""
    return ParameterUpdate(
        update_id=f"upd_{int(time.time() * 1000)}",
        parameter_name=parameter_name,
        delta=delta * learning_rate,
        learning_rate=learning_rate,
        signal_id=signal_id,
    )
