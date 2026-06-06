"""
自驱永续进化Agent系统 — 预测引擎
阶段4：预测引擎接口化

第一性原理：不同层级的预测本质相同，只是时间尺度不同
- 底层：下一时刻的精确状态
- 中层：短期趋势
- 高层：长期模式
"""

import numpy as np
from typing import Dict, Any, List, Optional
from collections import deque

from ..core.interfaces import Predictor, Prediction, BaseModule, AgentMessage, MessageType


class BasePredictor(Predictor, BaseModule):
    """
    预测器基类

    实现Predictor接口和BaseModule接口的统一
    """

    def __init__(self, module_id: str, horizon: int = 1):
        BaseModule.__init__(self, module_id)
        self.horizon = horizon
        self._history: deque = deque(maxlen=1000)
        self._error_history: deque = deque(maxlen=100)

    def predict(self, current_state: Dict[str, Any],
                horizon: int = 1) -> Prediction:
        raise NotImplementedError

    def update(self, actual_state: Dict[str, Any],
               predicted_state: Dict[str, Any]) -> None:
        """记录历史用于学习"""
        self._history.append({
            "actual": actual_state,
            "predicted": predicted_state,
        })
        # 计算简单误差
        error = self._compute_error(actual_state, predicted_state)
        self._error_history.append(error)

    def get_model_state(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "horizon": self.horizon,
            "history_size": len(self._history),
            "mean_error": np.mean(list(self._error_history)) if self._error_history else 0.0,
        }

    def initialize(self, config: Dict[str, Any]) -> None:
        self.horizon = config.get("horizon", self.horizon)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.STATE_UPDATE:
            # 收到状态更新，进行预测
            state = message.payload.get("state", {})
            prediction = self.predict(state)
            return AgentMessage(
                msg_type=MessageType.PREDICTION,
                source=self.module_id,
                payload={
                    "prediction": prediction.to_dict() if hasattr(prediction, 'to_dict') else prediction,
                    "horizon": self.horizon,
                }
            )
        return None

    @staticmethod
    def _compute_error(actual: Dict, predicted: Dict) -> float:
        """计算预测误差"""
        errors = []
        for key in actual:
            if key in predicted:
                try:
                    errors.append(abs(float(actual[key]) - float(predicted[key])))
                except (ValueError, TypeError):
                    pass
        return np.mean(errors) if errors else 0.0


class LinearPredictor(BasePredictor):
    """
    线性预测器

    基于最近N个状态的变化趋势进行线性外推
    适用于：短期、平滑变化的状态
    """

    def __init__(self, module_id: str, horizon: int = 1, window_size: int = 5):
        super().__init__(module_id, horizon)
        self.window_size = window_size
        self._state_buffer: deque = deque(maxlen=window_size)

    def predict(self, current_state: Dict[str, Any],
                horizon: int = 1) -> Prediction:
        self._state_buffer.append(current_state)

        if len(self._state_buffer) < 2:
            # 数据不足，返回当前状态
            return Prediction(
                predicted_state=current_state.copy(),
                confidence=0.5,
                uncertainty=1.0,
                horizon=horizon,
            )

        # 对每个数值型字段进行线性外推
        predicted = {}
        confidence_sum = 0.0
        count = 0

        for key in current_state:
            values = []
            for state in self._state_buffer:
                if key in state:
                    try:
                        values.append(float(state[key]))
                    except (ValueError, TypeError):
                        pass

            if len(values) >= 2:
                # 线性回归: y = a * x + b
                x = np.arange(len(values))
                a, b = np.polyfit(x, values, 1)
                next_value = a * len(values) + b
                predicted[key] = next_value

                # 置信度基于拟合质量
                residuals = values - (a * x + b)
                mse = np.mean(residuals ** 2)
                confidence = 1.0 / (1.0 + mse)
                confidence_sum += confidence
                count += 1
            else:
                predicted[key] = current_state[key]

        avg_confidence = confidence_sum / count if count > 0 else 0.5

        return Prediction(
            predicted_state=predicted,
            confidence=min(avg_confidence, 1.0),
            uncertainty=1.0 - avg_confidence,
            horizon=horizon,
            metadata={
                "model": "linear",
                "window_size": self.window_size,
                "buffer_size": len(self._state_buffer),
            }
        )

    def initialize(self, config: Dict[str, Any]) -> None:
        self.window_size = config.get("window_size", self.window_size)
        super().initialize(config)


class MovingAveragePredictor(BasePredictor):
    """
    移动平均预测器

    基于最近N个状态的平均值进行预测
    适用于：噪声较大的状态
    """

    def __init__(self, module_id: str, horizon: int = 1, window_size: int = 10):
        super().__init__(module_id, horizon)
        self.window_size = window_size
        self._state_buffer: deque = deque(maxlen=window_size)

    def predict(self, current_state: Dict[str, Any],
                horizon: int = 1) -> Prediction:
        self._state_buffer.append(current_state)

        predicted = {}
        for key in current_state:
            values = []
            for state in self._state_buffer:
                if key in state:
                    try:
                        values.append(float(state[key]))
                    except (ValueError, TypeError):
                        pass

            if values:
                predicted[key] = np.mean(values)
            else:
                predicted[key] = current_state[key]

        # 置信度与数据量正相关
        confidence = min(len(self._state_buffer) / self.window_size, 1.0) * 0.8

        return Prediction(
            predicted_state=predicted,
            confidence=confidence,
            uncertainty=1.0 - confidence,
            horizon=horizon,
            metadata={
                "model": "moving_average",
                "window_size": self.window_size,
            }
        )


class MultiLayerPredictor(BaseModule):
    """
    多层预测器协调器

    第一性原理：不同层级的预测本质相同，只是时间尺度不同
    - 底层（Layer 0）：下一时刻，快速响应
    - 中层（Layer 1）：短期趋势，平滑噪声
    - 高层（Layer 2）：长期模式，战略判断
    """

    def __init__(self, module_id: str):
        super().__init__(module_id)
        self._layers: Dict[str, BasePredictor] = {}
        self._layer_weights = {
            "low": 0.5,    # 底层权重
            "mid": 0.3,    # 中层权重
            "high": 0.2,   # 高层权重
        }

    def add_layer(self, name: str, predictor: BasePredictor) -> None:
        """添加预测层"""
        self._layers[name] = predictor
        predictor.attach_message_bus(self._message_bus)

    def predict(self, current_state: Dict[str, Any]) -> Dict[str, Prediction]:
        """
        执行多层预测

        Returns:
            各层的预测结果字典
        """
        results = {}
        for name, predictor in self._layers.items():
            results[name] = predictor.predict(current_state)
        return results

    def combine_predictions(self, predictions: Dict[str, Prediction]) -> Prediction:
        """
        加权组合多层预测结果

        第一性原理：综合多个尺度的信息，得到更稳健的预测
        """
        if not predictions:
            return Prediction(
                predicted_state={},
                confidence=0.0,
                uncertainty=1.0,
                horizon=1,
            )

        # 收集所有字段
        all_keys = set()
        for pred in predictions.values():
            all_keys.update(pred.predicted_state.keys())

        combined = {}
        total_weight = 0.0
        total_confidence = 0.0

        for key in all_keys:
            weighted_sum = 0.0
            weight_sum = 0.0

            for layer_name, pred in predictions.items():
                if key in pred.predicted_state:
                    weight = self._layer_weights.get(layer_name, 0.33)
                    try:
                        value = float(pred.predicted_state[key])
                        weighted_sum += value * weight * pred.confidence
                        weight_sum += weight * pred.confidence
                    except (ValueError, TypeError):
                        pass

            if weight_sum > 0:
                combined[key] = weighted_sum / weight_sum

        # 计算整体置信度
        for layer_name, pred in predictions.items():
            weight = self._layer_weights.get(layer_name, 0.33)
            total_confidence += pred.confidence * weight
            total_weight += weight

        avg_confidence = total_confidence / total_weight if total_weight > 0 else 0.5

        return Prediction(
            predicted_state=combined,
            confidence=avg_confidence,
            uncertainty=1.0 - avg_confidence,
            horizon=1,
            metadata={
                "layers": list(predictions.keys()),
                "combination": "weighted_average",
            }
        )

    def initialize(self, config: Dict[str, Any]) -> None:
        self._layer_weights = config.get("layer_weights", self._layer_weights)
        for predictor in self._layers.values():
            predictor.initialize(config)
        self._initialized = True

    def start(self) -> None:
        self._running = True
        for predictor in self._layers.values():
            predictor.start()

    def stop(self) -> None:
        self._running = False
        for predictor in self._layers.values():
            predictor.stop()

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.STATE_UPDATE:
            state = message.payload.get("state", {})
            predictions = self.predict(state)
            combined = self.combine_predictions(predictions)
            return AgentMessage(
                msg_type=MessageType.PREDICTION,
                source=self.module_id,
                payload={
                    "combined_prediction": {
                        "predicted_state": combined.predicted_state,
                        "confidence": combined.confidence,
                        "uncertainty": combined.uncertainty,
                    },
                    "layer_predictions": {
                        name: {
                            "predicted_state": p.predicted_state,
                            "confidence": p.confidence,
                        }
                        for name, p in predictions.items()
                    },
                }
            )
        return None

    def get_model_state(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "layers": {
                name: predictor.get_model_state()
                for name, predictor in self._layers.items()
            },
            "weights": self._layer_weights,
        }
