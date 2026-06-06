"""
阶段49测试: A/B测试接口标准化
"""
import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.ab_testing import (
    ABTestEngine, Experiment, Variant, AssignmentStrategy, ExperimentStatus,
    MetricStats, create_ab_test_engine, create_variant, create_experiment
)


def test_create_variant():
    """测试创建变体"""
    v = create_variant("v1", "Variant A", traffic_ratio=0.5, color="red")
    assert v.variant_id == "v1"
    assert v.name == "Variant A"
    assert v.traffic_ratio == 0.5
    assert v.config["color"] == "red"
    print("  [test_create_variant] 创建变体 ✓")


def test_experiment_lifecycle():
    """测试实验生命周期"""
    exp = create_experiment(
        "exp1", "Test",
        [create_variant("a", "A"), create_variant("b", "B")]
    )

    assert exp.status == ExperimentStatus.DRAFT

    exp.start()
    assert exp.status == ExperimentStatus.RUNNING

    exp.pause()
    assert exp.status == ExperimentStatus.PAUSED

    exp.stop()
    assert exp.status == ExperimentStatus.COMPLETED
    print("  [test_experiment_lifecycle] 实验生命周期 ✓")


def test_hash_assignment():
    """测试哈希分组"""
    exp = create_experiment(
        "exp1", "Test",
        [create_variant("a", "A", 0.5), create_variant("b", "B", 0.5)],
        strategy=AssignmentStrategy.HASH
    )
    exp.start()

    # 同一用户应始终分配到同一变体
    user_id = "user_123"
    v1 = exp.assign(user_id)
    v2 = exp.assign(user_id)
    assert v1 is v2
    assert v1.variant_id in ("a", "b")
    print("  [test_hash_assignment] 哈希分组 ✓")


def test_random_assignment():
    """测试随机分组"""
    exp = create_experiment(
        "exp2", "Test",
        [create_variant("a", "A", 0.5), create_variant("b", "B", 0.5)],
        strategy=AssignmentStrategy.RANDOM
    )
    exp.start()

    counts = {"a": 0, "b": 0}
    for i in range(100):
        v = exp.assign(f"user_{i}")
        counts[v.variant_id] += 1

    # 随机分配，两个变体都应有样本
    assert counts["a"] > 0
    assert counts["b"] > 0
    print("  [test_random_assignment] 随机分组 ✓")


def test_not_running():
    """测试实验未运行时返回None"""
    exp = create_experiment(
        "exp3", "Test",
        [create_variant("a", "A")]
    )
    # 未启动
    assert exp.assign("user") is None
    print("  [test_not_running] 未运行返回None ✓")


def test_record_metric():
    """测试记录指标"""
    exp = create_experiment(
        "exp4", "Test",
        [create_variant("a", "A"), create_variant("b", "B")]
    )

    exp.record_metric("a", "click_rate", 0.1)
    exp.record_metric("a", "click_rate", 0.2)
    exp.record_metric("b", "click_rate", 0.15)

    results = exp.get_results()
    variant_a = next(v for v in results["variants"] if v["variant_id"] == "a")
    assert variant_a["metrics"]["click_rate"]["count"] == 2
    assert variant_a["metrics"]["click_rate"]["mean"] == 0.15
    print("  [test_record_metric] 记录指标 ✓")


def test_ab_test_engine():
    """测试A/B测试引擎"""
    engine = create_ab_test_engine()
    exp = create_experiment(
        "engine_test", "Test",
        [create_variant("a", "A"), create_variant("b", "B")]
    )
    exp.start()

    engine.register_experiment(exp)

    variant = engine.assign_variant("engine_test", "user_1")
    assert variant is not None

    engine.record_observation("engine_test", variant.variant_id, "conversion", 1.0)

    results = engine.get_experiment_results("engine_test")
    assert results["experiment_id"] == "engine_test"
    print("  [test_ab_test_engine] A/B测试引擎 ✓")


def test_metric_stats():
    """测试指标统计"""
    stats = MetricStats(metric_name="test", variant_id="a")
    stats.add(10)
    stats.add(20)
    stats.add(30)

    assert stats.count == 3
    assert stats.mean == 20.0
    assert stats.std > 0
    print("  [test_metric_stats] 指标统计 ✓")


def test_experiment_results():
    """测试实验结果汇总"""
    exp = create_experiment(
        "results_test", "Test",
        [create_variant("control", "Control"), create_variant("treatment", "Treatment")]
    )

    for i in range(10):
        exp.record_metric("control", "revenue", 100.0)
        exp.record_metric("treatment", "revenue", 110.0)

    results = exp.get_results()
    assert len(results["variants"]) == 2

    control = next(v for v in results["variants"] if v["variant_id"] == "control")
    treatment = next(v for v in results["variants"] if v["variant_id"] == "treatment")

    assert control["metrics"]["revenue"]["mean"] == 100.0
    assert treatment["metrics"]["revenue"]["mean"] == 110.0
    print("  [test_experiment_results] 实验结果汇总 ✓")


def test_threshold_assignment():
    """测试阈值分组"""
    exp = create_experiment(
        "threshold_test", "Test",
        [create_variant("a", "A", 0.3), create_variant("b", "B", 0.7)],
        strategy=AssignmentStrategy.THRESHOLD
    )
    exp.start()

    counts = {"a": 0, "b": 0}
    for i in range(1000):
        v = exp.assign(f"user_{i}")
        counts[v.variant_id] += 1

    # 大致符合流量比例
    ratio_a = counts["a"] / 1000
    assert 0.25 < ratio_a < 0.35
    print("  [test_threshold_assignment] 阈值分组 ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("阶段49测试: A/B测试接口标准化")
    print("=" * 60)

    test_create_variant()
    test_experiment_lifecycle()
    test_hash_assignment()
    test_random_assignment()
    test_not_running()
    test_record_metric()
    test_ab_test_engine()
    test_metric_stats()
    test_experiment_results()
    test_threshold_assignment()

    print("=" * 60)
    print("全部10项测试通过 ✓")
    print("=" * 60)
