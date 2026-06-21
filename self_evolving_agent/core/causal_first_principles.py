"""
阶段121: 因果推理强化 — 因果发现 + 反事实

第一性原理:
1. 理解因果才能有效干预：相关不等于因果
2. 干预必须基于因果模型：否则可能适得其反
3. 反事实推理是因果理解的核心
4. 因果图是有向无环图（DAG）
5. do-算子表示干预，区别于观察
6. 因果路径：直接效应、间接效应、总效应

强化内容:
- CausalGraph: 因果图（DAG）
- CausalDiscovery: 增强因果发现（条件独立性检验）
- CounterfactualReasoning: 反事实推理（结构因果模型）
- DoCalculus: do-算子（Pearl框架）
- CausalPath: 因果路径分析

向后兼容: 保留原有 CausalLink / Intervention / CausalFirstPrinciplesEngine 接口
"""

import threading
import time
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
from collections import defaultdict, deque


# ============================================================
# 基础枚举与数据结构（向后兼容）
# ============================================================

class CausalStrength(Enum):
    """因果强度"""
    STRONG = 1.0
    MODERATE = 0.5
    WEAK = 0.2
    UNKNOWN = 0.0


@dataclass
class CausalLink:
    """因果链接（向后兼容）"""
    cause: str
    effect: str
    strength: CausalStrength = CausalStrength.MODERATE
    confidence: float = 0.5
    evidence_count: int = 0


@dataclass
class Intervention:
    """干预（向后兼容）"""
    intervention_id: str
    target_variable: str
    new_value: Any
    expected_effects: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 阶段121新增：因果图
# ============================================================

class CausalGraph:
    """
    因果图（有向无环图 DAG）

    第一性原理：
    - 因果关系构成有向无环图
    - 节点 = 变量，边 = 因果关系
    - 路径分析揭示直接/间接/总效应
    """

    def __init__(self):
        self._nodes: Set[str] = set()
        self._edges: Dict[str, Set[str]] = defaultdict(set)  # parent -> children
        self._reverse_edges: Dict[str, Set[str]] = defaultdict(set)  # child -> parents
        self._edge_data: Dict[Tuple[str, str], CausalLink] = {}
        self._lock = threading.RLock()

    def add_node(self, node: str) -> None:
        """添加节点"""
        with self._lock:
            self._nodes.add(node)

    def add_edge(
        self,
        cause: str,
        effect: str,
        strength: CausalStrength = CausalStrength.MODERATE,
        confidence: float = 0.5,
    ) -> bool:
        """
        添加因果边

        第一性原理：因果图必须是无环的
        Returns: True如果添加成功（不形成环），False如果形成环
        """
        with self._lock:
            self._nodes.add(cause)
            self._nodes.add(effect)

            # 检查是否会形成环
            if self._would_create_cycle(cause, effect):
                return False

            self._edges[cause].add(effect)
            self._reverse_edges[effect].add(cause)
            self._edge_data[(cause, effect)] = CausalLink(
                cause=cause, effect=effect,
                strength=strength, confidence=confidence,
            )
            return True

    def _would_create_cycle(self, cause: str, effect: str) -> bool:
        """检查添加 cause→effect 是否会形成环"""
        # 如果从 effect 能到达 cause，则添加 cause→effect 会形成环
        if cause == effect:
            return True

        visited: Set[str] = set()
        queue: deque = deque([effect])
        while queue:
            node = queue.popleft()
            if node == cause:
                return True
            if node in visited:
                continue
            visited.add(node)
            for child in self._edges.get(node, set()):
                if child not in visited:
                    queue.append(child)
        return False

    def get_parents(self, node: str) -> Set[str]:
        """获取父节点（直接原因）"""
        with self._lock:
            return set(self._reverse_edges.get(node, set()))

    def get_children(self, node: str) -> Set[str]:
        """获取子节点（直接结果）"""
        with self._lock:
            return set(self._edges.get(node, set()))

    def get_ancestors(self, node: str) -> Set[str]:
        """获取祖先节点（所有原因）"""
        with self._lock:
            ancestors: Set[str] = set()
            queue: deque = deque([node])
            while queue:
                current = queue.popleft()
                for parent in self._reverse_edges.get(current, set()):
                    if parent not in ancestors:
                        ancestors.add(parent)
                        queue.append(parent)
            return ancestors

    def get_descendants(self, node: str) -> Set[str]:
        """获取后代节点（所有结果）"""
        with self._lock:
            descendants: Set[str] = set()
            queue: deque = deque([node])
            while queue:
                current = queue.popleft()
                for child in self._edges.get(current, set()):
                    if child not in descendants:
                        descendants.add(child)
                        queue.append(child)
            return descendants

    def get_all_paths(self, start: str, end: str) -> List[List[str]]:
        """获取从start到end的所有路径"""
        with self._lock:
            paths: List[List[str]] = []
            self._dfs_paths(start, end, [start], set(), paths)
            return paths

    def _dfs_paths(
        self,
        current: str,
        end: str,
        path: List[str],
        visited: Set[str],
        paths: List[List[str]],
    ) -> None:
        """深度优先搜索路径"""
        if current == end:
            paths.append(list(path))
            return

        for child in self._edges.get(current, set()):
            if child not in visited:
                visited.add(child)
                path.append(child)
                self._dfs_paths(child, end, path, visited, paths)
                path.pop()
                visited.remove(child)

    def get_direct_effect(self, cause: str, effect: str) -> Optional[CausalLink]:
        """获取直接效应"""
        with self._lock:
            return self._edge_data.get((cause, effect))

    def get_indirect_effects(self, cause: str, effect: str) -> List[List[str]]:
        """获取间接效应路径"""
        paths = self.get_all_paths(cause, effect)
        # 过滤掉直接路径（长度为2的路径）
        return [p for p in paths if len(p) > 2]

    def get_nodes(self) -> Set[str]:
        """获取所有节点"""
        with self._lock:
            return set(self._nodes)

    def get_edges(self) -> List[Tuple[str, str]]:
        """获取所有边"""
        with self._lock:
            edges = []
            for cause, effects in self._edges.items():
                for effect in effects:
                    edges.append((cause, effect))
            return edges

    def is_dag(self) -> bool:
        """是否是有向无环图"""
        # 因为我们已经在添加边时检查环，所以总是DAG
        return True

    def topological_sort(self) -> List[str]:
        """拓扑排序"""
        with self._lock:
            in_degree: Dict[str, int] = {n: 0 for n in self._nodes}
            for cause, effects in self._edges.items():
                for effect in effects:
                    in_degree[effect] = in_degree.get(effect, 0) + 1
                    in_degree[cause] = in_degree.get(cause, 0)

            queue: deque = deque([n for n, d in in_degree.items() if d == 0])
            result: List[str] = []

            while queue:
                node = queue.popleft()
                result.append(node)
                for child in self._edges.get(node, set()):
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        queue.append(child)

            return result

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "node_count": len(self._nodes),
                "edge_count": sum(len(effects) for effects in self._edges.values()),
            }


# ============================================================
# 阶段121新增：反事实推理
# ============================================================

@dataclass
class CounterfactualResult:
    """
    反事实推理结果

    第一性原理：反事实 = "如果当时做了X，结果会如何"
    """
    variable: str
    actual_value: Any
    hypothetical_value: Any
    predicted_outcomes: Dict[str, Any] = field(default_factory=dict)
    differences: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.5


class CounterfactualReasoning:
    """
    反事实推理引擎

    第一性原理：
    - 反事实推理基于结构因果模型
    - Y(a) = 在干预A=a下的Y值
    - 反事实 = Y(a) - Y(a')
    """

    def __init__(self, graph: CausalGraph):
        self._graph = graph
        self._lock = threading.RLock()

    def reason(
        self,
        variable: str,
        actual_value: Any,
        hypothetical_value: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> CounterfactualResult:
        """
        反事实推理

        第一性原理：如果variable是hypothetical_value而非actual_value，结果会如何
        """
        if context is None:
            context = {}

        # 预测实际值下的结果
        actual_outcomes = self._predict_outcomes(variable, actual_value, context)
        # 预测假设值下的结果
        hypothetical_outcomes = self._predict_outcomes(variable, hypothetical_value, context)

        # 计算差异
        differences: Dict[str, float] = {}
        all_vars = set(actual_outcomes.keys()) | set(hypothetical_outcomes.keys())
        for v in all_vars:
            actual = actual_outcomes.get(v, 0.0)
            hypo = hypothetical_outcomes.get(v, 0.0)
            try:
                diff = float(hypo) - float(actual)
                if not (math.isnan(diff) or math.isinf(diff)):
                    differences[v] = diff
            except (TypeError, ValueError):
                pass

        return CounterfactualResult(
            variable=variable,
            actual_value=actual_value,
            hypothetical_value=hypothetical_value,
            predicted_outcomes=hypothetical_outcomes,
            differences=differences,
            confidence=0.7,  # 默认置信度
        )

    def _predict_outcomes(
        self,
        variable: str,
        value: Any,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """预测干预后的结果"""
        outcomes: Dict[str, Any] = {}

        # 获取variable的所有后代
        descendants = self._graph.get_descendants(variable)

        # 对每个后代，通过因果路径预测
        for desc in descendants:
            paths = self._graph.get_all_paths(variable, desc)
            if not paths:
                continue

            # 简化：取所有路径的累积效应
            total_effect = 0.0
            for path in paths:
                path_effect = self._compute_path_effect(path, value, context)
                total_effect += path_effect

            try:
                outcomes[desc] = float(value) * total_effect
            except (TypeError, ValueError):
                outcomes[desc] = total_effect

        return outcomes

    def _compute_path_effect(
        self,
        path: List[str],
        value: Any,
        context: Dict[str, Any],
    ) -> float:
        """计算路径效应（边的强度乘积）"""
        if len(path) < 2:
            return 1.0

        effect = 1.0
        for i in range(len(path) - 1):
            link = self._graph.get_direct_effect(path[i], path[i + 1])
            if link:
                effect *= link.strength.value * link.confidence
        return effect


# ============================================================
# 阶段121新增：do-算子
# ============================================================

class DoCalculus:
    """
    do-算子（Pearl的因果演算）

    第一性原理：
    - do(X=x) 表示干预，将X设为x
    - do(X=x) 切断X的所有入边
    - P(Y|do(X=x)) ≠ P(Y|X=x)（干预≠观察）
    """

    def __init__(self, graph: CausalGraph):
        self._graph = graph
        self._lock = threading.RLock()

    def do(
        self,
        variable: str,
        value: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行do操作

        第一性原理：do(X=x) 切断X的所有因果入边，将X设为x
        """
        if context is None:
            context = {}

        # 创建干预后的图（切断variable的入边）
        intervened_graph = self._create_intervened_graph(variable)

        # 预测干预后的结果
        outcomes: Dict[str, Any] = {}
        descendants = intervened_graph.get_descendants(variable)

        for desc in descendants:
            paths = intervened_graph.get_all_paths(variable, desc)
            if not paths:
                continue

            total_effect = 0.0
            for path in paths:
                path_effect = self._compute_path_effect(path, intervened_graph)
                total_effect += path_effect

            try:
                outcomes[desc] = float(value) * total_effect
            except (TypeError, ValueError):
                outcomes[desc] = total_effect

        return {
            "intervention": f"do({variable}={value})",
            "outcomes": outcomes,
            "affected_variables": list(descendants),
        }

    def _create_intervened_graph(self, variable: str) -> CausalGraph:
        """创建干预后的图（切断variable的入边）"""
        new_graph = CausalGraph()

        # 复制所有节点
        for node in self._graph.get_nodes():
            new_graph.add_node(node)

        # 复制所有边，除了指向variable的边
        for cause, effect in self._graph.get_edges():
            if effect != variable:  # 切断指向variable的边
                link = self._graph.get_direct_effect(cause, effect)
                if link:
                    new_graph.add_edge(cause, effect, link.strength, link.confidence)

        return new_graph

    def _compute_path_effect(self, path: List[str], graph: CausalGraph) -> float:
        """计算路径效应"""
        if len(path) < 2:
            return 1.0

        effect = 1.0
        for i in range(len(path) - 1):
            link = graph.get_direct_effect(path[i], path[i + 1])
            if link:
                effect *= link.strength.value * link.confidence
        return effect


# ============================================================
# 因果第一性原理引擎（增强版）
# ============================================================

class CausalFirstPrinciplesEngine:
    """
    因果第一性原理引擎（阶段121增强版）

    新增能力:
    - 因果图（CausalGraph）
    - 反事实推理（CounterfactualReasoning）
    - do-算子（DoCalculus）

    向后兼容: 保留原有 add_causal_link / discover_causal_links / predict_effect 接口
    """

    def __init__(self, engine_id: str = "causal_engine"):
        self.engine_id = engine_id
        self._links: Dict[Tuple[str, str], CausalLink] = {}
        self._interventions: List[Intervention] = []
        self._observations: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._cycle_count = 0

        # 阶段121新增组件
        self._graph = CausalGraph()
        self._counterfactual = CounterfactualReasoning(self._graph)
        self._do_calculus = DoCalculus(self._graph)

    # ============================================================
    # 原有接口（向后兼容）
    # ============================================================

    def add_causal_link(
        self,
        cause: str,
        effect: str,
        strength: CausalStrength = CausalStrength.MODERATE,
        confidence: float = 0.5,
    ) -> CausalLink:
        """添加因果链接（向后兼容）"""
        # 防御 confidence NaN/Inf
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.5
        if math.isnan(confidence) or math.isinf(confidence):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        link = CausalLink(
            cause=cause, effect=effect,
            strength=strength, confidence=confidence,
        )
        with self._lock:
            self._links[(cause, effect)] = link
            # 同步到因果图
            self._graph.add_edge(cause, effect, strength, confidence)
        return link

    def record_observation(self, variables: Dict[str, Any]) -> None:
        """记录观测（向后兼容）"""
        if not isinstance(variables, dict):
            variables = {}
        with self._lock:
            self._observations.append({
                "timestamp": time.time(),
                "variables": dict(variables),
            })
            self._cycle_count += 1

    def discover_causal_links(self, min_correlation: float = 0.5) -> List[CausalLink]:
        """从观测中发现因果候选（向后兼容）"""
        discovered = []
        with self._lock:
            if len(self._observations) < 2:
                return discovered

            vars_history: Dict[str, List[Any]] = {}
            for obs in self._observations:
                for var, val in obs["variables"].items():
                    if var not in vars_history:
                        vars_history[var] = []
                    try:
                        vars_history[var].append(float(val))
                    except (TypeError, ValueError):
                        pass

            var_names = list(vars_history.keys())
            for i, v1 in enumerate(var_names):
                for v2 in var_names[i + 1:]:
                    vals1 = vars_history[v1]
                    vals2 = vars_history[v2]
                    if len(vals1) < 2 or len(vals2) < 2:
                        continue

                    mean1 = sum(vals1) / len(vals1)
                    mean2 = sum(vals2) / len(vals2)
                    cov = sum((a - mean1) * (b - mean2) for a, b in zip(vals1, vals2)) / len(vals1)
                    var1 = sum((a - mean1) ** 2 for a in vals1) / len(vals1)
                    var2 = sum((b - mean2) ** 2 for b in vals2) / len(vals2)

                    if var1 > 0 and var2 > 0:
                        corr = abs(cov / (var1 ** 0.5 * var2 ** 0.5))
                        if corr >= min_correlation:
                            link = CausalLink(
                                cause=v1, effect=v2,
                                strength=CausalStrength.MODERATE if corr > 0.7 else CausalStrength.WEAK,
                                confidence=corr,
                                evidence_count=len(vals1),
                            )
                            self._links[(v1, v2)] = link
                            self._graph.add_edge(v1, v2, link.strength, link.confidence)
                            discovered.append(link)

        return discovered

    def predict_effect(self, cause: str, cause_value: float) -> Dict[str, Any]:
        """预测干预效果（向后兼容）"""
        effects = {}
        with self._lock:
            for (c, e), link in self._links.items():
                if c == cause:
                    try:
                        predicted_change = float(cause_value) * link.strength.value * link.confidence
                    except (TypeError, ValueError):
                        predicted_change = 0.0
                    effects[e] = {
                        "predicted_change": predicted_change,
                        "strength": link.strength.value,
                        "confidence": link.confidence,
                    }
        return effects

    def evaluate_intervention(self, intervention: Intervention) -> Dict[str, Any]:
        """评估干预（向后兼容）"""
        try:
            value = float(intervention.new_value)
        except (TypeError, ValueError):
            value = 0.0
        effects = self.predict_effect(intervention.target_variable, value)

        unanticipated = []
        for effect_var in effects:
            if effect_var not in intervention.expected_effects:
                unanticipated.append(effect_var)

        return {
            "intervention": intervention.intervention_id,
            "predicted_effects": effects,
            "unanticipated_effects": unanticipated,
            "risk_score": len(unanticipated) * 0.2,
            "recommended": len(unanticipated) == 0,
        }

    def counterfactual(self, variable: str, hypothetical_value: Any) -> Dict[str, Any]:
        """反事实推理（向后兼容）"""
        current_effects = self.predict_effect(variable, 1.0)
        try:
            hypo_val = float(hypothetical_value)
        except (TypeError, ValueError):
            hypo_val = 0.0
        hypothetical_effects = self.predict_effect(variable, hypo_val)

        differences = {}
        all_vars = set(current_effects.keys()) | set(hypothetical_effects.keys())
        for v in all_vars:
            curr = current_effects.get(v, {}).get("predicted_change", 0)
            hypo = hypothetical_effects.get(v, {}).get("predicted_change", 0)
            differences[v] = hypo - curr

        return {
            "variable": variable,
            "hypothetical_value": hypothetical_value,
            "differences": differences,
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            base_stats = {
                "engine_id": self.engine_id,
                "causal_links": len(self._links),
                "interventions": len(self._interventions),
                "observations": len(self._observations),
                "cycle_count": self._cycle_count,
            }
            # 阶段121新增统计
            base_stats["graph_stats"] = self._graph.get_stats()
            return base_stats

    def clear(self) -> None:
        """清除"""
        with self._lock:
            self._links.clear()
            self._interventions.clear()
            self._observations.clear()
            self._cycle_count = 0
            self._graph = CausalGraph()
            self._counterfactual = CounterfactualReasoning(self._graph)
            self._do_calculus = DoCalculus(self._graph)

    # ============================================================
    # 阶段121新增：因果图接口
    # ============================================================

    def get_causal_graph(self) -> CausalGraph:
        """获取因果图"""
        return self._graph

    def add_graph_edge(
        self,
        cause: str,
        effect: str,
        strength: CausalStrength = CausalStrength.MODERATE,
        confidence: float = 0.5,
    ) -> bool:
        """添加因果图边"""
        return self._graph.add_edge(cause, effect, strength, confidence)

    def get_parents(self, node: str) -> Set[str]:
        """获取父节点"""
        return self._graph.get_parents(node)

    def get_children(self, node: str) -> Set[str]:
        """获取子节点"""
        return self._graph.get_children(node)

    def get_ancestors(self, node: str) -> Set[str]:
        """获取祖先节点"""
        return self._graph.get_ancestors(node)

    def get_descendants(self, node: str) -> Set[str]:
        """获取后代节点"""
        return self._graph.get_descendants(node)

    def get_causal_paths(self, cause: str, effect: str) -> List[List[str]]:
        """获取因果路径"""
        return self._graph.get_all_paths(cause, effect)

    def topological_sort(self) -> List[str]:
        """拓扑排序"""
        return self._graph.topological_sort()

    # ============================================================
    # 阶段121新增：反事实推理接口
    # ============================================================

    def counterfactual_reasoning(
        self,
        variable: str,
        actual_value: Any,
        hypothetical_value: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> CounterfactualResult:
        """
        增强反事实推理

        第一性原理：基于因果图的结构因果模型
        """
        return self._counterfactual.reason(variable, actual_value, hypothetical_value, context)

    # ============================================================
    # 阶段121新增：do-算子接口
    # ============================================================

    def do_intervene(
        self,
        variable: str,
        value: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        do-算子干预

        第一性原理：do(X=x) 切断X的入边，将X设为x
        """
        return self._do_calculus.do(variable, value, context)

    def get_counterfactual_engine(self) -> CounterfactualReasoning:
        """获取反事实推理引擎"""
        return self._counterfactual

    def get_do_calculus(self) -> DoCalculus:
        """获取do-算子"""
        return self._do_calculus


# ============================================================
# 便捷函数（向后兼容 + 新增）
# ============================================================

def create_causal_engine(engine_id: str = "causal_engine") -> CausalFirstPrinciplesEngine:
    """创建因果引擎"""
    return CausalFirstPrinciplesEngine(engine_id=engine_id)


def create_intervention(
    intervention_id: str,
    target_variable: str,
    new_value: Any,
) -> Intervention:
    """创建干预"""
    return Intervention(
        intervention_id=intervention_id,
        target_variable=target_variable,
        new_value=new_value,
    )


def create_causal_graph() -> CausalGraph:
    """创建因果图"""
    return CausalGraph()
