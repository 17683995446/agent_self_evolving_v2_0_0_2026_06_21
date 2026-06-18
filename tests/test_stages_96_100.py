"""
阶段100: pytest 测试框架

验证自驱永续进化Agent系统的核心功能。
运行方式：pytest tests/ -v
"""

import pytest
from self_evolving_agent import (
    SelfEvolvingAgent,
    create_default_agent,
    SystemCoordinator,
    create_coordinator,
    UnifiedFirstPrinciplesEngine,
    create_unified_engine,
    LLMService,
    RAGService,
)
from self_evolving_agent.core.engine_coordinators import (
    PerceptionCoordinator,
    MotivationCoordinator,
    DecisionCoordinator,
    ExplorationCoordinator,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def agent():
    """默认 Agent（无 LLM）"""
    return create_default_agent()


@pytest.fixture
def coordinator():
    """系统协调器"""
    return create_coordinator("test_coordinator")


@pytest.fixture
def engine():
    """统一引擎"""
    return create_unified_engine("test_engine")


# ============================================================
# 阶段96: 统一架构测试
# ============================================================

class TestUnifiedArchitecture:
    """阶段96: 验证 SelfEvolvingAgent 作为 SystemCoordinator 薄包装层"""

    def test_agent_has_coordinator(self, agent):
        """Agent 持有 SystemCoordinator"""
        assert isinstance(agent.coordinator, SystemCoordinator)

    def test_agent_has_engine(self, agent):
        """Agent 通过 coordinator 访问统一引擎"""
        assert isinstance(agent.engine, UnifiedFirstPrinciplesEngine)

    def test_agent_observe(self, agent):
        """observe 委托给 coordinator"""
        result = agent.observe({
            "module_id": "test",
            "predicted": {"value": 0.5},
            "actual": {"value": 0.6},
        })
        assert "prediction" in result
        assert "error" in result

    def test_agent_act(self, agent):
        """act 委托给 coordinator"""
        result = agent.act("explore", context={})
        assert "action_taken" in result
        assert "decision" in result

    def test_agent_reflect(self, agent):
        """reflect 委托给 coordinator"""
        result = agent.reflect()
        assert "cycle_count" in result
        assert "goals" in result

    def test_agent_get_state(self, agent):
        """get_state 返回统一状态"""
        state = agent.get_state()
        assert state["agent_id"] == "self_evolving_agent"
        assert "coordinator" in state
        assert "modules" in state


# ============================================================
# 阶段97: God Engine 拆分测试
# ============================================================

class TestEngineCoordinators:
    """阶段97: 验证 4 个职责内聚的协调器"""

    def test_four_coordinators(self, engine):
        """引擎持有 4 个协调器"""
        assert isinstance(engine.perception_coordinator, PerceptionCoordinator)
        assert isinstance(engine.motivation_coordinator, MotivationCoordinator)
        assert isinstance(engine.decision_coordinator, DecisionCoordinator)
        assert isinstance(engine.exploration_coordinator, ExplorationCoordinator)

    def test_backward_compat_sub_engines(self, engine):
        """向后兼容：15 个子引擎属性可访问"""
        sub_engines = [
            "predictive_coding", "learning", "memory",
            "drive", "emotion", "evolution",
            "metacognition", "consciousness", "free_will", "safety", "efficiency",
            "exploration", "creativity", "social", "causal",
        ]
        for name in sub_engines:
            assert getattr(engine, name) is not None, f"missing sub-engine: {name}"

    def test_perceive_and_predict(self, engine):
        """感知与预测"""
        result = engine.perceive_and_predict("test", {"value": 0.5}, {"value": 0.6})
        assert "prediction" in result
        assert "error" in result

    def test_evaluate_drives(self, engine):
        """评估驱力"""
        gaps = engine.evaluate_drives()
        assert isinstance(gaps, list)

    def test_make_decision(self, engine):
        """做出整合决策"""
        from self_evolving_agent.core.free_will_first_principles import ChoiceSet
        choices = ChoiceSet(choice_id="test", options=["a", "b", "c"], context={})
        result = engine.make_consolidated_decision(choices)
        assert "decision" in result

    def test_run_integration_cycle(self, engine):
        """运行整合周期"""
        result = engine.run_integration_cycle({"outcome": {"information_value": 0.7}})
        assert "cycle" in result
        assert "gaps" in result

    def test_get_full_stats(self, engine):
        """获取完整统计"""
        stats = engine.get_full_stats()
        assert "engine_id" in stats
        assert "predictive_coding" in stats
        assert "drive" in stats
        assert "consciousness" in stats


# ============================================================
# 阶段98: 分层架构测试
# ============================================================

class TestLayeredArchitecture:
    """阶段98: 验证 core/ 分层子包"""

    def test_engines_subpackage(self):
        """engines 子包可导入"""
        from self_evolving_agent.core.engines import (
            UnifiedFirstPrinciplesEngine,
            SystemCoordinator,
            LLMService,
            RAGService,
            PerceptionCoordinator,
        )
        assert UnifiedFirstPrinciplesEngine is not None
        assert SystemCoordinator is not None

    def test_infra_subpackage(self):
        """infra 子包可导入"""
        from self_evolving_agent.core.infra import (
            LocalMessageBus,
            ConfigurationManager,
            BaseModule,
            AgentMessage,
        )
        assert LocalMessageBus is not None
        assert ConfigurationManager is not None

    def test_devops_subpackage(self):
        """devops 子包可导入"""
        from self_evolving_agent.core.devops import CircuitBreaker, RateLimiter
        assert CircuitBreaker is not None
        assert RateLimiter is not None

    def test_mlops_subpackage(self):
        """mlops 子包可导入"""
        from self_evolving_agent.core.mlops import ModelManager, ABTestEngine
        assert ModelManager is not None
        assert ABTestEngine is not None

    def test_data_subpackage(self):
        """data 子包可导入"""
        from self_evolving_agent.core.data import DataPipeline
        assert DataPipeline is not None

    def test_backward_compat_flat_imports(self):
        """向后兼容：扁平导入仍然有效"""
        from self_evolving_agent.core.system_coordinator import SystemCoordinator
        from self_evolving_agent.core.unified_first_principles_engine import UnifiedFirstPrinciplesEngine
        assert SystemCoordinator is not None
        assert UnifiedFirstPrinciplesEngine is not None


# ============================================================
# 阶段99: 门面模式测试
# ============================================================

class TestFacadePattern:
    """阶段99: 验证 SystemCoordinator 门面方法"""

    def test_set_goal(self, coordinator):
        """设置目标（声明式）"""
        coordinator.set_goal("safe", 0.95)
        coordinator.set_goal("gain", 0.8)
        coordinator.set_goal("eff", 0.85)

    def test_observe(self, coordinator):
        """观察环境状态"""
        result = coordinator.observe({
            "module_id": "test",
            "predicted": {"value": 0.5},
            "actual": {"value": 0.6},
        })
        assert "prediction" in result

    def test_act_with_resources(self, coordinator):
        """执行行动（含资源记录）"""
        result = coordinator.act("explore", context={
            "resources_used": {"cpu": 0.3},
            "output_value": 0.5,
        })
        assert "action_taken" in result

    def test_reflect(self, coordinator):
        """反思（通过门面方法访问子引擎）"""
        result = coordinator.reflect()
        assert "recommended_action" in result
        assert "dominant_emotion" in result
        assert "consciousness_contents" in result
        assert isinstance(result["consciousness_contents"], list)

    def test_get_status(self, coordinator):
        """获取系统状态"""
        status = coordinator.get_status()
        assert status["coordinator_id"] == "test_coordinator"
        assert "engine_status" in status


# ============================================================
# 端到端集成测试
# ============================================================

class TestEndToEnd:
    """端到端集成测试"""

    def test_full_cycle(self, agent):
        """完整周期：observe -> act -> reflect"""
        # 1. 设置目标
        agent.set_goal("safe", 0.95)
        agent.set_goal("gain", 0.8)

        # 2. 观察环境
        obs = agent.observe({
            "module_id": "env",
            "predicted": {"value": 0.5},
            "actual": {"value": 0.55},
        })
        assert "prediction" in obs

        # 3. 执行行动
        act_result = agent.act("explore", context={
            "resources_used": {"cpu": 0.2, "memory": 0.1},
            "output_value": 0.6,
        })
        assert "action_taken" in act_result

        # 4. 反思
        reflection = agent.reflect()
        assert reflection["cycle_count"] >= 1

        # 5. 运行完整周期
        cycle = agent.run_cycle({"outcome": {"information_value": 0.8}})
        assert "cycle" in cycle

    def test_multiple_cycles(self, agent):
        """多周期运行稳定性"""
        for i in range(5):
            agent.observe({
                "module_id": f"module_{i}",
                "predicted": {"value": 0.5 + i * 0.01},
                "actual": {"value": 0.5 + i * 0.01 + 0.02},
            })
        state = agent.get_state()
        assert state["cycle_count"] >= 5
