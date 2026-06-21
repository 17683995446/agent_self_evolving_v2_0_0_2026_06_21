"""
阶段116: 学习算法强化 — 专项测试

验证新增能力:
1. Experience: 经验元组
2. ExperienceReplayBuffer: 经验回放缓冲区（均匀/优先级采样）
3. LearningRateScheduler: 学习率调度器（5种策略）
4. OnlineLearner: 在线学习器（动量、梯度裁剪）
5. EnhancedLearningEngine: 整合经验回放和在线学习
6. 向后兼容性

第一性原理验证:
- 经验复用：过去经验应被重新采样学习
- 学习率自适应：误差下降时增大，震荡时减小
- 动量加速：一致梯度方向应加速收敛
- 梯度裁剪：防止梯度爆炸
"""

import math
import threading
import time
import pytest

from self_evolving_agent.core.learning_first_principles import (
    LearningFirstPrinciplesEngine,
    LearningSignal,
    ParameterUpdate,
    UpdateType,
    LRScheduleType,
    Experience,
    ExperienceReplayBuffer,
    LearningRateScheduler,
    OnlineLearner,
    create_learning_engine,
    create_learning_signal,
    create_parameter_update,
    create_experience,
    create_lr_scheduler,
)


# ============================================================
# 1. Experience 数据结构测试
# ============================================================

class TestExperience:
    """经验元组测试"""

    def test_experience_creation(self):
        """经验创建"""
        exp = Experience(
            experience_id="e1",
            state={"s": 0.5},
            action="move",
            reward=1.0,
            next_state={"s": 0.6},
        )
        assert exp.experience_id == "e1"
        assert exp.action == "move"
        assert exp.reward == 1.0
        assert exp.td_error == 0.0
        assert exp.visit_count == 0

    def test_importance_with_td_error(self):
        """有TD误差时重要性更高"""
        exp_no_td = Experience("e1", {"s": 0}, "a", 0, {"s": 0})
        exp_with_td = Experience("e2", {"s": 0}, "a", 0, {"s": 0}, td_error=0.5)
        assert exp_with_td.importance > exp_no_td.importance

    def test_importance_always_positive(self):
        """重要性始终为正"""
        exp = Experience("e1", {"s": 0}, "a", 0, {"s": 0}, td_error=0.0)
        assert exp.importance > 0


# ============================================================
# 2. ExperienceReplayBuffer 测试
# ============================================================

class TestExperienceReplayBuffer:
    """经验回放缓冲区测试"""

    def test_add_and_len(self):
        """添加经验和长度"""
        buf = ExperienceReplayBuffer(capacity=100)
        assert len(buf) == 0
        buf.add(Experience("e1", {"s": 0}, "a", 1.0, {"s": 1}))
        assert len(buf) == 1

    def test_add_duplicate_fails(self):
        """重复ID添加失败"""
        buf = ExperienceReplayBuffer()
        buf.add(Experience("e1", {"s": 0}, "a", 1.0, {"s": 1}))
        assert buf.add(Experience("e1", {"s": 0}, "a", 1.0, {"s": 1})) is False

    def test_capacity_limit(self):
        """容量上限"""
        buf = ExperienceReplayBuffer(capacity=5)
        for i in range(10):
            buf.add(Experience(f"e{i}", {"s": i}, "a", 1.0, {"s": i + 1}))
        assert len(buf) == 5  # 只保留最新5个

    def test_uniform_sample(self):
        """均匀采样"""
        buf = ExperienceReplayBuffer(seed=42)
        for i in range(20):
            buf.add(Experience(f"e{i}", {"s": i}, "a", 1.0, {"s": i + 1}))
        sampled = buf.sample(batch_size=5, prioritized=False)
        assert len(sampled) == 5
        # 采样后访问计数增加
        for exp in sampled:
            assert exp.visit_count >= 1

    def test_priority_sample(self):
        """优先级采样"""
        buf = ExperienceReplayBuffer(seed=42)
        # 添加不同TD误差的经验
        for i in range(20):
            buf.add(Experience(
                f"e{i}", {"s": i}, "a", 1.0, {"s": i + 1},
                td_error=float(i) * 0.1,  # 递增TD误差
            ))
        sampled = buf.sample(batch_size=10, prioritized=True)
        assert len(sampled) == 10
        # 高TD误差的经验应更可能被采样
        avg_td = sum(e.td_error for e in sampled) / len(sampled)
        all_avg = sum(e.td_error for e in buf._buffer) / len(buf._buffer)
        assert avg_td >= all_avg * 0.8  # 允许一定随机性

    def test_sample_empty_buffer(self):
        """空缓冲区采样"""
        buf = ExperienceReplayBuffer()
        assert buf.sample(10) == []

    def test_sample_more_than_available(self):
        """采样数大于可用数"""
        buf = ExperienceReplayBuffer()
        buf.add(Experience("e1", {"s": 0}, "a", 1.0, {"s": 1}))
        sampled = buf.sample(batch_size=10)
        assert len(sampled) == 1

    def test_update_priorities(self):
        """更新优先级"""
        buf = ExperienceReplayBuffer()
        buf.add(Experience("e1", {"s": 0}, "a", 1.0, {"s": 1}, td_error=0.1))
        buf.update_priorities({"e1": 0.9})
        exp = buf.get_experience("e1")
        assert exp.td_error == 0.9
        assert exp.priority == 0.91  # 0.9 + 0.01

    def test_get_experience(self):
        """获取特定经验"""
        buf = ExperienceReplayBuffer()
        buf.add(Experience("e1", {"s": 0}, "a", 1.0, {"s": 1}))
        exp = buf.get_experience("e1")
        assert exp is not None
        assert exp.experience_id == "e1"
        assert buf.get_experience("nonexistent") is None

    def test_remove_experience(self):
        """移除经验"""
        buf = ExperienceReplayBuffer()
        buf.add(Experience("e1", {"s": 0}, "a", 1.0, {"s": 1}))
        assert buf.remove("e1") is True
        assert len(buf) == 0
        assert buf.remove("e1") is False

    def test_clear(self):
        """清空缓冲区"""
        buf = ExperienceReplayBuffer()
        for i in range(5):
            buf.add(Experience(f"e{i}", {"s": i}, "a", 1.0, {"s": i + 1}))
        buf.clear()
        assert len(buf) == 0

    def test_get_stats(self):
        """获取统计"""
        buf = ExperienceReplayBuffer()
        for i in range(10):
            buf.add(Experience(f"e{i}", {"s": i}, "a", 1.0, {"s": i + 1}, td_error=0.1 * i))
        stats = buf.get_stats()
        assert stats["size"] == 10
        assert stats["capacity"] == 10000
        assert "avg_td_error" in stats
        assert "alpha" in stats

    def test_set_priority_params(self):
        """设置优先级参数"""
        buf = ExperienceReplayBuffer()
        buf.set_priority_params(0.8, 0.6)
        stats = buf.get_stats()
        assert stats["alpha"] == 0.8
        assert stats["beta"] == 0.6

    def test_thread_safety(self):
        """线程安全"""
        buf = ExperienceReplayBuffer(capacity=1000)
        errors = []

        def worker(thread_id):
            try:
                for i in range(100):
                    buf.add(Experience(
                        f"e_{thread_id}_{i}", {"s": i}, "a", 1.0, {"s": i + 1}
                    ))
                    buf.sample(5)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0


# ============================================================
# 3. LearningRateScheduler 测试
# ============================================================

class TestLearningRateScheduler:
    """学习率调度器测试"""

    def test_constant_schedule(self):
        """恒定学习率"""
        sched = LearningRateScheduler(base_lr=0.1, schedule_type=LRScheduleType.CONSTANT)
        lr1 = sched.step()
        lr2 = sched.step()
        assert lr1 == 0.1
        assert lr2 == 0.1

    def test_decay_schedule(self):
        """衰减学习率"""
        sched = LearningRateScheduler(
            base_lr=1.0, schedule_type=LRScheduleType.DECAY, decay_rate=0.9
        )
        lr1 = sched.step()
        lr2 = sched.step()
        assert lr1 < 1.0  # 衰减后
        assert lr2 < lr1  # 继续衰减

    def test_warmup_schedule(self):
        """预热学习率"""
        sched = LearningRateScheduler(
            base_lr=0.1, schedule_type=LRScheduleType.WARMUP, warmup_steps=10
        )
        lr_early = sched.step()  # step 1
        for _ in range(9):
            sched.step()
        lr_late = sched.get_lr()  # step 10
        assert lr_early < 0.1  # 预热阶段小于base
        assert lr_late <= 0.1  # 预热完成

    def test_cyclical_schedule(self):
        """循环学习率"""
        sched = LearningRateScheduler(
            schedule_type=LRScheduleType.CYCLICAL,
            min_lr=0.001, max_lr=0.1, cycle_steps=100,
        )
        lrs = [sched.step() for _ in range(100)]
        # 应在 [min_lr, max_lr] 范围内
        for lr in lrs:
            assert 0.001 <= lr <= 0.1
        # 应有振荡
        assert max(lrs) > min(lrs)

    def test_adaptive_schedule_increases_on_descent(self):
        """自适应：误差下降时增大学习率"""
        sched = LearningRateScheduler(
            base_lr=0.01, schedule_type=LRScheduleType.ADAPTIVE,
        )
        # 模拟误差持续下降
        for i in range(20):
            error = 1.0 - i * 0.05  # 线性下降
            sched.step(error)
        # 自适应因子应增大
        assert sched._adaptive_factor > 1.0

    def test_adaptive_schedule_decreases_on_oscillation(self):
        """自适应：误差震荡时减小学习率"""
        sched = LearningRateScheduler(
            base_lr=0.01, schedule_type=LRScheduleType.ADAPTIVE,
        )
        # 模拟误差震荡
        for i in range(20):
            error = 0.5 + 0.5 * ((-1) ** i)  # 在0和1之间震荡
            sched.step(error)
        # 自适应因子应减小
        assert sched._adaptive_factor < 1.0

    def test_reset(self):
        """重置调度器"""
        sched = LearningRateScheduler(schedule_type=LRScheduleType.DECAY)
        for _ in range(10):
            sched.step()
        sched.reset()
        assert sched._step_count == 0
        assert sched._adaptive_factor == 1.0

    def test_get_stats(self):
        """获取统计"""
        sched = LearningRateScheduler(base_lr=0.05, schedule_type=LRScheduleType.WARMUP)
        sched.step()
        stats = sched.get_stats()
        assert stats["base_lr"] == 0.05
        assert stats["schedule_type"] == "warmup"
        assert stats["step_count"] == 1
        assert "current_lr" in stats

    def test_base_lr_minimum(self):
        """基础学习率下界"""
        sched = LearningRateScheduler(base_lr=-1.0)
        assert sched._base_lr > 0


# ============================================================
# 4. OnlineLearner 测试
# ============================================================

class TestOnlineLearner:
    """在线学习器测试"""

    def test_set_and_get_parameter(self):
        """设置和获取参数"""
        learner = OnlineLearner()
        learner.set_parameter("w1", 0.5)
        assert learner.get_parameter("w1") == 0.5

    def test_update_changes_parameter(self):
        """更新改变参数值"""
        learner = OnlineLearner(momentum=0.0)  # 无动量
        learner.set_parameter("w1", 1.0)
        delta = learner.update("w1", gradient=0.5)
        assert delta != 0
        assert learner.get_parameter("w1") != 1.0

    def test_gradient_clipping(self):
        """梯度裁剪"""
        learner = OnlineLearner(momentum=0.0, max_gradient=1.0)
        learner.set_parameter("w1", 0.0)
        # 巨大梯度应被裁剪
        delta = learner.update("w1", gradient=1000.0)
        # 裁剪后梯度=1.0，delta = lr * 1.0
        assert abs(delta) <= 0.1  # 默认lr=0.01，所以delta≈0.01

    def test_momentum_acceleration(self):
        """动量加速"""
        learner = OnlineLearner(momentum=0.9, max_gradient=1.0)
        learner.set_parameter("w1", 0.0)
        # 连续相同方向梯度
        deltas = []
        for _ in range(10):
            delta = learner.update("w1", gradient=1.0)
            deltas.append(abs(delta))
        # 后续delta应大于第一个（动量累积）
        assert deltas[-1] > deltas[0]

    def test_nan_gradient_defense(self):
        """NaN梯度防御"""
        learner = OnlineLearner()
        learner.set_parameter("w1", 0.5)
        delta = learner.update("w1", gradient=float("nan"))
        assert delta == 0.0
        assert learner.get_parameter("w1") == 0.5  # 不变

    def test_inf_gradient_defense(self):
        """Inf梯度防御"""
        learner = OnlineLearner()
        learner.set_parameter("w1", 0.5)
        delta = learner.update("w1", gradient=float("inf"))
        # Inf被视为无效，返回0
        assert delta == 0.0
        assert learner.get_parameter("w1") == 0.5  # 不变

    def test_batch_update(self):
        """批量更新"""
        learner = OnlineLearner(momentum=0.0)
        learner.set_parameter("w1", 0.0)
        learner.set_parameter("w2", 0.0)
        results = learner.batch_update({"w1": 0.5, "w2": -0.3})
        assert "w1" in results
        assert "w2" in results
        assert results["w1"] != 0
        assert results["w2"] != 0

    def test_reset_momentum(self):
        """重置动量"""
        learner = OnlineLearner(momentum=0.9)
        learner.set_parameter("w1", 0.0)
        for _ in range(5):
            learner.update("w1", gradient=1.0)
        # 有动量
        assert learner._velocities["w1"] != 0
        learner.reset_momentum()
        assert learner._velocities["w1"] == 0

    def test_get_all_parameters(self):
        """获取所有参数"""
        learner = OnlineLearner()
        learner.set_parameter("w1", 0.1)
        learner.set_parameter("w2", 0.2)
        params = learner.get_all_parameters()
        assert params["w1"] == 0.1
        assert params["w2"] == 0.2

    def test_get_stats(self):
        """获取统计"""
        learner = OnlineLearner()
        learner.set_parameter("w1", 0.0)
        learner.update("w1", gradient=0.5)
        stats = learner.get_stats()
        assert stats["update_count"] == 1
        assert stats["parameter_count"] == 1
        assert "momentum" in stats
        assert "scheduler_stats" in stats


# ============================================================
# 5. EnhancedLearningEngine 测试
# ============================================================

class TestEnhancedLearningEngine:
    """增强学习引擎测试"""

    def test_engine_has_new_components(self):
        """引擎包含新组件"""
        engine = LearningFirstPrinciplesEngine("test")
        assert engine.get_replay_buffer() is not None
        assert engine.get_online_learner() is not None
        assert engine.get_scheduler() is not None

    def test_add_experience(self):
        """添加经验"""
        engine = LearningFirstPrinciplesEngine("test")
        exp = engine.add_experience(
            state={"s": 0.5}, action="move", reward=1.0,
            next_state={"s": 0.6}, td_error=0.1,
        )
        assert exp is not None
        assert len(engine.get_replay_buffer()) == 1

    def test_sample_experiences(self):
        """采样经验"""
        engine = LearningFirstPrinciplesEngine("test")
        for i in range(10):
            engine.add_experience(
                state={"s": float(i)}, action="a", reward=1.0,
                next_state={"s": float(i + 1)}, td_error=0.1 * i,
            )
        sampled = engine.sample_experiences(batch_size=5)
        assert len(sampled) == 5

    def test_replay_learn(self):
        """经验回放学习"""
        engine = LearningFirstPrinciplesEngine("test")
        for i in range(10):
            engine.add_experience(
                state={"s": float(i)}, action="move", reward=1.0,
                next_state={"s": float(i + 1)}, td_error=0.5,
            )
        updates = engine.replay_learn(batch_size=5, prioritized=True)
        assert len(updates) > 0
        # 应产生参数更新
        assert len(engine._updates) > 0

    def test_replay_learn_with_custom_fn(self):
        """自定义学习函数的经验回放"""
        engine = LearningFirstPrinciplesEngine("test")
        for i in range(10):
            engine.add_experience(
                state={"s": float(i)}, action="a", reward=float(i),
                next_state={"s": float(i + 1)}, td_error=0.1,
            )

        def custom_fn(exp):
            return ("w", -exp.reward * 0.1, 0.1)

        updates = engine.replay_learn(batch_size=5, learning_fn=custom_fn)
        assert len(updates) > 0
        # 参数应被更新
        assert engine.get_parameter("w") != 0.0

    def test_online_update(self):
        """在线更新"""
        engine = LearningFirstPrinciplesEngine("test")
        engine.set_parameter("w1", 0.0)
        delta = engine.online_update("w1", gradient=0.5, error=0.1)
        assert delta != 0
        assert engine.get_parameter("w1") != 0.0

    def test_online_batch_update(self):
        """批量在线更新"""
        engine = LearningFirstPrinciplesEngine("test")
        engine.set_parameter("w1", 0.0)
        engine.set_parameter("w2", 0.0)
        results = engine.online_batch_update(
            {"w1": 0.5, "w2": -0.3}, error=0.1
        )
        assert "w1" in results
        assert "w2" in results

    def test_set_schedule_type(self):
        """设置调度策略"""
        engine = LearningFirstPrinciplesEngine("test")
        engine.set_schedule_type(LRScheduleType.DECAY, base_lr=0.05, decay_rate=0.95)
        stats = engine.get_scheduler().get_stats()
        assert stats["schedule_type"] == "decay"
        assert stats["base_lr"] == 0.05

    def test_update_experience_priorities(self):
        """更新经验优先级"""
        engine = LearningFirstPrinciplesEngine("test")
        exp = engine.add_experience(
            state={"s": 0}, action="a", reward=1.0,
            next_state={"s": 1}, td_error=0.1,
        )
        engine.update_experience_priorities({exp.experience_id: 0.9})
        updated = engine.get_replay_buffer().get_experience(exp.experience_id)
        assert updated.td_error == 0.9

    def test_get_stats_includes_new_fields(self):
        """统计包含新字段"""
        engine = LearningFirstPrinciplesEngine("test")
        engine.add_experience({"s": 0}, "a", 1.0, {"s": 1})
        stats = engine.get_stats()
        assert "replay_buffer_stats" in stats
        assert "online_learner_stats" in stats
        assert stats["replay_buffer_stats"]["size"] == 1


# ============================================================
# 6. 向后兼容性测试
# ============================================================

class TestBackwardCompatibility:
    """向后兼容性测试"""

    def test_create_learning_engine_factory(self):
        """工厂函数兼容"""
        engine = create_learning_engine("test")
        assert isinstance(engine, LearningFirstPrinciplesEngine)
        assert engine.engine_id == "test"

    def test_create_learning_signal_helper(self):
        """信号创建辅助函数兼容"""
        sig = create_learning_signal(0.5, "test_source", 0.8)
        assert sig is not None
        assert sig.error_magnitude == 0.5
        assert sig.error_source == "test_source"

    def test_create_learning_signal_zero_error(self):
        """零误差不创建信号"""
        sig = create_learning_signal(0.0)
        assert sig is None

    def test_create_parameter_update_helper(self):
        """参数更新辅助函数兼容"""
        update = create_parameter_update("w1", 0.5, "sig1", 0.01)
        assert update.parameter_name == "w1"
        assert update.signal_id == "sig1"

    def test_create_experience_helper(self):
        """经验创建辅助函数"""
        exp = create_experience({"s": 0}, "a", 1.0, {"s": 1}, td_error=0.1)
        assert exp.action == "a"
        assert exp.reward == 1.0

    def test_create_lr_scheduler_helper(self):
        """调度器创建辅助函数"""
        sched = create_lr_scheduler(0.05, LRScheduleType.DECAY)
        assert sched._base_lr == 0.05
        assert sched._schedule_type == LRScheduleType.DECAY

    def test_create_signal(self):
        """创建信号兼容"""
        engine = LearningFirstPrinciplesEngine("test")
        sig = engine.create_signal(0.5, "test")
        assert sig is not None
        assert sig.is_valid is True

    def test_create_signal_zero_error(self):
        """零误差不创建信号"""
        engine = LearningFirstPrinciplesEngine("test")
        sig = engine.create_signal(0.0)
        assert sig is None

    def test_propose_update(self):
        """提议更新兼容"""
        engine = LearningFirstPrinciplesEngine("test")
        sig = engine.create_signal(0.5, "test")
        update = engine.propose_update("w1", 0.1, sig.signal_id, 0.01)
        assert update is not None
        assert update.parameter_name == "w1"

    def test_propose_update_invalid_signal(self):
        """无效信号更新被拒绝"""
        engine = LearningFirstPrinciplesEngine("test")
        update = engine.propose_update("w1", 0.1, "nonexistent", 0.01)
        assert update is None
        assert engine._rejected_updates == 1

    def test_apply_update(self):
        """应用更新兼容"""
        engine = LearningFirstPrinciplesEngine("test")
        sig = engine.create_signal(0.5)
        update = engine.propose_update("w1", 1.0, sig.signal_id, 0.01)
        engine.apply_update(update)
        assert engine.get_parameter("w1") != 0.0

    def test_learn_from_error(self):
        """从误差学习兼容"""
        engine = LearningFirstPrinciplesEngine("test")
        update = engine.learn_from_error("w1", 0.5, 1.0, "test", 0.01)
        assert update is not None
        assert engine.get_parameter("w1") != 0.0

    def test_learn_from_error_zero(self):
        """零误差不学习"""
        engine = LearningFirstPrinciplesEngine("test")
        update = engine.learn_from_error("w1", 0.0, 1.0)
        assert update is None

    def test_trace_update_to_error(self):
        """追溯更新到误差"""
        engine = LearningFirstPrinciplesEngine("test")
        update = engine.learn_from_error("w1", 0.5, 1.0, "source")
        signal = engine.trace_update_to_error(update.update_id)
        assert signal is not None
        assert signal.error_source == "source"

    def test_trace_nonexistent_update(self):
        """追溯不存在的更新"""
        engine = LearningFirstPrinciplesEngine("test")
        assert engine.trace_update_to_error("nonexistent") is None

    def test_set_and_get_parameter(self):
        """设置和获取参数兼容"""
        engine = LearningFirstPrinciplesEngine("test")
        engine.set_parameter("w1", 0.5)
        assert engine.get_parameter("w1") == 0.5

    def test_clear_history(self):
        """清除历史兼容"""
        engine = LearningFirstPrinciplesEngine("test")
        engine.learn_from_error("w1", 0.5, 1.0)
        engine.clear_history()
        stats = engine.get_stats()
        assert stats["signals_count"] == 0
        assert stats["updates_count"] == 0

    def test_update_type_enum(self):
        """更新类型枚举兼容"""
        assert UpdateType.GRADIENT_DESCENT.value == "gradient_descent"
        assert UpdateType.ERROR_CORRECTION.value == "error_correction"

    def test_learning_signal_is_valid(self):
        """学习信号有效性"""
        sig = LearningSignal("s1", error_magnitude=0.5)
        assert sig.is_valid is True
        sig_zero = LearningSignal("s2", error_magnitude=0.0)
        assert sig_zero.is_valid is False

    def test_parameter_update_magnitude(self):
        """参数更新幅度"""
        update = ParameterUpdate("u1", "w1", delta=0.5)
        assert update.update_magnitude == 0.5


# ============================================================
# 7. 并发安全测试
# ============================================================

class TestConcurrencySafety:
    """并发安全测试"""

    def test_concurrent_experience_operations(self):
        """并发经验操作"""
        engine = LearningFirstPrinciplesEngine("test")
        errors = []

        def worker(thread_id):
            try:
                for i in range(50):
                    engine.add_experience(
                        state={"s": float(i)},
                        action=f"a_{thread_id}",
                        reward=float(i) * 0.01,
                        next_state={"s": float(i + 1)},
                        td_error=0.1 * i,
                    )
                    engine.sample_experiences(5, prioritized=True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert len(engine.get_replay_buffer()) == 500

    def test_concurrent_online_learning(self):
        """并发在线学习"""
        engine = LearningFirstPrinciplesEngine("test")
        engine.set_parameter("w1", 0.0)
        errors = []

        def worker():
            try:
                for _ in range(100):
                    engine.online_update("w1", gradient=0.01, error=0.1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0


# ============================================================
# 8. 性能测试
# ============================================================

class TestPerformance:
    """性能基准测试"""

    def test_add_experience_latency(self):
        """添加经验延迟 < 1ms"""
        engine = LearningFirstPrinciplesEngine("test")
        start = time.time()
        for i in range(1000):
            engine.add_experience(
                state={"s": float(i)}, action="a", reward=1.0,
                next_state={"s": float(i + 1)},
            )
        elapsed = time.time() - start
        avg_ms = (elapsed / 1000) * 1000
        assert avg_ms < 1.0, f"平均延迟 {avg_ms:.2f}ms 超过 1ms"

    def test_sample_latency(self):
        """采样延迟 < 5ms"""
        engine = LearningFirstPrinciplesEngine("test")
        for i in range(1000):
            engine.add_experience(
                state={"s": float(i)}, action="a", reward=1.0,
                next_state={"s": float(i + 1)}, td_error=0.1 * (i % 10),
            )
        start = time.time()
        for _ in range(100):
            engine.sample_experiences(32, prioritized=True)
        elapsed = time.time() - start
        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 5.0, f"平均延迟 {avg_ms:.2f}ms 超过 5ms"

    def test_online_update_latency(self):
        """在线更新延迟 < 1ms"""
        engine = LearningFirstPrinciplesEngine("test")
        engine.set_parameter("w1", 0.0)
        start = time.time()
        for _ in range(1000):
            engine.online_update("w1", gradient=0.01, error=0.1)
        elapsed = time.time() - start
        avg_ms = (elapsed / 1000) * 1000
        assert avg_ms < 1.0, f"平均延迟 {avg_ms:.2f}ms 超过 1ms"

    def test_replay_learn_latency(self):
        """经验回放学习延迟 < 50ms"""
        engine = LearningFirstPrinciplesEngine("test")
        for i in range(100):
            engine.add_experience(
                state={"s": float(i)}, action="a", reward=1.0,
                next_state={"s": float(i + 1)}, td_error=0.1,
            )
        start = time.time()
        engine.replay_learn(batch_size=32, prioritized=True)
        elapsed = time.time() - start
        assert elapsed < 0.05, f"回放学习耗时 {elapsed * 1000:.2f}ms 超过 50ms"


# ============================================================
# 9. 异常容错测试
# ============================================================

class TestErrorTolerance:
    """异常容错测试"""

    def test_nan_in_experience(self):
        """经验中包含NaN"""
        engine = LearningFirstPrinciplesEngine("test")
        exp = engine.add_experience(
            state={"s": float("nan")}, action="a", reward=1.0,
            next_state={"s": 1.0}, td_error=0.1,
        )
        assert exp is not None  # 不崩溃

    def test_inf_in_experience(self):
        """经验中包含Inf"""
        engine = LearningFirstPrinciplesEngine("test")
        exp = engine.add_experience(
            state={"s": float("inf")}, action="a", reward=1.0,
            next_state={"s": 1.0}, td_error=0.1,
        )
        assert exp is not None

    def test_negative_reward(self):
        """负奖励"""
        engine = LearningFirstPrinciplesEngine("test")
        exp = engine.add_experience(
            state={"s": 0}, action="a", reward=-1.0,
            next_state={"s": 1}, td_error=0.1,
        )
        assert exp is not None
        assert exp.reward == -1.0

    def test_empty_state(self):
        """空状态"""
        engine = LearningFirstPrinciplesEngine("test")
        exp = engine.add_experience(
            state={}, action="a", reward=1.0, next_state={},
        )
        assert exp is not None

    def test_nan_gradient_online_update(self):
        """在线更新NaN梯度"""
        engine = LearningFirstPrinciplesEngine("test")
        engine.set_parameter("w1", 0.5)
        delta = engine.online_update("w1", gradient=float("nan"))
        assert delta == 0.0
        assert engine.get_parameter("w1") == 0.5  # 不变

    def test_replay_learn_empty_buffer(self):
        """空缓冲区回放学习"""
        engine = LearningFirstPrinciplesEngine("test")
        updates = engine.replay_learn(batch_size=32)
        assert updates == []

    def test_large_batch_sample(self):
        """大批量采样"""
        engine = LearningFirstPrinciplesEngine("test")
        for i in range(10):
            engine.add_experience(
                state={"s": i}, action="a", reward=1.0,
                next_state={"s": i + 1},
            )
        # 请求100但只有10
        sampled = engine.sample_experiences(100)
        assert len(sampled) == 10

    def test_scheduler_with_nan_error(self):
        """调度器NaN误差"""
        sched = LearningRateScheduler(schedule_type=LRScheduleType.ADAPTIVE)
        # 不应崩溃
        for _ in range(20):
            sched.step(float("nan"))


# ============================================================
# 10. 第一性原理验证测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_error_driven_learning(self):
        """误差驱动学习"""
        engine = LearningFirstPrinciplesEngine("test")
        # 有误差 → 学习
        update = engine.learn_from_error("w1", 0.5, 1.0, "test")
        assert update is not None
        # 无误差 → 不学习
        update_zero = engine.learn_from_error("w2", 0.0, 1.0)
        assert update_zero is None

    def test_experience_reuse(self):
        """经验复用"""
        engine = LearningFirstPrinciplesEngine("test")
        # 添加经验
        for i in range(20):
            engine.add_experience(
                state={"s": float(i)}, action="a", reward=1.0,
                next_state={"s": float(i + 1)}, td_error=0.2,
            )
        # 第一次回放学习
        updates1 = engine.replay_learn(batch_size=10)
        count1 = len(updates1)
        # 第二次回放学习（复用经验）
        updates2 = engine.replay_learn(batch_size=10)
        count2 = len(updates2)
        # 两次都应产生学习
        assert count1 > 0
        assert count2 > 0

    def test_momentum_accelerates_convergence(self):
        """动量加速收敛"""
        # 无动量
        learner_no = OnlineLearner(momentum=0.0, max_gradient=1.0)
        learner_no.set_parameter("w", 0.0)
        for _ in range(20):
            learner_no.update("w", gradient=1.0)
        final_no = learner_no.get_parameter("w")

        # 有动量
        learner_yes = OnlineLearner(momentum=0.9, max_gradient=1.0)
        learner_yes.set_parameter("w", 0.0)
        for _ in range(20):
            learner_yes.update("w", gradient=1.0)
        final_yes = learner_yes.get_parameter("w")

        # 有动量应移动更远（更快收敛）
        assert abs(final_yes) > abs(final_no)

    def test_gradient_clipping_prevents_explosion(self):
        """梯度裁剪防止爆炸"""
        learner = OnlineLearner(momentum=0.0, max_gradient=1.0)
        learner.set_parameter("w", 0.0)
        # 巨大梯度
        for _ in range(10):
            learner.update("w", gradient=10000.0)
        final = learner.get_parameter("w")
        # 应被裁剪，不会爆炸
        assert abs(final) < 1.0

    def test_priority_replay_favors_surprising(self):
        """优先级回放偏向高TD误差"""
        buf = ExperienceReplayBuffer(seed=42)
        # 添加低TD和高TD经验
        for i in range(50):
            td = 0.01 if i < 25 else 1.0  # 前25个低，后25个高
            buf.add(Experience(
                f"e{i}", {"s": i}, "a", 1.0, {"s": i + 1}, td_error=td,
            ))
        # 优先级采样
        sampled = buf.sample(batch_size=20, prioritized=True)
        # 高TD误差的经验应占多数
        high_td_count = sum(1 for e in sampled if e.td_error > 0.5)
        assert high_td_count > 10  # 大部分应是高TD

    def test_adaptive_lr_responds_to_trend(self):
        """自适应学习率响应趋势"""
        sched = LearningRateScheduler(
            base_lr=0.01, schedule_type=LRScheduleType.ADAPTIVE,
        )
        # 误差下降趋势
        initial_factor = sched._adaptive_factor
        for i in range(30):
            error = 1.0 * (0.95 ** i)  # 指数下降
            sched.step(error)
        # 因子应增大
        assert sched._adaptive_factor > initial_factor

    def test_traceability_all_updates_from_errors(self):
        """可追溯性：所有更新源于误差"""
        engine = LearningFirstPrinciplesEngine("test")
        update = engine.learn_from_error("w1", 0.5, 1.0, "source1")
        # 追溯到误差信号
        signal = engine.trace_update_to_error(update.update_id)
        assert signal is not None
        assert signal.error_source == "source1"
        assert signal.error_magnitude == 0.5
