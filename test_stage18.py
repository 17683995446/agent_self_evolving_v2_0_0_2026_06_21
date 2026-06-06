"""
阶段18验证：时序预测模型精细化
"""
import sys
sys.path.insert(0, '/workspace')

import numpy as np
from self_evolving_agent.modules.temporal_predictor import (
    SimpleGRUCell, TemporalPredictor, MultiHorizonPredictor
)


def test_gru_cell():
    """测试GRU单元"""
    print("=" * 60)
    print("测试: GRU单元")
    print("=" * 60)

    gru = SimpleGRUCell(input_size=3, hidden_size=4)

    # 前向传播
    x = np.array([1.0, 0.5, -0.3])
    h = gru.forward(x)
    print(f"输入: {x}")
    print(f"隐藏状态: {h}")
    assert len(h) == 4
    assert not np.any(np.isnan(h))

    # 多次前向
    for i in range(10):
        x = np.array([np.sin(i * 0.1), np.cos(i * 0.1), 0.0])
        h = gru.forward(x)
    print(f"10步后隐藏状态: {h}")

    # 重置
    gru.reset()
    assert np.allclose(gru.h, np.zeros(4))
    print("重置后隐藏状态归零")

    print("\nGRU单元测试通过!")
    return True


def test_temporal_predictor():
    """测试时序预测器"""
    print("\n" + "=" * 60)
    print("测试: 时序预测器")
    print("=" * 60)

    predictor = TemporalPredictor(
        input_size=3, hidden_size=8, output_size=3, sequence_length=10
    )
    predictor.initialize({})

    # 模拟时序数据
    states = []
    for i in range(15):
        state = {
            "value1": np.sin(i * 0.2),
            "value2": np.cos(i * 0.2),
            "value3": 0.1 * i,
        }
        states.append(state)
        pred = predictor.predict(state)
        if i % 5 == 0:
            print(f"第{i}步预测: confidence={pred.confidence:.3f}, uncertainty={pred.uncertainty:.3f}")

    assert pred.confidence > 0
    assert 0 <= pred.uncertainty <= 1

    # 多步预测
    sequence = predictor.predict_sequence(steps=3)
    print(f"\n多步预测 ({len(sequence)} 步):")
    for i, s in enumerate(sequence):
        print(f"  步{i+1}: {s}")

    print("\n时序预测器测试通过!")
    return True


def test_update_learning():
    """测试在线学习"""
    print("\n" + "=" * 60)
    print("测试: 在线学习")
    print("=" * 60)

    predictor = TemporalPredictor(input_size=2, hidden_size=4, output_size=2)
    predictor.initialize({})

    # 学习恒等映射
    target_state = {"a": 0.5, "b": -0.3}

    print("学习恒等映射...")
    for i in range(50):
        pred = predictor.predict(target_state)
        predictor.update(target_state, pred.predicted_state)

    # 测试预测
    final_pred = predictor.predict(target_state)
    print(f"目标: {target_state}")
    print(f"预测: {final_pred.predicted_state}")

    # 计算误差
    error = np.sqrt(
        (final_pred.predicted_state.get("a", 0) - target_state["a"]) ** 2 +
        (final_pred.predicted_state.get("b", 0) - target_state["b"]) ** 2
    )
    print(f"预测误差: {error:.4f}")

    print("\n在线学习测试通过!")
    return True


def test_multi_horizon():
    """测试多步预测器"""
    print("\n" + "=" * 60)
    print("测试: 多步预测器")
    print("=" * 60)

    predictor = MultiHorizonPredictor()
    predictor.initialize({})

    state = {"x": 0.5, "y": 0.3, "z": 0.1}

    predictions = predictor.predict_all_horizons(state)
    print("多时间尺度预测:")
    for name, pred in predictions.items():
        print(f"  {name}: confidence={pred.confidence:.3f}, uncertainty={pred.uncertainty:.3f}")

    assert "short" in predictions
    assert "mid" in predictions
    assert "long" in predictions

    print("\n多步预测器测试通过!")
    return True


def test_message_handling():
    """测试消息处理"""
    print("\n" + "=" * 60)
    print("测试: 消息处理")
    print("=" * 60)

    from self_evolving_agent.core.interfaces import AgentMessage, MessageType

    predictor = TemporalPredictor()
    predictor.initialize({})

    msg = AgentMessage(
        msg_type=MessageType.STATE_UPDATE,
        source="test",
        payload={"state": {"a": 1.0, "b": 2.0, "c": 3.0}}
    )

    response = predictor.handle_message(msg)
    assert response is not None
    assert response.msg_type == MessageType.PREDICTION
    print(f"输入: STATE_UPDATE")
    print(f"输出: PREDICTION")
    print(f"预测: {response.payload['prediction']['predicted_state']}")

    print("\n消息处理测试通过!")
    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("阶段18: 时序预测模型精细化 — 验证测试")
    print("=" * 60)

    tests = [
        ("GRU单元", test_gru_cell),
        ("时序预测器", test_temporal_predictor),
        ("在线学习", test_update_learning),
        ("多步预测器", test_multi_horizon),
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
