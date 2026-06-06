"""
阶段30: 指标收集接口

第一性原理:
1. 可观测性依赖于指标。没有指标，系统的行为是不可知的黑盒
2. 指标必须标准化、可聚合、可查询
3. 指标类型决定聚合方式：计数器累加、仪表盘取最新、直方图分桶、摘要计算分位数

设计原则:
- 支持四种标准指标类型：Counter, Gauge, Histogram, Summary
- 标签维度支持多维度筛选
- 支持指标导出（Prometheus格式）
- 支持指标查询和聚合
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional, Tuple
from enum import Enum
from collections import defaultdict
from datetime import datetime
import threading
import time
import statistics


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"       # 单调递增计数器
    GAUGE = "gauge"           # 可增可减的仪表盘
    HISTOGRAM = "histogram"   # 直方图（分桶计数）
    SUMMARY = "summary"       # 摘要（计算分位数）


@dataclass
class MetricValue:
    """指标值记录"""
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)


# ============================================================
# 指标定义
# ============================================================

class Metric:
    """
    指标基类
    
    第一性原理：指标是对系统状态的量化观测，必须有明确的语义和聚合规则
    """
    
    def __init__(self, name: str, description: str, metric_type: MetricType,
                 unit: str = "", label_names: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.metric_type = metric_type
        self.unit = unit
        self.label_names = label_names or []
        self._values: Dict[Tuple[str, ...], List[MetricValue]] = defaultdict(list)
        self._lock = threading.RLock()
    
    def _key(self, labels: Dict[str, str]) -> Tuple[str, ...]:
        """将标签字典转换为元组键"""
        return tuple(str(labels.get(k, "")) for k in self.label_names)
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """记录观测值"""
        labels = labels or {}
        key = self._key(labels)
        
        with self._lock:
            self._values[key].append(MetricValue(value=value, labels=labels))
    
    def get_values(self, labels: Optional[Dict[str, str]] = None) -> List[MetricValue]:
        """获取指标值列表"""
        with self._lock:
            if labels is None:
                # 返回所有值
                all_values = []
                for vals in self._values.values():
                    all_values.extend(vals)
                return all_values
            
            key = self._key(labels)
            return self._values.get(key, [])[:]
    
    def get_latest(self, labels: Optional[Dict[str, str]] = None) -> Optional[MetricValue]:
        """获取最新值"""
        values = self.get_values(labels)
        return values[-1] if values else None
    
    def clear(self) -> None:
        """清除所有记录"""
        with self._lock:
            self._values.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "type": self.metric_type.value,
            "unit": self.unit,
            "label_names": self.label_names,
        }


class Counter(Metric):
    """
    计数器
    
    第一性原理：计数器记录事件发生的次数，只能单调递增
    """
    
    def __init__(self, name: str, description: str, unit: str = "",
                 label_names: Optional[List[str]] = None):
        super().__init__(name, description, MetricType.COUNTER, unit, label_names)
        self._totals: Dict[Tuple[str, ...], float] = defaultdict(float)
    
    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """增加计数"""
        if amount < 0:
            raise ValueError("Counter can only be incremented by non-negative values")
        
        labels = labels or {}
        key = self._key(labels)
        
        with self._lock:
            self._totals[key] += amount
            self._values[key].append(MetricValue(value=self._totals[key], labels=labels))
    
    def get_total(self, labels: Optional[Dict[str, str]] = None) -> float:
        """获取总计数"""
        if labels is None:
            with self._lock:
                return sum(self._totals.values())
        
        key = self._key(labels)
        with self._lock:
            return self._totals.get(key, 0.0)
    
    def get_rate(self, window_seconds: float = 60.0,
                 labels: Optional[Dict[str, str]] = None) -> float:
        """获取指定时间窗口内的速率"""
        values = self.get_values(labels)
        if len(values) < 2:
            return 0.0
        
        now = datetime.now()
        window_values = [
            v for v in values
            if (now - v.timestamp).total_seconds() <= window_seconds
        ]
        
        if len(window_values) < 2:
            return 0.0
        
        first = window_values[0]
        last = window_values[-1]
        duration = (last.timestamp - first.timestamp).total_seconds()
        
        if duration <= 0:
            return 0.0
        
        return (last.value - first.value) / duration


class Gauge(Metric):
    """
    仪表盘
    
    第一性原理：仪表盘记录瞬时值，可增可减
    """
    
    def __init__(self, name: str, description: str, unit: str = "",
                 label_names: Optional[List[str]] = None):
        super().__init__(name, description, MetricType.GAUGE, unit, label_names)
        self._current: Dict[Tuple[str, ...], float] = {}
    
    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """设置当前值"""
        labels = labels or {}
        key = self._key(labels)
        
        with self._lock:
            self._current[key] = value
            self._values[key].append(MetricValue(value=value, labels=labels))
    
    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """增加当前值"""
        labels = labels or {}
        key = self._key(labels)
        
        with self._lock:
            current = self._current.get(key, 0.0)
            new_value = current + amount
            self._current[key] = new_value
            self._values[key].append(MetricValue(value=new_value, labels=labels))
    
    def dec(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """减少当前值"""
        self.inc(-amount, labels)
    
    def get_current(self, labels: Optional[Dict[str, str]] = None) -> float:
        """获取当前值"""
        if labels is None:
            with self._lock:
                return sum(self._current.values())
        
        key = self._key(labels)
        with self._lock:
            return self._current.get(key, 0.0)


class Histogram(Metric):
    """
    直方图
    
    第一性原理：直方图将观测值分到预定义的桶中，用于分析分布
    """
    
    def __init__(self, name: str, description: str, unit: str = "",
                 buckets: Optional[List[float]] = None,
                 label_names: Optional[List[str]] = None):
        super().__init__(name, description, MetricType.HISTOGRAM, unit, label_names)
        # 默认桶边界：指数分布
        self.buckets = sorted(buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10])
        self._bucket_counts: Dict[Tuple[str, ...], Dict[float, int]] = defaultdict(lambda: defaultdict(int))
        self._sums: Dict[Tuple[str, ...], float] = defaultdict(float)
        self._counts: Dict[Tuple[str, ...], int] = defaultdict(int)
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """记录观测值到桶中"""
        labels = labels or {}
        key = self._key(labels)
        
        with self._lock:
            # 更新桶计数
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[key][bucket] += 1
            
            # 记录总和和计数
            self._sums[key] += value
            self._counts[key] += 1
            
            # 记录原始值
            self._values[key].append(MetricValue(value=value, labels=labels))
    
    def get_bucket_counts(self, labels: Optional[Dict[str, str]] = None) -> Dict[float, int]:
        """获取桶计数"""
        if labels is None:
            # 聚合所有标签
            with self._lock:
                result = defaultdict(int)
                for counts in self._bucket_counts.values():
                    for bucket, count in counts.items():
                        result[bucket] += count
                return dict(result)
        
        key = self._key(labels)
        with self._lock:
            return dict(self._bucket_counts.get(key, {}))
    
    def get_sum(self, labels: Optional[Dict[str, str]] = None) -> float:
        """获取总和"""
        if labels is None:
            with self._lock:
                return sum(self._sums.values())
        
        key = self._key(labels)
        with self._lock:
            return self._sums.get(key, 0.0)
    
    def get_count(self, labels: Optional[Dict[str, str]] = None) -> int:
        """获取计数"""
        if labels is None:
            with self._lock:
                return sum(self._counts.values())
        
        key = self._key(labels)
        with self._lock:
            return self._counts.get(key, 0)
    
    def get_percentile(self, percentile: float,
                       labels: Optional[Dict[str, str]] = None) -> float:
        """计算百分位数（基于桶的线性插值）"""
        values = [v.value for v in self.get_values(labels)]
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * percentile / 100.0
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_values) else f
        
        if f == c:
            return sorted_values[f]
        
        return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)


class Summary(Metric):
    """
    摘要
    
    第一性原理：摘要计算观测值的分位数，用于了解分布特征
    """
    
    def __init__(self, name: str, description: str, unit: str = "",
                 quantiles: Optional[List[float]] = None,
                 label_names: Optional[List[str]] = None,
                 max_age_seconds: float = 600.0):
        super().__init__(name, description, MetricType.SUMMARY, unit, label_names)
        self.quantiles = quantiles or [0.5, 0.9, 0.95, 0.99]
        self.max_age_seconds = max_age_seconds
        self._sums: Dict[Tuple[str, ...], float] = defaultdict(float)
        self._counts: Dict[Tuple[str, ...], int] = defaultdict(int)
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """记录观测值"""
        labels = labels or {}
        key = self._key(labels)
        
        with self._lock:
            self._sums[key] += value
            self._counts[key] += 1
            self._values[key].append(MetricValue(value=value, labels=labels))
    
    def get_quantiles(self, labels: Optional[Dict[str, str]] = None) -> Dict[float, float]:
        """计算分位数"""
        values = self.get_values(labels)
        
        # 过滤过期值
        now = datetime.now()
        valid_values = [
            v.value for v in values
            if (now - v.timestamp).total_seconds() <= self.max_age_seconds
        ]
        
        if not valid_values:
            return {q: 0.0 for q in self.quantiles}
        
        sorted_values = sorted(valid_values)
        result = {}
        
        for q in self.quantiles:
            idx = int(q * len(sorted_values))
            idx = min(idx, len(sorted_values) - 1)
            result[q] = sorted_values[idx]
        
        return result
    
    def get_sum(self, labels: Optional[Dict[str, str]] = None) -> float:
        """获取总和"""
        if labels is None:
            with self._lock:
                return sum(self._sums.values())
        
        key = self._key(labels)
        with self._lock:
            return self._sums.get(key, 0.0)
    
    def get_count(self, labels: Optional[Dict[str, str]] = None) -> int:
        """获取计数"""
        if labels is None:
            with self._lock:
                return sum(self._counts.values())
        
        key = self._key(labels)
        with self._lock:
            return self._counts.get(key, 0)
    
    def get_average(self, labels: Optional[Dict[str, str]] = None) -> float:
        """获取平均值"""
        total = self.get_sum(labels)
        count = self.get_count(labels)
        return total / count if count > 0 else 0.0


# ============================================================
# 指标注册表
# ============================================================

class MetricsRegistry:
    """指标注册表"""
    
    def __init__(self):
        self._metrics: Dict[str, Metric] = {}
        self._lock = threading.RLock()
    
    def register(self, metric: Metric) -> None:
        """注册指标"""
        with self._lock:
            if metric.name in self._metrics:
                raise ValueError(f"Metric '{metric.name}' already registered")
            self._metrics[metric.name] = metric
    
    def get(self, name: str) -> Optional[Metric]:
        """获取指标"""
        with self._lock:
            return self._metrics.get(name)
    
    def counter(self, name: str, description: str, unit: str = "",
                label_names: Optional[List[str]] = None) -> Counter:
        """创建并注册计数器"""
        counter = Counter(name, description, unit, label_names)
        self.register(counter)
        return counter
    
    def gauge(self, name: str, description: str, unit: str = "",
              label_names: Optional[List[str]] = None) -> Gauge:
        """创建并注册仪表盘"""
        gauge = Gauge(name, description, unit, label_names)
        self.register(gauge)
        return gauge
    
    def histogram(self, name: str, description: str, unit: str = "",
                  buckets: Optional[List[float]] = None,
                  label_names: Optional[List[str]] = None) -> Histogram:
        """创建并注册直方图"""
        hist = Histogram(name, description, unit, buckets, label_names)
        self.register(hist)
        return hist
    
    def summary(self, name: str, description: str, unit: str = "",
                quantiles: Optional[List[float]] = None,
                label_names: Optional[List[str]] = None) -> Summary:
        """创建并注册摘要"""
        summary = Summary(name, description, unit, quantiles, label_names)
        self.register(summary)
        return summary
    
    def list_metrics(self) -> List[Metric]:
        """列出所有指标"""
        with self._lock:
            return list(self._metrics.values())
    
    def to_prometheus_format(self) -> str:
        """导出为Prometheus格式"""
        lines = []
        
        with self._lock:
            metrics = list(self._metrics.values())
        
        for metric in metrics:
            lines.append(f"# HELP {metric.name} {metric.description}")
            lines.append(f"# TYPE {metric.name} {metric.metric_type.value}")
            
            if isinstance(metric, Counter):
                for key in metric._totals.keys():
                    labels_str = self._format_labels(metric, key)
                    lines.append(f"{metric.name}{labels_str} {metric._totals[key]}")
            
            elif isinstance(metric, Gauge):
                for key in metric._current.keys():
                    labels_str = self._format_labels(metric, key)
                    lines.append(f"{metric.name}{labels_str} {metric._current[key]}")
            
            elif isinstance(metric, Histogram):
                for key in metric._bucket_counts.keys():
                    counts = metric._bucket_counts[key]
                    labels_str = self._format_labels(metric, key)
                    for bucket in metric.buckets:
                        bucket_labels = labels_str[:-1] + f',le="{bucket}"' + "}"
                        lines.append(f"{metric.name}_bucket{bucket_labels} {counts.get(bucket, 0)}")
                    lines.append(f"{metric.name}_sum{labels_str} {metric._sums[key]}")
                    lines.append(f"{metric.name}_count{labels_str} {metric._counts[key]}")
            
            elif isinstance(metric, Summary):
                for key in metric._sums.keys():
                    labels_str = self._format_labels(metric, key)
                    lines.append(f"{metric.name}_sum{labels_str} {metric._sums[key]}")
                    lines.append(f"{metric.name}_count{labels_str} {metric._counts[key]}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_labels(self, metric: Metric, key: Tuple[str, ...]) -> str:
        """格式化标签"""
        if not metric.label_names:
            return ""
        
        pairs = []
        for i, name in enumerate(metric.label_names):
            if i < len(key):
                pairs.append(f'{name}="{key[i]}"')
        
        return "{" + ", ".join(pairs) + "}"


# ============================================================
# 便捷函数
# ============================================================

_global_registry = MetricsRegistry()


def get_metrics_registry() -> MetricsRegistry:
    """获取全局指标注册表"""
    return _global_registry


def create_counter(name: str, description: str, **kwargs) -> Counter:
    """创建计数器"""
    return _global_registry.counter(name, description, **kwargs)


def create_gauge(name: str, description: str, **kwargs) -> Gauge:
    """创建仪表盘"""
    return _global_registry.gauge(name, description, **kwargs)


def create_histogram(name: str, description: str, **kwargs) -> Histogram:
    """创建直方图"""
    return _global_registry.histogram(name, description, **kwargs)


def create_summary(name: str, description: str, **kwargs) -> Summary:
    """创建摘要"""
    return _global_registry.summary(name, description, **kwargs)
