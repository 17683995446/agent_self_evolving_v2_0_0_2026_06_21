"""
阶段46测试: 知识图谱接口标准化
"""
import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.knowledge_graph import (
    KnowledgeGraph, Entity, Relation, RelationType,
    create_knowledge_graph, create_entity, create_relation
)


def test_add_entity():
    """测试添加实体"""
    kg = create_knowledge_graph()
    entity = create_entity("e1", "person", "Alice", age=30)

    assert kg.add_entity(entity) is True
    assert kg.get_entity("e1").name == "Alice"
    assert kg.get_entity("e1").properties["age"] == 30
    print("  [test_add_entity] 添加实体 ✓")


def test_add_relation():
    """测试添加关系"""
    kg = create_knowledge_graph()
    kg.add_entity(create_entity("e1", "person", "Alice"))
    kg.add_entity(create_entity("e2", "person", "Bob"))

    rel = create_relation("e1", "e2", RelationType.RELATED_TO)
    assert kg.add_relation(rel) is True

    rels = kg.get_relations("e1")
    assert len(rels) == 1
    assert rels[0].target_id == "e2"
    print("  [test_add_relation] 添加关系 ✓")


def test_query_triple():
    """测试三元组查询"""
    kg = create_knowledge_graph()
    kg.add_entity(create_entity("e1", "person", "Alice"))
    kg.add_entity(create_entity("e2", "person", "Bob"))
    kg.add_entity(create_entity("e3", "person", "Charlie"))

    kg.add_relation(create_relation("e1", "e2", RelationType.RELATED_TO))
    kg.add_relation(create_relation("e1", "e3", RelationType.RELATED_TO))
    kg.add_relation(create_relation("e2", "e3", RelationType.DEPENDS_ON))

    # 查询所有 RELATED_TO
    results = kg.query_triple(predicate=RelationType.RELATED_TO)
    assert len(results) == 2

    # 查询 e1 的所有关系
    results = kg.query_triple(subject="e1")
    assert len(results) == 2

    # 查询指向 e3 的关系
    results = kg.query_triple(obj="e3")
    assert len(results) == 2
    print("  [test_query_triple] 三元组查询 ✓")


def test_find_path():
    """测试路径查找"""
    kg = create_knowledge_graph()
    kg.add_entity(create_entity("a", "node", "A"))
    kg.add_entity(create_entity("b", "node", "B"))
    kg.add_entity(create_entity("c", "node", "C"))
    kg.add_entity(create_entity("d", "node", "D"))

    kg.add_relation(create_relation("a", "b", RelationType.RELATED_TO))
    kg.add_relation(create_relation("b", "c", RelationType.RELATED_TO))
    kg.add_relation(create_relation("c", "d", RelationType.RELATED_TO))

    path = kg.find_path("a", "d")
    assert path is not None
    assert len(path) == 3

    # 不存在路径
    no_path = kg.find_path("a", "z")
    assert no_path is None
    print("  [test_find_path] 路径查找 ✓")


def test_get_neighbors():
    """测试获取邻居"""
    kg = create_knowledge_graph()
    kg.add_entity(create_entity("a", "node", "A"))
    kg.add_entity(create_entity("b", "node", "B"))
    kg.add_entity(create_entity("c", "node", "C"))

    kg.add_relation(create_relation("a", "b", RelationType.RELATED_TO))
    kg.add_relation(create_relation("a", "c", RelationType.DEPENDS_ON))

    neighbors = kg.get_neighbors("a")
    assert len(neighbors) == 2

    related = kg.get_neighbors("a", RelationType.RELATED_TO)
    assert len(related) == 1
    assert related[0].entity_id == "b"
    print("  [test_get_neighbors] 获取邻居 ✓")


def test_get_related_entities():
    """测试关联实体查询"""
    kg = create_knowledge_graph()
    kg.add_entity(create_entity("a", "node", "A"))
    kg.add_entity(create_entity("b", "node", "B"))
    kg.add_entity(create_entity("c", "node", "C"))
    kg.add_entity(create_entity("d", "node", "D"))

    kg.add_relation(create_relation("a", "b", RelationType.RELATED_TO))
    kg.add_relation(create_relation("b", "c", RelationType.RELATED_TO))
    kg.add_relation(create_relation("c", "d", RelationType.RELATED_TO))

    related = kg.get_related_entities("a", max_depth=2)
    assert "b" in related
    assert "c" in related
    assert "d" not in related  # depth=2 到不了 d
    print("  [test_get_related_entities] 关联实体 ✓")


def test_infer_relation():
    """测试关系推理"""
    kg = create_knowledge_graph()
    kg.add_entity(create_entity("a", "node", "A"))
    kg.add_entity(create_entity("b", "node", "B"))
    kg.add_entity(create_entity("c", "node", "C"))

    kg.add_relation(create_relation("a", "c", RelationType.RELATED_TO))
    kg.add_relation(create_relation("b", "c", RelationType.RELATED_TO))

    inferred = kg.infer_relation("a", "b")
    assert RelationType.RELATED_TO in inferred  # 共同邻居 c
    print("  [test_infer_relation] 关系推理 ✓")


def test_remove_entity():
    """测试移除实体"""
    kg = create_knowledge_graph()
    kg.add_entity(create_entity("a", "node", "A"))
    kg.add_entity(create_entity("b", "node", "B"))
    kg.add_relation(create_relation("a", "b", RelationType.RELATED_TO))

    assert kg.remove_entity("a") is True
    assert kg.get_entity("a") is None
    # 关系也应被移除
    assert len(kg.get_relations("a")) == 0
    assert kg.get_entity("b") is not None
    print("  [test_remove_entity] 移除实体 ✓")


def test_kg_stats():
    """测试统计信息"""
    kg = create_knowledge_graph()
    kg.add_entity(create_entity("a", "person", "A"))
    kg.add_entity(create_entity("b", "person", "B"))
    kg.add_entity(create_entity("c", "org", "C"))
    kg.add_relation(create_relation("a", "b", RelationType.RELATED_TO))

    stats = kg.get_stats()
    assert stats["entity_count"] == 3
    assert stats["relation_count"] == 1
    assert "person" in stats["entity_types"]
    assert "org" in stats["entity_types"]
    print("  [test_kg_stats] 统计信息 ✓")


def test_entity_equality():
    """测试实体相等性"""
    e1 = create_entity("id1", "t", "Name")
    e2 = create_entity("id1", "t", "Name")
    e3 = create_entity("id2", "t", "Name")

    assert e1 == e2
    assert e1 != e3
    assert hash(e1) == hash(e2)
    print("  [test_entity_equality] 实体相等性 ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("阶段46测试: 知识图谱接口标准化")
    print("=" * 60)

    test_add_entity()
    test_add_relation()
    test_query_triple()
    test_find_path()
    test_get_neighbors()
    test_get_related_entities()
    test_infer_relation()
    test_remove_entity()
    test_kg_stats()
    test_entity_equality()

    print("=" * 60)
    print("全部10项测试通过 ✓")
    print("=" * 60)
