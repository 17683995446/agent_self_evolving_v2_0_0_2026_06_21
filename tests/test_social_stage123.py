"""
阶段123: 社交能力强化 — 专项测试

验证新增能力:
1. TheoryOfMind: 理论心智（信念、欲望、意图、情感建模）
2. PerspectiveTaking: 视角采择
3. TrustModel: 信任模型
4. Collaboration: 协作引擎
5. SocialFirstPrinciplesEngine: 新增接口
6. 向后兼容性

第一性原理验证:
- 理论心智 = 理解他人心理状态
- 协作产生规模效应
- 信任基于历史交互
- 视角采择基于心理状态
- 共情 = 理解他人情感
"""

import math
import threading
import time
import pytest

from self_evolving_agent.core.social_first_principles import (
    MessageType,
    MentalStateType,
    TaskStatus,
    AgentIdentity,
    InterAgentMessage,
    MentalState,
    CollaborationTask,
    TheoryOfMind,
    PerspectiveTaking,
    TrustModel,
    Collaboration,
    SocialFirstPrinciplesEngine,
    create_social_engine,
    create_agent_identity,
    create_theory_of_mind,
    create_trust_model,
    create_collaboration,
)


# ============================================================
# 1. TheoryOfMind 测试
# ============================================================

class TestTheoryOfMind:
    """理论心智测试"""

    def test_creation(self):
        """创建"""
        tom = TheoryOfMind()
        assert tom is not None

    def test_model_belief(self):
        """建模信念"""
        tom = TheoryOfMind()
        state = tom.model_belief("agent1", "task is hard", 0.8)
        assert state.agent_id == "agent1"
        assert state.state_type == MentalStateType.BELIEF
        assert state.content == "task is hard"
        assert abs(state.confidence - 0.8) < 1e-6

    def test_model_desire(self):
        """建模欲望"""
        tom = TheoryOfMind()
        state = tom.model_desire("agent1", "complete task")
        assert state.state_type == MentalStateType.DESIRE
        assert state.content == "complete task"

    def test_model_intention(self):
        """建模意图"""
        tom = TheoryOfMind()
        state = tom.model_intention("agent1", "ask for help")
        assert state.state_type == MentalStateType.INTENTION
        assert state.content == "ask for help"

    def test_model_emotion(self):
        """建模情感"""
        tom = TheoryOfMind()
        state = tom.model_emotion("agent1", "happy")
        assert state.state_type == MentalStateType.EMOTION
        assert state.content == "happy"

    def test_get_mental_states_all(self):
        """获取所有心理状态"""
        tom = TheoryOfMind()
        tom.model_belief("agent1", "belief1")
        tom.model_desire("agent1", "desire1")
        states = tom.get_mental_states("agent1")
        assert len(states) == 2

    def test_get_mental_states_by_type(self):
        """按类型获取心理状态"""
        tom = TheoryOfMind()
        tom.model_belief("agent1", "belief1")
        tom.model_desire("agent1", "desire1")
        tom.model_belief("agent1", "belief2")
        beliefs = tom.get_mental_states("agent1", MentalStateType.BELIEF)
        assert len(beliefs) == 2
        desires = tom.get_mental_states("agent1", MentalStateType.DESIRE)
        assert len(desires) == 1

    def test_get_mental_states_nonexistent(self):
        """不存在Agent的心理状态"""
        tom = TheoryOfMind()
        assert tom.get_mental_states("nonexistent") == []

    def test_get_latest_belief(self):
        """获取最新信念"""
        tom = TheoryOfMind()
        tom.model_belief("agent1", "old belief")
        tom.model_belief("agent1", "new belief")
        latest = tom.get_latest_belief("agent1")
        assert latest is not None
        assert latest.content == "new belief"

    def test_get_latest_belief_none(self):
        """无信念时返回None"""
        tom = TheoryOfMind()
        assert tom.get_latest_belief("agent1") is None

    def test_get_latest_desire(self):
        """获取最新欲望"""
        tom = TheoryOfMind()
        tom.model_desire("agent1", "desire1")
        latest = tom.get_latest_desire("agent1")
        assert latest is not None
        assert latest.content == "desire1"

    def test_get_latest_intention(self):
        """获取最新意图"""
        tom = TheoryOfMind()
        tom.model_intention("agent1", "intention1")
        latest = tom.get_latest_intention("agent1")
        assert latest is not None
        assert latest.content == "intention1"

    def test_predict_action(self):
        """预测行动"""
        tom = TheoryOfMind()
        tom.model_intention("agent1", "ask for help")
        action = tom.predict_action("agent1")
        assert action == "ask for help"

    def test_predict_action_no_intention(self):
        """无意图时预测返回None"""
        tom = TheoryOfMind()
        assert tom.predict_action("agent1") is None

    def test_confidence_clamping(self):
        """置信度钳制"""
        tom = TheoryOfMind()
        state = tom.model_belief("agent1", "belief", 1.5)
        assert state.confidence == 1.0
        state = tom.model_belief("agent1", "belief", -0.5)
        assert state.confidence == 0.0

    def test_confidence_nan_defense(self):
        """NaN置信度防御"""
        tom = TheoryOfMind()
        state = tom.model_belief("agent1", "belief", float("nan"))
        assert state.confidence == 0.5

    def test_confidence_inf_defense(self):
        """Inf置信度防御"""
        tom = TheoryOfMind()
        state = tom.model_belief("agent1", "belief", float("inf"))
        assert state.confidence == 0.5

    def test_confidence_string_defense(self):
        """字符串置信度防御"""
        tom = TheoryOfMind()
        state = tom.model_belief("agent1", "belief", "not a number")
        assert state.confidence == 0.5

    def test_clear_agent(self):
        """清除Agent心理状态"""
        tom = TheoryOfMind()
        tom.model_belief("agent1", "belief")
        tom.clear_agent("agent1")
        assert tom.get_mental_states("agent1") == []

    def test_clear_all(self):
        """清除所有"""
        tom = TheoryOfMind()
        tom.model_belief("agent1", "belief")
        tom.model_belief("agent2", "belief")
        tom.clear_all()
        assert tom.get_mental_states("agent1") == []
        assert tom.get_mental_states("agent2") == []


# ============================================================
# 2. PerspectiveTaking 测试
# ============================================================

class TestPerspectiveTaking:
    """视角采择测试"""

    def test_creation(self):
        """创建"""
        tom = TheoryOfMind()
        pt = PerspectiveTaking(tom)
        assert pt is not None

    def test_take_perspective_basic(self):
        """基本视角采择"""
        tom = TheoryOfMind()
        tom.model_belief("agent1", "task is hard")
        tom.model_desire("agent1", "complete task")
        tom.model_intention("agent1", "ask for help")
        pt = PerspectiveTaking(tom)
        persp = pt.take_perspective("agent1", {"task": "complete"})
        assert persp["agent_id"] == "agent1"
        assert persp["interpreted_belief"] == "task is hard"
        assert persp["interpreted_desire"] == "complete task"
        assert persp["interpreted_intention"] == "ask for help"

    def test_take_perspective_no_states(self):
        """无心理状态时视角采择"""
        tom = TheoryOfMind()
        pt = PerspectiveTaking(tom)
        persp = pt.take_perspective("agent1", "situation")
        assert persp["interpreted_belief"] is None
        assert persp["interpreted_desire"] is None
        assert persp["interpreted_intention"] is None

    def test_take_perspective_relevance(self):
        """相关性评估"""
        tom = TheoryOfMind()
        tom.model_desire("agent1", "task")
        pt = PerspectiveTaking(tom)
        persp = pt.take_perspective("agent1", {"task": "complete"})
        assert "relevance" in persp
        assert persp["relevance"] >= 0.0

    def test_infer_belief_basic(self):
        """推断信念"""
        tom = TheoryOfMind()
        pt = PerspectiveTaking(tom)
        belief = pt.infer_belief("agent1", {"action": "running"})
        assert belief is not None
        assert "running" in belief

    def test_infer_belief_none(self):
        """None观察推断返回None"""
        tom = TheoryOfMind()
        pt = PerspectiveTaking(tom)
        assert pt.infer_belief("agent1", None) is None

    def test_infer_belief_non_dict(self):
        """非字典观察推断"""
        tom = TheoryOfMind()
        pt = PerspectiveTaking(tom)
        belief = pt.infer_belief("agent1", "observation")
        assert belief is not None

    def test_empathize_matching(self):
        """共情匹配"""
        tom = TheoryOfMind()
        tom.model_emotion("agent1", "happy")
        pt = PerspectiveTaking(tom)
        empathy = pt.empathize("agent1", "happy")
        assert empathy == 0.9

    def test_empathize_no_emotion(self):
        """无情感时共情"""
        tom = TheoryOfMind()
        pt = PerspectiveTaking(tom)
        empathy = pt.empathize("agent1", "happy")
        assert empathy == 0.3

    def test_empathize_partial_match(self):
        """部分匹配共情"""
        tom = TheoryOfMind()
        tom.model_emotion("agent1", "very happy today")
        pt = PerspectiveTaking(tom)
        empathy = pt.empathize("agent1", "happy")
        assert empathy > 0.5

    def test_empathize_in_range(self):
        """共情在[0,1]范围"""
        tom = TheoryOfMind()
        tom.model_emotion("agent1", "happy")
        pt = PerspectiveTaking(tom)
        empathy = pt.empathize("agent1", "sad")
        assert 0.0 <= empathy <= 1.0


# ============================================================
# 3. TrustModel 测试
# ============================================================

class TestTrustModel:
    """信任模型测试"""

    def test_creation(self):
        """创建"""
        tm = TrustModel()
        assert tm is not None

    def test_creation_with_initial(self):
        """带初始信任创建"""
        tm = TrustModel(initial_trust=0.7)
        assert tm.get_trust("agent1") == 0.7

    def test_update_trust_success(self):
        """成功增加信任"""
        tm = TrustModel(initial_trust=0.5)
        new_trust = tm.update_trust("agent1", True)
        assert new_trust == 0.6

    def test_update_trust_failure(self):
        """失败减少信任"""
        tm = TrustModel(initial_trust=0.5)
        new_trust = tm.update_trust("agent1", False)
        assert new_trust == 0.3

    def test_update_trust_multiple(self):
        """多次更新信任"""
        tm = TrustModel(initial_trust=0.5)
        tm.update_trust("agent1", True)
        tm.update_trust("agent1", True)
        tm.update_trust("agent1", False)
        # 0.5 + 0.1 + 0.1 - 0.2 = 0.5
        assert abs(tm.get_trust("agent1") - 0.5) < 1e-6

    def test_trust_clamping_high(self):
        """信任上限"""
        tm = TrustModel(initial_trust=0.95)
        new_trust = tm.update_trust("agent1", True)
        assert new_trust == 1.0

    def test_trust_clamping_low(self):
        """信任下限"""
        tm = TrustModel(initial_trust=0.1)
        new_trust = tm.update_trust("agent1", False)
        assert new_trust == 0.0

    def test_get_trusted_agents(self):
        """获取可信Agent"""
        tm = TrustModel(initial_trust=0.5)
        tm.update_trust("agent1", True)
        tm.update_trust("agent1", True)
        tm.update_trust("agent1", True)
        # 0.5 + 0.3 = 0.8
        trusted = tm.get_trusted_agents(0.7)
        assert "agent1" in trusted

    def test_get_trusted_agents_empty(self):
        """无可信Agent"""
        tm = TrustModel(initial_trust=0.5)
        trusted = tm.get_trusted_agents(0.9)
        assert trusted == []

    def test_get_interaction_count(self):
        """获取交互次数"""
        tm = TrustModel()
        tm.update_trust("agent1", True)
        tm.update_trust("agent1", False)
        assert tm.get_interaction_count("agent1") == 2

    def test_get_interaction_count_zero(self):
        """无交互时次数为0"""
        tm = TrustModel()
        assert tm.get_interaction_count("agent1") == 0

    def test_reset_trust(self):
        """重置信任"""
        tm = TrustModel(initial_trust=0.5)
        tm.update_trust("agent1", True)
        tm.reset_trust("agent1")
        assert tm.get_trust("agent1") == 0.5  # 回到初始值
        assert tm.get_interaction_count("agent1") == 0

    def test_clear_all(self):
        """清除所有"""
        tm = TrustModel()
        tm.update_trust("agent1", True)
        tm.update_trust("agent2", True)
        tm.clear_all()
        assert tm.get_trust("agent1") == 0.5
        assert tm.get_interaction_count("agent1") == 0


# ============================================================
# 4. Collaboration 测试
# ============================================================

class TestCollaboration:
    """协作引擎测试"""

    def test_creation(self):
        """创建"""
        collab = Collaboration()
        assert collab is not None

    def test_create_task(self):
        """创建任务"""
        collab = Collaboration()
        task = collab.create_task("task1", "Build feature", ["coding", "design"])
        assert task.task_id == "task1"
        assert task.description == "Build feature"
        assert task.required_capabilities == ["coding", "design"]
        assert task.status == TaskStatus.PENDING

    def test_assign_task(self):
        """分配任务"""
        collab = Collaboration()
        collab.create_task("task1", "Build feature", ["coding"])
        assert collab.assign_task("task1", ["agent1"]) is True
        task = collab.get_task("task1")
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.assigned_agents == ["agent1"]

    def test_assign_task_nonexistent(self):
        """分配不存在的任务"""
        collab = Collaboration()
        assert collab.assign_task("nonexistent", ["agent1"]) is False

    def test_assign_task_already_assigned(self):
        """分配已分配的任务"""
        collab = Collaboration()
        collab.create_task("task1", "Build feature", ["coding"])
        collab.assign_task("task1", ["agent1"])
        # 再次分配应该失败
        assert collab.assign_task("task1", ["agent2"]) is False

    def test_update_progress(self):
        """更新进度"""
        collab = Collaboration()
        collab.create_task("task1", "Build feature", ["coding"])
        collab.assign_task("task1", ["agent1"])
        assert collab.update_progress("task1", 0.5) is True
        task = collab.get_task("task1")
        assert task.progress == 0.5

    def test_update_progress_nonexistent(self):
        """更新不存在任务进度"""
        collab = Collaboration()
        assert collab.update_progress("nonexistent", 0.5) is False

    def test_update_progress_not_in_progress(self):
        """更新非进行中任务进度"""
        collab = Collaboration()
        collab.create_task("task1", "Build feature", ["coding"])
        # 任务是PENDING状态
        assert collab.update_progress("task1", 0.5) is False

    def test_update_progress_clamping(self):
        """进度钳制"""
        collab = Collaboration()
        collab.create_task("task1", "Build feature", ["coding"])
        collab.assign_task("task1", ["agent1"])
        collab.update_progress("task1", 1.5)
        task = collab.get_task("task1")
        assert task.progress == 1.0

    def test_update_progress_nan_defense(self):
        """NaN进度防御"""
        collab = Collaboration()
        collab.create_task("task1", "Build feature", ["coding"])
        collab.assign_task("task1", ["agent1"])
        assert collab.update_progress("task1", float("nan")) is False

    def test_complete_task(self):
        """完成任务"""
        collab = Collaboration()
        collab.create_task("task1", "Build feature", ["coding"])
        collab.assign_task("task1", ["agent1"])
        assert collab.complete_task("task1") is True
        task = collab.get_task("task1")
        assert task.status == TaskStatus.COMPLETED
        assert task.progress == 1.0
        assert task.completed_at is not None

    def test_complete_task_nonexistent(self):
        """完成不存在任务"""
        collab = Collaboration()
        assert collab.complete_task("nonexistent") is False

    def test_complete_task_not_in_progress(self):
        """完成非进行中任务"""
        collab = Collaboration()
        collab.create_task("task1", "Build feature", ["coding"])
        # PENDING状态
        assert collab.complete_task("task1") is False

    def test_fail_task(self):
        """失败任务"""
        collab = Collaboration()
        collab.create_task("task1", "Build feature", ["coding"])
        collab.assign_task("task1", ["agent1"])
        assert collab.fail_task("task1") is True
        task = collab.get_task("task1")
        assert task.status == TaskStatus.FAILED

    def test_get_task(self):
        """获取任务"""
        collab = Collaboration()
        collab.create_task("task1", "Build feature", ["coding"])
        task = collab.get_task("task1")
        assert task is not None
        assert task.task_id == "task1"

    def test_get_task_nonexistent(self):
        """获取不存在任务"""
        collab = Collaboration()
        assert collab.get_task("nonexistent") is None

    def test_get_tasks_by_status(self):
        """按状态获取任务"""
        collab = Collaboration()
        collab.create_task("task1", "T1", ["coding"])
        collab.create_task("task2", "T2", ["coding"])
        collab.create_task("task3", "T3", ["coding"])
        collab.assign_task("task1", ["agent1"])
        collab.assign_task("task2", ["agent2"])
        collab.complete_task("task1")
        pending = collab.get_tasks_by_status(TaskStatus.PENDING)
        in_progress = collab.get_tasks_by_status(TaskStatus.IN_PROGRESS)
        completed = collab.get_tasks_by_status(TaskStatus.COMPLETED)
        assert len(pending) == 1  # task3
        assert len(in_progress) == 1  # task2
        assert len(completed) == 1  # task1

    def test_find_best_team(self):
        """寻找最佳团队"""
        collab = Collaboration()
        candidates = {
            "agent1": ["coding", "testing"],
            "agent2": ["design", "testing"],
            "agent3": ["coding", "design"],
        }
        team = collab.find_best_team(["coding", "design"], candidates)
        # 应该能找到覆盖coding和design的团队
        assert len(team) > 0
        # 验证能力覆盖
        all_caps = set()
        for agent_id in team:
            all_caps |= set(candidates[agent_id])
        assert "coding" in all_caps
        assert "design" in all_caps

    def test_find_best_team_no_match(self):
        """寻找团队无匹配"""
        collab = Collaboration()
        candidates = {
            "agent1": ["coding"],
        }
        team = collab.find_best_team(["design"], candidates)
        assert team == []

    def test_find_best_team_empty_requirements(self):
        """空需求团队"""
        collab = Collaboration()
        team = collab.find_best_team([], {"agent1": ["coding"]})
        assert team == []

    def test_get_stats(self):
        """获取统计"""
        collab = Collaboration()
        collab.create_task("task1", "T1", ["coding"])
        collab.create_task("task2", "T2", ["coding"])
        collab.assign_task("task1", ["agent1"])
        collab.complete_task("task1")
        stats = collab.get_stats()
        assert stats["total_tasks"] == 2
        assert stats["pending"] == 1
        assert stats["in_progress"] == 0
        assert stats["completed"] == 1

    def test_clear(self):
        """清除"""
        collab = Collaboration()
        collab.create_task("task1", "T1", ["coding"])
        collab.clear()
        stats = collab.get_stats()
        assert stats["total_tasks"] == 0


# ============================================================
# 5. Enhanced Engine 测试
# ============================================================

class TestEnhancedEngine:
    """增强引擎测试"""

    def test_engine_creation(self):
        """引擎创建"""
        eng = SocialFirstPrinciplesEngine("test")
        assert eng.engine_id == "test"

    def test_get_theory_of_mind(self):
        """获取理论心智引擎"""
        eng = SocialFirstPrinciplesEngine()
        tom = eng.get_theory_of_mind()
        assert isinstance(tom, TheoryOfMind)

    def test_get_perspective_taking(self):
        """获取视角采择引擎"""
        eng = SocialFirstPrinciplesEngine()
        pt = eng.get_perspective_taking()
        assert isinstance(pt, PerspectiveTaking)

    def test_get_trust_model(self):
        """获取信任模型"""
        eng = SocialFirstPrinciplesEngine()
        tm = eng.get_trust_model()
        assert isinstance(tm, TrustModel)

    def test_get_collaboration_engine(self):
        """获取协作引擎"""
        eng = SocialFirstPrinciplesEngine()
        collab = eng.get_collaboration_engine()
        assert isinstance(collab, Collaboration)

    def test_model_belief(self):
        """建模信念接口"""
        eng = SocialFirstPrinciplesEngine()
        state = eng.model_belief("agent1", "belief", 0.8)
        assert isinstance(state, MentalState)
        assert state.state_type == MentalStateType.BELIEF

    def test_model_desire(self):
        """建模欲望接口"""
        eng = SocialFirstPrinciplesEngine()
        state = eng.model_desire("agent1", "desire")
        assert isinstance(state, MentalState)
        assert state.state_type == MentalStateType.DESIRE

    def test_model_intention(self):
        """建模意图接口"""
        eng = SocialFirstPrinciplesEngine()
        state = eng.model_intention("agent1", "intention")
        assert isinstance(state, MentalState)
        assert state.state_type == MentalStateType.INTENTION

    def test_model_emotion(self):
        """建模情感接口"""
        eng = SocialFirstPrinciplesEngine()
        state = eng.model_emotion("agent1", "emotion")
        assert isinstance(state, MentalState)
        assert state.state_type == MentalStateType.EMOTION

    def test_get_mental_states(self):
        """获取心理状态接口"""
        eng = SocialFirstPrinciplesEngine()
        eng.model_belief("agent1", "belief")
        states = eng.get_mental_states("agent1")
        assert len(states) == 1

    def test_predict_action(self):
        """预测行动接口"""
        eng = SocialFirstPrinciplesEngine()
        eng.model_intention("agent1", "ask for help")
        action = eng.predict_action("agent1")
        assert action == "ask for help"

    def test_take_perspective(self):
        """视角采择接口"""
        eng = SocialFirstPrinciplesEngine()
        eng.model_belief("agent1", "belief")
        persp = eng.take_perspective("agent1", "situation")
        assert persp["agent_id"] == "agent1"

    def test_infer_belief(self):
        """推断信念接口"""
        eng = SocialFirstPrinciplesEngine()
        belief = eng.infer_belief("agent1", {"action": "running"})
        assert belief is not None

    def test_empathize(self):
        """共情接口"""
        eng = SocialFirstPrinciplesEngine()
        eng.model_emotion("agent1", "happy")
        empathy = eng.empathize("agent1", "happy")
        assert empathy == 0.9

    def test_record_interaction(self):
        """记录交互接口"""
        eng = SocialFirstPrinciplesEngine()
        eng.register_peer("agent1")
        new_trust = eng.record_interaction("agent1", True)
        assert new_trust == 0.6

    def test_record_interaction_syncs_peer(self):
        """记录交互同步到peer"""
        eng = SocialFirstPrinciplesEngine()
        peer = eng.register_peer("agent1")
        initial_trust = peer.trust_score
        eng.record_interaction("agent1", True)
        assert peer.trust_score > initial_trust

    def test_get_agent_trust(self):
        """获取Agent信任度"""
        eng = SocialFirstPrinciplesEngine()
        eng.record_interaction("agent1", True)
        assert eng.get_agent_trust("agent1") == 0.6

    def test_get_trusted_agents(self):
        """获取可信Agent"""
        eng = SocialFirstPrinciplesEngine()
        eng.record_interaction("agent1", True)
        eng.record_interaction("agent1", True)
        eng.record_interaction("agent1", True)
        trusted = eng.get_trusted_agents(0.7)
        assert "agent1" in trusted

    def test_create_collaboration_task(self):
        """创建协作任务接口"""
        eng = SocialFirstPrinciplesEngine()
        task = eng.create_collaboration_task("task1", "Build feature", ["coding"])
        assert isinstance(task, CollaborationTask)
        assert task.task_id == "task1"

    def test_assign_collaboration_task(self):
        """分配协作任务接口"""
        eng = SocialFirstPrinciplesEngine()
        eng.create_collaboration_task("task1", "Build feature", ["coding"])
        assert eng.assign_collaboration_task("task1", ["agent1"]) is True

    def test_update_task_progress(self):
        """更新任务进度接口"""
        eng = SocialFirstPrinciplesEngine()
        eng.create_collaboration_task("task1", "Build feature", ["coding"])
        eng.assign_collaboration_task("task1", ["agent1"])
        assert eng.update_task_progress("task1", 0.5) is True

    def test_complete_collaboration_task(self):
        """完成协作任务接口"""
        eng = SocialFirstPrinciplesEngine()
        eng.create_collaboration_task("task1", "Build feature", ["coding"])
        eng.assign_collaboration_task("task1", ["agent1"])
        assert eng.complete_collaboration_task("task1") is True

    def test_fail_collaboration_task(self):
        """失败协作任务接口"""
        eng = SocialFirstPrinciplesEngine()
        eng.create_collaboration_task("task1", "Build feature", ["coding"])
        eng.assign_collaboration_task("task1", ["agent1"])
        assert eng.fail_collaboration_task("task1") is True

    def test_get_collaboration_task(self):
        """获取协作任务接口"""
        eng = SocialFirstPrinciplesEngine()
        eng.create_collaboration_task("task1", "Build feature", ["coding"])
        task = eng.get_collaboration_task("task1")
        assert task is not None

    def test_find_best_team(self):
        """寻找最佳团队接口"""
        eng = SocialFirstPrinciplesEngine()
        eng.register_peer("agent1", ["coding"])
        eng.register_peer("agent2", ["design"])
        team = eng.find_best_team(["coding", "design"])
        assert len(team) > 0

    def test_stats_include_collaboration(self):
        """统计包含协作信息"""
        eng = SocialFirstPrinciplesEngine()
        eng.create_collaboration_task("task1", "T1", ["coding"])
        stats = eng.get_stats()
        assert "collaboration_stats" in stats


# ============================================================
# 6. 向后兼容性测试
# ============================================================

class TestBackwardCompat:
    """向后兼容性测试"""

    def test_message_type_enum(self):
        """消息类型枚举"""
        assert MessageType.KNOWLEDGE_SHARE.value == "knowledge_share"
        assert MessageType.TASK_COLLABORATION.value == "task_collab"
        assert MessageType.ERROR_REPORT.value == "error_report"
        assert MessageType.QUERY.value == "query"
        assert MessageType.RESPONSE.value == "response"

    def test_mental_state_type_enum(self):
        """心理状态类型枚举"""
        assert MentalStateType.BELIEF.value == "belief"
        assert MentalStateType.DESIRE.value == "desire"
        assert MentalStateType.INTENTION.value == "intention"
        assert MentalStateType.EMOTION.value == "emotion"

    def test_task_status_enum(self):
        """任务状态枚举"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"

    def test_agent_identity_dataclass(self):
        """Agent身份数据类"""
        agent = AgentIdentity(agent_id="agent1")
        assert agent.agent_id == "agent1"
        assert agent.capabilities == []
        assert agent.trust_score == 0.5
        assert agent.last_seen > 0

    def test_inter_agent_message_dataclass(self):
        """Agent间消息数据类"""
        msg = InterAgentMessage(
            message_id="msg1",
            sender_id="agent1",
            receiver_id="agent2",
            message_type=MessageType.QUERY,
            payload="hello",
        )
        assert msg.message_id == "msg1"
        assert msg.sender_id == "agent1"
        assert msg.receiver_id == "agent2"
        assert msg.message_type == MessageType.QUERY
        assert msg.payload == "hello"

    def test_mental_state_dataclass(self):
        """心理状态数据类"""
        state = MentalState(
            agent_id="agent1",
            state_type=MentalStateType.BELIEF,
            content="belief",
        )
        assert state.agent_id == "agent1"
        assert state.state_type == MentalStateType.BELIEF
        assert state.content == "belief"
        assert state.confidence == 0.5

    def test_collaboration_task_dataclass(self):
        """协作任务数据类"""
        task = CollaborationTask(
            task_id="task1",
            description="Build feature",
        )
        assert task.task_id == "task1"
        assert task.description == "Build feature"
        assert task.required_capabilities == []
        assert task.assigned_agents == []
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0.0
        assert task.completed_at is None

    def test_register_peer(self):
        """注册对等Agent（向后兼容）"""
        eng = SocialFirstPrinciplesEngine()
        peer = eng.register_peer("agent1", ["coding"])
        assert peer.agent_id == "agent1"
        assert peer.capabilities == ["coding"]

    def test_register_peer_no_capabilities(self):
        """注册无能力Agent"""
        eng = SocialFirstPrinciplesEngine()
        peer = eng.register_peer("agent1")
        assert peer.capabilities == []

    def test_update_trust(self):
        """更新信任分数（向后兼容）"""
        eng = SocialFirstPrinciplesEngine()
        eng.register_peer("agent1")
        eng.update_trust("agent1", 0.2)
        peer = eng._peers["agent1"]
        assert abs(peer.trust_score - 0.7) < 1e-6

    def test_update_trust_nonexistent(self):
        """更新不存在Agent信任"""
        eng = SocialFirstPrinciplesEngine()
        # 不应崩溃
        eng.update_trust("nonexistent", 0.2)

    def test_update_trust_clamping(self):
        """信任分数钳制"""
        eng = SocialFirstPrinciplesEngine()
        eng.register_peer("agent1")
        eng.update_trust("agent1", 1.0)  # 0.5 + 1.0 = 1.5 -> 1.0
        peer = eng._peers["agent1"]
        assert peer.trust_score == 1.0

    def test_send_message(self):
        """发送消息（向后兼容）"""
        eng = SocialFirstPrinciplesEngine()
        msg = eng.send_message("agent1", "agent2", MessageType.QUERY, "hello")
        assert msg.sender_id == "agent1"
        assert msg.receiver_id == "agent2"
        assert msg.message_type == MessageType.QUERY

    def test_broadcast(self):
        """广播消息（向后兼容）"""
        eng = SocialFirstPrinciplesEngine()
        msg = eng.broadcast("agent1", MessageType.KNOWLEDGE_SHARE, "info")
        assert msg.receiver_id == "*"

    def test_receive_messages(self):
        """接收消息（向后兼容）"""
        eng = SocialFirstPrinciplesEngine()
        eng.send_message("agent1", "agent2", MessageType.QUERY, "hello")
        messages = eng.receive_messages("agent2")
        assert len(messages) == 1
        assert messages[0].payload == "hello"

    def test_receive_messages_broadcast(self):
        """接收广播消息"""
        eng = SocialFirstPrinciplesEngine()
        eng.broadcast("agent1", MessageType.KNOWLEDGE_SHARE, "info")
        messages = eng.receive_messages("agent2")
        assert len(messages) == 1

    def test_receive_messages_empty(self):
        """接收无消息"""
        eng = SocialFirstPrinciplesEngine()
        messages = eng.receive_messages("agent1")
        assert messages == []

    def test_share_knowledge(self):
        """共享知识（向后兼容）"""
        eng = SocialFirstPrinciplesEngine()
        eng.share_knowledge("agent1", "key1", "value1")
        result = eng.query_knowledge("key1")
        assert "agent1" in result

    def test_query_knowledge_empty(self):
        """查询无知识"""
        eng = SocialFirstPrinciplesEngine()
        result = eng.query_knowledge("nonexistent")
        assert result == {}

    def test_find_collaborators(self):
        """寻找协作者（向后兼容）"""
        eng = SocialFirstPrinciplesEngine()
        eng.register_peer("agent1", ["coding"])
        eng.register_peer("agent2", ["design"])
        collaborators = eng.find_collaborators("coding")
        assert len(collaborators) == 1
        assert collaborators[0].agent_id == "agent1"

    def test_find_collaborators_no_match(self):
        """寻找协作者无匹配"""
        eng = SocialFirstPrinciplesEngine()
        eng.register_peer("agent1", ["coding"])
        collaborators = eng.find_collaborators("design")
        assert collaborators == []

    def test_get_stats(self):
        """获取统计（向后兼容）"""
        eng = SocialFirstPrinciplesEngine()
        eng.register_peer("agent1")
        eng.send_message("agent1", "agent2", MessageType.QUERY, "hello")
        stats = eng.get_stats()
        assert stats["peers_count"] == 1
        assert stats["cycle_count"] == 1

    def test_clear(self):
        """清除（向后兼容）"""
        eng = SocialFirstPrinciplesEngine()
        eng.register_peer("agent1")
        eng.send_message("agent1", "agent2", MessageType.QUERY, "hello")
        eng.share_knowledge("agent1", "key", "value")
        eng.clear()
        stats = eng.get_stats()
        assert stats["inbox_size"] == 0
        assert stats["outbox_size"] == 0
        assert stats["shared_knowledge_topics"] == 0

    def test_create_social_engine(self):
        """创建社交引擎便捷函数"""
        eng = create_social_engine("test")
        assert isinstance(eng, SocialFirstPrinciplesEngine)
        assert eng.engine_id == "test"

    def test_create_agent_identity(self):
        """创建Agent身份便捷函数"""
        agent = create_agent_identity("agent1", ["coding"])
        assert isinstance(agent, AgentIdentity)
        assert agent.agent_id == "agent1"

    def test_create_theory_of_mind(self):
        """创建理论心智引擎便捷函数"""
        tom = create_theory_of_mind()
        assert isinstance(tom, TheoryOfMind)

    def test_create_trust_model(self):
        """创建信任模型便捷函数"""
        tm = create_trust_model(0.7)
        assert isinstance(tm, TrustModel)

    def test_create_collaboration(self):
        """创建协作引擎便捷函数"""
        collab = create_collaboration()
        assert isinstance(collab, Collaboration)


# ============================================================
# 7. 并发安全测试
# ============================================================

class TestConcurrency:
    """并发安全测试"""

    def test_concurrent_register_peers(self):
        """并发注册Agent"""
        eng = SocialFirstPrinciplesEngine()
        errors = []

        def worker(idx):
            try:
                for i in range(20):
                    eng.register_peer(f"agent_{idx}_{i}", ["coding"])
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        stats = eng.get_stats()
        assert stats["peers_count"] == 100

    def test_concurrent_model_belief(self):
        """并发建模信念"""
        eng = SocialFirstPrinciplesEngine()
        errors = []

        def worker(idx):
            try:
                for i in range(20):
                    eng.model_belief(f"agent_{idx}", f"belief_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_update_trust(self):
        """并发更新信任"""
        eng = SocialFirstPrinciplesEngine()
        eng.register_peer("agent1")
        errors = []

        def worker():
            try:
                for _ in range(10):
                    eng.record_interaction("agent1", True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # 50次成功交互，信任应该接近1.0
        assert abs(eng.get_agent_trust("agent1") - 1.0) < 1e-6

    def test_concurrent_collaboration(self):
        """并发协作"""
        eng = SocialFirstPrinciplesEngine()
        errors = []

        def worker(idx):
            try:
                eng.create_collaboration_task(f"task_{idx}", "T", ["coding"])
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        stats = eng.get_stats()
        assert stats["collaboration_stats"]["total_tasks"] == 10


# ============================================================
# 8. 性能测试
# ============================================================

class TestPerformance:
    """性能测试"""

    def test_large_peer_set(self):
        """大Agent集性能"""
        eng = SocialFirstPrinciplesEngine()
        start = time.time()
        for i in range(1000):
            eng.register_peer(f"agent{i}", ["coding", "testing"])
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_many_messages(self):
        """大量消息性能"""
        eng = SocialFirstPrinciplesEngine()
        eng.register_peer("agent1")
        eng.register_peer("agent2")
        start = time.time()
        for _ in range(1000):
            eng.send_message("agent1", "agent2", MessageType.QUERY, "hello")
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_many_mental_states(self):
        """大量心理状态性能"""
        eng = SocialFirstPrinciplesEngine()
        start = time.time()
        for i in range(1000):
            eng.model_belief("agent1", f"belief_{i}")
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_many_tasks(self):
        """大量任务性能"""
        eng = SocialFirstPrinciplesEngine()
        start = time.time()
        for i in range(1000):
            eng.create_collaboration_task(f"task{i}", "T", ["coding"])
        elapsed = time.time() - start
        assert elapsed < 5.0


# ============================================================
# 9. 异常容错测试
# ============================================================

class TestErrorTolerance:
    """异常容错测试"""

    def test_empty_engine_operations(self):
        """空引擎操作"""
        eng = SocialFirstPrinciplesEngine()
        assert eng.predict_action("nonexistent") is None
        assert eng.get_mental_states("nonexistent") == []
        assert eng.get_agent_trust("nonexistent") == 0.5
        assert eng.get_collaboration_task("nonexistent") is None
        assert eng.find_best_team(["coding"]) == []

    def test_assign_nonexistent_task(self):
        """分配不存在任务"""
        eng = SocialFirstPrinciplesEngine()
        assert eng.assign_collaboration_task("nonexistent", ["agent1"]) is False

    def test_complete_nonexistent_task(self):
        """完成不存在任务"""
        eng = SocialFirstPrinciplesEngine()
        assert eng.complete_collaboration_task("nonexistent") is False

    def test_update_progress_nonexistent(self):
        """更新不存在任务进度"""
        eng = SocialFirstPrinciplesEngine()
        assert eng.update_task_progress("nonexistent", 0.5) is False

    def test_update_progress_string(self):
        """字符串进度防御"""
        eng = SocialFirstPrinciplesEngine()
        eng.create_collaboration_task("task1", "T", ["coding"])
        eng.assign_collaboration_task("task1", ["agent1"])
        assert eng.update_task_progress("task1", "not a number") is False

    def test_update_progress_inf(self):
        """Inf进度防御"""
        eng = SocialFirstPrinciplesEngine()
        eng.create_collaboration_task("task1", "T", ["coding"])
        eng.assign_collaboration_task("task1", ["agent1"])
        assert eng.update_task_progress("task1", float("inf")) is False

    def test_clear_resets_engines(self):
        """清除重置所有引擎"""
        eng = SocialFirstPrinciplesEngine()
        eng.model_belief("agent1", "belief")
        eng.record_interaction("agent1", True)
        eng.create_collaboration_task("task1", "T", ["coding"])
        eng.clear()
        # 所有引擎应该重置
        assert eng.get_mental_states("agent1") == []
        assert eng.get_agent_trust("agent1") == 0.5
        assert eng.get_collaboration_task("task1") is None

    def test_infer_belief_none(self):
        """None观察推断"""
        eng = SocialFirstPrinciplesEngine()
        assert eng.infer_belief("agent1", None) is None

    def test_empathize_no_emotion(self):
        """无情感时共情"""
        eng = SocialFirstPrinciplesEngine()
        empathy = eng.empathize("agent1", "happy")
        assert empathy == 0.3

    def test_predict_action_no_intention(self):
        """无意图时预测"""
        eng = SocialFirstPrinciplesEngine()
        assert eng.predict_action("agent1") is None


# ============================================================
# 10. 第一性原理验证测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证测试"""

    def test_theory_of_mind_models_others(self):
        """第一性原理：理论心智建模他人心理状态"""
        eng = SocialFirstPrinciplesEngine()
        eng.model_belief("agent1", "task is hard")
        eng.model_desire("agent1", "complete task")
        eng.model_intention("agent1", "ask for help")
        # 应该能获取建模的心理状态
        beliefs = eng.get_mental_states("agent1", MentalStateType.BELIEF)
        assert len(beliefs) == 1
        desires = eng.get_mental_states("agent1", MentalStateType.DESIRE)
        assert len(desires) == 1

    def test_collaboration_synergy(self):
        """第一性原理：协作产生规模效应"""
        eng = SocialFirstPrinciplesEngine()
        eng.register_peer("agent1", ["coding"])
        eng.register_peer("agent2", ["design"])
        # 单个Agent无法完成需要两种能力的任务
        team = eng.find_best_team(["coding", "design"])
        # 应该找到两个Agent的团队
        assert len(team) == 2

    def test_trust_based_on_history(self):
        """第一性原理：信任基于历史交互"""
        eng = SocialFirstPrinciplesEngine()
        # 多次成功交互
        for _ in range(5):
            eng.record_interaction("agent1", True)
        # 信任应该高
        assert abs(eng.get_agent_trust("agent1") - 1.0) < 1e-6

    def test_trust_failure_decreases(self):
        """第一性原理：失败降低信任"""
        eng = SocialFirstPrinciplesEngine()
        eng.record_interaction("agent1", False)
        assert eng.get_agent_trust("agent1") < 0.5

    def test_perspective_taking_uses_mental_state(self):
        """第一性原理：视角采择基于心理状态"""
        eng = SocialFirstPrinciplesEngine()
        eng.model_belief("agent1", "task is hard")
        eng.model_desire("agent1", "complete task")
        persp = eng.take_perspective("agent1", "situation")
        # 视角应该反映心理状态
        assert persp["interpreted_belief"] == "task is hard"
        assert persp["interpreted_desire"] == "complete task"

    def test_empathy_reflects_emotion(self):
        """第一性原理：共情反映情感"""
        eng = SocialFirstPrinciplesEngine()
        eng.model_emotion("agent1", "happy")
        # 匹配的情感共情程度高
        assert eng.empathize("agent1", "happy") == 0.9

    def test_action_prediction_from_intention(self):
        """第一性原理：行动预测基于意图"""
        eng = SocialFirstPrinciplesEngine()
        eng.model_intention("agent1", "ask for help")
        action = eng.predict_action("agent1")
        assert action == "ask for help"

    def test_collaboration_requires_capabilities(self):
        """第一性原理：协作需要能力匹配"""
        eng = SocialFirstPrinciplesEngine()
        eng.register_peer("agent1", ["coding"])
        # 需要design能力，但只有coding
        team = eng.find_best_team(["design"])
        # 应该找不到团队
        assert team == []
