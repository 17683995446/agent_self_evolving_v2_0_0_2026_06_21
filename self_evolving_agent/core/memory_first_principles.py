"""
阶段75: 记忆第一性原理化

第一性原理:
1. 信息价值决定记忆优先级：无价值信息无需记忆
2. 记忆是压缩：只保留能减小未来预测误差的信息
3. 遗忘是优化：清除无价值信息释放资源

设计原则:
- MemoryItem: 记忆条目，带信息价值评分
- InformationValue: 信息价值计算
- MemoryFirstPrinciplesEngine: 记忆引擎
- 存储/保留/遗忘都基于信息增益
"""

import threading
import time
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class MemoryPriority(Enum):
    """记忆优先级"""
    CRITICAL = "critical"      # 关键信息，永久保留
    HIGH = "high"              # 高价值信息
    MEDIUM = "medium"          # 中等价值
    LOW = "low"                # 低价值，可遗忘
    EPHEMERAL = "ephemeral"    # 临时信息，立即遗忘


@dataclass
class MemoryItem:
    """记忆条目"""
    item_id: str
    content: Any
    information_value: float = 0.0        # 信息价值 [0,1]
    access_count: int = 0                 # 访问次数
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    priority: MemoryPriority = MemoryPriority.MEDIUM

    @property
    def retention_score(self) -> float:
        """
        保留分数

        第一性原理：保留分数 = 信息价值 * 时效衰减 + 访问频率奖励
        """
        age_sec = time.time() - self.created_at
        # 阶段104修复：防止时钟偏移导致 OverflowError
        if age_sec < 0:
            age_sec = 0.0
        try:
            time_decay = math.exp(-age_sec / 3600.0)  # 1小时衰减常数
        except OverflowError:
            time_decay = 0.0

        access_bonus = min(1.0, max(0.0, self.access_count / 10.0))

        return self.information_value * time_decay + access_bonus * 0.2

    def access(self) -> None:
        """访问记忆"""
        self.access_count += 1
        self.last_accessed = time.time()


# ============================================================
# 记忆第一性原理引擎
# ============================================================

class MemoryFirstPrinciplesEngine:
    """
    记忆第一性原理引擎

    核心原则：信息价值决定记忆操作

    第一性原理推导:
    1. 信息的价值 = 能减小多少未来预测误差
    2. 高价值信息 -> 存储 -> 长期记忆
    3. 低价值信息 -> 丢弃 -> 遗忘
    4. 记忆容量有限，必须优化信息密度
    """

    def __init__(
        self,
        engine_id: str = "memory_engine",
        capacity: int = 1000,
        retention_threshold: float = 0.1,
    ):
        self.engine_id = engine_id
        self._capacity = capacity
        self._retention_threshold = retention_threshold
        self._items: Dict[str, MemoryItem] = {}
        self._lock = threading.RLock()
        self._stored_count = 0
        self._forgotten_count = 0

    def evaluate_information_value(
        self,
        content: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        评估信息价值

        第一性原理：信息价值 = 与现有记忆的差异度
        越新颖的信息价值越高
        """
        # 简单实现：基于内容哈希的新颖度
        content_str = str(content)
        novelty = 1.0

        with self._lock:
            for item in self._items.values():
                if str(item.content) == content_str:
                    novelty = 0.1  # 重复信息价值低
                    break
                # 简单字符串相似度
                similarity = self._string_similarity(content_str, str(item.content))
                novelty = min(novelty, 1.0 - similarity)

        # 上下文增强
        if context and context.get("error_reduction_potential"):
            novelty *= (1.0 + float(context["error_reduction_potential"]))
            novelty = min(1.0, novelty)

        return novelty

    def _string_similarity(self, a: str, b: str) -> float:
        """简单字符串相似度"""
        if not a or not b:
            return 0.0
        # 使用最长公共子串的简单近似
        shorter = min(len(a), len(b))
        if shorter == 0:
            return 0.0
        common = sum(1 for i in range(shorter) if i < len(a) and i < len(b) and a[i] == b[i])
        return common / max(len(a), len(b))

    def store(
        self,
        item_id: str,
        content: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[MemoryItem]:
        """
        存储记忆

        第一性原理：只有高价值信息才值得存储
        """
        with self._lock:
            # 阶段106修复：如果key已存在，直接覆盖更新（不检查信息价值）
            if item_id in self._items:
                value = self.evaluate_information_value(content, context)
                item = MemoryItem(
                    item_id=item_id,
                    content=content,
                    information_value=value,
                    priority=self._items[item_id].priority,  # 保留原优先级
                )
                self._items[item_id] = item
                self._stored_count += 1
                return item

        value = self.evaluate_information_value(content, context)

        if value < self._retention_threshold:
            with self._lock:
                self._forgotten_count += 1
            return None

        # 确定优先级
        if value > 0.9:
            priority = MemoryPriority.CRITICAL
        elif value > 0.7:
            priority = MemoryPriority.HIGH
        elif value > 0.4:
            priority = MemoryPriority.MEDIUM
        elif value > 0.2:
            priority = MemoryPriority.LOW
        else:
            priority = MemoryPriority.EPHEMERAL

        item = MemoryItem(
            item_id=item_id,
            content=content,
            information_value=value,
            priority=priority,
        )

        with self._lock:
            # 容量管理：如果满了，遗忘最低保留分数的
            if len(self._items) >= self._capacity:
                self._forget_lowest_value()

            self._items[item_id] = item
            self._stored_count += 1

        return item

    def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        """检索记忆"""
        with self._lock:
            item = self._items.get(item_id)
        if item:
            item.access()
            return item
        return None

    def search_by_value(self, min_value: float = 0.5) -> List[MemoryItem]:
        """按价值搜索记忆"""
        with self._lock:
            return [item for item in self._items.values() if item.information_value >= min_value]

    def _forget_lowest_value(self) -> None:
        """
        遗忘最低价值的记忆

        第一性原理：遗忘是优化，释放资源给高价值信息
        """
        if not self._items:
            return

        # 找到保留分数最低的非关键记忆
        lowest_id = None
        lowest_score = float('inf')

        for item_id, item in self._items.items():
            if item.priority == MemoryPriority.CRITICAL:
                continue  # 关键记忆不遗忘
            score = item.retention_score
            if score < lowest_score:
                lowest_score = score
                lowest_id = item_id

        if lowest_id:
            del self._items[lowest_id]
            self._forgotten_count += 1

    def consolidate(self) -> int:
        """
        记忆巩固

        清理低价值记忆，优化存储
        """
        forgotten = 0
        with self._lock:
            to_forget = [
                item_id for item_id, item in self._items.items()
                if item.priority != MemoryPriority.CRITICAL
                and item.retention_score < self._retention_threshold
            ]
            for item_id in to_forget:
                del self._items[item_id]
                forgotten += 1
            self._forgotten_count += forgotten

        return forgotten

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            # 阶段104修复：capacity=0 时防止 ZeroDivisionError
            utilization = len(self._items) / self._capacity if self._capacity > 0 else 0.0
            return {
                "engine_id": self.engine_id,
                "items_count": len(self._items),
                "capacity": self._capacity,
                "stored_count": self._stored_count,
                "forgotten_count": self._forgotten_count,
                "utilization": utilization,
                "avg_information_value": sum(i.information_value for i in self._items.values()) / len(self._items) if self._items else 0,
            }

    def clear(self) -> None:
        """清空记忆"""
        with self._lock:
            self._items.clear()


# ============================================================
# 便捷函数
# ============================================================

def create_memory_engine(
    engine_id: str = "memory_engine",
    capacity: int = 1000,
) -> MemoryFirstPrinciplesEngine:
    """创建记忆引擎"""
    return MemoryFirstPrinciplesEngine(engine_id=engine_id, capacity=capacity)


def create_memory_item(
    item_id: str,
    content: Any,
    information_value: float = 0.5,
) -> MemoryItem:
    """创建记忆条目"""
    return MemoryItem(
        item_id=item_id,
        content=content,
        information_value=information_value,
    )
