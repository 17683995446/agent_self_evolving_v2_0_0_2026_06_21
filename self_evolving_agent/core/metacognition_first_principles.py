"""
阶段82: 元认知第一性原理化

第一性原理:
1. 认知自身才能优化认知：不知道自己在想什么就无法改进
2. 元认知是监控和调节认知过程的能力
3. 系统必须能评估自身认知状态

设计原则:
- CognitiveState: 认知状态
- MetacognitiveMonitor: 元认知监控
- MetacognitionFirstPrinciplesEngine: 元认知引擎
- 支持自我监控、策略选择、认知负荷管理
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class CognitiveStrategy(Enum):
    """认知策略"""
    DEEP_PROCESSING = "deep"           # 深度处理
    SHALLOW_PROCESSING = "shallow"     # 浅层处理
    PARALLEL = "parallel"              # 并行处理
    SEQUENTIAL = "sequential"          # 串行处理
    HEURISTIC = "heuristic"            # 启发式
    ANALYTIC = "analytic"              # 分析式


class ConfidenceLevel(Enum):
    """置信水平"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class CognitiveState:
    """认知状态"""
    state_id: str
    task_complexity: float = 0.5        # 任务复杂度 [0,1]
    cognitive_load: float = 0.5         # 认知负荷 [0,1]
    fatigue_level: float = 0.0          # 疲劳度 [0,1]
    focus_level: float = 0.5            # 专注度 [0,1]
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
    """自我评估"""
    assessment_id: str
    task_id: str
    predicted_performance: float = 0.5   # 预测表现 [0,1]
    actual_performance: Optional[float] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 元认知第一性原理引擎
# ============================================================

class MetacognitionFirstPrinciplesEngine:
    """
    元认知第一性原理引擎

    核心原则：系统必须能评估自身认知状态

    第一性原理推导:
    1. 认知过程可以被观察
    2. 观察结果可以被评估
    3. 评估可以指导策略调整
    4. 自我监控是优化的前提
    """

    def __init__(self, engine_id: str = "metacognition_engine"):
        self.engine_id = engine_id
        self._current_state = CognitiveState(state_id="current")
        self._assessments: List[SelfAssessment] = []
        self._strategy_history: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._cycle_count = 0

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
                self._current_state.task_complexity = max(0.0, min(1.0, task_complexity))
            if cognitive_load is not None:
                self._current_state.cognitive_load = max(0.0, min(1.0, cognitive_load))
            if fatigue_level is not None:
                self._current_state.fatigue_level = max(0.0, min(1.0, fatigue_level))
            if focus_level is not None:
                self._current_state.focus_level = max(0.0, min(1.0, focus_level))
            self._current_state.timestamp = time.time()

    def assess_task(self, task_id: str, task_features: Dict[str, Any]) -> SelfAssessment:
        """
        评估任务难度和自身能力匹配

        第一性原理：知道任务多难，才知道该用什么策略
        """
        # 阶段104修复：None 或非字典输入防御
        if not isinstance(task_features, dict):
            task_features = {}
        complexity = task_features.get("complexity", 0.5)
        required_capacity = task_features.get("required_capacity", 0.5)

        with self._lock:
            available = self._current_state.capacity_available

        # 预测表现 = 可用容量 / 需求容量
        if required_capacity > 0:
            predicted = min(1.0, available / required_capacity)
        else:
            predicted = 1.0

        # 置信度
        if predicted > 0.8:
            confidence = ConfidenceLevel.HIGH
        elif predicted > 0.5:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

        assessment = SelfAssessment(
            assessment_id=f"assess_{int(time.time() * 1000)}",
            task_id=task_id,
            predicted_performance=predicted,
            confidence=confidence,
        )

        with self._lock:
            self._assessments.append(assessment)
            self._cycle_count += 1

        return assessment

    def select_strategy(self, task_features: Dict[str, Any]) -> CognitiveStrategy:
        """
        选择认知策略

        第一性原理：策略必须匹配当前认知状态
        """
        # 阶段104修复：None 或非字典输入防御
        if not isinstance(task_features, dict):
            task_features = {}
        with self._lock:
            state = self._current_state

        complexity = task_features.get("complexity", 0.5)
        urgency = task_features.get("urgency", 0.5)

        if state.fatigue_level > 0.6:
            # 疲劳时选择简单策略
            return CognitiveStrategy.SHALLOW_PROCESSING

        if urgency > 0.8 and complexity < 0.5:
            # 紧急且简单：启发式
            return CognitiveStrategy.HEURISTIC

        if complexity > 0.7:
            # 复杂任务：深度分析
            return CognitiveStrategy.DEEP_PROCESSING

        if state.capacity_available > 0.6:
            # 容量充足：并行处理
            return CognitiveStrategy.PARALLEL

        return CognitiveStrategy.SEQUENTIAL

    def record_outcome(self, task_id: str, actual_performance: float) -> None:
        """记录实际表现，用于校准自我评估"""
        with self._lock:
            for assessment in reversed(self._assessments):
                if assessment.task_id == task_id and assessment.actual_performance is None:
                    assessment.actual_performance = actual_performance
                    break

    def get_calibration_accuracy(self) -> float:
        """
        获取自我评估校准度

        第一性原理：准确的自我认知是有效元认知的基础
        """
        with self._lock:
            completed = [a for a in self._assessments if a.actual_performance is not None]

        if not completed:
            return 0.0

        errors = [abs(a.predicted_performance - a.actual_performance) for a in completed]
        avg_error = sum(errors) / len(errors)
        return max(0.0, 1.0 - avg_error)

    def get_recommended_action(self) -> str:
        """
        获取推荐行动

        基于当前认知状态给出建议
        """
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
            return {
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

    def reset(self) -> None:
        """重置"""
        with self._lock:
            self._current_state = CognitiveState(state_id="current")
            self._assessments.clear()
            self._strategy_history.clear()
            self._cycle_count = 0


# ============================================================
# 便捷函数
# ============================================================

def create_metacognition_engine(engine_id: str = "metacognition_engine") -> MetacognitionFirstPrinciplesEngine:
    """创建元认知引擎"""
    return MetacognitionFirstPrinciplesEngine(engine_id=engine_id)
