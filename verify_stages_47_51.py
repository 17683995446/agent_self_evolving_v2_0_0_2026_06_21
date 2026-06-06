"""
验证阶段47-51: 推理引擎、工作流编排、A/B测试、多租户、审计日志
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

# 加载模块
ie = load_module("inference_engine", "/workspace/self_evolving_agent/core/inference_engine.py")
wf = load_module("workflow", "/workspace/self_evolving_agent/core/workflow.py")
ab = load_module("ab_testing", "/workspace/self_evolving_agent/core/ab_testing.py")
mt = load_module("multi_tenant", "/workspace/self_evolving_agent/core/multi_tenant.py")
al = load_module("audit_log", "/workspace/self_evolving_agent/core/audit_log.py")

print("=" * 60)
print("验证阶段47-51")
print("=" * 60)

# ========== 阶段47: 推理引擎 ==========
def test_stage47():
    engine = ie.create_inference_engine()
    engine.add_fact(ie.create_fact("temperature", "sensor1", 25.0))
    engine.add_fact(ie.create_fact("humidity", "sensor1", 60.0))

    rule = ie.create_rule(
        name="comfort_check",
        conditions=[
            lambda facts: any(f.predicate == "temperature" and f.value > 20 for f in facts),
        ],
        conclusion=lambda facts: [ie.create_fact("comfort", "room1", "comfortable", 0.9)],
        priority=1,
    )
    engine.add_rule(rule)
    results = engine.infer()
    assert len(results) >= 1, "推理应产生结果"
    assert results[0].conclusion.predicate == "comfort"
    stats = engine.get_stats()
    assert stats["fact_count"] >= 3
    assert stats["rule_count"] == 1
    print("  [阶段47] 推理引擎 OK")

# ========== 阶段48: 工作流编排 ==========
def test_stage48():
    workflow = wf.create_workflow("wf1")
    step1 = wf.create_step("step1", fn=lambda x: x + 1)
    step2 = wf.create_step("step2", fn=lambda x: x * 2, dependencies=["step1"])
    workflow.add_step(step1)
    workflow.add_step(step2)

    engine = wf.WorkflowEngine()
    engine.register(workflow)
    results = engine.execute("wf1", initial_input=5)

    assert results["step1"].status.name == "SUCCESS"
    assert results["step1"].output == 6
    assert results["step2"].status.name == "SUCCESS"
    assert results["step2"].output == 12
    print("  [阶段48] 工作流编排 OK")

# ========== 阶段49: A/B测试 ==========
def test_stage49():
    variant_a = ab.create_variant("A", "控制组", traffic_ratio=0.5, color="red")
    variant_b = ab.create_variant("B", "实验组", traffic_ratio=0.5, color="blue")
    experiment = ab.create_experiment("exp1", "按钮颜色实验", [variant_a, variant_b], strategy=ab.AssignmentStrategy.HASH)
    experiment.start()

    engine = ab.create_ab_test_engine()
    engine.register_experiment(experiment)

    # 分配用户
    assignment_counts = {"A": 0, "B": 0}
    for i in range(100):
        v = engine.assign_variant("exp1", f"user_{i}")
        assert v is not None
        assignment_counts[v.variant_id] += 1

    # 记录指标
    for i in range(100):
        v = engine.assign_variant("exp1", f"user_{i}")
        engine.record_observation("exp1", v.variant_id, "click_rate", 0.1 if v.variant_id == "A" else 0.15)

    results = engine.get_experiment_results("exp1")
    assert results["experiment_id"] == "exp1"
    assert len(results["variants"]) == 2
    print("  [阶段49] A/B测试 OK")

# ========== 阶段50: 多租户 ==========
def test_stage50():
    manager = mt.create_tenant_manager()
    t1 = manager.create_tenant("t1", "租户A", region="cn")
    t2 = manager.create_tenant("t2", "租户B", region="us")

    assert manager.get_tenant("t1").name == "租户A"
    assert manager.get_tenant("t2").name == "租户B"

    manager.set_quota("t1", "cpu", 100.0)
    assert manager.get_quota("t1", "cpu") == 100.0
    assert manager.check_access("t1") is True

    # 测试上下文
    mt.TenantContext.set_current_tenant("t1")
    assert mt.TenantContext.get_current_tenant_id() == "t1"
    mt.TenantContext.clear()
    assert mt.TenantContext.get_current_tenant_id() is None

    stats = manager.get_stats()
    assert stats["total_tenants"] == 2
    print("  [阶段50] 多租户 OK")

# ========== 阶段51: 审计日志 ==========
def test_stage51():
    log = al.create_audit_log()
    e1 = log.log("alice", al.AuditAction.CREATE, "model1", al.AuditResult.SUCCESS)
    e2 = log.log("bob", al.AuditAction.UPDATE, "model1", al.AuditResult.SUCCESS)
    e3 = log.log("alice", al.AuditAction.DELETE, "model2", al.AuditResult.FAILURE)

    assert log.verify_integrity() is True
    assert e2.previous_hash == e1.current_hash

    results = log.query(user_id="alice")
    assert len(results) == 2

    results = log.query(action=al.AuditAction.UPDATE)
    assert len(results) == 1

    # 篡改检测
    log._events[0].current_hash = "tampered"
    assert log.verify_integrity() is False
    print("  [阶段51] 审计日志 OK")

if __name__ == "__main__":
    test_stage47()
    test_stage48()
    test_stage49()
    test_stage50()
    test_stage51()
    print("=" * 60)
    print("阶段47-51全部验证通过 ✓")
    print("=" * 60)
