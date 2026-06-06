"""
阶段72: 驱力第一性原理化

第一性原理:
1. 动机源于差距：没有差距就没有行动的必要
2. 驱力是行为的唯一根源：所有行为必须服务于消除某个缺口
3. 三大驱力是生存的基础：安全、收益、能效

设计原则:
- DriveGap: 驱力缺口，行为的根源
- DriveType: 驱力类型（安全/收益/能效）
- DriveFirstPrinciplesEngine: 驱力引擎，只计算缺口，不生成任务
- 所有行为必须可追溯到某个驱力缺口
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class DriveType(Enum):
    """驱力类型"""
    SAFE = "safe"      # 安全驱力：避免危险、保持稳定
    GAIN = "gain"      # 收益驱力：获取资源、增长能力
    EFF = "eff"        # 能效驱力：节约能量、提高效率


@dataclass
class DriveGap:
    """驱力缺口"""
    gap_id: str
    drive_type: DriveType
    current_level: float = 0.0
    target_level: float = 1.0
    gap_magnitude: float = 0.0        # 缺口幅度 = target - current
    urgency: float = 0.0              # 紧急度 [0,1]
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        self.gap_magnitude = max(0.0, self.target_level - self.current_level)
        # 缺口越大越紧急，但安全驱力紧急度增长更快
        base_urgency = min(1.0, self.gap_magnitude / max(0.01, self.target_level))
        if self.drive_type == DriveType.SAFE:
            self.urgency = min(1.0, base_urgency * 1.5)  # 安全驱力更紧急
        else:
            self.urgency = base_urgency


@dataclass
class DriveState:
    """驱力状态"""
    safe_level: float = 0.5
    gain_level: float = 0.5
    eff_level: float = 0.5
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, float]:
        return {
            "safe": self.safe_level,
            "gain": self.gain_level,
            "eff": self.eff_level,
        }


# ============================================================
# 驱力第一性原理引擎
# ============================================================

class DriveFirstPrinciplesEngine:
    """
    驱力第一性原理引擎

    核心原则：只计算缺口，不生成任务
    所有行为必须可追溯到某个驱力缺口

    第一性原理推导:
    1. 系统有目标状态（安全=1, 收益=1, 能效=1）
    2. 当前状态与目标状态的差距 = 缺口
    3. 缺口产生驱力
    4. 驱力驱动行为
    5. 行为消除缺口
    """

    def __init__(self, engine_id: str = "drive_engine"):
        self.engine_id = engine_id
        self._state = DriveState()
        self._gaps: Dict[str, DriveGap] = {}
        self._gap_history: List[DriveGap] = []
        self._lock = threading.RLock()
        self._cycle_count = 0

        # 目标水平（第一性原理：无限趋近但永不达到）
        self._target_safe = 1.0
        self._target_gain = 1.0
        self._target_eff = 1.0

    def update_state(
        self,
        safe_level: Optional[float] = None,
        gain_level: Optional[float] = None,
        eff_level: Optional[float] = None,
    ) -> None:
        """更新当前驱力水平"""
        with self._lock:
            if safe_level is not None:
                self._state.safe_level = max(0.0, min(1.0, safe_level))
            if gain_level is not None:
                self._state.gain_level = max(0.0, min(1.0, gain_level))
            if eff_level is not None:
                self._state.eff_level = max(0.0, min(1.0, eff_level))
            self._state.timestamp = time.time()

    def compute_gaps(self) -> List[DriveGap]:
        """
        计算所有驱力缺口

        第一性原理：缺口 = 目标 - 当前
        """
        with self._lock:
            gaps = [
                DriveGap(
                    gap_id=f"gap_safe_{int(time.time() * 1000)}",
                    drive_type=DriveType.SAFE,
                    current_level=self._state.safe_level,
                    target_level=self._target_safe,
                ),
                DriveGap(
                    gap_id=f"gap_gain_{int(time.time() * 1000)}",
                    drive_type=DriveType.GAIN,
                    current_level=self._state.gain_level,
                    target_level=self._target_gain,
                ),
                DriveGap(
                    gap_id=f"gap_eff_{int(time.time() * 1000)}",
                    drive_type=DriveType.EFF,
                    current_level=self._state.eff_level,
                    target_level=self._target_eff,
                ),
            ]

            for gap in gaps:
                self._gaps[gap.gap_id] = gap
                self._gap_history.append(gap)

            self._cycle_count += 1
            return gaps

    def get_dominant_gap(self) -> Optional[DriveGap]:
        """
        获取主导缺口

        第一性原理：最紧急的缺口驱动当前行为
        """
        with self._lock:
            if not self._gaps:
                return None
            return max(self._gaps.values(), key=lambda g: g.urgency)

    def get_total_drive_pressure(self) -> float:
        """
        获取总驱力压力

        所有缺口幅度的加权和
        """
        with self._lock:
            gaps = list(self._gaps.values())
        if not gaps:
            return 0.0
        return sum(g.gap_magnitude * g.urgency for g in gaps)

    def is_action_required(self) -> bool:
        """
        是否需要行动

        第一性原理：有缺口就需要行动
        """
        gaps = self.compute_gaps()
        return any(g.gap_magnitude > 0.01 for g in gaps)

    def trace_action_to_gap(self, action_description: str) -> Optional[DriveGap]:
        """
        追溯行为到驱力缺口

        第一性原理：所有行为必须可追溯到某个缺口
        这是一个声明式接口，实际映射由上层实现
        """
        # 返回当前主导缺口作为默认映射
        return self.get_dominant_gap()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            gaps = list(self._gaps.values())
            return {
                "engine_id": self.engine_id,
                "state": self._state.to_dict(),
                "active_gaps": len(gaps),
                "total_gaps_history": len(self._gap_history),
                "cycle_count": self._cycle_count,
                "dominant_drive": self.get_dominant_gap().drive_type.value if gaps else None,
                "total_pressure": self.get_total_drive_pressure(),
                "action_required": self.is_action_required(),
            }

    def clear_history(self) -> None:
        """清除历史"""
        with self._lock:
            self._gap_history.clear()
            self._gaps.clear()


# ============================================================
# 便捷函数
# ============================================================

def create_drive_engine(engine_id: str = "drive_engine") -> DriveFirstPrinciplesEngine:
    """创建驱力引擎"""
    return DriveFirstPrinciplesEngine(engine_id=engine_id)


def create_drive_gap(
    gap_id: str,
    drive_type: DriveType,
    current_level: float,
    target_level: float,
) -> DriveGap:
    """创建驱力缺口"""
    return DriveGap(
        gap_id=gap_id,
        drive_type=drive_type,
        current_level=current_level,
        target_level=target_level,
    )


def create_drive_state(
    safe_level: float = 0.5,
    gain_level: float = 0.5,
    eff_level: float = 0.5,
) -> DriveState:
    """创建驱力状态"""
    return DriveState(
        safe_level=safe_level,
        gain_level=gain_level,
        eff_level=eff_level,
    )
