"""
阶段77: 安全第一性原理化

第一性原理:
1. 系统稳定性是进化的前提：没有稳定就没有持续
2. 安全约束必须可追溯到资源或行为边界
3. 硬性约束应改为基于稳定性分析的动态约束

设计原则:
- SafetyBoundary: 安全边界
- StabilityAnalysis: 稳定性分析
- SafetyFirstPrinciplesEngine: 安全引擎
- 动态约束基于实时稳定性评估
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class BoundaryType(Enum):
    """边界类型"""
    RESOURCE = "resource"      # 资源边界（内存、CPU等）
    BEHAVIOR = "behavior"      # 行为边界（操作限制）
    RATE = "rate"              # 速率边界（频率限制）
    SCOPE = "scope"            # 范围边界（权限限制）


class RiskLevel(Enum):
    """风险级别"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SafetyBoundary:
    """安全边界"""
    boundary_id: str
    boundary_type: BoundaryType
    metric_name: str
    current_value: float = 0.0
    threshold: float = 1.0
    dynamic_margin: float = 0.1           # 动态余量
    timestamp: float = field(default_factory=time.time)

    @property
    def effective_threshold(self) -> float:
        """有效阈值 = 阈值 * (1 - 动态余量)"""
        return self.threshold * (1.0 - self.dynamic_margin)

    @property
    def utilization(self) -> float:
        """利用率"""
        if self.threshold == 0:
            return 1.0
        return self.current_value / self.threshold

    @property
    def risk_level(self) -> RiskLevel:
        """风险级别"""
        u = self.utilization
        if u >= 1.0:
            return RiskLevel.CRITICAL
        elif u >= 0.9:
            return RiskLevel.HIGH
        elif u >= 0.7:
            return RiskLevel.MEDIUM
        elif u >= 0.5:
            return RiskLevel.LOW
        return RiskLevel.NONE


@dataclass
class StabilityReport:
    """稳定性报告"""
    report_id: str
    overall_stability: float = 1.0        # 整体稳定性 [0,1]
    risk_count: int = 0
    critical_boundaries: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 安全第一性原理引擎
# ============================================================

class SafetyFirstPrinciplesEngine:
    """
    安全第一性原理引擎

    核心原则：安全约束基于稳定性分析，而非固定阈值

    第一性原理推导:
    1. 系统有多个资源/行为维度
    2. 每个维度有物理或逻辑上限
    3. 接近上限 = 不稳定
    4. 动态余量根据系统负载调整
    5. 任何操作必须通过稳定性评估
    """

    def __init__(self, engine_id: str = "safety_engine"):
        self.engine_id = engine_id
        self._boundaries: Dict[str, SafetyBoundary] = {}
        self._history: List[StabilityReport] = []
        self._lock = threading.RLock()
        self._cycle_count = 0

    def register_boundary(
        self,
        boundary_id: str,
        boundary_type: BoundaryType,
        metric_name: str,
        threshold: float,
        initial_margin: float = 0.1,
    ) -> SafetyBoundary:
        """注册安全边界"""
        boundary = SafetyBoundary(
            boundary_id=boundary_id,
            boundary_type=boundary_type,
            metric_name=metric_name,
            threshold=threshold,
            dynamic_margin=initial_margin,
        )
        with self._lock:
            self._boundaries[boundary_id] = boundary
        return boundary

    def update_metric(self, boundary_id: str, current_value: float) -> Optional[SafetyBoundary]:
        """更新指标值"""
        with self._lock:
            boundary = self._boundaries.get(boundary_id)
            if boundary is None:
                return None
            boundary.current_value = current_value
            boundary.timestamp = time.time()
            return boundary

    def evaluate_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估操作安全性

        第一性原理：操作必须不破坏系统稳定性
        """
        # 防御性校验：None 或非字典输入
        if not isinstance(operation, dict):
            return {
                "allowed": False,
                "risk_score": 1.0,
                "violations": [{"error": "invalid_operation", "reason": f"expected dict, got {type(operation).__name__}"}],
            }
        required_resources = operation.get("required_resources", {}) or {}
        if not isinstance(required_resources, dict):
            required_resources = {}
        risk_score = 0.0
        violations = []

        with self._lock:
            for resource, amount in required_resources.items():
                for boundary in self._boundaries.values():
                    if boundary.metric_name == resource:
                        projected = boundary.current_value + amount
                        if projected > boundary.effective_threshold:
                            risk_score += 1.0
                            violations.append({
                                "boundary": boundary.boundary_id,
                                "projected": projected,
                                "threshold": boundary.effective_threshold,
                            })
                        elif projected > boundary.threshold * 0.8:
                            risk_score += 0.5

        return {
            "allowed": len(violations) == 0,
            "risk_score": risk_score,
            "violations": violations,
        }

    def analyze_stability(self) -> StabilityReport:
        """
        分析系统稳定性

        第一性原理：稳定性 = 所有边界利用率的补集
        """
        with self._lock:
            boundaries = list(self._boundaries.values())

        if not boundaries:
            return StabilityReport(report_id=f"stab_{int(time.time() * 1000)}")

        utilizations = [b.utilization for b in boundaries]
        avg_util = sum(utilizations) / len(utilizations)
        max_util = max(utilizations)

        # 稳定性：利用率越低越稳定
        stability = max(0.0, 1.0 - max_util)

        critical = [b.boundary_id for b in boundaries if b.risk_level == RiskLevel.CRITICAL]
        high_risk = [b.boundary_id for b in boundaries if b.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)]

        report = StabilityReport(
            report_id=f"stab_{int(time.time() * 1000)}",
            overall_stability=stability,
            risk_count=len(high_risk),
            critical_boundaries=critical,
        )

        with self._lock:
            self._history.append(report)
            self._cycle_count += 1

        return report

    def adjust_margins(self, target_stability: float = 0.8) -> None:
        """
        动态调整安全余量

        第一性原理：不稳定时增加余量，稳定时可放宽
        """
        report = self.analyze_stability()

        with self._lock:
            for boundary in self._boundaries.values():
                if report.overall_stability < target_stability:
                    # 不稳定，增加余量
                    boundary.dynamic_margin = min(0.5, boundary.dynamic_margin + 0.05)
                else:
                    # 稳定，可稍微放宽
                    boundary.dynamic_margin = max(0.05, boundary.dynamic_margin - 0.01)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            boundaries = list(self._boundaries.values())
            report = self.analyze_stability()
            return {
                "engine_id": self.engine_id,
                "boundaries_count": len(boundaries),
                "cycle_count": self._cycle_count,
                "overall_stability": report.overall_stability,
                "risk_count": report.risk_count,
                "critical_count": len(report.critical_boundaries),
                "boundary_status": {
                    b.boundary_id: {
                        "utilization": b.utilization,
                        "risk": b.risk_level.name,
                        "margin": b.dynamic_margin,
                    }
                    for b in boundaries
                },
            }

    def reset(self) -> None:
        """重置"""
        with self._lock:
            self._boundaries.clear()
            self._history.clear()
            self._cycle_count = 0


# ============================================================
# 便捷函数
# ============================================================

def create_safety_engine(engine_id: str = "safety_engine") -> SafetyFirstPrinciplesEngine:
    """创建安全引擎"""
    return SafetyFirstPrinciplesEngine(engine_id=engine_id)


def create_safety_boundary(
    boundary_id: str,
    boundary_type: BoundaryType,
    metric_name: str,
    threshold: float,
) -> SafetyBoundary:
    """创建安全边界"""
    return SafetyBoundary(
        boundary_id=boundary_id,
        boundary_type=boundary_type,
        metric_name=metric_name,
        threshold=threshold,
    )
