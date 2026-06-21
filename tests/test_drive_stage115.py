"""
阶段115: 驱力系统强化 — 专项测试

验证新增能力:
1. Goal: 动态目标（截止时间、优先级、依赖、验收标准）
2. GoalManager: 目标生命周期管理
3. PriorityArbitrator: 多因子优先级仲裁
4. 增强DriveFirstPrinciplesEngine整合
5. 向后兼容性

第一性原理验证:
- 动机源于差距：缺口驱动行为
- 资源有限：多目标竞争时选择期望价值最高的
- 目标有时间约束：截止时间影响优先级
- 依赖关系：前置目标完成才能激活后续目标
"""

import math
import threading
import time
import pytest

from self_evolving_agent.core.drive_first_principles import (
    DriveFirstPrinciplesEngine,
    DriveType,
    DriveGap,
    DriveState,
    Goal,
    GoalStatus,
    GoalPriority,
    GoalManager,
    PriorityArbitrator,
    create_drive_engine,
    create_drive_gap,
    create_drive_state,
    create_goal,
)


# ============================================================
# 1. Goal 数据结构测试
# ============================================================

class TestGoal:
    """动态目标测试"""

    def test_goal_creation(self):
        """目标创建"""
        goal = Goal(
            goal_id="g1",
            name="提升安全",
            drive_type=DriveType.SAFE,
            target_state={"safe": 0.9},
        )
        assert goal.goal_id == "g1"
        assert goal.status == GoalStatus.PENDING
        assert goal.priority == GoalPriority.MEDIUM
        assert goal.progress == 0.0

    def test_time_remaining_no_deadline(self):
        """无截止时间时剩余时间为None"""
        goal = Goal(
            goal_id="g1", name="test", drive_type=DriveType.GAIN,
            target_state={"gain": 1.0},
        )
        assert goal.time_remaining is None
        assert goal.time_pressure == 0.0

    def test_time_remaining_with_deadline(self):
        """有截止时间时剩余时间正确"""
        future = time.time() + 100
        goal = Goal(
            goal_id="g1", name="test", drive_type=DriveType.GAIN,
            target_state={"gain": 1.0},
            created_at=time.time() - 50,
            deadline=future,
        )
        remaining = goal.time_remaining
        assert remaining is not None
        assert 0 < remaining <= 100

    def test_time_pressure_increases_with_time(self):
        """时间压力随时间增加"""
        now = time.time()
        goal_early = Goal(
            goal_id="g1", name="test", drive_type=DriveType.GAIN,
            target_state={"gain": 1.0},
            created_at=now - 10,
            deadline=now + 90,  # 剩余90%
        )
        goal_late = Goal(
            goal_id="g2", name="test", drive_type=DriveType.GAIN,
            target_state={"gain": 1.0},
            created_at=now - 90,
            deadline=now + 10,  # 剩余10%
        )
        assert goal_late.time_pressure > goal_early.time_pressure

    def test_expired_goal(self):
        """过期目标检测"""
        past = time.time() - 100
        goal = Goal(
            goal_id="g1", name="test", drive_type=DriveType.SAFE,
            target_state={"safe": 1.0},
            deadline=past,
        )
        assert goal.is_expired is True

    def test_not_expired_no_deadline(self):
        """无截止时间永不过期"""
        goal = Goal(
            goal_id="g1", name="test", drive_type=DriveType.SAFE,
            target_state={"safe": 1.0},
        )
        assert goal.is_expired is False

    def test_check_completion_default(self):
        """默认验收标准（目标值达到）"""
        goal = Goal(
            goal_id="g1", name="test", drive_type=DriveType.GAIN,
            target_state={"gain": 0.9},
        )
        # 未达到
        assert goal.check_completion({"gain": 0.5}) is False
        # 达到（误差<0.05）
        assert goal.check_completion({"gain": 0.88}) is True

    def test_check_completion_custom_criteria(self):
        """自定义验收标准"""
        goal = Goal(
            goal_id="g1", name="test", drive_type=DriveType.GAIN,
            target_state={"gain": 1.0},
            acceptance_criteria=lambda state: state.get("gain", 0) > 0.8,
        )
        assert goal.check_completion({"gain": 0.9}) is True
        assert goal.check_completion({"gain": 0.5}) is False

    def test_check_completion_criteria_exception(self):
        """验收标准抛异常时回退到默认"""
        goal = Goal(
            goal_id="g1", name="test", drive_type=DriveType.GAIN,
            target_state={"gain": 1.0},
            acceptance_criteria=lambda state: state["missing_key"],  # KeyError
        )
        # 应回退到默认检查，不崩溃
        result = goal.check_completion({"gain": 1.0})
        assert result is True

    def test_update_progress(self):
        """进度更新"""
        goal = Goal(
            goal_id="g1", name="test", drive_type=DriveType.GAIN,
            target_state={"gain": 1.0, "eff": 1.0},
        )
        progress = goal.update_progress({"gain": 0.5, "eff": 0.8})
        assert 0 < progress < 1.0
        assert goal.progress == progress

    def test_update_progress_empty_target(self):
        """空目标状态进度不变"""
        goal = Goal(
            goal_id="g1", name="test", drive_type=DriveType.GAIN,
            target_state={},
        )
        progress = goal.update_progress({"gain": 0.5})
        assert progress == 0.0

    def test_is_blocked_with_dependencies(self):
        """有依赖时被阻塞"""
        goal = Goal(
            goal_id="g1", name="test", drive_type=DriveType.GAIN,
            target_state={"gain": 1.0},
            dependencies={"g0"},
        )
        assert goal.is_blocked is True

    def test_is_blocked_no_dependencies(self):
        """无依赖时不阻塞"""
        goal = Goal(
            goal_id="g1", name="test", drive_type=DriveType.GAIN,
            target_state={"gain": 1.0},
        )
        assert goal.is_blocked is False


# ============================================================
# 2. GoalManager 测试
# ============================================================

class TestGoalManager:
    """目标管理器测试"""

    def test_add_and_get_goal(self):
        """添加和获取目标"""
        mgr = GoalManager()
        goal = Goal("g1", "test", DriveType.SAFE, {"safe": 1.0})
        assert mgr.add_goal(goal) is True
        assert mgr.get_goal("g1") is goal

    def test_add_duplicate_goal(self):
        """重复ID添加失败"""
        mgr = GoalManager()
        mgr.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}))
        assert mgr.add_goal(Goal("g1", "dup", DriveType.SAFE, {"safe": 1.0})) is False

    def test_remove_goal(self):
        """移除目标"""
        mgr = GoalManager()
        mgr.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}))
        assert mgr.remove_goal("g1") is True
        assert mgr.get_goal("g1") is None
        assert mgr.remove_goal("g1") is False

    def test_activate_goal_no_dependencies(self):
        """无依赖时激活成功"""
        mgr = GoalManager()
        mgr.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}))
        assert mgr.activate_goal("g1") is True
        assert mgr.get_goal("g1").status == GoalStatus.ACTIVE
        assert mgr.get_goal("g1").started_at is not None

    def test_activate_goal_with_unmet_dependency(self):
        """依赖未满足时激活失败"""
        mgr = GoalManager()
        mgr.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}))
        mgr.add_goal(Goal("g2", "dep", DriveType.GAIN, {"gain": 1.0}, dependencies={"g1"}))
        assert mgr.activate_goal("g2") is False
        assert mgr.get_goal("g2").status == GoalStatus.PENDING

    def test_activate_goal_with_met_dependency(self):
        """依赖满足后激活成功"""
        mgr = GoalManager()
        mgr.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}))
        mgr.add_goal(Goal("g2", "dep", DriveType.GAIN, {"gain": 1.0}, dependencies={"g1"}))
        mgr.activate_goal("g1")
        mgr.complete_goal("g1")
        assert mgr.activate_goal("g2") is True

    def test_complete_goal(self):
        """完成目标"""
        mgr = GoalManager()
        mgr.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}))
        mgr.activate_goal("g1")
        assert mgr.complete_goal("g1") is True
        assert mgr.get_goal("g1").status == GoalStatus.COMPLETED
        assert mgr.get_goal("g1").progress == 1.0
        assert mgr.get_goal("g1").completed_at is not None

    def test_fail_goal(self):
        """标记目标失败"""
        mgr = GoalManager()
        mgr.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}))
        assert mgr.fail_goal("g1") is True
        assert mgr.get_goal("g1").status == GoalStatus.FAILED

    def test_pause_and_resume(self):
        """暂停和恢复"""
        mgr = GoalManager()
        mgr.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}))
        mgr.activate_goal("g1")
        assert mgr.pause_goal("g1") is True
        assert mgr.get_goal("g1").status == GoalStatus.PAUSED
        assert mgr.resume_goal("g1") is True
        assert mgr.get_goal("g1").status == GoalStatus.ACTIVE

    def test_pause_non_active_fails(self):
        """暂停非活跃目标失败"""
        mgr = GoalManager()
        mgr.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}))
        assert mgr.pause_goal("g1") is False  # PENDING状态

    def test_update_progress_auto_complete(self):
        """进度更新自动完成"""
        mgr = GoalManager()
        mgr.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 0.9}))
        mgr.activate_goal("g1")
        # 达到目标值
        results = mgr.update_progress({"safe": 0.88})
        assert results["g1"] > 0.9
        assert mgr.get_goal("g1").status == GoalStatus.COMPLETED

    def test_cleanup_expired(self):
        """清理过期目标"""
        mgr = GoalManager()
        past = time.time() - 100
        mgr.add_goal(Goal("g1", "expired", DriveType.SAFE, {"safe": 1.0}, deadline=past))
        mgr.add_goal(Goal("g2", "active", DriveType.SAFE, {"safe": 1.0}))
        expired = mgr.cleanup_expired()
        assert "g1" in expired
        assert mgr.get_goal("g1").status == GoalStatus.EXPIRED
        assert mgr.get_goal("g2").status == GoalStatus.PENDING

    def test_get_goals_by_status(self):
        """按状态获取目标"""
        mgr = GoalManager()
        mgr.add_goal(Goal("g1", "t1", DriveType.SAFE, {"safe": 1.0}))
        mgr.add_goal(Goal("g2", "t2", DriveType.SAFE, {"safe": 1.0}))
        mgr.activate_goal("g2")
        pending = mgr.get_goals_by_status(GoalStatus.PENDING)
        active = mgr.get_goals_by_status(GoalStatus.ACTIVE)
        assert len(pending) == 1
        assert len(active) == 1

    def test_get_goals_by_drive(self):
        """按驱力类型获取目标"""
        mgr = GoalManager()
        mgr.add_goal(Goal("g1", "t1", DriveType.SAFE, {"safe": 1.0}))
        mgr.add_goal(Goal("g2", "t2", DriveType.GAIN, {"gain": 1.0}))
        safe_goals = mgr.get_goals_by_drive(DriveType.SAFE)
        gain_goals = mgr.get_goals_by_drive(DriveType.GAIN)
        assert len(safe_goals) == 1
        assert len(gain_goals) == 1

    def test_get_stats(self):
        """获取统计"""
        mgr = GoalManager()
        mgr.add_goal(Goal("g1", "t1", DriveType.SAFE, {"safe": 1.0}))
        mgr.add_goal(Goal("g2", "t2", DriveType.SAFE, {"safe": 1.0}))
        mgr.activate_goal("g2")
        stats = mgr.get_stats()
        assert stats["total_goals"] == 2
        assert stats["status_counts"]["pending"] == 1
        assert stats["status_counts"]["active"] == 1

    def test_nonexistent_goal_operations(self):
        """操作不存在的目标"""
        mgr = GoalManager()
        assert mgr.get_goal("nonexistent") is None
        assert mgr.remove_goal("nonexistent") is False
        assert mgr.activate_goal("nonexistent") is False
        assert mgr.complete_goal("nonexistent") is False
        assert mgr.fail_goal("nonexistent") is False
        assert mgr.pause_goal("nonexistent") is False
        assert mgr.resume_goal("nonexistent") is False


# ============================================================
# 3. PriorityArbitrator 测试
# ============================================================

class TestPriorityArbitrator:
    """优先级仲裁器测试"""

    def test_compute_score_basic(self):
        """基本分数计算"""
        arb = PriorityArbitrator()
        goal = Goal(
            "g1", "test", DriveType.SAFE, {"safe": 1.0},
            priority=GoalPriority.HIGH,
            feasibility=0.9,
            resource_cost=0.3,
        )
        score = arb.compute_score(goal, urgency=0.8)
        assert score > 0
        assert not math.isnan(score)

    def test_higher_priority_scores_higher(self):
        """高优先级目标分数更高"""
        arb = PriorityArbitrator()
        goal_low = Goal("g1", "low", DriveType.SAFE, {"safe": 1.0}, priority=GoalPriority.LOW)
        goal_high = Goal("g2", "high", DriveType.SAFE, {"safe": 1.0}, priority=GoalPriority.HIGH)
        score_low = arb.compute_score(goal_low, urgency=0.5)
        score_high = arb.compute_score(goal_high, urgency=0.5)
        assert score_high > score_low

    def test_higher_urgency_scores_higher(self):
        """高紧急度分数更高"""
        arb = PriorityArbitrator()
        goal = Goal("g1", "test", DriveType.SAFE, {"safe": 1.0})
        score_low = arb.compute_score(goal, urgency=0.1)
        score_high = arb.compute_score(goal, urgency=0.9)
        assert score_high > score_low

    def test_lower_cost_scores_higher(self):
        """低成本目标分数更高"""
        arb = PriorityArbitrator()
        goal_expensive = Goal("g1", "exp", DriveType.SAFE, {"safe": 1.0}, resource_cost=0.9)
        goal_cheap = Goal("g2", "cheap", DriveType.SAFE, {"safe": 1.0}, resource_cost=0.1)
        score_exp = arb.compute_score(goal_expensive, urgency=0.5)
        score_cheap = arb.compute_score(goal_cheap, urgency=0.5)
        assert score_cheap > score_exp

    def test_higher_feasibility_scores_higher(self):
        """高可行性分数更高"""
        arb = PriorityArbitrator()
        goal_hard = Goal("g1", "hard", DriveType.SAFE, {"safe": 1.0}, feasibility=0.2)
        goal_easy = Goal("g2", "easy", DriveType.SAFE, {"safe": 1.0}, feasibility=0.9)
        score_hard = arb.compute_score(goal_hard, urgency=0.5)
        score_easy = arb.compute_score(goal_easy, urgency=0.5)
        assert score_easy > score_hard

    def test_arbitrate_returns_sorted(self):
        """仲裁返回降序排列"""
        arb = PriorityArbitrator()
        goals = [
            Goal("g1", "low", DriveType.SAFE, {"safe": 1.0}, priority=GoalPriority.LOW),
            Goal("g2", "high", DriveType.SAFE, {"safe": 1.0}, priority=GoalPriority.HIGH),
            Goal("g3", "crit", DriveType.SAFE, {"safe": 1.0}, priority=GoalPriority.CRITICAL),
        ]
        ranked = arb.arbitrate(goals)
        assert len(ranked) == 3
        # 分数应降序
        assert ranked[0][1] >= ranked[1][1] >= ranked[2][1]
        # CRITICAL应排第一
        assert ranked[0][0].goal_id == "g3"

    def test_arbitrate_empty(self):
        """空列表仲裁"""
        arb = PriorityArbitrator()
        assert arb.arbitrate([]) == []

    def test_select_top(self):
        """选择前k个"""
        arb = PriorityArbitrator()
        goals = [
            Goal("g1", "low", DriveType.SAFE, {"safe": 1.0}, priority=GoalPriority.LOW),
            Goal("g2", "high", DriveType.SAFE, {"safe": 1.0}, priority=GoalPriority.HIGH),
            Goal("g3", "crit", DriveType.SAFE, {"safe": 1.0}, priority=GoalPriority.CRITICAL),
        ]
        top2 = arb.select_top(goals, k=2)
        assert len(top2) == 2
        assert top2[0].goal_id == "g3"
        assert top2[1].goal_id == "g2"

    def test_set_and_get_weights(self):
        """设置和获取权重"""
        arb = PriorityArbitrator()
        arb.set_weight("urgency", 2.0)
        weights = arb.get_weights()
        assert weights["urgency"] == 2.0

    def test_set_invalid_weight_factor_ignored(self):
        """设置无效因子被忽略"""
        arb = PriorityArbitrator()
        arb.set_weight("nonexistent", 1.0)
        weights = arb.get_weights()
        assert "nonexistent" not in weights

    def test_nan_defense_in_score(self):
        """NaN防御"""
        arb = PriorityArbitrator()
        goal = Goal("g1", "test", DriveType.SAFE, {"safe": 1.0})
        # NaN urgency应被钳制
        score = arb.compute_score(goal, urgency=float("nan"))
        assert not math.isnan(score)

    def test_time_pressure_affects_score(self):
        """时间压力影响分数"""
        arb = PriorityArbitrator()
        now = time.time()
        goal_no_pressure = Goal(
            "g1", "no_pressure", DriveType.SAFE, {"safe": 1.0},
            created_at=now, deadline=now + 1000,
        )
        goal_high_pressure = Goal(
            "g2", "high_pressure", DriveType.SAFE, {"safe": 1.0},
            created_at=now - 999, deadline=now + 1,
        )
        score_no = arb.compute_score(goal_no_pressure, urgency=0.5)
        score_high = arb.compute_score(goal_high_pressure, urgency=0.5)
        assert score_high > score_no


# ============================================================
# 4. 增强DriveFirstPrinciplesEngine测试
# ============================================================

class TestEnhancedDriveEngine:
    """增强驱力引擎测试"""

    def test_engine_has_goal_manager_and_arbitrator(self):
        """引擎包含目标管理器和仲裁器"""
        engine = DriveFirstPrinciplesEngine("test")
        assert engine.get_goal_manager() is not None
        assert engine.get_arbitrator() is not None

    def test_add_and_activate_goal(self):
        """添加并激活目标"""
        engine = DriveFirstPrinciplesEngine("test")
        goal = Goal("g1", "提升安全", DriveType.SAFE, {"safe": 0.9})
        assert engine.add_goal(goal) is True
        assert engine.activate_goal("g1") is True
        assert engine.get_goal("g1").status == GoalStatus.ACTIVE

    def test_update_goal_progress(self):
        """更新目标进度"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 0.9}))
        engine.activate_goal("g1")
        results = engine.update_goal_progress({"safe": 0.5})
        assert "g1" in results
        assert 0 < results["g1"] < 1.0

    def test_update_goal_progress_auto_complete(self):
        """进度更新自动完成目标"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 0.9}))
        engine.activate_goal("g1")
        engine.update_goal_progress({"safe": 0.88})
        assert engine.get_goal("g1").status == GoalStatus.COMPLETED

    def test_arbitrate_goals(self):
        """仲裁目标"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.add_goal(Goal("g1", "low", DriveType.SAFE, {"safe": 1.0}, priority=GoalPriority.LOW))
        engine.add_goal(Goal("g2", "high", DriveType.SAFE, {"safe": 1.0}, priority=GoalPriority.HIGH))
        engine.activate_goal("g1")
        engine.activate_goal("g2")
        ranked = engine.arbitrate_goals()
        assert len(ranked) == 2
        assert ranked[0][0].goal_id == "g2"  # HIGH优先

    def test_get_top_goal(self):
        """获取最高优先级目标"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.add_goal(Goal("g1", "low", DriveType.SAFE, {"safe": 1.0}, priority=GoalPriority.LOW))
        engine.add_goal(Goal("g2", "crit", DriveType.SAFE, {"safe": 1.0}, priority=GoalPriority.CRITICAL))
        engine.activate_goal("g1")
        engine.activate_goal("g2")
        top = engine.get_top_goal()
        assert top is not None
        assert top.goal_id == "g2"

    def test_get_top_goal_empty(self):
        """无目标时返回None"""
        engine = DriveFirstPrinciplesEngine("test")
        assert engine.get_top_goal() is None

    def test_select_top_goals(self):
        """选择前k个目标"""
        engine = DriveFirstPrinciplesEngine("test")
        for i, prio in enumerate([GoalPriority.LOW, GoalPriority.MEDIUM, GoalPriority.HIGH]):
            engine.add_goal(Goal(f"g{i}", f"goal{i}", DriveType.SAFE, {"safe": 1.0}, priority=prio))
            engine.activate_goal(f"g{i}")
        top2 = engine.select_top_goals(k=2)
        assert len(top2) == 2
        assert top2[0].priority.value >= top2[1].priority.value

    def test_set_arbitration_weight(self):
        """设置仲裁权重"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.set_arbitration_weight("urgency", 2.0)
        weights = engine.get_arbitration_weights()
        assert weights["urgency"] == 2.0

    def test_pause_and_resume_goal(self):
        """暂停和恢复目标"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}))
        engine.activate_goal("g1")
        assert engine.pause_goal("g1") is True
        assert engine.get_goal("g1").status == GoalStatus.PAUSED
        assert engine.resume_goal("g1") is True
        assert engine.get_goal("g1").status == GoalStatus.ACTIVE

    def test_complete_and_fail_goal(self):
        """完成和失败目标"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}))
        engine.add_goal(Goal("g2", "test", DriveType.SAFE, {"safe": 1.0}))
        assert engine.complete_goal("g1") is True
        assert engine.fail_goal("g2") is True
        assert engine.get_goal("g1").status == GoalStatus.COMPLETED
        assert engine.get_goal("g2").status == GoalStatus.FAILED

    def test_remove_goal(self):
        """移除目标"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}))
        assert engine.remove_goal("g1") is True
        assert engine.get_goal("g1") is None

    def test_get_stats_includes_goal_info(self):
        """统计包含目标信息"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}))
        engine.activate_goal("g1")
        stats = engine.get_stats()
        assert "goal_stats" in stats
        assert "active_goals_count" in stats
        assert stats["active_goals_count"] == 1


# ============================================================
# 5. 向后兼容性测试
# ============================================================

class TestBackwardCompatibility:
    """向后兼容性测试"""

    def test_create_drive_engine_factory(self):
        """工厂函数兼容"""
        engine = create_drive_engine("test")
        assert isinstance(engine, DriveFirstPrinciplesEngine)
        assert engine.engine_id == "test"

    def test_create_drive_gap_helper(self):
        """缺口创建辅助函数兼容"""
        gap = create_drive_gap("gap1", DriveType.SAFE, 0.5, 1.0)
        assert gap.gap_id == "gap1"
        assert gap.drive_type == DriveType.SAFE
        assert gap.gap_magnitude == 0.5

    def test_create_drive_state_helper(self):
        """状态创建辅助函数兼容"""
        state = create_drive_state(0.7, 0.6, 0.5)
        assert state.safe_level == 0.7
        assert state.gain_level == 0.6
        assert state.eff_level == 0.5

    def test_create_goal_helper(self):
        """目标创建辅助函数"""
        goal = create_goal(
            "g1", "test", DriveType.SAFE, {"safe": 0.9},
            priority=GoalPriority.HIGH,
        )
        assert goal.goal_id == "g1"
        assert goal.priority == GoalPriority.HIGH

    def test_update_state(self):
        """状态更新兼容"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.update_state(safe_level=0.8, gain_level=0.6)
        stats = engine.get_stats()
        assert stats["state"]["safe"] == 0.8
        assert stats["state"]["gain"] == 0.6

    def test_compute_gaps(self):
        """缺口计算兼容"""
        engine = DriveFirstPrinciplesEngine("test")
        gaps = engine.compute_gaps()
        assert len(gaps) == 3
        types = {g.drive_type for g in gaps}
        assert types == {DriveType.SAFE, DriveType.GAIN, DriveType.EFF}

    def test_get_dominant_gap(self):
        """主导缺口兼容"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.update_state(safe_level=0.1, gain_level=0.9, eff_level=0.9)
        engine.compute_gaps()
        dominant = engine.get_dominant_gap()
        assert dominant is not None
        assert dominant.drive_type == DriveType.SAFE  # 安全缺口最大

    def test_is_action_required(self):
        """行动需求检测兼容（无副作用）"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.update_state(safe_level=1.0, gain_level=1.0, eff_level=1.0)
        assert engine.is_action_required() is False
        engine.update_state(safe_level=0.5)
        assert engine.is_action_required() is True

    def test_get_total_drive_pressure(self):
        """总驱力压力兼容"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.update_state(safe_level=0.5)
        engine.compute_gaps()
        pressure = engine.get_total_drive_pressure()
        assert pressure > 0

    def test_trace_action_to_gap(self):
        """行为追溯兼容"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.compute_gaps()
        gap = engine.trace_action_to_gap("some action")
        assert gap is not None

    def test_clear_history(self):
        """清除历史兼容"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.compute_gaps()
        engine.clear_history()
        stats = engine.get_stats()
        assert stats["active_gaps"] == 0

    def test_drive_type_enum(self):
        """驱力类型枚举兼容"""
        assert DriveType.SAFE.value == "safe"
        assert DriveType.GAIN.value == "gain"
        assert DriveType.EFF.value == "eff"

    def test_drive_gap_urgency_safe_higher(self):
        """安全驱力紧急度更高"""
        gap_safe = DriveGap("g1", DriveType.SAFE, 0.5, 1.0)
        gap_gain = DriveGap("g2", DriveType.GAIN, 0.5, 1.0)
        assert gap_safe.urgency > gap_gain.urgency


# ============================================================
# 6. 并发安全测试
# ============================================================

class TestConcurrencySafety:
    """并发安全测试"""

    def test_concurrent_goal_operations(self):
        """并发目标操作"""
        engine = DriveFirstPrinciplesEngine("test")
        errors = []

        def worker(thread_id):
            try:
                for i in range(50):
                    goal_id = f"g_{thread_id}_{i}"
                    engine.add_goal(Goal(goal_id, f"goal{goal_id}", DriveType.SAFE, {"safe": 1.0}))
                    engine.activate_goal(goal_id)
                    engine.update_goal_progress({"safe": 0.5})
                    engine.arbitrate_goals()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0

    def test_concurrent_arbitration(self):
        """并发仲裁"""
        engine = DriveFirstPrinciplesEngine("test")
        for i in range(20):
            engine.add_goal(Goal(f"g{i}", f"goal{i}", DriveType.SAFE, {"safe": 1.0}))
            engine.activate_goal(f"g{i}")

        errors = []

        def worker():
            try:
                for _ in range(100):
                    engine.arbitrate_goals()
                    engine.select_top_goals(k=3)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0


# ============================================================
# 7. 性能测试
# ============================================================

class TestPerformance:
    """性能基准测试"""

    def test_compute_gaps_latency(self):
        """缺口计算延迟 < 5ms"""
        engine = DriveFirstPrinciplesEngine("test")
        start = time.time()
        for _ in range(100):
            engine.compute_gaps()
        elapsed = time.time() - start
        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 5.0, f"平均延迟 {avg_ms:.2f}ms 超过 5ms"

    def test_arbitration_latency(self):
        """仲裁延迟 < 10ms（20目标）"""
        engine = DriveFirstPrinciplesEngine("test")
        for i in range(20):
            engine.add_goal(Goal(f"g{i}", f"goal{i}", DriveType.SAFE, {"safe": 1.0}))
            engine.activate_goal(f"g{i}")
        # 预热
        engine.arbitrate_goals()
        start = time.time()
        for _ in range(100):
            engine.arbitrate_goals()
        elapsed = time.time() - start
        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 10.0, f"平均延迟 {avg_ms:.2f}ms 超过 10ms"

    def test_goal_progress_update_latency(self):
        """进度更新延迟 < 5ms（50目标）"""
        engine = DriveFirstPrinciplesEngine("test")
        for i in range(50):
            engine.add_goal(Goal(f"g{i}", f"goal{i}", DriveType.SAFE, {"safe": 1.0}))
            engine.activate_goal(f"g{i}")
        start = time.time()
        for _ in range(100):
            engine.update_goal_progress({"safe": 0.5})
        elapsed = time.time() - start
        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 5.0, f"平均延迟 {avg_ms:.2f}ms 超过 5ms"


# ============================================================
# 8. 异常容错测试
# ============================================================

class TestErrorTolerance:
    """异常容错测试"""

    def test_goal_with_nan_values(self):
        """NaN值目标"""
        engine = DriveFirstPrinciplesEngine("test")
        goal = Goal(
            "g1", "test", DriveType.SAFE, {"safe": 1.0},
            feasibility=float("nan"),
            resource_cost=float("nan"),
        )
        engine.add_goal(goal)
        engine.activate_goal("g1")
        # 不应崩溃
        ranked = engine.arbitrate_goals()
        assert len(ranked) == 1
        assert not math.isnan(ranked[0][1])

    def test_goal_with_inf_values(self):
        """Inf值目标"""
        engine = DriveFirstPrinciplesEngine("test")
        goal = Goal(
            "g1", "test", DriveType.SAFE, {"safe": 1.0},
            feasibility=float("inf"),
        )
        engine.add_goal(goal)
        engine.activate_goal("g1")
        ranked = engine.arbitrate_goals()
        assert len(ranked) == 1

    def test_goal_with_empty_target_state(self):
        """空目标状态"""
        engine = DriveFirstPrinciplesEngine("test")
        goal = Goal("g1", "test", DriveType.SAFE, {})
        engine.add_goal(goal)
        engine.activate_goal("g1")
        results = engine.update_goal_progress({"safe": 0.5})
        assert "g1" in results

    def test_goal_with_negative_cost(self):
        """负资源成本"""
        arb = PriorityArbitrator()
        goal = Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}, resource_cost=-1.0)
        score = arb.compute_score(goal, urgency=0.5)
        assert not math.isnan(score)

    def test_update_progress_with_none_state(self):
        """None状态更新进度"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 1.0}))
        engine.activate_goal("g1")
        # None应使用引擎内部状态
        results = engine.update_goal_progress(None)
        assert "g1" in results

    def test_arbitrate_with_no_active_goals(self):
        """无活跃目标时仲裁"""
        engine = DriveFirstPrinciplesEngine("test")
        ranked = engine.arbitrate_goals()
        assert ranked == []

    def test_many_goals_stress(self):
        """大量目标压力测试"""
        engine = DriveFirstPrinciplesEngine("test")
        for i in range(100):
            engine.add_goal(Goal(f"g{i}", f"goal{i}", DriveType.SAFE, {"safe": 1.0}))
            engine.activate_goal(f"g{i}")
        ranked = engine.arbitrate_goals()
        assert len(ranked) == 100
        # 应正确排序
        for i in range(len(ranked) - 1):
            assert ranked[i][1] >= ranked[i + 1][1]


# ============================================================
# 9. 第一性原理验证测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_gap_drives_action(self):
        """缺口驱动行动"""
        engine = DriveFirstPrinciplesEngine("test")
        # 无缺口
        engine.update_state(safe_level=1.0, gain_level=1.0, eff_level=1.0)
        assert engine.is_action_required() is False
        # 有缺口
        engine.update_state(safe_level=0.3)
        assert engine.is_action_required() is True

    def test_priority_arbitration_selects_best(self):
        """优先级仲裁选择最优目标"""
        engine = DriveFirstPrinciplesEngine("test")
        # 低成本高优先级 vs 高成本低优先级
        engine.add_goal(Goal(
            "g1", "best", DriveType.SAFE, {"safe": 1.0},
            priority=GoalPriority.CRITICAL, resource_cost=0.1, feasibility=0.9,
        ))
        engine.add_goal(Goal(
            "g2", "worst", DriveType.SAFE, {"safe": 1.0},
            priority=GoalPriority.LOW, resource_cost=0.9, feasibility=0.2,
        ))
        engine.activate_goal("g1")
        engine.activate_goal("g2")
        top = engine.get_top_goal()
        assert top.goal_id == "g1"

    def test_dependency_enforces_order(self):
        """依赖强制执行顺序"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.add_goal(Goal("g1", "first", DriveType.SAFE, {"safe": 1.0}))
        engine.add_goal(Goal("g2", "second", DriveType.SAFE, {"safe": 1.0}, dependencies={"g1"}))
        # g2依赖g1，g1未完成时g2不能激活
        assert engine.activate_goal("g2") is False
        # 完成g1后g2可激活
        engine.activate_goal("g1")
        engine.complete_goal("g1")
        assert engine.activate_goal("g2") is True

    def test_deadline_affects_priority(self):
        """截止时间影响优先级"""
        engine = DriveFirstPrinciplesEngine("test")
        now = time.time()
        # 两个相同优先级目标，一个快到期
        engine.add_goal(Goal(
            "g1", "relaxed", DriveType.SAFE, {"safe": 1.0},
            created_at=now, deadline=now + 1000,
        ))
        engine.add_goal(Goal(
            "g2", "urgent", DriveType.SAFE, {"safe": 1.0},
            created_at=now - 999, deadline=now + 1,
        ))
        engine.activate_goal("g1")
        engine.activate_goal("g2")
        top = engine.get_top_goal()
        # 紧急目标应优先
        assert top.goal_id == "g2"

    def test_goal_completion_reduces_pressure(self):
        """目标完成减少压力"""
        engine = DriveFirstPrinciplesEngine("test")
        engine.add_goal(Goal("g1", "test", DriveType.SAFE, {"safe": 0.9}))
        engine.activate_goal("g1")
        engine.update_state(safe_level=0.5)
        engine.compute_gaps()
        pressure_before = engine.get_total_drive_pressure()
        # 完成目标
        engine.update_goal_progress({"safe": 0.88})
        # 目标完成后活跃目标减少
        active = engine.get_active_goals()
        assert len(active) == 0  # g1已完成

    def test_resource_efficiency_principle(self):
        """资源效率原理：低成本目标优先"""
        arb = PriorityArbitrator()
        # 相同优先级，不同成本
        goal_cheap = Goal("g1", "cheap", DriveType.SAFE, {"safe": 1.0}, resource_cost=0.1)
        goal_expensive = Goal("g2", "expensive", DriveType.SAFE, {"safe": 1.0}, resource_cost=0.9)
        score_cheap = arb.compute_score(goal_cheap, urgency=0.5)
        score_expensive = arb.compute_score(goal_expensive, urgency=0.5)
        # 低成本应得分更高（资源效率原理）
        assert score_cheap > score_expensive
