"""
阶段14验证：驱力计算数学化
"""
import sys
sys.path.insert(0, '/workspace')

import numpy as np
from self_evolving_agent.modules.drive_formulas import (
    SafeDriveEngine, GainDriveEngine, EffDriveEngine,
    UnifiedDriveSystem, DriveFormula
)


def test_safe_drive_formula():
    """测试安全驱力公式"""
    print("=" * 60)
    print("测试: 安全驱力公式")
    print("=" * 60)

    safe = SafeDriveEngine(z_threshold=2.0, lambda_param=1.0)
    safe.initialize({})

    # 获取公式
    formula = safe.get_formula()
    print(f"公式: {formula.formula}")
    print(f"物理意义: {formula.physical_meaning}")
    print(f"参数: {formula.parameters}")

    # 正常状态（无异常）
    normal_state = {"v1": 0.5, "v2": 0.6, "v3": 0.4}
    for _ in range(20):
        gap = safe.compute_gaps(normal_state)
    print(f"\n正常状态: gap={gap:.3f}")
    assert 0 <= gap <= 1

    # 异常状态
    anomaly_state = {"v1": 5.0, "v2": 0.6, "v3": 0.4}
    gap = safe.compute_gaps(anomaly_state)
    print(f"异常状态: gap={gap:.3f}")
    assert gap > 0.5  # 应该有显著的安全缺口

    # 验证公式行为
    # z_max = 0 时，gap 应该接近 0
    zero_state = {"v1": 0.5, "v2": 0.5, "v3": 0.5}
    for _ in range(20):
        gap = safe.compute_gaps(zero_state)
    print(f"恒定状态: gap={gap:.3f}")

    print("\n安全驱力公式测试通过!")
    return True


def test_gain_drive_formula():
    """测试收益驱力公式"""
    print("\n" + "=" * 60)
    print("测试: 收益驱力公式")
    print("=" * 60)

    gain = GainDriveEngine(mu_param=2.0, target_uncertainty=0.05)
    gain.initialize({})

    formula = gain.get_formula()
    print(f"公式: {formula.formula}")
    print(f"物理意义: {formula.physical_meaning}")

    # 低不确定性（信息充足）
    low_unc = {"uncertainty": 0.01}
    gap = gain.compute_gaps(low_unc)
    print(f"\n低不确定性: gap={gap:.3f}")
    assert gap < 0.1  # 应该几乎没有缺口

    # 高不确定性（信息不足）
    high_unc = {"uncertainty": 0.8}
    gap = gain.compute_gaps(high_unc)
    print(f"高不确定性: gap={gap:.3f}")
    assert gap > 0.5  # 应该有显著的缺口

    # 边界：uncertainty = 0
    zero_unc = {"uncertainty": 0.0}
    gap = gain.compute_gaps(zero_unc)
    print(f"零不确定性: gap={gap:.3f}")
    assert gap == 0.0

    print("\n收益驱力公式测试通过!")
    return True


def test_eff_drive_formula():
    """测试能效驱力公式"""
    print("\n" + "=" * 60)
    print("测试: 能效驱力公式")
    print("=" * 60)

    eff = EffDriveEngine(target_efficiency=0.8)
    eff.initialize({})

    formula = eff.get_formula()
    print(f"公式: {formula.formula}")
    print(f"物理意义: {formula.physical_meaning}")

    # 高能效状态
    high_eff = {"cpu_usage": 0.2, "memory_usage": 0.3, "task_completion_rate": 0.9}
    gap = eff.compute_gaps(high_eff)
    print(f"\n高能效: gap={gap:.3f}")
    assert gap == 0.0  # 应该无缺口

    # 低能效状态
    low_eff = {"cpu_usage": 0.9, "memory_usage": 0.9, "task_completion_rate": 0.3}
    gap = eff.compute_gaps(low_eff)
    print(f"低能效: gap={gap:.3f}")
    assert gap > 0.0  # 应该有缺口

    # 边界：刚好达标
    borderline = {"cpu_usage": 0.5, "memory_usage": 0.5, "task_completion_rate": 0.8}
    gap = eff.compute_gaps(borderline)
    print(f"边界状态: gap={gap:.3f}")
    assert 0 <= gap <= 1

    print("\n能效驱力公式测试通过!")
    return True


def test_normalization():
    """测试归一化"""
    print("\n" + "=" * 60)
    print("测试: 归一化")
    print("=" * 60)

    system = UnifiedDriveSystem()
    system.initialize({})

    test_states = [
        {"v1": 0.5, "v2": 0.6, "uncertainty": 0.5, "cpu_usage": 0.5, "memory_usage": 0.5, "task_completion_rate": 0.5},
        {"v1": 100.0, "v2": -100.0, "uncertainty": 1.0, "cpu_usage": 0.99, "memory_usage": 0.99, "task_completion_rate": 0.01},
        {"v1": 0.0, "v2": 0.0, "uncertainty": 0.0, "cpu_usage": 0.01, "memory_usage": 0.01, "task_completion_rate": 1.0},
    ]

    for i, state in enumerate(test_states):
        gaps = system.compute_all_gaps(state)
        print(f"\n状态 {i+1}:")
        print(f"  safe={gaps.safe_gap:.3f}, gain={gaps.gain_gap:.3f}, eff={gaps.eff_gap:.3f}")
        assert gaps.validate(), f"状态 {i+1} 验证失败"
        assert 0 <= gaps.safe_gap <= 1
        assert 0 <= gaps.gain_gap <= 1
        assert 0 <= gaps.eff_gap <= 1

    print("\n归一化测试通过!")
    return True


def test_unified_system():
    """测试统一驱力系统"""
    print("\n" + "=" * 60)
    print("测试: 统一驱力系统")
    print("=" * 60)

    system = UnifiedDriveSystem()
    system.initialize({})

    # 获取所有公式
    formulas = system.get_formulas()
    print(f"驱力公式数量: {len(formulas)}")
    for f in formulas:
        print(f"  {f.name}: {f.formula}")

    # 计算驱力
    state = {
        "v1": 0.5, "v2": 0.6, "v3": 0.4,
        "uncertainty": 0.3,
        "cpu_usage": 0.4, "memory_usage": 0.5, "task_completion_rate": 0.7,
    }
    gaps = system.compute_all_gaps(state)
    print(f"\n驱力缺口: safe={gaps.safe_gap:.3f}, gain={gaps.gain_gap:.3f}, eff={gaps.eff_gap:.3f}")

    assert gaps.validate()

    print("\n统一驱力系统测试通过!")
    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("阶段14: 驱力计算数学化 — 验证测试")
    print("=" * 60)

    tests = [
        ("安全驱力公式", test_safe_drive_formula),
        ("收益驱力公式", test_gain_drive_formula),
        ("能效驱力公式", test_eff_drive_formula),
        ("归一化", test_normalization),
        ("统一驱力系统", test_unified_system),
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
