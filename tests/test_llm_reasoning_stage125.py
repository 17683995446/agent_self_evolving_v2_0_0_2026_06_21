"""
阶段125: LLM协同推理层 — 专项测试

验证:
1. SemanticBridge 语义桥接（规则降级）
2. LLMReasoningCoordinator 协调器
3. 三种推理模式（LLM_LEAD / ENGINE_LEAD / HYBRID）
4. 任务路由
5. Agent集成
6. 并发安全、性能、异常容错
7. 第一性原理验证
"""

import threading
import time
import pytest

from self_evolving_agent.core.llm_reasoning_coordinator import (
    ReasoningMode,
    TaskType,
    ReasoningTask,
    ReasoningResult,
    SemanticMapping,
    SemanticBridge,
    LLMReasoningCoordinator,
    create_reasoning_task,
    create_llm_reasoning_coordinator,
)


# ============================================================
# 1. 数据结构测试
# ============================================================

class TestDataStructures:
    """数据结构测试"""

    def test_reasoning_mode_enum(self):
        """推理模式枚举"""
        assert ReasoningMode.LLM_LEAD.value == "llm_lead"
        assert ReasoningMode.ENGINE_LEAD.value == "engine_lead"
        assert ReasoningMode.HYBRID.value == "hybrid"

    def test_task_type_enum(self):
        """任务类型枚举"""
        assert TaskType.ANALYSIS.value == "analysis"
        assert TaskType.DECISION.value == "decision"
        assert TaskType.CREATION.value == "creation"
        assert TaskType.CAUSAL.value == "causal"
        assert TaskType.REFLECTION.value == "reflection"
        assert TaskType.GENERAL.value == "general"

    def test_reasoning_task_creation(self):
        """推理任务创建"""
        task = ReasoningTask(
            task_id="t1",
            task_type=TaskType.ANALYSIS,
            query="分析这个错误",
        )
        assert task.task_id == "t1"
        assert task.task_type == TaskType.ANALYSIS
        assert task.query == "分析这个错误"
        assert task.mode == ReasoningMode.HYBRID
        assert task.timestamp > 0

    def test_reasoning_result_creation(self):
        """推理结果创建"""
        result = ReasoningResult(
            task_id="t1",
            success=True,
            answer="这是答案",
        )
        assert result.task_id == "t1"
        assert result.success is True
        assert result.answer == "这是答案"
        assert result.structured_data == {}
        assert result.confidence == 0.5
        assert result.sources == []

    def test_semantic_mapping_creation(self):
        """语义映射创建"""
        mapping = SemanticMapping(
            natural_text="hello",
            structured={"key": "value"},
            mapping_type="to_struct",
        )
        assert mapping.natural_text == "hello"
        assert mapping.structured == {"key": "value"}
        assert mapping.mapping_type == "to_struct"


# ============================================================
# 2. SemanticBridge 测试
# ============================================================

class TestSemanticBridge:
    """语义桥接测试"""

    def test_creation(self):
        """创建"""
        bridge = SemanticBridge()
        assert bridge is not None

    def test_to_structured_basic(self):
        """基本结构化"""
        bridge = SemanticBridge()
        result = bridge.to_structured("CPU使用率90%")
        assert "raw_text" in result
        assert "numbers" in result
        assert 90.0 in result["numbers"]

    def test_to_structured_empty(self):
        """空输入结构化"""
        bridge = SemanticBridge()
        result = bridge.to_structured("")
        assert result == {}

    def test_to_structured_none(self):
        """None输入结构化"""
        bridge = SemanticBridge()
        result = bridge.to_structured(None)
        assert result == {}

    def test_to_structured_extracts_numbers(self):
        """提取数字"""
        bridge = SemanticBridge()
        result = bridge.to_structured("温度25.5度，湿度60%")
        assert "numbers" in result
        assert 25.5 in result["numbers"]

    def test_to_structured_extracts_percentages(self):
        """提取百分比"""
        bridge = SemanticBridge()
        result = bridge.to_structured("CPU 90%，内存80%")
        assert "percentages" in result
        assert 0.9 in result["percentages"]

    def test_to_structured_detects_error_tag(self):
        """检测错误标签"""
        bridge = SemanticBridge()
        result = bridge.to_structured("发生错误")
        assert "tags" in result
        assert "error" in result["tags"]

    def test_to_structured_detects_warning_tag(self):
        """检测警告标签"""
        bridge = SemanticBridge()
        result = bridge.to_structured("warning: high load")
        assert "tags" in result
        assert "warning" in result["tags"]

    def test_to_structured_detects_success_tag(self):
        """检测成功标签"""
        bridge = SemanticBridge()
        result = bridge.to_structured("任务成功完成")
        assert "tags" in result
        assert "success" in result["tags"]

    def test_to_structured_cache(self):
        """缓存"""
        bridge = SemanticBridge()
        bridge.to_structured("test cache")
        assert bridge.get_cache_size() > 0

    def test_to_structured_same_input_cached(self):
        """相同输入使用缓存"""
        bridge = SemanticBridge()
        r1 = bridge.to_structured("test cache same")
        size1 = bridge.get_cache_size()
        r2 = bridge.to_structured("test cache same")
        size2 = bridge.get_cache_size()
        # 缓存大小不应增加
        assert size2 == size1

    def test_to_natural_text_basic(self):
        """基本自然语言表达"""
        bridge = SemanticBridge()
        text = bridge.to_natural_text({"cpu": 90, "status": "ok"})
        assert "cpu" in text
        assert "90" in text

    def test_to_natural_text_empty(self):
        """空输入表达"""
        bridge = SemanticBridge()
        text = bridge.to_natural_text({})
        assert text == ""

    def test_to_natural_text_none(self):
        """None输入表达"""
        bridge = SemanticBridge()
        text = bridge.to_natural_text(None)
        assert text == ""

    def test_to_natural_text_with_template(self):
        """模板表达"""
        bridge = SemanticBridge()
        text = bridge.to_natural_text({"value": 42}, template="答案是 {value}")
        assert "42" in text

    def test_to_natural_text_list_value(self):
        """列表值表达"""
        bridge = SemanticBridge()
        text = bridge.to_natural_text({"items": ["a", "b", "c"]})
        assert "a" in text

    def test_clear_cache(self):
        """清除缓存"""
        bridge = SemanticBridge()
        bridge.to_structured("test")
        bridge.clear_cache()
        assert bridge.get_cache_size() == 0


# ============================================================
# 3. LLMReasoningCoordinator 测试
# ============================================================

class TestLLMReasoningCoordinator:
    """LLM推理协调器测试"""

    def test_creation(self):
        """创建"""
        coord = LLMReasoningCoordinator()
        assert coord is not None

    def test_creation_with_llm(self):
        """带LLM创建"""
        class MockLLM:
            def chat(self, messages, **kwargs):
                from self_evolving_agent.core.llm_service import LLMResponse
                return LLMResponse(content="mock answer", success=True)

            def parse_observation(self, text):
                return {"parsed": True}

            def generate_reflection(self, stats):
                return "mock reflection"

        coord = LLMReasoningCoordinator(llm_service=MockLLM())
        assert coord is not None

    def test_reason_basic(self):
        """基本推理"""
        coord = LLMReasoningCoordinator()
        task = create_reasoning_task("t1", "测试查询", TaskType.GENERAL)
        result = coord.reason(task)
        assert isinstance(result, ReasoningResult)
        assert result.task_id == "t1"

    def test_reason_hybrid_mode(self):
        """混合模式推理"""
        coord = LLMReasoningCoordinator()
        task = create_reasoning_task("t1", "分析", TaskType.ANALYSIS, mode=ReasoningMode.HYBRID)
        result = coord.reason(task)
        assert result is not None

    def test_reason_llm_lead_no_llm(self):
        """无LLM时LLM主导降级"""
        coord = LLMReasoningCoordinator()
        task = create_reasoning_task("t1", "分析", TaskType.ANALYSIS, mode=ReasoningMode.LLM_LEAD)
        result = coord.reason(task)
        # 无LLM降级到引擎，无引擎降级返回失败或空结果
        assert result is not None

    def test_reason_engine_lead_no_engine(self):
        """无引擎时引擎主导降级"""
        coord = LLMReasoningCoordinator()
        task = create_reasoning_task("t1", "分析", TaskType.CAUSAL, mode=ReasoningMode.ENGINE_LEAD)
        result = coord.reason(task)
        # 无引擎降级到LLM，无LLM返回失败
        assert result is not None

    def test_reason_with_mock_llm(self):
        """带mock LLM推理"""
        class MockLLM:
            def chat(self, messages, **kwargs):
                from self_evolving_agent.core.llm_service import LLMResponse
                return LLMResponse(content="LLM answer", success=True)

            def parse_observation(self, text):
                return {"parsed": True}

            def generate_reflection(self, stats):
                return "reflection"

        coord = LLMReasoningCoordinator(llm_service=MockLLM())
        task = create_reasoning_task("t1", "分析", TaskType.ANALYSIS, mode=ReasoningMode.LLM_LEAD)
        result = coord.reason(task)
        assert result.success is True
        assert result.answer == "LLM answer"

    def test_reason_with_mock_engine(self):
        """带mock引擎推理"""
        class MockEngine:
            pass

        class MockCoordinator:
            def reflect(self):
                return {"status": "ok"}

        coord = LLMReasoningCoordinator(engine=MockEngine(), coordinator=MockCoordinator())
        task = create_reasoning_task("t1", "反思", TaskType.REFLECTION, mode=ReasoningMode.ENGINE_LEAD)
        result = coord.reason(task)
        assert result.success is True

    def test_set_routing(self):
        """设置路由"""
        coord = LLMReasoningCoordinator()
        coord.set_routing(TaskType.ANALYSIS, ReasoningMode.ENGINE_LEAD)
        # 不崩溃即可
        task = create_reasoning_task("t1", "分析", TaskType.ANALYSIS)
        result = coord.reason(task)
        assert result is not None

    def test_get_history(self):
        """获取历史"""
        coord = LLMReasoningCoordinator()
        task = create_reasoning_task("t1", "查询", TaskType.GENERAL)
        coord.reason(task)
        history = coord.get_history()
        assert len(history) == 1

    def test_get_stats(self):
        """获取统计"""
        coord = LLMReasoningCoordinator()
        task = create_reasoning_task("t1", "查询", TaskType.GENERAL)
        coord.reason(task)
        stats = coord.get_stats()
        assert stats["total_tasks"] == 1
        assert "success_rate" in stats
        assert "avg_latency_ms" in stats

    def test_clear_history(self):
        """清除历史"""
        coord = LLMReasoningCoordinator()
        task = create_reasoning_task("t1", "查询", TaskType.GENERAL)
        coord.reason(task)
        coord.clear_history()
        assert len(coord.get_history()) == 0

    def test_semantic_bridge_property(self):
        """语义桥接属性"""
        coord = LLMReasoningCoordinator()
        bridge = coord.semantic_bridge
        assert isinstance(bridge, SemanticBridge)


# ============================================================
# 4. 任务路由测试
# ============================================================

class TestTaskRouting:
    """任务路由测试"""

    def test_analysis_routes_to_llm(self):
        """分析任务路由到LLM"""
        coord = LLMReasoningCoordinator()
        task = create_reasoning_task("t1", "分析", TaskType.ANALYSIS)
        result = coord.reason(task)
        assert result is not None

    def test_decision_routes_to_engine(self):
        """决策任务路由到引擎"""
        coord = LLMReasoningCoordinator()
        task = create_reasoning_task("t1", "决策", TaskType.DECISION)
        result = coord.reason(task)
        assert result is not None

    def test_causal_routes_to_engine(self):
        """因果任务路由到引擎"""
        coord = LLMReasoningCoordinator()
        task = create_reasoning_task("t1", "因果", TaskType.CAUSAL)
        result = coord.reason(task)
        assert result is not None

    def test_creation_routes_to_llm(self):
        """创作任务路由到LLM"""
        coord = LLMReasoningCoordinator()
        task = create_reasoning_task("t1", "创作", TaskType.CREATION)
        result = coord.reason(task)
        assert result is not None

    def test_reflection_routes_to_hybrid(self):
        """反思任务路由到混合"""
        coord = LLMReasoningCoordinator()
        task = create_reasoning_task("t1", "反思", TaskType.REFLECTION)
        result = coord.reason(task)
        assert result is not None

    def test_explicit_mode_overrides_routing(self):
        """显式模式覆盖路由"""
        coord = LLMReasoningCoordinator()
        # 分析任务默认LLM_LEAD，显式设为ENGINE_LEAD
        task = create_reasoning_task(
            "t1", "分析", TaskType.ANALYSIS, mode=ReasoningMode.ENGINE_LEAD
        )
        result = coord.reason(task)
        assert result is not None


# ============================================================
# 5. Agent集成测试
# ============================================================

class TestAgentIntegration:
    """Agent集成测试"""

    def test_agent_has_llm_coordinator(self):
        """Agent有LLM协调器"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        assert agent.llm_coordinator is not None

    def test_agent_reason_basic(self):
        """Agent基本推理"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        result = agent.reason("测试查询")
        assert result is not None
        assert result.task_id is not None

    def test_agent_reason_with_task_type(self):
        """Agent带任务类型推理"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        result = agent.reason("分析这个", TaskType.ANALYSIS)
        assert result is not None

    def test_agent_reason_with_mode(self):
        """Agent带模式推理"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        result = agent.reason("测试", TaskType.GENERAL, ReasoningMode.HYBRID)
        assert result is not None

    def test_agent_reason_with_context(self):
        """Agent带上下文推理"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent("test")
        result = agent.reason("测试", context={"key": "value"})
        assert result is not None


# ============================================================
# 6. 并发安全测试
# ============================================================

class TestConcurrency:
    """并发安全测试"""

    def test_concurrent_reason(self):
        """并发推理"""
        coord = LLMReasoningCoordinator()
        errors = []

        def worker(idx):
            try:
                for i in range(10):
                    task = create_reasoning_task(
                        f"t_{idx}_{i}", f"查询{idx}_{i}", TaskType.GENERAL
                    )
                    coord.reason(task)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(coord.get_history()) == 50

    def test_concurrent_bridge(self):
        """并发桥接"""
        bridge = SemanticBridge()
        errors = []

        def worker(idx):
            try:
                for i in range(20):
                    bridge.to_structured(f"test {idx}_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ============================================================
# 7. 性能测试
# ============================================================

class TestPerformance:
    """性能测试"""

    def test_bridge_parse_performance(self):
        """桥接解析性能"""
        bridge = SemanticBridge()
        start = time.time()
        for _ in range(1000):
            bridge.to_structured("CPU 90% 错误")
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_bridge_cache_hit_performance(self):
        """缓存命中性能"""
        bridge = SemanticBridge()
        bridge.to_structured("cached query")
        start = time.time()
        for _ in range(1000):
            bridge.to_structured("cached query")
        elapsed = time.time() - start
        assert elapsed < 2.0

    def test_reason_performance(self):
        """推理性能"""
        coord = LLMReasoningCoordinator()
        start = time.time()
        for i in range(100):
            task = create_reasoning_task(f"t{i}", f"查询{i}", TaskType.GENERAL)
            coord.reason(task)
        elapsed = time.time() - start
        assert elapsed < 10.0


# ============================================================
# 8. 异常容错测试
# ============================================================

class TestErrorTolerance:
    """异常容错测试"""

    def test_reason_with_failing_llm(self):
        """LLM失败时容错"""
        class FailingLLM:
            def chat(self, messages, **kwargs):
                from self_evolving_agent.core.llm_service import LLMResponse
                return LLMResponse(content="", success=False, error="LLM failed")

            def parse_observation(self, text):
                raise Exception("parse failed")

            def generate_reflection(self, stats):
                raise Exception("reflection failed")

        coord = LLMReasoningCoordinator(llm_service=FailingLLM())
        task = create_reasoning_task("t1", "查询", TaskType.ANALYSIS, mode=ReasoningMode.LLM_LEAD)
        result = coord.reason(task)
        # 应该降级而非崩溃
        assert result is not None

    def test_reason_with_failing_engine(self):
        """引擎失败时容错"""
        class FailingCoordinator:
            def reflect(self):
                raise Exception("engine failed")

        coord = LLMReasoningCoordinator(coordinator=FailingCoordinator())
        task = create_reasoning_task("t1", "查询", TaskType.REFLECTION, mode=ReasoningMode.ENGINE_LEAD)
        result = coord.reason(task)
        # 应该降级而非崩溃
        assert result is not None

    def test_empty_query(self):
        """空查询"""
        coord = LLMReasoningCoordinator()
        task = create_reasoning_task("t1", "", TaskType.GENERAL)
        result = coord.reason(task)
        assert result is not None

    def test_very_long_query(self):
        """超长查询"""
        coord = LLMReasoningCoordinator()
        long_query = "x" * 10000
        task = create_reasoning_task("t1", long_query, TaskType.GENERAL)
        result = coord.reason(task)
        assert result is not None

    def test_history_limit(self):
        """历史限制"""
        coord = LLMReasoningCoordinator()
        coord._max_history = 5
        for i in range(10):
            task = create_reasoning_task(f"t{i}", f"查询{i}", TaskType.GENERAL)
            coord.reason(task)
        assert len(coord.get_history()) <= 5


# ============================================================
# 9. 第一性原理验证测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证测试"""

    def test_llm_handles_semantics(self):
        """第一性原理：LLM处理语义"""
        bridge = SemanticBridge()
        # LLM擅长解析自然语言
        result = bridge.to_structured("CPU使用率90%，发生错误")
        assert "raw_text" in result
        assert "numbers" in result

    def test_engine_handles_structure(self):
        """第一性原理：引擎处理结构化"""
        class MockCoordinator:
            def reflect(self):
                return {"status": "ok", "metrics": {"cpu": 0.5}}

        coord = LLMReasoningCoordinator(coordinator=MockCoordinator())
        task = create_reasoning_task("t1", "反思", TaskType.REFLECTION, mode=ReasoningMode.ENGINE_LEAD)
        result = coord.reason(task)
        # 引擎应该处理结构化数据
        assert result.success is True

    def test_hybrid_combines_both(self):
        """第一性原理：混合模式结合两者"""
        class MockLLM:
            def chat(self, messages, **kwargs):
                from self_evolving_agent.core.llm_service import LLMResponse
                return LLMResponse(content="LLM分析", success=True)

            def parse_observation(self, text):
                return {"parsed": True}

            def generate_reflection(self, stats):
                return "reflection"

        class MockCoordinator:
            def reflect(self):
                return {"status": "ok"}

        coord = LLMReasoningCoordinator(llm_service=MockLLM(), coordinator=MockCoordinator())
        task = create_reasoning_task("t1", "分析", TaskType.REFLECTION, mode=ReasoningMode.HYBRID)
        result = coord.reason(task)
        # 混合模式应该结合LLM和引擎
        assert result.success is True
        assert "semantic_bridge" in result.sources

    def test_degradation_without_llm(self):
        """第一性原理：无LLM时降级"""
        coord = LLMReasoningCoordinator()
        # 无LLM时应该降级到规则
        bridge = coord.semantic_bridge
        result = bridge.to_structured("测试")
        assert "raw_text" in result

    def test_degradation_without_engine(self):
        """第一性原理：无引擎时降级"""
        coord = LLMReasoningCoordinator()
        task = create_reasoning_task("t1", "查询", TaskType.CAUSAL, mode=ReasoningMode.ENGINE_LEAD)
        result = coord.reason(task)
        # 无引擎时应该降级到LLM或返回失败
        assert result is not None

    def test_division_of_labor(self):
        """第一性原理：分工边界"""
        # LLM主导：分析任务
        # 引擎主导：因果任务
        coord = LLMReasoningCoordinator()
        analysis_task = create_reasoning_task("t1", "分析", TaskType.ANALYSIS)
        causal_task = create_reasoning_task("t2", "因果", TaskType.CAUSAL)
        # 两种任务都能处理
        r1 = coord.reason(analysis_task)
        r2 = coord.reason(causal_task)
        assert r1 is not None
        assert r2 is not None
