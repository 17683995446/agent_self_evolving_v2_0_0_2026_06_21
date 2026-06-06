"""
阶段20验证：消息序列化协议
"""
import sys
sys.path.insert(0, '/workspace')

from datetime import datetime
from self_evolving_agent.core.interfaces import AgentMessage, MessageType, MessagePriority
from self_evolving_agent.core.serialization import (
    JSONSerializer, BinarySerializer, MessageSerializer,
    SerializationFormat, SerializationError
)


def create_test_message() -> AgentMessage:
    """创建测试消息"""
    return AgentMessage(
        msg_id="test-123",
        msg_type=MessageType.STATE_UPDATE,
        source="predictor",
        target="drive_engine",
        payload={"state": {"value": 0.5}, "cycle": 42},
        timestamp=datetime.now(),
        priority=MessagePriority.HIGH,
    )


def test_json_serialize():
    """测试JSON序列化"""
    print("=" * 60)
    print("测试: JSON序列化")
    print("=" * 60)

    msg = create_test_message()
    json_str = JSONSerializer.serialize(msg)
    print(f"序列化后: {json_str[:80]}...")

    # 反序列化
    msg2 = JSONSerializer.deserialize(json_str)
    assert msg2.source == msg.source
    assert msg2.msg_type == msg.msg_type
    assert msg2.payload == msg.payload
    print(f"反序列化: source={msg2.source}, type={msg2.msg_type.name}")

    print("\nJSON序列化测试通过!")
    return True


def test_binary_serialize():
    """测试二进制序列化"""
    print("\n" + "=" * 60)
    print("测试: 二进制序列化")
    print("=" * 60)

    msg = create_test_message()
    binary_data = BinarySerializer.serialize(msg)
    print(f"序列化后: {len(binary_data)} bytes")

    # 反序列化
    msg2 = BinarySerializer.deserialize(binary_data)
    assert msg2.source == msg.source
    assert msg2.msg_type == msg.msg_type
    assert msg2.payload == msg.payload
    print(f"反序列化: source={msg2.source}, type={msg2.msg_type.name}")

    print("\n二进制序列化测试通过!")
    return True


def test_size_comparison():
    """比较序列化大小"""
    print("\n" + "=" * 60)
    print("测试: 序列化大小比较")
    print("=" * 60)

    msg = create_test_message()

    json_size = len(JSONSerializer.serialize(msg).encode('utf-8'))
    binary_size = len(BinarySerializer.serialize(msg))

    print(f"JSON大小: {json_size} bytes")
    print(f"Binary大小: {binary_size} bytes")
    print(f"压缩比: {binary_size / json_size * 100:.1f}%")

    assert binary_size < json_size  # 二进制应更紧凑

    print("\n大小比较测试通过!")
    return True


def test_version_compatibility():
    """测试版本兼容性"""
    print("\n" + "=" * 60)
    print("测试: 版本兼容性")
    print("=" * 60)

    # 模拟旧版本消息（缺少某些字段）
    old_json = '{"msg_type": "STATE_UPDATE", "source": "old_module", "payload": {}}'
    msg = JSONSerializer.deserialize(old_json)
    assert msg.source == "old_module"
    assert msg.priority == MessagePriority.NORMAL  # 默认值
    print(f"旧版本消息: source={msg.source}, priority={msg.priority.name}")

    # 模拟新版本消息（有额外字段）
    new_json = '{"version": "2.0.0", "msg_type": "STATE_UPDATE", "source": "new_module", "payload": {}, "extra_field": "ignored"}'
    msg2 = JSONSerializer.deserialize(new_json)
    assert msg2.source == "new_module"
    print(f"新版本消息: source={msg2.source}, version={msg2.version}")

    print("\n版本兼容性测试通过!")
    return True


def test_invalid_data():
    """测试无效数据处理"""
    print("\n" + "=" * 60)
    print("测试: 无效数据处理")
    print("=" * 60)

    # 无效JSON
    try:
        JSONSerializer.deserialize("invalid json")
        assert False, "应抛出异常"
    except SerializationError:
        print("无效JSON正确抛出异常")

    # 无效二进制
    try:
        BinarySerializer.deserialize(b"too short")
        assert False, "应抛出异常"
    except SerializationError:
        print("无效二进制正确抛出异常")

    # 未知消息类型
    unknown_json = '{"msg_type": "UNKNOWN_TYPE", "source": "test", "payload": {}}'
    msg = JSONSerializer.deserialize(unknown_json)
    assert msg.msg_type == MessageType.SYSTEM_EVENT  # 回退到默认值
    print(f"未知类型回退: {msg.msg_type.name}")

    print("\n无效数据处理测试通过!")
    return True


def test_message_serializer():
    """测试统一序列化器"""
    print("\n" + "=" * 60)
    print("测试: 统一序列化器")
    print("=" * 60)

    serializer = MessageSerializer(default_format=SerializationFormat.JSON)

    msg = create_test_message()

    # JSON序列化
    serialized = serializer.serialize(msg, SerializationFormat.JSON)
    assert serialized.format == SerializationFormat.JSON
    print(f"JSON: {serialized.size} bytes")

    msg2 = serializer.deserialize(serialized)
    assert msg2.source == msg.source

    # Binary序列化
    serialized2 = serializer.serialize(msg, SerializationFormat.BINARY)
    assert serialized2.format == SerializationFormat.BINARY
    print(f"Binary: {serialized2.size} bytes")

    msg3 = serializer.deserialize(serialized2)
    assert msg3.source == msg.source

    print("\n统一序列化器测试通过!")
    return True


def test_batch_serialization():
    """测试批量序列化"""
    print("\n" + "=" * 60)
    print("测试: 批量序列化")
    print("=" * 60)

    serializer = MessageSerializer()

    messages = [
        AgentMessage(msg_type=MessageType.STATE_UPDATE, source=f"module_{i}", payload={"value": i})
        for i in range(5)
    ]

    # JSON批量
    batch_json = serializer.serialize_batch(messages, SerializationFormat.JSON)
    print(f"JSON批量: {batch_json.size} bytes")

    # Binary批量
    batch_binary = serializer.serialize_batch(messages, SerializationFormat.BINARY)
    print(f"Binary批量: {batch_binary.size} bytes")

    print("\n批量序列化测试通过!")
    return True


def test_stats():
    """测试统计信息"""
    print("\n" + "=" * 60)
    print("测试: 统计信息")
    print("=" * 60)

    serializer = MessageSerializer()
    stats = serializer.get_stats()
    print(f"统计: {stats}")
    assert "default_format" in stats
    assert "supported_formats" in stats

    print("\n统计信息测试通过!")
    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("阶段20: 消息序列化协议 — 验证测试")
    print("=" * 60)

    tests = [
        ("JSON序列化", test_json_serialize),
        ("二进制序列化", test_binary_serialize),
        ("大小比较", test_size_comparison),
        ("版本兼容性", test_version_compatibility),
        ("无效数据", test_invalid_data),
        ("统一序列化器", test_message_serializer),
        ("批量序列化", test_batch_serialization),
        ("统计信息", test_stats),
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
