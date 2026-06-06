"""
阶段12验证：自由能计算精确化
"""
import sys
sys.path.insert(0, '/workspace')

import numpy as np
from self_evolving_agent.modules.free_energy import (
    EnergyTerm, ComplexityTerm, FreeEnergy, FreeEnergyCalculator
)


def test_energy_term():
    """测试能量项计算"""
    print("=" * 60)
    print("测试: 能量项")
    print("=" * 60)

    calc = FreeEnergyCalculator()

    # 完美预测
    perfect = calc.compute_energy(
        predicted={"a": 1.0, "b": 2.0},
        actual={"a": 1.0, "b": 2.0}
    )
    print(f"完美预测: accuracy={perfect.accuracy:.3f}, error={perfect.prediction_error:.3f}")
    assert perfect.prediction_error == 0.0
    assert perfect.accuracy == 0.0

    # 有误差预测
    imperfect = calc.compute_energy(
        predicted={"a": 1.0, "b": 2.0},
        actual={"a": 1.5, "b": 2.5}
    )
    print(f"有误差预测: accuracy={imperfect.accuracy:.3f}, error={imperfect.prediction_error:.3f}")
    assert imperfect.prediction_error > 0.0
    assert imperfect.accuracy < 0.0

    print("\n能量项测试通过!")
    return True


def test_complexity_term():
    """测试复杂度项计算"""
    print("\n" + "=" * 60)
    print("测试: 复杂度项")
    print("=" * 60)

    calc = FreeEnergyCalculator()

    # 简单后验（接近先验）
    simple = calc.compute_complexity(
        posterior_mean={"a": 0.1, "b": 0.1},
        posterior_var={"a": 0.9, "b": 0.9},
    )
    print(f"简单后验: KL={simple.kl_divergence:.3f}, params={simple.parameter_count}")

    # 复杂后验（远离先验）
    complex_post = calc.compute_complexity(
        posterior_mean={"a": 2.0, "b": 3.0},
        posterior_var={"a": 0.1, "b": 0.1},
    )
    print(f"复杂后验: KL={complex_post.kl_divergence:.3f}, params={complex_post.parameter_count}")
    assert complex_post.kl_divergence > simple.kl_divergence

    print("\n复杂度项测试通过!")
    return True


def test_free_energy():
    """测试总自由能"""
    print("\n" + "=" * 60)
    print("测试: 总自由能")
    print("=" * 60)

    calc = FreeEnergyCalculator()

    # 计算自由能
    fe = calc.compute(
        predicted={"a": 1.0, "b": 2.0},
        actual={"a": 1.2, "b": 2.1},
        posterior_var={"a": 0.1, "b": 0.1},
    )

    print(f"总自由能: {fe.total:.3f}")
    print(f"能量项: {fe.energy.value():.3f}")
    print(f"复杂度项: {fe.complexity.value():.3f}")
    print(f"惊奇度: {fe.surprise:.3f}")

    decomp = fe.decompose()
    print(f"分解: {decomp}")

    assert fe.total == fe.energy.value() + fe.complexity.value()

    # 多次计算，检查历史
    for i in range(15):
        calc.compute(
            predicted={"a": 1.0 + i * 0.1, "b": 2.0},
            actual={"a": 1.2, "b": 2.1},
        )

    avg = calc.get_average(window=10)
    print(f"\n最近10次平均: {avg}")
    assert avg is not None
    assert "mean_total" in avg

    print("\n总自由能测试通过!")
    return True


def test_numerical_stability():
    """测试数值稳定性"""
    print("\n" + "=" * 60)
    print("测试: 数值稳定性")
    print("=" * 60)

    calc = FreeEnergyCalculator()

    # 极端值
    extreme = calc.compute(
        predicted={"a": 1e6, "b": -1e6},
        actual={"a": -1e6, "b": 1e6},
    )
    print(f"极端值: total={extreme.total:.3f}, error={extreme.energy.prediction_error:.3e}")
    assert not np.isnan(extreme.total)
    assert not np.isinf(extreme.total)

    # 零值
    zero = calc.compute(
        predicted={"a": 0.0, "b": 0.0},
        actual={"a": 0.0, "b": 0.0},
    )
    print(f"零值: total={zero.total:.3f}")
    assert not np.isnan(zero.total)

    print("\n数值稳定性测试通过!")
    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("阶段12: 自由能计算精确化 — 验证测试")
    print("=" * 60)

    tests = [
        ("能量项", test_energy_term),
        ("复杂度项", test_complexity_term),
        ("总自由能", test_free_energy),
        ("数值稳定性", test_numerical_stability),
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
