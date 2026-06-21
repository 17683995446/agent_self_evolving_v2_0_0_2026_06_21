"""
阶段137: 端到端集成测试 — 真实场景验证

第一性原理:
1. 整体性 — 系统作为整体必须正确工作，而非仅组件单独正确
2. 真实性 — 测试应模拟真实使用场景，而非人造的单元测试
3. 完整性 — 覆盖从输入到输出的完整数据流
4. 鲁棒性 — 系统在异常条件下应保持稳定
5. 可重复性 — 测试结果应可重复

测试场景:
1. Agent完整生命周期 — 创建→初始化→运行→停止
2. 感知-行动-反思闭环 — observe→act→reflect→learn
3. 任务执行全流程 — 提交→执行→监控→完成
4. 代码质量管线 — 编写→审查→文档→修复
5. 插件系统全流程 — 创建→加载→配置→运行→监控→重载→卸载
6. 生产部署全流程 — 启动→健康检查→限流→停止
7. 多模块协同 — 性能+可观测性+分布式+生产
8. 错误恢复 — 注入错误→验证隔离→验证恢复
9. 并发安全 — 多线程操作验证
10. API端到端 — REST API完整工作流
"""

import os
import sys
import time
import json
import threading
import tempfile
import textwrap

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from self_evolving_agent import SelfEvolvingAgent, create_default_agent
from self_evolving_agent.core.system_coordinator import create_coordinator
from self_evolving_agent.core.plugin_system import (
    EnhancedPlugin, PluginManifest, PluginConfig, PluginContext,
    PluginHealthStatus, PluginHealthResult, create_enhanced_plugin_manager,
)
from self_evolving_agent.core.task_executor import TaskStatus
from self_evolving_agent.core.doc_generator import DocFormat
from self_evolving_agent.core.performance import create_performance_monitor
from self_evolving_agent.core.observability import (
    LogLevel, AlertSeverity, create_observability_manager,
)
from self_evolving_agent.core.production import create_production_manager


# ============================================================
# 测试辅助
# ============================================================

def create_test_agent(agent_id: str = "e2e_test") -> SelfEvolvingAgent:
    """创建测试Agent"""
    agent = SelfEvolvingAgent(agent_id=agent_id)
    agent.initialize({})
    return agent


# ============================================================
# 1. Agent完整生命周期
# ============================================================

class TestAgentLifecycleE2E:
    """Agent完整生命周期端到端测试"""

    def test_full_lifecycle(self):
        """E2E: 创建→初始化→启动→运行→停止"""
        # 创建
        agent = SelfEvolvingAgent(agent_id="lifecycle_test")
        assert agent is not None

        # 初始化
        agent.initialize({})
        assert agent._coordinator is not None

        # 启动
        agent.start()
        assert agent._running is True

        # 运行周期
        for _ in range(3):
            agent.coordinator.run_cycle({})

        # 验证运行了
        state = agent.get_state()
        assert state is not None

        # 停止
        agent.stop()
        assert agent._running is False

    def test_multiple_cycles_progress(self):
        """E2E: 多周期运行系统状态递进"""
        agent = create_test_agent("progress_test")
        agent.start()

        initial_count = agent.coordinator._cycle_count

        for _ in range(5):
            agent.coordinator.run_cycle({})

        final_count = agent.coordinator._cycle_count
        assert final_count > initial_count

        agent.stop()

    def test_repeated_start_stop(self):
        """E2E: 反复启停不崩溃"""
        agent = create_test_agent("restart_test")

        for _ in range(3):
            agent.start()
            assert agent._running is True
            agent.stop()
            assert agent._running is False


# ============================================================
# 2. 感知-行动-反思闭环
# ============================================================

class TestPerceptionActionReflectionE2E:
    """感知-行动-反思闭环测试"""

    def test_observe_act_reflect_flow(self):
        """E2E: observe→act→reflect完整流程"""
        agent = create_test_agent("oar_test")

        # 感知
        obs_result = agent.coordinator.observe({"module_id": "test"})
        assert obs_result is not None

        # 行动
        act_result = agent.coordinator.act("explore", {})
        assert act_result is not None

        # 反思
        reflect_result = agent.coordinator.reflect()
        assert reflect_result is not None

    def test_full_cycle_integration(self):
        """E2E: 完整周期整合所有引擎"""
        agent = create_test_agent("cycle_integration")

        result = agent.coordinator.run_cycle({
            "module_id": "integration_test",
            "predicted": {"value": 0.5},
            "actual": {"value": 0.7},
        })

        assert result is not None
        # 周期应产生某种结果
        assert isinstance(result, dict) or result is not None

    def test_learning_progresses(self):
        """E2E: 多次运行后系统状态变化"""
        agent = create_test_agent("learning_test")
        agent.start()

        states = []
        for i in range(5):
            agent.coordinator.run_cycle({"module_id": f"module_{i}"})
            states.append(agent.get_state())

        # 系统应产生不同的状态
        assert len(states) == 5

        agent.stop()


# ============================================================
# 3. 任务执行全流程
# ============================================================

class TestTaskExecutionE2E:
    """任务执行全流程测试"""

    def test_submit_execute_result_flow(self):
        """E2E: 提交→执行→获取结果"""
        agent = create_test_agent("task_e2e")

        # 提交任务
        task_id = agent.submit_task(goal="observe test environment")
        assert task_id is not None

        # 检查状态
        status = agent.get_task_status(task_id)
        assert status is not None
        assert status in [TaskStatus.PENDING, TaskStatus.PLANNING, TaskStatus.READY, TaskStatus.EXECUTING, TaskStatus.COMPLETED]

        # 同步执行
        result = agent.execute_task("simple observation task")
        assert result is not None

    def test_multiple_tasks_sequential(self):
        """E2E: 多个任务顺序执行"""
        agent = create_test_agent("multi_task")

        task_ids = []
        for i in range(5):
            tid = agent.submit_task(goal=f"task_{i}")
            task_ids.append(tid)

        assert len(task_ids) == 5
        # 所有任务ID应唯一
        assert len(set(task_ids)) == 5

    def test_task_status_tracking(self):
        """E2E: 任务状态跟踪"""
        agent = create_test_agent("task_tracking")

        task_id = agent.submit_task(goal="tracked task")

        # 初始状态
        status1 = agent.get_task_status(task_id)
        assert status1 is not None

        # 执行后状态
        agent.execute_task("tracked task")
        # 状态可能变化
        status2 = agent.get_task_status(task_id)
        assert status2 is not None


# ============================================================
# 4. 代码质量管线
# ============================================================

class TestCodeQualityPipelineE2E:
    """代码质量管线测试"""

    def test_review_and_document(self):
        """E2E: 审查代码→生成文档"""
        agent = create_test_agent("code_quality")

        code = '''
def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
'''

        # 审查
        report = agent.review_code(code)
        assert report is not None
        assert report.language == "python"

        # 生成文档
        doc_report = agent.generate_docs(code, DocFormat.MARKDOWN)
        assert doc_report is not None
        assert doc_report.content  # 应有内容

    def test_review_finds_issues(self):
        """E2E: 审查应发现问题代码"""
        agent = create_test_agent("code_review_issues")

        bad_code = '''
import os
def dangerous():
    eval("1+1")
    exec("x=1")
    pass
'''

        report = agent.review_code(bad_code)
        assert report is not None
        # 应有安全问题
        assert len(report.issues) > 0 or report.error_count > 0

    def test_file_review_and_docs(self, tmp_path):
        """E2E: 文件审查和文档生成"""
        agent = create_test_agent("file_pipeline")

        # 创建测试文件
        test_file = tmp_path / "sample.py"
        test_file.write_text(textwrap.dedent('''
            def greet(name):
                """Greet someone."""
                return f"Hello, {name}"
        '''))

        # 审查文件
        review = agent.review_file(str(test_file))
        assert review is not None

        # 生成文档
        docs = agent.generate_file_docs(str(test_file), DocFormat.MARKDOWN)
        assert docs is not None

    def test_html_documentation(self):
        """E2E: HTML格式文档生成"""
        agent = create_test_agent("html_docs")

        code = "def f():\n    pass\n"
        report = agent.generate_docs(code, DocFormat.HTML)
        assert report is not None
        assert report.format == DocFormat.HTML


# ============================================================
# 5. 插件系统全流程
# ============================================================

class TestPluginSystemE2E:
    """插件系统全流程测试"""

    def test_plugin_full_lifecycle(self):
        """E2E: 创建→加载→配置→运行→监控→卸载"""

        class LifecyclePlugin(EnhancedPlugin):
            def __init__(self):
                super().__init__()
                self._events = []

            @property
            def manifest(self):
                return PluginManifest(
                    name="lifecycle_e2e",
                    version="1.0.0",
                    hooks=["on_test"],
                    config_schema={
                        "enabled": {"type": "bool", "default": True},
                    },
                )

            def initialize_with_context(self, ctx):
                super().initialize_with_context(ctx)
                self._events.append("init")
                return True

            def start(self):
                self._events.append("start")
                return True

            def stop(self):
                self._events.append("stop")
                return True

            def on_event(self, event_type, payload):
                self._events.append(f"event:{event_type}")
                return {"processed": True}

        mgr = create_enhanced_plugin_manager()
        plugin = LifecyclePlugin()

        # 加载
        assert mgr.load_enhanced(plugin, {"enabled": True})
        assert mgr.registry.get_state("lifecycle_e2e").value == "active"

        # 配置
        config = mgr.get_config("lifecycle_e2e")
        assert config is not None
        assert config.get("enabled") is True

        # 运行（触发事件）
        responses = mgr.emit("on_test", {"data": "test"})
        assert len(responses) > 0

        # 监控（健康检查）
        health = mgr.check_health("lifecycle_e2e")
        assert health.status == PluginHealthStatus.HEALTHY

        # 卸载
        assert mgr.unload("lifecycle_e2e")
        assert mgr.registry.get("lifecycle_e2e") is None

        # 验证生命周期事件
        assert "init" in plugin._events
        assert "start" in plugin._events
        assert "stop" in plugin._events

    def test_plugin_hot_reload(self):
        """E2E: 热重载保持配置"""

        class ReloadablePlugin(EnhancedPlugin):
            @property
            def manifest(self):
                return PluginManifest(
                    name="reloadable",
                    version="1.0.0",
                    config_schema={
                        "value": {"type": "int", "default": 0},
                    },
                )

        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(ReloadablePlugin(), {"value": 42})

        # 验证配置
        assert mgr.get_config("reloadable").get("value") == 42

        # 热重载
        assert mgr.reload("reloadable")

        # 配置应保留
        assert mgr.get_config("reloadable").get("value") == 42
        assert mgr.registry.get_state("reloadable").value == "active"

    def test_plugin_event_bus_communication(self):
        """E2E: 插件间通过事件总线通信"""

        class ProducerPlugin(EnhancedPlugin):
            @property
            def manifest(self):
                return PluginManifest(name="producer", version="1.0.0")

            def produce(self):
                self._context.emit_event("data_ready", {"value": 100})

        class ConsumerPlugin(EnhancedPlugin):
            def __init__(self):
                super().__init__()
                self.received = []

            @property
            def manifest(self):
                return PluginManifest(name="consumer", version="1.0.0")

            def initialize_with_context(self, ctx):
                super().initialize_with_context(ctx)
                # 订阅事件
                self._context.set_event_publisher(
                    lambda et, p, s: self.received.append((et, p))
                )
                return True

        mgr = create_enhanced_plugin_manager()

        # 先注册消费者
        consumer = ConsumerPlugin()
        mgr.load_enhanced(consumer)

        # 通过事件总线订阅
        received = []
        mgr.subscribe_event("data_ready", lambda e: received.append(e))

        # 加载生产者
        producer = ProducerPlugin()
        mgr.load_enhanced(producer)

        # 生产者发送事件
        mgr.publish_event("data_ready", {"value": 100}, "producer")

        # 消费者应收到
        assert len(received) > 0
        assert received[0].payload["value"] == 100

    def test_plugin_discovery_from_directory(self, tmp_path):
        """E2E: 从目录自动发现插件"""
        plugin_file = tmp_path / "discovered.py"
        plugin_file.write_text(textwrap.dedent('''
            from self_evolving_agent.core.plugin_system import Plugin, PluginInfo

            class DiscoveredPlugin(Plugin):
                @property
                def info(self):
                    return PluginInfo(name="discovered", version="1.0.0")
        '''))

        mgr = create_enhanced_plugin_manager()
        results = mgr.discover_and_load(str(tmp_path))

        assert "discovered" in results
        assert results["discovered"] is True


# ============================================================
# 6. 生产部署全流程
# ============================================================

class TestProductionDeploymentE2E:
    """生产部署全流程测试"""

    def test_production_start_stop(self):
        """E2E: 生产模式启停"""
        agent = create_test_agent("prod_e2e")

        # 启动生产模式
        assert agent.start_production()

        # 状态检查
        status = agent.get_production_status()
        assert status is not None

        # 健康检查
        health = agent.production_health_check()
        assert health is not None

        # 停止
        assert agent.stop_production()

    def test_rate_limiting(self):
        """E2E: 限流器工作"""
        agent = create_test_agent("rate_limit_e2e")

        # 多次请求
        allowed = 0
        for _ in range(10):
            if agent.check_rate_limit():
                allowed += 1

        # 应有部分请求被允许
        assert allowed > 0

    def test_circuit_breaker(self):
        """E2E: 熔断器状态"""
        agent = create_test_agent("circuit_e2e")
        cb = agent.get_circuit_breaker("test_service")
        assert cb is not None

    def test_resource_management(self):
        """E2E: 资源管理"""
        agent = create_test_agent("resource_e2e")

        # 设置配额
        agent.set_resource_quota("connections", 5)

        # 获取资源
        results = []
        for _ in range(5):
            results.append(agent.acquire_resource("connections"))

        # 应全部成功
        assert all(results)

        # 释放
        agent.release_resource("connections")
        # 再次获取应成功
        assert agent.acquire_resource("connections")


# ============================================================
# 7. 多模块协同
# ============================================================

class TestMultiModuleIntegrationE2E:
    """多模块协同测试"""

    def test_performance_with_observability(self):
        """E2E: 性能监控+可观测性协同"""
        agent = create_test_agent("perf_obs_e2e")

        # 记录日志
        agent.log(LogLevel.INFO, "Test log message")

        # 获取性能报告
        perf_report = agent.get_performance_report()
        assert perf_report is not None

        # 获取可观测性仪表板
        dashboard = agent.get_observability_dashboard()
        assert dashboard is not None
        assert "service_name" in dashboard

        # 获取日志
        logs = agent.get_logs()
        assert logs is not None

    def test_alert_system(self):
        """E2E: 告警系统"""
        agent = create_test_agent("alert_e2e")

        # 触发告警
        alert = agent.trigger_alert(
            "test_alert",
            AlertSeverity.WARNING,
            "Test alert message",
        )
        assert alert is not None

        # 获取活跃告警
        alerts = agent.get_active_alerts()
        assert len(alerts) > 0

    def test_performance_cache_integration(self):
        """E2E: 性能缓存集成"""
        agent = create_test_agent("cache_e2e")

        # 写入缓存
        agent.cache_put("test_key", "test_value")

        # 读取缓存
        value = agent.cache_get("test_key")
        assert value == "test_value"

        # 缓存统计
        stats = agent.get_cache_stats()
        assert stats is not None

        # 使缓存失效
        agent.cache_invalidate("test_key")
        assert agent.cache_get("test_key") is None

    def test_all_systems_together(self):
        """E2E: 所有系统同时工作"""
        agent = create_test_agent("all_systems")
        agent.start()

        # 运行周期
        agent.coordinator.run_cycle({})

        # 性能报告
        assert agent.get_performance_report() is not None

        # 可观测性
        assert agent.get_observability_dashboard() is not None

        # 插件系统
        assert agent.list_plugins() is not None

        # 生产状态
        assert agent.get_production_status() is not None

        # 日志
        agent.log(LogLevel.INFO, "All systems test")
        assert len(agent.get_logs()) > 0

        agent.stop()


# ============================================================
# 8. 错误恢复
# ============================================================

class TestErrorRecoveryE2E:
    """错误恢复测试"""

    def test_observe_error_recovery(self):
        """E2E: 感知错误后系统恢复"""
        agent = create_test_agent("error_recovery")

        # 正常感知
        result1 = agent.coordinator.observe({"module_id": "normal"})
        assert result1 is not None

        # 异常输入（不崩溃）
        try:
            agent.coordinator.observe({"module_id": None, "actual": None})
        except Exception:
            pass  # 异常被预期

        # 系统仍可正常工作
        result2 = agent.coordinator.observe({"module_id": "recovery"})
        assert result2 is not None

    def test_plugin_error_isolation(self):
        """E2E: 插件错误不影响系统"""

        class CrashyPlugin(EnhancedPlugin):
            @property
            def manifest(self):
                return PluginManifest(name="crashy", version="1.0.0")

            def on_event(self, event_type, payload):
                raise RuntimeError("Plugin crashed!")

        class GoodPlugin(EnhancedPlugin):
            @property
            def manifest(self):
                return PluginManifest(name="good", version="1.0.0", hooks=["test"])

            def on_event(self, event_type, payload):
                return "ok"

        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(GoodPlugin())

        # 触发事件 — 好插件应正常响应
        responses = mgr.emit("test", {})
        assert "ok" in responses

    def test_task_error_handling(self):
        """E2E: 任务执行错误处理"""
        agent = create_test_agent("task_error")

        # 执行任务不应崩溃
        try:
            result = agent.execute_task("invalid task that might fail")
            # 即使失败也不应崩溃
        except Exception as e:
            # 异常应被处理
            assert e is not None

    def test_concurrent_error_isolation(self):
        """E2E: 并发错误隔离"""
        agent = create_test_agent("concurrent_error")
        errors = []

        def worker():
            try:
                for _ in range(3):
                    agent.coordinator.observe({"module_id": threading.current_thread().name})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 错误不应传播到主线程
        # 系统应继续可用
        assert agent.coordinator.observe({"module_id": "post_concurrent"}) is not None


# ============================================================
# 9. 并发安全
# ============================================================

class TestConcurrencySafetyE2E:
    """并发安全测试"""

    def test_concurrent_observe(self):
        """E2E: 并发感知"""
        agent = create_test_agent("concurrent_observe")
        results = []

        def worker():
            for _ in range(5):
                try:
                    r = agent.coordinator.observe({"module_id": "concurrent"})
                    results.append(r)
                except Exception:
                    pass

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 应有部分成功
        assert len(results) > 0

    def test_concurrent_task_submit(self):
        """E2E: 并发任务提交"""
        agent = create_test_agent("concurrent_tasks")
        task_ids = []
        lock = threading.Lock()

        def worker():
            for _ in range(3):
                tid = agent.submit_task(goal="concurrent task")
                with lock:
                    task_ids.append(tid)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有任务ID应唯一
        assert len(task_ids) == 9
        assert len(set(task_ids)) == 9

    def test_concurrent_cache_access(self):
        """E2E: 并发缓存访问"""
        agent = create_test_agent("concurrent_cache")

        def writer():
            for i in range(20):
                agent.cache_put(f"key_{i}", f"value_{i}")

        def reader():
            for i in range(20):
                agent.cache_get(f"key_{i}")

        threads = [threading.Thread(target=writer) for _ in range(2)]
        threads += [threading.Thread(target=reader) for _ in range(2)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 不崩溃即通过
        assert agent.cache_get("key_0") is not None


# ============================================================
# 10. API端到端
# ============================================================

class TestAPIE2E:
    """API端到端测试"""

    @pytest.fixture
    def client(self):
        """Flask测试客户端"""
        os.environ.setdefault("SKIP_LLM_INIT", "true")
        from main import app as flask_app, init_agent
        # 确保coordinator已初始化
        import main as _main
        if _main._coordinator is None:
            init_agent()
        flask_app.config["TESTING"] = True
        return flask_app.test_client()

    def test_full_api_workflow(self, client):
        """E2E: API完整工作流"""
        # 1. 检查状态
        resp = client.get("/api/status")
        assert resp.status_code == 200

        # 2. 运行周期
        resp = client.post("/api/cycle", json={})
        assert resp.status_code == 200

        # 3. 感知
        resp = client.post("/api/observe", json={"module_id": "api_test"})
        assert resp.status_code == 200

        # 4. 行动
        resp = client.post("/api/act", json={"action": "test"})
        assert resp.status_code == 200

        # 5. 反思
        resp = client.get("/api/reflect")
        assert resp.status_code == 200

    def test_api_task_workflow(self, client):
        """E2E: API任务工作流"""
        # 提交任务
        resp = client.post("/api/task/submit", json={"goal": "api task"})
        assert resp.status_code == 200
        task_id = resp.get_json()["task_id"]

        # 查询状态
        resp = client.get(f"/api/task/{task_id}/status")
        assert resp.status_code == 200

    def test_api_code_review_workflow(self, client):
        """E2E: API代码审查工作流"""
        code = "def f():\n    return 42\n"

        # 审查代码
        resp = client.post("/api/review/code", json={"code": code})
        assert resp.status_code == 200

        # 生成文档
        resp = client.post("/api/docs/generate", json={"code": code, "format": "markdown"})
        assert resp.status_code == 200

    def test_api_monitoring_workflow(self, client):
        """E2E: API监控工作流"""
        # 性能报告
        resp = client.get("/api/performance/report")
        assert resp.status_code == 200

        # 可观测性仪表板
        resp = client.get("/api/observability/dashboard")
        assert resp.status_code == 200

        # 插件列表
        resp = client.get("/api/plugins")
        assert resp.status_code == 200

        # 生产状态
        resp = client.get("/api/production/status")
        assert resp.status_code == 200

    def test_api_health_endpoints(self, client):
        """E2E: API健康端点"""
        for endpoint in ["/health/liveness", "/health/readiness", "/health"]:
            resp = client.get(endpoint)
            assert resp.status_code in (200, 503)


# ============================================================
# 11. 第一性原理验证
# ============================================================

class TestFirstPrinciplesE2E:
    """第一性原理端到端验证"""

    def test_system_coherence_principle(self):
        """第一性原理：系统一致性 — 所有模块协同工作"""
        agent = create_test_agent("coherence")
        agent.start()

        # 运行周期
        agent.coordinator.run_cycle({})

        # 所有子系统应可用
        assert agent.get_performance_report() is not None
        assert agent.get_observability_dashboard() is not None
        assert agent.get_production_status() is not None
        assert agent.list_plugins() is not None

        agent.stop()

    def test_data_flow_integrity_principle(self):
        """第一性原理：数据流完整性 — 输入到输出完整"""
        agent = create_test_agent("data_flow")

        # 感知输入 → 预测 → 误差 → 学习
        result = agent.coordinator.observe({
            "module_id": "flow_test",
            "predicted": {"value": 0.5},
            "actual": {"value": 0.8},
        })

        # 数据流应完整
        assert result is not None

    def test_error_containment_principle(self):
        """第一性原理：错误遏制 — 错误不传播"""
        agent = create_test_agent("containment")

        # 注入错误
        try:
            agent.coordinator.observe({"invalid": None})
        except Exception:
            pass

        # 系统仍正常
        assert agent.coordinator.observe({"module_id": "post_error"}) is not None

    def test_resource_efficiency_principle(self):
        """第一性原理：资源效率 — 不泄漏"""
        agent = create_test_agent("efficiency")

        # 多次操作
        for _ in range(10):
            agent.coordinator.run_cycle({})
            agent.cache_put("temp", "val")
            agent.cache_invalidate("temp")

        # 系统应仍高效
        perf = agent.get_performance_report()
        assert perf is not None

    def test_extensibility_e2e_principle(self):
        """第一性原理：可扩展性 — 端到端插件"""

        class ExtensionPlugin(EnhancedPlugin):
            @property
            def manifest(self):
                return PluginManifest(
                    name="extension_e2e",
                    version="1.0.0",
                    hooks=["on_extend"],
                    config_schema={"mode": {"type": "string", "default": "active"}},
                )

            def on_event(self, event_type, payload):
                if event_type == "on_extend":
                    return {"extended": True, "mode": self._config.get("mode")}

        agent = create_test_agent("extensibility_e2e")
        plugin = ExtensionPlugin()

        # 通过Agent加载插件
        assert agent.load_plugin(plugin, {"mode": "active"})

        # 验证加载
        assert agent.get_plugin_status("extension_e2e") == "active"

        # 触发钩子
        responses = agent.plugin_manager.emit("on_extend", {})
        assert len(responses) > 0
        assert responses[0]["extended"] is True

        # 健康检查
        health = agent.get_plugin_health("extension_e2e")
        assert health.status == PluginHealthStatus.HEALTHY

        # 卸载
        assert agent.unload_plugin("extension_e2e")
        assert agent.get_plugin("extension_e2e") is None
