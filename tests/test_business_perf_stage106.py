"""
阶段106: 业务场景闭环 + 数据一致性校验 + 性能核验

1. 业务场景闭环：正向、逆向、中断、重复操作场景
2. 数据一致性校验：增删改查、数据存储、关联关系、数据回显
3. 基础性能核验：高频核心流程验证响应稳定，无卡顿、阻塞、内存溢出
"""

import pytest
import time
import threading
import os
import resource
from self_evolving_agent import create_default_agent, create_coordinator
from self_evolving_agent.core.unified_first_principles_engine import create_unified_engine
from self_evolving_agent.core.memory_first_principles import MemoryFirstPrinciplesEngine, MemoryPriority
from self_evolving_agent.core.efficiency_first_principles import EfficiencyFirstPrinciplesEngine, ResourceType


@pytest.fixture
def agent():
    return create_default_agent()


@pytest.fixture
def engine():
    return create_unified_engine()


# ============================================================
# 1. 业务场景闭环测试
# ============================================================

class TestBusinessScenarios:
    """业务场景闭环：正向、逆向、中断、重复操作"""

    # ---------- 正向场景 ----------

    def test_positive_full_lifecycle(self, agent):
        """正向完整生命周期：初始化 -> 设目标 -> 感知 -> 行动 -> 反思 -> 进化"""
        # 1. 设置目标
        agent.set_goal("safe", 0.95)
        agent.set_goal("gain", 0.8)
        agent.set_goal("eff", 0.85)

        # 2. 感知环境
        obs = agent.observe({
            "module_id": "env",
            "predicted": {"value": 0.5},
            "actual": {"value": 0.55},
        })
        assert "prediction" in obs

        # 3. 行动
        act = agent.act("explore", context={
            "resources_used": {"cpu": 0.2},
            "output_value": 0.6,
        })
        assert "action_taken" in act

        # 4. 反思
        reflection = agent.reflect()
        assert "cycle_count" in reflection

        # 5. 运行周期
        cycle = agent.run_cycle({"outcome": {"information_value": 0.7}})
        assert "cycle" in cycle

    def test_positive_multi_module_perception(self, agent):
        """正向多模块感知"""
        modules = ["cpu_monitor", "memory_monitor", "disk_monitor", "network_monitor"]
        for mod in modules:
            result = agent.observe({
                "module_id": mod,
                "predicted": {"usage": 0.5},
                "actual": {"usage": 0.6},
            })
            assert "prediction" in result

    def test_positive_goal_progression(self, agent):
        """正向目标渐进"""
        # 从低目标开始
        agent.set_goal("safe", 0.5)
        agent.set_goal("gain", 0.5)
        agent.set_goal("eff", 0.5)

        # 逐步提升
        for level in [0.6, 0.7, 0.8, 0.9, 0.95]:
            agent.set_goal("safe", level)
            agent.observe({
                "module_id": "env",
                "predicted": {"v": 0.5},
                "actual": {"v": 0.5 + (level - 0.5) * 0.1},
            })

    # ---------- 逆向场景 ----------

    def test_reverse_degradation_recovery(self, agent):
        """逆向降级恢复：先正常运行，注入异常，验证恢复"""
        # 正常运行
        for i in range(5):
            agent.observe({"module_id": f"mod_{i}", "predicted": {"v": 0.5}, "actual": {"v": 0.6}})

        # 注入异常
        for i in range(5):
            try:
                agent.observe({"module_id": None, "predicted": None, "actual": None})
            except Exception:
                pass

        # 验证恢复
        result = agent.observe({"module_id": "recovery", "predicted": {"v": 0.5}, "actual": {"v": 0.6}})
        assert "prediction" in result

    def test_reverse_goal_lowering(self, agent):
        """逆向降低目标"""
        agent.set_goal("safe", 0.95)
        agent.set_goal("safe", 0.5)
        agent.set_goal("safe", 0.1)
        # 系统应正常处理目标降低
        result = agent.reflect()
        assert "goals" in result

    # ---------- 中断场景 ----------

    def test_interrupt_start_stop_resume(self, agent):
        """中断场景：启动 -> 停止 -> 恢复"""
        agent.start()
        time.sleep(0.1)
        agent.stop()

        # 恢复后仍能正常工作
        result = agent.observe({"module_id": "resume", "predicted": {"v": 0.5}, "actual": {"v": 0.6}})
        assert "prediction" in result

        agent.start()
        time.sleep(0.1)
        agent.stop()

    def test_interrupt_mid_cycle(self, agent):
        """中断场景：周期中途停止"""
        agent.start()
        # 在运行中注入操作
        for i in range(3):
            agent.observe({"module_id": f"interrupt_{i}", "predicted": {"v": 0.5}, "actual": {"v": 0.6}})
        agent.stop()
        # 停止后仍能手动操作
        result = agent.reflect()
        assert result is not None

    # ---------- 重复操作场景 ----------

    def test_repeated_observe_same_input(self, agent):
        """重复相同输入"""
        state = {"module_id": "repeat", "predicted": {"v": 0.5}, "actual": {"v": 0.6}}
        for _ in range(50):
            result = agent.observe(state)
            assert "prediction" in result

    def test_repeated_goals(self, agent):
        """重复设置相同目标"""
        for _ in range(20):
            agent.set_goal("safe", 0.95)
        result = agent.reflect()
        assert result is not None

    def test_repeated_start_stop(self, agent):
        """重复启停"""
        for _ in range(10):
            agent.start()
            agent.stop()


# ============================================================
# 2. 数据一致性校验
# ============================================================

class TestDataConsistency:
    """数据一致性校验"""

    def test_memory_store_retrieve_consistency(self):
        """记忆存储-检索一致性"""
        mem = MemoryFirstPrinciplesEngine("test", capacity=100, retention_threshold=0.0)
        # 存储（使用低阈值确保都能存储）
        mem.store("key1", {"data": "alpha_beta_gamma"}, context={})
        mem.store("key2", {"data": "delta_epsilon_zeta"}, context={})
        mem.store("key3", {"data": "eta_theta_iota_kappa"}, context={})

        # 检索验证
        item1 = mem.retrieve("key1")
        item2 = mem.retrieve("key2")
        item3 = mem.retrieve("key3")

        assert item1 is not None and item1.content == {"data": "alpha_beta_gamma"}
        assert item2 is not None and item2.content == {"data": "delta_epsilon_zeta"}
        assert item3 is not None and item3.content == {"data": "eta_theta_iota_kappa"}

    def test_memory_store_overwrite(self):
        """记忆覆盖一致性"""
        mem = MemoryFirstPrinciplesEngine("test", capacity=100, retention_threshold=0.0)
        mem.store("key1", {"version": 1, "data": "initial_state"})
        mem.store("key1", {"version": 2, "data": "updated_state"})

        item = mem.retrieve("key1")
        assert item.content == {"version": 2, "data": "updated_state"}

    def test_memory_delete_consistency(self):
        """记忆删除一致性"""
        mem = MemoryFirstPrinciplesEngine("test", capacity=100, retention_threshold=0.0)
        mem.store("key1", {"data": "unique_content_alpha"})
        mem.store("key2", {"data": "unique_content_beta"})

        stats_before = mem.get_stats()
        assert stats_before["items_count"] == 2

        # 删除（通过清空机制）
        mem.clear()
        stats_after = mem.get_stats()
        assert stats_after["items_count"] == 0

    def test_efficiency_budget_consistency(self):
        """能效预算一致性"""
        eff = EfficiencyFirstPrinciplesEngine("test")
        eff.set_budget("b1", ResourceType.CPU, 10.0)

        # 记录使用
        eff.record_usage("u1", ResourceType.CPU, 3.0, 1.0)
        eff.record_usage("u2", ResourceType.CPU, 2.0, 1.0)

        budget = eff._budgets["b1"]
        assert budget.consumed == 5.0  # 3 + 2
        assert budget.allocated == 10.0
        assert budget.remaining == 5.0

    def test_efficiency_usage_update_consistency(self):
        """能效使用更新一致性"""
        eff = EfficiencyFirstPrinciplesEngine("test")
        eff.set_budget("b1", ResourceType.CPU, 10.0)

        # 第一次记录
        eff.record_usage("u1", ResourceType.CPU, 3.0, 1.0)
        assert eff._budgets["b1"].consumed == 3.0

        # 更新同一 usage
        eff.record_usage("u1", ResourceType.CPU, 5.0, 1.0)
        assert eff._budgets["b1"].consumed == 5.0  # 不是 8.0

    def test_engine_state_consistency(self, engine):
        """引擎状态一致性"""
        # 多次获取统计，验证一致性
        stats1 = engine.get_full_stats()
        stats2 = engine.get_full_stats()

        assert stats1["engine_id"] == stats2["engine_id"]
        assert stats1["cycle_count"] == stats2["cycle_count"]

    def test_agent_state_consistency(self, agent):
        """Agent状态一致性"""
        state1 = agent.get_state()
        state2 = agent.get_state()

        assert state1["agent_id"] == state2["agent_id"]
        assert state1["running"] == state2["running"]

    def test_cycle_count_monotonic(self, agent):
        """周期计数单调递增"""
        counts = []
        for _ in range(10):
            agent.observe({"module_id": "env", "predicted": {"v": 0.5}, "actual": {"v": 0.6}})
            state = agent.get_state()
            counts.append(state["cycle_count"])

        # 验证单调递增
        for i in range(1, len(counts)):
            assert counts[i] >= counts[i - 1], f"周期计数非单调: {counts}"


# ============================================================
# 3. 基础性能核验
# ============================================================

class TestPerformance:
    """基础性能核验"""

    def test_observe_latency(self, agent):
        """observe 延迟 < 10ms"""
        times = []
        for _ in range(100):
            start = time.perf_counter()
            agent.observe({"module_id": "perf", "predicted": {"v": 0.5}, "actual": {"v": 0.6}})
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg = sum(times) / len(times)
        p99 = sorted(times)[98]
        assert avg < 10.0, f"平均延迟 {avg:.2f}ms > 10ms"
        assert p99 < 50.0, f"P99延迟 {p99:.2f}ms > 50ms"

    def test_reflect_latency(self, agent):
        """reflect 延迟 < 20ms"""
        times = []
        for _ in range(50):
            start = time.perf_counter()
            agent.reflect()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg = sum(times) / len(times)
        assert avg < 20.0, f"平均延迟 {avg:.2f}ms > 20ms"

    def test_run_cycle_latency(self, agent):
        """run_cycle 延迟 < 50ms"""
        times = []
        for _ in range(50):
            start = time.perf_counter()
            agent.run_cycle({"outcome": {"information_value": 0.5}})
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg = sum(times) / len(times)
        assert avg < 50.0, f"平均延迟 {avg:.2f}ms > 50ms"

    def test_get_stats_latency(self, engine):
        """get_full_stats 延迟 < 10ms"""
        times = []
        for _ in range(100):
            start = time.perf_counter()
            engine.get_full_stats()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg = sum(times) / len(times)
        assert avg < 10.0, f"平均延迟 {avg:.2f}ms > 10ms"

    def test_long_running_no_memory_leak(self, agent):
        """长期运行无内存泄漏"""
        import gc

        # 获取初始内存
        gc.collect()
        mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        # 运行1000个周期
        for i in range(1000):
            agent.observe({
                "module_id": f"leak_test_{i}",
                "predicted": {"v": 0.5},
                "actual": {"v": 0.6},
            })
            if i % 100 == 99:
                agent.reflect()

        gc.collect()
        mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        # 内存增长不超过 50MB（KB单位）
        mem_growth = mem_after - mem_before
        assert mem_growth < 51200, f"内存增长 {mem_growth}KB > 50MB"

    def test_high_frequency_stability(self, agent):
        """高频核心流程稳定性"""
        errors = []
        for i in range(500):
            try:
                agent.observe({
                    "module_id": f"hf_{i}",
                    "predicted": {"v": 0.5},
                    "actual": {"v": 0.5 + i * 0.001},
                })
            except Exception as e:
                errors.append(str(e))

        assert len(errors) == 0, f"高频运行错误: {errors[:3]}"

    def test_concurrent_throughput(self, agent):
        """并发吞吐量"""
        count = 0
        count_lock = threading.Lock()
        errors = []

        def worker():
            nonlocal count
            try:
                for _ in range(50):
                    agent.observe({
                        "module_id": "throughput",
                        "predicted": {"v": 0.5},
                        "actual": {"v": 0.6},
                    })
                    with count_lock:
                        count += 1
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)
        elapsed = time.perf_counter() - start

        assert len(errors) == 0, f"并发错误: {errors[:3]}"
        assert count == 500
        throughput = count / elapsed
        assert throughput > 100, f"吞吐量 {throughput:.0f} ops/s < 100 ops/s"
