"""
验证阶段48-52: 工作流编排、A/B测试、多租户、审计日志、安全沙箱
"""
import sys
import importlib.util
import time

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

wf = load_module("workflow", "/workspace/self_evolving_agent/core/workflow.py")
ab = load_module("ab_testing", "/workspace/self_evolving_agent/core/ab_testing.py")
mt = load_module("multi_tenant", "/workspace/self_evolving_agent/core/multi_tenant.py")
al = load_module("audit_log", "/workspace/self_evolving_agent/core/audit_log.py")
sb = load_module("sandbox", "/workspace/self_evolving_agent/core/sandbox.py")

print("=" * 60)
print("验证阶段48-52")
print("=" * 60)

# 阶段48: 工作流编排
def test_stage48():
    workflow = wf.create_workflow("wf_test")
    step1 = wf.create_step("s1", fn=lambda x: x + 1)
    step2 = wf.create_step("s2", fn=lambda x: x * 2, dependencies=["s1"])
    workflow.add_step(step1)
    workflow.add_step(step2)
    engine = wf.WorkflowEngine()
    engine.register(workflow)
    results = engine.execute("wf_test", initial_input=5)
    assert results["s1"].output == 6
    assert results["s2"].output == 12
    print("  [阶段48] 工作流编排 OK")

# 阶段49: A/B测试
def test_stage49():
    va = ab.create_variant("A", "控制组", 0.5, color="red")
    vb = ab.create_variant("B", "实验组", 0.5, color="blue")
    exp = ab.create_experiment("e1", "颜色实验", [va, vb], ab.AssignmentStrategy.HASH)
    exp.start()
    engine = ab.create_ab_test_engine()
    engine.register_experiment(exp)
    for i in range(50):
        v = engine.assign_variant("e1", f"u{i}")
        engine.record_observation("e1", v.variant_id, "click", 1.0 if v.variant_id == "B" else 0.5)
    r = engine.get_experiment_results("e1")
    assert r["experiment_id"] == "e1"
    assert len(r["variants"]) == 2
    print("  [阶段49] A/B测试 OK")

# 阶段50: 多租户
def test_stage50():
    manager = mt.create_tenant_manager()
    manager.create_tenant("ta", "租户A", region="cn")
    manager.set_quota("ta", "cpu", 100.0)
    assert manager.get_quota("ta", "cpu") == 100.0
    mt.TenantContext.set_current_tenant("ta")
    assert mt.TenantContext.get_current_tenant_id() == "ta"
    mt.TenantContext.clear()
    assert mt.TenantContext.get_current_tenant_id() is None
    print("  [阶段50] 多租户 OK")

# 阶段51: 审计日志
def test_stage51():
    log = al.create_audit_log()
    e1 = log.log("alice", al.AuditAction.CREATE, "m1", al.AuditResult.SUCCESS)
    e2 = log.log("bob", al.AuditAction.UPDATE, "m1", al.AuditResult.SUCCESS)
    assert log.verify_integrity() is True
    assert e2.previous_hash == e1.current_hash
    assert len(log.query(user_id="alice")) == 1
    log._events[0].current_hash = "bad"
    assert log.verify_integrity() is False
    print("  [阶段51] 审计日志 OK")

# 阶段52: 安全沙箱
def compute_sum():
    return sum(range(100))

def sleep_short():
    time.sleep(2)

def test_stage52():
    ts = sb.create_thread_sandbox()
    task = sb.create_task("t1", compute_sum)
    limits = sb.ResourceLimit(max_execution_time_ms=2000)
    r = ts.execute(task, limits)
    assert r.status == sb.SandboxStatus.COMPLETED
    assert r.output == 4950

    task2 = sb.create_task("t2", sleep_short)
    limits2 = sb.ResourceLimit(max_execution_time_ms=100)
    r2 = ts.execute(task2, limits2)
    assert r2.status == sb.SandboxStatus.TIMEOUT
    print("  [阶段52] 安全沙箱 OK")

if __name__ == "__main__":
    test_stage48()
    test_stage49()
    test_stage50()
    test_stage51()
    test_stage52()
    print("=" * 60)
    print("阶段48-52全部验证通过 ✓")
    print("=" * 60)
