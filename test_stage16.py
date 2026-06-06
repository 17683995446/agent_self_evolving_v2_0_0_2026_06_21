"""
阶段16验证：任务评估公式化
"""
import sys
sys.path.insert(0, '/workspace')

import numpy as np
from self_evolving_agent.modules.task_evaluation import (
    FormulaTaskEvaluator, UCBTaskSelector, EvaluationComponents
)
from self_evolving_agent.core.interfaces import TaskCandidate


def test_evaluation_components():
    """测试评估分量"""
    print("=" * 60)
    print("测试: 评估分量")
    print("=" * 60)

    components = EvaluationComponents(
        benefit=0.8,
        cost=0.3,
        success_prob=0.9,
        info_value=0.5,
        risk=0.1,
    )

    weights = {"benefit": 0.4, "cost": 0.3, "success": 0.2, "info": 0.1, "risk": 0.0}
    score = components.compute_score(weights)
    print(f"分量: benefit={components.benefit}, cost={components.cost}, "
          f"success={components.success_prob}, info={components.info_value}, risk={components.risk}")
    print(f"得分: {score:.3f}")

    # 验证计算
    expected = 0.4 * 0.8 - 0.3 * 0.3 + 0.2 * 0.9 + 0.1 * 0.5 - 0.0 * 0.1
    assert abs(score - expected) < 1e-6

    print("\n评估分量测试通过!")
    return True


def test_formula_evaluator():
    """测试公式化评估器"""
    print("\n" + "=" * 60)
    print("测试: 公式化评估器")
    print("=" * 60)

    evaluator = FormulaTaskEvaluator()
    evaluator.initialize({})

    print(f"评估公式: {evaluator.get_evaluation_formula()}")

    # 创建候选任务
    candidate = TaskCandidate(
        action="explore",
        params={"gap": 0.7, "novelty": 0.8, "difficulty": 0.3, "failure_cost": 0.2},
    )

    state = {
        "cpu_usage": 0.3,
        "memory_usage": 0.4,
        "historical_success_rate": 0.8,
        "uncertainty": 0.5,
    }

    evaluated = evaluator.evaluate(candidate, state)
    print(f"\n任务: {evaluated.action}")
    print(f"收益: {evaluated.expected_benefit:.3f}")
    print(f"成本: {evaluated.cost:.3f}")
    print(f"成功概率: {evaluated.success_probability:.3f}")
    print(f"信息价值: {evaluated.info_value:.3f}")

    # 获取分解
    breakdown = evaluator.get_component_breakdown(evaluated.task_id)
    print(f"分量分解: {breakdown}")
    assert breakdown is not None

    print("\n公式化评估器测试通过!")
    return True


def test_ucb_selector():
    """测试UCB选择器"""
    print("\n" + "=" * 60)
    print("测试: UCB选择器")
    print("=" * 60)

    selector = UCBTaskSelector(exploration_constant=1.414)
    selector.initialize({})

    # 创建候选任务
    candidates = [
        TaskCandidate(task_id="task1", action="explore", params={}),
        TaskCandidate(task_id="task2", action="exploit", params={}),
        TaskCandidate(task_id="task3", action="maintain", params={}),
    ]

    # 第一次选择：应该优先选择未执行过的
    selected = selector.select(candidates, exploration_rate=0.1)
    print(f"第一次选择: {selected.action} ({selected.task_id})")

    # 模拟多次选择
    for i in range(20):
        selected = selector.select(candidates, exploration_rate=0.1)
        # 更新得分
        score = 0.8 if selected.task_id == "task1" else 0.5
        selector.update_score(selected.task_id, score)

    print(f"20轮后统计:")
    state = selector.get_state()
    print(f"  总选择次数: {state['total_selections']}")
    print(f"  不同任务数: {state['unique_tasks']}")

    assert state['total_selections'] == 21  # 1 + 20

    print("\nUCB选择器测试通过!")
    return True


def test_ucb_exploration():
    """测试UCB探索行为"""
    print("\n" + "=" * 60)
    print("测试: UCB探索行为")
    print("=" * 60)

    selector = UCBTaskSelector(exploration_constant=2.0)
    selector.initialize({})

    # 创建两个任务，一个高得分但已选多次，一个低得分但未选
    candidates = [
        TaskCandidate(task_id="good", action="good_action", params={}),
        TaskCandidate(task_id="new", action="new_action", params={}),
    ]

    # 先多次选择good任务
    for _ in range(10):
        selected = selector.select(candidates, exploration_rate=0.1)
        selector.update_score(selected.task_id, 0.9)

    # 再选择时，new任务应因探索项而被选中
    selected = selector.select(candidates, exploration_rate=0.5)
    print(f"高探索率下选择: {selected.task_id}")

    # 低探索率下应选good
    selected = selector.select(candidates, exploration_rate=0.01)
    print(f"低探索率下选择: {selected.task_id}")

    print("\nUCB探索行为测试通过!")
    return True


def test_message_handling():
    """测试消息处理"""
    print("\n" + "=" * 60)
    print("测试: 消息处理")
    print("=" * 60)

    from self_evolving_agent.core.interfaces import AgentMessage, MessageType

    evaluator = FormulaTaskEvaluator()
    evaluator.initialize({})

    msg = AgentMessage(
        msg_type=MessageType.TASK_CANDIDATE,
        source="test",
        payload={
            "candidates": [
                {"task_id": "t1", "action": "a1", "params": {"gap": 0.5}},
                {"task_id": "t2", "action": "a2", "params": {"gap": 0.8}},
            ],
            "state": {"cpu_usage": 0.3, "uncertainty": 0.4},
        }
    )

    response = evaluator.handle_message(msg)
    assert response is not None
    assert response.msg_type == MessageType.TASK_CANDIDATE
    evaluated = response.payload.get("evaluated_candidates", [])
    print(f"评估了 {len(evaluated)} 个候选任务")
    for e in evaluated:
        print(f"  {e['action']}: score={e['score']:.3f}")

    print("\n消息处理测试通过!")
    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("阶段16: 任务评估公式化 — 验证测试")
    print("=" * 60)

    tests = [
        ("评估分量", test_evaluation_components),
        ("公式化评估器", test_formula_evaluator),
        ("UCB选择器", test_ucb_selector),
        ("UCB探索行为", test_ucb_exploration),
        ("消息处理", test_message_handling),
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
