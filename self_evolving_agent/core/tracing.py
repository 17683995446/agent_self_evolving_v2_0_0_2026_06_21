"""
阶段67: 链路追踪接口标准化

第一性原理:
1. 分布式请求是跨服务的：一个请求经过多个节点
2. 问题定位需要全链路视图：只看单个节点无法定位根因
3. 追踪必须低开销：不能显著增加请求延迟

设计原则:
- Trace: 追踪
- Span: 跨度
- TraceContext: 追踪上下文
- Tracer: 追踪器
- 支持父子关系、标签、日志事件
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Span:
    """跨度"""
    span_id: str
    trace_id: str
    parent_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def finish(self, end_time: Optional[float] = None) -> None:
        """结束跨度"""
        self.end_time = end_time or time.time()

    def set_tag(self, key: str, value: Any) -> None:
        """设置标签"""
        self.tags[key] = value

    def log_event(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """记录日志事件"""
        self.logs.append({
            "timestamp": time.time(),
            "event": event,
            "payload": payload or {},
        })

    @property
    def duration_ms(self) -> float:
        """持续时间（毫秒）"""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000


@dataclass
class Trace:
    """追踪"""
    trace_id: str
    spans: List[Span] = field(default_factory=list)

    def get_root_span(self) -> Optional[Span]:
        """获取根跨度"""
        for span in self.spans:
            if span.parent_id is None:
                return span
        return None

    def get_duration_ms(self) -> float:
        """获取总持续时间"""
        if not self.spans:
            return 0.0
        starts = [s.start_time for s in self.spans]
        ends = [s.end_time for s in self.spans if s.end_time is not None]
        if not ends:
            return 0.0
        return (max(ends) - min(starts)) * 1000


# ============================================================
# 追踪器
# ============================================================

class Tracer:
    """
    追踪器

    创建和管理追踪与跨度
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self._traces: Dict[str, Trace] = {}
        self._active_spans: Dict[str, Span] = {}
        self._lock = threading.Lock()

    def start_span(self, operation_name: str, trace_id: Optional[str] = None, parent_id: Optional[str] = None) -> Span:
        """开始新跨度"""
        span_id = str(uuid.uuid4())[:8]
        trace_id = trace_id or str(uuid.uuid4())

        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_id=parent_id,
            operation_name=operation_name,
            start_time=time.time(),
        )

        with self._lock:
            if trace_id not in self._traces:
                self._traces[trace_id] = Trace(trace_id=trace_id)
            self._traces[trace_id].spans.append(span)
            self._active_spans[span_id] = span

        return span

    def finish_span(self, span_id: str) -> Optional[Span]:
        """结束跨度"""
        with self._lock:
            span = self._active_spans.pop(span_id, None)
        if span:
            span.finish()
        return span

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """获取追踪"""
        with self._lock:
            return self._traces.get(trace_id)

    def inject_context(self, span: Span) -> Dict[str, str]:
        """注入追踪上下文到请求头"""
        return {
            "x-trace-id": span.trace_id,
            "x-span-id": span.span_id,
        }

    def extract_context(self, headers: Dict[str, str]) -> Optional[Dict[str, str]]:
        """从请求头提取追踪上下文"""
        trace_id = headers.get("x-trace-id")
        span_id = headers.get("x-span-id")
        if trace_id and span_id:
            return {"trace_id": trace_id, "span_id": span_id}
        return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "service_name": self.service_name,
                "total_traces": len(self._traces),
                "active_spans": len(self._active_spans),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_tracer(service_name: str) -> Tracer:
    """创建追踪器"""
    return Tracer(service_name=service_name)


def create_span(
    span_id: str,
    trace_id: str,
    operation_name: str,
    parent_id: Optional[str] = None,
) -> Span:
    """创建跨度"""
    return Span(
        span_id=span_id,
        trace_id=trace_id,
        parent_id=parent_id,
        operation_name=operation_name,
        start_time=time.time(),
    )
