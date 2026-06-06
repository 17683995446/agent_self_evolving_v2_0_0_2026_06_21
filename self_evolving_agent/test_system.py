"""
自驱永续进化Agent系统 — 系统测试

验证所有模块的正确性和集成性
"""

import time
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from self_evolving_agent import create_default_agent


def test_basic_operation():
    """测试基本运行"""
    print("=" * 60)
    print("测试1: 基本运行测试")
    print("=" * 60)

    agent = create_default_agent()
    agent.start()

    # 运行5个周期
    time.sleep(5.5)

    state = agent.get_state()
    print(f"\n运行周期: {state['cycle_count']}")
    print(f"消息总线状态: {state['message_bus']}")

    agent.stop()
    print("\n测试1通过!")
    return True


def test_module_independence():
    """测试模块独立性"""
    print("\n" + "=" * 60)
    print("测试2: 模块独立性测试")
    print("=" * 60)

    agent = create_default_agent()
    agent.start()
    time.sleep(2)

    # 检查各模块状态
    state = agent.get_state()
    modules = state.get("modules", {})

    for name, module_state in modules.items():
        if module_state:
            print(f"\n模块 {name}:")
            print(f"  - 运行状态: {module_state.get('running', 'unknown')}")
            print(f"  - 初始化状态: {module_state.get('initialized', 'unknown')}")

    agent.stop()
    print("\n测试2通过!")
    return True


def test_message_bus():
    """测试消息总线"""
    print("\n" + "=" * 60)
    print("测试3: 消息总线测试")
    print("=" * 60)

    from self_evolving_agent.core.message_bus import LocalMessageBus
    from self_evolving_agent.core.interfaces import AgentMessage, MessageType

    bus = LocalMessageBus(async_mode=False)
    bus.start()

    received_messages = []

    def handler(msg):
        received_messages.append(msg.msg_type.name)

    bus.subscribe("test_module", [MessageType.STATE_UPDATE], handler)

    # 发送消息
    msg = AgentMessage(
        msg_type=MessageType.STATE_UPDATE,
        source="test",
        payload={"data": "test"},
    )
    bus.publish(msg)

    print(f"发送消息: {msg.msg_type.name}")
    print(f"接收消息: {received_messages}")

    bus.stop()

    assert len(received_messages) == 1
    print("\n测试3通过!")
    return True


def test_drive_engine():
    """测试驱力引擎"""
    print("\n" + "=" * 60)
    print("测试4: 驱力引擎测试")
    print("=" * 60)

    from self_evolving_agent.modules.drive_engine import UnifiedDriveEngine

    engine = UnifiedDriveEngine()
    engine.initialize({})

    # 测试正常状态
    normal_state = {
        "value": 0.5,
        "cpu_usage": 0.3,
        "memory_usage": 0.4,
        "task_completion_rate": 0.8,
        "uncertainty": 0.2,
    }
    gaps = engine.compute_all_gaps(normal_state)
    print(f"正常状态驱力缺口: safe={gaps.safe_gap:.3f}, gain={gaps.gain_gap:.3f}, eff={gaps.eff_gap:.3f}")
    assert gaps.validate()

    # 测试异常状态
    anomaly_state = {
        "value": 10.0,  # 异常值
        "cpu_usage": 0.9,
        "memory_usage": 0.9,
        "task_completion_rate": 0.3,
        "uncertainty": 0.8,
    }
    gaps = engine.compute_all_gaps(anomaly_state)
    print(f"异常状态驱力缺口: safe={gaps.safe_gap:.3f}, gain={gaps.gain_gap:.3f}, eff={gaps.eff_gap:.3f}")
    assert gaps.validate()

    print("\n测试4通过!")
    return True


def test_predictor():
    """测试预测器"""
    print("\n" + "=" * 60)
    print("测试5: 预测器测试")
    print("=" * 60)

    from self_evolving_agent.modules.predictor import LinearPredictor

    predictor = LinearPredictor("test_predictor", window_size=5)
    predictor.initialize({})

    # 生成线性数据
    import numpy as np
    for i in range(10):
        state = {"value": i * 0.1}
        pred = predictor.predict(state)
        print(f"输入: {state['value']:.1f}, 预测: {pred.predicted_state.get('value', 0):.3f}, 置信度: {pred.confidence:.3f}")

    print("\n测试5通过!")
    return True


def test_memory():
    """测试记忆系统"""
    print("\n" + "=" * 60)
    print("测试6: 记忆系统测试")
    print("=" * 60)

    from self_evolving_agent.modules.memory import MemoryCoordinator

    memory = MemoryCoordinator()
    memory.initialize({})

    # 存储数据
    memory.store("key1", "value1")
    memory.store("key2", "value2")
    memory.store("key3", "value3")

    # 检索
    data = memory.retrieve("key1")
    print(f"检索 key1: {data}")
    assert data == "value1"

    # 巩固
    memory.consolidate()
    print("记忆巩固完成")

    print("\n测试6通过!")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("自驱永续进化Agent系统 — 全面测试")
    print("=" * 60)

    tests = [
        ("消息总线", test_message_bus),
        ("驱力引擎", test_drive_engine),
        ("预测器", test_predictor),
        ("记忆系统", test_memory),
        ("基本运行", test_basic_operation),
        ("模块独立性", test_module_independence),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
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
