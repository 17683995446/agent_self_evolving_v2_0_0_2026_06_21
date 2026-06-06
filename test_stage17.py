"""
阶段17验证：探索-利用自适应
"""
import sys
sys.path.insert(0, '/workspace')

import numpy as np
from self_evolving_agent.modules.exploration import (
    AdaptiveExplorationRate, ExplorationStrategy
)


def test_adaptive_rate():
    """测试自适应探索率"""
    print("=" * 60)
    print("测试: 自适应探索率")
    print("=" * 60)

    adaptive = AdaptiveExplorationRate(
        epsilon_min=0.01, epsilon_max=0.5, adaptation_rate=0.2
    )
    adaptive.initialize({})

    # 高不确定性 + 低性能 -> 高探索率
    eps = adaptive.compute_exploration_rate(uncertainty=0.8, performance=0.2)
    print(f"高不确定性+低性能: ε={eps:.3f}")
    assert eps > 0.2

    # 低不确定性 + 高性能 -> 低探索率
    for _ in range(10):
        eps = adaptive.compute_exploration_rate(uncertainty=0.1, performance=0.9)
    print(f"低不确定性+高性能: ε={eps:.3f}")
    assert eps < 0.1

    # 中等状态
    for _ in range(5):
        eps = adaptive.compute_exploration_rate(uncertainty=0.5, performance=0.5)
    print(f"中等状态: ε={eps:.3f}")
    assert 0.01 <= eps <= 0.5

    print("\n自适应探索率测试通过!")
    return True


def test_temperature():
    """测试温度参数"""
    print("\n" + "=" * 60)
    print("测试: 温度参数")
    print("=" * 60)

    adaptive = AdaptiveExplorationRate()
    adaptive.initialize({})

    for t in [0, 1, 10, 100, 1000]:
        temp = adaptive.get_temperature(t)
        print(f"迭代 {t}: T={temp:.4f}")

    # 温度应随时间递减
    assert adaptive.get_temperature(0) > adaptive.get_temperature(10)
    assert adaptive.get_temperature(10) > adaptive.get_temperature(100)

    print("\n温度参数测试通过!")
    return True


def test_boltzmann_selection():
    """测试Boltzmann选择"""
    print("\n" + "=" * 60)
    print("测试: Boltzmann选择")
    print("=" * 60)

    adaptive = AdaptiveExplorationRate()
    adaptive.initialize({})

    scores = [1.0, 2.0, 3.0]

    # 高温：选择更随机
    counts_high = [0, 0, 0]
    for _ in range(1000):
        idx = adaptive.boltzmann_selection(scores, temperature=10.0)
        counts_high[idx] += 1
    print(f"高温(T=10): 选择分布={counts_high}")

    # 低温：选择更集中于最高分
    counts_low = [0, 0, 0]
    for _ in range(1000):
        idx = adaptive.boltzmann_selection(scores, temperature=0.1)
        counts_low[idx] += 1
    print(f"低温(T=0.1): 选择分布={counts_low}")

    # 低温下最高分应被选择更多
    assert counts_low[2] > counts_low[0]

    print("\nBoltzmann选择测试通过!")
    return True


def test_exploration_strategy():
    """测试探索策略"""
    print("\n" + "=" * 60)
    print("测试: 探索策略")
    print("=" * 60)

    strategy = ExplorationStrategy()
    strategy.initialize({})

    action_scores = {
        "action_a": 0.3,
        "action_b": 0.5,
        "action_c": 0.2,
    }

    # 高不确定性 -> 更多探索
    selections = {"action_a": 0, "action_b": 0, "action_c": 0}
    for _ in range(100):
        action = strategy.select_action(
            action_scores, uncertainty=0.8, performance=0.3
        )
        selections[action] += 1

    print(f"高不确定性下选择分布: {selections}")
    # 高不确定性下探索较多，但Boltzmann仍会偏向高分
    assert selections["action_b"] > selections["action_c"]  # action_b得分更高

    # 低不确定性 -> 更多利用
    strategy2 = ExplorationStrategy()
    strategy2.initialize({})
    selections2 = {"action_a": 0, "action_b": 0, "action_c": 0}
    for _ in range(100):
        action = strategy2.select_action(
            action_scores, uncertainty=0.1, performance=0.9
        )
        selections2[action] += 1

    print(f"低不确定性下选择分布: {selections2}")
    # action_b得分最高，应被选择最多
    assert selections2["action_b"] > 50

    print("\n探索策略测试通过!")
    return True


def test_state_tracking():
    """测试状态跟踪"""
    print("\n" + "=" * 60)
    print("测试: 状态跟踪")
    print("=" * 60)

    adaptive = AdaptiveExplorationRate()
    adaptive.initialize({})

    for i in range(20):
        adaptive.compute_exploration_rate(
            uncertainty=0.3 + 0.1 * np.sin(i),
            performance=0.7 + 0.1 * np.cos(i)
        )

    state = adaptive.get_state()
    print(f"状态: {state}")
    assert "current_epsilon" in state
    assert "uncertainty_history_size" in state
    assert state["uncertainty_history_size"] == 20

    print("\n状态跟踪测试通过!")
    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("阶段17: 探索-利用自适应 — 验证测试")
    print("=" * 60)

    tests = [
        ("自适应探索率", test_adaptive_rate),
        ("温度参数", test_temperature),
        ("Boltzmann选择", test_boltzmann_selection),
        ("探索策略", test_exploration_strategy),
        ("状态跟踪", test_state_tracking),
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
