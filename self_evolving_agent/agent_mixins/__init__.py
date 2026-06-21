"""
agent_mixins — SelfEvolvingAgent领域Mixin包

阶段149：将agent.py的巨型类按领域拆分为14个Mixin。
每个Mixin负责一个业务域，方法委托到对应的核心模块管理器。

SelfEvolvingAgent通过多继承组合所有Mixin，保持100%向后兼容。
"""

from .environment import EnvironmentMixin
from .persistence import PersistenceMixin
from .task import TaskMixin
from .code_docs import CodeDocsMixin
from .performance import PerformanceMixin
from .distributed import DistributedMixin
from .observability import ObservabilityMixin
from .production import ProductionMixin
from .plugins import PluginsMixin
from .config import ConfigMixin
from .security import SecurityMixin
from .recovery import RecoveryMixin
from .benchmark import BenchmarkMixin
from .tenants import TenantsMixin

__all__ = [
    "EnvironmentMixin",
    "PersistenceMixin",
    "TaskMixin",
    "CodeDocsMixin",
    "PerformanceMixin",
    "DistributedMixin",
    "ObservabilityMixin",
    "ProductionMixin",
    "PluginsMixin",
    "ConfigMixin",
    "SecurityMixin",
    "RecoveryMixin",
    "BenchmarkMixin",
    "TenantsMixin",
]
