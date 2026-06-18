"""
阶段98: engines 子包 — 第一性原理引擎层

按职责聚合 15 个第一性原理引擎 + 协调器 + 统一引擎 + LLM/RAG 服务。

推荐导入方式：
    from self_evolving_agent.core.engines import (
        UnifiedFirstPrinciplesEngine,
        SystemCoordinator,
        PerceptionCoordinator,
        LLMService,
        RAGService,
    )

向后兼容：原有 `from self_evolving_agent.core.X import Y` 仍然有效。
"""

# 统一引擎 + 协调器
from ..unified_first_principles_engine import (
    UnifiedFirstPrinciplesEngine,
    create_unified_engine,
)
from ..engine_coordinators import (
    PerceptionCoordinator,
    MotivationCoordinator,
    DecisionCoordinator,
    ExplorationCoordinator,
    create_coordinators,
)
from ..system_coordinator import SystemCoordinator, create_coordinator

# 15 个第一性原理引擎
from ..predictive_coding_engine import (
    PredictiveCodingEngine,
    create_predictive_coding_engine,
    PrecisionWeight,
)
from ..drive_first_principles import (
    DriveFirstPrinciplesEngine,
    create_drive_engine,
    DriveType,
    DriveGap,
)
from ..learning_first_principles import (
    LearningFirstPrinciplesEngine,
    create_learning_engine,
    UpdateType,
)
from ..exploration_first_principles import (
    ExplorationFirstPrinciplesEngine,
    create_exploration_engine,
    ExplorationStrategy,
)
from ..memory_first_principles import (
    MemoryFirstPrinciplesEngine,
    create_memory_engine,
    MemoryPriority,
)
from ..evolution_first_principles import (
    EvolutionFirstPrinciplesEngine,
    create_evolution_engine,
    GoalType,
)
from ..safety_first_principles import (
    SafetyFirstPrinciplesEngine,
    create_safety_engine,
    BoundaryType,
    RiskLevel,
)
from ..efficiency_first_principles import (
    EfficiencyFirstPrinciplesEngine,
    create_efficiency_engine,
    ResourceType,
)
from ..social_first_principles import (
    SocialFirstPrinciplesEngine,
    create_social_engine,
)
from ..creativity_first_principles import (
    CreativityFirstPrinciplesEngine,
    create_creativity_engine,
    ConceptType,
)
from ..causal_first_principles import (
    CausalFirstPrinciplesEngine,
    create_causal_engine,
    CausalStrength,
)
from ..metacognition_first_principles import (
    MetacognitionFirstPrinciplesEngine,
    create_metacognition_engine,
    CognitiveStrategy,
    ConfidenceLevel,
)
from ..emotion_first_principles import (
    EmotionFirstPrinciplesEngine,
    create_emotion_engine,
    EmotionType,
)
from ..consciousness_first_principles import (
    ConsciousnessFirstPrinciplesEngine,
    create_consciousness_engine,
    ContentType,
    WorkspaceContent,
)
from ..free_will_first_principles import (
    FreeWillFirstPrinciplesEngine,
    create_free_will_engine,
    DecisionSource,
    ChoiceSet,
)

# LLM 与 RAG 服务
from ..llm_service import LLMService, SiliconFlowClient, create_llm_service
from ..vector_store import EmbeddingClient, VectorStore, RAGService, create_rag_service

# 推理与知识
from ..inference_engine import InferenceEngine
from ..knowledge_graph import KnowledgeGraph

__all__ = [
    # 统一引擎 + 协调器
    "UnifiedFirstPrinciplesEngine",
    "create_unified_engine",
    "PerceptionCoordinator",
    "MotivationCoordinator",
    "DecisionCoordinator",
    "ExplorationCoordinator",
    "create_coordinators",
    "SystemCoordinator",
    "create_coordinator",
    # 15 个第一性原理引擎
    "PredictiveCodingEngine",
    "create_predictive_coding_engine",
    "PrecisionWeight",
    "DriveFirstPrinciplesEngine",
    "create_drive_engine",
    "DriveType",
    "DriveGap",
    "LearningFirstPrinciplesEngine",
    "create_learning_engine",
    "UpdateType",
    "ExplorationFirstPrinciplesEngine",
    "create_exploration_engine",
    "ExplorationStrategy",
    "MemoryFirstPrinciplesEngine",
    "create_memory_engine",
    "MemoryPriority",
    "EvolutionFirstPrinciplesEngine",
    "create_evolution_engine",
    "GoalType",
    "SafetyFirstPrinciplesEngine",
    "create_safety_engine",
    "BoundaryType",
    "RiskLevel",
    "EfficiencyFirstPrinciplesEngine",
    "create_efficiency_engine",
    "ResourceType",
    "SocialFirstPrinciplesEngine",
    "create_social_engine",
    "CreativityFirstPrinciplesEngine",
    "create_creativity_engine",
    "ConceptType",
    "CausalFirstPrinciplesEngine",
    "create_causal_engine",
    "CausalStrength",
    "MetacognitionFirstPrinciplesEngine",
    "create_metacognition_engine",
    "CognitiveStrategy",
    "ConfidenceLevel",
    "EmotionFirstPrinciplesEngine",
    "create_emotion_engine",
    "EmotionType",
    "ConsciousnessFirstPrinciplesEngine",
    "create_consciousness_engine",
    "ContentType",
    "WorkspaceContent",
    "FreeWillFirstPrinciplesEngine",
    "create_free_will_engine",
    "DecisionSource",
    "ChoiceSet",
    # LLM 与 RAG
    "LLMService",
    "SiliconFlowClient",
    "create_llm_service",
    "EmbeddingClient",
    "VectorStore",
    "RAGService",
    "create_rag_service",
    # 推理与知识
    "InferenceEngine",
    "KnowledgeGraph",
]
