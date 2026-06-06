"""
阶段78: 能效第一性原理化

第一性原理:
1. 能量效率是生存的基础：资源有限，效率决定寿命
2. 所有资源使用必须有明确的效率目标
3. 低效行为必须被识别和优化

设计原则:
- ResourceUsage: 资源使用记录
- EfficiencyMetric: 效率指标
- EfficiencyFirstPrinciplesEngine: 能效引擎
- 追踪每单位产出的资源消耗
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
    TIME = "time"
    ENERGY = "energy"
    NETWORK = "network"
    STORAGE = "storage"


@dataclass
class ResourceUsage:
    """资源使用"""
    usage_id: str
    resource_type: ResourceType
    amount: float = 0.0                   # 使用量
    output_value: float = 0.0             # 产出价值
    timestamp: float = field(default_factory=time.time)

    @property
    def efficiency(self) -> float:
        """
        效率 = 产出 / 消耗

        第一性原理：效率衡量资源转化的有效性
        """
        if self.amount <= 0:
            return 1.0  # 无消耗 = 最高效率
        return self.output_value / self.amount


@dataclass
class EfficiencyBudget:
    """效率预算"""
    budget_id: str
    resource_type: ResourceType
    allocated: float = 0.0                # 预算分配
    consumed: float = 0.0                 # 已消耗
    minimum_efficiency: float = 0.1       # 最低效率要求

    @property
    def remaining(self) -> float:
        return max(0.0, self.allocated - self.consumed)

    @property
    def is_exhausted(self) -> bool:
        return self.consumed >= self.allocated


# ============================================================
# 能效第一性原理引擎
# ============================================================

class EfficiencyFirstPrinciplesEngine:
    """
    能效第一性原理引擎

    核心原则：所有资源使用必须有明确的效率目标

    第一性原理推导:
    1. 资源是有限的
    2. 每单位资源应产生最大价值
    3. 效率 = 价值 / 消耗
    4. 低效行为应被识别和淘汰
    5. 能效是三个无限目标之一
    """

    def __init__(self, engine_id: str = "efficiency_engine"):
        self.engine_id = engine_id
        self._usages: Dict[str, ResourceUsage] = {}
        self._budgets: Dict[str, EfficiencyBudget] = {}
        self._lock = threading.RLock()
        self._cycle_count = 0

    def record_usage(
        self,
        usage_id: str,
        resource_type: ResourceType,
        amount: float,
        output_value: float,
    ) -> ResourceUsage:
        """
        记录资源使用

        第一性原理：无记录就无法优化
        """
        usage = ResourceUsage(
            usage_id=usage_id,
            resource_type=resource_type,
            amount=amount,
            output_value=output_value,
        )

        with self._lock:
            self._usages[usage_id] = usage
            self._cycle_count += 1

            # 更新预算
            for budget in self._budgets.values():
                if budget.resource_type == resource_type:
                    budget.consumed += amount

        return usage

    def set_budget(
        self,
        budget_id: str,
        resource_type: ResourceType,
        allocated: float,
        minimum_efficiency: float = 0.1,
    ) -> EfficiencyBudget:
        """设置效率预算"""
        budget = EfficiencyBudget(
            budget_id=budget_id,
            resource_type=resource_type,
            allocated=allocated,
            minimum_efficiency=minimum_efficiency,
        )
        with self._lock:
            self._budgets[budget_id] = budget
        return budget

    def get_efficiency(self, resource_type: ResourceType) -> float:
        """
        获取某类资源的整体效率

        第一性原理：整体效率 = 总产出 / 总消耗
        """
        with self._lock:
            usages = [u for u in self._usages.values() if u.resource_type == resource_type]

        if not usages:
            return 1.0

        total_output = sum(u.output_value for u in usages)
        total_amount = sum(u.amount for u in usages)

        if total_amount <= 0:
            return 1.0

        return total_output / total_amount

    def identify_inefficiency(self, threshold: float = 0.5) -> List[ResourceUsage]:
        """
        识别低效使用

        第一性原理：低于阈值的效率需要优化
        """
        with self._lock:
            return [u for u in self._usages.values() if u.efficiency < threshold]

    def evaluate_action_efficiency(
        self,
        action_name: str,
        estimated_resources: Dict[ResourceType, float],
        expected_output: float,
    ) -> Dict[str, Any]:
        """
        评估行动的能效

        第一性原理：行动前必须评估能效
        """
        total_cost = sum(estimated_resources.values())
        projected_efficiency = expected_output / max(0.001, total_cost)

        budget_violations = []
        with self._lock:
            for budget in self._budgets.values():
                required = estimated_resources.get(budget.resource_type, 0.0)
                if budget.remaining < required:
                    budget_violations.append({
                        "budget": budget.budget_id,
                        "required": required,
                        "remaining": budget.remaining,
                    })

        return {
            "action": action_name,
            "projected_efficiency": projected_efficiency,
            "total_cost": total_cost,
            "expected_output": expected_output,
            "budget_violations": budget_violations,
            "recommended": len(budget_violations) == 0 and projected_efficiency > 0.1,
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            usages = list(self._usages.values())
            budgets = list(self._budgets.values())

            efficiencies = {}
            for rt in ResourceType:
                eff = self.get_efficiency(rt)
                if eff < 1.0 or any(u.resource_type == rt for u in usages):
                    efficiencies[rt.value] = eff

            return {
                "engine_id": self.engine_id,
                "total_usages": len(usages),
                "active_budgets": len(budgets),
                "cycle_count": self._cycle_count,
                "efficiencies_by_resource": efficiencies,
                "overall_efficiency": sum(efficiencies.values()) / len(efficiencies) if efficiencies else 1.0,
                "inefficient_count": len(self.identify_inefficiency()),
            }

    def clear(self) -> None:
        """清除记录"""
        with self._lock:
            self._usages.clear()
            self._budgets.clear()
            self._cycle_count = 0


# ============================================================
# 便捷函数
# ============================================================

def create_efficiency_engine(engine_id: str = "efficiency_engine") -> EfficiencyFirstPrinciplesEngine:
    """创建能效引擎"""
    return EfficiencyFirstPrinciplesEngine(engine_id=engine_id)


def create_resource_usage(
    usage_id: str,
    resource_type: ResourceType,
    amount: float,
    output_value: float,
) -> ResourceUsage:
    """创建资源使用记录"""
    return ResourceUsage(
        usage_id=usage_id,
        resource_type=resource_type,
        amount=amount,
        output_value=output_value,
    )
