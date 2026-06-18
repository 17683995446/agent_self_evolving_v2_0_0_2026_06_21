"""
阶段98: data 子包 — 数据工程层

聚合数据管道、数据版本管理、特征工程、优化器等数据相关模块。

推荐导入方式：
    from self_evolving_agent.core.data import (
        DataPipeline,
        VersionController,
        FeatureEngineeringPipeline,
    )

向后兼容：原有 `from self_evolving_agent.core.X import Y` 仍然有效。
"""

from ..data_pipeline import DataPipeline
from ..data_versioning import VersionController
from ..feature_engineering import FeatureEngineeringPipeline
from ..optimizers import OptimizerFactory, BaseOptimizer

__all__ = [
    "DataPipeline",
    "VersionController",
    "FeatureEngineeringPipeline",
    "OptimizerFactory",
    "BaseOptimizer",
]
