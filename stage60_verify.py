"""
阶段60验证: 部署编排接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("do", "/workspace/self_evolving_agent/core/deployment_orchestrator.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["do"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段60验证: 部署编排接口标准化")
print("=" * 60)

# 测试1: 滚动部署
def test_rolling_deploy():
    orch = mod.create_orchestrator()
    dep = mod.create_deployment("d1", "svc1", "v2", mod.DeploymentStrategyType.ROLLING, replicas=3)
    instances = orch.deploy(dep)
    assert len(instances) == 3
    assert all(i.status == mod.InstanceStatus.RUNNING for i in instances)
    print("  [test_rolling_deploy] 滚动部署 OK")

# 测试2: 蓝绿部署
def test_blue_green_deploy():
    orch = mod.create_orchestrator()
    dep = mod.create_deployment("d2", "svc2", "v1", mod.DeploymentStrategyType.BLUE_GREEN, replicas=2)
    instances = orch.deploy(dep)
    assert len(instances) == 2
    assert all(i.status == mod.InstanceStatus.HEALTHY for i in instances)
    assert all("green" in i.instance_id for i in instances)
    print("  [test_blue_green_deploy] 蓝绿部署 OK")

# 测试3: 金丝雀部署
def test_canary_deploy():
    orch = mod.create_orchestrator()
    dep = mod.create_deployment("d3", "svc3", "v1", mod.DeploymentStrategyType.CANARY, replicas=10)
    instances = orch.deploy(dep)
    assert len(instances) == 1  # 10% of 10 = 1
    assert all("canary" in i.instance_id for i in instances)
    print("  [test_canary_deploy] 金丝雀部署 OK")

# 测试4: 扩缩容
def test_scale():
    orch = mod.create_orchestrator()
    dep = mod.create_deployment("d4", "svc4", "v1", replicas=2)
    orch.deploy(dep)
    assert len(orch.get_instances("svc4")) == 2

    orch.scale("svc4", 5)
    assert len(orch.get_instances("svc4")) == 5

    orch.scale("svc4", 1)
    running = [i for i in orch.get_instances("svc4") if i.status not in (mod.InstanceStatus.STOPPED, mod.InstanceStatus.TERMINATING)]
    assert len(running) == 1
    print("  [test_scale] 扩缩容 OK")

# 测试5: 健康检查
def test_health_check():
    orch = mod.create_orchestrator()
    dep = mod.create_deployment("d5", "svc5", "v1", replicas=1)
    instances = orch.deploy(dep)
    instance_id = instances[0].instance_id

    result = orch.health_check(instance_id)
    assert isinstance(result, bool)
    instance = orch.get_instances("svc5")[0]
    assert instance.health_checks >= 1
    print("  [test_health_check] 健康检查 OK")

# 测试6: 回滚
def test_rollback():
    orch = mod.create_orchestrator()
    dep = mod.create_deployment("d6", "svc6", "v2", replicas=3)
    orch.deploy(dep)
    assert len(orch.get_instances("svc6")) == 3

    orch.rollback("d6")
    stopped = [i for i in orch.get_instances("svc6") if i.status == mod.InstanceStatus.STOPPED]
    assert len(stopped) == 3
    print("  [test_rollback] 回滚 OK")

# 测试7: 统计信息
def test_stats():
    orch = mod.create_orchestrator()
    dep = mod.create_deployment("d7", "svc7", "v1", replicas=2)
    orch.deploy(dep)
    for inst in orch.get_instances("svc7"):
        orch.health_check(inst.instance_id)

    stats = orch.get_stats()
    assert stats["total_instances"] == 2
    assert stats["total_deployments"] == 1
    print("  [test_stats] 统计信息 OK")

if __name__ == "__main__":
    test_rolling_deploy()
    test_blue_green_deploy()
    test_canary_deploy()
    test_scale()
    test_health_check()
    test_rollback()
    test_stats()
    print("=" * 60)
    print("阶段60验证通过 ✓")
    print("=" * 60)
