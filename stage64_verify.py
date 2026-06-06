"""
阶段64验证: 成本优化接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("co", "/workspace/self_evolving_agent/core/cost_optimization.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["co"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段64验证: 成本优化接口标准化")
print("=" * 60)

# 测试1: 资源成本计算
def test_resource_cost():
    cost = mod.create_resource_cost(mod.ResourceUnit.CPU_CORE, 4.0, 0.1, mod.PricingModel.ON_DEMAND, 24)
    assert cost.total_cost == 4.0 * 0.1 * 24 * 1.0

    cost_reserved = mod.create_resource_cost(mod.ResourceUnit.CPU_CORE, 4.0, 0.1, mod.PricingModel.RESERVED, 24)
    assert cost_reserved.total_cost == 4.0 * 0.1 * 24 * 0.6
    print("  [test_resource_cost] 资源成本计算 OK")

# 测试2: 记录和分析成本
def test_analyze():
    optimizer = mod.create_cost_optimizer()
    optimizer.record_cost("svc1", mod.create_resource_cost(mod.ResourceUnit.CPU_CORE, 4.0, 0.1, mod.PricingModel.ON_DEMAND, 24))
    optimizer.record_cost("svc1", mod.create_resource_cost(mod.ResourceUnit.MEMORY_GB, 16.0, 0.01, mod.PricingModel.ON_DEMAND, 24))

    report = optimizer.analyze("svc1")
    assert report.total_cost > 0
    assert "cpu_core" in report.breakdown
    assert len(report.recommendations) > 0
    print("  [test_analyze] 记录和分析成本 OK")

# 测试3: 定价模型对比
def test_compare_pricing():
    optimizer = mod.create_cost_optimizer()
    comparison = optimizer.compare_pricing_models(mod.ResourceUnit.CPU_CORE, 4.0, 24, 0.1)

    assert comparison[mod.PricingModel.ON_DEMAND] > comparison[mod.PricingModel.RESERVED]
    assert comparison[mod.PricingModel.RESERVED] > comparison[mod.PricingModel.SPOT]
    print("  [test_compare_pricing] 定价模型对比 OK")

# 测试4: 空数据分析
def test_empty_analyze():
    optimizer = mod.create_cost_optimizer()
    report = optimizer.analyze("svc_empty")
    assert report.total_cost == 0.0
    assert "no cost data" in report.recommendations[0]
    print("  [test_empty_analyze] 空数据分析 OK")

# 测试5: 低利用率建议
def test_low_utilization():
    optimizer = mod.create_cost_optimizer()
    optimizer.record_cost("svc2", mod.create_resource_cost(mod.ResourceUnit.CPU_CORE, 0.5, 0.1, mod.PricingModel.ON_DEMAND, 1))

    report = optimizer.analyze("svc2")
    assert any("reducing CPU" in r for r in report.recommendations)
    print("  [test_low_utilization] 低利用率建议 OK")

# 测试6: 统计信息
def test_stats():
    optimizer = mod.create_cost_optimizer()
    optimizer.record_cost("svc1", mod.create_resource_cost(mod.ResourceUnit.CPU_CORE, 1.0, 0.1))
    optimizer.record_cost("svc2", mod.create_resource_cost(mod.ResourceUnit.CPU_CORE, 2.0, 0.1))

    stats = optimizer.get_stats()
    assert stats["total_services"] == 2
    assert stats["total_cost_records"] == 2
    print("  [test_stats] 统计信息 OK")

if __name__ == "__main__":
    test_resource_cost()
    test_analyze()
    test_compare_pricing()
    test_empty_analyze()
    test_low_utilization()
    test_stats()
    print("=" * 60)
    print("阶段64验证通过 ✓")
    print("=" * 60)
