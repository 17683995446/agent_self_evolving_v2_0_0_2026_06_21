"""
core 包 — 核心基础设施与引擎层

本包包含自驱永续进化Agent系统的所有核心组件：
- 15个第一性原理引擎（engines/ 子包）
- 系统协调器（system_coordinator）
- 统一引擎（unified_first_principles_engine）
- LLM与RAG服务（llm_service, vector_store）
- 基础设施（cache, retry, persistence, security, recovery 等）
- 多租户支持（multi_tenant）

推荐导入方式：
    # 顶层快捷导入
    from self_evolving_agent import SelfEvolvingAgent

    # 引擎层
    from self_evolving_agent.core.engines import UnifiedFirstPrinciplesEngine

    # 具体模块
    from self_evolving_agent.core.security import SecurityManager
    from self_evolving_agent.core.multi_tenant import TenantManager

为避免命名空间污染和导入时间过长，本 __init__.py 仅导出最核心的协调器组件。
各功能模块请直接从其子模块导入。
"""

# 核心协调器（最常用，作为快捷导出）
from .system_coordinator import SystemCoordinator, create_coordinator
from .unified_first_principles_engine import (
    UnifiedFirstPrinciplesEngine,
    create_unified_engine,
)

__all__ = [
    "SystemCoordinator",
    "create_coordinator",
    "UnifiedFirstPrinciplesEngine",
    "create_unified_engine",
]
