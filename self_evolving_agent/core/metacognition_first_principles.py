"""
阶段119: 元认知强化 — 自我评估 + 策略优化

第一性原理:
1. 认知自身才能优化认知：不知道自己在想什么就无法改进
2. 元认知是监控和调节认知过程的能力
3. 系统必须能评估自身认知状态
4. 自我评估的准确性可被校准（元认知校准）
5. 策略选择应基于历史表现优化（策略优化）
6. 反思是从经验中学习的关键（反思日志）

强化内容:
- SelfEvaluation: 多维度自我评估（准确度、速度、效率、置信度）
- StrategyOptimizer: 策略优化器（基于历史表现选择最优策略）
- CognitiveBiasDetector: 认知偏差检测（过度自信、不足自信）
- ReflectionLog: 反思日志（从经验中学习）
- MetacognitiveControl: 元认知控制（监控、调节、反思）

向后兼容: 保留原有 CognitiveState / SelfAssessment / MetacognitionFirstPrinciplesEngine 接口
"""

import threading
import time
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from collections import defaultdict


# ============================================================
# 基础枚举与数据结构（向后兼容）
# ============================================================

class CognitiveStrategy(Enum):
    """认知策略"""
    DEEP_PROCESSING = "deep"
    SHALLOW_PROCESSING = "shallow"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    HEURISTIC = "heuristic"
    ANALYTIC = "analytic"


class ConfidenceLevel(Enum):
    """置信水平"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class CognitiveState:
    """认知状态（向后兼容）"""
    state_id: str
    task_complexity: float = 0.5
    cognitive_load: float = 0.5
    fatigue_level: float = 0.0
    focus_level: float = 0.5
    timestamp: float = field(default_factory=time.time)

    @property
    def capacity_available(self) -> float:
        """可用认知容量"""
        return max(0.0, 1.0 - self.cognitive_load - self.fatigue_level)

    @property
    def needs_rest(self) -> bool:
        """是否需要休息"""
        return self.fatigue_level > 0.7 or self.cognitive_load > 0.9


@dataclass
class SelfAssessment:
    """自我评估（向后兼容）"""
    assessment_id: str
    task_id: str
    predicted_performance: float = 0.5
    actual_performance: Optional[float] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 阶段119新增：多维度自我评估
# ============================================================

@dataclass
class SelfEvaluation:
    """
    多维度自我评估

    第一性原理：自我评估应涵盖多个认知维度
    - accuracy: 准确度（任务完成质量）
    - speed: 速度（任务完成效率）
    - efficiency: 效率（资源使用率）
    - confidence: 置信度（对结果的信心）
    - metacognitive_accuracy: 元认知准确度（预测与实际的偏差）
    """
    evaluation_id: str
    task_id: str
    accuracy: float = 0.5
    speed: float = 0.5
    efficiency: float = 0.5
    confidence: float = 0.5
    predicted_performance: float = 0.5
    actual_performance: Optional[float] = None
    strategy_used: Optional[CognitiveStrategy] = None
    timestamp: float = field(default_factory=time.time)

    @property
    def overall_score(self) -> float:
        """综合得分（加权平均）"""
        weights = {"accuracy": 0.4, "speed": 0.2, "efficiency": 0.2, "confidence": 0.2}
        total = (
            self.accuracy * weights["accuracy"]
            + self.speed * weights["speed"]
            + self.efficiency * weights["efficiency"]
            + self.confidence * weights["confidence"]
        )
        return max(0.0, min(1.0, total))

    @property
    def metacognitive_accuracy(self) -> float:
        """
        元认知准确度

        第一性原理：预测与实际的偏差越小，元认知越准确
        返回 [0, 1]，1表示完全准确
        """
        if self.actual_performance is None:
            return 0.0
        error = abs(self.predicted_performance - self.actual_performance)
        return max(0.0, 1.0 - error)

    @property
    def is_overconfident(self) -> bool:
        """是否过度自信（预测显著高于实际）"""
        if self.actual_performance is None:
            return False
        return self.predicted_performance > self.actual_performance + 0.2

    @property
    def is_underconfident(self) -> bool:
        """是否不足自信（预测显著低于实际）"""
        if self.actual_performance is None:
            return False
        return self.predicted_performance < self.actual_performance - 0.2


# ============================================================
# 阶段119新增：认知偏差检测器
# ============================================================

class CognitiveBiasDetector:
    """
    认知偏差检测器

    第一性原理：系统性自我评估偏差是认知偏差
    - 过度自信偏差：普遍高估自己的能力
    - 不足自信偏差：普遍低估自己的能力
    - Dunning-Kruger效应：能力低者高估，能力高者低估
    """

    def __init__(self):
        self._evaluations: List[SelfEvaluation] = []
        self._lock = threading.RLock()

    def add_evaluation(self, evaluation: SelfEvaluation) -> None:
        """添加评估"""
        with self._lock:
            self._evaluations.append(evaluation)

    def detect_overconfidence_bias(self) -> float:
        """
        检测过度自信偏差

        第一性原理：平均预测 - 平均实际 > 0 表示过度自信
        返回 [-1, 1]，正值表示过度自信，负值表示不足自信
        """
        with self._lock:
            completed = [e for e in self._evaluations if e.actual_performance is not None]

        if not completed:
            return 0.0

        avg_predicted = sum(e.predicted_performance for e in completed) / len(completed)
        avg_actual = sum(e.actual_performance for e in completed) / len(completed)
        return avg_predicted - avg_actual

    def detect_dunning_kruger(self) -> Dict[str, Any]:
        """
        检测Dunning-Kruger效应

        第一性原理：低能力者高估自己，高能力者低估自己
        """
        with self._lock:
            completed = [e for e in self._evaluations if e.actual_performance is not None]

        if len(completed) < 2:
            return {"detected": False, "low_ability_overestimate": 0.0, "high_ability_underestimate": 0.0}

        # 按实际表现分组
        sorted_evals = sorted(completed, key=lambda e: e.actual_performance)
        n = len(sorted_evals)
        low_third = sorted_evals[:n // 3]
        high_third = sorted_evals[2 * n // 3:]

        low_overestimate = 0.0
        if low_third:
            low_predicted = sum(e.predicted_performance for e in low_third) / len(low_third)
            low_actual = sum(e.actual_performance for e in low_third) / len(low_third)
            low_overestimate = low_predicted - low_actual

        high_underestimate = 0.0
        if high_third:
            high_predicted = sum(e.predicted_performance for e in high_third) / len(high_third)
            high_actual = sum(e.actual_performance for e in high_third) / len(high_third)
            high_underestimate = high_actual - high_predicted

        return {
            "detected": low_overestimate > 0.1 and high_underestimate > 0.1,
            "low_ability_overestimate": low_overestimate,
            "high_ability_underestimate": high_underestimate,
        }

    def get_bias_summary(self) -> Dict[str, Any]:
        """获取偏差总结"""
        return {
            "overconfidence_bias": self.detect_overconfidence_bias(),
            "dunning_kruger": self.detect_dunning_kruger(),
            "evaluation_count": len(self._evaluations),
        }

    def clear(self) -> None:
        """清空"""
        with self._lock:
            self._evaluations.clear()


# ============================================================
# 阶段119新增：策略优化器
# ============================================================

class StrategyOptimizer:
    """
    策略优化器

    第一性原理：
    - 不同策略在不同情境下表现不同
    - 通过历史表现学习策略-情境匹配
    - 选择期望表现最好的策略
    """

    def __init__(self):
        # strategy_performance[strategy][situation_key] = list of scores
        self._strategy_performance: Dict[CognitiveStrategy, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._lock = threading.RLock()

    def record_performance(
        self,
        strategy: CognitiveStrategy,
        situation: Dict[str, Any],
        performance: float,
    ) -> None:
        """记录策略表现"""
        # 安全转换 performance 为 float
        try:
            performance = float(performance)
        except (TypeError, ValueError):
            return
        # 防御 NaN/Inf
        if math.isnan(performance) or math.isinf(performance):
            return
        performance = max(0.0, min(1.0, performance))

        situation_key = self._situation_key(situation)
        with self._lock:
            self._strategy_performance[strategy][situation_key].append(performance)

    def _situation_key(self, situation: Dict[str, Any]) -> str:
        """将情境转化为键"""
        if not isinstance(situation, dict):
            return "default"
        complexity = situation.get("complexity", 0.5)
        urgency = situation.get("urgency", 0.5)
        # 离散化为桶
        c_bucket = "high" if complexity > 0.66 else ("low" if complexity < 0.33 else "mid")
        u_bucket = "high" if urgency > 0.66 else ("low" if urgency < 0.33 else "mid")
        return f"c_{c_bucket}_u_{u_bucket}"

    def get_average_performance(
        self,
        strategy: CognitiveStrategy,
        situation: Dict[str, Any],
    ) -> float:
        """获取策略在情境下的平均表现"""
        situation_key = self._situation_key(situation)
        with self._lock:
            scores = self._strategy_performance.get(strategy, {}).get(situation_key, [])
        if not scores:
            return 0.5  # 无数据时返回中性值
        return sum(scores) / len(scores)

    def recommend_strategy(self, situation: Dict[str, Any]) -> Tuple[CognitiveStrategy, float]:
        """
        推荐策略

        第一性原理：选择在相似情境下历史表现最好的策略
        Returns: (推荐策略, 预期表现)
        """
        best_strategy = CognitiveStrategy.SEQUENTIAL
        best_score = -1.0

        with self._lock:
            for strategy in CognitiveStrategy:
                avg = self.get_average_performance(strategy, situation)
                if avg > best_score:
                    best_score = avg
                    best_strategy = strategy

        return best_strategy, max(0.0, best_score)

    def get_strategy_stats(self) -> Dict[str, Any]:
        """获取策略统计"""
        with self._lock:
            stats = {}
            for strategy, situations in self._strategy_performance.items():
                all_scores = []
                for scores in situations.values():
                    all_scores.extend(scores)
                if all_scores:
                    stats[strategy.value] = {
                        "count": len(all_scores),
                        "avg_performance": sum(all_scores) / len(all_scores),
                    }
            return stats

    def clear(self) -> None:
        """清空"""
        with self._lock:
            self._strategy_performance.clear()


# ============================================================
# 阶段119新增：反思日志
# ============================================================

@dataclass
class ReflectionEntry:
    """
    反思条目

    第一性原理：反思是从经验中提取可复用知识的过程
    """
    reflection_id: str
    task_id: str
    what_worked: List[str] = field(default_factory=list)
    what_failed: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    strategy_used: Optional[CognitiveStrategy] = None
    outcome_score: float = 0.5
    timestamp: float = field(default_factory=time.time)


class ReflectionLog:
    """
    反思日志

    第一性原理：
    - 反思是将经验转化为知识的过程
    - 成功和失败的经验都应被记录
    - 反思可指导未来策略选择
    """

    def __init__(self, max_entries: int = 1000):
        self._entries: List[ReflectionEntry] = []
        self._max_entries = max_entries
        self._lock = threading.RLock()

    def add_reflection(self, entry: ReflectionEntry) -> None:
        """添加反思"""
        with self._lock:
            self._entries.append(entry)
            # 容量管理
            while len(self._entries) > self._max_entries:
                self._entries.pop(0)

    def get_reflections_by_task(self, task_id: str) -> List[ReflectionEntry]:
        """按任务获取反思"""
        with self._lock:
            return [e for e in self._entries if e.task_id == task_id]

    def get_reflections_by_strategy(self, strategy: CognitiveStrategy) -> List[ReflectionEntry]:
        """按策略获取反思"""
        with self._lock:
            return [e for e in self._entries if e.strategy_used == strategy]

    def get_successful_reflections(self, threshold: float = 0.7) -> List[ReflectionEntry]:
        """获取成功反思"""
        with self._lock:
            return [e for e in self._entries if e.outcome_score >= threshold]

    def get_failed_reflections(self, threshold: float = 0.3) -> List[ReflectionEntry]:
        """获取失败反思"""
        with self._lock:
            return [e for e in self._entries if e.outcome_score < threshold]

    def get_common_lessons(self, top_n: int = 5) -> List[Tuple[str, int]]:
        """获取常见教训"""
        with self._lock:
            lesson_counts: Dict[str, int] = defaultdict(int)
            for entry in self._entries:
                for lesson in entry.lessons_learned:
                    lesson_counts[lesson] += 1
            sorted_lessons = sorted(lesson_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_lessons[:top_n]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "total_reflections": len(self._entries),
                "success_count": sum(1 for e in self._entries if e.outcome_score >= 0.7),
                "failure_count": sum(1 for e in self._entries if e.outcome_score < 0.3),
            }

    def clear(self) -> None:
        """清空"""
        with self._lock:
            self._entries.clear()


# ============================================================
# 元认知第一性原理引擎（增强版）
# ============================================================

class MetacognitionFirstPrinciplesEngine:
    """
    元认知第一性原理引擎（阶段119增强版）

    新增能力:
    - 多维度自我评估（SelfEvaluation）
    - 认知偏差检测（CognitiveBiasDetector）
    - 策略优化（StrategyOptimizer）
    - 反思日志（ReflectionLog）

    向后兼容: 保留原有 assess_task / select_strategy / record_outcome 接口
    """

    def __init__(self, engine_id: str = "metacognition_engine"):
        self.engine_id = engine_id
        self._current_state = CognitiveState(state_id="current")
        self._assessments: List[SelfAssessment] = []
        self._evaluations: List[SelfEvaluation] = []
        self._strategy_history: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._cycle_count = 0

        # 阶段119新增组件
        self._bias_detector = CognitiveBiasDetector()
        self._strategy_optimizer = StrategyOptimizer()
        self._reflection_log = ReflectionLog()

    # ============================================================
    # 原有接口（向后兼容）
    # ============================================================

    def update_state(
        self,
        task_complexity: Optional[float] = None,
        cognitive_load: Optional[float] = None,
        fatigue_level: Optional[float] = None,
        focus_level: Optional[float] = None,
    ) -> None:
        """更新认知状态"""
        with self._lock:
            if task_complexity is not None:
                self._current_state.task_complexity = max(0.0, min(1.0, self._safe_float(task_complexity, 0.5)))
            if cognitive_load is not None:
                self._current_state.cognitive_load = max(0.0, min(1.0, self._safe_float(cognitive_load, 0.5)))
            if fatigue_level is not None:
                self._current_state.fatigue_level = max(0.0, min(1.0, self._safe_float(fatigue_level, 0.0)))
            if focus_level is not None:
                self._current_state.focus_level = max(0.0, min(1.0, self._safe_float(focus_level, 0.5)))
            self._current_state.timestamp = time.time()

    @staticmethod
    def _safe_float(val: Any, default: float = 0.0) -> float:
        """安全的浮点转换"""
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return default
            return f
        except (TypeError, ValueError):
            return default

    def assess_task(self, task_id: str, task_features: Dict[str, Any]) -> SelfAssessment:
        """评估任务（向后兼容）"""
        if not isinstance(task_features, dict):
            task_features = {}
        complexity = self._safe_float(task_features.get("complexity", 0.5), 0.5)
        required_capacity = self._safe_float(task_features.get("required_capacity", 0.5), 0.5)

        with self._lock:
            available = self._current_state.capacity_available

        if required_capacity > 0:
            predicted = min(1.0, available / required_capacity)
        else:
            predicted = 1.0

        if predicted > 0.8:
            confidence = ConfidenceLevel.HIGH
        elif predicted > 0.5:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

        assessment = SelfAssessment(
            assessment_id=f"assess_{int(time.time() * 1000)}_{self._cycle_count}",
            task_id=task_id,
            predicted_performance=predicted,
            confidence=confidence,
        )

        with self._lock:
            self._assessments.append(assessment)
            self._cycle_count += 1

        return assessment

    def select_strategy(self, task_features: Dict[str, Any]) -> CognitiveStrategy:
        """选择认知策略（向后兼容）"""
        if not isinstance(task_features, dict):
            task_features = {}
        with self._lock:
            state = self._current_state

        complexity = self._safe_float(task_features.get("complexity", 0.5), 0.5)
        urgency = self._safe_float(task_features.get("urgency", 0.5), 0.5)

        if state.fatigue_level > 0.6:
            return CognitiveStrategy.SHALLOW_PROCESSING

        if urgency > 0.8 and complexity < 0.5:
            return CognitiveStrategy.HEURISTIC

        if complexity > 0.7:
            return CognitiveStrategy.DEEP_PROCESSING

        if state.capacity_available > 0.6:
            return CognitiveStrategy.PARALLEL

        return CognitiveStrategy.SEQUENTIAL

    def record_outcome(self, task_id: str, actual_performance: float) -> None:
        """记录实际表现（向后兼容）"""
        actual_performance = self._safe_float(actual_performance, 0.0)
        with self._lock:
            for assessment in reversed(self._assessments):
                if assessment.task_id == task_id and assessment.actual_performance is None:
                    assessment.actual_performance = actual_performance
                    break

    def get_calibration_accuracy(self) -> float:
        """获取自我评估校准度（向后兼容）"""
        with self._lock:
            completed = [a for a in self._assessments if a.actual_performance is not None]

        if not completed:
            return 0.0

        errors = [abs(a.predicted_performance - a.actual_performance) for a in completed]
        avg_error = sum(errors) / len(errors)
        return max(0.0, 1.0 - avg_error)

    def get_recommended_action(self) -> str:
        """获取推荐行动（向后兼容）"""
        with self._lock:
            state = self._current_state

        if state.needs_rest:
            return "rest"
        if state.capacity_available < 0.3:
            return "simplify_task"
        if state.focus_level < 0.3:
            return "refocus"
        return "proceed"

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            base_stats = {
                "engine_id": self.engine_id,
                "cycle_count": self._cycle_count,
                "current_state": {
                    "capacity_available": self._current_state.capacity_available,
                    "needs_rest": self._current_state.needs_rest,
                    "cognitive_load": self._current_state.cognitive_load,
                },
                "assessments_count": len(self._assessments),
                "calibration_accuracy": self.get_calibration_accuracy(),
                "recommended_action": self.get_recommended_action(),
            }
            # 阶段119新增统计
            base_stats["evaluations_count"] = len(self._evaluations)
            base_stats["bias_summary"] = self._bias_detector.get_bias_summary()
            base_stats["strategy_stats"] = self._strategy_optimizer.get_strategy_stats()
            base_stats["reflection_stats"] = self._reflection_log.get_stats()
            return base_stats

    def reset(self) -> None:
        """重置"""
        with self._lock:
            self._current_state = CognitiveState(state_id="current")
            self._assessments.clear()
            self._evaluations.clear()
            self._strategy_history.clear()
            self._cycle_count = 0
            self._bias_detector.clear()
            self._strategy_optimizer.clear()
            self._reflection_log.clear()

    # ============================================================
    # 阶段119新增：多维度自我评估接口
    # ============================================================

    def evaluate_self(
        self,
        task_id: str,
        accuracy: float = 0.5,
        speed: float = 0.5,
        efficiency: float = 0.5,
        confidence: float = 0.5,
        predicted_performance: float = 0.5,
        actual_performance: Optional[float] = None,
        strategy_used: Optional[CognitiveStrategy] = None,
    ) -> SelfEvaluation:
        """
        多维度自我评估

        第一性原理：自我评估应涵盖多个认知维度
        """
        evaluation = SelfEvaluation(
            evaluation_id=f"eval_{int(time.time() * 1000)}_{self._cycle_count}",
            task_id=task_id,
            accuracy=max(0.0, min(1.0, self._safe_float(accuracy, 0.5))),
            speed=max(0.0, min(1.0, self._safe_float(speed, 0.5))),
            efficiency=max(0.0, min(1.0, self._safe_float(efficiency, 0.5))),
            confidence=max(0.0, min(1.0, self._safe_float(confidence, 0.5))),
            predicted_performance=max(0.0, min(1.0, self._safe_float(predicted_performance, 0.5))),
            actual_performance=self._safe_float(actual_performance, None) if actual_performance is not None else None,
            strategy_used=strategy_used,
        )

        with self._lock:
            self._evaluations.append(evaluation)
            self._bias_detector.add_evaluation(evaluation)
            self._cycle_count += 1

            # 如果有策略和实际表现，记录到策略优化器
            if strategy_used is not None and actual_performance is not None:
                situation = {
                    "complexity": self._current_state.task_complexity,
                    "urgency": 0.5,  # 默认
                }
                self._strategy_optimizer.record_performance(strategy_used, situation, actual_performance)

        return evaluation

    def detect_bias(self) -> Dict[str, Any]:
        """检测认知偏差"""
        return self._bias_detector.get_bias_summary()

    def recommend_strategy(self, situation: Dict[str, Any]) -> Tuple[CognitiveStrategy, float]:
        """推荐策略（基于历史表现）"""
        return self._strategy_optimizer.recommend_strategy(situation)

    def reflect(
        self,
        task_id: str,
        what_worked: List[str],
        what_failed: List[str],
        lessons_learned: List[str],
        strategy_used: Optional[CognitiveStrategy] = None,
        outcome_score: float = 0.5,
    ) -> ReflectionEntry:
        """
        反思

        第一性原理：反思是从经验中提取可复用知识的过程
        """
        entry = ReflectionEntry(
            reflection_id=f"reflect_{int(time.time() * 1000)}_{self._cycle_count}",
            task_id=task_id,
            what_worked=list(what_worked) if what_worked else [],
            what_failed=list(what_failed) if what_failed else [],
            lessons_learned=list(lessons_learned) if lessons_learned else [],
            strategy_used=strategy_used,
            outcome_score=max(0.0, min(1.0, self._safe_float(outcome_score, 0.5))),
        )

        with self._lock:
            self._reflection_log.add_reflection(entry)
            self._cycle_count += 1

        return entry

    def get_reflections(self, task_id: Optional[str] = None) -> List[ReflectionEntry]:
        """获取反思"""
        with self._lock:
            if task_id is None:
                return list(self._reflection_log._entries)
            return self._reflection_log.get_reflections_by_task(task_id)

    def get_common_lessons(self, top_n: int = 5) -> List[Tuple[str, int]]:
        """获取常见教训"""
        return self._reflection_log.get_common_lessons(top_n)

    def get_evaluations(self) -> List[SelfEvaluation]:
        """获取所有评估"""
        with self._lock:
            return list(self._evaluations)

    def get_bias_detector(self) -> CognitiveBiasDetector:
        """获取偏差检测器"""
        return self._bias_detector

    def get_strategy_optimizer(self) -> StrategyOptimizer:
        """获取策略优化器"""
        return self._strategy_optimizer

    def get_reflection_log(self) -> ReflectionLog:
        """获取反思日志"""
        return self._reflection_log


# ============================================================
# 便捷函数（向后兼容 + 新增）
# ============================================================

def create_metacognition_engine(engine_id: str = "metacognition_engine") -> MetacognitionFirstPrinciplesEngine:
    """创建元认知引擎"""
    return MetacognitionFirstPrinciplesEngine(engine_id=engine_id)


def create_self_evaluation(
    task_id: str,
    accuracy: float = 0.5,
    speed: float = 0.5,
    efficiency: float = 0.5,
    confidence: float = 0.5,
) -> SelfEvaluation:
    """创建自我评估"""
    return SelfEvaluation(
        evaluation_id=f"eval_{int(time.time() * 1000)}",
        task_id=task_id,
        accuracy=accuracy,
        speed=speed,
        efficiency=efficiency,
        confidence=confidence,
    )


def create_reflection_entry(
    task_id: str,
    what_worked: List[str] = None,
    what_failed: List[str] = None,
    lessons_learned: List[str] = None,
) -> ReflectionEntry:
    """创建反思条目"""
    return ReflectionEntry(
        reflection_id=f"reflect_{int(time.time() * 1000)}",
        task_id=task_id,
        what_worked=what_worked or [],
        what_failed=what_failed or [],
        lessons_learned=lessons_learned or [],
    )
