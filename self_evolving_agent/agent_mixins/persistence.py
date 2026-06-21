"""持久化管理Mixin — 阶段149从agent.py拆分"""

import time
from typing import Any, Dict, Optional

from ..core.persistence import StorageInterface, PersistenceManager


class PersistenceMixin:
    """持久化接口（阶段126）"""

    def save_state(self, key: str, state: Dict[str, Any]) -> bool:
        """保存状态到持久化存储（阶段126新增）"""
        return self._persistence.save_state(key, state)

    def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        """从持久化存储加载状态（阶段126新增）"""
        return self._persistence.load_state(key)

    def save_checkpoint(self, checkpoint_id: str = None) -> str:
        """保存检查点（阶段126新增）"""
        if checkpoint_id is None:
            checkpoint_id = f"checkpoint_{int(time.time())}"
        state = {
            "cycle_count": self._cycle_count,
            "timestamp": time.time(),
        }
        self._persistence.save_checkpoint(checkpoint_id, state)
        return checkpoint_id

    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """加载检查点（阶段126新增）"""
        return self._persistence.load_checkpoint(checkpoint_id)

    def set_persistence_storage(self, storage: StorageInterface) -> None:
        """设置持久化存储后端（阶段126新增）"""
        self._persistence = PersistenceManager(
            storage=storage,
            manager_id=self._persistence.manager_id,
        )
