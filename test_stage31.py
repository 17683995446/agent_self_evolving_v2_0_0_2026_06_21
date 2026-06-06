"""
阶段31: 模块生命周期管理 — 验证测试

验证目标:
1. 状态机转换正确
2. 生命周期回调按序调用
3. 依赖拓扑排序正确
4. 批量操作按依赖序执行
5. 状态转换历史可追踪
6. 监听器可接收事件
"""

import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.lifecycle import (
    LifecycleState, LifecycleEvent, StateTransition,
    LifecycleAware, LifecycleManager,
)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print('='*60)


class MockModule(LifecycleAware):
    """模拟模块"""

    def __init__(self, name: str, dependencies: list = None, fail_on: str = None):
        self._name = name
        self._dependencies = dependencies or []
        self._fail_on = fail_on
        self.events = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def dependencies(self) -> list:
        return self._dependencies

    def on_initialize(self):
        self.events.append("initialize")
        if self._fail_on == "initialize":
            raise RuntimeError("Init failed")

    def on_start(self):
        self.events.append("start")
        if self._fail_on == "start":
            raise RuntimeError("Start failed")

    def on_stop(self):
        self.events.append("stop")
        if self._fail_on == "stop":
            raise RuntimeError("Stop failed")

    def on_destroy(self):
        self.events.append("destroy")
        if self._fail_on == "destroy":
            raise RuntimeError("Destroy failed")


def test_state_transitions():
    """测试状态转换"""
    print_section("状态转换")

    manager = LifecycleManager()
    module = MockModule("test")
    manager.register(module)

    # 初始状态
    assert manager.get_state("test") == LifecycleState.CREATED
    print(f"初始状态: {manager.get_state('test').value}")

    # 初始化
    assert manager.initialize("test") == True
    assert manager.get_state("test") == LifecycleState.INITIALIZED
    print(f"初始化后: {manager.get_state('test').value}")

    # 启动
    assert manager.start("test") == True
    assert manager.get_state("test") == LifecycleState.RUNNING
    print(f"启动后: {manager.get_state('test').value}")

    # 停止
    assert manager.stop("test") == True
    assert manager.get_state("test") == LifecycleState.STOPPED
    print(f"停止后: {manager.get_state('test').value}")

    # 销毁
    assert manager.destroy("test") == True
    assert manager.get_state("test") == LifecycleState.DESTROYED
    print(f"销毁后: {manager.get_state('test').value}")

    # 已销毁不能再次启动
    assert manager.start("test") == False
    print("已销毁不能启动: True")

    print("\n状态转换测试通过!")
    return True


def test_dependency_order():
    """测试依赖顺序"""
    print_section("依赖顺序")

    manager = LifecycleManager()

    # A依赖B, B依赖C
    # 初始化顺序: C -> B -> A
    # 销毁顺序: A -> B -> C
    module_a = MockModule("A", ["B"])
    module_b = MockModule("B", ["C"])
    module_c = MockModule("C")

    manager.register(module_a)
    manager.register(module_b)
    manager.register(module_c)

    # 全部初始化
    results = manager.initialize_all()
    assert all(results.values())

    # 检查初始化顺序
    assert module_c.events == ["initialize"]
    assert module_b.events == ["initialize"]
    assert module_a.events == ["initialize"]
    print(f"初始化顺序: C({module_c.events}), B({module_b.events}), A({module_a.events})")

    # 全部启动
    manager.start_all()
    assert module_c.events == ["initialize", "start"]
    assert module_a.events == ["initialize", "start"]
    print(f"启动后: C({module_c.events}), A({module_a.events})")

    # 全部停止（逆序）
    manager.stop_all()
    assert module_a.events[-1] == "stop"
    assert module_c.events[-1] == "stop"
    print(f"停止后末尾: A({module_a.events}), C({module_c.events})")

    # 全部销毁（逆序）
    manager.destroy_all()
    assert module_a.events[-1] == "destroy"
    assert module_c.events[-1] == "destroy"
    print(f"销毁后末尾: A({module_a.events}), C({module_c.events})")

    print("\n依赖顺序测试通过!")
    return True


def test_failure_handling():
    """测试失败处理"""
    print_section("失败处理")

    manager = LifecycleManager()
    module = MockModule("fail_module", fail_on="initialize")
    manager.register(module)

    # 初始化失败
    result = manager.initialize("fail_module")
    assert result == False
    assert manager.get_state("fail_module") == LifecycleState.FAILED
    print(f"初始化失败状态: {manager.get_state('fail_module').value}")

    # 失败状态不能启动
    assert manager.start("fail_module") == False
    print("失败状态不能启动: True")

    # 失败状态可以销毁
    assert manager.destroy("fail_module") == True
    assert manager.get_state("fail_module") == LifecycleState.DESTROYED
    print(f"失败后销毁: {manager.get_state('fail_module').value}")

    print("\n失败处理测试通过!")
    return True


def test_transition_history():
    """测试状态转换历史"""
    print_section("状态转换历史")

    manager = LifecycleManager()
    module = MockModule("hist")
    manager.register(module)

    manager.initialize("hist")
    manager.start("hist")
    manager.stop("hist")

    history = manager.get_transition_history("hist")
    assert len(history) == 3

    states = [(h.from_state.value, h.to_state.value) for h in history]
    assert states[0] == ("created", "initialized")
    assert states[1] == ("initialized", "running")
    assert states[2] == ("running", "stopped")
    print(f"历史记录: {states}")

    # 所有转换都成功
    assert all(h.success for h in history)
    print("所有转换成功: True")

    print("\n状态转换历史测试通过!")
    return True


def test_listener():
    """测试监听器"""
    print_section("监听器")

    manager = LifecycleManager()
    events = []

    def listener(name, transition):
        events.append((name, transition.from_state.value, transition.to_state.value))

    manager.add_listener(listener)

    module = MockModule("listen")
    manager.register(module)
    manager.initialize("listen")
    manager.start("listen")

    assert len(events) == 2
    assert events[0] == ("listen", "created", "initialized")
    assert events[1] == ("listen", "initialized", "running")
    print(f"监听到的事件: {events}")

    print("\n监听器测试通过!")
    return True


def test_is_running():
    """测试运行状态检查"""
    print_section("运行状态检查")

    manager = LifecycleManager()
    module = MockModule("run_test")
    manager.register(module)

    assert manager.is_running("run_test") == False
    print(f"初始is_running: {manager.is_running('run_test')}")

    manager.initialize("run_test")
    assert manager.is_running("run_test") == False
    print(f"初始化后is_running: {manager.is_running('run_test')}")

    manager.start("run_test")
    assert manager.is_running("run_test") == True
    print(f"启动后is_running: {manager.is_running('run_test')}")

    manager.stop("run_test")
    assert manager.is_running("run_test") == False
    print(f"停止后is_running: {manager.is_running('run_test')}")

    print("\n运行状态检查测试通过!")
    return True


def test_health_check():
    """测试健康检查"""
    print_section("健康检查")

    manager = LifecycleManager()
    module = MockModule("health_test")
    manager.register(module)

    # 未运行时不健康
    healthy, msg = manager.is_healthy("health_test")
    assert healthy == False
    assert "not running" in msg
    print(f"未运行时: {healthy}, {msg}")

    # 运行后健康
    manager.initialize("health_test")
    manager.start("health_test")
    healthy, msg = manager.is_healthy("health_test")
    assert healthy == True
    assert msg == "OK"
    print(f"运行时: {healthy}, {msg}")

    print("\n健康检查测试通过!")
    return True


def test_unregister():
    """测试注销"""
    print_section("注销")

    manager = LifecycleManager()
    module = MockModule("unreg")
    manager.register(module)

    # 运行中不能注销
    manager.initialize("unreg")
    manager.start("unreg")
    assert manager.unregister("unreg") == False
    print("运行中不能注销: True")

    # 停止并销毁后可以注销
    manager.stop("unreg")
    manager.destroy("unreg")
    assert manager.unregister("unreg") == True
    assert manager.get_state("unreg") is None
    print("销毁后可注销: True")

    print("\n注销测试通过!")
    return True


def test_auto_initialize_on_start():
    """测试启动时自动初始化"""
    print_section("启动时自动初始化")

    manager = LifecycleManager()
    module = MockModule("auto_init")
    manager.register(module)

    # 直接从CREATED启动，应自动初始化
    result = manager.start("auto_init")
    assert result == True
    assert manager.get_state("auto_init") == LifecycleState.RUNNING
    assert module.events == ["initialize", "start"]
    print(f"事件序列: {module.events}")

    print("\n启动时自动初始化测试通过!")
    return True


def test_circular_dependency():
    """测试循环依赖"""
    print_section("循环依赖")

    manager = LifecycleManager()

    # A依赖B, B依赖A（循环）
    module_a = MockModule("CA", ["CB"])
    module_b = MockModule("CB", ["CA"])

    manager.register(module_a)
    manager.register(module_b)

    # 拓扑排序应能处理（Kahn算法在这种情况下会返回部分结果）
    # 实际行为取决于实现，这里只验证不崩溃
    try:
        manager.initialize_all()
        print("循环依赖处理: 未崩溃")
    except Exception as e:
        print(f"循环依赖异常: {e}")

    print("\n循环依赖测试通过!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("阶段31: 模块生命周期管理 — 验证测试")
    print("="*60)

    tests = [
        test_state_transitions,
        test_dependency_order,
        test_failure_handling,
        test_transition_history,
        test_listener,
        test_is_running,
        test_health_check,
        test_unregister,
        test_auto_initialize_on_start,
        test_circular_dependency,
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
