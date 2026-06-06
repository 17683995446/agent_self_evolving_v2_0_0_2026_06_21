"""
验证阶段64-68: 成本优化、灾备恢复、性能剖析、链路追踪、告警管理
"""
import sys
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

co = load_module("cost_optimization", "/workspace/self_evolving_agent/core/cost_optimization.py")
dr = load_module("disaster_recovery", "/workspace/self_evolving_agent/core/disaster_recovery.py")
pf = load_module("profiler", "/workspace/self_evolving_agent/core/profiler.py")
tr = load_module("tracing", "/workspace/self_evolving_agent/core/tracing.py")
am = load_module("alert_manager", "/workspace/self_evolving_agent/core/alert_manager.py")

print("=" * 60)
print("验证阶段64-68")
print("=" * 60)

# 阶段64: 成本优化
def test_stage64():
    optimizer = co.create_cost_optimizer()
    optimizer.record_cost("svc1", co.create_resource_cost(co.ResourceUnit.CPU_CORE, 4.0, 0.1, co.PricingModel.ON_DEMAND, 24))
    report = optimizer.analyze("svc1")
    assert report.total_cost > 0
    assert len(report.recommendations) > 0
    print("  [阶段64] 成本优化 OK")

# 阶段65: 灾备恢复
def test_stage65():
    engine = dr.create_disaster_recovery_engine()
    engine.create_backup("db1", dr.BackupType.FULL)
    plan = dr.create_dr_plan("plan1", "svc1", rpo_seconds=3600)
    engine.register_plan(plan)
    engine.create_backup("svc1", dr.BackupType.FULL)
    compliance = engine.check_rpo_compliance("plan1")
    assert compliance["compliant"] is True
    print("  [阶段65] 灾备恢复 OK")

# 阶段66: 性能剖析
def test_stage66():
    profiler = pf.create_profiler("p1")
    profiler.record(pf.create_profile_sample("s1", pf.ProfileType.CPU, 50.0, "func_a"))
    report = profiler.generate_report(pf.ProfileType.CPU)
    assert report.total_samples == 1
    assert report.avg_value == 50.0
    print("  [阶段66] 性能剖析 OK")

# 阶段67: 链路追踪
def test_stage67():
    tracer = tr.create_tracer("svc1")
    span = tracer.start_span("op1")
    tracer.finish_span(span.span_id)
    trace = tracer.get_trace(span.trace_id)
    assert trace is not None
    assert len(trace.spans) == 1
    print("  [阶段67] 链路追踪 OK")

# 阶段68: 告警管理
def test_stage68():
    manager = am.create_alert_manager()
    rule = am.create_alert_rule("r1", "CPU高", lambda m: m.get("cpu", 0) > 80, am.AlertSeverity.HIGH, "CPU: {cpu}%", cooldown_sec=0)
    manager.register_rule(rule)
    alert = manager.evaluate("r1", {"cpu": 90})
    assert alert is not None
    assert alert.severity == am.AlertSeverity.HIGH
    print("  [阶段68] 告警管理 OK")

if __name__ == "__main__":
    test_stage64()
    test_stage65()
    test_stage66()
    test_stage67()
    test_stage68()
    print("=" * 60)
    print("阶段64-68全部验证通过 ✓")
    print("=" * 60)
