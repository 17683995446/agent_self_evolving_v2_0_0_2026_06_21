"""
阶段67验证: 链路追踪接口标准化
"""
import sys
import importlib.util
import time

spec = importlib.util.spec_from_file_location("tr", "/workspace/self_evolving_agent/core/tracing.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["tr"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段67验证: 链路追踪接口标准化")
print("=" * 60)

# 测试1: 创建跨度
def test_create_span():
    span = mod.create_span("s1", "t1", "op1")
    assert span.span_id == "s1"
    assert span.trace_id == "t1"
    assert span.parent_id is None
    assert span.operation_name == "op1"
    print("  [test_create_span] 创建跨度 OK")

# 测试2: 跨度生命周期
def test_span_lifecycle():
    tracer = mod.create_tracer("svc1")
    span = tracer.start_span("operation_a")
    assert span.trace_id is not None
    assert span.span_id is not None

    time.sleep(0.05)
    tracer.finish_span(span.span_id)
    assert span.duration_ms >= 50
    print("  [test_span_lifecycle] 跨度生命周期 OK")

# 测试3: 父子跨度
def test_parent_child():
    tracer = mod.create_tracer("svc2")
    parent = tracer.start_span("parent_op")
    child = tracer.start_span("child_op", trace_id=parent.trace_id, parent_id=parent.span_id)

    assert child.parent_id == parent.span_id
    assert child.trace_id == parent.trace_id
    print("  [test_parent_child] 父子跨度 OK")

# 测试4: 追踪上下文注入提取
def test_context_propagation():
    tracer = mod.create_tracer("svc3")
    span = tracer.start_span("op1")

    headers = tracer.inject_context(span)
    assert headers["x-trace-id"] == span.trace_id
    assert headers["x-span-id"] == span.span_id

    ctx = tracer.extract_context(headers)
    assert ctx["trace_id"] == span.trace_id
    assert ctx["span_id"] == span.span_id
    print("  [test_context_propagation] 上下文传播 OK")

# 测试5: 标签和日志
def test_tags_logs():
    span = mod.create_span("s1", "t1", "op1")
    span.set_tag("http.method", "GET")
    span.set_tag("http.status", 200)
    span.log_event("request_received", {"path": "/api"})

    assert span.tags["http.method"] == "GET"
    assert len(span.logs) == 1
    assert span.logs[0]["event"] == "request_received"
    print("  [test_tags_logs] 标签和日志 OK")

# 测试6: 获取追踪
def test_get_trace():
    tracer = mod.create_tracer("svc4")
    span = tracer.start_span("op1")
    tracer.finish_span(span.span_id)

    trace = tracer.get_trace(span.trace_id)
    assert trace is not None
    assert len(trace.spans) == 1
    assert trace.get_root_span().operation_name == "op1"
    print("  [test_get_trace] 获取追踪 OK")

# 测试7: 追踪持续时间
def test_trace_duration():
    tracer = mod.create_tracer("svc5")
    s1 = tracer.start_span("op1")
    time.sleep(0.03)
    s2 = tracer.start_span("op2", trace_id=s1.trace_id)
    time.sleep(0.02)
    tracer.finish_span(s1.span_id)
    tracer.finish_span(s2.span_id)

    trace = tracer.get_trace(s1.trace_id)
    duration = trace.get_duration_ms()
    assert duration >= 50  # 30ms + 20ms
    print("  [test_trace_duration] 追踪持续时间 OK")

if __name__ == "__main__":
    test_create_span()
    test_span_lifecycle()
    test_parent_child()
    test_context_propagation()
    test_tags_logs()
    test_get_trace()
    test_trace_duration()
    print("=" * 60)
    print("阶段67验证通过 ✓")
    print("=" * 60)
