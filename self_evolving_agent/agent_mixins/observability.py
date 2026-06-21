"""可观测性Mixin — 阶段149从agent.py拆分"""

from typing import Any, Callable, Dict, List, Optional

from ..core.observability import (
    LogLevel, LogRecord, HealthCheckResult, AlertSeverity, Alert, TraceSpan,
)


class ObservabilityMixin:
    """可观测性接口（阶段132）"""

    def log(self, level: LogLevel, message: str, **fields) -> None:
        """记录日志（阶段132新增）"""
        self._observability.log_event(level, message, **fields)

    def get_logs(self, level: Optional[LogLevel] = None, limit: int = 100) -> List[LogRecord]:
        """获取日志（阶段132新增）"""
        return self._observability.logger.get_records(level=level, limit=limit)

    def get_observability_dashboard(self) -> Dict[str, Any]:
        """获取可观测性仪表板（阶段132新增）"""
        return self._observability.dashboard()

    def check_health(self) -> Dict[str, Any]:
        """健康检查（阶段132新增）"""
        return self._observability.check_health()

    def add_health_check(self, name: str, check_fn: Callable[[], HealthCheckResult]) -> None:
        """添加健康检查项（阶段132新增）"""
        self._observability.health_checker.register_check(name, check_fn)

    def trigger_alert(
        self,
        name: str,
        severity: AlertSeverity,
        message: str,
        **details,
    ) -> Alert:
        """触发告警（阶段132新增）"""
        return self._observability.alert_manager.trigger_alert(
            name, severity, message, **details
        )

    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警（阶段132新增）"""
        return self._observability.alert_manager.get_active_alerts()

    def start_trace(self, name: str, **tags) -> TraceSpan:
        """开始追踪（阶段132新增）"""
        return self._observability.start_span(name, **tags)
