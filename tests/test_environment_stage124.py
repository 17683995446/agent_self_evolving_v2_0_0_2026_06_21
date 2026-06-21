"""
阶段124: 真实环境接入层 — 专项测试

验证:
1. EnvironmentInterface抽象接口
2. SimulatedEnvironment模拟环境（向后兼容）
3. FilesystemEnvironment文件系统环境
4. HTTPEnvironment HTTP环境
5. CommandEnvironment命令行环境
6. EnvironmentManager多环境管理
7. Agent集成
8. 安全性（路径穿越、命令白名单）
9. 并发安全、性能、异常容错
10. 第一性原理验证
"""

import os
import tempfile
import threading
import time
import pytest

from self_evolving_agent.core.environment_interface import (
    EnvironmentType,
    EnvironmentState,
    EnvironmentAction,
    ActionResult,
    EnvironmentInterface,
    SimulatedEnvironment,
    FilesystemEnvironment,
    HTTPEnvironment,
    CommandEnvironment,
    EnvironmentManager,
    create_simulated_environment,
    create_filesystem_environment,
    create_http_environment,
    create_command_environment,
    create_environment_manager,
    create_environment_action,
)


# ============================================================
# 1. 数据结构测试
# ============================================================

class TestDataStructures:
    """数据结构测试"""

    def test_environment_type_enum(self):
        """环境类型枚举"""
        assert EnvironmentType.SIMULATED.value == "simulated"
        assert EnvironmentType.FILESYSTEM.value == "filesystem"
        assert EnvironmentType.HTTP.value == "http"
        assert EnvironmentType.COMMAND.value == "command"
        assert EnvironmentType.COMPOSITE.value == "composite"

    def test_environment_state_creation(self):
        """环境状态创建"""
        state = EnvironmentState(
            env_type=EnvironmentType.SIMULATED,
            source="test",
            data={"key": "value"},
        )
        assert state.env_type == EnvironmentType.SIMULATED
        assert state.source == "test"
        assert state.data == {"key": "value"}
        assert state.timestamp > 0

    def test_environment_state_to_dict(self):
        """环境状态转字典"""
        state = EnvironmentState(
            env_type=EnvironmentType.FILESYSTEM,
            source="fs",
            data={"entries": ["a", "b"]},
        )
        d = state.to_dict()
        assert d["env_type"] == "filesystem"
        assert d["source"] == "fs"
        assert d["data"] == {"entries": ["a", "b"]}

    def test_environment_action_creation(self):
        """环境动作创建"""
        action = EnvironmentAction(
            action_type="read",
            target="file.txt",
            parameters={"encoding": "utf-8"},
        )
        assert action.action_type == "read"
        assert action.target == "file.txt"
        assert action.parameters == {"encoding": "utf-8"}

    def test_action_result_creation(self):
        """动作结果创建"""
        result = ActionResult(success=True, output={"data": "hello"})
        assert result.success is True
        assert result.output == {"data": "hello"}
        assert result.error is None
        assert result.duration == 0.0


# ============================================================
# 2. SimulatedEnvironment 测试
# ============================================================

class TestSimulatedEnvironment:
    """模拟环境测试"""

    def test_creation(self):
        """创建"""
        env = SimulatedEnvironment()
        assert env.env_id is not None

    def test_observe(self):
        """感知"""
        env = SimulatedEnvironment()
        state = env.observe()
        assert state.env_type == EnvironmentType.SIMULATED
        assert "cycle" in state.data
        assert "predicted" in state.data
        assert "actual" in state.data

    def test_observe_increments_cycle(self):
        """感知递增周期"""
        env = SimulatedEnvironment()
        s1 = env.observe()
        s2 = env.observe()
        assert s2.data["cycle"] == s1.data["cycle"] + 1

    def test_act(self):
        """执行动作"""
        env = SimulatedEnvironment()
        action = EnvironmentAction(action_type="test", target="x")
        result = env.act(action)
        assert result.success is True

    def test_get_capabilities(self):
        """获取能力"""
        env = SimulatedEnvironment()
        caps = env.get_capabilities()
        assert "observe" in caps
        assert "simulate" in caps

    def test_is_available(self):
        """可用性"""
        env = SimulatedEnvironment()
        assert env.is_available() is True

    def test_observer_notification(self):
        """观察者通知"""
        env = SimulatedEnvironment()
        received = []
        env.register_observer(lambda s: received.append(s))
        env.observe()
        assert len(received) == 1

    def test_action_history(self):
        """动作历史"""
        env = SimulatedEnvironment()
        env.act(EnvironmentAction(action_type="a", target="t"))
        env.act(EnvironmentAction(action_type="b", target="t"))
        history = env.get_action_history()
        assert len(history) == 2

    def test_stats(self):
        """统计"""
        env = SimulatedEnvironment()
        env.act(EnvironmentAction(action_type="a", target="t"))
        stats = env.get_stats()
        assert stats["total_actions"] == 1
        assert stats["successful_actions"] == 1


# ============================================================
# 3. FilesystemEnvironment 测试
# ============================================================

class TestFilesystemEnvironment:
    """文件系统环境测试"""

    def test_creation(self):
        """创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            assert env.is_available() is True

    def test_creation_nonexistent_path(self):
        """不存在路径创建失败"""
        with pytest.raises(ValueError):
            FilesystemEnvironment("/nonexistent/path/that/does/not/exist")

    def test_observe(self):
        """感知"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一些文件
            with open(os.path.join(tmpdir, "a.txt"), "w") as f:
                f.write("hello")
            os.mkdir(os.path.join(tmpdir, "subdir"))

            env = FilesystemEnvironment(tmpdir)
            state = env.observe()
            assert state.env_type == EnvironmentType.FILESYSTEM
            assert state.data["entry_count"] == 2

    def test_write_and_read(self):
        """写入和读取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)

            # 写入
            write_result = env.act(
                EnvironmentAction("write", "test.txt", {"content": "hello world"})
            )
            assert write_result.success is True
            assert write_result.output["size"] == 11

            # 读取
            read_result = env.act(EnvironmentAction("read", "test.txt"))
            assert read_result.success is True
            assert read_result.output["content"] == "hello world"

    def test_read_nonexistent(self):
        """读取不存在文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            result = env.act(EnvironmentAction("read", "nonexistent.txt"))
            assert result.success is False
            assert "not found" in result.error.lower()

    def test_delete(self):
        """删除文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            env.act(EnvironmentAction("write", "to_delete.txt", {"content": "x"}))
            result = env.act(EnvironmentAction("delete", "to_delete.txt"))
            assert result.success is True
            assert not os.path.exists(os.path.join(tmpdir, "to_delete.txt"))

    def test_delete_nonexistent(self):
        """删除不存在文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            result = env.act(EnvironmentAction("delete", "nonexistent.txt"))
            assert result.success is False

    def test_list(self):
        """列出目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            env.act(EnvironmentAction("write", "a.txt", {"content": "1"}))
            env.act(EnvironmentAction("write", "b.txt", {"content": "2"}))
            result = env.act(EnvironmentAction("list", "."))
            assert result.success is True
            assert "a.txt" in result.output["entries"]
            assert "b.txt" in result.output["entries"]

    def test_mkdir(self):
        """创建目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            result = env.act(EnvironmentAction("mkdir", "new_dir"))
            assert result.success is True
            assert os.path.isdir(os.path.join(tmpdir, "new_dir"))

    def test_write_creates_parent_dirs(self):
        """写入自动创建父目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            result = env.act(
                EnvironmentAction("write", "sub/dir/file.txt", {"content": "x"})
            )
            assert result.success is True

    def test_path_traversal_blocked(self):
        """路径穿越防御"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            with pytest.raises(ValueError):
                env._safe_path("../../../etc/passwd")

    def test_absolute_path_traversal_blocked(self):
        """绝对路径穿越防御"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            with pytest.raises(ValueError):
                env._safe_path("/etc/passwd")

    def test_get_capabilities(self):
        """获取能力"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            caps = env.get_capabilities()
            assert "read" in caps
            assert "write" in caps
            assert "delete" in caps
            assert "list" in caps
            assert "mkdir" in caps

    def test_unknown_action(self):
        """未知动作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            result = env.act(EnvironmentAction("unknown_action", "x"))
            assert result.success is False

    def test_max_file_size(self):
        """文件大小限制"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir, max_file_size=10)
            env.act(EnvironmentAction("write", "big.txt", {"content": "x" * 100}))
            result = env.act(EnvironmentAction("read", "big.txt"))
            assert result.success is False
            assert "too large" in result.error.lower()


# ============================================================
# 4. HTTPEnvironment 测试
# ============================================================

class TestHTTPEnvironment:
    """HTTP环境测试"""

    def test_creation(self):
        """创建"""
        env = HTTPEnvironment("https://api.example.com")
        assert env.is_available() is True

    def test_creation_empty_url(self):
        """空URL创建失败"""
        with pytest.raises(ValueError):
            HTTPEnvironment("")

    def test_creation_with_headers(self):
        """带headers创建"""
        env = HTTPEnvironment(
            "https://api.example.com",
            headers={"Authorization": "Bearer token"},
        )
        assert env.is_available() is True

    def test_get_capabilities(self):
        """获取能力"""
        env = HTTPEnvironment("https://api.example.com")
        caps = env.get_capabilities()
        assert "GET" in caps
        assert "POST" in caps
        assert "PUT" in caps

    def test_observe_unreachable(self):
        """不可达URL感知"""
        env = HTTPEnvironment("http://localhost:1")  # 不可达端口
        env._timeout = 1.0
        state = env.observe()
        assert "error" in state.data

    def test_act_unreachable(self):
        """不可达URL动作"""
        env = HTTPEnvironment("http://localhost:1")
        env._timeout = 1.0
        result = env.act(EnvironmentAction("GET", "test"))
        assert result.success is False


# ============================================================
# 5. CommandEnvironment 测试
# ============================================================

class TestCommandEnvironment:
    """命令行环境测试"""

    def test_creation(self):
        """创建"""
        env = CommandEnvironment()
        assert env.is_available() is True

    def test_creation_with_allowlist(self):
        """带白名单创建"""
        env = CommandEnvironment(allowed_commands=["echo", "ls"])
        assert env.is_available() is True

    def test_observe(self):
        """感知"""
        env = CommandEnvironment()
        state = env.observe()
        assert state.env_type == EnvironmentType.COMMAND
        assert "platform" in state.data
        assert "python_version" in state.data

    def test_execute_allowed_command(self):
        """执行允许的命令"""
        env = CommandEnvironment(allowed_commands=["echo"])
        result = env.act(EnvironmentAction("execute", "echo hello"))
        assert result.success is True
        assert "hello" in result.output["stdout"]

    def test_execute_blocked_command(self):
        """执行被阻止的命令"""
        env = CommandEnvironment(allowed_commands=["echo"])
        result = env.act(EnvironmentAction("execute", "rm -rf /"))
        assert result.success is False
        assert "not allowed" in result.error.lower()

    def test_execute_empty_command(self):
        """执行空命令"""
        env = CommandEnvironment()
        result = env.act(EnvironmentAction("execute", ""))
        assert result.success is False

    def test_execute_any_when_no_allowlist(self):
        """无白名单时允许所有"""
        env = CommandEnvironment()
        result = env.act(EnvironmentAction("execute", "echo test"))
        assert result.success is True

    def test_get_capabilities_with_allowlist(self):
        """带白名单的能力"""
        env = CommandEnvironment(allowed_commands=["echo", "ls"])
        caps = env.get_capabilities()
        assert "echo" in caps
        assert "ls" in caps

    def test_get_capabilities_no_allowlist(self):
        """无白名单的能力"""
        env = CommandEnvironment()
        caps = env.get_capabilities()
        assert "execute_any" in caps

    def test_command_failure(self):
        """命令失败"""
        env = CommandEnvironment()
        result = env.act(EnvironmentAction("execute", "false"))
        assert result.success is False
        assert result.output["returncode"] != 0


# ============================================================
# 6. EnvironmentManager 测试
# ============================================================

class TestEnvironmentManager:
    """环境管理器测试"""

    def test_creation(self):
        """创建"""
        mgr = EnvironmentManager()
        assert mgr.manager_id is not None

    def test_register_and_get(self):
        """注册和获取"""
        mgr = EnvironmentManager()
        env = SimulatedEnvironment()
        mgr.register_environment("sim", env)
        assert mgr.get_environment("sim") is env

    def test_register_default(self):
        """注册默认环境"""
        mgr = EnvironmentManager()
        env = SimulatedEnvironment()
        mgr.register_environment("sim", env, is_default=True)
        assert mgr.get_default_environment() is env

    def test_first_registered_becomes_default(self):
        """第一个注册的成为默认"""
        mgr = EnvironmentManager()
        env1 = SimulatedEnvironment("e1")
        env2 = SimulatedEnvironment("e2")
        mgr.register_environment("e1", env1)
        mgr.register_environment("e2", env2)
        assert mgr.get_default_environment() is env1

    def test_unregister(self):
        """注销环境"""
        mgr = EnvironmentManager()
        mgr.register_environment("sim", SimulatedEnvironment())
        assert mgr.unregister_environment("sim") is True
        assert mgr.get_environment("sim") is None

    def test_unregister_nonexistent(self):
        """注销不存在环境"""
        mgr = EnvironmentManager()
        assert mgr.unregister_environment("nonexistent") is False

    def test_unregister_default_switches(self):
        """注销默认环境后切换"""
        mgr = EnvironmentManager()
        env1 = SimulatedEnvironment("e1")
        env2 = SimulatedEnvironment("e2")
        mgr.register_environment("e1", env1, is_default=True)
        mgr.register_environment("e2", env2)
        mgr.unregister_environment("e1")
        assert mgr.get_default_environment() is env2

    def test_observe_default(self):
        """感知默认环境"""
        mgr = EnvironmentManager()
        mgr.register_environment("sim", SimulatedEnvironment())
        state = mgr.observe()
        assert state is not None
        assert state.env_type == EnvironmentType.SIMULATED

    def test_observe_specific(self):
        """感知指定环境"""
        mgr = EnvironmentManager()
        mgr.register_environment("sim", SimulatedEnvironment())
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr.register_environment("fs", FilesystemEnvironment(tmpdir))
            state = mgr.observe("fs")
            assert state.env_type == EnvironmentType.FILESYSTEM

    def test_observe_nonexistent(self):
        """感知不存在环境"""
        mgr = EnvironmentManager()
        assert mgr.observe("nonexistent") is None

    def test_observe_all(self):
        """感知所有环境"""
        mgr = EnvironmentManager()
        mgr.register_environment("sim1", SimulatedEnvironment())
        mgr.register_environment("sim2", SimulatedEnvironment())
        states = mgr.observe_all()
        assert len(states) == 2
        assert "sim1" in states
        assert "sim2" in states

    def test_act_default(self):
        """在默认环境执行动作"""
        mgr = EnvironmentManager()
        mgr.register_environment("sim", SimulatedEnvironment())
        result = mgr.act(EnvironmentAction("test", "x"))
        assert result is not None
        assert result.success is True

    def test_act_specific(self):
        """在指定环境执行动作"""
        mgr = EnvironmentManager()
        mgr.register_environment("sim", SimulatedEnvironment())
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr.register_environment("fs", FilesystemEnvironment(tmpdir))
            result = mgr.act(EnvironmentAction("write", "f.txt", {"content": "x"}), "fs")
            assert result.success is True

    def test_act_nonexistent(self):
        """在不存在环境执行动作"""
        mgr = EnvironmentManager()
        result = mgr.act(EnvironmentAction("test", "x"), "nonexistent")
        assert result.success is False

    def test_get_all_stats(self):
        """获取所有统计"""
        mgr = EnvironmentManager()
        mgr.register_environment("sim", SimulatedEnvironment())
        mgr.act(EnvironmentAction("test", "x"))
        stats = mgr.get_all_stats()
        assert "sim" in stats
        assert stats["sim"]["total_actions"] == 1

    def test_get_environment_ids(self):
        """获取所有环境ID"""
        mgr = EnvironmentManager()
        mgr.register_environment("e1", SimulatedEnvironment())
        mgr.register_environment("e2", SimulatedEnvironment())
        ids = mgr.get_environment_ids()
        assert "e1" in ids
        assert "e2" in ids

    def test_clear_all_history(self):
        """清除所有历史"""
        mgr = EnvironmentManager()
        env = SimulatedEnvironment()
        mgr.register_environment("sim", env)
        mgr.act(EnvironmentAction("test", "x"))
        mgr.clear_all_history()
        assert len(env.get_action_history()) == 0


# ============================================================
# 7. Agent集成测试
# ============================================================

class TestAgentIntegration:
    """Agent集成测试"""

    def test_agent_has_env_manager(self):
        """Agent有环境管理器"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        assert agent.env_manager is not None

    def test_agent_default_simulated_env(self):
        """Agent默认模拟环境"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        state = agent._sense_environment()
        assert state["env_type"] == "simulated"

    def test_agent_register_filesystem_env(self):
        """Agent注册文件系统环境"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        with tempfile.TemporaryDirectory() as tmpdir:
            agent.register_environment(
                "fs",
                FilesystemEnvironment(tmpdir),
                is_default=True,
            )
            state = agent._sense_environment()
            assert state["env_type"] == "filesystem"

    def test_agent_set_default_environment(self):
        """Agent设置默认环境"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        with tempfile.TemporaryDirectory() as tmpdir:
            agent.register_environment("fs", FilesystemEnvironment(tmpdir))
            assert agent.set_default_environment("fs") is True
            state = agent._sense_environment()
            assert state["env_type"] == "filesystem"

    def test_agent_set_default_nonexistent(self):
        """Agent设置不存在的默认环境"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        assert agent.set_default_environment("nonexistent") is False

    def test_agent_execute_environment_action(self):
        """Agent执行环境动作"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        with tempfile.TemporaryDirectory() as tmpdir:
            agent.register_environment(
                "fs",
                FilesystemEnvironment(tmpdir),
                is_default=True,
            )
            result = agent.execute_environment_action(
                EnvironmentAction("write", "test.txt", {"content": "hello"})
            )
            assert result.success is True


# ============================================================
# 8. 并发安全测试
# ============================================================

class TestConcurrency:
    """并发安全测试"""

    def test_concurrent_observe_simulated(self):
        """并发感知模拟环境"""
        env = SimulatedEnvironment()
        errors = []

        def worker():
            try:
                for _ in range(20):
                    env.observe()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_filesystem_write(self):
        """并发文件系统写入"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            errors = []

            def worker(idx):
                try:
                    for i in range(10):
                        env.act(
                            EnvironmentAction("write", f"f_{idx}_{i}.txt", {"content": "x"})
                        )
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0
            # 50个文件
            entries = os.listdir(tmpdir)
            assert len(entries) == 50

    def test_concurrent_manager_observe(self):
        """并发管理器感知"""
        mgr = EnvironmentManager()
        mgr.register_environment("sim1", SimulatedEnvironment())
        mgr.register_environment("sim2", SimulatedEnvironment())
        errors = []

        def worker():
            try:
                for _ in range(20):
                    mgr.observe_all()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ============================================================
# 9. 性能测试
# ============================================================

class TestPerformance:
    """性能测试"""

    def test_simulated_observe_performance(self):
        """模拟环境感知性能"""
        env = SimulatedEnvironment()
        start = time.time()
        for _ in range(1000):
            env.observe()
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_filesystem_observe_performance(self):
        """文件系统感知性能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(100):
                with open(os.path.join(tmpdir, f"f{i}.txt"), "w") as f:
                    f.write("x")
            env = FilesystemEnvironment(tmpdir)
            start = time.time()
            for _ in range(100):
                env.observe()
            elapsed = time.time() - start
            assert elapsed < 5.0

    def test_filesystem_write_performance(self):
        """文件系统写入性能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            start = time.time()
            for i in range(100):
                env.act(
                    EnvironmentAction("write", f"f{i}.txt", {"content": "x" * 100})
                )
            elapsed = time.time() - start
            assert elapsed < 5.0

    def test_command_observe_performance(self):
        """命令行感知性能"""
        env = CommandEnvironment()
        start = time.time()
        for _ in range(100):
            env.observe()
        elapsed = time.time() - start
        assert elapsed < 5.0


# ============================================================
# 10. 异常容错测试
# ============================================================

class TestErrorTolerance:
    """异常容错测试"""

    def test_filesystem_observe_error(self):
        """文件系统感知错误处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            # 删除目录后感知
            os.rmdir(tmpdir)
            state = env.observe()
            # 应该返回错误状态而非崩溃
            assert "error" in state.data or "entries" in state.data

    def test_filesystem_none_path(self):
        """文件系统None路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            # None路径不应崩溃
            path = env._safe_path(None)
            assert path is not None

    def test_command_timeout(self):
        """命令行超时"""
        env = CommandEnvironment(timeout=0.1)
        result = env.act(EnvironmentAction("execute", "sleep 5"))
        assert result.success is False
        assert "timed out" in result.error.lower() or "timeout" in result.error.lower()

    def test_manager_observe_unavailable(self):
        """管理器感知不可用环境"""
        mgr = EnvironmentManager()
        # 注册一个不可用的HTTP环境
        env = HTTPEnvironment("http://localhost:1")
        env._available = False
        mgr.register_environment("http", env)
        # observe_all应该跳过不可用环境
        states = mgr.observe_all()
        # HTTP环境observe会返回错误状态，但is_available为False时observe_all跳过
        assert "http" not in states

    def test_observer_exception_isolated(self):
        """观察者异常隔离"""
        env = SimulatedEnvironment()

        def bad_observer(state):
            raise Exception("bad observer")

        env.register_observer(bad_observer)
        # 不应崩溃
        state = env.observe()
        assert state is not None

    def test_action_history_limit(self):
        """动作历史限制"""
        env = SimulatedEnvironment()
        env._max_history = 5
        for _ in range(10):
            env.act(EnvironmentAction("test", "x"))
        history = env.get_action_history()
        assert len(history) <= 5

    def test_clear_history(self):
        """清除历史"""
        env = SimulatedEnvironment()
        env.act(EnvironmentAction("test", "x"))
        env.clear_history()
        assert len(env.get_action_history()) == 0


# ============================================================
# 11. 第一性原理验证测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证测试"""

    def test_observe_act_loop(self):
        """第一性原理：感知-行动闭环"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            # 感知（空目录）
            state1 = env.observe()
            assert state1.data["entry_count"] == 0
            # 行动（创建文件）
            env.act(EnvironmentAction("write", "test.txt", {"content": "hello"}))
            # 感知（有文件）
            state2 = env.observe()
            assert state2.data["entry_count"] == 1

    def test_environment_isolation(self):
        """第一性原理：环境隔离"""
        with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
            env1 = FilesystemEnvironment(tmpdir1)
            env2 = FilesystemEnvironment(tmpdir2)
            env1.act(EnvironmentAction("write", "a.txt", {"content": "1"}))
            # env2不应该看到env1的文件
            state2 = env2.observe()
            assert state2.data["entry_count"] == 0

    def test_standardized_state(self):
        """第一性原理：标准化状态"""
        env = SimulatedEnvironment()
        state = env.observe()
        # 所有环境状态都应该有标准字段
        assert hasattr(state, "env_type")
        assert hasattr(state, "source")
        assert hasattr(state, "data")
        assert hasattr(state, "timestamp")

    def test_standardized_action(self):
        """第一性原理：标准化动作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = FilesystemEnvironment(tmpdir)
            action = EnvironmentAction("write", "test.txt", {"content": "x"})
            result = env.act(action)
            # 所有动作结果都应该有标准字段
            assert hasattr(result, "success")
            assert hasattr(result, "output")
            assert hasattr(result, "error")
            assert hasattr(result, "duration")

    def test_open_closed_principle(self):
        """第一性原理：开闭原则（可扩展新环境）"""

        # 创建自定义环境
        class CustomEnvironment(EnvironmentInterface):
            def observe(self):
                return EnvironmentState(
                    env_type=EnvironmentType.SIMULATED,
                    source="custom",
                    data={"custom": True},
                )

            def act(self, action):
                result = ActionResult(success=True, output={"custom": True})
                self._record_action(result)
                return result

            def get_capabilities(self):
                return ["custom"]

            def is_available(self):
                return True

        mgr = EnvironmentManager()
        mgr.register_environment("custom", CustomEnvironment())
        state = mgr.observe("custom")
        assert state.source == "custom"
        assert state.data["custom"] is True

    def test_multiple_environments_composition(self):
        """第一性原理：多环境组合"""
        mgr = EnvironmentManager()
        mgr.register_environment("sim", SimulatedEnvironment())
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr.register_environment("fs", FilesystemEnvironment(tmpdir))
            mgr.register_environment("cmd", CommandEnvironment())

            states = mgr.observe_all()
            # 应该能同时感知3个环境
            assert len(states) == 3
            assert "sim" in states
            assert "fs" in states
            assert "cmd" in states
