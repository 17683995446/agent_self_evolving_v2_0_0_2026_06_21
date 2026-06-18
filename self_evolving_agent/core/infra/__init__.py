"""
阶段98: infra 子包 — 基础设施层

聚合消息总线、配置、日志、追踪、指标、序列化、校验等基础设施模块。

推荐导入方式：
    from self_evolving_agent.core.infra import (
        LocalMessageBus,
        ConfigurationManager,
        BaseModule,
        AgentMessage,
    )

向后兼容：原有 `from self_evolving_agent.core.X import Y` 仍然有效。
"""

from ..interfaces import (
    BaseModule,
    AgentMessage,
    MessageType,
    MessagePriority,
    Predictor,
    Prediction,
    DriveEngine,
    DriveGaps,
    Optimizer,
    OptimizationResult,
    Memory,
    ErrorCalculator,
    FeedbackGenerator,
    ErrorMetrics,
    TaskFactory,
    TaskEvaluator,
    TaskSelector,
    TaskCandidate,
)
from ..message_bus import LocalMessageBus
from ..event_bus import EventBus
from ..config_manager import ConfigurationManager
from ..config_schema import ConfigSchema
from ..logging import LogManager, StructuredLogger
from ..tracing import Tracer
from ..metrics import MetricsRegistry
from ..health import HealthRegistry, HealthChecker
from ..serialization import JSONSerializer, BinarySerializer, MessageSerializer
from ..validation import InputValidator
from ..schemas import SchemaValidator, SchemaSerializer
from ..error_codes import ErrorCode
from ..version_compat import VersionCompatibilityChecker
from ..lifecycle import LifecycleManager
from ..plugin_system import PluginManager
from ..cache import Cache
from ..concurrency import ConcurrencyController, RWLock
from ..async_tasks import AsyncTaskExecutor
from ..batch import BatchProcessor

__all__ = [
    "BaseModule",
    "AgentMessage",
    "MessageType",
    "MessagePriority",
    "Predictor",
    "Prediction",
    "DriveEngine",
    "DriveGaps",
    "Optimizer",
    "OptimizationResult",
    "Memory",
    "ErrorCalculator",
    "FeedbackGenerator",
    "ErrorMetrics",
    "TaskFactory",
    "TaskEvaluator",
    "TaskSelector",
    "TaskCandidate",
    "LocalMessageBus",
    "EventBus",
    "ConfigurationManager",
    "ConfigSchema",
    "LogManager",
    "StructuredLogger",
    "Tracer",
    "MetricsRegistry",
    "HealthRegistry",
    "HealthChecker",
    "JSONSerializer",
    "BinarySerializer",
    "MessageSerializer",
    "InputValidator",
    "SchemaValidator",
    "SchemaSerializer",
    "ErrorCode",
    "VersionCompatibilityChecker",
    "LifecycleManager",
    "PluginManager",
    "Cache",
    "ConcurrencyController",
    "RWLock",
    "AsyncTaskExecutor",
    "BatchProcessor",
]
