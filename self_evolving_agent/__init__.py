"""
自驱永续进化Agent系统

基于第一性原理设计的自驱永续进化预测修正Agent系统。

核心特性：
- 预测编码：多层预测模型 + 自由能最小化
- 三大驱力：安全（Safe）、收益（Gain）、能效（Eff）
- 15个第一性原理引擎：预测编码、驱力、学习、探索、记忆、进化、
  安全、能效、社交、创造、因果、元认知、情感、意识、自由意志
- LLM 集成：硅基流动（SiliconFlow）Chat + Embedding
- RAG 检索增强：向量数据库 + 余弦相似度搜索
- 统一架构：SystemCoordinator + UnifiedFirstPrinciplesEngine

阶段96+：统一两套架构，SelfEvolvingAgent 作为 SystemCoordinator 的薄包装层。
"""

__version__ = "2.0.0"

# 架构B：统一入口（推荐）
from .agent import (
    SelfEvolvingAgent,
    create_default_agent,
    create_default_agent_with_llm,
)
from .core.system_coordinator import SystemCoordinator, create_coordinator
from .core.unified_first_principles_engine import (
    UnifiedFirstPrinciplesEngine,
    create_unified_engine,
)
from .core.llm_service import LLMService, SiliconFlowClient, create_llm_service
from .core.vector_store import (
    EmbeddingClient,
    VectorStore,
    RAGService,
    create_rag_service,
)

# 基础设施（向后兼容）
from .core.interfaces import (
    AgentMessage,
    BaseModule,
    DriveEngine,
    DriveGaps,
    ErrorCalculator,
    ErrorMetrics,
    FeedbackGenerator,
    Memory,
    MessagePriority,
    MessageType,
    OptimizationResult,
    Optimizer,
    Prediction,
    Predictor,
    TaskCandidate,
    TaskEvaluator,
    TaskFactory,
    TaskSelector,
)
from .core.message_bus import LocalMessageBus
from .core.config_manager import ConfigurationManager

__all__ = [
    # 架构B：统一入口（推荐）
    "SelfEvolvingAgent",
    "create_default_agent",
    "create_default_agent_with_llm",
    "SystemCoordinator",
    "create_coordinator",
    "UnifiedFirstPrinciplesEngine",
    "create_unified_engine",
    # LLM 与 RAG
    "LLMService",
    "SiliconFlowClient",
    "create_llm_service",
    "EmbeddingClient",
    "VectorStore",
    "RAGService",
    "create_rag_service",
    # 基础设施
    "BaseModule",
    "AgentMessage",
    "MessageType",
    "MessagePriority",
    "LocalMessageBus",
    "ConfigurationManager",
    # 接口抽象
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
]
