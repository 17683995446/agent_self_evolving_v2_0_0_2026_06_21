"""
阶段46: 知识图谱接口标准化

第一性原理:
1. 知识是实体和关系的网络。实体是节点，关系是边
2. 知识必须可查询、可推理、可扩展
3. 图谱是动态演化的：新实体加入、关系更新、旧知识淘汰

设计原则:
- Entity: 实体（节点）
- Relation: 关系（边）
- KnowledgeGraph: 图存储和查询
- 支持三元组查询、路径查询、相似度查询
- 支持知识推理（传递闭包等）
"""

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum


class RelationType(Enum):
    """关系类型"""
    IS_A = "is_a"              # 继承
    PART_OF = "part_of"        # 组成
    RELATED_TO = "related_to"  # 相关
    CAUSES = "causes"          # 因果
    DEPENDS_ON = "depends_on"  # 依赖
    CUSTOM = "custom"          # 自定义


@dataclass
class Entity:
    """实体（节点）"""
    entity_id: str
    entity_type: str
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.entity_id)

    def __eq__(self, other):
        if isinstance(other, Entity):
            return self.entity_id == other.entity_id
        return False


@dataclass
class Relation:
    """关系（边）"""
    source_id: str
    target_id: str
    relation_type: RelationType
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0  # 置信度 0-1


# ============================================================
# 知识图谱
# ============================================================

class KnowledgeGraph:
    """
    知识图谱

    第一性原理：知识以图结构存储，查询即遍历
    """

    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        self._relations: Dict[str, List[Relation]] = {}  # source_id -> relations
        self._lock = threading.Lock()

    def add_entity(self, entity: Entity) -> bool:
        """添加实体"""
        with self._lock:
            self._entities[entity.entity_id] = entity
            return True

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        with self._lock:
            return self._entities.get(entity_id)

    def remove_entity(self, entity_id: str) -> bool:
        """移除实体及其关系"""
        with self._lock:
            if entity_id not in self._entities:
                return False
            del self._entities[entity_id]
            # 移除以该实体为源的关系
            if entity_id in self._relations:
                del self._relations[entity_id]
            # 移除以该实体为目标的关系
            for source_id, rels in list(self._relations.items()):
                self._relations[source_id] = [
                    r for r in rels if r.target_id != entity_id
                ]
            return True

    def add_relation(self, relation: Relation) -> bool:
        """添加关系"""
        with self._lock:
            if relation.source_id not in self._entities:
                return False
            if relation.target_id not in self._entities:
                return False
            if relation.source_id not in self._relations:
                self._relations[relation.source_id] = []
            self._relations[relation.source_id].append(relation)
            return True

    def get_relations(self, entity_id: str, relation_type: Optional[RelationType] = None) -> List[Relation]:
        """获取实体的出边关系"""
        with self._lock:
            rels = self._relations.get(entity_id, [])
            if relation_type:
                return [r for r in rels if r.relation_type == relation_type]
            return list(rels)

    def get_neighbors(self, entity_id: str, relation_type: Optional[RelationType] = None) -> List[Entity]:
        """获取邻居实体"""
        rels = self.get_relations(entity_id, relation_type)
        with self._lock:
            return [
                self._entities[r.target_id]
                for r in rels
                if r.target_id in self._entities
            ]

    def query_triple(self, subject: Optional[str] = None, predicate: Optional[RelationType] = None, obj: Optional[str] = None) -> List[Tuple[str, RelationType, str]]:
        """
        三元组查询

        支持部分匹配：None表示通配符
        """
        results = []
        with self._lock:
            for source_id, rels in self._relations.items():
                if subject and source_id != subject:
                    continue
                for rel in rels:
                    if predicate and rel.relation_type != predicate:
                        continue
                    if obj and rel.target_id != obj:
                        continue
                    results.append((source_id, rel.relation_type, rel.target_id))
        return results

    def find_path(self, start_id: str, end_id: str, max_depth: int = 5) -> Optional[List[Relation]]:
        """
        查找两点之间的路径（BFS）
        """
        if start_id == end_id:
            return []

        visited = {start_id}
        queue = [(start_id, [])]

        with self._lock:
            while queue:
                current_id, path = queue.pop(0)
                if len(path) >= max_depth:
                    continue

                for rel in self._relations.get(current_id, []):
                    next_id = rel.target_id
                    new_path = path + [rel]

                    if next_id == end_id:
                        return new_path

                    if next_id not in visited:
                        visited.add(next_id)
                        queue.append((next_id, new_path))

        return None

    def get_related_entities(self, entity_id: str, max_depth: int = 2) -> Set[str]:
        """获取关联实体（传递闭包）"""
        related = set()
        visited = {entity_id}
        current_level = {entity_id}

        with self._lock:
            for _ in range(max_depth):
                next_level = set()
                for eid in current_level:
                    for rel in self._relations.get(eid, []):
                        if rel.target_id not in visited:
                            visited.add(rel.target_id)
                            next_level.add(rel.target_id)
                            related.add(rel.target_id)
                current_level = next_level
                if not current_level:
                    break

        return related

    def infer_relation(self, entity_a: str, entity_b: str) -> List[RelationType]:
        """
        推理两个实体之间可能存在的关系

        基于共同邻居
        """
        neighbors_a = self.get_related_entities(entity_a, max_depth=1)
        neighbors_b = self.get_related_entities(entity_b, max_depth=1)
        common = neighbors_a & neighbors_b

        inferred = []
        # 如果有共同邻居，可能存在 RELATED_TO 关系
        if common:
            inferred.append(RelationType.RELATED_TO)

        return inferred

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total_relations = sum(len(rels) for rels in self._relations.values())
            return {
                "entity_count": len(self._entities),
                "relation_count": total_relations,
                "entity_types": list(set(e.entity_type for e in self._entities.values())),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_knowledge_graph() -> KnowledgeGraph:
    """创建知识图谱"""
    return KnowledgeGraph()


def create_entity(entity_id: str, entity_type: str, name: str, **properties) -> Entity:
    """创建实体"""
    return Entity(
        entity_id=entity_id,
        entity_type=entity_type,
        name=name,
        properties=properties,
    )


def create_relation(source_id: str, target_id: str, relation_type: RelationType, confidence: float = 1.0, **properties) -> Relation:
    """创建关系"""
    return Relation(
        source_id=source_id,
        target_id=target_id,
        relation_type=relation_type,
        confidence=confidence,
        properties=properties,
    )
