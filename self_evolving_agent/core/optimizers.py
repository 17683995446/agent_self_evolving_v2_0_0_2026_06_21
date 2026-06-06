"""
自驱永续进化Agent系统 — 优化算法库
阶段13：梯度下降算法库化

第一性原理：优化是参数空间的搜索，不同策略对应不同的搜索路径
- SGD：沿梯度方向直线搜索
- Momentum：利用惯性加速收敛
- Adam：自适应学习率
- RMSprop：均方根传播

统一接口：step(params, grads) -> updated_params
"""

import numpy as np
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OptimizerState:
    """优化器状态"""
    iteration: int = 0
    learning_rate: float = 0.01
    history: Dict[str, Any] = None

    def __post_init__(self):
        if self.history is None:
            self.history = {}


class BaseOptimizer(ABC):
    """
    优化器基类

    统一接口：step(params, grads) -> updated_params
    """

    def __init__(self, learning_rate: float = 0.01,
                 name: str = "base_optimizer"):
        self.name = name
        self.lr = learning_rate
        self.state = OptimizerState(learning_rate=learning_rate)

    @abstractmethod
    def step(self, params: Dict[str, np.ndarray],
             grads: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        执行一步优化

        Args:
            params: 当前参数
            grads: 梯度

        Returns:
            更新后的参数
        """
        pass

    def zero_grad(self) -> None:
        """清零梯度（如果需要）"""
        pass

    def get_state(self) -> Dict[str, Any]:
        """获取优化器状态"""
        return {
            "name": self.name,
            "learning_rate": self.lr,
            "iteration": self.state.iteration,
        }


class SGD(BaseOptimizer):
    """
    随机梯度下降

    数学：θ_{t+1} = θ_t - α * ∇J(θ_t)
    最基础的优化算法，沿负梯度方向更新
    """

    def __init__(self, learning_rate: float = 0.01,
                 weight_decay: float = 0.0):
        super().__init__(learning_rate, "SGD")
        self.weight_decay = weight_decay

    def step(self, params: Dict[str, np.ndarray],
             grads: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """SGD更新步"""
        updated = {}
        for key in params:
            if key in grads:
                # 权重衰减
                decay = self.weight_decay * params[key]
                # 梯度下降
                updated[key] = params[key] - self.lr * (grads[key] + decay)
            else:
                updated[key] = params[key].copy()

        self.state.iteration += 1
        return updated


class Momentum(BaseOptimizer):
    """
    动量梯度下降

    数学：
    - v_t = β * v_{t-1} + ∇J(θ_t)
    - θ_{t+1} = θ_t - α * v_t

    物理意义：引入惯性，加速收敛，减少震荡
    """

    def __init__(self, learning_rate: float = 0.01,
                 momentum: float = 0.9,
                 weight_decay: float = 0.0):
        super().__init__(learning_rate, "Momentum")
        self.momentum = momentum
        self.weight_decay = weight_decay
        self._velocity: Dict[str, np.ndarray] = {}

    def step(self, params: Dict[str, np.ndarray],
             grads: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Momentum更新步"""
        updated = {}
        for key in params:
            if key in grads:
                # 初始化速度
                if key not in self._velocity:
                    self._velocity[key] = np.zeros_like(params[key])

                # 权重衰减
                grad = grads[key] + self.weight_decay * params[key]

                # 更新速度
                self._velocity[key] = (
                    self.momentum * self._velocity[key] + grad
                )

                # 更新参数
                updated[key] = params[key] - self.lr * self._velocity[key]
            else:
                updated[key] = params[key].copy()

        self.state.iteration += 1
        return updated


class RMSprop(BaseOptimizer):
    """
    RMSprop

    数学：
    - v_t = β * v_{t-1} + (1-β) * (∇J)^2
    - θ_{t+1} = θ_t - α * ∇J / (√v_t + ε)

    特点：自适应学习率，对梯度大的方向减小步长
    """

    def __init__(self, learning_rate: float = 0.01,
                 beta: float = 0.99,
                 epsilon: float = 1e-8,
                 weight_decay: float = 0.0):
        super().__init__(learning_rate, "RMSprop")
        self.beta = beta
        self.epsilon = epsilon
        self.weight_decay = weight_decay
        self._square_avg: Dict[str, np.ndarray] = {}

    def step(self, params: Dict[str, np.ndarray],
             grads: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """RMSprop更新步"""
        updated = {}
        for key in params:
            if key in grads:
                # 初始化平方平均
                if key not in self._square_avg:
                    self._square_avg[key] = np.zeros_like(params[key])

                # 权重衰减
                grad = grads[key] + self.weight_decay * params[key]

                # 更新平方平均
                self._square_avg[key] = (
                    self.beta * self._square_avg[key] +
                    (1 - self.beta) * (grad ** 2)
                )

                # 自适应学习率更新
                adapted_lr = self.lr / (np.sqrt(self._square_avg[key]) + self.epsilon)
                updated[key] = params[key] - adapted_lr * grad
            else:
                updated[key] = params[key].copy()

        self.state.iteration += 1
        return updated


class Adam(BaseOptimizer):
    """
    Adam (Adaptive Moment Estimation)

    数学：
    - m_t = β1 * m_{t-1} + (1-β1) * ∇J
    - v_t = β2 * v_{t-1} + (1-β2) * (∇J)^2
    - m̂_t = m_t / (1-β1^t)
    - v̂_t = v_t / (1-β2^t)
    - θ_{t+1} = θ_t - α * m̂_t / (√v̂_t + ε)

    特点：结合Momentum和RMSprop的优点
    """

    def __init__(self, learning_rate: float = 0.001,
                 beta1: float = 0.9,
                 beta2: float = 0.999,
                 epsilon: float = 1e-8,
                 weight_decay: float = 0.0):
        super().__init__(learning_rate, "Adam")
        self.beta1 = beta1
        self.beta2 = beta2
        self.epsilon = epsilon
        self.weight_decay = weight_decay
        self._m: Dict[str, np.ndarray] = {}  # 一阶矩
        self._v: Dict[str, np.ndarray] = {}  # 二阶矩

    def step(self, params: Dict[str, np.ndarray],
             grads: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Adam更新步"""
        self.state.iteration += 1
        t = self.state.iteration

        updated = {}
        for key in params:
            if key in grads:
                # 初始化矩
                if key not in self._m:
                    self._m[key] = np.zeros_like(params[key])
                    self._v[key] = np.zeros_like(params[key])

                # 权重衰减
                grad = grads[key] + self.weight_decay * params[key]

                # 更新一阶矩（动量）
                self._m[key] = (
                    self.beta1 * self._m[key] + (1 - self.beta1) * grad
                )

                # 更新二阶矩（平方平均）
                self._v[key] = (
                    self.beta2 * self._v[key] + (1 - self.beta2) * (grad ** 2)
                )

                # 偏差修正
                m_hat = self._m[key] / (1 - self.beta1 ** t)
                v_hat = self._v[key] / (1 - self.beta2 ** t)

                # 更新参数
                adapted_lr = self.lr / (np.sqrt(v_hat) + self.epsilon)
                updated[key] = params[key] - adapted_lr * m_hat
            else:
                updated[key] = params[key].copy()

        return updated


# ============================================================================
# 学习率调度器
# ============================================================================

class LearningRateScheduler(ABC):
    """学习率调度器基类"""

    @abstractmethod
    def get_lr(self, initial_lr: float, iteration: int) -> float:
        """获取当前学习率"""
        pass


class StepDecay(LearningRateScheduler):
    """
    阶梯衰减

    每 step_size 次迭代，学习率乘以 gamma
    """

    def __init__(self, step_size: int = 100, gamma: float = 0.1):
        self.step_size = step_size
        self.gamma = gamma

    def get_lr(self, initial_lr: float, iteration: int) -> float:
        return initial_lr * (self.gamma ** (iteration // self.step_size))


class ExponentialDecay(LearningRateScheduler):
    """
    指数衰减

    lr = initial_lr * exp(-gamma * iteration)
    """

    def __init__(self, gamma: float = 0.01):
        self.gamma = gamma

    def get_lr(self, initial_lr: float, iteration: int) -> float:
        return initial_lr * np.exp(-self.gamma * iteration)


class CosineAnnealing(LearningRateScheduler):
    """
    余弦退火

    lr = initial_lr * 0.5 * (1 + cos(π * iteration / max_iterations))
    """

    def __init__(self, max_iterations: int = 1000):
        self.max_iterations = max_iterations

    def get_lr(self, initial_lr: float, iteration: int) -> float:
        if iteration >= self.max_iterations:
            return 0.0
        return initial_lr * 0.5 * (1 + np.cos(np.pi * iteration / self.max_iterations))


class ScheduledOptimizer(BaseOptimizer):
    """
    带学习率调度的优化器包装器
    """

    def __init__(self, optimizer: BaseOptimizer,
                 scheduler: LearningRateScheduler):
        super().__init__(optimizer.lr, f"Scheduled_{optimizer.name}")
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.initial_lr = optimizer.lr

    def step(self, params: Dict[str, np.ndarray],
             grads: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        # 更新学习率
        new_lr = self.scheduler.get_lr(
            self.initial_lr, self.optimizer.state.iteration
        )
        self.optimizer.lr = new_lr
        self.lr = new_lr

        # 执行优化步
        return self.optimizer.step(params, grads)

    def get_state(self) -> Dict[str, Any]:
        state = self.optimizer.get_state()
        state["current_lr"] = self.lr
        return state


# ============================================================================
# 优化器工厂
# ============================================================================

class OptimizerFactory:
    """优化器工厂"""

    _optimizers = {
        "sgd": SGD,
        "momentum": Momentum,
        "rmsprop": RMSprop,
        "adam": Adam,
    }

    _schedulers = {
        "step": StepDecay,
        "exponential": ExponentialDecay,
        "cosine": CosineAnnealing,
    }

    @classmethod
    def create(cls, name: str, **kwargs) -> BaseOptimizer:
        """创建优化器"""
        name_lower = name.lower()
        if name_lower not in cls._optimizers:
            raise ValueError(f"Unknown optimizer: {name}. "
                           f"Available: {list(cls._optimizers.keys())}")

        optimizer = cls._optimizers[name_lower](**kwargs)

        # 检查是否需要调度器
        scheduler_name = kwargs.get("scheduler")
        if scheduler_name:
            scheduler = cls._schedulers[scheduler_name.lower()](
                **kwargs.get("scheduler_params", {})
            )
            optimizer = ScheduledOptimizer(optimizer, scheduler)

        return optimizer

    @classmethod
    def list_optimizers(cls) -> List[str]:
        """列出可用优化器"""
        return list(cls._optimizers.keys())
