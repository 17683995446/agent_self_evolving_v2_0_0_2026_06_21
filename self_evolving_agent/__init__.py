"""
自驱永续进化Agent系统

基于第一性原理设计的自驱永续进化预测修正Agent系统。

核心特性：
- 预测编码：多层预测模型
- 自由能最小化：误差驱动学习
- 三大驱力：安全、收益、能效
- 消息总线：完全解耦的模块通信
- 双模式优化：微修正 + 结构性重构
"""

__version__ = "1.0.0"

from .agent import SelfEvolvingAgent, create_default_agent
from .core.interfaces import (
    BaseModule, AgentMessage, MessageType, MessagePriority,
    Predictor, Prediction, DriveEngine, DriveGaps,
    Optimizer, OptimizationResult, Memory,
    ErrorCalculator, FeedbackGenerator, ErrorMetrics,
    TaskFactory, TaskEvaluator, TaskSelector, TaskCandidate,
)
from .core.message_bus import LocalMessageBus
from .core.config_manager import ConfigurationManager

__all__ = [
    "SelfEvolvingAgent",
    "create_default_agent",
    "BaseModule",
    "AgentMessage",
    "MessageType",
    "MessagePriority",
    "LocalMessageBus",
    "ConfigurationManager",
]
