"""
阶段68: 告警管理接口标准化

第一性原理:
1. 异常必须被及时发现：问题越早发现，修复成本越低
2. 告警必须可分级：不是所有异常都需要立即处理
3. 告警必须可抑制：避免告警风暴

设计原则:
- Alert: 告警
- AlertRule: 告警规则
- AlertManager: 告警管理器
- NotificationChannel: 通知渠道
- 支持分级、抑制、聚合、自动恢复
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class AlertSeverity(Enum):
    """告警级别"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(Enum):
    """告警状态"""
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"


@dataclass
class Alert:
    """告警"""
    alert_id: str
    rule_id: str
    severity: AlertSeverity
    message: str
    timestamp: float
    status: AlertStatus = AlertStatus.FIRING
    labels: Dict[str, str] = field(default_factory=dict)
    resolved_at: Optional[float] = None


@dataclass
class AlertRule:
    """告警规则"""
    rule_id: str
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    severity: AlertSeverity
    message_template: str
    cooldown_sec: float = 300.0
    labels: Dict[str, str] = field(default_factory=dict)


# ============================================================
# 通知渠道
# ============================================================

class NotificationChannel:
    """通知渠道"""

    def __init__(self, channel_id: str, channel_type: str):
        self.channel_id = channel_id
        self.channel_type = channel_type
        self._notifications: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def send(self, alert: Alert) -> bool:
        """发送通知"""
        with self._lock:
            self._notifications.append({
                "alert_id": alert.alert_id,
                "severity": alert.severity.value,
                "message": alert.message,
                "timestamp": time.time(),
            })
        return True

    def get_notifications(self) -> List[Dict[str, Any]]:
        """获取通知历史"""
        with self._lock:
            return list(self._notifications)


# ============================================================
# 告警管理器
# ============================================================

class AlertManager:
    """
    告警管理器

    管理告警规则、告警状态和通知
    """

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._channels: Dict[str, NotificationChannel] = {}
        self._last_fired: Dict[str, float] = {}  # rule_id -> timestamp
        self._lock = threading.Lock()

    def register_rule(self, rule: AlertRule) -> None:
        """注册告警规则"""
        with self._lock:
            self._rules[rule.rule_id] = rule

    def register_channel(self, channel: NotificationChannel) -> None:
        """注册通知渠道"""
        with self._lock:
            self._channels[channel.channel_id] = channel

    def evaluate(self, rule_id: str, metrics: Dict[str, Any]) -> Optional[Alert]:
        """
        评估告警规则

        如果条件满足且冷却期已过，则触发告警
        """
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                return None

            # 检查冷却期
            last_fired = self._last_fired.get(rule_id, 0)
            if time.time() - last_fired < rule.cooldown_sec:
                return None

            # 评估条件
            if not rule.condition(metrics):
                return None

            # 创建告警
            alert_id = f"alert_{rule_id}_{int(time.time())}"
            alert = Alert(
                alert_id=alert_id,
                rule_id=rule_id,
                severity=rule.severity,
                message=rule.message_template.format(**metrics),
                timestamp=time.time(),
                labels=dict(rule.labels),
            )

            self._alerts[alert_id] = alert
            self._last_fired[rule_id] = alert.timestamp

            # 发送通知
            for channel in self._channels.values():
                channel.send(alert)

            return alert

    def resolve(self, alert_id: str) -> bool:
        """解决告警"""
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert is None:
                return False
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = time.time()
            return True

    def silence(self, alert_id: str) -> bool:
        """静默告警"""
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert is None:
                return False
            alert.status = AlertStatus.SILENCED
            return True

    def get_alerts(self, status_filter: Optional[AlertStatus] = None) -> List[Alert]:
        """获取告警列表"""
        with self._lock:
            alerts = list(self._alerts.values())
            if status_filter:
                alerts = [a for a in alerts if a.status == status_filter]
            return alerts

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "total_rules": len(self._rules),
                "total_alerts": len(self._alerts),
                "firing": sum(1 for a in self._alerts.values() if a.status == AlertStatus.FIRING),
                "resolved": sum(1 for a in self._alerts.values() if a.status == AlertStatus.RESOLVED),
                "channels": list(self._channels.keys()),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_alert_manager() -> AlertManager:
    """创建告警管理器"""
    return AlertManager()


def create_alert_rule(
    rule_id: str,
    name: str,
    condition: Callable[[Dict[str, Any]], bool],
    severity: AlertSeverity,
    message_template: str,
    cooldown_sec: float = 300.0,
) -> AlertRule:
    """创建告警规则"""
    return AlertRule(
        rule_id=rule_id,
        name=name,
        condition=condition,
        severity=severity,
        message_template=message_template,
        cooldown_sec=cooldown_sec,
    )


def create_notification_channel(channel_id: str, channel_type: str) -> NotificationChannel:
    """创建通知渠道"""
    return NotificationChannel(channel_id=channel_id, channel_type=channel_type)
