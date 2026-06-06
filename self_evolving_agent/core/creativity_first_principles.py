"""
阶段80: 创造第一性原理化

第一性原理:
1. 组合产生新颖：没有全新创造，只有重新组合
2. 创造性行为基于已有知识的跨域迁移
3. 创新 = 旧元素的新组合

设计原则:
- Concept: 概念单元
- Combination: 组合
- CreativityFirstPrinciplesEngine: 创造引擎
- 支持概念重组、跨域类比、涌现发现
"""

import threading
import time
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum


class ConceptType(Enum):
    """概念类型"""
    PRIMITIVE = "primitive"        # 原始概念
    COMPOUND = "compound"          # 复合概念
    ANALOGY = "analogy"            # 类比概念
    EMERGENT = "emergent"          # 涌现概念


@dataclass
class Concept:
    """概念"""
    concept_id: str
    name: str
    concept_type: ConceptType
    domain: str
    properties: Dict[str, Any] = field(default_factory=dict)
    source_concepts: List[str] = field(default_factory=list)  # 来源概念ID
    novelty_score: float = 0.0      # 新颖度 [0,1]


@dataclass
class Combination:
    """组合"""
    combination_id: str
    concept_ids: List[str]
    result_concept: Optional[Concept] = None
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 创造第一性原理引擎
# ============================================================

class CreativityFirstPrinciplesEngine:
    """
    创造第一性原理引擎

    核心原则：创造性行为基于已有知识的组合

    第一性原理推导:
    1. 所有知识由基本概念构成
    2. 概念可以跨域组合
    3. 新组合产生新属性（涌现）
    4. 新颖度 = 组合的不常见程度
    5. 创造是搜索组合空间的过程
    """

    def __init__(self, engine_id: str = "creativity_engine"):
        self.engine_id = engine_id
        self._concepts: Dict[str, Concept] = {}
        self._combinations: List[Combination] = []
        self._combination_history: Set[Tuple[str, ...]] = set()
        self._lock = threading.RLock()
        self._cycle_count = 0

    def add_concept(
        self,
        concept_id: str,
        name: str,
        domain: str,
        concept_type: ConceptType = ConceptType.PRIMITIVE,
        properties: Dict[str, Any] = None,
    ) -> Concept:
        """添加概念"""
        concept = Concept(
            concept_id=concept_id,
            name=name,
            concept_type=concept_type,
            domain=domain,
            properties=properties or {},
        )
        with self._lock:
            self._concepts[concept_id] = concept
        return concept

    def combine(self, concept_ids: List[str]) -> Optional[Concept]:
        """
        组合概念

        第一性原理：组合产生新颖
        """
        with self._lock:
            concepts = [self._concepts.get(cid) for cid in concept_ids]
            if None in concepts:
                return None

            # 检查是否已尝试过此组合
            sorted_ids = tuple(sorted(concept_ids))
            if sorted_ids in self._combination_history:
                # 已尝试过，新颖度降低
                novelty = 0.1
            else:
                self._combination_history.add(sorted_ids)
                # 跨域组合更新颖
                domains = set(c.domain for c in concepts)
                novelty = 0.5 + 0.5 * (len(domains) - 1) / max(1, len(concepts))

            # 合并属性
            merged_props: Dict[str, Any] = {}
            for c in concepts:
                merged_props.update(c.properties)

            # 检测涌现属性（简单实现：不同域的概念组合产生新属性）
            domains = set(c.domain for c in concepts)
            if len(domains) > 1:
                merged_props["cross_domain"] = True
                merged_props["emergent"] = True

            result = Concept(
                concept_id=f"comb_{int(time.time() * 1000)}_{self._cycle_count}",
                name=" + ".join(c.name for c in concepts),
                concept_type=ConceptType.COMPOUND if len(domains) == 1 else ConceptType.EMERGENT,
                domain="/".join(sorted(domains)),
                properties=merged_props,
                source_concepts=list(concept_ids),
                novelty_score=min(1.0, novelty),
            )

            combination = Combination(
                combination_id=f"cmb_{int(time.time() * 1000)}",
                concept_ids=list(concept_ids),
                result_concept=result,
            )

            self._combinations.append(combination)
            self._concepts[result.concept_id] = result
            self._cycle_count += 1

            return result

    def find_analogy(self, source_domain: str, target_domain: str) -> List[Dict[str, Any]]:
        """
        寻找跨域类比

        第一性原理：不同域可能有相同结构
        """
        with self._lock:
            source_concepts = [c for c in self._concepts.values() if c.domain == source_domain]
            target_concepts = [c for c in self._concepts.values() if c.domain == target_domain]

        analogies = []
        for sc in source_concepts:
            for tc in target_concepts:
                # 简单类比：属性重叠度
                common_props = set(sc.properties.keys()) & set(tc.properties.keys())
                if len(common_props) > 0:
                    similarity = len(common_props) / max(len(sc.properties), len(tc.properties), 1)
                    if similarity > 0.3:
                        analogies.append({
                            "source": sc.concept_id,
                            "target": tc.concept_id,
                            "similarity": similarity,
                            "common_properties": list(common_props),
                        })

        analogies.sort(key=lambda x: x["similarity"], reverse=True)
        return analogies

    def generate_novel_combination(self, domain_filter: Optional[str] = None) -> Optional[Concept]:
        """
        生成新颖组合

        第一性原理：随机探索组合空间
        """
        with self._lock:
            candidates = list(self._concepts.values())
            if domain_filter:
                candidates = [c for c in candidates if c.domain == domain_filter]

        if len(candidates) < 2:
            return None

        # 优先选择跨域组合
        random.shuffle(candidates)
        selected = candidates[:2]
        return self.combine([c.concept_id for c in selected])

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            concepts = list(self._concepts.values())
            return {
                "engine_id": self.engine_id,
                "concepts_count": len(concepts),
                "combinations_count": len(self._combinations),
                "cycle_count": self._cycle_count,
                "avg_novelty": sum(c.novelty_score for c in concepts) / len(concepts) if concepts else 0,
                "emergent_concepts": sum(1 for c in concepts if c.concept_type == ConceptType.EMERGENT),
            }

    def clear(self) -> None:
        """清除"""
        with self._lock:
            self._concepts.clear()
            self._combinations.clear()
            self._combination_history.clear()
            self._cycle_count = 0


# ============================================================
# 便捷函数
# ============================================================

def create_creativity_engine(engine_id: str = "creativity_engine") -> CreativityFirstPrinciplesEngine:
    """创建创造引擎"""
    return CreativityFirstPrinciplesEngine(engine_id=engine_id)


def create_concept(
    concept_id: str,
    name: str,
    domain: str,
    properties: Dict[str, Any] = None,
) -> Concept:
    """创建概念"""
    return Concept(
        concept_id=concept_id,
        name=name,
        concept_type=ConceptType.PRIMITIVE,
        domain=domain,
        properties=properties or {},
    )
