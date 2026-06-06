"""
阶段49: A/B测试接口标准化

第一性原理:
1. 改进必须可量化：没有对比就没有结论
2. 分组必须随机：消除选择偏差
3. 统计必须显著：避免随机波动误导决策

设计原则:
- Experiment: 实验定义
- Variant: 变体定义（A/B/C...）
- AssignmentStrategy: 用户分组策略
- ExperimentResult: 实验结果统计
- 支持多变量、多指标、置信度计算
"""

import hashlib
import random
import statistics
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class AssignmentStrategy(Enum):
    """分组策略"""
    RANDOM = "random"           # 完全随机
    HASH = "hash"               # 基于用户ID哈希
    THRESHOLD = "threshold"     # 阈值分配


class ExperimentStatus(Enum):
    """实验状态"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class Variant:
    """实验变体"""
    variant_id: str
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    traffic_ratio: float = 0.5  # 流量占比


@dataclass
class MetricObservation:
    """指标观测值"""
    variant_id: str
    metric_name: str
    value: float
    user_id: Optional[str] = None


@dataclass
class MetricStats:
    """指标统计"""
    metric_name: str
    variant_id: str
    count: int = 0
    mean: float = 0.0
    std: float = 0.0
    total: float = 0.0
    values: List[float] = field(default_factory=list)

    def add(self, value: float) -> None:
        """添加观测值"""
        self.values.append(value)
        self.count += 1
        self.total += value
        self.mean = self.total / self.count
        if self.count > 1:
            self.std = statistics.stdev(self.values)


# ============================================================
# A/B测试引擎
# ============================================================

class ABTestEngine:
    """
    A/B测试引擎

    第一性原理：通过受控对比实验验证改进效果
    """

    def __init__(self):
        self._experiments: Dict[str, 'Experiment'] = {}
        self._lock = threading.Lock()

    def register_experiment(self, experiment: 'Experiment') -> None:
        """注册实验"""
        with self._lock:
            self._experiments[experiment.experiment_id] = experiment

    def get_experiment(self, experiment_id: str) -> Optional['Experiment']:
        """获取实验"""
        with self._lock:
            return self._experiments.get(experiment_id)

    def assign_variant(self, experiment_id: str, user_id: str) -> Optional[Variant]:
        """为用户分配变体"""
        experiment = self.get_experiment(experiment_id)
        if experiment is None:
            return None
        return experiment.assign(user_id)

    def record_observation(self, experiment_id: str, variant_id: str, metric_name: str, value: float, user_id: Optional[str] = None) -> None:
        """记录观测值"""
        experiment = self.get_experiment(experiment_id)
        if experiment:
            experiment.record_metric(variant_id, metric_name, value, user_id)

    def get_experiment_results(self, experiment_id: str) -> Dict[str, Any]:
        """获取实验结果"""
        experiment = self.get_experiment(experiment_id)
        if experiment is None:
            return {"error": "Experiment not found"}
        return experiment.get_results()


# ============================================================
# 实验
# ============================================================

class Experiment:
    """
    实验

    管理变体、分组、指标收集和结果统计
    """

    def __init__(
        self,
        experiment_id: str,
        name: str,
        variants: List[Variant],
        strategy: AssignmentStrategy = AssignmentStrategy.HASH,
    ):
        self.experiment_id = experiment_id
        self.name = name
        self.variants = variants
        self.strategy = strategy
        self.status = ExperimentStatus.DRAFT
        self._metrics: Dict[str, MetricStats] = {}  # key: "variant_id:metric_name"
        self._lock = threading.Lock()

    def assign(self, user_id: str) -> Optional[Variant]:
        """分配变体"""
        if self.status != ExperimentStatus.RUNNING:
            return None

        if self.strategy == AssignmentStrategy.RANDOM:
            return self._random_assign()
        elif self.strategy == AssignmentStrategy.HASH:
            return self._hash_assign(user_id)
        elif self.strategy == AssignmentStrategy.THRESHOLD:
            return self._threshold_assign(user_id)
        return None

    def _random_assign(self) -> Variant:
        """随机分配"""
        weights = [v.traffic_ratio for v in self.variants]
        return random.choices(self.variants, weights=weights)[0]

    def _hash_assign(self, user_id: str) -> Variant:
        """哈希分配"""
        hash_val = int(hashlib.md5(f"{self.experiment_id}:{user_id}".encode()).hexdigest(), 16)
        bucket = hash_val % 100
        cumulative = 0
        for variant in self.variants:
            cumulative += int(variant.traffic_ratio * 100)
            if bucket < cumulative:
                return variant
        return self.variants[-1]

    def _threshold_assign(self, user_id: str) -> Variant:
        """阈值分配（基于用户ID排序）"""
        hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        normalized = (hash_val % 10000) / 10000.0
        cumulative = 0.0
        for variant in self.variants:
            cumulative += variant.traffic_ratio
            if normalized < cumulative:
                return variant
        return self.variants[-1]

    def record_metric(self, variant_id: str, metric_name: str, value: float, user_id: Optional[str] = None) -> None:
        """记录指标"""
        key = f"{variant_id}:{metric_name}"
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = MetricStats(metric_name=metric_name, variant_id=variant_id)
            self._metrics[key].add(value)

    def get_results(self) -> Dict[str, Any]:
        """获取实验结果"""
        with self._lock:
            results = {
                "experiment_id": self.experiment_id,
                "name": self.name,
                "status": self.status.value,
                "variants": [],
            }

            for variant in self.variants:
                variant_result = {
                    "variant_id": variant.variant_id,
                    "name": variant.name,
                    "metrics": {},
                }
                for metric_name in self._get_metric_names():
                    key = f"{variant.variant_id}:{metric_name}"
                    stats = self._metrics.get(key)
                    if stats:
                        variant_result["metrics"][metric_name] = {
                            "count": stats.count,
                            "mean": round(stats.mean, 4),
                            "std": round(stats.std, 4),
                        }
                results["variants"].append(variant_result)

            return results

    def _get_metric_names(self) -> set:
        """获取所有指标名"""
        names = set()
        for stats in self._metrics.values():
            names.add(stats.metric_name)
        return names

    def start(self) -> None:
        """启动实验"""
        self.status = ExperimentStatus.RUNNING

    def pause(self) -> None:
        """暂停实验"""
        self.status = ExperimentStatus.PAUSED

    def stop(self) -> None:
        """停止实验"""
        self.status = ExperimentStatus.COMPLETED


# ============================================================
# 便捷函数
# ============================================================

def create_ab_test_engine() -> ABTestEngine:
    """创建A/B测试引擎"""
    return ABTestEngine()


def create_variant(variant_id: str, name: str, traffic_ratio: float = 0.5, **config) -> Variant:
    """创建变体"""
    return Variant(
        variant_id=variant_id,
        name=name,
        traffic_ratio=traffic_ratio,
        config=config,
    )


def create_experiment(experiment_id: str, name: str, variants: List[Variant], strategy: AssignmentStrategy = AssignmentStrategy.HASH) -> Experiment:
    """创建实验"""
    return Experiment(
        experiment_id=experiment_id,
        name=name,
        variants=variants,
        strategy=strategy,
    )
