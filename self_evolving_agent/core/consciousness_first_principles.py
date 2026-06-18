"""
阶段84: 意识第一性原理化

第一性原理:
1. 意识是全局广播：进入意识的内容被所有模块访问
2. 意识容量有限：需要竞争进入
3. 意识内容是当前最显著的信息

设计原则:
- WorkspaceContent: 工作空间内容
- ConsciousnessStream: 意识流
- ConsciousnessFirstPrinciplesEngine: 意识引擎
- 基于全局工作空间理论
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class ContentType(Enum):
    """内容类型"""
    PERCEPTION = "perception"      # 感知
    THOUGHT = "thought"            # 思维
    MEMORY = "memory"              # 记忆
    EMOTION = "emotion"            # 情感
    GOAL = "goal"                  # 目标
    ACTION = "action"              # 行动意图


@dataclass
class WorkspaceContent:
    """工作空间内容"""
    content_id: str
    content_type: ContentType
    content: Any
    salience: float = 0.5           # 显著度 [0,1]
    duration_ms: float = 500.0      # 持续时间
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 意识第一性原理引擎
# ============================================================

class ConsciousnessFirstPrinciplesEngine:
    """
    意识第一性原理引擎

    核心原则：意识是全局广播的显著信息

    第一性原理推导（全局工作空间理论）:
    1. 多个模块并行处理信息
    2. 最显著的信息竞争进入全局工作空间
    3. 进入工作空间的信息被广播到所有模块
    4. 意识 = 当前工作空间中的内容
    5. 工作空间容量有限（7±2个组块）
    """

    def __init__(self, engine_id: str = "consciousness_engine", capacity: int = 5):
        self.engine_id = engine_id
        self._capacity = capacity
        self._workspace: List[WorkspaceContent] = []
        self._stream: List[WorkspaceContent] = []
        self._lock = threading.RLock()
        self._cycle_count = 0

    def broadcast(self, content: WorkspaceContent) -> bool:
        """
        广播内容到全局工作空间

        第一性原理：只有足够显著的内容才能进入意识
        """
        # 防御性校验：None 输入
        if content is None:
            return False
        with self._lock:
            # 如果工作空间已满，驱逐最低显著度的内容
            if len(self._workspace) >= self._capacity:
                self._workspace.sort(key=lambda c: c.salience)
                if self._workspace[0].salience < content.salience:
                    evicted = self._workspace.pop(0)
                    evicted.duration_ms = (time.time() - evicted.timestamp) * 1000
                    self._stream.append(evicted)
                else:
                    return False  # 不够显著，无法进入

            self._workspace.append(content)
            self._workspace.sort(key=lambda c: c.salience, reverse=True)
            self._cycle_count += 1
            return True

    def get_conscious_contents(self) -> List[WorkspaceContent]:
        """获取当前意识内容"""
        with self._lock:
            return list(self._workspace)

    def get_dominant_content(self) -> Optional[WorkspaceContent]:
        """获取主导意识内容"""
        with self._lock:
            if self._workspace:
                return max(self._workspace, key=lambda c: c.salience)
            return None

    def is_in_consciousness(self, content_id: str) -> bool:
        """检查内容是否在意识中"""
        with self._lock:
            return any(c.content_id == content_id for c in self._workspace)

    def update_salience(self, content_id: str, new_salience: float) -> bool:
        """更新内容显著度"""
        with self._lock:
            for content in self._workspace:
                if content.content_id == content_id:
                    content.salience = max(0.0, min(1.0, new_salience))
                    self._workspace.sort(key=lambda c: c.salience, reverse=True)
                    return True
        return False

    def clear_workspace(self) -> None:
        """清空工作空间"""
        with self._lock:
            for content in self._workspace:
                content.duration_ms = (time.time() - content.timestamp) * 1000
                self._stream.append(content)
            self._workspace.clear()

    def get_stream(self, limit: int = 100) -> List[WorkspaceContent]:
        """获取意识流历史"""
        with self._lock:
            return self._stream[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "engine_id": self.engine_id,
                "workspace_size": len(self._workspace),
                "capacity": self._capacity,
                "stream_length": len(self._stream),
                "cycle_count": self._cycle_count,
                "dominant_content": self.get_dominant_content().content_id if self.get_dominant_content() else None,
                "consciousness_utilization": len(self._workspace) / self._capacity,
            }

    def reset(self) -> None:
        """重置"""
        with self._lock:
            self._workspace.clear()
            self._stream.clear()
            self._cycle_count = 0


# ============================================================
# 便捷函数
# ============================================================

def create_consciousness_engine(engine_id: str = "consciousness_engine", capacity: int = 5) -> ConsciousnessFirstPrinciplesEngine:
    """创建意识引擎"""
    return ConsciousnessFirstPrinciplesEngine(engine_id=engine_id, capacity=capacity)


def create_workspace_content(
    content_id: str,
    content_type: ContentType,
    content: Any,
    salience: float = 0.5,
) -> WorkspaceContent:
    """创建工作空间内容"""
    return WorkspaceContent(
        content_id=content_id,
        content_type=content_type,
        content=content,
        salience=salience,
    )
