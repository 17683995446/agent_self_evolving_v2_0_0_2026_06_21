"""
自驱永续进化Agent系统 — 时序预测模型
阶段18：时序预测模型精细化

第一性原理：时序数据有记忆效应，当前状态依赖于历史状态

简化版GRU（Gated Recurrent Unit）实现：
- 更新门：控制历史信息的保留程度
- 重置门：控制历史信息的遗忘程度
- 候选状态：新的候选记忆

数学：
- z_t = σ(W_z * [h_{t-1}, x_t])  — 更新门
- r_t = σ(W_r * [h_{t-1}, x_t])  — 重置门
- h̃_t = tanh(W * [r_t ⊙ h_{t-1}, x_t])  — 候选状态
- h_t = (1 - z_t) ⊙ h_{t-1} + z_t ⊙ h̃_t  — 新状态
"""

import numpy as np
from typing import Dict, Any, List, Optional
from collections import deque

from ..core.interfaces import Predictor, Prediction, BaseModule, AgentMessage, MessageType


class SimpleGRUCell:
    """
    简化版GRU单元

    实现GRU的核心数学公式
    """

    def __init__(self, input_size: int, hidden_size: int):
        self.input_size = input_size
        self.hidden_size = hidden_size

        # 初始化权重
        self.W_z = np.random.randn(hidden_size, input_size + hidden_size) * 0.01
        self.b_z = np.zeros(hidden_size)

        self.W_r = np.random.randn(hidden_size, input_size + hidden_size) * 0.01
        self.b_r = np.zeros(hidden_size)

        self.W_h = np.random.randn(hidden_size, input_size + hidden_size) * 0.01
        self.b_h = np.zeros(hidden_size)

        # 隐藏状态
        self.h = np.zeros(hidden_size)

    def forward(self, x: np.ndarray) -> np.ndarray:
        """
        前向传播

        数学：
        z = σ(W_z * [h, x] + b_z)
        r = σ(W_r * [h, x] + b_r)
        h_tilde = tanh(W_h * [r⊙h, x] + b_h)
        h = (1-z)⊙h + z⊙h_tilde
        """
        # 拼接输入和隐藏状态
        hx = np.concatenate([self.h, x])

        # 更新门
        z = self._sigmoid(np.dot(self.W_z, hx) + self.b_z)

        # 重置门
        r = self._sigmoid(np.dot(self.W_r, hx) + self.b_r)

        # 候选状态
        rh = r * self.h
        rhx = np.concatenate([rh, x])
        h_tilde = np.tanh(np.dot(self.W_h, rhx) + self.b_h)

        # 新隐藏状态
        self.h = (1 - z) * self.h + z * h_tilde

        return self.h.copy()

    def reset(self) -> None:
        """重置隐藏状态"""
        self.h = np.zeros(self.hidden_size)

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        """sigmoid激活函数"""
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


class TemporalPredictor(Predictor, BaseModule):
    """
    时序预测器

    使用简化版GRU进行时序预测
    """

    def __init__(self, module_id: str = "temporal_predictor",
                 input_size: int = 3,
                 hidden_size: int = 8,
                 output_size: int = 3,
                 sequence_length: int = 10):
        BaseModule.__init__(self, module_id)
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        self.sequence_length = sequence_length

        # GRU单元
        self.gru = SimpleGRUCell(input_size, hidden_size)

        # 输出层权重
        self.W_out = np.random.randn(output_size, hidden_size) * 0.01
        self.b_out = np.zeros(output_size)

        # 序列缓冲区
        self._sequence: deque = deque(maxlen=sequence_length)

        # 预测历史
        self._prediction_history: deque = deque(maxlen=100)

    def predict(self, current_state: Dict[str, Any],
                horizon: int = 1) -> Prediction:
        """
        预测未来状态

        流程：
        1. 将状态转换为向量
        2. 更新GRU状态
        3. 生成预测
        """
        # 提取特征
        x = self._state_to_vector(current_state)

        # 确保维度匹配
        if len(x) != self.input_size:
            x = self._resize_vector(x, self.input_size)

        # 更新GRU
        self.gru.forward(x)

        # 存储序列
        self._sequence.append(x)

        # 生成预测
        predicted = self._generate_prediction()

        # 转换为状态字典
        predicted_state = self._vector_to_state(predicted, current_state)

        # 计算置信度（基于序列长度）
        confidence = min(1.0, len(self._sequence) / self.sequence_length)

        # 计算不确定性（基于预测历史方差）
        uncertainty = self._compute_uncertainty(predicted_state)

        self._prediction_history.append(predicted_state)

        return Prediction(
            predicted_state=predicted_state,
            confidence=confidence,
            uncertainty=uncertainty,
            horizon=horizon,
            metadata={
                "model": "simple_gru",
                "sequence_length": len(self._sequence),
                "hidden_size": self.hidden_size,
            }
        )

    def update(self, actual_state: Dict[str, Any],
               predicted_state: Dict[str, Any]) -> None:
        """
        根据实际结果更新模型

        简化实现：使用预测误差调整输出层权重
        """
        actual = self._state_to_vector(actual_state)
        predicted = self._state_to_vector(predicted_state)

        if len(actual) != len(predicted):
            return

        # 计算误差
        error = actual - predicted

        # 更新输出层权重（梯度下降）
        learning_rate = 0.01
        self.W_out += learning_rate * np.outer(error, self.gru.h)
        self.b_out += learning_rate * error

    def predict_sequence(self, steps: int = 5) -> List[Dict[str, Any]]:
        """
        多步预测

        使用自回归方式：用预测结果作为下一步的输入
        """
        if len(self._sequence) == 0:
            return []

        predictions = []
        current_h = self.gru.h.copy()

        for _ in range(steps):
            # 使用最后输入作为近似
            last_input = self._sequence[-1]

            # 生成预测
            output = np.dot(self.W_out, current_h) + self.b_out
            predictions.append(output)

            # 更新GRU状态（使用预测作为下一步输入）
            hx = np.concatenate([current_h, last_input])
            z = self.gru._sigmoid(np.dot(self.gru.W_z, hx) + self.gru.b_z)
            r = self.gru._sigmoid(np.dot(self.gru.W_r, hx) + self.gru.b_r)
            rh = r * current_h
            rhx = np.concatenate([rh, last_input])
            h_tilde = np.tanh(np.dot(self.gru.W_h, rhx) + self.gru.b_h)
            current_h = (1 - z) * current_h + z * h_tilde

        # 转换为状态字典
        template = self._prediction_history[-1] if self._prediction_history else {}
        return [self._vector_to_state(p, template) for p in predictions]

    def _generate_prediction(self) -> np.ndarray:
        """生成预测"""
        output = np.dot(self.W_out, self.gru.h) + self.b_out
        return output

    def _compute_uncertainty(self, predicted_state: Dict[str, Any]) -> float:
        """计算不确定性"""
        if len(self._prediction_history) < 5:
            return 0.5

        # 计算最近预测的标准差
        recent = list(self._prediction_history)[-5:]
        variances = []
        for key in predicted_state:
            values = []
            for p in recent:
                if key in p:
                    try:
                        values.append(float(p[key]))
                    except (ValueError, TypeError):
                        pass
            if len(values) > 1:
                variances.append(np.var(values))

        return np.mean(variances) if variances else 0.5

    @staticmethod
    def _state_to_vector(state: Dict[str, Any]) -> np.ndarray:
        """状态转向量"""
        values = []
        for v in state.values():
            try:
                values.append(float(v))
            except (ValueError, TypeError):
                pass
        return np.array(values) if values else np.zeros(1)

    @staticmethod
    def _vector_to_state(vector: np.ndarray,
                         template: Dict[str, Any]) -> Dict[str, Any]:
        """向量转状态"""
        result = {}
        keys = list(template.keys())
        for i, key in enumerate(keys):
            if i < len(vector):
                result[key] = float(vector[i])
            else:
                result[key] = template[key]
        return result

    @staticmethod
    def _resize_vector(vector: np.ndarray, target_size: int) -> np.ndarray:
        """调整向量大小"""
        if len(vector) == target_size:
            return vector
        if len(vector) < target_size:
            return np.pad(vector, (0, target_size - len(vector)))
        return vector[:target_size]

    def get_model_state(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "input_size": self.input_size,
            "hidden_size": self.hidden_size,
            "output_size": self.output_size,
            "sequence_length": self.sequence_length,
            "current_sequence_length": len(self._sequence),
            "prediction_history_size": len(self._prediction_history),
        }

    def initialize(self, config: Dict[str, Any]) -> None:
        self.input_size = config.get("input_size", self.input_size)
        self.hidden_size = config.get("hidden_size", self.hidden_size)
        self.output_size = config.get("output_size", self.output_size)
        self.sequence_length = config.get("sequence_length", self.sequence_length)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.STATE_UPDATE:
            state = message.payload.get("state", {})
            prediction = self.predict(state)
            return AgentMessage(
                msg_type=MessageType.PREDICTION,
                source=self.module_id,
                payload={
                    "prediction": {
                        "predicted_state": prediction.predicted_state,
                        "confidence": prediction.confidence,
                        "uncertainty": prediction.uncertainty,
                    },
                    "horizon": prediction.horizon,
                }
            )
        return None


class MultiHorizonPredictor(BaseModule):
    """
    多步预测器

    整合多个时间尺度的预测
    """

    def __init__(self, module_id: str = "multi_horizon_predictor"):
        super().__init__(module_id)
        self._short_term = TemporalPredictor(
            "short_term", input_size=3, hidden_size=4, sequence_length=5
        )
        self._mid_term = TemporalPredictor(
            "mid_term", input_size=3, hidden_size=8, sequence_length=20
        )
        self._long_term = TemporalPredictor(
            "long_term", input_size=3, hidden_size=16, sequence_length=50
        )

    def predict_all_horizons(self, state: Dict[str, Any]) -> Dict[str, Prediction]:
        """预测多个时间尺度"""
        return {
            "short": self._short_term.predict(state, horizon=1),
            "mid": self._mid_term.predict(state, horizon=5),
            "long": self._long_term.predict(state, horizon=20),
        }

    def initialize(self, config: Dict[str, Any]) -> None:
        self._short_term.initialize(config.get("short", {}))
        self._mid_term.initialize(config.get("mid", {}))
        self._long_term.initialize(config.get("long", {}))
        self._initialized = True

    def start(self) -> None:
        self._running = True
        self._short_term.start()
        self._mid_term.start()
        self._long_term.start()

    def stop(self) -> None:
        self._running = False
        self._short_term.stop()
        self._mid_term.stop()
        self._long_term.stop()

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.STATE_UPDATE:
            state = message.payload.get("state", {})
            predictions = self.predict_all_horizons(state)
            return AgentMessage(
                msg_type=MessageType.PREDICTION,
                source=self.module_id,
                payload={
                    "predictions": {
                        name: {
                            "predicted_state": p.predicted_state,
                            "confidence": p.confidence,
                            "uncertainty": p.uncertainty,
                        }
                        for name, p in predictions.items()
                    }
                }
            )
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        base.update({
            "short_term": self._short_term.get_model_state(),
            "mid_term": self._mid_term.get_model_state(),
            "long_term": self._long_term.get_model_state(),
        })
        return base
