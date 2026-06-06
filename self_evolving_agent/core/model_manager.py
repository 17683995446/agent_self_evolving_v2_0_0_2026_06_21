"""
阶段45: 模型管理接口标准化

第一性原理:
1. 模型是系统的核心资产，必须可追踪、可版本化、可复现
2. 模型有生命周期：训练->验证->注册->部署->监控->退役
3. 模型必须可比较：版本、指标、元数据

设计原则:
- Model: 模型接口定义
- ModelRegistry: 模型注册表（版本、元数据、指标）
- ModelManager: 模型生命周期管理
- 支持A/B测试、灰度发布、回滚
"""

import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


class ModelStage(Enum):
    """模型阶段"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class ModelStatus(Enum):
    """模型状态"""
    TRAINING = "training"
    VALIDATING = "validating"
    READY = "ready"
    DEPLOYED = "deployed"
    FAILED = "failed"
    RETIRED = "retired"


@dataclass
class ModelMetrics:
    """模型指标"""
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    loss: Optional[float] = None
    custom: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for k, v in self.__dict__.items():
            if v is not None and k != "custom":
                result[k] = v
        result.update(self.custom)
        return result


@dataclass
class ModelVersion:
    """模型版本"""
    version_id: str
    model_name: str
    created_at: float
    metrics: ModelMetrics = field(default_factory=ModelMetrics)
    stage: ModelStage = ModelStage.DEVELOPMENT
    status: ModelStatus = ModelStatus.READY
    metadata: Dict[str, Any] = field(default_factory=dict)
    artifact_path: Optional[str] = None


# ============================================================
# 模型接口
# ============================================================

class Model(ABC):
    """
    模型接口

    第一性原理：模型必须能预测、能评估、能序列化
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """模型名称"""
        pass

    @abstractmethod
    def predict(self, input_data: Any) -> Any:
        """预测"""
        pass

    @abstractmethod
    def evaluate(self, test_data: Any, labels: Any) -> ModelMetrics:
        """评估"""
        pass

    def get_params(self) -> Dict[str, Any]:
        """获取模型参数"""
        return {}

    def set_params(self, params: Dict[str, Any]) -> None:
        """设置模型参数"""
        pass


# ============================================================
# 模型注册表
# ============================================================

class ModelRegistry:
    """
    模型注册表

    管理模型的所有版本
    """

    def __init__(self):
        self._models: Dict[str, List[ModelVersion]] = {}  # name -> versions
        self._lock = threading.Lock()

    def register(self, version: ModelVersion) -> bool:
        """注册模型版本"""
        with self._lock:
            name = version.model_name
            if name not in self._models:
                self._models[name] = []
            self._models[name].append(version)
            return True

    def get_versions(self, model_name: str) -> List[ModelVersion]:
        """获取模型的所有版本"""
        with self._lock:
            return list(self._models.get(model_name, []))

    def get_version(self, model_name: str, version_id: str) -> Optional[ModelVersion]:
        """获取特定版本"""
        with self._lock:
            for v in self._models.get(model_name, []):
                if v.version_id == version_id:
                    return v
            return None

    def get_latest(self, model_name: str, stage: Optional[ModelStage] = None) -> Optional[ModelVersion]:
        """获取最新版本"""
        with self._lock:
            versions = self._models.get(model_name, [])
            if stage:
                versions = [v for v in versions if v.stage == stage]
            if not versions:
                return None
            return max(versions, key=lambda v: v.created_at)

    def update_stage(self, model_name: str, version_id: str, stage: ModelStage) -> bool:
        """更新模型阶段"""
        with self._lock:
            for v in self._models.get(model_name, []):
                if v.version_id == version_id:
                    v.stage = stage
                    return True
            return False

    def update_status(self, model_name: str, version_id: str, status: ModelStatus) -> bool:
        """更新模型状态"""
        with self._lock:
            for v in self._models.get(model_name, []):
                if v.version_id == version_id:
                    v.status = status
                    return True
            return False

    def list_models(self) -> List[str]:
        """列出所有模型名称"""
        with self._lock:
            return list(self._models.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total_versions = sum(len(vs) for vs in self._models.values())
            return {
                "total_models": len(self._models),
                "total_versions": total_versions,
            }


# ============================================================
# 模型管理器
# ============================================================

class ModelManager:
    """
    模型管理器

    管理模型的完整生命周期
    """

    def __init__(self):
        self.registry = ModelRegistry()
        self._deployed: Dict[str, ModelVersion] = {}  # alias -> version
        self._lock = threading.Lock()

    def register_model(
        self,
        model: Model,
        metrics: Optional[ModelMetrics] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModelVersion:
        """注册新模型版本"""
        version = ModelVersion(
            version_id=f"{model.name}_{int(time.time() * 1000)}",
            model_name=model.name,
            created_at=time.time(),
            metrics=metrics or ModelMetrics(),
            metadata=metadata or {},
        )
        self.registry.register(version)
        return version

    def deploy(self, model_name: str, version_id: str, alias: str = "default") -> bool:
        """部署模型"""
        version = self.registry.get_version(model_name, version_id)
        if version is None:
            return False

        with self._lock:
            self._deployed[alias] = version

        self.registry.update_status(model_name, version_id, ModelStatus.DEPLOYED)
        return True

    def undeploy(self, alias: str) -> bool:
        """取消部署"""
        with self._lock:
            if alias in self._deployed:
                del self._deployed[alias]
                return True
            return False

    def get_deployed(self, alias: str = "default") -> Optional[ModelVersion]:
        """获取已部署的模型版本"""
        with self._lock:
            return self._deployed.get(alias)

    def promote(self, model_name: str, version_id: str, stage: ModelStage) -> bool:
        """提升模型阶段"""
        return self.registry.update_stage(model_name, version_id, stage)

    def compare_versions(self, model_name: str, v1_id: str, v2_id: str) -> Dict[str, Any]:
        """比较两个版本"""
        v1 = self.registry.get_version(model_name, v1_id)
        v2 = self.registry.get_version(model_name, v2_id)

        if v1 is None or v2 is None:
            return {"error": "Version not found"}

        m1 = v1.metrics.to_dict()
        m2 = v2.metrics.to_dict()

        comparison = {}
        all_keys = set(m1.keys()) | set(m2.keys())
        for k in all_keys:
            val1 = m1.get(k)
            val2 = m2.get(k)
            if val1 is not None and val2 is not None:
                diff = val2 - val1
                comparison[k] = {
                    "v1": val1,
                    "v2": val2,
                    "diff": diff,
                    "improved": diff > 0 if k != "loss" else diff < 0,
                }
            else:
                comparison[k] = {"v1": val1, "v2": val2}

        return comparison

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            registry_stats = self.registry.get_stats()
            return {
                **registry_stats,
                "deployed_aliases": len(self._deployed),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_model_manager() -> ModelManager:
    """创建模型管理器"""
    return ModelManager()
