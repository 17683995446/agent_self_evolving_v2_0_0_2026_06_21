"""
阶段53: 数据版本控制接口标准化

第一性原理:
1. 数据是系统的核心资产，变更必须可追溯
2. 版本控制让数据可回滚、可对比、可审计
3. 每次变更都是不可变快照，防止意外覆盖

设计原则:
- DataVersion: 数据版本定义
- VersionedDataset: 版本化数据集
- VersionController: 版本控制器
- 支持分支、标签、回滚、差异比较
"""

import hashlib
import time
import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class VersionStatus(Enum):
    """版本状态"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass
class DataVersion:
    """数据版本"""
    version_id: str
    parent_id: Optional[str]
    timestamp: float
    author: str
    comment: str
    data_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: VersionStatus = VersionStatus.ACTIVE
    tags: List[str] = field(default_factory=list)


# ============================================================
# 版本化数据集
# ============================================================

class VersionedDataset:
    """
    版本化数据集

    管理数据的多版本历史，支持快照和回滚
    """

    def __init__(self, dataset_id: str):
        self.dataset_id = dataset_id
        self._versions: Dict[str, DataVersion] = {}
        self._data_store: Dict[str, Any] = {}  # version_id -> data snapshot
        self._current_version_id: Optional[str] = None

    def commit(
        self,
        data: Any,
        author: str,
        comment: str,
        tags: Optional[List[str]] = None,
    ) -> DataVersion:
        """提交新版本"""
        data_hash = self._compute_hash(data)
        version_id = f"v{len(self._versions) + 1}_{int(time.time() * 1000)}"

        version = DataVersion(
            version_id=version_id,
            parent_id=self._current_version_id,
            timestamp=time.time(),
            author=author,
            comment=comment,
            data_hash=data_hash,
            tags=tags or [],
        )

        self._versions[version_id] = version
        self._data_store[version_id] = copy.deepcopy(data)
        self._current_version_id = version_id
        return version

    def checkout(self, version_id: str) -> Optional[Any]:
        """检出指定版本的数据"""
        if version_id not in self._data_store:
            return None
        return copy.deepcopy(self._data_store[version_id])

    def get_version(self, version_id: str) -> Optional[DataVersion]:
        """获取版本信息"""
        return self._versions.get(version_id)

    def get_current_version(self) -> Optional[DataVersion]:
        """获取当前版本"""
        if self._current_version_id is None:
            return None
        return self._versions.get(self._current_version_id)

    def get_history(self) -> List[DataVersion]:
        """获取版本历史（按时间倒序）"""
        return sorted(
            self._versions.values(),
            key=lambda v: v.timestamp,
            reverse=True,
        )

    def rollback(self, version_id: str) -> bool:
        """回滚到指定版本"""
        if version_id not in self._versions:
            return False
        self._current_version_id = version_id
        return True

    def diff(self, version_a: str, version_b: str) -> Dict[str, Any]:
        """比较两个版本的差异"""
        data_a = self._data_store.get(version_a)
        data_b = self._data_store.get(version_b)
        return {
            "version_a": version_a,
            "version_b": version_b,
            "same": data_a == data_b,
            "size_a": len(str(data_a)) if data_a is not None else 0,
            "size_b": len(str(data_b)) if data_b is not None else 0,
        }

    def tag(self, version_id: str, tag: str) -> bool:
        """为版本打标签"""
        version = self._versions.get(version_id)
        if version is None:
            return False
        if tag not in version.tags:
            version.tags.append(tag)
        return True

    def find_by_tag(self, tag: str) -> List[DataVersion]:
        """按标签查找版本"""
        return [v for v in self._versions.values() if tag in v.tags]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "dataset_id": self.dataset_id,
            "total_versions": len(self._versions),
            "current_version": self._current_version_id,
        }

    @staticmethod
    def _compute_hash(data: Any) -> str:
        """计算数据哈希"""
        return hashlib.sha256(str(data).encode()).hexdigest()[:16]


# ============================================================
# 版本控制器
# ============================================================

class VersionController:
    """
    版本控制器

    管理多个版本化数据集
    """

    def __init__(self):
        self._datasets: Dict[str, VersionedDataset] = {}

    def create_dataset(self, dataset_id: str) -> VersionedDataset:
        """创建数据集"""
        dataset = VersionedDataset(dataset_id)
        self._datasets[dataset_id] = dataset
        return dataset

    def get_dataset(self, dataset_id: str) -> Optional[VersionedDataset]:
        """获取数据集"""
        return self._datasets.get(dataset_id)

    def list_datasets(self) -> List[str]:
        """列出所有数据集"""
        return list(self._datasets.keys())

    def delete_dataset(self, dataset_id: str) -> bool:
        """删除数据集"""
        if dataset_id not in self._datasets:
            return False
        del self._datasets[dataset_id]
        return True


# ============================================================
# 便捷函数
# ============================================================

def create_version_controller() -> VersionController:
    """创建版本控制器"""
    return VersionController()


def create_versioned_dataset(dataset_id: str) -> VersionedDataset:
    """创建版本化数据集"""
    return VersionedDataset(dataset_id)
