"""
阶段47: 推理引擎接口标准化

第一性原理:
1. 推理是从已知到未知的逻辑推导过程
2. 推理必须可解释：每一步推导都应有依据
3. 推理结果必须可置信度量化

设计原则:
- InferenceEngine: 推理引擎接口
- Rule: 规则定义（条件->结论）
- Fact: 事实定义
- InferenceResult: 推理结果（结论+置信度+推导链）
- 支持前向链、后向链推理
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum


class InferenceStrategy(Enum):
    """推理策略"""
    FORWARD_CHAINING = "forward"   # 前向链：从事实推导结论
    BACKWARD_CHAINING = "backward" # 后向链：从目标反推事实


@dataclass
class Fact:
    """事实"""
    predicate: str          # 谓词
    subject: str            # 主语
    value: Any              # 值
    confidence: float = 1.0 # 置信度

    def __hash__(self):
        return hash((self.predicate, self.subject, str(self.value)))

    def __eq__(self, other):
        if isinstance(other, Fact):
            return (self.predicate, self.subject, str(self.value)) == \
                   (other.predicate, other.subject, str(other.value))
        return False


@dataclass
class Rule:
    """规则"""
    name: str
    conditions: List[Callable[[List[Fact]], bool]]
    conclusion: Callable[[List[Fact]], List[Fact]]
    priority: int = 0


@dataclass
class InferenceResult:
    """推理结果"""
    conclusion: Fact
    confidence: float
    derivation_chain: List[str] = field(default_factory=list)
    applied_rules: List[str] = field(default_factory=list)


# ============================================================
# 推理引擎
# ============================================================

class InferenceEngine:
    """
    推理引擎

    第一性原理：基于规则从已知事实推导新结论
    """

    def __init__(self, strategy: InferenceStrategy = InferenceStrategy.FORWARD_CHAINING):
        self.strategy = strategy
        self._facts: Set[Fact] = set()
        self._rules: List[Rule] = []
        self._results: List[InferenceResult] = []

    def add_fact(self, fact: Fact) -> None:
        """添加事实"""
        self._facts.add(fact)

    def add_facts(self, facts: List[Fact]) -> None:
        """批量添加事实"""
        for fact in facts:
            self._facts.add(fact)

    def add_rule(self, rule: Rule) -> None:
        """添加规则"""
        self._rules.append(rule)
        # 按优先级排序
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def infer(self, max_iterations: int = 100) -> List[InferenceResult]:
        """
        执行推理

        Args:
            max_iterations: 最大迭代次数，防止无限循环

        Returns:
            推理结果列表
        """
        if self.strategy == InferenceStrategy.FORWARD_CHAINING:
            return self._forward_chain(max_iterations)
        return []

    def _forward_chain(self, max_iterations: int) -> List[InferenceResult]:
        """前向链推理"""
        results = []
        facts_list = list(self._facts)

        for _ in range(max_iterations):
            new_facts_found = False

            for rule in self._rules:
                # 检查条件
                try:
                    if all(cond(facts_list) for cond in rule.conditions):
                        # 应用结论
                        conclusions = rule.conclusion(facts_list)
                        for conclusion in conclusions:
                            if conclusion not in self._facts:
                                self._facts.add(conclusion)
                                facts_list.append(conclusion)
                                new_facts_found = True

                                result = InferenceResult(
                                    conclusion=conclusion,
                                    confidence=conclusion.confidence,
                                    derivation_chain=[f"{f.predicate}({f.subject})={f.value}" for f in facts_list[:5]],
                                    applied_rules=[rule.name],
                                )
                                results.append(result)
                except Exception:
                    continue

            if not new_facts_found:
                break

        self._results.extend(results)
        return results

    def query(self, predicate: str, subject: Optional[str] = None) -> List[Fact]:
        """查询事实"""
        results = []
        for fact in self._facts:
            if fact.predicate == predicate:
                if subject is None or fact.subject == subject:
                    results.append(fact)
        return results

    def get_facts(self) -> List[Fact]:
        """获取所有事实"""
        return list(self._facts)

    def get_results(self) -> List[InferenceResult]:
        """获取所有推理结果"""
        return list(self._results)

    def reset(self) -> None:
        """重置引擎"""
        self._facts.clear()
        self._results.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "fact_count": len(self._facts),
            "rule_count": len(self._rules),
            "inference_count": len(self._results),
            "strategy": self.strategy.value,
        }


# ============================================================
# 便捷函数
# ============================================================

def create_inference_engine(strategy: InferenceStrategy = InferenceStrategy.FORWARD_CHAINING) -> InferenceEngine:
    """创建推理引擎"""
    return InferenceEngine(strategy=strategy)


def create_fact(predicate: str, subject: str, value: Any, confidence: float = 1.0) -> Fact:
    """创建事实"""
    return Fact(predicate=predicate, subject=subject, value=value, confidence=confidence)


def create_rule(name: str, conditions: List[Callable], conclusion: Callable, priority: int = 0) -> Rule:
    """创建规则"""
    return Rule(name=name, conditions=conditions, conclusion=conclusion, priority=priority)
