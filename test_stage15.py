"""
阶段15验证：动态权重自适应
"""
import sys
sys.path.insert(0, '/workspace')

import numpy as np
from self_evolving_agent.modules.drive_weights import (
    DynamicWeightAdapter, WeightedDriveSystem, WeightConfig
)


def test_softmax_normalization():
    """测试softmax归一化"""
    print("=" * 60)
    print("测试: Softmax归一化")
    print("=" * 60)

    adapter = DynamicWeightAdapter()
    adapter.initialize({})

    # 初始权重
    weights = adapter.compute_weights()
    print(f"初始权重: safe={weights.safe:.3f}, gain={weights.gain:.3f}, eff={weights.eff:.3f}")
    assert abs(weights.safe + weights.gain + weights.eff - 1.0) < 1e-6

    # 更新权重
    adapter.update("safe", 1.0)
    adapter.update("gain", 0.5)
    adapter.update("eff", 0.3)

    weights = adapter.compute_weights()
    print(f"更新后权重: safe={weights.safe:.3f}, gain={weights.gain:.3f}, eff={weights.eff:.3f}")
    assert abs(weights.safe + weights.gain + weights.eff - 1.0) < 1e-6
    assert weights.safe > weights.gain  # safe表现更好，权重应更高

    print("\nSoftmax归一化测试通过!")
    return True


def test_weight_adaptation():
    """测试权重自适应"""
    print("\n" + "=" * 60)
    print("测试: 权重自适应")
    print("=" * 60)

    adapter = DynamicWeightAdapter(learning_rate=0.5)
    adapter.initialize({})

    print("模拟：safe驱力持续有效，gain和eff无效")
    for i in range(20):
        adapter.update("safe", 1.0)
        adapter.update("gain", 0.2)
        adapter.update("eff", 0.2)

    weights = adapter.compute_weights()
    print(f"20轮后权重: safe={weights.safe:.3f}, gain={weights.gain:.3f}, eff={weights.eff:.3f}")
    assert weights.safe > 0.5  # safe应占主导

    print("\n模拟：切换到gain驱力有效")
    for i in range(20):
        adapter.update("safe", 0.2)
        adapter.update("gain", 1.0)
        adapter.update("eff", 0.2)

    weights = adapter.compute_weights()
    print(f"再20轮后权重: safe={weights.safe:.3f}, gain={weights.gain:.3f}, eff={weights.eff:.3f}")
    assert weights.gain > 0.5  # gain应占主导

    print("\n权重自适应测试通过!")
    return True


def test_weighted_gaps():
    """测试加权缺口计算"""
    print("\n" + "=" * 60)
    print("测试: 加权缺口计算")
    print("=" * 60)

    adapter = DynamicWeightAdapter()
    adapter.initialize({})

    # 设置权重偏好
    for _ in range(10):
        adapter.update("safe", 1.0)
        adapter.update("gain", 0.5)
        adapter.update("eff", 0.3)

    # 计算加权缺口
    result = adapter.get_weighted_gaps(0.8, 0.5, 0.3)
    print(f"原始缺口: safe=0.8, gain=0.5, eff=0.3")
    print(f"加权后: safe={result['safe']:.3f}, gain={result['gain']:.3f}, eff={result['eff']:.3f}")
    print(f"权重: safe={result['weights']['safe']:.3f}, gain={result['weights']['gain']:.3f}, eff={result['weights']['eff']:.3f}")

    # 加权和应为1
    assert abs(result["safe"] + result["gain"] + result["eff"] - 1.0) < 1e-6

    print("\n加权缺口计算测试通过!")
    return True


def test_weighted_drive_system():
    """测试加权驱力系统"""
    print("\n" + "=" * 60)
    print("测试: 加权驱力系统")
    print("=" * 60)

    system = WeightedDriveSystem()
    system.initialize({})

    state = {
        "v1": 0.5, "v2": 0.6, "v3": 0.4,
        "uncertainty": 0.3,
        "cpu_usage": 0.4, "memory_usage": 0.5, "task_completion_rate": 0.7,
    }

    result = system.compute_weighted_gaps(state)
    print(f"原始缺口: {result['raw_gaps']}")
    print(f"加权缺口: {result['weighted_gaps']}")
    print(f"权重: {result['weights']}")

    assert "raw_gaps" in result
    assert "weighted_gaps" in result
    assert "weights" in result

    # 更新权重
    system.update_weights("safe", 1.0)
    system.update_weights("gain", 0.5)

    result2 = system.compute_weighted_gaps(state)
    print(f"\n更新权重后:")
    print(f"权重: {result2['weights']}")

    print("\n加权驱力系统测试通过!")
    return True


def test_weight_config():
    """测试权重配置"""
    print("\n" + "=" * 60)
    print("测试: 权重配置")
    print("=" * 60)

    config = WeightConfig(safe=0.5, gain=0.3, eff=0.2)
    arr = config.to_array()
    print(f"配置转数组: {arr}")
    assert len(arr) == 3

    config2 = WeightConfig.from_array(arr)
    print(f"数组转配置: safe={config2.safe}, gain={config2.gain}, eff={config2.eff}")
    assert config2.safe == 0.5

    print("\n权重配置测试通过!")
    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("阶段15: 动态权重自适应 — 验证测试")
    print("=" * 60)

    tests = [
        ("Softmax归一化", test_softmax_normalization),
        ("权重自适应", test_weight_adaptation),
        ("加权缺口计算", test_weighted_gaps),
        ("加权驱力系统", test_weighted_drive_system),
        ("权重配置", test_weight_config),
    ]

    passed = 0
    failed = 0
    for name, test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"\n测试 {name} 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
