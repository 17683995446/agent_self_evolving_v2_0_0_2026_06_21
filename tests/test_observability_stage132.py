"""
阶段132: 可观测性增强层 — 专项测试

测试覆盖：
1. StructuredLogger: 日志记录、级别过滤、处理器
2. LoggerRegistry: 日志器注册表
3. MetricsCollector: 计数器、仪表、直方图
4. Tracer: 分布式追踪
5. HealthChecker: 健康检查
6. AlertManager: 告警管理
7. ObservabilityManager: 集成管理器
8. Agent集成
9. 并发安全
10. 异常容错
11. 第一性原理验证
"""

import time
import threading
import json
import pytest
from unittest.mock import MagicMock

from self_evolving_agent.core.observability import (
    LogLevel,
    LogRecord,
    StructuredLogger,
    LoggerRegistry,
    get_logger,
    MetricType,
    Metric,
    MetricsCollector,
    TraceSpan,
    Tracer,
    HealthStatus,
    HealthCheckResult,
    HealthChecker,
    AlertSeverity,
    Alert,
    AlertRule,
    AlertManager,
    ObservabilityManager,
    create_observability_manager,
)


# ============================================================
# 结构化日志测试
# ============================================================

class TestStructuredLogger:
    """结构化日志器测试"""

    def test_basic_logging(self):
        """测试基本日志"""
        logger = StructuredLogger("test")
        logger.info("hello")
        records = logger.get_records()
        assert len(records) == 1
        assert records[0].message == "hello"
        assert records[0].level == LogLevel.INFO

    def test_log_levels(self):
        """测试日志级别"""
        logger = StructuredLogger("test", level=LogLevel.WARNING)
        logger.debug("debug")  # 应被过滤
        logger.info("info")    # 应被过滤
        logger.warning("warn") # 应记录
        logger.error("error")  # 应记录
        records = logger.get_records()
        assert len(records) == 2

    def test_structured_fields(self):
        """测试结构化字段"""
        logger = StructuredLogger("test")
        logger.info("user action", user_id=123, action="login")
        records = logger.get_records()
        assert records[0].fields["user_id"] == 123
        assert records[0].fields["action"] == "login"

    def test_exception_logging(self):
        """测试异常日志"""
        logger = StructuredLogger("test")
        try:
            raise ValueError("test error")
        except ValueError as e:
            logger.error("operation failed", exception=e)
        records = logger.get_records()
        assert records[0].exception is not None
        assert "ValueError" in records[0].exception

    def test_log_level_methods(self):
        """测试各级别方法"""
        logger = StructuredLogger("test", level=LogLevel.DEBUG)
        logger.debug("d")
        logger.info("i")
        logger.warning("w")
        logger.error("e")
        logger.critical("c")
        records = logger.get_records()
        assert len(records) == 5
        levels = [r.level for r in records]
        assert LogLevel.DEBUG in levels
        assert LogLevel.CRITICAL in levels

    def test_handler(self):
        """测试日志处理器"""
        logger = StructuredLogger("test")
        received = []
        logger.add_handler(lambda r: received.append(r))
        logger.info("test")
        assert len(received) == 1

    def test_get_records_with_level_filter(self):
        """测试按级别获取记录"""
        logger = StructuredLogger("test", level=LogLevel.DEBUG)
        logger.debug("d")
        logger.warning("w")
        logger.error("e")
        warnings_and_above = logger.get_records(level=LogLevel.WARNING)
        assert len(warnings_and_above) == 2

    def test_get_records_with_limit(self):
        """测试限制返回数量"""
        logger = StructuredLogger("test")
        for i in range(10):
            logger.info(f"msg_{i}")
        records = logger.get_records(limit=3)
        assert len(records) == 3

    def test_stats(self):
        """测试统计"""
        logger = StructuredLogger("test")
        logger.info("a")
        logger.warning("b")
        logger.error("c")
        stats = logger.get_stats()
        assert stats["total_records"] == 3
        assert stats["counters"]["INFO"] == 1
        assert stats["counters"]["WARNING"] == 1
        assert stats["counters"]["ERROR"] == 1

    def test_clear(self):
        """测试清空"""
        logger = StructuredLogger("test")
        logger.info("a")
        logger.clear()
        assert len(logger.get_records()) == 0

    def test_set_level(self):
        """测试设置级别"""
        logger = StructuredLogger("test", level=LogLevel.ERROR)
        logger.info("should not log")
        assert len(logger.get_records()) == 0
        logger.set_level(LogLevel.DEBUG)
        logger.info("should log now")
        assert len(logger.get_records()) == 1

    def test_to_json(self):
        """测试JSON序列化"""
        logger = StructuredLogger("test")
        logger.info("test", key="value")
        records = logger.get_records()
        json_str = records[0].to_json()
        data = json.loads(json_str)
        assert data["message"] == "test"
        assert data["fields"]["key"] == "value"

    def test_handler_exception_isolation(self):
        """测试处理器异常隔离"""
        logger = StructuredLogger("test")

        def bad_handler(r):
            raise RuntimeError("handler error")

        logger.add_handler(bad_handler)
        # 不应崩溃
        logger.info("test")


# ============================================================
# 日志器注册表测试
# ============================================================

class TestLoggerRegistry:
    """日志器注册表测试"""

    def test_get_logger(self):
        """测试获取日志器"""
        logger1 = LoggerRegistry.get_logger("test_logger")
        logger2 = LoggerRegistry.get_logger("test_logger")
        assert logger1 is logger2  # 同一实例

    def test_get_different_loggers(self):
        """测试获取不同日志器"""
        logger1 = LoggerRegistry.get_logger("logger_a")
        logger2 = LoggerRegistry.get_logger("logger_b")
        assert logger1 is not logger2

    def test_get_all_loggers(self):
        """测试获取所有日志器"""
        LoggerRegistry.get_logger("test_all_1")
        LoggerRegistry.get_logger("test_all_2")
        all_loggers = LoggerRegistry.get_all_loggers()
        assert "test_all_1" in all_loggers
        assert "test_all_2" in all_loggers

    def test_get_logger_helper(self):
        """测试便捷函数"""
        logger = get_logger("helper_test")
        assert logger is not None
        assert logger.name == "helper_test"


# ============================================================
# 指标收集器测试
# ============================================================

class TestMetricsCollector:
    """指标收集器测试"""

    def test_counter(self):
        """测试计数器"""
        metrics = MetricsCollector()
        metrics.counter("requests")
        metrics.counter("requests")
        metrics.counter("requests", 5)
        m = metrics.get_metric("requests")
        assert m.value == 7

    def test_counter_with_labels(self):
        """测试带标签的计数器"""
        metrics = MetricsCollector()
        metrics.counter("requests", endpoint="/api")
        metrics.counter("requests", endpoint="/api")
        metrics.counter("requests", endpoint="/web")
        api_metric = metrics.get_metric("requests", endpoint="/api")
        web_metric = metrics.get_metric("requests", endpoint="/web")
        assert api_metric.value == 2
        assert web_metric.value == 1

    def test_gauge(self):
        """测试仪表"""
        metrics = MetricsCollector()
        metrics.gauge("temperature", 23.5)
        m = metrics.get_metric("temperature")
        assert m.value == 23.5
        metrics.gauge("temperature", 24.0)
        m = metrics.get_metric("temperature")
        assert m.value == 24.0

    def test_histogram(self):
        """测试直方图"""
        metrics = MetricsCollector()
        for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
            metrics.histogram("latency", v)
        stats = metrics.get_histogram_stats("latency")
        assert stats["count"] == 5
        assert stats["avg"] == 3.0
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0

    def test_histogram_percentiles(self):
        """测试直方图百分位数"""
        metrics = MetricsCollector()
        for i in range(100):
            metrics.histogram("latency", float(i + 1))
        stats = metrics.get_histogram_stats("latency")
        assert stats["p50"] >= 49
        assert stats["p90"] >= 89

    def test_namespace(self):
        """测试命名空间"""
        metrics = MetricsCollector(namespace="myapp")
        metrics.counter("requests")
        m = metrics.get_metric("requests")
        assert m.name == "myapp.requests"

    def test_get_all_metrics(self):
        """测试获取所有指标"""
        metrics = MetricsCollector()
        metrics.counter("a")
        metrics.gauge("b", 1.0)
        all_metrics = metrics.get_all_metrics()
        assert len(all_metrics) == 2

    def test_export(self):
        """测试导出"""
        metrics = MetricsCollector(namespace="test")
        metrics.counter("requests")
        exported = metrics.export()
        assert exported["namespace"] == "test"
        assert len(exported["metrics"]) == 1

    def test_reset(self):
        """测试重置"""
        metrics = MetricsCollector()
        metrics.counter("a")
        metrics.gauge("b", 1.0)
        metrics.reset()
        assert len(metrics.get_all_metrics()) == 0

    def test_get_nonexistent_metric(self):
        """测试获取不存在的指标"""
        metrics = MetricsCollector()
        assert metrics.get_metric("nonexistent") is None

    def test_histogram_stats_empty(self):
        """测试空直方图统计"""
        metrics = MetricsCollector()
        assert metrics.get_histogram_stats("nonexistent") == {}


# ============================================================
# 追踪器测试
# ============================================================

class TestTracer:
    """追踪器测试"""

    def test_start_and_finish_span(self):
        """测试开始和结束跨度"""
        tracer = Tracer("test")
        span = tracer.start_span("operation")
        assert span.status == "active"
        span.finish()
        assert span.status == "finished"
        assert span.duration is not None

    def test_span_duration(self):
        """测试跨度持续时间"""
        tracer = Tracer("test")
        span = tracer.start_span("op")
        time.sleep(0.01)
        span.finish()
        assert span.duration >= 0.01

    def test_parent_child_spans(self):
        """测试父子跨度"""
        tracer = Tracer("test")
        parent = tracer.start_span("parent")
        child = tracer.start_span("child", trace_id=parent.trace_id, parent_span_id=parent.span_id)
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id

    def test_span_tags(self):
        """测试跨度标签"""
        tracer = Tracer("test")
        span = tracer.start_span("op")
        span.set_tag("user", "test")
        span.set_tag("count", 42)
        assert span.tags["user"] == "test"
        assert span.tags["count"] == 42

    def test_span_logs(self):
        """测试跨度日志"""
        tracer = Tracer("test")
        span = tracer.start_span("op")
        span.log("started")
        span.log("processing", item="test")
        assert len(span.logs) == 2
        assert span.logs[0]["message"] == "started"

    def test_span_error(self):
        """测试跨度错误"""
        tracer = Tracer("test")
        span = tracer.start_span("op")
        span.set_error()
        assert span.status == "error"
        assert span.end_time is not None

    def test_get_trace(self):
        """测试获取追踪"""
        tracer = Tracer("test")
        span1 = tracer.start_span("op1")
        span2 = tracer.start_span("op2", trace_id=span1.trace_id)
        trace = tracer.get_trace(span1.trace_id)
        assert len(trace) == 2

    def test_get_all_traces(self):
        """测试获取所有追踪"""
        tracer = Tracer("test")
        tracer.start_span("op1")
        tracer.start_span("op2")
        traces = tracer.get_all_traces()
        assert len(traces) == 2

    def test_stats(self):
        """测试统计"""
        tracer = Tracer("test")
        tracer.start_span("op1")
        tracer.start_span("op2")
        stats = tracer.stats()
        assert stats["total_spans"] == 2
        assert stats["total_traces"] == 2

    def test_clear(self):
        """测试清空"""
        tracer = Tracer("test")
        tracer.start_span("op")
        tracer.clear()
        assert tracer.stats()["total_spans"] == 0

    def test_trace_decorator(self):
        """测试追踪装饰器"""
        tracer = Tracer("test")

        @tracer.trace("decorated_op")
        def my_func():
            return 42

        result = my_func()
        assert result == 42
        assert tracer.stats()["total_spans"] == 1

    def test_trace_decorator_error(self):
        """测试追踪装饰器错误"""
        tracer = Tracer("test")

        @tracer.trace("failing_op")
        def failing_func():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            failing_func()

        traces = tracer.get_all_traces()
        span_data = traces[list(traces.keys())[0]][0]
        assert span_data["status"] == "error"


# ============================================================
# 健康检查器测试
# ============================================================

class TestHealthChecker:
    """健康检查器测试"""

    def test_register_and_run_check(self):
        """测试注册和运行检查"""
        checker = HealthChecker()
        checker.register_check("db", lambda: HealthCheckResult(
            name="db", status=HealthStatus.HEALTHY, message="OK"
        ))
        result = checker.run_check("db")
        assert result.status == HealthStatus.HEALTHY

    def test_run_nonexistent_check(self):
        """测试运行不存在的检查"""
        checker = HealthChecker()
        result = checker.run_check("nonexistent")
        assert result.status == HealthStatus.UNKNOWN

    def test_run_all(self):
        """测试运行所有检查"""
        checker = HealthChecker()
        checker.register_check("a", lambda: HealthCheckResult(
            name="a", status=HealthStatus.HEALTHY
        ))
        checker.register_check("b", lambda: HealthCheckResult(
            name="b", status=HealthStatus.HEALTHY
        ))
        results = checker.run_all()
        assert len(results) == 2

    def test_overall_status_healthy(self):
        """测试总体状态-健康"""
        checker = HealthChecker()
        checker.register_check("a", lambda: HealthCheckResult(
            name="a", status=HealthStatus.HEALTHY
        ))
        assert checker.get_overall_status() == HealthStatus.HEALTHY

    def test_overall_status_degraded(self):
        """测试总体状态-降级"""
        checker = HealthChecker()
        checker.register_check("a", lambda: HealthCheckResult(
            name="a", status=HealthStatus.HEALTHY
        ))
        checker.register_check("b", lambda: HealthCheckResult(
            name="b", status=HealthStatus.DEGRADED
        ))
        assert checker.get_overall_status() == HealthStatus.DEGRADED

    def test_overall_status_unhealthy(self):
        """测试总体状态-不健康"""
        checker = HealthChecker()
        checker.register_check("a", lambda: HealthCheckResult(
            name="a", status=HealthStatus.HEALTHY
        ))
        checker.register_check("b", lambda: HealthCheckResult(
            name="b", status=HealthStatus.UNHEALTHY
        ))
        assert checker.get_overall_status() == HealthStatus.UNHEALTHY

    def test_overall_status_empty(self):
        """测试总体状态-空"""
        checker = HealthChecker()
        assert checker.get_overall_status() == HealthStatus.UNKNOWN

    def test_check_exception(self):
        """测试检查异常"""
        checker = HealthChecker()

        def failing_check():
            raise RuntimeError("check failed")

        checker.register_check("failing", failing_check)
        result = checker.run_check("failing")
        assert result.status == HealthStatus.UNHEALTHY
        assert "check failed" in result.message.lower()

    def test_unregister_check(self):
        """测试注销检查"""
        checker = HealthChecker()
        checker.register_check("a", lambda: HealthCheckResult(
            name="a", status=HealthStatus.HEALTHY
        ))
        checker.unregister_check("a")
        assert "a" not in checker.list_checks()

    def test_list_checks(self):
        """测试列出检查项"""
        checker = HealthChecker()
        checker.register_check("a", lambda: HealthCheckResult(name="a", status=HealthStatus.HEALTHY))
        checker.register_check("b", lambda: HealthCheckResult(name="b", status=HealthStatus.HEALTHY))
        checks = checker.list_checks()
        assert "a" in checks
        assert "b" in checks

    def test_duration_tracking(self):
        """测试持续时间跟踪"""
        checker = HealthChecker()

        def slow_check():
            time.sleep(0.01)
            return HealthCheckResult(name="slow", status=HealthStatus.HEALTHY)

        checker.register_check("slow", slow_check)
        result = checker.run_check("slow")
        assert result.duration_ms > 0


# ============================================================
# 告警管理器测试
# ============================================================

class TestAlertManager:
    """告警管理器测试"""

    def test_add_rule(self):
        """测试添加规则"""
        am = AlertManager()
        rule = AlertRule("test", lambda: True)
        am.add_rule(rule)
        assert "test" in am._rules

    def test_remove_rule(self):
        """测试移除规则"""
        am = AlertManager()
        rule = AlertRule("test", lambda: True)
        am.add_rule(rule)
        am.remove_rule("test")
        assert "test" not in am._rules

    def test_check_rules_trigger(self):
        """测试检查规则触发"""
        am = AlertManager()
        rule = AlertRule("high_cpu", lambda: True, severity=AlertSeverity.WARNING)
        am.add_rule(rule)
        alerts = am.check_rules()
        assert len(alerts) == 1
        assert alerts[0].name == "high_cpu"

    def test_check_rules_no_trigger(self):
        """测试检查规则不触发"""
        am = AlertManager()
        rule = AlertRule("low_cpu", lambda: False)
        am.add_rule(rule)
        alerts = am.check_rules()
        assert len(alerts) == 0

    def test_cooldown(self):
        """测试冷却时间"""
        am = AlertManager()
        rule = AlertRule("test", lambda: True, cooldown=1.0)
        am.add_rule(rule)
        # 第一次触发
        alerts1 = am.check_rules()
        assert len(alerts1) == 1
        # 冷却中，不应再触发
        alerts2 = am.check_rules()
        assert len(alerts2) == 0

    def test_trigger_alert_manual(self):
        """测试手动触发告警"""
        am = AlertManager()
        alert = am.trigger_alert("manual", AlertSeverity.ERROR, "manual alert")
        assert alert.name == "manual"
        assert alert.severity == AlertSeverity.ERROR

    def test_resolve_alert(self):
        """测试解决告警"""
        am = AlertManager()
        alert = am.trigger_alert("test", AlertSeverity.WARNING, "test")
        assert am.resolve_alert(alert.alert_id) is True
        assert len(am.get_active_alerts()) == 0

    def test_resolve_nonexistent(self):
        """测试解决不存在的告警"""
        am = AlertManager()
        assert am.resolve_alert("nonexistent") is False

    def test_get_active_alerts(self):
        """测试获取活跃告警"""
        am = AlertManager()
        am.trigger_alert("a", AlertSeverity.WARNING, "a")
        am.trigger_alert("b", AlertSeverity.ERROR, "b")
        active = am.get_active_alerts()
        assert len(active) == 2

    def test_get_alert_history(self):
        """测试获取告警历史"""
        am = AlertManager()
        for i in range(5):
            am.trigger_alert(f"alert_{i}", AlertSeverity.INFO, f"alert {i}")
        history = am.get_alert_history()
        assert len(history) == 5

    def test_alert_handler(self):
        """测试告警处理器"""
        am = AlertManager()
        received = []
        am.add_handler(lambda a: received.append(a))
        am.trigger_alert("test", AlertSeverity.WARNING, "test alert")
        assert len(received) == 1

    def test_stats(self):
        """测试统计"""
        am = AlertManager()
        am.add_rule(AlertRule("rule1", lambda: True))
        am.trigger_alert("a", AlertSeverity.WARNING, "a")
        stats = am.stats()
        assert stats["total_alerts"] == 1
        assert stats["active_alerts"] == 1
        assert stats["rules"] == 1

    def test_rule_condition_exception(self):
        """测试规则条件异常"""
        am = AlertManager()

        def failing_condition():
            raise RuntimeError("condition error")

        rule = AlertRule("failing", failing_condition)
        am.add_rule(rule)
        alerts = am.check_rules()
        assert len(alerts) == 0  # 异常不应触发告警


# ============================================================
# 可观测性管理器测试
# ============================================================

class TestObservabilityManager:
    """可观测性管理器测试"""

    def test_creation(self):
        """测试创建"""
        om = create_observability_manager("test_service")
        assert om.logger is not None
        assert om.metrics is not None
        assert om.tracer is not None
        assert om.health_checker is not None
        assert om.alert_manager is not None

    def test_default_health_checks(self):
        """测试默认健康检查"""
        om = create_observability_manager("test")
        checks = om.health_checker.list_checks()
        assert "liveness" in checks
        assert "readiness" in checks

    def test_start_span(self):
        """测试开始跨度"""
        om = create_observability_manager("test")
        span = om.start_span("operation", user="test")
        assert span.name == "operation"
        assert span.tags["user"] == "test"

    def test_log_event(self):
        """测试记录日志事件"""
        om = create_observability_manager("test")
        om.log_event(LogLevel.INFO, "test message", key="value")
        records = om.logger.get_records()
        assert len(records) == 1

    def test_record_metric(self):
        """测试记录指标"""
        om = create_observability_manager("test")
        om.record_metric("cpu", 0.75)
        m = om.metrics.get_metric("cpu")
        assert m.value == 0.75

    def test_increment_counter(self):
        """测试递增计数器"""
        om = create_observability_manager("test")
        om.increment_counter("requests")
        om.increment_counter("requests")
        m = om.metrics.get_metric("requests")
        assert m.value == 2

    def test_observe_histogram(self):
        """测试观测直方图"""
        om = create_observability_manager("test")
        om.observe_histogram("latency", 0.05)
        om.observe_histogram("latency", 0.15)
        stats = om.metrics.get_histogram_stats("latency")
        assert stats["count"] == 2

    def test_check_health(self):
        """测试健康检查"""
        om = create_observability_manager("test")
        result = om.check_health()
        assert "overall_status" in result
        assert "checks" in result

    def test_check_alerts(self):
        """测试检查告警"""
        om = create_observability_manager("test")
        om.alert_manager.add_rule(AlertRule("test", lambda: True))
        alerts = om.check_alerts()
        assert len(alerts) == 1

    def test_dashboard(self):
        """测试仪表板"""
        om = create_observability_manager("test")
        om.logger.info("test")
        om.increment_counter("requests")
        dashboard = om.dashboard()
        assert "service_name" in dashboard
        assert "logger_stats" in dashboard
        assert "metrics_export" in dashboard
        assert "tracer_stats" in dashboard
        assert "health_status" in dashboard
        assert "alert_stats" in dashboard


# ============================================================
# Agent集成测试
# ============================================================

class TestAgentIntegration:
    """Agent集成测试"""

    def test_agent_has_observability(self):
        """测试Agent有可观测性管理器"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        assert agent.observability is not None

    def test_agent_log(self):
        """测试Agent日志"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        agent.log(LogLevel.INFO, "test log", key="value")
        logs = agent.get_logs()
        assert len(logs) >= 1

    def test_agent_health_check(self):
        """测试Agent健康检查"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        health = agent.check_health()
        assert "overall_status" in health

    def test_agent_add_health_check(self):
        """测试Agent添加健康检查"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        from self_evolving_agent.core.observability import HealthStatus, HealthCheckResult
        agent = SelfEvolvingAgent()
        agent.add_health_check("custom", lambda: HealthCheckResult(
            name="custom", status=HealthStatus.HEALTHY
        ))
        health = agent.check_health()
        assert "custom" in health["checks"]

    def test_agent_trigger_alert(self):
        """测试Agent触发告警"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        alert = agent.trigger_alert("test", AlertSeverity.WARNING, "test alert")
        assert alert.name == "test"
        active = agent.get_active_alerts()
        assert len(active) >= 1

    def test_agent_start_trace(self):
        """测试Agent开始追踪"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        span = agent.start_trace("test_operation")
        assert span.name == "test_operation"

    def test_agent_dashboard(self):
        """测试Agent仪表板"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent()
        dashboard = agent.get_observability_dashboard()
        assert "service_name" in dashboard


# ============================================================
# 并发安全测试
# ============================================================

class TestConcurrencySafety:
    """并发安全测试"""

    def test_logger_concurrent(self):
        """测试日志器并发"""
        logger = StructuredLogger("test")
        errors = []

        def worker(i):
            try:
                for j in range(50):
                    logger.info(f"msg_{i}_{j}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(logger.get_records(limit=10000)) == 500

    def test_metrics_concurrent(self):
        """测试指标并发"""
        metrics = MetricsCollector()
        errors = []

        def worker(i):
            try:
                for j in range(100):
                    metrics.counter("requests", worker_id=i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        total = sum(m.value for m in metrics.get_all_metrics())
        assert total == 1000

    def test_tracer_concurrent(self):
        """测试追踪器并发"""
        tracer = Tracer("test")
        errors = []

        def worker(i):
            try:
                for j in range(10):
                    span = tracer.start_span(f"op_{i}_{j}")
                    span.finish()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert tracer.stats()["total_spans"] == 100

    def test_alert_manager_concurrent(self):
        """测试告警管理器并发"""
        am = AlertManager()
        errors = []

        def worker(i):
            try:
                am.trigger_alert(f"alert_{i}", AlertSeverity.WARNING, f"alert {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(am.get_active_alerts()) == 20


# ============================================================
# 异常容错测试
# ============================================================

class TestErrorHandling:
    """异常容错测试"""

    def test_logger_handler_exception(self):
        """测试日志处理器异常"""
        logger = StructuredLogger("test")

        def bad_handler(r):
            raise RuntimeError("bad handler")

        logger.add_handler(bad_handler)
        # 不应崩溃
        logger.info("test")

    def test_health_check_exception(self):
        """测试健康检查异常"""
        checker = HealthChecker()

        def failing_check():
            raise ValueError("check failed")

        checker.register_check("failing", failing_check)
        result = checker.run_check("failing")
        assert result.status == HealthStatus.UNHEALTHY

    def test_alert_handler_exception(self):
        """测试告警处理器异常"""
        am = AlertManager()

        def bad_handler(a):
            raise RuntimeError("bad handler")

        am.add_handler(bad_handler)
        # 不应崩溃
        am.trigger_alert("test", AlertSeverity.WARNING, "test")

    def test_alert_condition_exception(self):
        """测试告警条件异常"""
        am = AlertManager()

        def failing_condition():
            raise RuntimeError("condition failed")

        rule = AlertRule("failing", failing_condition)
        am.add_rule(rule)
        alerts = am.check_rules()
        assert len(alerts) == 0  # 异常条件不触发告警

    def test_empty_health_checker(self):
        """测试空健康检查器"""
        checker = HealthChecker()
        assert checker.get_overall_status() == HealthStatus.UNKNOWN
        assert checker.run_all() == {}

    def test_empty_alert_manager(self):
        """测试空告警管理器"""
        am = AlertManager()
        assert am.check_rules() == []
        assert am.get_active_alerts() == []
        assert am.get_alert_history() == []


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_logging_principle(self):
        """第一性原理：日志记录离散事件"""
        logger = StructuredLogger("test")
        logger.info("event1", user="a")
        logger.info("event2", user="b")
        records = logger.get_records()
        # 每个事件都被独立记录
        assert len(records) == 2
        assert records[0].fields["user"] == "a"
        assert records[1].fields["user"] == "b"

    def test_metrics_principle(self):
        """第一性原理：指标聚合数值"""
        metrics = MetricsCollector()
        for _ in range(100):
            metrics.counter("requests")
        m = metrics.get_metric("requests")
        # 指标聚合了100次请求
        assert m.value == 100

    def test_tracing_principle(self):
        """第一性原理：追踪请求链路"""
        tracer = Tracer("test")
        parent = tracer.start_span("parent_op")
        child = tracer.start_span("child_op", trace_id=parent.trace_id, parent_span_id=parent.span_id)
        child.finish()
        parent.finish()
        trace = tracer.get_trace(parent.trace_id)
        # 追踪记录了完整调用链
        assert len(trace) == 2
        assert trace[0].span_id == parent.span_id
        assert trace[1].parent_span_id == parent.span_id

    def test_health_check_principle(self):
        """第一性原理：健康检查探针"""
        checker = HealthChecker()
        checker.register_check("db", lambda: HealthCheckResult(
            name="db", status=HealthStatus.HEALTHY
        ))
        checker.register_check("cache", lambda: HealthCheckResult(
            name="cache", status=HealthStatus.UNHEALTHY, message="connection refused"
        ))
        overall = checker.get_overall_status()
        # 任一不健康导致整体不健康
        assert overall == HealthStatus.UNHEALTHY

    def test_alerting_principle(self):
        """第一性原理：告警主动通知"""
        am = AlertManager()
        received = []
        am.add_handler(lambda a: received.append(a))
        am.add_rule(AlertRule("high_error_rate", lambda: True, severity=AlertSeverity.CRITICAL))
        am.check_rules()
        # 告警被主动触发并通知
        assert len(received) == 1
        assert received[0].severity == AlertSeverity.CRITICAL

    def test_observability_trilogy_principle(self):
        """第一性原理：可观测性三支柱"""
        om = create_observability_manager("test")
        # 日志
        om.logger.info("event")
        # 指标
        om.increment_counter("requests")
        # 追踪
        span = om.start_span("operation")
        span.finish()
        # 三支柱都有数据
        assert len(om.logger.get_records()) >= 1
        assert len(om.metrics.get_all_metrics()) >= 1
        assert om.tracer.stats()["total_spans"] >= 1
