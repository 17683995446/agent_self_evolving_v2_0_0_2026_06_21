"""
阶段47测试: 推理引擎接口标准化
"""
import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.inference_engine import (
    InferenceEngine, InferenceStrategy, Fact, Rule, InferenceResult,
    create_inference_engine, create_fact, create_rule
)


def test_add_fact():
    """测试添加事实"""
    engine = create_inference_engine()
    fact = create_fact("temperature", "room1", 25.0)

    engine.add_fact(fact)
    assert len(engine.get_facts()) == 1
    assert engine.get_facts()[0].value == 25.0
    print("  [test_add_fact] 添加事实 ✓")


def test_query_fact():
    """测试查询事实"""
    engine = create_inference_engine()
    engine.add_fact(create_fact("temp", "room1", 20))
    engine.add_fact(create_fact("temp", "room2", 30))
    engine.add_fact(create_fact("humidity", "room1", 60))

    results = engine.query("temp")
    assert len(results) == 2

    results = engine.query("temp", "room1")
    assert len(results) == 1
    assert results[0].value == 20
    print("  [test_query_fact] 查询事实 ✓")


def test_forward_chain():
    """测试前向链推理"""
    engine = create_inference_engine()

    # 事实：如果温度>25且湿度>50，则闷热
    engine.add_fact(create_fact("temp", "room1", 30))
    engine.add_fact(create_fact("humidity", "room1", 70))

    # 规则
    def condition(facts):
        temps = [f for f in facts if f.predicate == "temp" and f.value > 25]
        humids = [f for f in facts if f.predicate == "humidity" and f.value > 50]
        return len(temps) > 0 and len(humids) > 0

    def conclusion(facts):
        return [create_fact("status", "room1", "hot_and_humid", confidence=0.9)]

    rule = create_rule("hot_rule", [condition], conclusion, priority=1)
    engine.add_rule(rule)

    results = engine.infer()
    assert len(results) == 1
    assert results[0].conclusion.value == "hot_and_humid"
    assert results[0].confidence == 0.9
    print("  [test_forward_chain] 前向链推理 ✓")


def test_rule_priority():
    """测试规则优先级"""
    engine = create_inference_engine()
    engine.add_fact(create_fact("x", "a", 10))

    triggered = []

    def make_rule(name, pri, val):
        def cond(facts):
            return any(f.value == 10 for f in facts)
        def conc(facts):
            triggered.append(name)
            return [create_fact("result", "a", val)]
        return create_rule(name, [cond], conc, priority=pri)

    engine.add_rule(make_rule("low", 1, "low_val"))
    engine.add_rule(make_rule("high", 10, "high_val"))

    engine.infer()
    # 高优先级先触发
    assert triggered[0] == "high"
    print("  [test_rule_priority] 规则优先级 ✓")


def test_inference_result():
    """测试推理结果"""
    result = InferenceResult(
        conclusion=create_fact("status", "room", "ok"),
        confidence=0.95,
        derivation_chain=["temp=25", "humidity=50"],
        applied_rules=["rule1"],
    )

    assert result.conclusion.predicate == "status"
    assert result.confidence == 0.95
    assert len(result.derivation_chain) == 2
    print("  [test_inference_result] 推理结果 ✓")


def test_engine_stats():
    """测试引擎统计"""
    engine = create_inference_engine()
    engine.add_fact(create_fact("a", "b", 1))
    engine.add_fact(create_fact("c", "d", 2))
    engine.add_rule(create_rule("r1", [lambda f: True], lambda f: []))

    stats = engine.get_stats()
    assert stats["fact_count"] == 2
    assert stats["rule_count"] == 1
    assert stats["strategy"] == "forward"
    print("  [test_engine_stats] 引擎统计 ✓")


def test_reset():
    """测试重置"""
    engine = create_inference_engine()
    engine.add_fact(create_fact("a", "b", 1))
    engine.infer()

    engine.reset()
    assert len(engine.get_facts()) == 0
    assert len(engine.get_results()) == 0
    print("  [test_reset] 重置 ✓")


def test_multiple_conditions():
    """测试多条件规则"""
    engine = create_inference_engine()
    engine.add_fact(create_fact("a", "x", 1))
    engine.add_fact(create_fact("b", "x", 2))
    engine.add_fact(create_fact("c", "x", 3))

    def cond1(facts):
        return any(f.predicate == "a" for f in facts)

    def cond2(facts):
        return any(f.predicate == "b" for f in facts)

    def conc(facts):
        return [create_fact("combined", "x", "yes")]

    engine.add_rule(create_rule("multi", [cond1, cond2], conc))
    results = engine.infer()

    assert len(results) == 1
    assert results[0].conclusion.value == "yes"
    print("  [test_multiple_conditions] 多条件规则 ✓")


def test_no_match():
    """测试无匹配规则"""
    engine = create_inference_engine()
    engine.add_fact(create_fact("a", "x", 1))

    def cond(facts):
        return any(f.predicate == "nonexistent" for f in facts)

    engine.add_rule(create_rule("nomatch", [cond], lambda f: []))
    results = engine.infer()

    assert len(results) == 0
    print("  [test_no_match] 无匹配规则 ✓")


def test_fact_equality():
    """测试事实相等性"""
    f1 = create_fact("temp", "room1", 25)
    f2 = create_fact("temp", "room1", 25)
    f3 = create_fact("temp", "room1", 30)

    assert f1 == f2
    assert f1 != f3
    assert hash(f1) == hash(f2)
    print("  [test_fact_equality] 事实相等性 ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("阶段47测试: 推理引擎接口标准化")
    print("=" * 60)

    test_add_fact()
    test_query_fact()
    test_forward_chain()
    test_rule_priority()
    test_inference_result()
    test_engine_stats()
    test_reset()
    test_multiple_conditions()
    test_no_match()
    test_fact_equality()

    print("=" * 60)
    print("全部10项测试通过 ✓")
    print("=" * 60)
