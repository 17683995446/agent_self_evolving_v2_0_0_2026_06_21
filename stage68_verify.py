"""
阶段68验证: 告警管理接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("am", "/workspace/self_evolving_agent/core/alert_manager.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["am"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段68验证: 告警管理接口标准化")
print("=" * 60)

# 测试1: 注册规则和触发告警
def test_trigger_alert():
    manager = mod.create_alert_manager()
    rule = mod.create_alert_rule(
        "r1", "CPU高",
        condition=lambda m: m.get("cpu", 0) > 80,
        severity=mod.AlertSeverity.HIGH,
        message_template="CPU使用率: {cpu}%",
        cooldown_sec=0,
    )
    manager.register_rule(rule)

    channel = mod.create_notification_channel("ch1", "email")
    manager.register_channel(channel)

    alert = manager.evaluate("r1", {"cpu": 90})
    assert alert is not None
    assert alert.severity == mod.AlertSeverity.HIGH
    assert "90" in alert.message
    assert alert.status == mod.AlertStatus.FIRING
    print("  [test_trigger_alert] 触发告警 OK")

# 测试2: 条件不满足不触发
def test_no_trigger():
    manager = mod.create_alert_manager()
    rule = mod.create_alert_rule(
        "r1", "CPU高",
        condition=lambda m: m.get("cpu", 0) > 80,
        severity=mod.AlertSeverity.HIGH,
        message_template="CPU: {cpu}%",
        cooldown_sec=0,
    )
    manager.register_rule(rule)

    alert = manager.evaluate("r1", {"cpu": 50})
    assert alert is None
    print("  [test_no_trigger] 不触发 OK")

# 测试3: 冷却期
def test_cooldown():
    manager = mod.create_alert_manager()
    rule = mod.create_alert_rule(
        "r1", "CPU高",
        condition=lambda m: True,
        severity=mod.AlertSeverity.HIGH,
        message_template="alert",
        cooldown_sec=60,
    )
    manager.register_rule(rule)

    alert1 = manager.evaluate("r1", {})
    assert alert1 is not None
    alert2 = manager.evaluate("r1", {})
    assert alert2 is None  # 冷却期内
    print("  [test_cooldown] 冷却期 OK")

# 测试4: 解决告警
def test_resolve():
    manager = mod.create_alert_manager()
    rule = mod.create_alert_rule(
        "r1", "CPU高",
        condition=lambda m: True,
        severity=mod.AlertSeverity.HIGH,
        message_template="alert",
        cooldown_sec=0,
    )
    manager.register_rule(rule)
    alert = manager.evaluate("r1", {})

    assert manager.resolve(alert.alert_id) is True
    assert alert.status == mod.AlertStatus.RESOLVED
    assert alert.resolved_at is not None
    print("  [test_resolve] 解决告警 OK")

# 测试5: 静默告警
def test_silence():
    manager = mod.create_alert_manager()
    rule = mod.create_alert_rule(
        "r1", "CPU高",
        condition=lambda m: True,
        severity=mod.AlertSeverity.HIGH,
        message_template="alert",
        cooldown_sec=0,
    )
    manager.register_rule(rule)
    alert = manager.evaluate("r1", {})

    assert manager.silence(alert.alert_id) is True
    assert alert.status == mod.AlertStatus.SILENCED
    print("  [test_silence] 静默告警 OK")

# 测试6: 通知渠道
def test_notification_channel():
    channel = mod.create_notification_channel("ch1", "email")
    alert = mod.Alert(
        alert_id="a1",
        rule_id="r1",
        severity=mod.AlertSeverity.CRITICAL,
        message="test",
        timestamp=0,
    )
    channel.send(alert)
    notifications = channel.get_notifications()
    assert len(notifications) == 1
    assert notifications[0]["severity"] == "critical"
    print("  [test_notification_channel] 通知渠道 OK")

# 测试7: 统计信息
def test_stats():
    manager = mod.create_alert_manager()
    rule = mod.create_alert_rule("r1", "Test", lambda m: True, mod.AlertSeverity.LOW, "msg", cooldown_sec=0)
    manager.register_rule(rule)
    manager.register_channel(mod.create_notification_channel("ch1", "email"))
    manager.evaluate("r1", {})

    stats = manager.get_stats()
    assert stats["total_rules"] == 1
    assert stats["total_alerts"] == 1
    assert stats["firing"] == 1
    assert "ch1" in stats["channels"]
    print("  [test_stats] 统计信息 OK")

if __name__ == "__main__":
    test_trigger_alert()
    test_no_trigger()
    test_cooldown()
    test_resolve()
    test_silence()
    test_notification_channel()
    test_stats()
    print("=" * 60)
    print("阶段68验证通过 ✓")
    print("=" * 60)
