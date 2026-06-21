"""
阶段135: 插件系统 — 可扩展架构 专项测试

测试覆盖：
1. PluginManifest — 扩展元信息
2. VersionChecker — 版本兼容性
3. PluginConfig — 配置管理（schema校验、动态更新、监听器）
4. PluginContext — 受控系统访问
5. PluginEventBus — 发布/订阅事件总线
6. PluginLoader — 插件发现和加载
7. EnhancedPlugin — 增强插件基类
8. EnhancedPluginManager — 增强管理器（热重载、发现、健康检查）
9. 向后兼容 — 旧版Plugin仍可使用
10. 错误隔离 — 插件异常不影响系统
11. 第一性原理验证
"""

import os
import sys
import tempfile
import textwrap
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from self_evolving_agent.core.plugin_system import (
    # 旧版接口
    Plugin, PluginInfo, PluginState, PluginRegistry, PluginManager,
    create_plugin_manager,
    # 阶段135新增
    PluginPriority, PluginHealthStatus, PluginManifest, VersionChecker,
    PluginConfig, PluginContext, PluginEvent, PluginEventBus,
    PluginHealthResult, PluginLoader, EnhancedPlugin, EnhancedPluginManager,
    create_enhanced_plugin_manager,
)


# ============================================================
# 测试辅助插件
# ============================================================

class SimplePlugin(Plugin):
    """简单插件（旧版接口）"""

    @property
    def info(self) -> PluginInfo:
        return PluginInfo(name="simple", version="1.0.0", description="A simple plugin")

    def initialize(self, context):
        self._init_ctx = context
        return True


class CounterPlugin(EnhancedPlugin):
    """计数器插件（增强版）"""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="counter",
            version="1.2.0",
            description="A counter plugin",
            author="test",
            license="MIT",
            hooks=["on_increment"],
            config_schema={
                "initial_value": {"type": "int", "default": 0, "min": 0, "max": 1000},
                "step": {"type": "int", "default": 1, "min": 1, "max": 100},
            },
        )

    def initialize_with_context(self, context: PluginContext) -> bool:
        super().initialize_with_context(context)
        self._count = self._config.get("initial_value", 0)
        self._step = self._config.get("step", 1)
        return True

    def increment(self) -> int:
        self._count += self._step
        if self._context:
            self._context.emit_event("on_increment", {"count": self._count})
        return self._count

    def get_count(self) -> int:
        return self._count

    def health_check(self) -> PluginHealthResult:
        if self._count > 10000:
            return PluginHealthResult(
                plugin_name="counter",
                status=PluginHealthStatus.DEGRADED,
                message="Count too high",
            )
        return PluginHealthResult(
            plugin_name="counter",
            status=PluginHealthStatus.HEALTHY,
            message=f"count={self._count}",
        )


class FailingPlugin(EnhancedPlugin):
    """总是失败的插件"""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(name="failing", version="1.0.0")

    def start(self) -> bool:
        raise RuntimeError("Plugin start failed")


class DependentPlugin(EnhancedPlugin):
    """依赖counter的插件"""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="dependent",
            version="1.0.0",
            dependencies=["counter"],
        )


class IncompatiblePlugin(EnhancedPlugin):
    """版本不兼容的插件"""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="incompatible",
            version="1.0.0",
            min_system_version="99.0.0",
        )


class ConfigValidatorPlugin(EnhancedPlugin):
    """需要必填配置的插件"""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="config_validator",
            version="1.0.0",
            config_schema={
                "api_key": {"type": "string", "required": True},
                "timeout": {"type": "int", "default": 30, "min": 1, "max": 300},
                "mode": {"type": "string", "choices": ["fast", "slow"]},
            },
        )


# ============================================================
# PluginManifest 测试
# ============================================================

class TestPluginManifest:
    """PluginManifest测试"""

    def test_manifest_creation(self):
        """测试清单创建"""
        m = PluginManifest(name="test", version="1.0.0")
        assert m.name == "test"
        assert m.version == "1.0.0"
        assert m.priority == PluginPriority.NORMAL
        assert m.dependencies == []

    def test_manifest_to_dict(self):
        """测试清单转字典"""
        m = PluginManifest(
            name="test", version="1.0.0", description="desc",
            license="MIT", homepage="http://example.com",
            dependencies=["dep1"], hooks=["hook1"],
            priority=PluginPriority.HIGH,
        )
        d = m.to_dict()
        assert d["name"] == "test"
        assert d["license"] == "MIT"
        assert d["priority"] == "HIGH"
        assert "dep1" in d["dependencies"]

    def test_manifest_from_plugin_info(self):
        """测试从PluginInfo转换"""
        info = PluginInfo(name="old", version="2.0.0", description="legacy")
        m = PluginManifest.from_plugin_info(info)
        assert m.name == "old"
        assert m.version == "2.0.0"


# ============================================================
# VersionChecker 测试
# ============================================================

class TestVersionChecker:
    """版本检查器测试"""

    def test_compatible(self):
        """测试兼容"""
        assert VersionChecker.is_compatible("1.0.0", "1.0.0", "2.0.0")
        assert VersionChecker.is_compatible("1.0.0", "1.0.0", "1.5.0")

    def test_incompatible(self):
        """测试不兼容"""
        assert not VersionChecker.is_compatible("1.0.0", "2.0.0", "1.0.0")
        assert not VersionChecker.is_compatible("1.0.0", "99.0.0", "1.0.0")

    def test_satisfies_dependency(self):
        """测试依赖满足"""
        assert VersionChecker.satisfies_dependency("2.0.0", "1.0.0")
        assert not VersionChecker.satisfies_dependency("1.0.0", "2.0.0")

    def test_invalid_version(self):
        """测试无效版本"""
        assert VersionChecker.is_compatible("1.0", "invalid", "1.0.0")


# ============================================================
# PluginConfig 测试
# ============================================================

class TestPluginConfig:
    """插件配置测试"""

    def test_get_set(self):
        """测试获取设置"""
        config = PluginConfig(values={"key1": "value1"})
        assert config.get("key1") == "value1"
        assert config.get("nonexistent", "default") == "default"

        config.set("key2", 42)
        assert config.get("key2") == 42

    def test_update(self):
        """测试批量更新"""
        config = PluginConfig()
        config.update({"a": 1, "b": 2, "c": 3})
        assert config.get("a") == 1
        assert config.get("b") == 2
        assert config.get("c") == 3

    def test_validate_empty_schema(self):
        """测试空schema校验"""
        config = PluginConfig(values={"key": "value"})
        valid, errors = config.validate()
        assert valid
        assert errors == []

    def test_validate_required(self):
        """测试必填校验"""
        config = PluginConfig(
            schema={"api_key": {"type": "string", "required": True}},
            values={},
        )
        valid, errors = config.validate()
        assert not valid
        assert any("api_key" in e for e in errors)

    def test_validate_type(self):
        """测试类型校验"""
        config = PluginConfig(
            schema={"port": {"type": "int"}},
            values={"port": "not_a_number"},
        )
        valid, errors = config.validate()
        assert not valid
        assert any("port" in e for e in errors)

    def test_validate_choices(self):
        """测试枚举校验"""
        config = PluginConfig(
            schema={"mode": {"type": "string", "choices": ["fast", "slow"]}},
            values={"mode": "medium"},
        )
        valid, errors = config.validate()
        assert not valid

    def test_validate_min_max(self):
        """测试范围校验"""
        config = PluginConfig(
            schema={"count": {"type": "int", "min": 0, "max": 100}},
            values={"count": 150},
        )
        valid, errors = config.validate()
        assert not valid
        assert any("<=" in e for e in errors)

    def test_validate_valid_config(self):
        """测试有效配置"""
        config = PluginConfig(
            schema={
                "name": {"type": "string", "required": True},
                "port": {"type": "int", "min": 1, "max": 65535},
            },
            values={"name": "test", "port": 8080},
        )
        valid, errors = config.validate()
        assert valid
        assert errors == []

    def test_on_change_listener(self):
        """测试变更监听器"""
        config = PluginConfig()
        changes = []
        config.on_change(lambda key, old, new: changes.append((key, old, new)))
        config.set("key", "value1")
        config.set("key", "value2")
        assert len(changes) == 2
        assert changes[0] == ("key", None, "value1")
        assert changes[1] == ("key", "value1", "value2")

    def test_to_dict(self):
        """测试导出"""
        config = PluginConfig(values={"a": 1, "b": 2})
        d = config.to_dict()
        assert d == {"a": 1, "b": 2}

    def test_bool_not_int(self):
        """测试bool不被当作int"""
        config = PluginConfig(
            schema={"count": {"type": "int"}},
            values={"count": True},
        )
        valid, _ = config.validate()
        assert not valid


# ============================================================
# PluginContext 测试
# ============================================================

class TestPluginContext:
    """插件上下文测试"""

    def test_context_creation(self):
        """测试上下文创建"""
        config = PluginConfig()
        ctx = PluginContext("test_plugin", config)
        assert ctx.name == "test_plugin"
        assert ctx.config is config

    def test_service_management(self):
        """测试服务管理"""
        config = PluginConfig()
        ctx = PluginContext("test", config)
        ctx.register_service("db", {"connection": "ok"})
        assert ctx.get_service("db") == {"connection": "ok"}
        assert "db" in ctx.list_services()
        ctx.unregister_service("db")
        assert ctx.get_service("db") is None

    def test_logging(self):
        """测试日志"""
        config = PluginConfig()
        ctx = PluginContext("test", config)
        ctx.log("INFO", "Hello")
        ctx.log("ERROR", "Oops", extra="detail")
        logs = ctx.get_logs()
        assert len(logs) == 2
        assert logs[0]["level"] == "INFO"
        assert logs[0]["message"] == "Hello"
        assert logs[1]["level"] == "ERROR"

    def test_event_publishing(self):
        """测试事件发布"""
        config = PluginConfig()
        ctx = PluginContext("test", config)
        published = []
        ctx.set_event_publisher(lambda et, p, s: published.append((et, p, s)))
        ctx.emit_event("test_event", {"data": 1})
        assert len(published) == 1
        assert published[0][0] == "test_event"
        assert published[0][2] == "test"

    def test_to_dict(self):
        """测试导出"""
        config = PluginConfig(values={"key": "val"})
        ctx = PluginContext("test", config)
        ctx.register_service("svc", "service")
        d = ctx.to_dict()
        assert d["plugin_name"] == "test"
        assert "svc" in d["services"]
        assert d["config"] == {"key": "val"}


# ============================================================
# PluginEventBus 测试
# ============================================================

class TestPluginEventBus:
    """事件总线测试"""

    def test_subscribe_publish(self):
        """测试订阅发布"""
        bus = PluginEventBus()
        received = []
        bus.subscribe("test_event", lambda e: received.append(e))
        bus.publish_simple("test_event", {"data": 1}, "source1")
        assert len(received) == 1
        assert received[0].payload == {"data": 1}

    def test_multiple_subscribers(self):
        """测试多订阅者"""
        bus = PluginEventBus()
        results1 = []
        results2 = []
        bus.subscribe("evt", lambda e: results1.append(1))
        bus.subscribe("evt", lambda e: results2.append(2))
        bus.publish_simple("evt", None, "")
        assert len(results1) == 1
        assert len(results2) == 1

    def test_unsubscribe(self):
        """测试取消订阅"""
        bus = PluginEventBus()
        received = []
        handler = lambda e: received.append(e)
        bus.subscribe("evt", handler)
        bus.publish_simple("evt", None, "")
        assert len(received) == 1
        assert bus.unsubscribe("evt", handler)
        bus.publish_simple("evt", None, "")
        assert len(received) == 1  # 没有新增

    def test_wildcard_subscription(self):
        """测试通配符订阅"""
        bus = PluginEventBus()
        received = []
        bus.subscribe("*", lambda e: received.append(e))
        bus.publish_simple("event_a", None, "")
        bus.publish_simple("event_b", None, "")
        assert len(received) == 2

    def test_response_collection(self):
        """测试响应收集"""
        bus = PluginEventBus()
        bus.subscribe("evt", lambda e: "response1")
        bus.subscribe("evt", lambda e: "response2")
        responses = bus.publish_simple("evt", None, "")
        assert "response1" in responses
        assert "response2" in responses

    def test_subscriber_error_isolation(self):
        """测试订阅者错误隔离"""
        bus = PluginEventBus()
        bus.subscribe("evt", lambda e: (_ for _ in ()).throw(RuntimeError("fail")))
        bus.subscribe("evt", lambda e: "ok")
        responses = bus.publish_simple("evt", None, "")
        # 错误的订阅者返回None，不影响其他
        assert None in responses
        assert "ok" in responses

    def test_event_history(self):
        """测试事件历史"""
        bus = PluginEventBus()
        bus.publish_simple("a", None, "")
        bus.publish_simple("b", None, "")
        bus.publish_simple("a", None, "")
        history = bus.get_history()
        assert len(history) == 3
        a_events = bus.get_history(event_type="a")
        assert len(a_events) == 2

    def test_stats(self):
        """测试统计"""
        bus = PluginEventBus()
        bus.subscribe("evt1", lambda e: None)
        bus.subscribe("evt1", lambda e: None)
        bus.subscribe("evt2", lambda e: None)
        bus.publish_simple("evt1", None, "")
        stats = bus.get_stats()
        assert stats["event_types"] >= 2
        assert stats["total_subscribers"] >= 3
        assert stats["events_published"] >= 1

    def test_clear(self):
        """测试清空"""
        bus = PluginEventBus()
        bus.subscribe("evt", lambda e: None)
        bus.publish_simple("evt", None, "")
        bus.clear()
        stats = bus.get_stats()
        assert stats["events_published"] == 0


# ============================================================
# PluginLoader 测试
# ============================================================

class TestPluginLoader:
    """插件加载器测试"""

    def test_discover_directory(self, tmp_path):
        """测试目录发现"""
        # 创建插件文件
        plugin_file = tmp_path / "my_plugin.py"
        plugin_file.write_text(textwrap.dedent("""
            from self_evolving_agent.core.plugin_system import Plugin, PluginInfo

            class MyPlugin(Plugin):
                @property
                def info(self):
                    return PluginInfo(name="my_plugin", version="1.0.0")
        """))
        loader = PluginLoader()
        discovered = loader.discover_directory(str(tmp_path))
        assert len(discovered) == 1
        assert "my_plugin.py" in discovered[0]

    def test_load_from_file(self, tmp_path):
        """测试从文件加载"""
        plugin_file = tmp_path / "test_plugin.py"
        plugin_file.write_text(textwrap.dedent("""
            from self_evolving_agent.core.plugin_system import Plugin, PluginInfo

            class TestPlugin(Plugin):
                @property
                def info(self):
                    return PluginInfo(name="file_plugin", version="1.0.0")
        """))
        loader = PluginLoader()
        plugin = loader.load_from_file(str(plugin_file))
        assert plugin is not None
        assert plugin.info.name == "file_plugin"

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        loader = PluginLoader()
        assert loader.load_from_file("/nonexistent/file.py") is None

    def test_discover_empty_directory(self, tmp_path):
        """测试空目录"""
        loader = PluginLoader()
        discovered = loader.discover_directory(str(tmp_path))
        assert discovered == []

    def test_discover_nonexistent_directory(self):
        """测试不存在的目录"""
        loader = PluginLoader()
        assert loader.discover_directory("/nonexistent/dir") == []

    def test_add_search_path(self, tmp_path):
        """测试添加搜索路径"""
        loader = PluginLoader()
        loader.add_search_path(str(tmp_path))
        assert len(loader._search_paths) == 1


# ============================================================
# EnhancedPlugin 测试
# ============================================================

class TestEnhancedPlugin:
    """增强插件测试"""

    def test_plugin_manifest(self):
        """测试插件清单"""
        plugin = CounterPlugin()
        m = plugin.manifest
        assert m.name == "counter"
        assert m.version == "1.2.0"

    def test_backward_compatible_info(self):
        """测试向后兼容info"""
        plugin = CounterPlugin()
        info = plugin.info
        assert info.name == "counter"
        assert info.version == "1.2.0"

    def test_default_health_check(self):
        """测试默认健康检查"""
        plugin = CounterPlugin()
        # 需先初始化才能进行健康检查
        config = PluginConfig(schema=plugin.manifest.config_schema)
        ctx = PluginContext("counter", config)
        plugin.initialize_with_context(ctx)
        result = plugin.health_check()
        assert result.status == PluginHealthStatus.HEALTHY

    def test_initialize_with_context(self):
        """测试上下文初始化"""
        plugin = CounterPlugin()
        config = PluginConfig(
            schema=plugin.manifest.config_schema,
            values={"initial_value": 10, "step": 5},
        )
        ctx = PluginContext("counter", config)
        assert plugin.initialize_with_context(ctx)
        assert plugin.get_count() == 10


# ============================================================
# EnhancedPluginManager 测试
# ============================================================

class TestEnhancedPluginManager:
    """增强插件管理器测试"""

    def test_load_enhanced_plugin(self):
        """测试加载增强插件"""
        mgr = create_enhanced_plugin_manager()
        plugin = CounterPlugin()
        assert mgr.load_enhanced(plugin, {"initial_value": 5, "step": 2})
        assert mgr.registry.get_state("counter") == PluginState.ACTIVE

    def test_load_with_default_config(self):
        """测试默认配置加载"""
        mgr = create_enhanced_plugin_manager()
        plugin = CounterPlugin()
        assert mgr.load_enhanced(plugin)
        config = mgr.get_config("counter")
        assert config is not None

    def test_get_manifest(self):
        """测试获取清单"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin())
        m = mgr.get_manifest("counter")
        assert m is not None
        assert m.name == "counter"

    def test_get_context(self):
        """测试获取上下文"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin())
        ctx = mgr.get_context("counter")
        assert ctx is not None
        assert ctx.name == "counter"

    def test_unload(self):
        """测试卸载"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin())
        assert mgr.unload("counter")
        assert mgr.registry.get("counter") is None
        assert mgr.get_config("counter") is None

    def test_reload(self):
        """测试热重载"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin(), {"initial_value": 10})
        assert mgr.reload("counter")
        assert mgr.registry.get_state("counter") == PluginState.ACTIVE
        # 配置应保留
        config = mgr.get_config("counter")
        assert config.get("initial_value") == 10

    def test_load_order(self):
        """测试加载顺序"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin())
        mgr.load_enhanced(DependentPlugin())
        order = mgr.get_load_order()
        assert order == ["counter", "dependent"]

    def test_dependency_check(self):
        """测试依赖检查"""
        mgr = create_enhanced_plugin_manager()
        # 不先加载counter，直接加载dependent
        assert not mgr.load_enhanced(DependentPlugin())
        assert mgr.registry.get_state("dependent") == PluginState.FAILED

    def test_version_incompatibility(self):
        """测试版本不兼容"""
        mgr = create_enhanced_plugin_manager("1.0.0")
        assert not mgr.load_enhanced(IncompatiblePlugin())
        assert mgr.registry.get_state("incompatible") == PluginState.FAILED

    def test_config_validation_failure(self):
        """测试配置校验失败"""
        mgr = create_enhanced_plugin_manager()
        plugin = ConfigValidatorPlugin()
        # 缺少必填的api_key
        assert not mgr.load_enhanced(plugin, {"timeout": 50})
        assert mgr.registry.get_state("config_validator") == PluginState.FAILED

    def test_config_validation_success(self):
        """测试配置校验成功"""
        mgr = create_enhanced_plugin_manager()
        plugin = ConfigValidatorPlugin()
        assert mgr.load_enhanced(plugin, {
            "api_key": "secret",
            "timeout": 60,
            "mode": "fast",
        })
        assert mgr.registry.get_state("config_validator") == PluginState.ACTIVE

    def test_update_config(self):
        """测试更新配置"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin(), {"initial_value": 0})
        valid, errors = mgr.update_config("counter", {"step": 10})
        assert valid
        config = mgr.get_config("counter")
        assert config.get("step") == 10

    def test_update_config_nonexistent(self):
        """测试更新不存在插件的配置"""
        mgr = create_enhanced_plugin_manager()
        valid, errors = mgr.update_config("nonexistent", {"key": "val"})
        assert not valid

    def test_health_check_active(self):
        """测试活跃插件健康检查"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin())
        result = mgr.check_health("counter")
        assert result.status == PluginHealthStatus.HEALTHY

    def test_health_check_nonexistent(self):
        """测试不存在插件健康检查"""
        mgr = create_enhanced_plugin_manager()
        result = mgr.check_health("nonexistent")
        assert result.status == PluginHealthStatus.UNKNOWN

    def test_check_all_health(self):
        """测试全量健康检查"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin())
        results = mgr.check_all_health()
        assert "counter" in results
        assert results["counter"].status == PluginHealthStatus.HEALTHY

    def test_register_custom_health_check(self):
        """测试自定义健康检查"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin())
        mgr.register_health_check("counter", lambda: PluginHealthResult(
            plugin_name="counter",
            status=PluginHealthStatus.DEGRADED,
            message="custom",
        ))
        result = mgr.check_health("counter")
        assert result.status == PluginHealthStatus.DEGRADED

    def test_event_bus_integration(self):
        """测试事件总线集成"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin(), {"initial_value": 0, "step": 1})

        received = []
        mgr.subscribe_event("on_increment", lambda e: received.append(e))

        plugin = mgr.registry.get("counter")
        plugin.increment()

        assert len(received) == 1
        assert received[0].event_type == "on_increment"

    def test_global_services(self):
        """测试全局服务"""
        mgr = create_enhanced_plugin_manager()
        mgr.register_global_service("database", {"url": "localhost"})
        mgr.load_enhanced(CounterPlugin())
        ctx = mgr.get_context("counter")
        assert ctx.get_service("database") == {"url": "localhost"}

    def test_shutdown(self):
        """测试关闭"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin())
        mgr.load_enhanced(DependentPlugin())
        mgr.shutdown()
        assert mgr.get_load_order() == []

    def test_stats(self):
        """测试统计"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin())
        stats = mgr.get_stats()
        assert stats["system_version"] == "1.0.0"
        assert "counter" in stats["load_order"]
        assert stats["enhanced_plugins"] >= 1

    def test_get_manifests(self):
        """测试获取所有清单"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin())
        manifests = mgr.get_manifests()
        assert "counter" in manifests


# ============================================================
# 向后兼容测试
# ============================================================

class TestBackwardCompatibility:
    """向后兼容测试"""

    def test_old_plugin_with_enhanced_manager(self):
        """测试旧版插件在增强管理器中使用"""
        mgr = create_enhanced_plugin_manager()
        plugin = SimplePlugin()
        assert mgr.load(plugin)
        assert mgr.registry.get_state("simple") == PluginState.ACTIVE

    def test_old_plugin_manager_still_works(self):
        """测试旧版管理器仍可用"""
        mgr = create_plugin_manager()
        plugin = SimplePlugin()
        assert mgr.load(plugin)
        assert mgr.registry.get_state("simple") == PluginState.ACTIVE

    def test_old_registry_still_works(self):
        """测试旧版注册表仍可用"""
        registry = PluginRegistry()
        plugin = SimplePlugin()
        registry.register(plugin)
        assert registry.get("simple") is not None
        assert registry.get_state("simple") == PluginState.REGISTERED

    def test_enhanced_plugin_info_property(self):
        """测试增强插件的info属性"""
        plugin = CounterPlugin()
        info = plugin.info
        assert isinstance(info, PluginInfo)
        assert info.name == "counter"


# ============================================================
# 错误隔离测试
# ============================================================

class TestErrorIsolation:
    """错误隔离测试"""

    def test_failing_plugin_does_not_crash(self):
        """测试失败插件不崩溃系统"""
        mgr = create_enhanced_plugin_manager()
        plugin = FailingPlugin()
        assert not mgr.load_enhanced(plugin)
        assert mgr.registry.get_state("failing") == PluginState.FAILED
        # 系统仍可加载其他插件
        assert mgr.load_enhanced(CounterPlugin())

    def test_event_subscriber_error_isolation(self):
        """测试事件订阅者错误隔离"""
        bus = PluginEventBus()

        def bad_handler(e):
            raise RuntimeError("handler error")

        bus.subscribe("evt", bad_handler)
        bus.subscribe("evt", lambda e: "ok")
        responses = bus.publish_simple("evt", None, "")
        assert None in responses  # 错误的返回None
        assert "ok" in responses

    def test_config_listener_error_isolation(self):
        """测试配置监听器错误隔离"""
        config = PluginConfig()

        def bad_listener(key, old, new):
            raise RuntimeError("listener error")

        config.on_change(bad_listener)
        # 不应抛出异常
        config.set("key", "value")

    def test_health_check_error_isolation(self):
        """测试健康检查错误隔离"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin())

        def bad_check():
            raise RuntimeError("check error")

        mgr.register_health_check("counter", bad_check)
        result = mgr.check_health("counter")
        assert result.status == PluginHealthStatus.UNHEALTHY


# ============================================================
# 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_extensibility_principle(self):
        """第一性原理：可扩展性 — 第三方可添加功能"""
        mgr = create_enhanced_plugin_manager()
        # 自定义插件
        class CustomPlugin(EnhancedPlugin):
            @property
            def manifest(self):
                return PluginManifest(name="custom", version="1.0.0")

            def custom_method(self):
                return "custom_result"

        plugin = CustomPlugin()
        assert mgr.load_enhanced(plugin)
        loaded = mgr.registry.get("custom")
        assert loaded.custom_method() == "custom_result"

    def test_isolation_principle(self):
        """第一性原理：隔离性 — 插件故障不传播"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin())

        # 一个插件失败不影响其他
        assert not mgr.load_enhanced(FailingPlugin())
        assert mgr.registry.get_state("counter") == PluginState.ACTIVE

    def test_discoverability_principle(self, tmp_path):
        """第一性原理：可发现性 — 自动发现插件"""
        plugin_file = tmp_path / "auto_plugin.py"
        plugin_file.write_text(textwrap.dedent("""
            from self_evolving_agent.core.plugin_system import Plugin, PluginInfo

            class AutoPlugin(Plugin):
                @property
                def info(self):
                    return PluginInfo(name="auto", version="1.0.0")
        """))
        mgr = create_enhanced_plugin_manager()
        results = mgr.discover_and_load(str(tmp_path))
        assert "auto" in results
        assert results["auto"]

    def test_configurability_principle(self):
        """第一性原理：可配置性 — 配置校验"""
        mgr = create_enhanced_plugin_manager()
        plugin = ConfigValidatorPlugin()
        # 无效配置被拒绝
        assert not mgr.load_enhanced(plugin, {"timeout": 999})
        # 有效配置被接受
        assert mgr.load_enhanced(plugin, {"api_key": "key", "mode": "fast"})

    def test_observability_principle(self):
        """第一性原理：可观测性 — 状态可监控"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin())

        # 状态可见
        assert mgr.registry.get_state("counter") == PluginState.ACTIVE
        # 健康可见
        health = mgr.check_health("counter")
        assert health.status == PluginHealthStatus.HEALTHY
        # 统计可见
        stats = mgr.get_stats()
        assert stats["total_plugins"] >= 1

    def test_hot_reload_principle(self):
        """第一性原理：热更新 — 无需重启"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin(), {"initial_value": 5})
        # 热重载
        assert mgr.reload("counter")
        # 状态恢复
        assert mgr.registry.get_state("counter") == PluginState.ACTIVE
        # 配置保留
        config = mgr.get_config("counter")
        assert config.get("initial_value") == 5

    def test_lifecycle_completeness_principle(self):
        """第一性原理：生命周期完整性"""
        mgr = create_enhanced_plugin_manager()
        plugin = CounterPlugin()

        # 加载
        assert mgr.load_enhanced(plugin)
        assert mgr.registry.get_state("counter") == PluginState.ACTIVE

        # 运行
        plugin.increment()
        assert plugin.get_count() > 0

        # 健康检查
        assert mgr.check_health("counter").status == PluginHealthStatus.HEALTHY

        # 卸载
        assert mgr.unload("counter")
        assert mgr.registry.get("counter") is None

    def test_decoupled_communication_principle(self):
        """第一性原理：解耦通信 — 通过事件总线"""
        mgr = create_enhanced_plugin_manager()
        mgr.load_enhanced(CounterPlugin(), {"initial_value": 0, "step": 1})

        # 插件A发布事件，插件B订阅
        received = []
        mgr.subscribe_event("on_increment", lambda e: received.append(e.payload))

        plugin = mgr.registry.get("counter")
        plugin.increment()
        plugin.increment()

        assert len(received) == 2
        assert received[0]["count"] == 1
        assert received[1]["count"] == 2
