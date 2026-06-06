"""
阶段71: 预测编码第一性原理化

第一性原理:
1. 智能的本质是预测：大脑是预测机器，而非反应机器
2. 感知是预测的反过程：我们看到的是预测，而非原始输入
3. 学习是减小预测误差：所有参数更新服务于更好的预测

设计原则:
- Prediction: 对下一时刻状态的预测
- PredictionError: 预测与实际之间的差异
- Precision: 误差的精度（可信度），决定更新权重
- PredictiveCodingEngine: 统一协调预测、误差计算、修正
- 所有模块行为必须可解释为预测或修正
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum


class PrecisionWeight(Enum):
    """精度权重级别"""
    HIGH = 1.0      # 高可信度，误差权重最大
    MEDIUM = 0.5    # 中等可信度
    LOW = 0.1       # 低可信度，可能是噪声
    IGNORE = 0.0    # 完全忽略


@dataclass
class Prediction:
    """预测结果"""
    prediction_id: str
    timestamp: float
    predicted_state: Dict[str, Any]
    confidence: float = 0.5           # 预测置信度 [0,1]
    time_horizon: float = 1.0         # 预测时间跨度（秒）
    source: str = "unknown"           # 预测来源模块


@dataclass
class PredictionError:
    """预测误差"""
    error_id: str
    prediction_id: str
    timestamp: float
    error_vector: Dict[str, float]    # 各维度误差
    precision: PrecisionWeight = PrecisionWeight.MEDIUM
    surprise: float = 0.0             # 惊奇度 = -log(预测概率)

    @property
    def weighted_error(self) -> float:
        """加权误差"""
        if not self.error_vector:
            return 0.0
        avg_error = sum(abs(v) for v in self.error_vector.values()) / len(self.error_vector)
        return avg_error * self.precision.value


@dataclass
class Correction:
    """修正动作"""
    correction_id: str
    error_id: str
    timestamp: float
    parameter_updates: Dict[str, float]  # 参数更新量
    update_magnitude: float = 0.0        # 更新幅度
    target_module: str = "unknown"


# ============================================================
# 预测编码引擎
# ============================================================

class PredictiveCodingEngine:
    """
    预测编码引擎

    统一协调预测、误差计算和修正，确保所有认知行为
    都可追溯到预测-修正循环。

    核心循环:
    1. 生成预测 -> Prediction
    2. 接收实际状态 -> 计算误差 -> PredictionError
    3. 根据精度加权误差 -> 生成修正 -> Correction
    4. 应用修正到模型参数
    """

    def __init__(self, engine_id: str = "predictive_coding"):
        self.engine_id = engine_id
        self._predictions: Dict[str, Prediction] = {}
        self._errors: Dict[str, PredictionError] = {}
        self._corrections: Dict[str, Correction] = {}
        self._predictors: Dict[str, Callable[[Dict[str, Any]], Prediction]] = {}
        self._correctors: Dict[str, Callable[[PredictionError], Correction]] = {}
        self._lock = threading.RLock()
        self._cycle_count = 0
        self._total_surprise = 0.0

    def register_predictor(
        self,
        module_id: str,
        predictor: Callable[[Dict[str, Any]], Prediction],
    ) -> None:
        """注册预测器"""
        with self._lock:
            self._predictors[module_id] = predictor

    def register_corrector(
        self,
        module_id: str,
        corrector: Callable[[PredictionError], Correction],
    ) -> None:
        """注册修正器"""
        with self._lock:
            self._correctors[module_id] = corrector

    def generate_prediction(
        self,
        module_id: str,
        current_state: Dict[str, Any],
    ) -> Optional[Prediction]:
        """
        生成预测

        第一性原理：所有行为始于预测
        """
        with self._lock:
            predictor = self._predictors.get(module_id)
        if predictor is None:
            return None

        prediction = predictor(current_state)
        with self._lock:
            self._predictions[prediction.prediction_id] = prediction
        return prediction

    def compute_error(
        self,
        prediction: Prediction,
        actual_state: Dict[str, Any],
        precision: PrecisionWeight = PrecisionWeight.MEDIUM,
    ) -> PredictionError:
        """
        计算预测误差

        第一性原理：误差是学习的唯一信号
        """
        error_vector: Dict[str, float] = {}
        for key, predicted in prediction.predicted_state.items():
            actual = actual_state.get(key)
            if actual is not None:
                try:
                    error_vector[key] = float(actual) - float(predicted)
                except (TypeError, ValueError):
                    error_vector[key] = 0.0 if actual == predicted else 1.0

        # 计算惊奇度（简单实现：误差越大越惊奇）
        surprise = sum(e ** 2 for e in error_vector.values()) ** 0.5

        error = PredictionError(
            error_id=f"err_{prediction.prediction_id}_{int(time.time() * 1000)}",
            prediction_id=prediction.prediction_id,
            timestamp=time.time(),
            error_vector=error_vector,
            precision=precision,
            surprise=surprise,
        )

        with self._lock:
            self._errors[error.error_id] = error
            self._total_surprise += surprise

        return error

    def generate_correction(
        self,
        module_id: str,
        error: PredictionError,
    ) -> Optional[Correction]:
        """
        生成修正

        第一性原理：修正的方向是减小未来误差
        """
        with self._lock:
            corrector = self._correctors.get(module_id)
        if corrector is None:
            return None

        correction = corrector(error)
        with self._lock:
            self._corrections[correction.correction_id] = correction
            self._cycle_count += 1

        return correction

    def run_cycle(
        self,
        module_id: str,
        current_state: Dict[str, Any],
        actual_state: Dict[str, Any],
        precision: PrecisionWeight = PrecisionWeight.MEDIUM,
    ) -> Tuple[Optional[Prediction], Optional[PredictionError], Optional[Correction]]:
        """
        执行完整预测-修正循环

        这是预测编码的核心：预测 -> 比较 -> 修正
        """
        prediction = self.generate_prediction(module_id, current_state)
        if prediction is None:
            return None, None, None

        error = self.compute_error(prediction, actual_state, precision)
        correction = self.generate_correction(module_id, error)

        return prediction, error, correction

    def get_free_energy_estimate(self) -> float:
        """
        估计自由能

        自由能 ≈ 预测误差 + 模型复杂度
        这里简化为累积惊奇度
        """
        with self._lock:
            return self._total_surprise

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "engine_id": self.engine_id,
                "predictions_count": len(self._predictions),
                "errors_count": len(self._errors),
                "corrections_count": len(self._corrections),
                "cycle_count": self._cycle_count,
                "free_energy_estimate": self._total_surprise,
                "registered_predictors": list(self._predictors.keys()),
                "registered_correctors": list(self._correctors.keys()),
            }

    def clear_history(self) -> None:
        """清除历史"""
        with self._lock:
            self._predictions.clear()
            self._errors.clear()
            self._corrections.clear()
            self._total_surprise = 0.0


# ============================================================
# 便捷函数
# ============================================================

def create_predictive_coding_engine(engine_id: str = "predictive_coding") -> PredictiveCodingEngine:
    """创建预测编码引擎"""
    return PredictiveCodingEngine(engine_id=engine_id)


def create_prediction(
    prediction_id: str,
    predicted_state: Dict[str, Any],
    confidence: float = 0.5,
    time_horizon: float = 1.0,
    source: str = "unknown",
) -> Prediction:
    """创建预测"""
    return Prediction(
        prediction_id=prediction_id,
        timestamp=time.time(),
        predicted_state=predicted_state,
        confidence=confidence,
        time_horizon=time_horizon,
        source=source,
    )


def create_prediction_error(
    error_id: str,
    prediction_id: str,
    error_vector: Dict[str, float],
    precision: PrecisionWeight = PrecisionWeight.MEDIUM,
    surprise: float = 0.0,
) -> PredictionError:
    """创建预测误差"""
    return PredictionError(
        error_id=error_id,
        prediction_id=prediction_id,
        timestamp=time.time(),
        error_vector=error_vector,
        precision=precision,
        surprise=surprise,
    )


def create_correction(
    correction_id: str,
    error_id: str,
    parameter_updates: Dict[str, float],
    update_magnitude: float = 0.0,
    target_module: str = "unknown",
) -> Correction:
    """创建修正"""
    return Correction(
        correction_id=correction_id,
        error_id=error_id,
        timestamp=time.time(),
        parameter_updates=parameter_updates,
        update_magnitude=update_magnitude,
        target_module=target_module,
    )
