"""
阶段118: 决策能力强化 — 多目标决策 + 决策树

第一性原理:
1. 决策归因于系统自身：系统对决策负责
2. 自由意志 = 在约束条件下的自主选择
3. 选择必须基于内部模型，而非外部指令
4. 多目标决策：现实决策通常有多个相互竞争的目标
5. 帕累托最优：没有方案能在所有目标上同时改进
6. 决策树：复杂决策可分解为层级子决策

强化内容:
- DecisionCriteria: 决策准则（最大化/最小化、权重）
- MultiObjectiveDecision: 多目标决策
- ParetoFrontier: 帕累托前沿（非支配解集）
- DecisionTreeNode / DecisionTree: 决策树
- ExpectedUtility: 期望效用计算

向后兼容: 保留原有 Decision / ChoiceSet / FreeWillFirstPrinciplesEngine 接口
"""

import threading
import time
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Set, Tuple
from enum import Enum


# ============================================================
# 基础枚举与数据结构（向后兼容）
# ============================================================

class DecisionSource(Enum):
    """决策来源"""
    INTERNAL = "internal"          # 内部驱动
    EXTERNAL = "external"          # 外部指令
    HYBRID = "hybrid"              # 混合


class CriterionType(Enum):
    """准则类型"""
    MAXIMIZE = "maximize"  # 最大化（如效用、收益）
    MINIMIZE = "minimize"  # 最小化（如成本、风险）


class DecisionNodeType(Enum):
    """决策节点类型"""
    DECISION = "decision"    # 决策节点（选择分支）
    CHANCE = "chance"        # 机会节点（概率分支）
    OUTCOME = "outcome"      # 结果节点（叶节点）


@dataclass
class Decision:
    """决策（向后兼容）"""
    decision_id: str
    chosen_action: str
    alternatives: List[str] = field(default_factory=list)
    reasons: Dict[str, float] = field(default_factory=dict)
    source: DecisionSource = DecisionSource.INTERNAL
    timestamp: float = field(default_factory=time.time)

    @property
    def autonomy_score(self) -> float:
        """自主性分数（向后兼容）"""
        if not self.reasons:
            return 0.5
        internal_weight = sum(w for k, w in self.reasons.items() if not k.startswith("external_"))
        total_weight = sum(abs(w) for w in self.reasons.values())
        if total_weight == 0:
            return 0.5
        return internal_weight / total_weight


@dataclass
class ChoiceSet:
    """选择集（向后兼容）"""
    choice_id: str
    options: List[str]
    constraints: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 阶段118新增：决策准则
# ============================================================

@dataclass
class DecisionCriterion:
    """
    决策准则

    第一性原理：每个准则代表一个决策维度
    - MAXIMIZE: 越大越好（效用、收益、安全性）
    - MINIMIZE: 越小越好（成本、风险、时间）
    """
    name: str
    criterion_type: CriterionType
    weight: float = 1.0  # 准则权重
    evaluator: Optional[Callable[[str, Dict[str, Any]], float]] = None

    def evaluate(self, option: str, context: Dict[str, Any]) -> float:
        """评估选项在该准则下的得分"""
        if self.evaluator is not None:
            try:
                raw = float(self.evaluator(option, context))
            except (TypeError, ValueError, ZeroDivisionError):
                raw = 0.0
        else:
            raw = 0.0

        # 防御 NaN/Inf
        if math.isnan(raw) or math.isinf(raw):
            raw = 0.0

        return raw

    def normalized_score(self, option: str, context: Dict[str, Any], min_val: float, max_val: float) -> float:
        """
        归一化得分到 [0, 1]

        第一性原理：不同准则的量纲不同，需归一化才能比较
        - MAXIMIZE: (val - min) / (max - min)
        - MINIMIZE: (max - val) / (max - min)
        """
        val = self.evaluate(option, context)
        if max_val == min_val:
            return 0.5  # 无差异

        if self.criterion_type == CriterionType.MAXIMIZE:
            score = (val - min_val) / (max_val - min_val)
        else:
            score = (max_val - val) / (max_val - min_val)

        return max(0.0, min(1.0, score))


# ============================================================
# 阶段118新增：多目标决策
# ============================================================

@dataclass
class MultiObjectiveDecision:
    """
    多目标决策

    第一性原理：
    - 现实决策有多个相互竞争的目标
    - 没有单一最优解，只有帕累托最优解集
    - 通过加权聚合或帕累托前沿选择
    """
    decision_id: str
    chosen_option: str
    pareto_optimal_set: List[str] = field(default_factory=list)
    criteria_scores: Dict[str, Dict[str, float]] = field(default_factory=dict)
    weighted_scores: Dict[str, float] = field(default_factory=dict)
    reasons: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def is_pareto_optimal_choice(self) -> bool:
        """选择是否在帕累托前沿上"""
        return self.chosen_option in self.pareto_optimal_set


# ============================================================
# 阶段118新增：帕累托前沿
# ============================================================

class ParetoFrontier:
    """
    帕累托前沿计算

    第一性原理：
    - 方案A支配方案B：A在所有准则上不差于B，且至少在一个准则上严格更好
    - 帕累托前沿：不被任何其他方案支配的方案集合
    """

    @staticmethod
    def compute(
        options: List[str],
        criteria: List[DecisionCriterion],
        context: Dict[str, Any],
    ) -> Tuple[List[str], Dict[str, Dict[str, float]]]:
        """
        计算帕累托前沿

        Returns:
            - pareto_set: 帕累托最优方案列表
            - scores: 每个方案在每个准则下的原始得分
        """
        if not options or not criteria:
            return [], {}

        # 计算每个方案在每个准则下的原始得分
        scores: Dict[str, Dict[str, float]] = {}
        for opt in options:
            scores[opt] = {}
            for criterion in criteria:
                scores[opt][criterion.name] = criterion.evaluate(opt, context)

        # 计算帕累托前沿
        pareto_set: List[str] = []
        for opt_a in options:
            dominated = False
            for opt_b in options:
                if opt_a == opt_b:
                    continue
                if ParetoFrontier._dominates(opt_b, opt_a, criteria, scores):
                    dominated = True
                    break
            if not dominated:
                pareto_set.append(opt_a)

        return pareto_set, scores

    @staticmethod
    def _dominates(
        opt_a: str,
        opt_b: str,
        criteria: List[DecisionCriterion],
        scores: Dict[str, Dict[str, float]],
    ) -> bool:
        """
        判断 opt_a 是否支配 opt_b

        第一性原理：A支配B 当且仅当
        - A在所有准则上不差于B
        - A至少在一个准则上严格好于B
        """
        at_least_one_strictly_better = False
        for criterion in criteria:
            val_a = scores[opt_a][criterion.name]
            val_b = scores[opt_b][criterion.name]

            if criterion.criterion_type == CriterionType.MAXIMIZE:
                if val_a < val_b:
                    return False
                if val_a > val_b:
                    at_least_one_strictly_better = True
            else:  # MINIMIZE
                if val_a > val_b:
                    return False
                if val_a < val_b:
                    at_least_one_strictly_better = True

        return at_least_one_strictly_better


# ============================================================
# 阶段118新增：决策树
# ============================================================

@dataclass
class DecisionTreeNode:
    """
    决策树节点

    第一性原理：复杂决策可分解为层级子决策
    - DECISION: 决策节点，选择一个分支
    - CHANCE: 机会节点，按概率分支
    - OUTCOME: 结果节点，叶节点，有效用值
    """
    node_id: str
    node_type: DecisionNodeType
    label: str = ""
    # 子节点及其连接信息
    children: List["DecisionTreeNode"] = field(default_factory=list)
    # 分支标签（与children一一对应）
    branch_labels: List[str] = field(default_factory=list)
    # 分支概率（仅CHANCE节点使用）
    branch_probabilities: List[float] = field(default_factory=list)
    # 效用值（仅OUTCOME节点使用）
    utility: float = 0.0
    # 上下文
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_child(
        self,
        child: "DecisionTreeNode",
        label: str = "",
        probability: Optional[float] = None,
    ) -> None:
        """添加子节点"""
        self.children.append(child)
        self.branch_labels.append(label)
        if probability is not None:
            self.branch_probabilities.append(probability)

    def is_leaf(self) -> bool:
        """是否叶节点"""
        return len(self.children) == 0


class DecisionTree:
    """
    决策树

    第一性原理：
    - 复杂决策分解为决策点（选择）和机会点（概率）
    - 通过期望效用最大化选择最优路径
    - E[U] = Σ p(outcome) × U(outcome)
    """

    def __init__(self, root: DecisionTreeNode):
        self._root = root
        self._lock = threading.RLock()

    def expected_utility(self, node: Optional[DecisionTreeNode] = None) -> float:
        """
        计算期望效用

        第一性原理：期望效用 = Σ p(outcome) × U(outcome)
        - DECISION节点：选择最大期望效用的分支
        - CHANCE节点：所有分支期望效用之和
        - OUTCOME节点：直接返回效用值
        """
        with self._lock:
            if node is None:
                node = self._root

            if node is None:
                return 0.0

            # 叶节点：返回效用
            if node.is_leaf():
                return node.utility

            # OUTCOME类型但非叶（防御）
            if node.node_type == DecisionNodeType.OUTCOME:
                return node.utility

            # CHANCE节点：期望效用 = Σ p × EU(child)
            if node.node_type == DecisionNodeType.CHANCE:
                total = 0.0
                for i, child in enumerate(node.children):
                    prob = node.branch_probabilities[i] if i < len(node.branch_probabilities) else 0.0
                    # 防御 NaN/Inf
                    if math.isnan(prob) or math.isinf(prob):
                        prob = 0.0
                    total += prob * self.expected_utility(child)
                return total

            # DECISION节点：选择最大期望效用的分支
            if node.node_type == DecisionNodeType.DECISION:
                if not node.children:
                    return node.utility
                return max(self.expected_utility(child) for child in node.children)

            return 0.0

    def best_path(self, node: Optional[DecisionTreeNode] = None) -> List[str]:
        """
        找到最优路径

        第一性原理：在每个决策点选择期望效用最大的分支
        """
        with self._lock:
            if node is None:
                node = self._root

            path: List[str] = []
            current = node

            while current is not None and not current.is_leaf():
                if current.node_type == DecisionNodeType.DECISION:
                    # 选择期望效用最大的子节点
                    best_child = None
                    best_eu = float("-inf")
                    best_label = ""
                    for i, child in enumerate(current.children):
                        eu = self.expected_utility(child)
                        if eu > best_eu:
                            best_eu = eu
                            best_child = child
                            best_label = current.branch_labels[i] if i < len(current.branch_labels) else ""
                    if best_child is None:
                        break
                    path.append(best_label or best_child.node_id)
                    current = best_child
                elif current.node_type == DecisionNodeType.CHANCE:
                    # 机会节点：记录所有可能分支
                    for i, child in enumerate(current.children):
                        label = current.branch_labels[i] if i < len(current.branch_labels) else ""
                        prob = current.branch_probabilities[i] if i < len(current.branch_probabilities) else 0.0
                        path.append(f"{label}(p={prob:.2f})")
                    # 机会节点不选择，展开所有分支
                    break
                else:
                    break

            return path

    def get_root(self) -> DecisionTreeNode:
        """获取根节点"""
        return self._root

    def count_nodes(self, node: Optional[DecisionTreeNode] = None) -> int:
        """统计节点数"""
        with self._lock:
            if node is None:
                node = self._root
            if node is None:
                return 0
            count = 1
            for child in node.children:
                count += self.count_nodes(child)
            return count

    def get_depth(self, node: Optional[DecisionTreeNode] = None) -> int:
        """获取树深度"""
        with self._lock:
            if node is None:
                node = self._root
            if node is None or node.is_leaf():
                return 1
            return 1 + max(self.get_depth(child) for child in node.children)


# ============================================================
# 自由意志第一性原理引擎（增强版）
# ============================================================

class FreeWillFirstPrinciplesEngine:
    """
    自由意志第一性原理引擎（阶段118增强版）

    新增能力:
    - 多目标决策（MultiObjectiveDecision）
    - 帕累托前沿计算（ParetoFrontier）
    - 决策树（DecisionTree）

    向后兼容: 保留原有 make_decision / evaluate_autonomy 接口
    """

    def __init__(self, engine_id: str = "free_will_engine"):
        self.engine_id = engine_id
        self._decisions: List[Decision] = []
        self._multi_objective_decisions: List[MultiObjectiveDecision] = []
        self._internal_model: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._cycle_count = 0
        # 阶段118新增：默认决策准则
        self._default_criteria: List[DecisionCriterion] = []

    # ============================================================
    # 原有接口（向后兼容）
    # ============================================================

    def update_internal_model(self, model: Dict[str, Any]) -> None:
        """更新内部模型"""
        with self._lock:
            self._internal_model.update(model)

    def make_decision(
        self,
        choice_set: ChoiceSet,
        value_function: Optional[Callable] = None,
    ) -> Decision:
        """做出决策（向后兼容）"""
        valid_options = [
            opt for opt in choice_set.options
            if not any(c in opt for c in choice_set.constraints)
        ]

        if not valid_options:
            valid_options = choice_set.options

        if not valid_options:
            decision = Decision(
                decision_id=f"dec_{int(time.time() * 1000)}_{self._cycle_count}",
                chosen_action="noop",
                alternatives=[],
                reasons={"empty_choice_set": True},
                source=DecisionSource.INTERNAL,
            )
            with self._lock:
                self._decisions.append(decision)
                self._cycle_count += 1
            return decision

        scores: Dict[str, float] = {}
        for opt in valid_options:
            if value_function:
                try:
                    scores[opt] = float(value_function(opt, choice_set.context))
                except (TypeError, ValueError, ZeroDivisionError):
                    scores[opt] = self._default_evaluate(opt, choice_set.context)
            else:
                scores[opt] = self._default_evaluate(opt, choice_set.context)

        chosen = max(scores, key=scores.get) if scores else valid_options[0]

        reasons = {f"value_{k}": v for k, v in scores.items()}
        reasons["internal_preference"] = scores.get(chosen, 0.0)

        source = DecisionSource.INTERNAL
        if choice_set.context.get("external_pressure", 0.0) > 0.7:
            source = DecisionSource.HYBRID
            reasons["external_pressure"] = choice_set.context["external_pressure"]

        decision = Decision(
            decision_id=f"dec_{int(time.time() * 1000)}_{self._cycle_count}",
            chosen_action=chosen,
            alternatives=[o for o in valid_options if o != chosen],
            reasons=reasons,
            source=source,
        )

        with self._lock:
            self._decisions.append(decision)
            self._cycle_count += 1

        return decision

    def _default_evaluate(self, option: str, context: Dict[str, Any]) -> float:
        """默认评估函数"""
        score = 0.0
        with self._lock:
            preferences = self._internal_model.get("preferences", {})
            for pref, weight in preferences.items():
                if pref in option:
                    score += weight

        if context.get("urgency", 0.0) > 0.5 and "fast" in option:
            score += 0.3

        return score

    def evaluate_autonomy(self, decision_id: str) -> float:
        """评估决策自主性"""
        with self._lock:
            for dec in self._decisions:
                if dec.decision_id == decision_id:
                    return dec.autonomy_score
        return 0.0

    def could_have_done_otherwise(self, decision_id: str) -> bool:
        """本可以做出其他选择"""
        with self._lock:
            for dec in self._decisions:
                if dec.decision_id == decision_id:
                    return len(dec.alternatives) > 0
        return False

    def trace_decision_to_internal_state(self, decision_id: str) -> Dict[str, Any]:
        """追溯决策到内部状态"""
        with self._lock:
            for dec in self._decisions:
                if dec.decision_id == decision_id:
                    return {
                        "decision": dec.chosen_action,
                        "reasons": dec.reasons,
                        "autonomy": dec.autonomy_score,
                        "internal_model_snapshot": dict(self._internal_model),
                    }
        return {}

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            base_stats = {
                "engine_id": self.engine_id,
                "decisions_count": len(self._decisions),
                "avg_autonomy": 0.0,
                "internal_sources": 0,
                "hybrid_sources": 0,
            }
            if self._decisions:
                base_stats["avg_autonomy"] = sum(d.autonomy_score for d in self._decisions) / len(self._decisions)
                base_stats["internal_sources"] = sum(1 for d in self._decisions if d.source == DecisionSource.INTERNAL)
                base_stats["hybrid_sources"] = sum(1 for d in self._decisions if d.source == DecisionSource.HYBRID)
            # 阶段118新增统计
            base_stats["multi_objective_decisions_count"] = len(self._multi_objective_decisions)
            return base_stats

    def reset(self) -> None:
        """重置"""
        with self._lock:
            self._decisions.clear()
            self._multi_objective_decisions.clear()
            self._internal_model.clear()
            self._cycle_count = 0

    # ============================================================
    # 阶段118新增：多目标决策接口
    # ============================================================

    def set_default_criteria(self, criteria: List[DecisionCriterion]) -> None:
        """设置默认决策准则"""
        with self._lock:
            self._default_criteria = list(criteria)

    def make_multi_objective_decision(
        self,
        choice_set: ChoiceSet,
        criteria: Optional[List[DecisionCriterion]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> MultiObjectiveDecision:
        """
        多目标决策

        第一性原理：
        1. 计算每个方案在每个准则下的得分
        2. 计算帕累托前沿
        3. 在帕累托前沿上按加权得分选择
        """
        if criteria is None:
            with self._lock:
                criteria = list(self._default_criteria)

        if context is None:
            context = choice_set.context

        # 应用约束过滤
        valid_options = [
            opt for opt in choice_set.options
            if not any(c in opt for c in choice_set.constraints)
        ]
        if not valid_options:
            valid_options = choice_set.options
        if not valid_options:
            # 空选项防御
            decision = MultiObjectiveDecision(
                decision_id=f"mod_{int(time.time() * 1000)}_{self._cycle_count}",
                chosen_option="noop",
                pareto_optimal_set=[],
                criteria_scores={},
                weighted_scores={},
                reasons={"empty_choice_set": True},
            )
            with self._lock:
                self._multi_objective_decisions.append(decision)
                self._cycle_count += 1
            return decision

        # 无准则时退化为默认评估
        if not criteria:
            scores = {opt: self._default_evaluate(opt, context) for opt in valid_options}
            chosen = max(scores, key=scores.get) if scores else valid_options[0]
            decision = MultiObjectiveDecision(
                decision_id=f"mod_{int(time.time() * 1000)}_{self._cycle_count}",
                chosen_option=chosen,
                pareto_optimal_set=valid_options,
                criteria_scores={"default": scores},
                weighted_scores=scores,
                reasons={"default_evaluation": scores.get(chosen, 0.0)},
            )
            with self._lock:
                self._multi_objective_decisions.append(decision)
                self._cycle_count += 1
            return decision

        # 计算帕累托前沿
        pareto_set, raw_scores = ParetoFrontier.compute(valid_options, criteria, context)

        # 归一化并加权
        weighted_scores: Dict[str, float] = {}
        criteria_scores: Dict[str, Dict[str, float]] = {}

        # 计算每个准则的min/max用于归一化
        for criterion in criteria:
            vals = [raw_scores[opt][criterion.name] for opt in valid_options]
            min_val = min(vals) if vals else 0.0
            max_val = max(vals) if vals else 0.0
            criteria_scores[criterion.name] = {}
            for opt in valid_options:
                norm_score = criterion.normalized_score(opt, context, min_val, max_val)
                criteria_scores[criterion.name][opt] = norm_score

        # 加权聚合
        total_weight = sum(c.weight for c in criteria)
        if total_weight == 0:
            total_weight = 1.0
        for opt in valid_options:
            weighted = sum(
                criteria_scores[c.name][opt] * c.weight
                for c in criteria
            ) / total_weight
            weighted_scores[opt] = weighted

        # 在帕累托前沿上选择加权得分最高的
        if pareto_set:
            chosen = max(pareto_set, key=lambda o: weighted_scores.get(o, 0.0))
        else:
            chosen = max(weighted_scores, key=weighted_scores.get) if weighted_scores else valid_options[0]

        reasons = {f"weighted_{opt}": score for opt, score in weighted_scores.items()}
        reasons["pareto_optimal"] = 1.0 if chosen in pareto_set else 0.0

        decision = MultiObjectiveDecision(
            decision_id=f"mod_{int(time.time() * 1000)}_{self._cycle_count}",
            chosen_option=chosen,
            pareto_optimal_set=pareto_set,
            criteria_scores=criteria_scores,
            weighted_scores=weighted_scores,
            reasons=reasons,
        )

        with self._lock:
            self._multi_objective_decisions.append(decision)
            self._cycle_count += 1

        return decision

    def evaluate_decision_tree(self, tree: DecisionTree) -> Dict[str, Any]:
        """
        评估决策树

        第一性原理：通过期望效用最大化选择最优路径
        """
        eu = tree.expected_utility()
        path = tree.best_path()
        return {
            "expected_utility": eu,
            "best_path": path,
            "node_count": tree.count_nodes(),
            "depth": tree.get_depth(),
        }

    def get_multi_objective_decisions(self) -> List[MultiObjectiveDecision]:
        """获取多目标决策历史"""
        with self._lock:
            return list(self._multi_objective_decisions)

    def get_pareto_frontier(
        self,
        options: List[str],
        criteria: List[DecisionCriterion],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[str], Dict[str, Dict[str, float]]]:
        """计算帕累托前沿"""
        return ParetoFrontier.compute(options, criteria, context or {})


# ============================================================
# 便捷函数（向后兼容 + 新增）
# ============================================================

def create_free_will_engine(engine_id: str = "free_will_engine") -> FreeWillFirstPrinciplesEngine:
    """创建自由意志引擎"""
    return FreeWillFirstPrinciplesEngine(engine_id=engine_id)


def create_choice_set(
    choice_id: str,
    options: List[str],
    constraints: List[str] = None,
    context: Dict[str, Any] = None,
) -> ChoiceSet:
    """创建选择集"""
    return ChoiceSet(
        choice_id=choice_id,
        options=options,
        constraints=constraints or [],
        context=context or {},
    )


def create_criterion(
    name: str,
    criterion_type: CriterionType = CriterionType.MAXIMIZE,
    weight: float = 1.0,
    evaluator: Optional[Callable[[str, Dict[str, Any]], float]] = None,
) -> DecisionCriterion:
    """创建决策准则"""
    return DecisionCriterion(
        name=name,
        criterion_type=criterion_type,
        weight=weight,
        evaluator=evaluator,
    )


def create_decision_node(
    node_id: str,
    node_type: DecisionNodeType = DecisionNodeType.DECISION,
    label: str = "",
    utility: float = 0.0,
) -> DecisionTreeNode:
    """创建决策树节点"""
    return DecisionTreeNode(
        node_id=node_id,
        node_type=node_type,
        label=label,
        utility=utility,
    )


def create_decision_tree(root: DecisionTreeNode) -> DecisionTree:
    """创建决策树"""
    return DecisionTree(root)
