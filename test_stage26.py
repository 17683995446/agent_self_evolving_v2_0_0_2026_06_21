"""
阶段26: 事件订阅发布规范化 — 验证测试

验证目标:
1. 事件类型可匹配通配符模式
2. 事件包含完整的追踪信息
3. 同步/异步投递正常工作
4. 订阅过滤和优先级排序正确
5. 事件可派生保持追踪链
6. 统计信息可观测
"""

import sys
import time
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.event_bus import (
    EventType, EventPriority, DeliveryMode, AgentEvent,
    EventBus, EventHandler, FunctionEventHandler,
    FilteringEventHandler, EventBuilder,
    StandardEvents,
)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print('='*60)


def test_event_type_matching():
    """测试事件类型匹配"""
    print_section("事件类型匹配")
    
    et = EventType("state", "updated")
    
    # 精确匹配
    assert et.matches("state.updated")
    print("精确匹配 state.updated: True")
    
    # Domain通配
    assert et.matches("state.*")
    print("Domain通配 state.*: True")
    
    # Action通配
    assert et.matches("*.updated")
    print("Action通配 *.updated: True")
    
    # 全通配
    assert et.matches("*.*")
    print("全通配 *.*: True")
    
    # 不匹配
    assert not et.matches("task.created")
    print("不匹配 task.created: False")
    
    # 不匹配（domain不同）
    assert not et.matches("task.*")
    print("不匹配 task.*: False")
    
    # 标准事件
    assert StandardEvents.STATE_UPDATED.matches("state.*")
    assert StandardEvents.TASK_COMPLETED.matches("*.completed")
    print("标准事件匹配: True")
    
    print("\n事件类型匹配测试通过!")
    return True


def test_event_creation():
    """测试事件创建"""
    print_section("事件创建")
    
    event = AgentEvent(
        event_type=StandardEvents.STATE_UPDATED,
        payload={"cpu": 0.5, "memory": 0.3},
        source="monitor",
        priority=EventPriority.HIGH,
    )
    
    assert event.event_type.full_name == "state.updated"
    assert event.source == "monitor"
    assert event.priority == EventPriority.HIGH
    assert "cpu" in event.payload
    assert len(event.event_id) == 8
    print(f"事件ID: {event.event_id}")
    print(f"事件类型: {event.event_type}")
    print(f"来源: {event.source}")
    print(f"优先级: {event.priority.name}")
    
    # 字典表示
    d = event.to_dict()
    assert d["type"] == "state.updated"
    assert d["source"] == "monitor"
    assert "timestamp" in d
    print(f"字典表示包含timestamp: True")
    
    print("\n事件创建测试通过!")
    return True


def test_event_derivation():
    """测试事件派生"""
    print_section("事件派生")
    
    original = AgentEvent(
        event_type=StandardEvents.TASK_CREATED,
        payload={"task_id": "abc"},
        source="task_system",
    )
    
    # 派生事件
    derived = original.derive(
        StandardEvents.TASK_COMPLETED,
        payload={"task_id": "abc", "result": "success"}
    )
    
    assert derived.event_type.full_name == "task.completed"
    assert derived.correlation_id == original.event_id
    assert derived.causation_id == original.event_id
    assert derived.source == original.source
    assert derived.priority == original.priority
    print(f"原始事件ID: {original.event_id}")
    print(f"派生事件关联ID: {derived.correlation_id}")
    print(f"派生事件因果ID: {derived.causation_id}")
    print(f"派生事件类型: {derived.event_type}")
    
    print("\n事件派生测试通过!")
    return True


def test_sync_publish():
    """测试同步发布"""
    print_section("同步发布")
    
    bus = EventBus()
    received = []
    
    handler = FunctionEventHandler(
        handler_fn=lambda e: received.append(e.event_type.full_name),
        event_pattern="state.*"
    )
    
    sub_id = bus.subscribe(handler, "state.*")
    print(f"订阅ID: {sub_id}")
    
    # 发布匹配事件
    event = AgentEvent(event_type=StandardEvents.STATE_UPDATED, source="test")
    results = bus.publish(event, mode=DeliveryMode.SYNC)
    
    assert len(received) == 1
    assert received[0] == "state.updated"
    print(f"同步发布: 处理器被调用")
    
    # 发布不匹配事件
    event2 = AgentEvent(event_type=StandardEvents.TASK_CREATED, source="test")
    bus.publish(event2, mode=DeliveryMode.SYNC)
    
    assert len(received) == 1  # 没有新增
    print(f"不匹配事件: 处理器未被调用")
    
    bus.clear()
    print("\n同步发布测试通过!")
    return True


def test_async_publish():
    """测试异步发布"""
    print_section("异步发布")
    
    bus = EventBus()
    received = []
    
    handler = FunctionEventHandler(
        handler_fn=lambda e: received.append(e.event_type.full_name),
        event_pattern="task.*"
    )
    
    bus.subscribe(handler, "task.*")
    bus.start()
    
    # 异步发布
    event = AgentEvent(event_type=StandardEvents.TASK_CREATED, source="test")
    bus.publish(event, mode=DeliveryMode.ASYNC)
    
    # 等待处理
    time.sleep(0.2)
    
    assert len(received) >= 1
    assert received[0] == "task.created"
    print(f"异步发布: 处理器被调用 ({len(received)} 次)")
    
    bus.stop()
    bus.clear()
    print("\n异步发布测试通过!")
    return True


def test_subscription_filter():
    """测试订阅过滤"""
    print_section("订阅过滤")
    
    bus = EventBus()
    high_priority_events = []
    
    # 只处理高优先级事件
    handler = FilteringEventHandler(
        handler_fn=lambda e: high_priority_events.append(e.event_type.full_name),
        event_pattern="*.*",
        filter_fn=lambda e: e.priority == EventPriority.HIGH
    )
    
    bus.subscribe(handler, "*.*")
    
    # 发布不同优先级事件
    bus.publish(AgentEvent(
        event_type=StandardEvents.STATE_UPDATED,
        priority=EventPriority.NORMAL,
        source="test"
    ), DeliveryMode.SYNC)
    
    bus.publish(AgentEvent(
        event_type=StandardEvents.ERROR_OCCURRED,
        priority=EventPriority.HIGH,
        source="test"
    ), DeliveryMode.SYNC)
    
    bus.publish(AgentEvent(
        event_type=StandardEvents.CONFIG_CHANGED,
        priority=EventPriority.LOW,
        source="test"
    ), DeliveryMode.SYNC)
    
    assert len(high_priority_events) == 1
    assert high_priority_events[0] == "error.occurred"
    print(f"过滤后只接收高优先级: {high_priority_events}")
    
    bus.clear()
    print("\n订阅过滤测试通过!")
    return True


def test_handler_priority():
    """测试处理器优先级"""
    print_section("处理器优先级")
    
    bus = EventBus()
    order = []
    
    # 低优先级处理器
    handler_low = FunctionEventHandler(
        handler_fn=lambda e: order.append("low"),
        event_pattern="*.*",
        priority=200
    )
    
    # 高优先级处理器
    handler_high = FunctionEventHandler(
        handler_fn=lambda e: order.append("high"),
        event_pattern="*.*",
        priority=10
    )
    
    # 默认优先级
    handler_normal = FunctionEventHandler(
        handler_fn=lambda e: order.append("normal"),
        event_pattern="*.*",
        priority=100
    )
    
    bus.subscribe(handler_low, "*.*")
    bus.subscribe(handler_high, "*.*")
    bus.subscribe(handler_normal, "*.*")
    
    event = AgentEvent(event_type=StandardEvents.STATE_UPDATED, source="test")
    bus.publish(event, mode=DeliveryMode.SYNC)
    
    assert order == ["high", "normal", "low"]
    print(f"处理顺序: {order}")
    
    bus.clear()
    print("\n处理器优先级测试通过!")
    return True


def test_unsubscribe():
    """测试取消订阅"""
    print_section("取消订阅")
    
    bus = EventBus()
    received = []
    
    handler = FunctionEventHandler(
        handler_fn=lambda e: received.append(1),
        event_pattern="*.*"
    )
    
    sub_id = bus.subscribe(handler, "*.*")
    
    # 发布一次
    bus.publish(AgentEvent(event_type=StandardEvents.STATE_UPDATED, source="test"), DeliveryMode.SYNC)
    assert len(received) == 1
    print(f"订阅时发布: 接收 {len(received)} 次")
    
    # 取消订阅
    result = bus.unsubscribe(sub_id)
    assert result == True
    print(f"取消订阅: {result}")
    
    # 再次发布
    bus.publish(AgentEvent(event_type=StandardEvents.STATE_UPDATED, source="test"), DeliveryMode.SYNC)
    assert len(received) == 1  # 没有新增
    print(f"取消后发布: 接收 {len(received)} 次")
    
    # 取消不存在的
    assert bus.unsubscribe("nonexistent") == False
    print("取消不存在的订阅: False")
    
    bus.clear()
    print("\n取消订阅测试通过!")
    return True


def test_event_builder():
    """测试事件构建器"""
    print_section("事件构建器")
    
    event = EventBuilder(StandardEvents.TASK_FAILED) \
        .with_payload(task_id="123", reason="timeout") \
        .from_source("executor") \
        .with_priority(EventPriority.HIGH) \
        .with_correlation("corr-456") \
        .caused_by("event-789") \
        .build()
    
    assert event.event_type.full_name == "task.failed"
    assert event.payload["task_id"] == "123"
    assert event.payload["reason"] == "timeout"
    assert event.source == "executor"
    assert event.priority == EventPriority.HIGH
    assert event.correlation_id == "corr-456"
    assert event.causation_id == "event-789"
    
    print(f"构建的事件: {event.to_dict()}")
    
    print("\n事件构建器测试通过!")
    return True


def test_event_bus_stats():
    """测试事件总线统计"""
    print_section("事件总线统计")
    
    bus = EventBus()
    
    # 初始状态
    stats = bus.get_stats()
    assert stats["subscriptions"] == 0
    assert stats["events_published"] == 0
    print(f"初始统计: {stats}")
    
    # 添加订阅并发布
    handler = FunctionEventHandler(lambda e: None, "*.*")
    bus.subscribe(handler, "*.*")
    
    bus.publish(AgentEvent(event_type=StandardEvents.STATE_UPDATED, source="test"), DeliveryMode.SYNC)
    bus.publish(AgentEvent(event_type=StandardEvents.TASK_CREATED, source="test"), DeliveryMode.SYNC)
    
    stats = bus.get_stats()
    assert stats["subscriptions"] == 1
    assert stats["events_published"] == 2
    assert stats["handlers_called"] == 2
    print(f"发布后统计: {stats}")
    
    bus.clear()
    print("\n事件总线统计测试通过!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("阶段26: 事件订阅发布规范化 — 验证测试")
    print("="*60)
    
    tests = [
        test_event_type_matching,
        test_event_creation,
        test_event_derivation,
        test_sync_publish,
        test_async_publish,
        test_subscription_filter,
        test_handler_priority,
        test_unsubscribe,
        test_event_builder,
        test_event_bus_stats,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"\n[失败] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("="*60)
