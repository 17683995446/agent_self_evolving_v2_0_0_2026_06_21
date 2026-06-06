"""
阶段66: 性能剖析接口标准化

第一性原理:
1. 性能瓶颈是客观存在的：任何系统都有最慢的部分
2. 测量是优化的前提：不知道慢在哪里就无法优化
3. 剖析必须低开销：测量工具不能显著影响被测系统

设计原则:
- ProfileSample: 性能样本
- Profiler: 剖析器接口
- ProfileReport: 剖析报告
- 支持CPU剖析、内存剖析、调用链分析
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class ProfileType(Enum):
    """剖析类型"""
    CPU = "cpu"
    MEMORY = "memory"
    LATENCY = "latency"
    CALL_GRAPH = "call_graph"


@dataclass
class ProfileSample:
    """性能样本"""
    sample_id: str
    profile_type: ProfileType
    timestamp: float
    value: float
    context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProfileReport:
    """剖析报告"""
    report_id: str
    profile_type: ProfileType
    total_samples: int = 0
    total_time_ms: float = 0.0
    avg_value: float = 0.0
    max_value: float = 0.0
    min_value: float = 0.0
    hotspots: List[Dict[str, Any]] = field(default_factory=list)


# ============================================================
# 剖析器
# ============================================================

class Profiler:
    """
    性能剖析器

    收集和分析性能样本
    """

    def __init__(self, profiler_id: str):
        self.profiler_id = profiler_id
        self._samples: List[ProfileSample] = []
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> None:
        """开始剖析"""
        self._running = True

    def stop(self) -> None:
        """停止剖析"""
        self._running = False

    def record(self, sample: ProfileSample) -> None:
        """记录样本"""
        with self._lock:
            self._samples.append(sample)

    def profile_function(self, fn: Callable[..., Any], *args, **kwargs) -> Dict[str, Any]:
        """
        剖析函数执行

        测量函数的执行时间和资源消耗
        """
        start = time.time()
        result = fn(*args, **kwargs)
        elapsed_ms = (time.time() - start) * 1000

        sample = ProfileSample(
            sample_id=f"sample_{len(self._samples)}",
            profile_type=ProfileType.LATENCY,
            timestamp=time.time(),
            value=elapsed_ms,
            context=fn.__name__,
        )
        self.record(sample)

        return {
            "result": result,
            "elapsed_ms": elapsed_ms,
        }

    def generate_report(self, profile_type: ProfileType) -> ProfileReport:
        """生成剖析报告"""
        with self._lock:
            samples = [s for s in self._samples if s.profile_type == profile_type]

        if not samples:
            return ProfileReport(
                report_id=f"report_{profile_type.value}",
                profile_type=profile_type,
            )

        values = [s.value for s in samples]
        total_time = sum(values)

        # 计算热点（按context分组）
        context_values: Dict[str, List[float]] = {}
        for s in samples:
            context_values.setdefault(s.context, []).append(s.value)

        hotspots = [
            {
                "context": ctx,
                "total": sum(vals),
                "avg": sum(vals) / len(vals),
                "count": len(vals),
            }
            for ctx, vals in context_values.items()
        ]
        hotspots.sort(key=lambda h: h["total"], reverse=True)

        return ProfileReport(
            report_id=f"report_{profile_type.value}_{int(time.time())}",
            profile_type=profile_type,
            total_samples=len(samples),
            total_time_ms=total_time,
            avg_value=sum(values) / len(values),
            max_value=max(values),
            min_value=min(values),
            hotspots=hotspots[:10],
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "profiler_id": self.profiler_id,
                "total_samples": len(self._samples),
                "running": self._running,
            }

    def clear(self) -> None:
        """清除样本"""
        with self._lock:
            self._samples = []


# ============================================================
# 便捷函数
# ============================================================

def create_profiler(profiler_id: str) -> Profiler:
    """创建剖析器"""
    return Profiler(profiler_id=profiler_id)


def create_profile_sample(
    sample_id: str,
    profile_type: ProfileType,
    value: float,
    context: str = "",
) -> ProfileSample:
    """创建性能样本"""
    return ProfileSample(
        sample_id=sample_id,
        profile_type=profile_type,
        timestamp=time.time(),
        value=value,
        context=context,
    )
