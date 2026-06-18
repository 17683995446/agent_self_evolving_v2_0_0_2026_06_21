"""
阶段98: mlops 子包 — 机器学习工程化层

聚合模型管理、模型蒸馏、联邦学习、A/B 测试、CI、自动化测试等 MLOps 模块。

推荐导入方式：
    from self_evolving_agent.core.mlops import (
        ModelManager,
        DistillationTrainer,
        FederatedServer,
        ABTestEngine,
    )

向后兼容：原有 `from self_evolving_agent.core.X import Y` 仍然有效。
"""

from ..model_manager import ModelManager
from ..model_distillation import DistillationTrainer
from ..federated_learning import FederatedServer
from ..ab_testing import ABTestEngine
from ..auto_testing import TestRunner
from ..ci_engine import CIEngine
from ..contract_testing import ContractTestExecutor
from ..doc_generator import InterfaceDocGenerator, SystemDocGenerator

__all__ = [
    "ModelManager",
    "DistillationTrainer",
    "FederatedServer",
    "ABTestEngine",
    "TestRunner",
    "CIEngine",
    "ContractTestExecutor",
    "InterfaceDocGenerator",
    "SystemDocGenerator",
]
