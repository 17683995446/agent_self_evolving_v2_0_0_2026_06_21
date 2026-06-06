"""
阶段11验证：预测编码算法精细化
"""
import sys
import os
sys.path.insert(0, '/workspace')

import numpy as np
from self_evolving_agent.modules.predictive_coding import (
    PredictiveCodingLayer, HierarchicalPredictiveCoder, ConvergenceStatus
)


def test_predictive_coding_layer():
    """测试单层预测编码"""
    print("=" * 60)
    print("测试: 单层预测编码")
    print("=" * 60)

    layer = PredictiveCodingLayer("test_layer", input_dim=3, learning_rate=0.01)

    # 测试前向预测
    state = np.array([1.0, 0.5, -0.3])
    prediction = layer.forward_prediction(state)
    print(f"输入状态: {state}")
    print(f"预测输出: {prediction}")
    assert prediction is not None
    assert len(prediction) == 3

    # 测试反向误差
    actual = np.array([1.1, 0.4, -0.2])
    error = layer.backward_error(actual, prediction)
    print(f"实际状态: {actual}")
    print(f"预测误差: {error}")
    assert len(error) == 3

    # 测试参数更新
    stats = layer.update_parameters(state, error)
    print(f"参数更新统计: {stats}")
    assert "weight_change" in stats

    # 测试收敛检测（数据不足时应未收敛）
    status = layer.check_convergence()
    print(f"收敛状态: converged={status.converged}, stability={status.stability_score:.3f}")
    assert isinstance(status, ConvergenceStatus)

    # 模拟多次迭代直到收敛
    print("\n模拟训练过程...")
    for i in range(50):
        pred = layer.forward_prediction(state)
        # 目标：学习恒等映射
        err = layer.backward_error(state, pred)
        layer.update_parameters(state, err)
        status = layer.check_convergence()
        if status.converged:
            print(f"第 {i+1} 次迭代后收敛！")
            print(f"最终误差: {status.final_error:.6f}")
            print(f"稳定性评分: {status.stability_score:.3f}")
            break

    print("\n单层预测编码测试通过!")
    return True


def test_hierarchical_predictive_coder():
    """测试层级预测编码器"""
    print("\n" + "=" * 60)
    print("测试: 层级预测编码器")
    print("=" * 60)

    coder = HierarchicalPredictiveCoder(
        "test_hpc",
        layer_dims=[3, 4, 2],
        learning_rate=0.01
    )
    coder.initialize({})

    # 测试预测
    state = {"value1": 1.0, "value2": 0.5, "value3": -0.3}
    prediction = coder.predict(state)
    print(f"输入状态: {state}")
    print(f"预测结果: {prediction.predicted_state}")
    print(f"置信度: {prediction.confidence:.3f}")
    print(f"不确定性: {prediction.uncertainty:.3f}")
    assert prediction.predicted_state is not None

    # 测试更新
    actual_state = {"value1": 1.1, "value2": 0.4, "value3": -0.2}
    coder.update(actual_state, prediction.predicted_state)
    print(f"\n更新后的模型状态:")
    model_state = coder.get_model_state()
    print(f"  层数: {model_state['num_layers']}")
    for layer_info in model_state['layers']:
        print(f"  {layer_info['layer_id']}: dim={layer_info['input_dim']}, "
              f"converged={layer_info['convergence']['converged']}")

    # 多次预测-更新循环
    print("\n模拟在线学习...")
    for i in range(20):
        pred = coder.predict(state)
        coder.update(state, pred.predicted_state)

    final_state = coder.get_model_state()
    print(f"训练后预测历史大小: {final_state['prediction_history_size']}")

    print("\n层级预测编码器测试通过!")
    return True


def test_message_handling():
    """测试消息处理"""
    print("\n" + "=" * 60)
    print("测试: 消息处理")
    print("=" * 60)

    from self_evolving_agent.core.interfaces import AgentMessage, MessageType

    coder = HierarchicalPredictiveCoder("msg_test")
    coder.initialize({})

    msg = AgentMessage(
        msg_type=MessageType.STATE_UPDATE,
        source="test",
        payload={"state": {"value": 0.5, "cpu": 0.3}}
    )

    response = coder.handle_message(msg)
    assert response is not None
    assert response.msg_type == MessageType.PREDICTION
    print(f"输入消息: STATE_UPDATE")
    print(f"输出消息: PREDICTION")
    print(f"预测内容: {response.payload['prediction']['predicted_state']}")

    print("\n消息处理测试通过!")
    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("阶段11: 预测编码算法精细化 — 验证测试")
    print("=" * 60)

    tests = [
        ("单层预测编码", test_predictive_coding_layer),
        ("层级预测编码器", test_hierarchical_predictive_coder),
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
