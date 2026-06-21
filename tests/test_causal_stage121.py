"""
阶段121: 因果推理强化 — 专项测试

验证新增能力:
1. CausalGraph: 因果图（DAG，环检测，路径，拓扑排序）
2. CounterfactualReasoning: 反事实推理（结构因果模型）
3. DoCalculus: do-算子（Pearl框架，切断入边）
4. CausalFirstPrinciplesEngine: 新增接口
5. 向后兼容性

第一性原理验证:
- 因果图是有向无环图（DAG）
- 相关不等于因果
- do(X=x) ≠ 观察X=x
- 反事实 = Y(a) - Y(a')
- 干预切断入边
"""

import math
import threading
import time
import pytest

from self_evolving_agent.core.causal_first_principles import (
    CausalStrength,
    CausalLink,
    Intervention,
    CausalGraph,
    CounterfactualResult,
    CounterfactualReasoning,
    DoCalculus,
    CausalFirstPrinciplesEngine,
    create_causal_engine,
    create_intervention,
    create_causal_graph,
)


# ============================================================
# 1. CausalGraph 测试
# ============================================================

class TestCausalGraph:
    """因果图测试"""

    def test_add_node(self):
        """添加节点"""
        g = CausalGraph()
        g.add_node("A")
        assert "A" in g.get_nodes()

    def test_add_edge_basic(self):
        """添加基本边"""
        g = CausalGraph()
        assert g.add_edge("A", "B", CausalStrength.STRONG, 0.9) is True
        assert "A" in g.get_nodes()
        assert "B" in g.get_nodes()

    def test_add_edge_auto_adds_nodes(self):
        """添加边自动添加节点"""
        g = CausalGraph()
        g.add_edge("X", "Y")
        nodes = g.get_nodes()
        assert "X" in nodes
        assert "Y" in nodes

    def test_cycle_detection_direct(self):
        """直接环检测：A→B→A"""
        g = CausalGraph()
        assert g.add_edge("A", "B") is True
        # B→A 会形成环
        assert g.add_edge("B", "A") is False

    def test_cycle_detection_indirect(self):
        """间接环检测：A→B→C→A"""
        g = CausalGraph()
        assert g.add_edge("A", "B") is True
        assert g.add_edge("B", "C") is True
        # C→A 会形成环
        assert g.add_edge("C", "A") is False

    def test_cycle_detection_long_chain(self):
        """长链环检测：A→B→C→D→E→A"""
        g = CausalGraph()
        for i in range(4):
            assert g.add_edge(f"N{i}", f"N{i+1}") is True
        # N4→N0 会形成环
        assert g.add_edge("N4", "N0") is False

    def test_self_loop_rejected(self):
        """自环被拒绝"""
        g = CausalGraph()
        assert g.add_edge("A", "A") is False

    def test_no_cycle_allows_parallel_paths(self):
        """无环允许平行路径"""
        g = CausalGraph()
        # A→B, A→C, B→D, C→D 是合法的DAG
        assert g.add_edge("A", "B") is True
        assert g.add_edge("A", "C") is True
        assert g.add_edge("B", "D") is True
        assert g.add_edge("C", "D") is True
        assert g.is_dag() is True

    def test_get_parents(self):
        """获取父节点"""
        g = CausalGraph()
        g.add_edge("A", "C")
        g.add_edge("B", "C")
        parents = g.get_parents("C")
        assert parents == {"A", "B"}

    def test_get_parents_no_parents(self):
        """无父节点"""
        g = CausalGraph()
        g.add_edge("A", "B")
        assert g.get_parents("A") == set()

    def test_get_children(self):
        """获取子节点"""
        g = CausalGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        children = g.get_children("A")
        assert children == {"B", "C"}

    def test_get_children_no_children(self):
        """无子节点"""
        g = CausalGraph()
        g.add_edge("A", "B")
        assert g.get_children("B") == set()

    def test_get_ancestors(self):
        """获取祖先节点"""
        g = CausalGraph()
        # A→B→C, A→D→C
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("A", "D")
        g.add_edge("D", "C")
        ancestors = g.get_ancestors("C")
        assert ancestors == {"A", "B", "D"}

    def test_get_ancestors_root(self):
        """根节点无祖先"""
        g = CausalGraph()
        g.add_edge("A", "B")
        assert g.get_ancestors("A") == set()

    def test_get_descendants(self):
        """获取后代节点"""
        g = CausalGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("A", "D")
        descendants = g.get_descendants("A")
        assert descendants == {"B", "C", "D"}

    def test_get_descendants_leaf(self):
        """叶子节点无后代"""
        g = CausalGraph()
        g.add_edge("A", "B")
        assert g.get_descendants("B") == set()

    def test_get_all_paths_direct(self):
        """直接路径"""
        g = CausalGraph()
        g.add_edge("A", "B")
        paths = g.get_all_paths("A", "B")
        assert paths == [["A", "B"]]

    def test_get_all_paths_indirect(self):
        """间接路径"""
        g = CausalGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        paths = g.get_all_paths("A", "C")
        assert paths == [["A", "B", "C"]]

    def test_get_all_paths_multiple(self):
        """多条路径"""
        g = CausalGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        g.add_edge("C", "D")
        paths = g.get_all_paths("A", "D")
        # 两条路径
        assert len(paths) == 2
        assert ["A", "B", "D"] in paths
        assert ["A", "C", "D"] in paths

    def test_get_all_paths_no_path(self):
        """无路径"""
        g = CausalGraph()
        g.add_edge("A", "B")
        g.add_edge("C", "D")
        paths = g.get_all_paths("A", "D")
        assert paths == []

    def test_get_all_paths_same_node(self):
        """同节点路径"""
        g = CausalGraph()
        g.add_edge("A", "B")
        paths = g.get_all_paths("A", "A")
        assert paths == [["A"]]

    def test_get_direct_effect(self):
        """获取直接效应"""
        g = CausalGraph()
        g.add_edge("A", "B", CausalStrength.STRONG, 0.9)
        link = g.get_direct_effect("A", "B")
        assert link is not None
        assert link.strength == CausalStrength.STRONG
        assert abs(link.confidence - 0.9) < 1e-6

    def test_get_direct_effect_nonexistent(self):
        """获取不存在的直接效应"""
        g = CausalGraph()
        g.add_edge("A", "B")
        assert g.get_direct_effect("A", "C") is None

    def test_get_indirect_effects(self):
        """获取间接效应路径"""
        g = CausalGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        # A→C 只有间接路径 A→B→C
        indirect = g.get_indirect_effects("A", "C")
        assert len(indirect) == 1
        assert indirect[0] == ["A", "B", "C"]

    def test_get_indirect_effects_only_direct(self):
        """只有直接效应时无间接"""
        g = CausalGraph()
        g.add_edge("A", "B")
        indirect = g.get_indirect_effects("A", "B")
        assert indirect == []

    def test_get_edges(self):
        """获取所有边"""
        g = CausalGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        edges = g.get_edges()
        assert ("A", "B") in edges
        assert ("B", "C") in edges
        assert len(edges) == 2

    def test_is_dag_always_true(self):
        """始终是DAG（添加时已检查环）"""
        g = CausalGraph()
        g.add_edge("A", "B")
        assert g.is_dag() is True

    def test_topological_sort_simple(self):
        """拓扑排序简单"""
        g = CausalGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        ts = g.topological_sort()
        assert ts.index("A") < ts.index("B")
        assert ts.index("B") < ts.index("C")

    def test_topological_sort_diamond(self):
        """拓扑排序菱形"""
        g = CausalGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        g.add_edge("C", "D")
        ts = g.topological_sort()
        assert ts.index("A") < ts.index("B")
        assert ts.index("A") < ts.index("C")
        assert ts.index("B") < ts.index("D")
        assert ts.index("C") < ts.index("D")

    def test_topological_sort_empty(self):
        """空图拓扑排序"""
        g = CausalGraph()
        assert g.topological_sort() == []

    def test_topological_sort_single_node(self):
        """单节点拓扑排序"""
        g = CausalGraph()
        g.add_node("A")
        ts = g.topological_sort()
        assert ts == ["A"]

    def test_get_stats(self):
        """获取统计"""
        g = CausalGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        stats = g.get_stats()
        assert stats["node_count"] == 3
        assert stats["edge_count"] == 2


# ============================================================
# 2. CounterfactualReasoning 测试
# ============================================================

class TestCounterfactualReasoning:
    """反事实推理测试"""

    def test_basic_reasoning(self):
        """基本反事实推理"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        cr = CounterfactualReasoning(g)
        result = cr.reason("X", 1.0, 2.0)
        assert result.variable == "X"
        assert result.actual_value == 1.0
        assert result.hypothetical_value == 2.0

    def test_reasoning_predicts_descendants(self):
        """反事实推理预测后代变化"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        cr = CounterfactualReasoning(g)
        result = cr.reason("X", 1.0, 2.0)
        assert "Y" in result.predicted_outcomes

    def test_reasoning_differences(self):
        """反事实推理差异计算"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        cr = CounterfactualReasoning(g)
        result = cr.reason("X", 1.0, 2.0)
        # 差异应该非零
        assert "Y" in result.differences
        assert result.differences["Y"] != 0

    def test_reasoning_chain(self):
        """链式因果反事实推理"""
        g = CausalGraph()
        g.add_edge("A", "B", CausalStrength.STRONG, 0.9)
        g.add_edge("B", "C", CausalStrength.MODERATE, 0.5)
        cr = CounterfactualReasoning(g)
        result = cr.reason("A", 1.0, 2.0)
        # B和C都应该在预测结果中
        assert "B" in result.predicted_outcomes
        assert "C" in result.predicted_outcomes

    def test_reasoning_no_descendants(self):
        """无后代的变量反事实推理"""
        g = CausalGraph()
        g.add_edge("A", "B")
        cr = CounterfactualReasoning(g)
        result = cr.reason("B", 1.0, 2.0)
        # B无后代，预测结果为空
        assert result.predicted_outcomes == {}

    def test_reasoning_with_context(self):
        """带上下文的反事实推理"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        cr = CounterfactualReasoning(g)
        result = cr.reason("X", 1.0, 2.0, context={"extra": "info"})
        assert result.variable == "X"

    def test_reasoning_default_confidence(self):
        """默认置信度"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        cr = CounterfactualReasoning(g)
        result = cr.reason("X", 1.0, 2.0)
        assert 0.0 <= result.confidence <= 1.0

    def test_reasoning_string_value(self):
        """字符串值反事实推理（防御）"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        cr = CounterfactualReasoning(g)
        # 字符串值不应崩溃
        result = cr.reason("X", "not_a_number", "also_not")
        assert result.variable == "X"

    def test_reasoning_none_value(self):
        """None值反事实推理（防御）"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        cr = CounterfactualReasoning(g)
        result = cr.reason("X", None, None)
        assert result.variable == "X"

    def test_reasoning_diamond_graph(self):
        """菱形图反事实推理"""
        g = CausalGraph()
        g.add_edge("A", "B", CausalStrength.STRONG, 0.9)
        g.add_edge("A", "C", CausalStrength.MODERATE, 0.5)
        g.add_edge("B", "D", CausalStrength.STRONG, 0.8)
        g.add_edge("C", "D", CausalStrength.WEAK, 0.3)
        cr = CounterfactualReasoning(g)
        result = cr.reason("A", 1.0, 2.0)
        # D应该有两条路径累积
        assert "D" in result.predicted_outcomes


# ============================================================
# 3. DoCalculus 测试
# ============================================================

class TestDoCalculus:
    """do-算子测试"""

    def test_basic_do(self):
        """基本do操作"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        dc = DoCalculus(g)
        result = dc.do("X", 5.0)
        assert "intervention" in result
        assert "outcomes" in result
        assert "affected_variables" in result

    def test_do_intervention_string(self):
        """do操作干预字符串"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        dc = DoCalculus(g)
        result = dc.do("X", 5.0)
        assert "do(X=5.0)" in result["intervention"]

    def test_do_affects_descendants(self):
        """do操作影响后代"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        g.add_edge("Y", "Z", CausalStrength.MODERATE, 0.6)
        dc = DoCalculus(g)
        result = dc.do("X", 1.0)
        assert "Y" in result["affected_variables"]
        assert "Z" in result["affected_variables"]

    def test_do_no_descendants(self):
        """do操作无后代"""
        g = CausalGraph()
        g.add_edge("A", "B")
        dc = DoCalculus(g)
        result = dc.do("B", 1.0)
        assert result["affected_variables"] == []
        assert result["outcomes"] == {}

    def test_do_cuts_incoming_edges(self):
        """do操作切断入边"""
        g = CausalGraph()
        # Z→X→Y, do(X)应该切断Z→X
        g.add_edge("Z", "X", CausalStrength.STRONG, 0.9)
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        dc = DoCalculus(g)
        result = dc.do("X", 1.0)
        # Y应该受影响（X的后代）
        assert "Y" in result["affected_variables"]
        # Z不应该受影响（不是X的后代）
        assert "Z" not in result["affected_variables"]

    def test_do_with_context(self):
        """带上下文的do操作"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        dc = DoCalculus(g)
        result = dc.do("X", 1.0, context={"extra": "info"})
        assert "outcomes" in result

    def test_do_string_value(self):
        """字符串值do操作（防御）"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        dc = DoCalculus(g)
        result = dc.do("X", "not_a_number")
        # 不应崩溃
        assert "outcomes" in result

    def test_do_none_value(self):
        """None值do操作（防御）"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        dc = DoCalculus(g)
        result = dc.do("X", None)
        assert "outcomes" in result

    def test_do_chain(self):
        """链式do操作"""
        g = CausalGraph()
        g.add_edge("A", "B", CausalStrength.STRONG, 0.9)
        g.add_edge("B", "C", CausalStrength.MODERATE, 0.5)
        dc = DoCalculus(g)
        result = dc.do("A", 2.0)
        assert "B" in result["outcomes"]
        assert "C" in result["outcomes"]

    def test_do_diamond(self):
        """菱形图do操作"""
        g = CausalGraph()
        g.add_edge("A", "B", CausalStrength.STRONG, 0.9)
        g.add_edge("A", "C", CausalStrength.MODERATE, 0.5)
        g.add_edge("B", "D", CausalStrength.STRONG, 0.8)
        g.add_edge("C", "D", CausalStrength.WEAK, 0.3)
        dc = DoCalculus(g)
        result = dc.do("A", 1.0)
        assert "D" in result["outcomes"]


# ============================================================
# 4. Enhanced Engine 测试
# ============================================================

class TestEnhancedEngine:
    """增强引擎测试"""

    def test_engine_creation(self):
        """引擎创建"""
        eng = CausalFirstPrinciplesEngine("test")
        assert eng.engine_id == "test"

    def test_get_causal_graph(self):
        """获取因果图"""
        eng = CausalFirstPrinciplesEngine()
        g = eng.get_causal_graph()
        assert isinstance(g, CausalGraph)

    def test_add_graph_edge(self):
        """添加因果图边"""
        eng = CausalFirstPrinciplesEngine()
        assert eng.add_graph_edge("A", "B", CausalStrength.STRONG, 0.9) is True

    def test_add_graph_edge_cycle_rejected(self):
        """添加因果图边拒绝环"""
        eng = CausalFirstPrinciplesEngine()
        assert eng.add_graph_edge("A", "B") is True
        assert eng.add_graph_edge("B", "A") is False

    def test_get_parents(self):
        """获取父节点"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_graph_edge("A", "C")
        eng.add_graph_edge("B", "C")
        parents = eng.get_parents("C")
        assert parents == {"A", "B"}

    def test_get_children(self):
        """获取子节点"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_graph_edge("A", "B")
        eng.add_graph_edge("A", "C")
        children = eng.get_children("A")
        assert children == {"B", "C"}

    def test_get_ancestors(self):
        """获取祖先"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_graph_edge("A", "B")
        eng.add_graph_edge("B", "C")
        ancestors = eng.get_ancestors("C")
        assert ancestors == {"A", "B"}

    def test_get_descendants(self):
        """获取后代"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_graph_edge("A", "B")
        eng.add_graph_edge("B", "C")
        descendants = eng.get_descendants("A")
        assert descendants == {"B", "C"}

    def test_get_causal_paths(self):
        """获取因果路径"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_graph_edge("A", "B")
        eng.add_graph_edge("B", "C")
        paths = eng.get_causal_paths("A", "C")
        assert paths == [["A", "B", "C"]]

    def test_topological_sort(self):
        """拓扑排序"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_graph_edge("A", "B")
        eng.add_graph_edge("B", "C")
        ts = eng.topological_sort()
        assert ts.index("A") < ts.index("B")
        assert ts.index("B") < ts.index("C")

    def test_counterfactual_reasoning(self):
        """反事实推理接口"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_graph_edge("X", "Y", CausalStrength.STRONG, 0.8)
        result = eng.counterfactual_reasoning("X", 1.0, 2.0)
        assert isinstance(result, CounterfactualResult)
        assert result.variable == "X"

    def test_do_intervene(self):
        """do-算子接口"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_graph_edge("X", "Y", CausalStrength.STRONG, 0.8)
        result = eng.do_intervene("X", 5.0)
        assert "intervention" in result
        assert "outcomes" in result

    def test_get_counterfactual_engine(self):
        """获取反事实推理引擎"""
        eng = CausalFirstPrinciplesEngine()
        cr = eng.get_counterfactual_engine()
        assert isinstance(cr, CounterfactualReasoning)

    def test_get_do_calculus(self):
        """获取do-算子"""
        eng = CausalFirstPrinciplesEngine()
        dc = eng.get_do_calculus()
        assert isinstance(dc, DoCalculus)

    def test_stats_include_graph(self):
        """统计包含图信息"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_graph_edge("A", "B")
        stats = eng.get_stats()
        assert "graph_stats" in stats
        assert stats["graph_stats"]["node_count"] == 2
        assert stats["graph_stats"]["edge_count"] == 1


# ============================================================
# 5. 向后兼容性测试
# ============================================================

class TestBackwardCompat:
    """向后兼容性测试"""

    def test_causal_strength_enum(self):
        """因果强度枚举"""
        assert CausalStrength.STRONG.value == 1.0
        assert CausalStrength.MODERATE.value == 0.5
        assert CausalStrength.WEAK.value == 0.2
        assert CausalStrength.UNKNOWN.value == 0.0

    def test_causal_link_dataclass(self):
        """因果链接数据类"""
        link = CausalLink(cause="A", effect="B")
        assert link.cause == "A"
        assert link.effect == "B"
        assert link.strength == CausalStrength.MODERATE
        assert link.confidence == 0.5
        assert link.evidence_count == 0

    def test_intervention_dataclass(self):
        """干预数据类"""
        iv = Intervention(
            intervention_id="iv1",
            target_variable="X",
            new_value=5.0,
        )
        assert iv.intervention_id == "iv1"
        assert iv.target_variable == "X"
        assert iv.new_value == 5.0
        assert iv.expected_effects == {}
        assert iv.timestamp > 0

    def test_add_causal_link(self):
        """添加因果链接（向后兼容）"""
        eng = CausalFirstPrinciplesEngine()
        link = eng.add_causal_link("A", "B", CausalStrength.STRONG, 0.9)
        assert link.cause == "A"
        assert link.effect == "B"
        assert link.strength == CausalStrength.STRONG
        assert abs(link.confidence - 0.9) < 1e-6

    def test_add_causal_link_syncs_to_graph(self):
        """添加因果链接同步到图"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_causal_link("A", "B", CausalStrength.STRONG, 0.9)
        # 图中应该有这条边
        children = eng.get_children("A")
        assert "B" in children

    def test_record_observation(self):
        """记录观测（向后兼容）"""
        eng = CausalFirstPrinciplesEngine()
        eng.record_observation({"X": 1.0, "Y": 2.0})
        stats = eng.get_stats()
        assert stats["observations"] == 1
        assert stats["cycle_count"] == 1

    def test_record_observation_non_dict(self):
        """记录非字典观测（防御）"""
        eng = CausalFirstPrinciplesEngine()
        eng.record_observation("not a dict")
        stats = eng.get_stats()
        assert stats["observations"] == 1

    def test_discover_causal_links(self):
        """发现因果链接（向后兼容）"""
        eng = CausalFirstPrinciplesEngine()
        # 添加强相关的观测
        for i in range(10):
            eng.record_observation({"X": float(i), "Y": float(i) * 2})
        discovered = eng.discover_causal_links(min_correlation=0.5)
        assert len(discovered) > 0

    def test_discover_causal_links_insufficient_data(self):
        """数据不足时发现因果链接"""
        eng = CausalFirstPrinciplesEngine()
        eng.record_observation({"X": 1.0})
        discovered = eng.discover_causal_links()
        assert discovered == []

    def test_predict_effect(self):
        """预测效果（向后兼容）"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_causal_link("X", "Y", CausalStrength.STRONG, 0.8)
        effects = eng.predict_effect("X", 2.0)
        assert "Y" in effects
        assert "predicted_change" in effects["Y"]

    def test_predict_effect_nonexistent_cause(self):
        """预测不存在原因的效果"""
        eng = CausalFirstPrinciplesEngine()
        effects = eng.predict_effect("nonexistent", 1.0)
        assert effects == {}

    def test_evaluate_intervention(self):
        """评估干预（向后兼容）"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_causal_link("X", "Y", CausalStrength.STRONG, 0.8)
        iv = Intervention(
            intervention_id="iv1",
            target_variable="X",
            new_value=5.0,
            expected_effects={"Y": 4.0},
        )
        result = eng.evaluate_intervention(iv)
        assert result["intervention"] == "iv1"
        assert "predicted_effects" in result
        assert "unanticipated_effects" in result
        assert "risk_score" in result
        assert "recommended" in result

    def test_evaluate_intervention_unanticipated(self):
        """评估干预发现意外效应"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_causal_link("X", "Y", CausalStrength.STRONG, 0.8)
        eng.add_causal_link("X", "Z", CausalStrength.MODERATE, 0.5)
        iv = Intervention(
            intervention_id="iv1",
            target_variable="X",
            new_value=5.0,
            expected_effects={"Y": 4.0},  # 没有预期Z
        )
        result = eng.evaluate_intervention(iv)
        assert "Z" in result["unanticipated_effects"]
        assert result["recommended"] is False

    def test_counterfactual_compat(self):
        """反事实推理（向后兼容接口）"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_causal_link("X", "Y", CausalStrength.STRONG, 0.8)
        result = eng.counterfactual("X", 2.0)
        assert result["variable"] == "X"
        assert "differences" in result

    def test_clear(self):
        """清除"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_causal_link("A", "B")
        eng.record_observation({"X": 1.0})
        eng.clear()
        stats = eng.get_stats()
        assert stats["causal_links"] == 0
        assert stats["observations"] == 0
        assert stats["graph_stats"]["node_count"] == 0

    def test_create_causal_engine(self):
        """创建因果引擎便捷函数"""
        eng = create_causal_engine("test")
        assert isinstance(eng, CausalFirstPrinciplesEngine)
        assert eng.engine_id == "test"

    def test_create_intervention(self):
        """创建干预便捷函数"""
        iv = create_intervention("iv1", "X", 5.0)
        assert isinstance(iv, Intervention)
        assert iv.intervention_id == "iv1"

    def test_create_causal_graph(self):
        """创建因果图便捷函数"""
        g = create_causal_graph()
        assert isinstance(g, CausalGraph)

    def test_confidence_clamping(self):
        """置信度钳制"""
        eng = CausalFirstPrinciplesEngine()
        link = eng.add_causal_link("A", "B", CausalStrength.STRONG, 1.5)
        assert link.confidence == 1.0
        link = eng.add_causal_link("C", "D", CausalStrength.STRONG, -0.5)
        assert link.confidence == 0.0

    def test_confidence_nan_defense(self):
        """NaN置信度防御"""
        eng = CausalFirstPrinciplesEngine()
        link = eng.add_causal_link("A", "B", CausalStrength.STRONG, float("nan"))
        assert link.confidence == 0.5

    def test_confidence_inf_defense(self):
        """Inf置信度防御"""
        eng = CausalFirstPrinciplesEngine()
        link = eng.add_causal_link("A", "B", CausalStrength.STRONG, float("inf"))
        assert link.confidence == 0.5

    def test_confidence_string_defense(self):
        """字符串置信度防御"""
        eng = CausalFirstPrinciplesEngine()
        link = eng.add_causal_link("A", "B", CausalStrength.STRONG, "not a number")
        assert link.confidence == 0.5


# ============================================================
# 6. 并发安全测试
# ============================================================

class TestConcurrency:
    """并发安全测试"""

    def test_concurrent_add_edges(self):
        """并发添加边"""
        eng = CausalFirstPrinciplesEngine()
        errors = []

        def worker(idx):
            try:
                for i in range(20):
                    eng.add_graph_edge(f"node_{idx}_{i}", f"node_{idx}_{i+1}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        stats = eng.get_stats()
        # 每个线程20条边，5个线程
        assert stats["graph_stats"]["edge_count"] == 100

    def test_concurrent_counterfactual(self):
        """并发反事实推理"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_graph_edge("X", "Y", CausalStrength.STRONG, 0.8)
        eng.add_graph_edge("Y", "Z", CausalStrength.MODERATE, 0.5)

        results = []
        results_lock = threading.Lock()

        def worker():
            r = eng.counterfactual_reasoning("X", 1.0, 2.0)
            with results_lock:
                results.append(r)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10
        for r in results:
            assert r.variable == "X"

    def test_concurrent_do_intervene(self):
        """并发do操作"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_graph_edge("X", "Y", CausalStrength.STRONG, 0.8)

        results = []
        results_lock = threading.Lock()

        def worker():
            r = eng.do_intervene("X", 1.0)
            with results_lock:
                results.append(r)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10


# ============================================================
# 7. 性能测试
# ============================================================

class TestPerformance:
    """性能测试"""

    def test_large_graph_performance(self):
        """大图性能"""
        eng = CausalFirstPrinciplesEngine()
        start = time.time()
        # 1000个节点的链
        for i in range(1000):
            eng.add_graph_edge(f"N{i}", f"N{i+1}", CausalStrength.STRONG, 0.9)
        elapsed = time.time() - start
        # 应该在合理时间内完成
        assert elapsed < 5.0
        stats = eng.get_stats()
        assert stats["graph_stats"]["node_count"] == 1001

    def test_path_finding_performance(self):
        """路径查找性能"""
        eng = CausalFirstPrinciplesEngine()
        for i in range(100):
            eng.add_graph_edge(f"N{i}", f"N{i+1}")
        start = time.time()
        paths = eng.get_causal_paths("N0", "N100")
        elapsed = time.time() - start
        assert elapsed < 2.0
        assert len(paths) == 1

    def test_counterfactual_performance(self):
        """反事实推理性能"""
        eng = CausalFirstPrinciplesEngine()
        for i in range(50):
            eng.add_graph_edge(f"N{i}", f"N{i+1}", CausalStrength.STRONG, 0.9)
        start = time.time()
        result = eng.counterfactual_reasoning("N0", 1.0, 2.0)
        elapsed = time.time() - start
        assert elapsed < 3.0

    def test_do_calculus_performance(self):
        """do-算子性能"""
        eng = CausalFirstPrinciplesEngine()
        for i in range(50):
            eng.add_graph_edge(f"N{i}", f"N{i+1}", CausalStrength.STRONG, 0.9)
        start = time.time()
        result = eng.do_intervene("N0", 1.0)
        elapsed = time.time() - start
        assert elapsed < 3.0


# ============================================================
# 8. 异常容错测试
# ============================================================

class TestErrorTolerance:
    """异常容错测试"""

    def test_empty_graph_operations(self):
        """空图操作"""
        g = CausalGraph()
        assert g.get_parents("X") == set()
        assert g.get_children("X") == set()
        assert g.get_ancestors("X") == set()
        assert g.get_descendants("X") == set()
        assert g.get_all_paths("A", "B") == []
        assert g.topological_sort() == []
        assert g.get_direct_effect("A", "B") is None

    def test_nonexistent_node_operations(self):
        """不存在节点操作"""
        g = CausalGraph()
        g.add_edge("A", "B")
        assert g.get_parents("nonexistent") == set()
        assert g.get_children("nonexistent") == set()
        assert g.get_ancestors("nonexistent") == set()
        assert g.get_descendants("nonexistent") == set()

    def test_counterfactual_nonexistent_variable(self):
        """不存在变量反事实推理"""
        g = CausalGraph()
        g.add_edge("A", "B")
        cr = CounterfactualReasoning(g)
        result = cr.reason("nonexistent", 1.0, 2.0)
        assert result.predicted_outcomes == {}

    def test_do_nonexistent_variable(self):
        """不存在变量do操作"""
        g = CausalGraph()
        g.add_edge("A", "B")
        dc = DoCalculus(g)
        result = dc.do("nonexistent", 1.0)
        assert result["affected_variables"] == []

    def test_nan_value_counterfactual(self):
        """NaN值反事实推理"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        cr = CounterfactualReasoning(g)
        # 不应崩溃
        result = cr.reason("X", float("nan"), 1.0)
        assert result.variable == "X"

    def test_inf_value_counterfactual(self):
        """Inf值反事实推理"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        cr = CounterfactualReasoning(g)
        result = cr.reason("X", float("inf"), 1.0)
        assert result.variable == "X"

    def test_nan_value_do(self):
        """NaN值do操作"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        dc = DoCalculus(g)
        result = dc.do("X", float("nan"))
        assert "outcomes" in result

    def test_engine_clear_resets_graph(self):
        """清除重置图"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_graph_edge("A", "B")
        eng.add_graph_edge("B", "C")
        eng.clear()
        # 图应该被重置
        assert eng.get_children("A") == set()
        stats = eng.get_stats()
        assert stats["graph_stats"]["node_count"] == 0

    def test_engine_clear_resets_counterfactual(self):
        """清除重置反事实引擎"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_graph_edge("A", "B")
        eng.clear()
        # 反事实引擎应该使用新图
        cr = eng.get_counterfactual_engine()
        result = cr.reason("A", 1.0, 2.0)
        assert result.predicted_outcomes == {}

    def test_engine_clear_resets_do_calculus(self):
        """清除重置do-算子"""
        eng = CausalFirstPrinciplesEngine()
        eng.add_graph_edge("A", "B")
        eng.clear()
        dc = eng.get_do_calculus()
        result = dc.do("A", 1.0)
        assert result["affected_variables"] == []


# ============================================================
# 9. 第一性原理验证测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证测试"""

    def test_causation_is_dag(self):
        """第一性原理：因果图是有向无环图"""
        g = CausalGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        # 任何尝试创建环的操作都应失败
        assert g.add_edge("C", "A") is False
        assert g.add_edge("B", "A") is False
        assert g.is_dag() is True

    def test_correlation_not_causation(self):
        """第一性原理：相关不等于因果"""
        eng = CausalFirstPrinciplesEngine()
        # 添加完全相关的观测
        for i in range(10):
            eng.record_observation({"X": float(i), "Y": float(i)})
        # 发现的"因果"链接只是候选，需要人工/系统验证
        discovered = eng.discover_causal_links(min_correlation=0.5)
        # 相关性高，但只是候选
        assert len(discovered) > 0
        # 这些只是候选，confidence基于相关性
        for link in discovered:
            assert 0.0 <= link.confidence <= 1.0

    def test_do_differs_from_observation(self):
        """第一性原理：do(X=x) ≠ 观察X=x"""
        g = CausalGraph()
        # Z→X→Y
        g.add_edge("Z", "X", CausalStrength.STRONG, 0.9)
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        dc = DoCalculus(g)
        # do(X=1) 切断Z→X
        result_do = dc.do("X", 1.0)
        # Z不应该受影响
        assert "Z" not in result_do["affected_variables"]
        # Y应该受影响
        assert "Y" in result_do["affected_variables"]

    def test_counterfactual_difference(self):
        """第一性原理：反事实 = Y(a) - Y(a')"""
        g = CausalGraph()
        g.add_edge("X", "Y", CausalStrength.STRONG, 0.8)
        cr = CounterfactualReasoning(g)
        result = cr.reason("X", 1.0, 2.0)
        # 差异 = Y(2) - Y(1)
        assert "Y" in result.differences
        # 差异应该非零（因为X变化了）
        assert result.differences["Y"] != 0

    def test_intervention_cuts_incoming_edges(self):
        """第一性原理：干预切断入边"""
        g = CausalGraph()
        # A→B→C, A→C
        g.add_edge("A", "B", CausalStrength.STRONG, 0.9)
        g.add_edge("B", "C", CausalStrength.STRONG, 0.8)
        g.add_edge("A", "C", CausalStrength.MODERATE, 0.5)
        dc = DoCalculus(g)
        # do(B=1) 切断A→B
        result = dc.do("B", 1.0)
        # C应该受影响（B的后代）
        assert "C" in result["affected_variables"]
        # A不应该受影响（不是B的后代）
        assert "A" not in result["affected_variables"]

    def test_causal_path_analysis(self):
        """第一性原理：因果路径分析（直接/间接/总效应）"""
        g = CausalGraph()
        # A→B→C (间接) + A→C (直接)
        g.add_edge("A", "B", CausalStrength.STRONG, 0.9)
        g.add_edge("B", "C", CausalStrength.STRONG, 0.8)
        g.add_edge("A", "C", CausalStrength.MODERATE, 0.5)
        # 直接效应
        direct = g.get_direct_effect("A", "C")
        assert direct is not None
        # 间接效应路径
        indirect = g.get_indirect_effects("A", "C")
        assert len(indirect) == 1
        assert indirect[0] == ["A", "B", "C"]
        # 所有路径
        all_paths = g.get_all_paths("A", "C")
        assert len(all_paths) == 2

    def test_topological_order_respects_causality(self):
        """第一性原理：拓扑排序尊重因果顺序"""
        g = CausalGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("A", "C")
        ts = g.topological_sort()
        # 原因必须在结果之前
        assert ts.index("A") < ts.index("B")
        assert ts.index("A") < ts.index("C")
        assert ts.index("B") < ts.index("C")
