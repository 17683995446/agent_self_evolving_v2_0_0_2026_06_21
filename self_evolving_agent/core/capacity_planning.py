"""
阶段63: 容量规划接口标准化

第一性原理:
1. 资源是有限的：CPU、内存、存储、带宽都有上限
2. 需求是变化的：峰值和谷值差异巨大
3. 规划必须提前：临时扩容来不及应对突发流量

设计原则:
- CapacityPlan: 容量规划
- ResourceForecast: 资源预测
- ScalingPolicy: 扩缩容策略
- CapacityPlanner: 容量规划器
- 支持趋势预测、水位线告警、自动扩缩容建议
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class ResourceType(Enum):
    """资源类型"""
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"


class ScalingDirection(Enum):
    """扩缩容方向"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_CHANGE = "no_change"


@dataclass
class ResourceMetrics:
    """资源指标"""
    resource_type: ResourceType
    current_usage: float
    total_capacity: float
    timestamp: float = field(default_factory=time.time)

    @property
    def utilization(self) -> float:
        """利用率"""
        if self.total_capacity == 0:
            return 0.0
        return self.current_usage / self.total_capacity


@dataclass
class ScalingPolicy:
    """扩缩容策略"""
    policy_id: str
    resource_type: ResourceType
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.3
    scale_up_step: int = 2
    scale_down_step: int = 1
    cooldown_sec: float = 300.0


@dataclass
class CapacityRecommendation:
    """容量建议"""
    service_name: str
    direction: ScalingDirection
    current_replicas: int
    recommended_replicas: int
    reason: str
    confidence: float = 0.0


# ============================================================
# 容量规划器
# ============================================================

class CapacityPlanner:
    """
    容量规划器

    基于历史指标和策略生成容量建议
    """

    def __init__(self):
        self._metrics_history: Dict[str, List[ResourceMetrics]] = {}
        self._policies: Dict[str, ScalingPolicy] = {}
        self._lock = threading.Lock()

    def record_metrics(self, service_name: str, metrics: ResourceMetrics) -> None:
        """记录资源指标"""
        with self._lock:
            key = f"{service_name}_{metrics.resource_type.value}"
            if key not in self._metrics_history:
                self._metrics_history[key] = []
            self._metrics_history[key].append(metrics)
            # 保留最近100条记录
            if len(self._metrics_history[key]) > 100:
                self._metrics_history[key] = self._metrics_history[key][-100:]

    def register_policy(self, policy: ScalingPolicy) -> None:
        """注册扩缩容策略"""
        with self._lock:
            self._policies[policy.policy_id] = policy

    def evaluate(self, service_name: str, resource_type: ResourceType, current_replicas: int) -> CapacityRecommendation:
        """
        评估容量需求

        基于最近指标和策略生成扩缩容建议
        """
        with self._lock:
            key = f"{service_name}_{resource_type.value}"
            history = self._metrics_history.get(key, [])

            if not history:
                return CapacityRecommendation(
                    service_name=service_name,
                    direction=ScalingDirection.NO_CHANGE,
                    current_replicas=current_replicas,
                    recommended_replicas=current_replicas,
                    reason="no metrics available",
                )

            # 计算平均利用率
            avg_utilization = sum(m.utilization for m in history[-10:]) / min(len(history), 10)

            # 查找匹配策略
            policy = None
            for p in self._policies.values():
                if p.resource_type == resource_type:
                    policy = p
                    break

            if policy is None:
                return CapacityRecommendation(
                    service_name=service_name,
                    direction=ScalingDirection.NO_CHANGE,
                    current_replicas=current_replicas,
                    recommended_replicas=current_replicas,
                    reason="no policy found",
                )

            # 根据策略生成建议
            if avg_utilization > policy.scale_up_threshold:
                recommended = current_replicas + policy.scale_up_step
                return CapacityRecommendation(
                    service_name=service_name,
                    direction=ScalingDirection.SCALE_UP,
                    current_replicas=current_replicas,
                    recommended_replicas=recommended,
                    reason=f"avg utilization {avg_utilization:.2%} exceeds threshold {policy.scale_up_threshold:.2%}",
                    confidence=min(avg_utilization, 1.0),
                )
            elif avg_utilization < policy.scale_down_threshold:
                recommended = max(1, current_replicas - policy.scale_down_step)
                return CapacityRecommendation(
                    service_name=service_name,
                    direction=ScalingDirection.SCALE_DOWN,
                    current_replicas=current_replicas,
                    recommended_replicas=recommended,
                    reason=f"avg utilization {avg_utilization:.2%} below threshold {policy.scale_down_threshold:.2%}",
                    confidence=1.0 - avg_utilization,
                )
            else:
                return CapacityRecommendation(
                    service_name=service_name,
                    direction=ScalingDirection.NO_CHANGE,
                    current_replicas=current_replicas,
                    recommended_replicas=current_replicas,
                    reason=f"avg utilization {avg_utilization:.2%} within normal range",
                )

    def forecast(self, service_name: str, resource_type: ResourceType, horizon_hours: int = 24) -> Dict[str, Any]:
        """
        资源使用预测

        基于历史趋势进行简单线性预测
        """
        with self._lock:
            key = f"{service_name}_{resource_type.value}"
            history = self._metrics_history.get(key, [])

            if len(history) < 2:
                return {"forecast": "insufficient_data"}

            # 简单线性趋势
            recent = history[-20:]
            x = list(range(len(recent)))
            y = [m.utilization for m in recent]

            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(xi * yi for xi, yi in zip(x, y))
            sum_x2 = sum(xi ** 2 for xi in x)

            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2) if (n * sum_x2 - sum_x ** 2) != 0 else 0
            intercept = (sum_y - slope * sum_x) / n

            future_utilization = intercept + slope * (n + horizon_hours)
            future_utilization = max(0.0, min(1.0, future_utilization))

            return {
                "service_name": service_name,
                "resource_type": resource_type.value,
                "current_utilization": y[-1],
                "predicted_utilization": future_utilization,
                "trend": "increasing" if slope > 0.001 else "decreasing" if slope < -0.001 else "stable",
                "slope": slope,
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "total_metric_streams": len(self._metrics_history),
                "total_policies": len(self._policies),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_capacity_planner() -> CapacityPlanner:
    """创建容量规划器"""
    return CapacityPlanner()


def create_scaling_policy(
    policy_id: str,
    resource_type: ResourceType,
    scale_up_threshold: float = 0.8,
    scale_down_threshold: float = 0.3,
    scale_up_step: int = 2,
    scale_down_step: int = 1,
) -> ScalingPolicy:
    """创建扩缩容策略"""
    return ScalingPolicy(
        policy_id=policy_id,
        resource_type=resource_type,
        scale_up_threshold=scale_up_threshold,
        scale_down_threshold=scale_down_threshold,
        scale_up_step=scale_up_step,
        scale_down_step=scale_down_step,
    )


def create_resource_metrics(resource_type: ResourceType, current_usage: float, total_capacity: float) -> ResourceMetrics:
    """创建资源指标"""
    return ResourceMetrics(
        resource_type=resource_type,
        current_usage=current_usage,
        total_capacity=total_capacity,
    )
