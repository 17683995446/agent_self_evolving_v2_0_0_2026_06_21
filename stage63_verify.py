"""
阶段63验证: 容量规划接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("cp", "/workspace/self_evolving_agent/core/capacity_planning.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["cp"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段63验证: 容量规划接口标准化")
print("=" * 60)

# 测试1: 记录指标
def test_record_metrics():
    planner = mod.create_capacity_planner()
    metrics = mod.create_resource_metrics(mod.ResourceType.CPU, 70.0, 100.0)
    planner.record_metrics("svc1", metrics)
    assert planner.get_stats()["total_metric_streams"] == 1
    print("  [test_record_metrics] 记录指标 OK")

# 测试2: 扩容建议
def test_scale_up_recommendation():
    planner = mod.create_capacity_planner()
    policy = mod.create_scaling_policy("p1", mod.ResourceType.CPU, scale_up_threshold=0.7)
    planner.register_policy(policy)

    for _ in range(15):
        planner.record_metrics("svc1", mod.create_resource_metrics(mod.ResourceType.CPU, 80.0, 100.0))

    rec = planner.evaluate("svc1", mod.ResourceType.CPU, current_replicas=3)
    assert rec.direction == mod.ScalingDirection.SCALE_UP
    assert rec.recommended_replicas == 5  # 3 + 2
    print("  [test_scale_up_recommendation] 扩容建议 OK")

# 测试3: 缩容建议
def test_scale_down_recommendation():
    planner = mod.create_capacity_planner()
    policy = mod.create_scaling_policy("p1", mod.ResourceType.CPU, scale_down_threshold=0.4)
    planner.register_policy(policy)

    for _ in range(15):
        planner.record_metrics("svc2", mod.create_resource_metrics(mod.ResourceType.CPU, 20.0, 100.0))

    rec = planner.evaluate("svc2", mod.ResourceType.CPU, current_replicas=5)
    assert rec.direction == mod.ScalingDirection.SCALE_DOWN
    assert rec.recommended_replicas == 4  # 5 - 1
    print("  [test_scale_down_recommendation] 缩容建议 OK")

# 测试4: 无需变更
def test_no_change():
    planner = mod.create_capacity_planner()
    policy = mod.create_scaling_policy("p1", mod.ResourceType.CPU, scale_up_threshold=0.8, scale_down_threshold=0.3)
    planner.register_policy(policy)

    for _ in range(10):
        planner.record_metrics("svc3", mod.create_resource_metrics(mod.ResourceType.CPU, 50.0, 100.0))

    rec = planner.evaluate("svc3", mod.ResourceType.CPU, current_replicas=3)
    assert rec.direction == mod.ScalingDirection.NO_CHANGE
    print("  [test_no_change] 无需变更 OK")

# 测试5: 预测
def test_forecast():
    planner = mod.create_capacity_planner()
    # 模拟上升趋势
    for i in range(20):
        planner.record_metrics("svc4", mod.create_resource_metrics(mod.ResourceType.CPU, 30.0 + i * 2, 100.0))

    forecast = planner.forecast("svc4", mod.ResourceType.CPU, horizon_hours=10)
    assert forecast["trend"] == "increasing"
    assert "predicted_utilization" in forecast
    print("  [test_forecast] 预测 OK")

# 测试6: 利用率计算
def test_utilization():
    metrics = mod.create_resource_metrics(mod.ResourceType.MEMORY, 75.0, 100.0)
    assert metrics.utilization == 0.75
    print("  [test_utilization] 利用率计算 OK")

if __name__ == "__main__":
    test_record_metrics()
    test_scale_up_recommendation()
    test_scale_down_recommendation()
    test_no_change()
    test_forecast()
    test_utilization()
    print("=" * 60)
    print("阶段63验证通过 ✓")
    print("=" * 60)
