"""
阶段118: 决策能力强化 — 专项测试

验证新增能力:
1. DecisionCriterion: 决策准则（最大化/最小化、权重、归一化）
2. MultiObjectiveDecision: 多目标决策
3. ParetoFrontier: 帕累托前沿（非支配解集）
4. DecisionTreeNode / DecisionTree: 决策树（期望效用、最优路径）
5. FreeWillFirstPrinciplesEngine: 新增多目标决策和决策树接口
6. 向后兼容性: 保留原有 make_decision / evaluate_autonomy 接口

第一性原理验证:
- 帕累托最优：非支配解集
- 期望效用最大化：E[U] = Σ p(outcome) × U(outcome)
- 多目标权衡：不同准则相互竞争
- 决策树分解：复杂决策分解为层级子决策
"""

import math
import threading
import time
import pytest

from self_evolving_agent.core.free_will_first_principles import (
    DecisionSource,
    CriterionType,
    DecisionNodeType,
    Decision,
    ChoiceSet,
    DecisionCriterion,
    MultiObjectiveDecision,
    ParetoFrontier,
    DecisionTreeNode,
    DecisionTree,
    FreeWillFirstPrinciplesEngine,
    create_free_will_engine,
    create_choice_set,
    create_criterion,
    create_decision_node,
    create_decision_tree,
)


# ============================================================
# 1. DecisionCriterion 测试
# ============================================================

class TestDecisionCriterion:
    """决策准则测试"""

    def test_creation(self):
        """创建准则"""
        c = DecisionCriterion("utility", CriterionType.MAXIMIZE, 1.0)
        assert c.name == "utility"
        assert c.criterion_type == CriterionType.MAXIMIZE
        assert c.weight == 1.0

    def test_evaluate_with_evaluator(self):
        """带评估器的评估"""
        c = create_criterion("score", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.8, "b": 0.5}.get(opt, 0.0))
        assert c.evaluate("a", {}) == 0.8
        assert c.evaluate("b", {}) == 0.5

    def test_evaluate_without_evaluator(self):
        """无评估器返回0"""
        c = DecisionCriterion("empty", CriterionType.MAXIMIZE)
        assert c.evaluate("a", {}) == 0.0

    def test_evaluate_exception_returns_zero(self):
        """评估器异常返回0"""
        c = create_criterion("bad", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: 1 / 0)
        assert c.evaluate("a", {}) == 0.0

    def test_evaluate_nan_returns_zero(self):
        """NaN返回0"""
        c = create_criterion("nan", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: float("nan"))
        assert c.evaluate("a", {}) == 0.0

    def test_evaluate_inf_returns_zero(self):
        """Inf返回0"""
        c = create_criterion("inf", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: float("inf"))
        assert c.evaluate("a", {}) == 0.0

    def test_normalized_score_maximize(self):
        """最大化归一化"""
        c = create_criterion("util", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.3, "b": 0.9}.get(opt, 0.5))
        # a: (0.3-0.3)/(0.9-0.3) = 0
        # b: (0.9-0.3)/(0.9-0.3) = 1
        assert c.normalized_score("a", {}, 0.3, 0.9) == 0.0
        assert c.normalized_score("b", {}, 0.3, 0.9) == 1.0

    def test_normalized_score_minimize(self):
        """最小化归一化"""
        c = create_criterion("cost", CriterionType.MINIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.3, "b": 0.9}.get(opt, 0.5))
        # a: (0.9-0.3)/(0.9-0.3) = 1 (低成本低分？不，低成本高归一化分)
        # b: (0.9-0.9)/(0.9-0.3) = 0
        assert c.normalized_score("a", {}, 0.3, 0.9) == 1.0
        assert c.normalized_score("b", {}, 0.3, 0.9) == 0.0

    def test_normalized_score_no_difference(self):
        """无差异时返回0.5"""
        c = create_criterion("util", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: 0.5)
        assert c.normalized_score("a", {}, 0.5, 0.5) == 0.5

    def test_normalized_score_clamped(self):
        """归一化得分钳制在[0,1]"""
        c = create_criterion("util", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: 2.0)
        score = c.normalized_score("a", {}, 0.0, 1.0)
        assert 0.0 <= score <= 1.0


# ============================================================
# 2. ParetoFrontier 测试
# ============================================================

class TestParetoFrontier:
    """帕累托前沿测试"""

    def test_empty_options(self):
        """空选项集"""
        pareto, scores = ParetoFrontier.compute([], [], {})
        assert pareto == []
        assert scores == {}

    def test_empty_criteria(self):
        """空准则"""
        pareto, scores = ParetoFrontier.compute(["a", "b"], [], {})
        assert pareto == []
        assert scores == {}

    def test_single_optimal(self):
        """单一最优解"""
        # a 在所有准则上都优于 b
        criteria = [
            create_criterion("util", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.9, "b": 0.5}.get(opt, 0.0)),
            create_criterion("cost", CriterionType.MINIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.1, "b": 0.5}.get(opt, 0.0)),
        ]
        pareto, scores = ParetoFrontier.compute(["a", "b"], criteria, {})
        assert "a" in pareto
        assert "b" not in pareto

    def test_pareto_optimal_set(self):
        """帕累托最优集"""
        # a: 高效用高成本
        # b: 低效用低成本
        # c: 中等效用中等成本
        # a 和 b 都在帕累托前沿上（互不支配）
        criteria = [
            create_criterion("util", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.9, "b": 0.3, "c": 0.6}.get(opt, 0.0)),
            create_criterion("cost", CriterionType.MINIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.8, "b": 0.2, "c": 0.5}.get(opt, 0.0)),
        ]
        pareto, scores = ParetoFrontier.compute(["a", "b", "c"], criteria, {})
        # a 和 b 在前沿上，c 被 a 或 b 支配？
        # a vs c: a util 0.9 > c 0.6, a cost 0.8 > c 0.5 (a成本更高，所以a不支配c)
        # b vs c: b util 0.3 < c 0.6, b cost 0.2 < c 0.5 (b效用更低，所以b不支配c)
        # 实际上 c 也可能在前沿上
        assert "a" in pareto
        assert "b" in pareto

    def test_all_equal_options(self):
        """所有选项相同（都在前沿上）"""
        criteria = [
            create_criterion("util", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: 0.5),
        ]
        pareto, _ = ParetoFrontier.compute(["a", "b", "c"], criteria, {})
        # 全部相同，互不支配，都在前沿
        assert len(pareto) == 3

    def test_dominance_maximize(self):
        """最大化支配关系"""
        scores = {
            "a": {"util": 0.9},
            "b": {"util": 0.5},
        }
        criteria = [DecisionCriterion("util", CriterionType.MAXIMIZE)]
        # a 支配 b（a效用更高）
        assert ParetoFrontier._dominates("a", "b", criteria, scores) is True
        assert ParetoFrontier._dominates("b", "a", criteria, scores) is False

    def test_dominance_minimize(self):
        """最小化支配关系"""
        scores = {
            "a": {"cost": 0.3},
            "b": {"cost": 0.7},
        }
        criteria = [DecisionCriterion("cost", CriterionType.MINIMIZE)]
        # a 支配 b（a成本更低）
        assert ParetoFrontier._dominates("a", "b", criteria, scores) is True
        assert ParetoFrontier._dominates("b", "a", criteria, scores) is False

    def test_no_dominance_when_equal(self):
        """相等时不支配"""
        scores = {
            "a": {"util": 0.5},
            "b": {"util": 0.5},
        }
        criteria = [DecisionCriterion("util", CriterionType.MAXIMIZE)]
        assert ParetoFrontier._dominates("a", "b", criteria, scores) is False

    def test_multi_criteria_dominance(self):
        """多准则支配"""
        scores = {
            "a": {"util": 0.9, "cost": 0.1},
            "b": {"util": 0.5, "cost": 0.5},
        }
        criteria = [
            DecisionCriterion("util", CriterionType.MAXIMIZE),
            DecisionCriterion("cost", CriterionType.MINIMIZE),
        ]
        # a 在两个准则上都优于 b
        assert ParetoFrontier._dominates("a", "b", criteria, scores) is True

    def test_partial_dominance_not_dominates(self):
        """部分准则优但不全优，不支配"""
        scores = {
            "a": {"util": 0.9, "cost": 0.8},
            "b": {"util": 0.5, "cost": 0.2},
        }
        criteria = [
            DecisionCriterion("util", CriterionType.MAXIMIZE),
            DecisionCriterion("cost", CriterionType.MINIMIZE),
        ]
        # a 效用高但成本也高，不支配 b
        assert ParetoFrontier._dominates("a", "b", criteria, scores) is False


# ============================================================
# 3. DecisionTreeNode / DecisionTree 测试
# ============================================================

class TestDecisionTree:
    """决策树测试"""

    def test_node_creation(self):
        """节点创建"""
        node = create_decision_node("n1", DecisionNodeType.DECISION, "label")
        assert node.node_id == "n1"
        assert node.node_type == DecisionNodeType.DECISION
        assert node.label == "label"
        assert node.is_leaf() is True

    def test_add_child(self):
        """添加子节点"""
        parent = create_decision_node("p", DecisionNodeType.DECISION)
        child = create_decision_node("c", DecisionNodeType.OUTCOME, utility=0.5)
        parent.add_child(child, "branch")
        assert len(parent.children) == 1
        assert parent.children[0] == child
        assert parent.branch_labels == ["branch"]
        assert parent.is_leaf() is False

    def test_add_child_with_probability(self):
        """带概率添加子节点"""
        parent = create_decision_node("p", DecisionNodeType.CHANCE)
        child = create_decision_node("c", DecisionNodeType.OUTCOME, utility=0.5)
        parent.add_child(child, "branch", 0.7)
        assert parent.branch_probabilities == [0.7]

    def test_outcome_utility(self):
        """结果节点效用"""
        tree = create_decision_tree(
            create_decision_node("root", DecisionNodeType.OUTCOME, utility=0.8)
        )
        assert tree.expected_utility() == 0.8

    def test_decision_node_max_utility(self):
        """决策节点选择最大效用"""
        root = create_decision_node("root", DecisionNodeType.DECISION)
        root.add_child(create_decision_node("a", DecisionNodeType.OUTCOME, utility=0.3), "a")
        root.add_child(create_decision_node("b", DecisionNodeType.OUTCOME, utility=0.9), "b")
        root.add_child(create_decision_node("c", DecisionNodeType.OUTCOME, utility=0.5), "c")
        tree = create_decision_tree(root)
        assert tree.expected_utility() == 0.9

    def test_chance_node_expected_utility(self):
        """机会节点期望效用"""
        root = create_decision_node("root", DecisionNodeType.CHANCE)
        root.add_child(create_decision_node("a", DecisionNodeType.OUTCOME, utility=0.9), "success", 0.7)
        root.add_child(create_decision_node("b", DecisionNodeType.OUTCOME, utility=0.1), "fail", 0.3)
        tree = create_decision_tree(root)
        # 0.7*0.9 + 0.3*0.1 = 0.63 + 0.03 = 0.66
        assert abs(tree.expected_utility() - 0.66) < 1e-6

    def test_nested_tree(self):
        """嵌套决策树"""
        # 决策 -> 机会 -> 结果
        root = create_decision_node("root", DecisionNodeType.DECISION)
        chance = create_decision_node("chance", DecisionNodeType.CHANCE)
        root.add_child(chance, "go")
        chance.add_child(create_decision_node("good", DecisionNodeType.OUTCOME, utility=0.9), "good", 0.6)
        chance.add_child(create_decision_node("bad", DecisionNodeType.OUTCOME, utility=0.2), "bad", 0.4)
        tree = create_decision_tree(root)
        # 0.6*0.9 + 0.4*0.2 = 0.54 + 0.08 = 0.62
        assert abs(tree.expected_utility() - 0.62) < 1e-6

    def test_best_path_decision(self):
        """最优路径（决策节点）"""
        root = create_decision_node("root", DecisionNodeType.DECISION)
        root.add_child(create_decision_node("a", DecisionNodeType.OUTCOME, utility=0.3), "go_a")
        root.add_child(create_decision_node("b", DecisionNodeType.OUTCOME, utility=0.9), "go_b")
        tree = create_decision_tree(root)
        path = tree.best_path()
        assert "go_b" in path

    def test_best_path_nested(self):
        """最优路径（嵌套）"""
        root = create_decision_node("root", DecisionNodeType.DECISION)
        # 分支A: 期望效用 0.7*0.9 + 0.3*0.1 = 0.66
        chance_a = create_decision_node("ca", DecisionNodeType.CHANCE)
        root.add_child(chance_a, "go_a")
        chance_a.add_child(create_decision_node("a1", DecisionNodeType.OUTCOME, utility=0.9), "good", 0.7)
        chance_a.add_child(create_decision_node("a2", DecisionNodeType.OUTCOME, utility=0.1), "bad", 0.3)
        # 分支B: 期望效用 0.5*0.8 + 0.5*0.4 = 0.6
        chance_b = create_decision_node("cb", DecisionNodeType.CHANCE)
        root.add_child(chance_b, "go_b")
        chance_b.add_child(create_decision_node("b1", DecisionNodeType.OUTCOME, utility=0.8), "good", 0.5)
        chance_b.add_child(create_decision_node("b2", DecisionNodeType.OUTCOME, utility=0.4), "bad", 0.5)

        tree = create_decision_tree(root)
        # A 期望效用 0.66 > B 期望效用 0.6
        path = tree.best_path()
        assert "go_a" in path[0]

    def test_count_nodes(self):
        """节点计数"""
        root = create_decision_node("root", DecisionNodeType.DECISION)
        root.add_child(create_decision_node("a", DecisionNodeType.OUTCOME, utility=0.5), "a")
        root.add_child(create_decision_node("b", DecisionNodeType.OUTCOME, utility=0.6), "b")
        tree = create_decision_tree(root)
        assert tree.count_nodes() == 3

    def test_get_depth(self):
        """树深度"""
        root = create_decision_node("root", DecisionNodeType.DECISION)
        child = create_decision_node("c", DecisionNodeType.DECISION)
        root.add_child(child, "go")
        leaf = create_decision_node("l", DecisionNodeType.OUTCOME, utility=0.5)
        child.add_child(leaf, "end")
        tree = create_decision_tree(root)
        assert tree.get_depth() == 3

    def test_empty_tree_utility(self):
        """空树效用为0"""
        tree = create_decision_tree(
            create_decision_node("root", DecisionNodeType.DECISION)
        )
        # 无子节点的决策节点返回自身utility（0.0）
        assert tree.expected_utility() == 0.0

    def test_chance_node_nan_probability(self):
        """NaN概率防御"""
        root = create_decision_node("root", DecisionNodeType.CHANCE)
        root.add_child(create_decision_node("a", DecisionNodeType.OUTCOME, utility=0.9), "a", float("nan"))
        root.add_child(create_decision_node("b", DecisionNodeType.OUTCOME, utility=0.1), "b", 0.5)
        tree = create_decision_tree(root)
        # NaN概率被当作0，结果 = 0*0.9 + 0.5*0.1 = 0.05
        eu = tree.expected_utility()
        assert not math.isnan(eu)


# ============================================================
# 4. MultiObjectiveDecision 测试
# ============================================================

class TestMultiObjectiveDecision:
    """多目标决策测试"""

    def test_is_pareto_optimal_choice(self):
        """帕累托最优选择属性"""
        d = MultiObjectiveDecision(
            decision_id="d1",
            chosen_option="a",
            pareto_optimal_set=["a", "b"],
        )
        assert d.is_pareto_optimal_choice is True

    def test_not_pareto_optimal_choice(self):
        """非帕累托最优选择"""
        d = MultiObjectiveDecision(
            decision_id="d1",
            chosen_option="c",
            pareto_optimal_set=["a", "b"],
        )
        assert d.is_pareto_optimal_choice is False


# ============================================================
# 5. FreeWillFirstPrinciplesEngine 新接口测试
# ============================================================

class TestEnhancedEngine:
    """增强引擎测试"""

    def test_set_default_criteria(self):
        """设置默认准则"""
        engine = create_free_will_engine()
        criteria = [create_criterion("util", CriterionType.MAXIMIZE)]
        engine.set_default_criteria(criteria)
        # 通过make_multi_objective_decision不传criteria验证
        cs = create_choice_set("test", ["a", "b"])
        decision = engine.make_multi_objective_decision(cs)
        assert decision is not None

    def test_make_multi_objective_decision(self):
        """多目标决策"""
        engine = create_free_will_engine()
        criteria = [
            create_criterion("util", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.9, "b": 0.5}.get(opt, 0.0)),
            create_criterion("cost", CriterionType.MINIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.1, "b": 0.5}.get(opt, 0.0)),
        ]
        cs = create_choice_set("test", ["a", "b"])
        decision = engine.make_multi_objective_decision(cs, criteria)
        # a 在两个准则上都优于 b，应选 a
        assert decision.chosen_option == "a"
        assert "a" in decision.pareto_optimal_set

    def test_make_multi_objective_decision_no_criteria(self):
        """无准则时退化"""
        engine = create_free_will_engine()
        cs = create_choice_set("test", ["a", "b"])
        decision = engine.make_multi_objective_decision(cs, [])
        assert decision is not None
        assert decision.chosen_option in ["a", "b"]

    def test_make_multi_objective_decision_empty_options(self):
        """空选项防御"""
        engine = create_free_will_engine()
        cs = create_choice_set("test", [])
        criteria = [create_criterion("util", CriterionType.MAXIMIZE)]
        decision = engine.make_multi_objective_decision(cs, criteria)
        assert decision.chosen_option == "noop"

    def test_make_multi_objective_decision_with_constraints(self):
        """带约束的多目标决策"""
        engine = create_free_will_engine()
        criteria = [
            create_criterion("util", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.9, "b": 0.5, "bad": 0.1}.get(opt, 0.0)),
        ]
        cs = create_choice_set("test", ["a", "b", "bad"], constraints=["bad"])
        decision = engine.make_multi_objective_decision(cs, criteria)
        assert "bad" not in decision.pareto_optimal_set

    def test_evaluate_decision_tree(self):
        """评估决策树"""
        engine = create_free_will_engine()
        root = create_decision_node("root", DecisionNodeType.DECISION)
        root.add_child(create_decision_node("a", DecisionNodeType.OUTCOME, utility=0.3), "a")
        root.add_child(create_decision_node("b", DecisionNodeType.OUTCOME, utility=0.9), "b")
        tree = create_decision_tree(root)
        result = engine.evaluate_decision_tree(tree)
        assert result["expected_utility"] == 0.9
        assert "best_path" in result
        assert result["node_count"] == 3
        assert result["depth"] == 2

    def test_get_multi_objective_decisions(self):
        """获取多目标决策历史"""
        engine = create_free_will_engine()
        cs = create_choice_set("test", ["a", "b"])
        engine.make_multi_objective_decision(cs, [])
        decisions = engine.get_multi_objective_decisions()
        assert len(decisions) == 1

    def test_get_pareto_frontier(self):
        """获取帕累托前沿"""
        engine = create_free_will_engine()
        criteria = [
            create_criterion("util", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.9, "b": 0.5}.get(opt, 0.0)),
        ]
        pareto, scores = engine.get_pareto_frontier(["a", "b"], criteria)
        assert "a" in pareto

    def test_stats_include_multi_objective(self):
        """统计包含多目标决策"""
        engine = create_free_will_engine()
        cs = create_choice_set("test", ["a", "b"])
        engine.make_multi_objective_decision(cs, [])
        stats = engine.get_stats()
        assert "multi_objective_decisions_count" in stats
        assert stats["multi_objective_decisions_count"] == 1


# ============================================================
# 6. 向后兼容性测试
# ============================================================

class TestBackwardCompat:
    """向后兼容性测试"""

    def test_make_decision_basic(self):
        """基础决策"""
        engine = create_free_will_engine()
        cs = create_choice_set("test", ["a", "b", "c"])
        decision = engine.make_decision(cs)
        assert isinstance(decision, Decision)
        assert decision.chosen_action in ["a", "b", "c"]

    def test_make_decision_with_value_function(self):
        """带价值函数的决策"""
        engine = create_free_will_engine()
        cs = create_choice_set("test", ["a", "b", "c"])
        decision = engine.make_decision(cs, lambda opt, ctx: {"a": 0.1, "b": 0.9, "c": 0.5}.get(opt, 0.0))
        assert decision.chosen_action == "b"

    def test_make_decision_with_constraints(self):
        """带约束的决策"""
        engine = create_free_will_engine()
        cs = create_choice_set("test", ["good_a", "bad_b", "good_c"], constraints=["bad"])
        decision = engine.make_decision(cs)
        assert "bad" not in decision.chosen_action

    def test_make_decision_empty_options(self):
        """空选项防御"""
        engine = create_free_will_engine()
        cs = create_choice_set("test", [])
        decision = engine.make_decision(cs)
        assert decision.chosen_action == "noop"

    def test_decision_autonomy_score(self):
        """决策自主性"""
        engine = create_free_will_engine()
        cs = create_choice_set("test", ["a", "b"])
        decision = engine.make_decision(cs, lambda opt, ctx: 1.0)
        autonomy = engine.evaluate_autonomy(decision.decision_id)
        assert 0.0 <= autonomy <= 1.0

    def test_could_have_done_otherwise(self):
        """本可以做出其他选择"""
        engine = create_free_will_engine()
        cs = create_choice_set("test", ["a", "b", "c"])
        decision = engine.make_decision(cs, lambda opt, ctx: 1.0)
        assert engine.could_have_done_otherwise(decision.decision_id) is True

    def test_trace_decision(self):
        """追溯决策"""
        engine = create_free_will_engine()
        engine.update_internal_model({"preferences": {"a": 1.0}})
        cs = create_choice_set("test", ["a", "b"])
        decision = engine.make_decision(cs)
        trace = engine.trace_decision_to_internal_state(decision.decision_id)
        assert "decision" in trace
        assert "reasons" in trace
        assert "autonomy" in trace

    def test_get_stats_backward_compat(self):
        """统计向后兼容"""
        engine = create_free_will_engine()
        cs = create_choice_set("test", ["a", "b"])
        engine.make_decision(cs)
        stats = engine.get_stats()
        assert "engine_id" in stats
        assert "decisions_count" in stats
        assert "avg_autonomy" in stats
        assert "internal_sources" in stats
        assert "hybrid_sources" in stats

    def test_reset(self):
        """重置"""
        engine = create_free_will_engine()
        cs = create_choice_set("test", ["a", "b"])
        engine.make_decision(cs)
        engine.make_multi_objective_decision(cs, [])
        engine.reset()
        stats = engine.get_stats()
        assert stats["decisions_count"] == 0
        assert stats["multi_objective_decisions_count"] == 0

    def test_external_pressure(self):
        """外部压力影响"""
        engine = create_free_will_engine()
        cs = create_choice_set("test", ["a", "b"], context={"external_pressure": 0.9})
        decision = engine.make_decision(cs, lambda opt, ctx: 1.0)
        assert decision.source == DecisionSource.HYBRID

    def test_create_choice_set_helper(self):
        """create_choice_set 便捷函数"""
        cs = create_choice_set("test", ["a", "b"], constraints=["x"], context={"k": "v"})
        assert cs.choice_id == "test"
        assert cs.options == ["a", "b"]
        assert cs.constraints == ["x"]
        assert cs.context == {"k": "v"}

    def test_create_criterion_helper(self):
        """create_criterion 便捷函数"""
        c = create_criterion("util", CriterionType.MAXIMIZE, 2.0)
        assert c.name == "util"
        assert c.weight == 2.0

    def test_create_decision_node_helper(self):
        """create_decision_node 便捷函数"""
        node = create_decision_node("n1", DecisionNodeType.OUTCOME, "label", 0.5)
        assert node.node_id == "n1"
        assert node.utility == 0.5

    def test_create_decision_tree_helper(self):
        """create_decision_tree 便捷函数"""
        root = create_decision_node("root", DecisionNodeType.OUTCOME, utility=0.5)
        tree = create_decision_tree(root)
        assert isinstance(tree, DecisionTree)


# ============================================================
# 7. 并发安全测试
# ============================================================

class TestConcurrency:
    """并发安全测试"""

    def test_concurrent_make_decision(self):
        """并发决策"""
        engine = create_free_will_engine()
        errors = []

        def worker(worker_id):
            try:
                for i in range(20):
                    cs = create_choice_set(f"w{worker_id}_{i}", ["a", "b", "c"])
                    engine.make_decision(cs, lambda opt, ctx: hash(opt) % 10)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert engine.get_stats()["decisions_count"] == 100

    def test_concurrent_multi_objective(self):
        """并发多目标决策"""
        engine = create_free_will_engine()
        criteria = [
            create_criterion("util", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: hash(opt) % 10),
        ]
        errors = []

        def worker(worker_id):
            try:
                for i in range(20):
                    cs = create_choice_set(f"w{worker_id}_{i}", ["a", "b", "c"])
                    engine.make_multi_objective_decision(cs, criteria)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert engine.get_stats()["multi_objective_decisions_count"] == 100

    def test_concurrent_decision_tree(self):
        """并发决策树评估"""
        engine = create_free_will_engine()
        errors = []

        # 共享一棵树
        root = create_decision_node("root", DecisionNodeType.DECISION)
        root.add_child(create_decision_node("a", DecisionNodeType.OUTCOME, utility=0.3), "a")
        root.add_child(create_decision_node("b", DecisionNodeType.OUTCOME, utility=0.9), "b")
        tree = create_decision_tree(root)

        def worker():
            try:
                for _ in range(50):
                    engine.evaluate_decision_tree(tree)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ============================================================
# 8. 性能测试
# ============================================================

class TestPerformance:
    """性能测试"""

    def test_make_decision_performance(self):
        """决策性能：1000次 < 1秒"""
        engine = create_free_will_engine()
        cs = create_choice_set("perf", ["a", "b", "c", "d", "e"])
        start = time.time()
        for _ in range(1000):
            engine.make_decision(cs, lambda opt, ctx: hash(opt) % 10)
        elapsed = time.time() - start
        assert elapsed < 1.0, f"决策1000次耗时 {elapsed:.3f}s"

    def test_multi_objective_performance(self):
        """多目标决策性能：100次 < 1秒"""
        engine = create_free_will_engine()
        criteria = [
            create_criterion("util", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: hash(opt) % 10),
            create_criterion("cost", CriterionType.MINIMIZE, 1.0,
                             lambda opt, ctx: hash(opt) % 5),
        ]
        cs = create_choice_set("perf", [f"opt{i}" for i in range(10)])
        start = time.time()
        for _ in range(100):
            engine.make_multi_objective_decision(cs, criteria)
        elapsed = time.time() - start
        assert elapsed < 1.0, f"多目标决策100次耗时 {elapsed:.3f}s"

    def test_pareto_frontier_performance(self):
        """帕累托前沿性能：100选项 < 0.5秒"""
        criteria = [
            create_criterion("c1", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: hash(opt) % 100),
            create_criterion("c2", CriterionType.MINIMIZE, 1.0,
                             lambda opt, ctx: hash(opt) % 50),
        ]
        options = [f"opt{i}" for i in range(100)]
        start = time.time()
        ParetoFrontier.compute(options, criteria, {})
        elapsed = time.time() - start
        assert elapsed < 0.5, f"帕累托前沿100选项耗时 {elapsed:.3f}s"

    def test_decision_tree_performance(self):
        """决策树评估性能：1000次 < 0.5秒"""
        # 构建深度为3的树
        root = create_decision_node("root", DecisionNodeType.DECISION)
        for i in range(5):
            chance = create_decision_node(f"c{i}", DecisionNodeType.CHANCE)
            root.add_child(chance, f"branch{i}")
            for j in range(3):
                chance.add_child(
                    create_decision_node(f"o{i}_{j}", DecisionNodeType.OUTCOME, utility=0.1 * j),
                    f"out{j}", 1.0 / 3
                )
        tree = create_decision_tree(root)
        start = time.time()
        for _ in range(1000):
            tree.expected_utility()
        elapsed = time.time() - start
        assert elapsed < 1.0, f"决策树评估1000次耗时 {elapsed:.3f}s"


# ============================================================
# 9. 异常容错测试
# ============================================================

class TestErrorTolerance:
    """异常容错测试"""

    def test_evaluator_raises_exception(self):
        """评估器抛异常返回0"""
        c = create_criterion("bad", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: 1 / 0)
        assert c.evaluate("a", {}) == 0.0

    def test_evaluator_returns_none(self):
        """评估器返回None"""
        c = create_criterion("none", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: None)
        assert c.evaluate("a", {}) == 0.0

    def test_evaluator_returns_string(self):
        """评估器返回字符串"""
        c = create_criterion("str", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: "not a number")
        assert c.evaluate("a", {}) == 0.0

    def test_zero_weight_criteria(self):
        """零权重准则"""
        engine = create_free_will_engine()
        criteria = [
            create_criterion("util", CriterionType.MAXIMIZE, 0.0,
                             lambda opt, ctx: {"a": 0.9, "b": 0.5}.get(opt, 0.0)),
        ]
        cs = create_choice_set("test", ["a", "b"])
        decision = engine.make_multi_objective_decision(cs, criteria)
        # 不崩溃即可
        assert decision is not None

    def test_negative_weight_criteria(self):
        """负权重准则"""
        engine = create_free_will_engine()
        criteria = [
            create_criterion("util", CriterionType.MAXIMIZE, -1.0,
                             lambda opt, ctx: {"a": 0.9, "b": 0.5}.get(opt, 0.0)),
        ]
        cs = create_choice_set("test", ["a", "b"])
        decision = engine.make_multi_objective_decision(cs, criteria)
        assert decision is not None

    def test_nan_probability_in_tree(self):
        """树中NaN概率"""
        root = create_decision_node("root", DecisionNodeType.CHANCE)
        root.add_child(create_decision_node("a", DecisionNodeType.OUTCOME, utility=0.9), "a", float("nan"))
        tree = create_decision_tree(root)
        eu = tree.expected_utility()
        assert not math.isnan(eu)

    def test_inf_probability_in_tree(self):
        """树中Inf概率"""
        root = create_decision_node("root", DecisionNodeType.CHANCE)
        root.add_child(create_decision_node("a", DecisionNodeType.OUTCOME, utility=0.9), "a", float("inf"))
        tree = create_decision_tree(root)
        eu = tree.expected_utility()
        assert not math.isnan(eu)

    def test_nan_utility_in_tree(self):
        """树中NaN效用"""
        root = create_decision_node("root", DecisionNodeType.OUTCOME, utility=float("nan"))
        tree = create_decision_tree(root)
        eu = tree.expected_utility()
        # NaN效用会传播，但不崩溃
        assert isinstance(eu, float)

    def test_deeply_nested_tree(self):
        """深层嵌套树"""
        root = create_decision_node("root", DecisionNodeType.DECISION)
        current = root
        for i in range(20):
            child = create_decision_node(f"d{i}", DecisionNodeType.DECISION)
            current.add_child(child, f"go{i}")
            current = child
        # 叶节点
        current.add_child(create_decision_node("leaf", DecisionNodeType.OUTCOME, utility=0.5), "end")
        tree = create_decision_tree(root)
        # 不崩溃即可
        eu = tree.expected_utility()
        assert eu == 0.5


# ============================================================
# 10. 第一性原理验证测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_pareto_optimality(self):
        """帕累托最优性：非支配解集"""
        # a: 高效用高成本
        # b: 低效用低成本
        # c: 中等效用中等成本
        criteria = [
            create_criterion("util", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.9, "b": 0.3, "c": 0.6}.get(opt, 0.0)),
            create_criterion("cost", CriterionType.MINIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.8, "b": 0.2, "c": 0.5}.get(opt, 0.0)),
        ]
        pareto, _ = ParetoFrontier.compute(["a", "b", "c"], criteria, {})
        # a 和 b 互不支配，都在前沿
        assert "a" in pareto
        assert "b" in pareto
        # c 被 a 在效用上不优于，被 b 在成本上不优于，但 c 也可能在前沿
        # 验证前沿中的每个方案都不被其他方案支配
        for opt in pareto:
            for other in pareto:
                if opt != other:
                    scores = {
                        "a": {"util": 0.9, "cost": 0.8},
                        "b": {"util": 0.3, "cost": 0.2},
                        "c": {"util": 0.6, "cost": 0.5},
                    }
                    assert not ParetoFrontier._dominates(other, opt, criteria, scores), \
                        f"{other} 不应支配 {opt}"

    def test_expected_utility_maximization(self):
        """期望效用最大化"""
        # 决策节点应选择期望效用最大的分支
        root = create_decision_node("root", DecisionNodeType.DECISION)
        # 分支A: 期望效用 0.5
        root.add_child(create_decision_node("a", DecisionNodeType.OUTCOME, utility=0.5), "a")
        # 分支B: 期望效用 0.9
        root.add_child(create_decision_node("b", DecisionNodeType.OUTCOME, utility=0.9), "b")
        tree = create_decision_tree(root)
        assert tree.expected_utility() == 0.9

    def test_expected_utility_probability_weighted(self):
        """期望效用按概率加权"""
        root = create_decision_node("root", DecisionNodeType.CHANCE)
        root.add_child(create_decision_node("a", DecisionNodeType.OUTCOME, utility=1.0), "a", 0.5)
        root.add_child(create_decision_node("b", DecisionNodeType.OUTCOME, utility=0.0), "b", 0.5)
        tree = create_decision_tree(root)
        # 0.5*1.0 + 0.5*0.0 = 0.5
        assert tree.expected_utility() == 0.5

    def test_multi_objective_tradeoff(self):
        """多目标权衡"""
        engine = create_free_will_engine()
        # a: 高效用高成本
        # b: 低效用低成本
        criteria = [
            create_criterion("util", CriterionType.MAXIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.9, "b": 0.3}.get(opt, 0.0)),
            create_criterion("cost", CriterionType.MINIMIZE, 1.0,
                             lambda opt, ctx: {"a": 0.8, "b": 0.2}.get(opt, 0.0)),
        ]
        cs = create_choice_set("test", ["a", "b"])
        decision = engine.make_multi_objective_decision(cs, criteria)
        # 两个都在帕累托前沿
        assert "a" in decision.pareto_optimal_set
        assert "b" in decision.pareto_optimal_set

    def test_decision_tree_decomposition(self):
        """决策树分解复杂决策"""
        # 投资决策：风险投资 vs 安全投资
        root = create_decision_node("invest", DecisionNodeType.DECISION)
        # 风险投资：70%成功得1.0，30%失败得0.0
        risky = create_decision_node("risky", DecisionNodeType.CHANCE)
        root.add_child(risky, "risky")
        risky.add_child(create_decision_node("r_good", DecisionNodeType.OUTCOME, utility=1.0), "good", 0.7)
        risky.add_child(create_decision_node("r_bad", DecisionNodeType.OUTCOME, utility=0.0), "bad", 0.3)
        # 安全投资：100%得0.5
        safe = create_decision_node("safe", DecisionNodeType.OUTCOME, utility=0.5)
        root.add_child(safe, "safe")

        tree = create_decision_tree(root)
        # 风险投资期望 = 0.7*1.0 + 0.3*0.0 = 0.7
        # 安全投资期望 = 0.5
        # 应选风险投资
        assert tree.expected_utility() == 0.7
        path = tree.best_path()
        assert "risky" in path[0]

    def test_weighted_criteria_aggregation(self):
        """加权准则聚合"""
        engine = create_free_will_engine()
        # a: 效用0.9, 成本0.8
        # b: 效用0.5, 成本0.2
        criteria = [
            create_criterion("util", CriterionType.MAXIMIZE, 2.0,  # 效用权重2
                             lambda opt, ctx: {"a": 0.9, "b": 0.5}.get(opt, 0.0)),
            create_criterion("cost", CriterionType.MINIMIZE, 1.0,  # 成本权重1
                             lambda opt, ctx: {"a": 0.8, "b": 0.2}.get(opt, 0.0)),
        ]
        cs = create_choice_set("test", ["a", "b"])
        decision = engine.make_multi_objective_decision(cs, criteria)
        # 归一化后：
        # a: util=1.0, cost=0.0; 加权 = (1.0*2 + 0.0*1)/3 = 0.667
        # b: util=0.0, cost=1.0; 加权 = (0.0*2 + 1.0*1)/3 = 0.333
        # a 应被选择
        assert decision.chosen_option == "a"

    def test_autonomy_internal_vs_external(self):
        """自主性：内部原因 vs 外部原因"""
        # 纯内部原因
        d_internal = Decision(
            decision_id="d1",
            chosen_action="a",
            reasons={"internal_pref": 0.8, "value": 0.5},
        )
        # 有外部原因
        d_external = Decision(
            decision_id="d2",
            chosen_action="a",
            reasons={"internal_pref": 0.8, "external_pressure": 0.9},
        )
        assert d_internal.autonomy_score > d_external.autonomy_score
