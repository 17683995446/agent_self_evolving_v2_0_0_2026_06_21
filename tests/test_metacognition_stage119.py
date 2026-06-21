"""
阶段119: 元认知强化 — 专项测试

验证新增能力:
1. SelfEvaluation: 多维度自我评估
2. CognitiveBiasDetector: 认知偏差检测
3. StrategyOptimizer: 策略优化器
4. ReflectionLog: 反思日志
5. MetacognitionFirstPrinciplesEngine: 新增接口
6. 向后兼容性

第一性原理验证:
- 元认知准确度：预测与实际偏差
- 过度自信偏差：系统性高估
- Dunning-Kruger效应：低能力高估，高能力低估
- 策略优化：基于历史表现选择最优策略
- 反思学习：从经验中提取教训
"""

import math
import threading
import time
import pytest

from self_evolving_agent.core.metacognition_first_principles import (
    CognitiveStrategy,
    ConfidenceLevel,
    CognitiveState,
    SelfAssessment,
    SelfEvaluation,
    CognitiveBiasDetector,
    StrategyOptimizer,
    ReflectionEntry,
    ReflectionLog,
    MetacognitionFirstPrinciplesEngine,
    create_metacognition_engine,
    create_self_evaluation,
    create_reflection_entry,
)


# ============================================================
# 1. SelfEvaluation 测试
# ============================================================

class TestSelfEvaluation:
    """多维度自我评估测试"""

    def test_creation(self):
        """创建评估"""
        ev = SelfEvaluation(evaluation_id="e1", task_id="t1")
        assert ev.task_id == "t1"
        assert ev.accuracy == 0.5
        assert ev.speed == 0.5

    def test_overall_score(self):
        """综合得分"""
        ev = SelfEvaluation(
            evaluation_id="e1", task_id="t1",
            accuracy=1.0, speed=1.0, efficiency=1.0, confidence=1.0,
        )
        assert ev.overall_score == 1.0

    def test_overall_score_weighted(self):
        """综合得分加权（accuracy权重0.4）"""
        ev = SelfEvaluation(
            evaluation_id="e1", task_id="t1",
            accuracy=1.0, speed=0.0, efficiency=0.0, confidence=0.0,
        )
        # 1.0*0.4 + 0*0.2 + 0*0.2 + 0*0.2 = 0.4
        assert abs(ev.overall_score - 0.4) < 1e-6

    def test_overall_score_range(self):
        """综合得分在[0,1]"""
        ev = SelfEvaluation(
            evaluation_id="e1", task_id="t1",
            accuracy=0.5, speed=0.5, efficiency=0.5, confidence=0.5,
        )
        assert 0.0 <= ev.overall_score <= 1.0

    def test_metacognitive_accuracy_no_actual(self):
        """无实际表现时元认知准确度为0"""
        ev = SelfEvaluation(evaluation_id="e1", task_id="t1", predicted_performance=0.8)
        assert ev.metacognitive_accuracy == 0.0

    def test_metacognitive_accuracy_perfect(self):
        """完美预测"""
        ev = SelfEvaluation(
            evaluation_id="e1", task_id="t1",
            predicted_performance=0.8, actual_performance=0.8,
        )
        assert ev.metacognitive_accuracy == 1.0

    def test_metacognitive_accuracy_partial(self):
        """部分预测"""
        ev = SelfEvaluation(
            evaluation_id="e1", task_id="t1",
            predicted_performance=0.8, actual_performance=0.6,
        )
        # 1 - 0.2 = 0.8
        assert abs(ev.metacognitive_accuracy - 0.8) < 1e-6

    def test_is_overconfident(self):
        """过度自信检测"""
        ev = SelfEvaluation(
            evaluation_id="e1", task_id="t1",
            predicted_performance=0.9, actual_performance=0.5,
        )
        assert ev.is_overconfident is True

    def test_not_overconfident(self):
        """非过度自信"""
        ev = SelfEvaluation(
            evaluation_id="e1", task_id="t1",
            predicted_performance=0.5, actual_performance=0.5,
        )
        assert ev.is_overconfident is False

    def test_is_underconfident(self):
        """不足自信检测"""
        ev = SelfEvaluation(
            evaluation_id="e1", task_id="t1",
            predicted_performance=0.3, actual_performance=0.8,
        )
        assert ev.is_underconfident is True

    def test_not_underconfident(self):
        """非不足自信"""
        ev = SelfEvaluation(
            evaluation_id="e1", task_id="t1",
            predicted_performance=0.5, actual_performance=0.5,
        )
        assert ev.is_underconfident is False


# ============================================================
# 2. CognitiveBiasDetector 测试
# ============================================================

class TestCognitiveBiasDetector:
    """认知偏差检测器测试"""

    def test_empty_detector(self):
        """空检测器"""
        detector = CognitiveBiasDetector()
        assert detector.detect_overconfidence_bias() == 0.0
        result = detector.detect_dunning_kruger()
        assert result["detected"] is False

    def test_overconfidence_bias_positive(self):
        """过度自信偏差为正"""
        detector = CognitiveBiasDetector()
        for i in range(5):
            detector.add_evaluation(SelfEvaluation(
                evaluation_id=f"e{i}", task_id=f"t{i}",
                predicted_performance=0.9, actual_performance=0.5,
            ))
        bias = detector.detect_overconfidence_bias()
        assert bias > 0  # 过度自信

    def test_overconfidence_bias_negative(self):
        """不足自信偏差为负"""
        detector = CognitiveBiasDetector()
        for i in range(5):
            detector.add_evaluation(SelfEvaluation(
                evaluation_id=f"e{i}", task_id=f"t{i}",
                predicted_performance=0.3, actual_performance=0.8,
            ))
        bias = detector.detect_overconfidence_bias()
        assert bias < 0  # 不足自信

    def test_overconfidence_bias_zero(self):
        """无偏差"""
        detector = CognitiveBiasDetector()
        for i in range(5):
            detector.add_evaluation(SelfEvaluation(
                evaluation_id=f"e{i}", task_id=f"t{i}",
                predicted_performance=0.7, actual_performance=0.7,
            ))
        bias = detector.detect_overconfidence_bias()
        assert abs(bias) < 1e-6

    def test_dunning_kruger_detected(self):
        """Dunning-Kruger效应检测"""
        detector = CognitiveBiasDetector()
        # 低能力者高估
        for i in range(5):
            detector.add_evaluation(SelfEvaluation(
                evaluation_id=f"low{i}", task_id=f"t{i}",
                predicted_performance=0.8, actual_performance=0.2,
            ))
        # 高能力者低估
        for i in range(5):
            detector.add_evaluation(SelfEvaluation(
                evaluation_id=f"high{i}", task_id=f"t{i}",
                predicted_performance=0.6, actual_performance=0.9,
            ))
        result = detector.detect_dunning_kruger()
        assert result["detected"] is True
        assert result["low_ability_overestimate"] > 0.1
        assert result["high_ability_underestimate"] > 0.1

    def test_dunning_kruger_not_detected(self):
        """无Dunning-Kruger效应"""
        detector = CognitiveBiasDetector()
        for i in range(6):
            detector.add_evaluation(SelfEvaluation(
                evaluation_id=f"e{i}", task_id=f"t{i}",
                predicted_performance=0.5, actual_performance=0.5,
            ))
        result = detector.detect_dunning_kruger()
        assert result["detected"] is False

    def test_get_bias_summary(self):
        """获取偏差总结"""
        detector = CognitiveBiasDetector()
        detector.add_evaluation(SelfEvaluation(
            evaluation_id="e1", task_id="t1",
            predicted_performance=0.8, actual_performance=0.5,
        ))
        summary = detector.get_bias_summary()
        assert "overconfidence_bias" in summary
        assert "dunning_kruger" in summary
        assert summary["evaluation_count"] == 1

    def test_clear(self):
        """清空"""
        detector = CognitiveBiasDetector()
        detector.add_evaluation(SelfEvaluation(evaluation_id="e1", task_id="t1"))
        detector.clear()
        assert detector.get_bias_summary()["evaluation_count"] == 0


# ============================================================
# 3. StrategyOptimizer 测试
# ============================================================

class TestStrategyOptimizer:
    """策略优化器测试"""

    def test_empty_optimizer(self):
        """空优化器"""
        opt = StrategyOptimizer()
        avg = opt.get_average_performance(CognitiveStrategy.DEEP_PROCESSING, {})
        assert avg == 0.5  # 无数据返回中性值

    def test_record_performance(self):
        """记录表现"""
        opt = StrategyOptimizer()
        opt.record_performance(CognitiveStrategy.DEEP_PROCESSING, {"complexity": 0.8}, 0.9)
        avg = opt.get_average_performance(CognitiveStrategy.DEEP_PROCESSING, {"complexity": 0.8})
        assert avg == 0.9

    def test_record_multiple_performances(self):
        """记录多次表现"""
        opt = StrategyOptimizer()
        opt.record_performance(CognitiveStrategy.DEEP_PROCESSING, {"complexity": 0.8}, 0.9)
        opt.record_performance(CognitiveStrategy.DEEP_PROCESSING, {"complexity": 0.8}, 0.7)
        avg = opt.get_average_performance(CognitiveStrategy.DEEP_PROCESSING, {"complexity": 0.8})
        assert abs(avg - 0.8) < 1e-6

    def test_different_situations(self):
        """不同情境下的表现"""
        opt = StrategyOptimizer()
        opt.record_performance(CognitiveStrategy.HEURISTIC, {"complexity": 0.2, "urgency": 0.9}, 0.9)
        opt.record_performance(CognitiveStrategy.HEURISTIC, {"complexity": 0.8, "urgency": 0.2}, 0.3)
        # 不同情境不同表现
        avg_low_complex = opt.get_average_performance(CognitiveStrategy.HEURISTIC, {"complexity": 0.2, "urgency": 0.9})
        avg_high_complex = opt.get_average_performance(CognitiveStrategy.HEURISTIC, {"complexity": 0.8, "urgency": 0.2})
        assert avg_low_complex > avg_high_complex

    def test_recommend_strategy(self):
        """推荐策略"""
        opt = StrategyOptimizer()
        # DEEP在复杂任务上表现好
        opt.record_performance(CognitiveStrategy.DEEP_PROCESSING, {"complexity": 0.8}, 0.9)
        opt.record_performance(CognitiveStrategy.HEURISTIC, {"complexity": 0.8}, 0.3)
        strategy, score = opt.recommend_strategy({"complexity": 0.8})
        assert strategy == CognitiveStrategy.DEEP_PROCESSING
        assert score > 0.5

    def test_recommend_strategy_no_data(self):
        """无数据时推荐"""
        opt = StrategyOptimizer()
        strategy, score = opt.recommend_strategy({"complexity": 0.5})
        assert isinstance(strategy, CognitiveStrategy)
        assert score == 0.5  # 所有策略都返回0.5

    def test_nan_performance_ignored(self):
        """NaN表现被忽略"""
        opt = StrategyOptimizer()
        opt.record_performance(CognitiveStrategy.DEEP_PROCESSING, {}, float("nan"))
        avg = opt.get_average_performance(CognitiveStrategy.DEEP_PROCESSING, {})
        assert avg == 0.5  # NaN被忽略，无数据

    def test_inf_performance_ignored(self):
        """Inf表现被忽略"""
        opt = StrategyOptimizer()
        opt.record_performance(CognitiveStrategy.DEEP_PROCESSING, {}, float("inf"))
        avg = opt.get_average_performance(CognitiveStrategy.DEEP_PROCESSING, {})
        assert avg == 0.5

    def test_performance_clamped(self):
        """表现值钳制到[0,1]"""
        opt = StrategyOptimizer()
        opt.record_performance(CognitiveStrategy.DEEP_PROCESSING, {}, 2.0)
        avg = opt.get_average_performance(CognitiveStrategy.DEEP_PROCESSING, {})
        assert avg == 1.0

    def test_get_strategy_stats(self):
        """获取策略统计"""
        opt = StrategyOptimizer()
        opt.record_performance(CognitiveStrategy.DEEP_PROCESSING, {"complexity": 0.8}, 0.9)
        stats = opt.get_strategy_stats()
        assert "deep" in stats
        assert stats["deep"]["count"] == 1

    def test_clear(self):
        """清空"""
        opt = StrategyOptimizer()
        opt.record_performance(CognitiveStrategy.DEEP_PROCESSING, {}, 0.9)
        opt.clear()
        stats = opt.get_strategy_stats()
        assert len(stats) == 0


# ============================================================
# 4. ReflectionLog 测试
# ============================================================

class TestReflectionLog:
    """反思日志测试"""

    def test_add_reflection(self):
        """添加反思"""
        log = ReflectionLog()
        entry = ReflectionEntry(reflection_id="r1", task_id="t1")
        log.add_reflection(entry)
        assert log.get_stats()["total_reflections"] == 1

    def test_get_reflections_by_task(self):
        """按任务获取反思"""
        log = ReflectionLog()
        log.add_reflection(ReflectionEntry(reflection_id="r1", task_id="t1"))
        log.add_reflection(ReflectionEntry(reflection_id="r2", task_id="t2"))
        results = log.get_reflections_by_task("t1")
        assert len(results) == 1
        assert results[0].task_id == "t1"

    def test_get_reflections_by_strategy(self):
        """按策略获取反思"""
        log = ReflectionLog()
        log.add_reflection(ReflectionEntry(
            reflection_id="r1", task_id="t1",
            strategy_used=CognitiveStrategy.DEEP_PROCESSING,
        ))
        log.add_reflection(ReflectionEntry(
            reflection_id="r2", task_id="t2",
            strategy_used=CognitiveStrategy.HEURISTIC,
        ))
        results = log.get_reflections_by_strategy(CognitiveStrategy.DEEP_PROCESSING)
        assert len(results) == 1

    def test_get_successful_reflections(self):
        """获取成功反思"""
        log = ReflectionLog()
        log.add_reflection(ReflectionEntry(reflection_id="r1", task_id="t1", outcome_score=0.9))
        log.add_reflection(ReflectionEntry(reflection_id="r2", task_id="t2", outcome_score=0.2))
        results = log.get_successful_reflections()
        assert len(results) == 1

    def test_get_failed_reflections(self):
        """获取失败反思"""
        log = ReflectionLog()
        log.add_reflection(ReflectionEntry(reflection_id="r1", task_id="t1", outcome_score=0.9))
        log.add_reflection(ReflectionEntry(reflection_id="r2", task_id="t2", outcome_score=0.2))
        results = log.get_failed_reflections()
        assert len(results) == 1

    def test_get_common_lessons(self):
        """获取常见教训"""
        log = ReflectionLog()
        log.add_reflection(ReflectionEntry(
            reflection_id="r1", task_id="t1",
            lessons_learned=["lesson_a", "lesson_b"],
        ))
        log.add_reflection(ReflectionEntry(
            reflection_id="r2", task_id="t2",
            lessons_learned=["lesson_a", "lesson_c"],
        ))
        lessons = log.get_common_lessons()
        assert len(lessons) > 0
        assert lessons[0][0] == "lesson_a"
        assert lessons[0][1] == 2

    def test_capacity_limit(self):
        """容量限制"""
        log = ReflectionLog(max_entries=5)
        for i in range(10):
            log.add_reflection(ReflectionEntry(reflection_id=f"r{i}", task_id=f"t{i}"))
        assert log.get_stats()["total_reflections"] == 5

    def test_get_stats(self):
        """获取统计"""
        log = ReflectionLog()
        log.add_reflection(ReflectionEntry(reflection_id="r1", task_id="t1", outcome_score=0.9))
        log.add_reflection(ReflectionEntry(reflection_id="r2", task_id="t2", outcome_score=0.2))
        stats = log.get_stats()
        assert stats["total_reflections"] == 2
        assert stats["success_count"] == 1
        assert stats["failure_count"] == 1

    def test_clear(self):
        """清空"""
        log = ReflectionLog()
        log.add_reflection(ReflectionEntry(reflection_id="r1", task_id="t1"))
        log.clear()
        assert log.get_stats()["total_reflections"] == 0


# ============================================================
# 5. Enhanced MetacognitionFirstPrinciplesEngine 测试
# ============================================================

class TestEnhancedEngine:
    """增强引擎测试"""

    def test_evaluate_self(self):
        """多维度自我评估"""
        engine = create_metacognition_engine()
        ev = engine.evaluate_self(
            "task1", accuracy=0.8, speed=0.7, efficiency=0.6, confidence=0.9,
        )
        assert ev.task_id == "task1"
        assert ev.accuracy == 0.8

    def test_evaluate_self_with_actual(self):
        """带实际表现的评估"""
        engine = create_metacognition_engine()
        ev = engine.evaluate_self(
            "task1", predicted_performance=0.8, actual_performance=0.7,
            strategy_used=CognitiveStrategy.DEEP_PROCESSING,
        )
        assert ev.metacognitive_accuracy > 0.8

    def test_detect_bias(self):
        """检测偏差"""
        engine = create_metacognition_engine()
        engine.evaluate_self("t1", predicted_performance=0.9, actual_performance=0.5)
        bias = engine.detect_bias()
        assert "overconfidence_bias" in bias
        assert bias["overconfidence_bias"] > 0

    def test_recommend_strategy(self):
        """推荐策略"""
        engine = create_metacognition_engine()
        # 记录一些表现
        engine.evaluate_self(
            "t1", actual_performance=0.9, strategy_used=CognitiveStrategy.DEEP_PROCESSING,
        )
        strategy, score = engine.recommend_strategy({"complexity": 0.5})
        assert isinstance(strategy, CognitiveStrategy)

    def test_reflect(self):
        """反思"""
        engine = create_metacognition_engine()
        entry = engine.reflect(
            "task1",
            what_worked=["good planning"],
            what_failed=["rushed execution"],
            lessons_learned=["take more time"],
        )
        assert entry.task_id == "task1"
        assert "good planning" in entry.what_worked

    def test_get_reflections(self):
        """获取反思"""
        engine = create_metacognition_engine()
        engine.reflect("t1", ["w1"], ["f1"], ["l1"])
        reflections = engine.get_reflections()
        assert len(reflections) == 1

    def test_get_reflections_by_task(self):
        """按任务获取反思"""
        engine = create_metacognition_engine()
        engine.reflect("t1", ["w1"], ["f1"], ["l1"])
        engine.reflect("t2", ["w2"], ["f2"], ["l2"])
        reflections = engine.get_reflections("t1")
        assert len(reflections) == 1

    def test_get_common_lessons(self):
        """获取常见教训"""
        engine = create_metacognition_engine()
        engine.reflect("t1", [], [], ["lesson_a"])
        engine.reflect("t2", [], [], ["lesson_a", "lesson_b"])
        lessons = engine.get_common_lessons()
        assert len(lessons) > 0

    def test_get_evaluations(self):
        """获取所有评估"""
        engine = create_metacognition_engine()
        engine.evaluate_self("t1")
        engine.evaluate_self("t2")
        evals = engine.get_evaluations()
        assert len(evals) == 2

    def test_stats_include_new_components(self):
        """统计包含新组件"""
        engine = create_metacognition_engine()
        engine.evaluate_self("t1")
        stats = engine.get_stats()
        assert "evaluations_count" in stats
        assert "bias_summary" in stats
        assert "strategy_stats" in stats
        assert "reflection_stats" in stats

    def test_get_bias_detector(self):
        """获取偏差检测器"""
        engine = create_metacognition_engine()
        detector = engine.get_bias_detector()
        assert isinstance(detector, CognitiveBiasDetector)

    def test_get_strategy_optimizer(self):
        """获取策略优化器"""
        engine = create_metacognition_engine()
        opt = engine.get_strategy_optimizer()
        assert isinstance(opt, StrategyOptimizer)

    def test_get_reflection_log(self):
        """获取反思日志"""
        engine = create_metacognition_engine()
        log = engine.get_reflection_log()
        assert isinstance(log, ReflectionLog)


# ============================================================
# 6. 向后兼容性测试
# ============================================================

class TestBackwardCompat:
    """向后兼容性测试"""

    def test_update_state(self):
        """更新认知状态"""
        engine = create_metacognition_engine()
        engine.update_state(task_complexity=0.8, cognitive_load=0.6)
        stats = engine.get_stats()
        assert stats["current_state"]["cognitive_load"] == 0.6

    def test_assess_task(self):
        """评估任务"""
        engine = create_metacognition_engine()
        assessment = engine.assess_task("t1", {"complexity": 0.8, "required_capacity": 0.5})
        assert isinstance(assessment, SelfAssessment)
        assert 0.0 <= assessment.predicted_performance <= 1.0

    def test_select_strategy(self):
        """选择策略"""
        engine = create_metacognition_engine()
        strategy = engine.select_strategy({"complexity": 0.8, "urgency": 0.3})
        assert isinstance(strategy, CognitiveStrategy)

    def test_record_outcome(self):
        """记录结果"""
        engine = create_metacognition_engine()
        engine.assess_task("t1", {"complexity": 0.5, "required_capacity": 0.5})
        engine.record_outcome("t1", 0.8)
        # 校准度应大于0
        calibration = engine.get_calibration_accuracy()
        assert calibration > 0

    def test_get_calibration_accuracy(self):
        """获取校准度"""
        engine = create_metacognition_engine()
        # 无数据时返回0
        assert engine.get_calibration_accuracy() == 0.0

    def test_get_recommended_action(self):
        """获取推荐行动"""
        engine = create_metacognition_engine()
        action = engine.get_recommended_action()
        assert action in ["rest", "simplify_task", "refocus", "proceed"]

    def test_get_stats_backward_compat(self):
        """统计向后兼容"""
        engine = create_metacognition_engine()
        stats = engine.get_stats()
        assert "engine_id" in stats
        assert "cycle_count" in stats
        assert "current_state" in stats
        assert "assessments_count" in stats
        assert "calibration_accuracy" in stats
        assert "recommended_action" in stats

    def test_reset(self):
        """重置"""
        engine = create_metacognition_engine()
        engine.assess_task("t1", {"complexity": 0.5})
        engine.evaluate_self("t1")
        engine.reflect("t1", [], [], [])
        engine.reset()
        stats = engine.get_stats()
        assert stats["assessments_count"] == 0
        assert stats["evaluations_count"] == 0
        assert stats["reflection_stats"]["total_reflections"] == 0

    def test_none_task_features(self):
        """None任务特征防御"""
        engine = create_metacognition_engine()
        assessment = engine.assess_task("t1", None)
        assert isinstance(assessment, SelfAssessment)

    def test_none_strategy_features(self):
        """None策略特征防御"""
        engine = create_metacognition_engine()
        strategy = engine.select_strategy(None)
        assert isinstance(strategy, CognitiveStrategy)

    def test_create_self_evaluation_helper(self):
        """create_self_evaluation 便捷函数"""
        ev = create_self_evaluation("t1", accuracy=0.8)
        assert ev.task_id == "t1"
        assert ev.accuracy == 0.8

    def test_create_reflection_entry_helper(self):
        """create_reflection_entry 便捷函数"""
        entry = create_reflection_entry("t1", ["w1"], ["f1"], ["l1"])
        assert entry.task_id == "t1"
        assert "w1" in entry.what_worked

    def test_cognitive_state_capacity(self):
        """认知状态容量"""
        state = CognitiveState(state_id="s1", cognitive_load=0.3, fatigue_level=0.2)
        assert abs(state.capacity_available - 0.5) < 1e-6

    def test_cognitive_state_needs_rest(self):
        """认知状态需要休息"""
        state = CognitiveState(state_id="s1", fatigue_level=0.8)
        assert state.needs_rest is True


# ============================================================
# 7. 并发安全测试
# ============================================================

class TestConcurrency:
    """并发安全测试"""

    def test_concurrent_evaluate(self):
        """并发评估"""
        engine = create_metacognition_engine()
        errors = []

        def worker(worker_id):
            try:
                for i in range(20):
                    engine.evaluate_self(f"t{worker_id}_{i}", accuracy=0.8)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert engine.get_stats()["evaluations_count"] == 100

    def test_concurrent_reflect(self):
        """并发反思"""
        engine = create_metacognition_engine()
        errors = []

        def worker(worker_id):
            try:
                for i in range(20):
                    engine.reflect(f"t{worker_id}_{i}", ["w"], ["f"], ["l"])
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert engine.get_stats()["reflection_stats"]["total_reflections"] == 100

    def test_concurrent_strategy_optimize(self):
        """并发策略优化"""
        opt = StrategyOptimizer()
        errors = []

        def worker(worker_id):
            try:
                for i in range(20):
                    opt.record_performance(
                        CognitiveStrategy.DEEP_PROCESSING,
                        {"complexity": 0.8}, 0.8,
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
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

    def test_evaluate_performance(self):
        """评估性能：1000次 < 1秒"""
        engine = create_metacognition_engine()
        start = time.time()
        for i in range(1000):
            engine.evaluate_self(f"t{i}", accuracy=0.8)
        elapsed = time.time() - start
        assert elapsed < 1.0, f"评估1000次耗时 {elapsed:.3f}s"

    def test_reflect_performance(self):
        """反思性能：1000次 < 1秒"""
        engine = create_metacognition_engine()
        start = time.time()
        for i in range(1000):
            engine.reflect(f"t{i}", ["w"], ["f"], ["l"])
        elapsed = time.time() - start
        assert elapsed < 1.0, f"反思1000次耗时 {elapsed:.3f}s"

    def test_strategy_recommend_performance(self):
        """策略推荐性能：1000次 < 1秒"""
        opt = StrategyOptimizer()
        # 预先记录一些数据
        for _ in range(100):
            opt.record_performance(CognitiveStrategy.DEEP_PROCESSING, {"complexity": 0.8}, 0.9)
        start = time.time()
        for _ in range(1000):
            opt.recommend_strategy({"complexity": 0.8})
        elapsed = time.time() - start
        assert elapsed < 1.0, f"策略推荐1000次耗时 {elapsed:.3f}s"

    def test_bias_detection_performance(self):
        """偏差检测性能：1000条评估 < 0.5秒"""
        detector = CognitiveBiasDetector()
        for i in range(1000):
            detector.add_evaluation(SelfEvaluation(
                evaluation_id=f"e{i}", task_id=f"t{i}",
                predicted_performance=0.7, actual_performance=0.5,
            ))
        start = time.time()
        detector.detect_overconfidence_bias()
        elapsed = time.time() - start
        assert elapsed < 0.5, f"偏差检测1000条耗时 {elapsed:.3f}s"


# ============================================================
# 9. 异常容错测试
# ============================================================

class TestErrorTolerance:
    """异常容错测试"""

    def test_nan_accuracy(self):
        """NaN准确度"""
        engine = create_metacognition_engine()
        ev = engine.evaluate_self("t1", accuracy=float("nan"))
        assert 0.0 <= ev.accuracy <= 1.0

    def test_inf_speed(self):
        """Inf速度"""
        engine = create_metacognition_engine()
        ev = engine.evaluate_self("t1", speed=float("inf"))
        assert 0.0 <= ev.speed <= 1.0

    def test_negative_efficiency(self):
        """负效率"""
        engine = create_metacognition_engine()
        ev = engine.evaluate_self("t1", efficiency=-0.5)
        assert ev.efficiency == 0.0

    def test_huge_confidence(self):
        """超大置信度"""
        engine = create_metacognition_engine()
        ev = engine.evaluate_self("t1", confidence=1e10)
        assert ev.confidence == 1.0

    def test_none_actual_performance(self):
        """None实际表现"""
        engine = create_metacognition_engine()
        ev = engine.evaluate_self("t1", actual_performance=None)
        assert ev.actual_performance is None
        assert ev.metacognitive_accuracy == 0.0

    def test_string_performance(self):
        """字符串表现"""
        opt = StrategyOptimizer()
        # 字符串无法转float，应被防御
        opt.record_performance(CognitiveStrategy.DEEP_PROCESSING, {}, "not a number")
        avg = opt.get_average_performance(CognitiveStrategy.DEEP_PROCESSING, {})
        # 字符串转float失败，performance为0.0（_safe_float返回0.0）
        # 但record_performance中performance已经是0.0，会被记录
        assert 0.0 <= avg <= 1.0

    def test_reflect_empty_lists(self):
        """空列表反思"""
        engine = create_metacognition_engine()
        entry = engine.reflect("t1", [], [], [])
        assert entry.what_worked == []
        assert entry.what_failed == []
        assert entry.lessons_learned == []

    def test_reflect_none_lists(self):
        """None列表反思"""
        engine = create_metacognition_engine()
        entry = engine.reflect("t1", None, None, None)
        assert entry.what_worked == []

    def test_update_state_nan(self):
        """NaN状态更新"""
        engine = create_metacognition_engine()
        engine.update_state(cognitive_load=float("nan"))
        stats = engine.get_stats()
        # NaN被防御为默认值0.5
        assert not math.isnan(stats["current_state"]["cognitive_load"])


# ============================================================
# 10. 第一性原理验证测试
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_metacognitive_accuracy_decreases_with_error(self):
        """元认知准确度随误差增大而减小"""
        ev_perfect = SelfEvaluation(
            evaluation_id="e1", task_id="t1",
            predicted_performance=0.7, actual_performance=0.7,
        )
        ev_medium = SelfEvaluation(
            evaluation_id="e2", task_id="t2",
            predicted_performance=0.7, actual_performance=0.5,
        )
        ev_poor = SelfEvaluation(
            evaluation_id="e3", task_id="t3",
            predicted_performance=0.7, actual_performance=0.2,
        )
        assert ev_perfect.metacognitive_accuracy > ev_medium.metacognitive_accuracy
        assert ev_medium.metacognitive_accuracy > ev_poor.metacognitive_accuracy

    def test_overconfidence_bias_systematic(self):
        """过度自信偏差是系统性的"""
        detector = CognitiveBiasDetector()
        # 多次高估
        for i in range(10):
            detector.add_evaluation(SelfEvaluation(
                evaluation_id=f"e{i}", task_id=f"t{i}",
                predicted_performance=0.9, actual_performance=0.5,
            ))
        bias = detector.detect_overconfidence_bias()
        # 系统性高估0.4
        assert abs(bias - 0.4) < 1e-6

    def test_strategy_optimization_learns(self):
        """策略优化器能学习"""
        opt = StrategyOptimizer()
        # DEEP在复杂任务上表现好
        for _ in range(10):
            opt.record_performance(CognitiveStrategy.DEEP_PROCESSING, {"complexity": 0.8}, 0.9)
        # HEURISTIC在复杂任务上表现差
        for _ in range(10):
            opt.record_performance(CognitiveStrategy.HEURISTIC, {"complexity": 0.8}, 0.3)

        strategy, score = opt.recommend_strategy({"complexity": 0.8})
        assert strategy == CognitiveStrategy.DEEP_PROCESSING
        assert score > 0.8

    def test_reflection_learns_lessons(self):
        """反思能学习教训"""
        engine = create_metacognition_engine()
        # 多次反思同一教训
        for i in range(5):
            engine.reflect(f"t{i}", [], [], ["always_test_edge_cases"])
        lessons = engine.get_common_lessons()
        assert len(lessons) > 0
        assert lessons[0][0] == "always_test_edge_cases"
        assert lessons[0][1] == 5

    def test_overall_score_reflects_performance(self):
        """综合得分反映表现"""
        ev_high = SelfEvaluation(
            evaluation_id="e1", task_id="t1",
            accuracy=1.0, speed=1.0, efficiency=1.0, confidence=1.0,
        )
        ev_low = SelfEvaluation(
            evaluation_id="e2", task_id="t2",
            accuracy=0.0, speed=0.0, efficiency=0.0, confidence=0.0,
        )
        assert ev_high.overall_score > ev_low.overall_score

    def test_dunning_kruger_pattern(self):
        """Dunning-Kruger模式：低能力高估，高能力低估"""
        detector = CognitiveBiasDetector()
        # 低能力者（actual=0.2）高估（predicted=0.8）
        for i in range(5):
            detector.add_evaluation(SelfEvaluation(
                evaluation_id=f"low{i}", task_id=f"t{i}",
                predicted_performance=0.8, actual_performance=0.2,
            ))
        # 高能力者（actual=0.9）低估（predicted=0.5）
        for i in range(5):
            detector.add_evaluation(SelfEvaluation(
                evaluation_id=f"high{i}", task_id=f"t{i}",
                predicted_performance=0.5, actual_performance=0.9,
            ))
        result = detector.detect_dunning_kruger()
        assert result["detected"] is True
        assert result["low_ability_overestimate"] > 0
        assert result["high_ability_underestimate"] > 0
