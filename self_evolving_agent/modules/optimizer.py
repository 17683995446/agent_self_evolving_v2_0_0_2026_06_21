"""
自驱永续进化Agent系统 — 优化器
阶段7：优化器接口统一

第一性原理：两种优化是不同策略，应对不同场景
- 微修正：梯度下降，快速适应
- 结构性重构：架构调整，应对范式转变
"""

import numpy as np
from typing import Dict, Any, Optional
from collections import deque

from ..core.interfaces import (
    Optimizer, OptimizationResult, Predictor, BaseModule,
    AgentMessage, MessageType
)


class GradientDescentOptimizer(Optimizer, BaseModule):
    """
    梯度下降优化器（微修正）

    第一性原理：小误差通过局部梯度修正
    """

    def __init__(self, module_id: str = "gd_optimizer",
                 learning_rate: float = 0.01,
                 max_iterations: int = 100,
                 convergence_threshold: float = 1e-6):
        BaseModule.__init__(self, module_id)
        self._learning_rate = learning_rate
        self._max_iterations = max_iterations
        self._convergence_threshold = convergence_threshold
        self._error_history: deque = deque(maxlen=50)

    def optimize(self, model: Predictor,
                 error_signal: Dict[str, Any]) -> OptimizationResult:
        """
        使用梯度下降优化模型参数

        简化实现：假设模型有可调整的参数
        """
        initial_error = error_signal.get("error", 1.0)
        current_error = initial_error
        iterations = 0

        # 模拟梯度下降过程
        for i in range(self._max_iterations):
            iterations = i + 1

            # 计算梯度（简化：使用数值近似）
            gradient = self._compute_gradient(model, error_signal)

            # 更新参数
            self._apply_gradient(model, gradient)

            # 计算新误差
            new_error = self._evaluate_error(model, error_signal)
            self._error_history.append(new_error)

            # 检查收敛
            if abs(current_error - new_error) < self._convergence_threshold:
                current_error = new_error
                break

            current_error = new_error

        return OptimizationResult(
            success=current_error < initial_error,
            model_state=model.get_model_state(),
            iterations=iterations,
            error_before=initial_error,
            error_after=current_error,
            metadata={
                "optimizer": "gradient_descent",
                "learning_rate": self._learning_rate,
            }
        )

    def can_handle(self, error_signal: Dict[str, Any]) -> bool:
        """
        判断是否能处理

        微修正适用于：
        - 误差较小
        - 模型结构无需改变
        """
        error = error_signal.get("error", 0.0)
        structural_issue = error_signal.get("structural_issue", False)
        return error < 0.5 and not structural_issue

    def _compute_gradient(self, model: Predictor,
                          error_signal: Dict[str, Any]) -> Dict[str, float]:
        """计算梯度（数值近似）"""
        # 简化实现
        return {"param_adjustment": -self._learning_rate * error_signal.get("error", 0.0)}

    def _apply_gradient(self, model: Predictor,
                        gradient: Dict[str, float]) -> None:
        """应用梯度更新"""
        # 简化实现，实际应调用模型的参数更新方法
        pass

    def _evaluate_error(self, model: Predictor,
                        error_signal: Dict[str, Any]) -> float:
        """评估当前误差"""
        return error_signal.get("error", 1.0) * 0.95  # 模拟误差减小

    def initialize(self, config: Dict[str, Any]) -> None:
        self._learning_rate = config.get("learning_rate", self._learning_rate)
        self._max_iterations = config.get("max_iterations", self._max_iterations)
        self._convergence_threshold = config.get("convergence_threshold", self._convergence_threshold)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.ERROR_SIGNAL:
            error_signal = message.payload
            if self.can_handle(error_signal):
                # 实际应用中需要获取模型引用
                return AgentMessage(
                    msg_type=MessageType.LEARNING_SIGNAL,
                    source=self.module_id,
                    payload={
                        "action": "micro_optimize",
                        "can_handle": True,
                    }
                )
        return None


class StructuralRestructurer(Optimizer, BaseModule):
    """
    结构性重构优化器

    第一性原理：大误差需要结构性改变，而非局部修正
    """

    def __init__(self, module_id: str = "restructurer",
                 complexity_penalty: float = 0.1):
        BaseModule.__init__(self, module_id)
        self._complexity_penalty = complexity_penalty
        self._restructure_count = 0

    def optimize(self, model: Predictor,
                 error_signal: Dict[str, Any]) -> OptimizationResult:
        """
        执行结构性重构

        简化实现：记录重构事件
        """
        initial_error = error_signal.get("error", 1.0)
        self._restructure_count += 1

        # 模拟重构：误差大幅下降但有一定代价
        new_error = initial_error * 0.3  # 重构后误差显著降低
        complexity_cost = self._complexity_penalty * self._restructure_count

        return OptimizationResult(
            success=True,
            model_state={
                "restructured": True,
                "version": self._restructure_count,
            },
            iterations=1,
            error_before=initial_error,
            error_after=new_error + complexity_cost,
            metadata={
                "optimizer": "structural_restructurer",
                "restructure_count": self._restructure_count,
                "complexity_cost": complexity_cost,
            }
        )

    def can_handle(self, error_signal: Dict[str, Any]) -> bool:
        """
        判断是否需要结构性重构

        适用于：
        - 误差较大
        - 长期无法收敛
        - 检测到结构性问题
        """
        error = error_signal.get("error", 0.0)
        structural_issue = error_signal.get("structural_issue", False)
        persistent = error_signal.get("persistent", False)
        return error > 0.5 or structural_issue or persistent

    def initialize(self, config: Dict[str, Any]) -> None:
        self._complexity_penalty = config.get("complexity_penalty", self._complexity_penalty)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.ERROR_SIGNAL:
            error_signal = message.payload
            if self.can_handle(error_signal):
                return AgentMessage(
                    msg_type=MessageType.LEARNING_SIGNAL,
                    source=self.module_id,
                    payload={
                        "action": "structural_restructure",
                        "can_handle": True,
                    }
                )
        return None


class OptimizationStrategy(BaseModule):
    """
    优化策略选择器

    第一性原理：根据误差特征选择最合适的优化策略
    """

    def __init__(self, module_id: str = "optimization_strategy"):
        super().__init__(module_id)
        self._micro_optimizer = GradientDescentOptimizer()
        self._restructurer = StructuralRestructurer()
        self._optimizers = [
            self._micro_optimizer,
            self._restructurer,
        ]
        self._selection_history: deque = deque(maxlen=100)

    def select_optimizer(self, error_signal: Dict[str, Any]) -> Optional[Optimizer]:
        """
        选择最适合的优化器

        策略：
        1. 检查每个优化器的can_handle
        2. 如果有多个可以处理，选择历史效果最好的
        """
        candidates = [opt for opt in self._optimizers if opt.can_handle(error_signal)]

        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        # 多个候选时，优先选择微修正（除非必须重构）
        if self._restructurer in candidates and error_signal.get("error", 0) < 0.7:
            return self._micro_optimizer

        return candidates[0]

    def optimize(self, model: Predictor,
                 error_signal: Dict[str, Any]) -> OptimizationResult:
        """执行优化"""
        optimizer = self.select_optimizer(error_signal)

        if optimizer is None:
            return OptimizationResult(
                success=False,
                model_state={},
                iterations=0,
                error_before=error_signal.get("error", 0),
                error_after=error_signal.get("error", 0),
                metadata={"reason": "no_suitable_optimizer"},
            )

        result = optimizer.optimize(model, error_signal)
        self._selection_history.append({
            "optimizer": optimizer.module_id,
            "success": result.success,
            "error_before": result.error_before,
            "error_after": result.error_after,
        })

        return result

    def initialize(self, config: Dict[str, Any]) -> None:
        self._micro_optimizer.initialize(config.get("micro", {}))
        self._restructurer.initialize(config.get("structural", {}))
        self._initialized = True

    def start(self) -> None:
        self._running = True
        self._micro_optimizer.start()
        self._restructurer.start()

    def stop(self) -> None:
        self._running = False
        self._micro_optimizer.stop()
        self._restructurer.stop()

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.ERROR_SIGNAL:
            optimizer = self.select_optimizer(message.payload)
            return AgentMessage(
                msg_type=MessageType.LEARNING_SIGNAL,
                source=self.module_id,
                payload={
                    "selected_optimizer": optimizer.module_id if optimizer else None,
                    "error": message.payload.get("error"),
                }
            )
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        base.update({
            "selection_history_size": len(self._selection_history),
            "micro_optimizer": self._micro_optimizer.get_state(),
            "restructurer": self._restructurer.get_state(),
        })
        return base
