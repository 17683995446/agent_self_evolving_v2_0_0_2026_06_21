"""
验证阶段62-66: 混沌工程、容量规划、成本优化、灾备恢复、性能剖析
"""
import sys
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

ce = load_module("chaos_engineering", "/workspace/self_evolving_agent/core/chaos_engineering.py")
cp = load_module("capacity_planning", "/workspace/self_evolving_agent/core/capacity_planning.py")
co = load_module("cost_optimization", "/workspace/self_evolving_agent/core/cost_optimization.py")
dr = load_module("disaster_recovery", "/workspace/self_evolving_agent/core/disaster_recovery.py")
pf = load_module("profiler", "/workspace/self_evolving_agent/core/profiler.py")

print("=" * 60)
print("验证阶段62-66")
print("=" * 60)

# 阶段62: 混沌工程
def test_stage62():
    engine = ce.create_chaos_engine()
    exp = ce.create_chaos_experiment("exp1", "系统在高延迟下保持可用")
    exp.add_attack(ce.create_chaos_attack("a1", ce.AttackType.LATENCY, "svc1", duration_sec=0.05))
    result = engine.run_experiment(exp)
    assert result.status == ce.ExperimentStatus.COMPLETED
    assert result.attacks_executed == 1
    print("  [阶段62] 混沌工程 OK")

# 阶段63: 容量规划
def test_stage63():
    planner = cp.create_capacity_planner()
    policy = cp.create_scaling_policy("p1", cp.ResourceType.CPU, scale_up_threshold=0.7)
    planner.register_policy(policy)
    for _ in range(15):
        planner.record_metrics("svc1", cp.create_resource_metrics(cp.ResourceType.CPU, 80.0, 100.0))
    rec = planner.evaluate("svc1", cp.ResourceType.CPU, current_replicas=3)
    assert rec.direction == cp.ScalingDirection.SCALE_UP
    print("  [阶段63] 容量规划 OK")

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

if __name__ == "__main__":
    test_stage62()
    test_stage63()
    test_stage64()
    test_stage65()
    test_stage66()
    print("=" * 60)
    print("阶段62-66全部验证通过 ✓")
    print("=" * 60)
