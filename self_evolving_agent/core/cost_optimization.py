"""
阶段64: 成本优化接口标准化

第一性原理:
1. 资源是有成本的：每一点计算、存储、带宽都要花钱
2. 利用率低就是浪费：空闲资源不产生价值
3. 优化必须可量化：省了多少、花了多少必须清楚

设计原则:
- CostModel: 成本模型
- ResourceCost: 资源成本
- CostOptimizer: 成本优化器
- OptimizationStrategy: 优化策略
- 支持预留实例、按需实例、Spot实例成本对比
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class PricingModel(Enum):
    """定价模型"""
    ON_DEMAND = "on_demand"
    RESERVED = "reserved"
    SPOT = "spot"


class ResourceUnit(Enum):
    """资源单位"""
    CPU_CORE = "cpu_core"
    MEMORY_GB = "memory_gb"
    STORAGE_GB = "storage_gb"
    NETWORK_GB = "network_gb"


@dataclass
class ResourceCost:
    """资源成本"""
    resource_unit: ResourceUnit
    quantity: float
    unit_price: float
    pricing_model: PricingModel
    duration_hours: float = 1.0

    @property
    def total_cost(self) -> float:
        """总成本"""
        multiplier = {
            PricingModel.ON_DEMAND: 1.0,
            PricingModel.RESERVED: 0.6,
            PricingModel.SPOT: 0.3,
        }
        return self.quantity * self.unit_price * self.duration_hours * multiplier.get(self.pricing_model, 1.0)


@dataclass
class CostReport:
    """成本报告"""
    service_name: str
    total_cost: float
    breakdown: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 成本优化器
# ============================================================

class CostOptimizer:
    """
    成本优化器

    分析资源使用情况，生成成本优化建议
    """

    def __init__(self):
        self._costs: Dict[str, List[ResourceCost]] = {}
        self._lock = threading.Lock()

    def record_cost(self, service_name: str, cost: ResourceCost) -> None:
        """记录成本"""
        with self._lock:
            if service_name not in self._costs:
                self._costs[service_name] = []
            self._costs[service_name].append(cost)

    def analyze(self, service_name: str) -> CostReport:
        """
        分析服务成本

        生成成本报告和优化建议
        """
        with self._lock:
            costs = self._costs.get(service_name, [])

        if not costs:
            return CostReport(
                service_name=service_name,
                total_cost=0.0,
                recommendations=["no cost data available"],
            )

        total_cost = sum(c.total_cost for c in costs)

        # 按资源类型分组
        breakdown: Dict[str, float] = {}
        for cost in costs:
            key = cost.resource_unit.value
            breakdown[key] = breakdown.get(key, 0.0) + cost.total_cost

        # 生成优化建议
        recommendations = []

        # 检查是否有按需实例可以转为预留
        on_demand_cost = sum(
            c.total_cost for c in costs
            if c.pricing_model == PricingModel.ON_DEMAND
        )
        if on_demand_cost > total_cost * 0.5:
            potential_savings = on_demand_cost * 0.4
            recommendations.append(
                f"Convert on-demand to reserved instances to save {potential_savings:.2f}"
            )

        # 检查低利用率资源
        cpu_costs = [c for c in costs if c.resource_unit == ResourceUnit.CPU_CORE]
        if cpu_costs:
            avg_quantity = sum(c.quantity for c in cpu_costs) / len(cpu_costs)
            if avg_quantity < 1.0:
                recommendations.append(
                    f"Consider reducing CPU allocation (avg {avg_quantity:.2f} cores)"
                )

        return CostReport(
            service_name=service_name,
            total_cost=total_cost,
            breakdown=breakdown,
            recommendations=recommendations,
        )

    def compare_pricing_models(
        self,
        resource_unit: ResourceUnit,
        quantity: float,
        duration_hours: float,
        unit_price: float,
    ) -> Dict[PricingModel, float]:
        """
        对比不同定价模型的成本

        Returns:
            {定价模型: 总成本}
        """
        return {
            model: ResourceCost(
                resource_unit=resource_unit,
                quantity=quantity,
                unit_price=unit_price,
                pricing_model=model,
                duration_hours=duration_hours,
            ).total_cost
            for model in PricingModel
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "total_services": len(self._costs),
                "total_cost_records": sum(len(v) for v in self._costs.values()),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_cost_optimizer() -> CostOptimizer:
    """创建成本优化器"""
    return CostOptimizer()


def create_resource_cost(
    resource_unit: ResourceUnit,
    quantity: float,
    unit_price: float,
    pricing_model: PricingModel = PricingModel.ON_DEMAND,
    duration_hours: float = 1.0,
) -> ResourceCost:
    """创建资源成本"""
    return ResourceCost(
        resource_unit=resource_unit,
        quantity=quantity,
        unit_price=unit_price,
        pricing_model=pricing_model,
        duration_hours=duration_hours,
    )
