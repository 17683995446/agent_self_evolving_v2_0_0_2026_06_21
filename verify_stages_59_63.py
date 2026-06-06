"""
验证阶段59-63: 自动化测试、部署编排、服务网格、混沌工程、容量规划
"""
import sys
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

at = load_module("auto_testing", "/workspace/self_evolving_agent/core/auto_testing.py")
do = load_module("deployment_orchestrator", "/workspace/self_evolving_agent/core/deployment_orchestrator.py")
sm = load_module("service_mesh", "/workspace/self_evolving_agent/core/service_mesh.py")
ce = load_module("chaos_engineering", "/workspace/self_evolving_agent/core/chaos_engineering.py")
cp = load_module("capacity_planning", "/workspace/self_evolving_agent/core/capacity_planning.py")

print("=" * 60)
print("验证阶段59-63")
print("=" * 60)

# 阶段59: 自动化测试
def test_stage59():
    suite = at.create_test_suite("s1")
    suite.add_test(at.create_test_case("t1", lambda: None))
    runner = at.create_test_runner()
    report = runner.run(suite)
    assert report.get_summary()["passed"] == 1
    print("  [阶段59] 自动化测试 OK")

# 阶段60: 部署编排
def test_stage60():
    orch = do.create_orchestrator()
    dep = do.create_deployment("d1", "svc1", "v2", do.DeploymentStrategyType.ROLLING, replicas=3)
    instances = orch.deploy(dep)
    assert len(instances) == 3
    orch.scale("svc1", 5)
    assert len(orch.get_instances("svc1")) == 5
    print("  [阶段60] 部署编排 OK")

# 阶段61: 服务网格
def test_stage61():
    mesh = sm.create_service_mesh()
    proxy = mesh.create_proxy("svc_a")
    ep = sm.create_endpoint("ep1", "svc_b", "10.0.0.1", 8080)
    proxy.register_endpoint(ep)
    result = proxy.route("svc_a", "svc_b", {})
    assert result["status"] == "success"
    print("  [阶段61] 服务网格 OK")

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

if __name__ == "__main__":
    test_stage59()
    test_stage60()
    test_stage61()
    test_stage62()
    test_stage63()
    print("=" * 60)
    print("阶段59-63全部验证通过 ✓")
    print("=" * 60)
