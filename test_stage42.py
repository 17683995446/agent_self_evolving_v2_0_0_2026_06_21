"""
阶段42测试: 插件系统接口标准化
"""
import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.plugin_system import (
    Plugin, PluginInfo, PluginState, PluginRegistry,
    PluginManager, create_plugin_manager
)


class TestPlugin(Plugin):
    """测试插件"""

    def __init__(self, name="test", version="1.0", hooks=None, deps=None):
        self._info = PluginInfo(
            name=name,
            version=version,
            description="Test plugin",
            hooks=hooks or [],
            dependencies=deps or [],
        )
        self.initialized = False
        self.started = False
        self.stopped = False
        self.unloaded = False
        self.events = []

    @property
    def info(self) -> PluginInfo:
        return self._info

    def initialize(self, context):
        self.initialized = True
        return True

    def start(self):
        self.started = True
        return True

    def stop(self):
        self.stopped = True
        return True

    def unload(self):
        self.unloaded = True
        return True

    def on_event(self, event_type, payload):
        self.events.append((event_type, payload))
        return f"handled:{payload}"


class FailingPlugin(Plugin):
    """失败插件"""

    def __init__(self, fail_at="init"):
        self._info = PluginInfo(name="failing", version="1.0")
        self.fail_at = fail_at

    @property
    def info(self):
        return self._info

    def initialize(self, context):
        if self.fail_at == "init":
            raise RuntimeError("Init failed")
        return True

    def start(self):
        if self.fail_at == "start":
            return False
        return True


def test_plugin_lifecycle():
    """测试插件完整生命周期"""
    manager = PluginManager()
    plugin = TestPlugin(name="lifecycle")

    success = manager.load(plugin)
    assert success is True
    assert plugin.initialized is True
    assert plugin.started is True
    assert manager.registry.get_state("lifecycle") == PluginState.ACTIVE

    success = manager.unload("lifecycle")
    assert success is True
    assert plugin.stopped is True
    assert plugin.unloaded is True
    print("  [test_plugin_lifecycle] 插件生命周期 ✓")


def test_plugin_registry():
    """测试插件注册表"""
    registry = PluginRegistry()
    plugin = TestPlugin(name="reg_test")

    registry.register(plugin)
    assert registry.get("reg_test") is plugin
    assert registry.get_state("reg_test") == PluginState.REGISTERED

    states = registry.list_plugins()
    assert "reg_test" in states

    registry.unregister("reg_test")
    assert registry.get("reg_test") is None
    print("  [test_plugin_registry] 注册表 ✓")


def test_plugin_hooks():
    """测试插件钩子"""
    manager = PluginManager()
    plugin = TestPlugin(name="hook_plugin", hooks=["on_predict", "on_train"])

    manager.load(plugin)
    responses = manager.emit("on_predict", "data1")

    assert len(responses) == 1
    assert responses[0] == "handled:data1"
    assert len(plugin.events) == 1

    # 未订阅的钩子不应触发
    responses2 = manager.emit("on_unknown", "data2")
    assert len(responses2) == 0
    print("  [test_plugin_hooks] 插件钩子 ✓")


def test_plugin_dependencies():
    """测试插件依赖"""
    manager = PluginManager()
    base = TestPlugin(name="base")
    dependent = TestPlugin(name="dependent", deps=["base"])

    # 先加载依赖
    assert manager.load(base) is True
    assert manager.load(dependent) is True
    assert manager.registry.get_state("dependent") == PluginState.ACTIVE

    print("  [test_plugin_dependencies] 插件依赖 ✓")


def test_plugin_missing_dependency():
    """测试缺失依赖"""
    manager = PluginManager()
    plugin = TestPlugin(name="orphan", deps=["missing"])

    success = manager.load(plugin)
    assert success is False
    assert manager.registry.get_state("orphan") == PluginState.FAILED
    print("  [test_plugin_missing_dependency] 缺失依赖 ✓")


def test_plugin_init_failure():
    """测试初始化失败"""
    manager = PluginManager()
    plugin = FailingPlugin(fail_at="init")

    success = manager.load(plugin)
    assert success is False
    assert manager.registry.get_state("failing") == PluginState.FAILED
    print("  [test_plugin_init_failure] 初始化失败 ✓")


def test_plugin_start_failure():
    """测试启动失败"""
    manager = PluginManager()
    plugin = FailingPlugin(fail_at="start")

    success = manager.load(plugin)
    assert success is False
    assert manager.registry.get_state("failing") == PluginState.FAILED
    print("  [test_plugin_start_failure] 启动失败 ✓")


def test_plugin_isolation():
    """测试插件异常隔离"""
    manager = PluginManager()

    class BadPlugin(Plugin):
        @property
        def info(self):
            return PluginInfo(name="bad", version="1.0", hooks=["test"])

        def on_event(self, event_type, payload):
            raise RuntimeError("I always fail")

    good = TestPlugin(name="good", hooks=["test"])
    bad = BadPlugin()

    manager.load(good)
    manager.load(bad)

    # bad 插件抛异常不应影响 good 插件
    responses = manager.emit("test", "data")
    assert len(responses) == 1
    assert responses[0] == "handled:data"
    print("  [test_plugin_isolation] 异常隔离 ✓")


def test_plugin_stats():
    """测试插件统计"""
    manager = PluginManager()

    manager.load(TestPlugin(name="p1"))
    manager.load(TestPlugin(name="p2", hooks=["h1"]))
    manager.load(FailingPlugin())

    stats = manager.get_stats()
    assert stats["total_plugins"] == 3
    assert stats["state_counts"]["active"] == 2
    assert stats["state_counts"]["failed"] == 1
    assert stats["hooks"]["h1"] == 1
    print("  [test_plugin_stats] 统计信息 ✓")


def test_duplicate_registration():
    """测试重复注册"""
    registry = PluginRegistry()
    plugin = TestPlugin(name="dup")

    registry.register(plugin)
    try:
        registry.register(plugin)
        assert False, "应抛出异常"
    except ValueError as e:
        assert "already registered" in str(e)
    print("  [test_duplicate_registration] 重复注册 ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("阶段42测试: 插件系统接口标准化")
    print("=" * 60)

    test_plugin_lifecycle()
    test_plugin_registry()
    test_plugin_hooks()
    test_plugin_dependencies()
    test_plugin_missing_dependency()
    test_plugin_init_failure()
    test_plugin_start_failure()
    test_plugin_isolation()
    test_plugin_stats()
    test_duplicate_registration()

    print("=" * 60)
    print("全部10项测试通过 ✓")
    print("=" * 60)
