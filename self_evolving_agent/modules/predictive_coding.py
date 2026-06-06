"""
自驱永续进化Agent系统 — 预测编码算法
阶段11：预测编码算法精细化

第一性原理：预测编码 = 前向预测 + 反向误差传播
大脑通过最小化预测误差来学习世界模型

数学基础：
- 前向：μ(t+1) = f(μ(t); θ)  — 生成模型预测下一状态
- 反向：ε(t) = s(t) - μ(t)    — 计算预测误差
- 更新：θ_new = θ - α * ∂ε/∂θ — 梯度下降更新参数
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from collections import deque
from dataclasses import dataclass

from ..core.interfaces import Predictor, Prediction, BaseModule, AgentMessage, MessageType


@dataclass
class ConvergenceStatus:
    """收敛状态"""
    converged: bool
    iteration: int
    final_error: float
    error_delta: float
    stability_score: float  # 稳定性评分 [0, 1]


class PredictiveCodingLayer:
    """
    单层预测编码

    实现标准预测编码的数学推导：
    1. forward_prediction: 生成预测
    2. backward_error: 计算误差并更新内部表示
    3. update_parameters: 更新模型参数
    """

    def __init__(self, layer_id: str, input_dim: int = 1,
                 learning_rate: float = 0.01):
        self.layer_id = layer_id
        self.input_dim = input_dim
        self.learning_rate = learning_rate

        # 模型参数：权重和偏置
        self.weights = np.random.randn(input_dim, input_dim) * 0.01
        self.bias = np.zeros(input_dim)

        # 内部状态（预测表示）
        self.mu = np.zeros(input_dim)  # 预测值
        self.epsilon = np.zeros(input_dim)  # 预测误差

        # 收敛检测
        self._error_history: deque = deque(maxlen=50)
        self._convergence_threshold = 1e-4
        self._max_iterations = 100

    def forward_prediction(self, state_vector: np.ndarray) -> np.ndarray:
        """
        前向预测

        数学：μ = W * s + b
        其中 W 是权重矩阵，b 是偏置，s 是当前状态

        Args:
            state_vector: 当前状态向量

        Returns:
            预测的状态向量
        """
        # 确保维度匹配
        if len(state_vector) != self.input_dim:
            # 动态调整维度
            self._resize_dimensions(len(state_vector))

        # 前向传播：μ = W * s + b
        self.mu = np.dot(self.weights, state_vector) + self.bias

        # 应用非线性激活（tanh，有界且可导）
        self.mu = np.tanh(self.mu)

        return self.mu

    def backward_error(self, actual_vector: np.ndarray,
                       predicted_vector: np.ndarray) -> np.ndarray:
        """
        反向误差传播

        数学：ε = s - μ
        误差是实际值与预测值之间的差异

        Args:
            actual_vector: 实际状态向量
            predicted_vector: 预测的状态向量

        Returns:
            误差向量
        """
        self.epsilon = actual_vector - predicted_vector
        self._error_history.append(np.mean(self.epsilon ** 2))
        return self.epsilon

    def update_parameters(self, state_vector: np.ndarray,
                          error_vector: np.ndarray) -> Dict[str, Any]:
        """
        更新模型参数

        数学：
        - ΔW = α * ε * s^T
        - Δb = α * ε

        这是梯度下降的最简形式，最小化预测误差的平方

        Args:
            state_vector: 当前状态向量
            error_vector: 误差向量

        Returns:
            更新统计信息
        """
        # 计算权重梯度
        weight_gradient = np.outer(error_vector, state_vector)

        # 更新参数
        self.weights += self.learning_rate * weight_gradient
        self.bias += self.learning_rate * error_vector

        # 权重衰减（防止过拟合）
        self.weights *= 0.999

        return {
            "weight_change": float(np.mean(np.abs(weight_gradient))),
            "bias_change": float(np.mean(np.abs(error_vector))),
            "mean_weight": float(np.mean(np.abs(self.weights))),
        }

    def check_convergence(self) -> ConvergenceStatus:
        """
        检查收敛性

        收敛标准：
        1. 误差变化小于阈值
        2. 达到最大迭代次数
        3. 稳定性评分足够高
        """
        if len(self._error_history) < 10:
            return ConvergenceStatus(
                converged=False,
                iteration=len(self._error_history),
                final_error=self._error_history[-1] if self._error_history else 1.0,
                error_delta=1.0,
                stability_score=0.0,
            )

        recent_errors = list(self._error_history)[-10:]
        current_error = recent_errors[-1]

        # 计算误差变化率
        error_delta = abs(recent_errors[-1] - recent_errors[-5]) if len(recent_errors) >= 5 else 1.0

        # 计算稳定性（误差方差的倒数）
        error_variance = np.var(recent_errors)
        stability_score = 1.0 / (1.0 + error_variance)

        # 收敛判断
        converged = (
            error_delta < self._convergence_threshold or
            len(self._error_history) >= self._max_iterations
        )

        return ConvergenceStatus(
            converged=converged,
            iteration=len(self._error_history),
            final_error=current_error,
            error_delta=error_delta,
            stability_score=stability_score,
        )

    def _resize_dimensions(self, new_dim: int) -> None:
        """动态调整维度"""
        old_dim = self.input_dim
        if new_dim == old_dim:
            return

        self.input_dim = new_dim

        # 扩展权重矩阵
        new_weights = np.random.randn(new_dim, new_dim) * 0.01
        min_dim = min(old_dim, new_dim)
        new_weights[:min_dim, :min_dim] = self.weights[:min_dim, :min_dim]
        self.weights = new_weights

        # 扩展偏置
        new_bias = np.zeros(new_dim)
        new_bias[:min_dim] = self.bias[:min_dim]
        self.bias = new_bias

        # 扩展状态向量
        new_mu = np.zeros(new_dim)
        new_mu[:min_dim] = self.mu[:min_dim]
        self.mu = new_mu

        new_epsilon = np.zeros(new_dim)
        new_epsilon[:min_dim] = self.epsilon[:min_dim]
        self.epsilon = new_epsilon

    def get_parameters(self) -> Dict[str, np.ndarray]:
        """获取当前参数"""
        return {
            "weights": self.weights.copy(),
            "bias": self.bias.copy(),
        }

    def set_parameters(self, params: Dict[str, np.ndarray]) -> None:
        """设置参数"""
        if "weights" in params:
            self.weights = params["weights"].copy()
        if "bias" in params:
            self.bias = params["bias"].copy()


class HierarchicalPredictiveCoder(Predictor, BaseModule):
    """
    层级预测编码器

    第一性原理：大脑通过多层预测编码处理信息
    - 低层：处理原始感知数据
    - 高层：提取抽象模式
    - 每层都试图预测下一层的活动
    """

    def __init__(self, module_id: str, layer_dims: List[int] = None,
                 learning_rate: float = 0.01):
        BaseModule.__init__(self, module_id)
        self.learning_rate = learning_rate

        # 默认三层结构
        if layer_dims is None:
            layer_dims = [1, 4, 2]

        # 创建层级
        self.layers: List[PredictiveCodingLayer] = []
        for i, dim in enumerate(layer_dims):
            self.layers.append(
                PredictiveCodingLayer(
                    layer_id=f"layer_{i}",
                    input_dim=dim,
                    learning_rate=learning_rate,
                )
            )

        # 层间连接权重
        self._layer_connections: List[np.ndarray] = []
        for i in range(len(layer_dims) - 1):
            conn = np.random.randn(layer_dims[i + 1], layer_dims[i]) * 0.01
            self._layer_connections.append(conn)

        self._prediction_history: deque = deque(maxlen=100)
        self._convergence_history: deque = deque(maxlen=50)

    def predict(self, current_state: Dict[str, Any],
                horizon: int = 1) -> Prediction:
        """
        执行层级预测

        流程：
        1. 将状态转换为向量
        2. 逐层前向预测
        3. 组合各层预测
        """
        # 提取数值特征
        state_vector = self._state_to_vector(current_state)

        # 逐层前向传播
        current = state_vector
        layer_predictions = []

        for layer in self.layers:
            predicted = layer.forward_prediction(current)
            layer_predictions.append(predicted.copy())
            current = predicted

        # 使用最高层的输出作为最终预测
        final_prediction = layer_predictions[-1] if layer_predictions else current

        # 将向量转换回状态字典
        predicted_state = self._vector_to_state(
            final_prediction, current_state
        )

        # 计算置信度（基于各层收敛状态）
        convergence_scores = [
            layer.check_convergence().stability_score
            for layer in self.layers
        ]
        avg_convergence = np.mean(convergence_scores) if convergence_scores else 0.5

        # 不确定性基于预测方差
        if len(self._prediction_history) >= 5:
            recent = list(self._prediction_history)[-5:]
            variances = []
            for key in predicted_state:
                values = [p.get(key, 0) for p in recent]
                if len(values) > 1:
                    variances.append(np.var(values))
            uncertainty = np.mean(variances) if variances else 0.5
        else:
            uncertainty = 0.5

        self._prediction_history.append(predicted_state)

        return Prediction(
            predicted_state=predicted_state,
            confidence=avg_convergence,
            uncertainty=min(uncertainty, 1.0),
            horizon=horizon,
            metadata={
                "model": "hierarchical_predictive_coding",
                "num_layers": len(self.layers),
                "layer_predictions": [
                    {k: float(v) for k, v in self._vector_to_state(p, current_state).items()}
                    for p in layer_predictions
                ],
                "convergence_scores": convergence_scores,
            }
        )

    def update(self, actual_state: Dict[str, Any],
               predicted_state: Dict[str, Any]) -> None:
        """
        根据实际结果更新模型

        流程：
        1. 计算预测误差
        2. 反向传播误差
        3. 更新各层参数
        """
        actual_vector = self._state_to_vector(actual_state)
        predicted_vector = self._state_to_vector(predicted_state)

        # 从最高层开始反向传播
        current_error = actual_vector - predicted_vector

        for i in range(len(self.layers) - 1, -1, -1):
            layer = self.layers[i]

            # 确保维度匹配
            if len(current_error) != layer.input_dim:
                layer._resize_dimensions(len(current_error))

            # 反向误差
            error = layer.backward_error(
                actual_vector if i == 0 else predicted_vector,
                layer.mu
            )

            # 更新参数
            state_input = actual_vector if i == 0 else self.layers[i - 1].mu
            if len(state_input) != layer.input_dim:
                # 填充或截断
                if len(state_input) < layer.input_dim:
                    state_input = np.pad(state_input, (0, layer.input_dim - len(state_input)))
                else:
                    state_input = state_input[:layer.input_dim]

            stats = layer.update_parameters(state_input, error)

            # 传播误差到下一层
            if i > 0 and i - 1 < len(self._layer_connections):
                conn = self._layer_connections[i - 1]
                # 确保维度匹配
                if error.shape[0] == conn.shape[0]:
                    current_error = np.dot(conn.T, error)
                else:
                    # 维度不匹配时，使用投影或直接传递
                    current_error = np.zeros(self.layers[i - 1].input_dim)
                    min_dim = min(len(error), len(current_error), conn.shape[0])
                    current_error[:min_dim] = np.dot(
                        conn[:min_dim, :min_dim].T, error[:min_dim]
                    )

        # 记录收敛状态
        convergence = self.layers[-1].check_convergence()
        self._convergence_history.append(convergence)

    def get_model_state(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "num_layers": len(self.layers),
            "learning_rate": self.learning_rate,
            "layers": [
                {
                    "layer_id": layer.layer_id,
                    "input_dim": layer.input_dim,
                    "convergence": {
                        "converged": layer.check_convergence().converged,
                        "stability": layer.check_convergence().stability_score,
                    },
                }
                for layer in self.layers
            ],
            "prediction_history_size": len(self._prediction_history),
        }

    def initialize(self, config: Dict[str, Any]) -> None:
        self.learning_rate = config.get("learning_rate", self.learning_rate)
        for layer in self.layers:
            layer.learning_rate = self.learning_rate
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
                        "metadata": prediction.metadata,
                    },
                    "horizon": prediction.horizon,
                }
            )
        return None

    @staticmethod
    def _state_to_vector(state: Dict[str, Any]) -> np.ndarray:
        """将状态字典转换为向量"""
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
        """将向量转换回状态字典"""
        result = {}
        keys = list(template.keys())
        for i, key in enumerate(keys):
            if i < len(vector):
                result[key] = float(vector[i])
            else:
                result[key] = template[key]
        return result
