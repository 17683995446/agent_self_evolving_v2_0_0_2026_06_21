"""
api 包 — REST API 蓝图层

按业务域组织的 Flask Blueprint，从 main.py 拆分而来（阶段148）。

蓝图列表:
- core_bp: 核心Agent操作
- llm_bp: LLM服务
- rag_bp: RAG检索增强
- env_bp: 环境管理
- task_bp: 任务执行
- code_bp: 代码审查与文档
- perf_bp: 性能与分布式
- observability_bp: 可观测性
- production_bp: 生产管理
- plugins_bp: 插件系统
- config_bp: 配置管理
- security_bp: 安全管理
- recovery_bp: 错误恢复
- benchmark_bp: 性能基准
- tenants_bp: 多租户管理
"""

from .shared import (
    CustomJSONProvider,
    ensure_agent,
    get_agent,
    init_agent,
)
from .core_routes import core_bp
from .llm_routes import llm_bp
from .rag_routes import rag_bp
from .env_routes import env_bp
from .task_routes import task_bp
from .code_routes import code_bp
from .perf_routes import perf_bp
from .observability_routes import observability_bp
from .production_routes import production_bp
from .plugins_routes import plugins_bp
from .config_routes import config_bp
from .security_routes import security_bp
from .recovery_routes import recovery_bp
from .benchmark_routes import benchmark_bp
from .tenants_routes import tenants_bp


__all__ = [
    "get_agent",
    "ensure_agent",
    "init_agent",
    "CustomJSONProvider",
    "core_bp",
    "llm_bp",
    "rag_bp",
    "env_bp",
    "task_bp",
    "code_bp",
    "perf_bp",
    "observability_bp",
    "production_bp",
    "plugins_bp",
    "config_bp",
    "security_bp",
    "recovery_bp",
    "benchmark_bp",
    "tenants_bp",
]
