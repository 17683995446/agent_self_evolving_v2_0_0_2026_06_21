"""
自驱永续进化Agent系统 — 评估器
阶段8：评估器解耦

第一性原理：误差是客观度量，反馈是主观解释
- ErrorCalculator：只计算数值误差
- FeedbackGenerator：将误差转化为反馈信号
"""

import numpy as np
from typing import Dict, Any, Optional
from collections import deque

from ..core.interfaces import (
    ErrorCalculator, FeedbackGenerator, ErrorMetrics,
    BaseModule, AgentMessage, MessageType
)


class PredictionErrorCalculator(ErrorCalculator, BaseModule):
    """
    预测误差计算器

    计算预测值与实际值之间的客观差异
    """

    def __init__(self, module_id: str = "error_calculator"):
        BaseModule.__init__(self, module_id)
        self._error_history: deque = deque(maxlen=100)

    def calculate(self, predicted: Dict[str, Any],
                  actual: Dict[str, Any]) -> ErrorMetrics:
        """
        计算预测误差

        使用均方误差（MSE）作为基础度量
        """
        errors = []
        for key in actual:
            if key in predicted:
                try:
                    pred_val = float(predicted[key])
                    act_val = float(actual[key])
                    errors.append((pred_val - act_val) ** 2)
                except (ValueError, TypeError):
                    pass

        mse = np.mean(errors) if errors else 0.0
        rmse = np.sqrt(mse)

        # 复杂度代价（简化：与预测字段数成正比）
        complexity_cost = len(predicted) * 0.01

        # 自由能近似 = 误差 + 复杂度
        free_energy = rmse + complexity_cost

        metrics = ErrorMetrics(
            prediction_error=rmse,
            complexity_cost=complexity_cost,
            free_energy=free_energy,
        )

        self._error_history.append(metrics)
        return metrics

    def initialize(self, config: Dict[str, Any]) -> None:
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.PREDICTION:
            pred = message.payload.get("prediction", {})
            # 需要实际状态来计算误差，这里只记录预测
            return None
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        if self._error_history:
            recent = list(self._error_history)[-10:]
            base.update({
                "mean_error": np.mean([e.prediction_error for e in recent]),
                "mean_free_energy": np.mean([e.free_energy for e in recent]),
            })
        return base


class DriveFeedbackGenerator(FeedbackGenerator, BaseModule):
    """
    驱力反馈生成器

    将客观误差转化为驱力系统的反馈信号
    """

    def __init__(self, module_id: str = "feedback_generator"):
        BaseModule.__init__(self, module_id)
        self._error_threshold = 0.3

    def generate(self, error_metrics: ErrorMetrics) -> Dict[str, Any]:
        """
        基于误差生成反馈

        反馈类型：
        - 预测误差大 -> 增加gain驱力（需要更多信息）
        - 自由能高 -> 增加eff驱力（需要更高效的模型）
        - 误差突增 -> 增加safe驱力（检测到异常）
        """
        feedback = {
            "timestamp": error_metrics.timestamp.isoformat(),
            "signals": {},
        }

        # 预测误差反馈
        if error_metrics.prediction_error > self._error_threshold:
            feedback["signals"]["gain"] = {
                "strength": min(1.0, error_metrics.prediction_error),
                "reason": "high_prediction_error",
            }

        # 复杂度反馈
        if error_metrics.complexity_cost > 0.1:
            feedback["signals"]["eff"] = {
                "strength": min(1.0, error_metrics.complexity_cost * 5),
                "reason": "high_complexity",
            }

        # 安全反馈（误差突增检测）
        if error_metrics.free_energy > 1.0:
            feedback["signals"]["safe"] = {
                "strength": min(1.0, error_metrics.free_energy / 2),
                "reason": "high_free_energy",
            }

        return feedback

    def initialize(self, config: Dict[str, Any]) -> None:
        self._error_threshold = config.get("error_threshold", self._error_threshold)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.ERROR_SIGNAL:
            # 从消息中提取误差指标
            payload = message.payload
            metrics = ErrorMetrics(
                prediction_error=payload.get("prediction_error", 0),
                complexity_cost=payload.get("complexity_cost", 0),
                free_energy=payload.get("free_energy", 0),
            )
            feedback = self.generate(metrics)
            return AgentMessage(
                msg_type=MessageType.LEARNING_SIGNAL,
                source=self.module_id,
                payload=feedback,
            )
        return None


class UnifiedEvaluator(BaseModule):
    """
    统一评估器

    协调误差计算和反馈生成
    """

    def __init__(self, module_id: str = "evaluator"):
        super().__init__(module_id)
        self._error_calculator = PredictionErrorCalculator()
        self._feedback_generator = DriveFeedbackGenerator()

    def evaluate(self, predicted: Dict[str, Any],
                 actual: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行完整评估流程

        1. 计算客观误差
        2. 生成主观反馈
        """
        # 计算误差
        metrics = self._error_calculator.calculate(predicted, actual)

        # 生成反馈
        feedback = self._feedback_generator.generate(metrics)

        return {
            "metrics": {
                "prediction_error": metrics.prediction_error,
                "complexity_cost": metrics.complexity_cost,
                "free_energy": metrics.free_energy,
            },
            "feedback": feedback,
        }

    def initialize(self, config: Dict[str, Any]) -> None:
        self._error_calculator.initialize(config.get("error", {}))
        self._feedback_generator.initialize(config.get("feedback", {}))
        self._initialized = True

    def start(self) -> None:
        self._running = True
        self._error_calculator.start()
        self._feedback_generator.start()

    def stop(self) -> None:
        self._running = False
        self._error_calculator.stop()
        self._feedback_generator.stop()

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.STATE_UPDATE:
            # 需要预测和实际状态来评估
            payload = message.payload
            if "predicted" in payload and "actual" in payload:
                result = self.evaluate(payload["predicted"], payload["actual"])
                return AgentMessage(
                    msg_type=MessageType.LEARNING_SIGNAL,
                    source=self.module_id,
                    payload=result,
                )
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        base.update({
            "error_calculator": self._error_calculator.get_state(),
            "feedback_generator": self._feedback_generator.get_state(),
        })
        return base
