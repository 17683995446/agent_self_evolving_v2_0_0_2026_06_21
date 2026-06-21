"""
阶段117: 记忆系统强化 — 分层记忆 + 遗忘曲线

第一性原理:
1. 信息价值决定记忆优先级：无价值信息无需记忆
2. 记忆是压缩：只保留能减小未来预测误差的信息
3. 遗忘是优化：清除无价值信息释放资源
4. 记忆是分层的：工作记忆→短期记忆→长期记忆
5. 遗忘遵循指数曲线：R = e^(-t/S)，S随复习增大

强化内容:
- MemoryLayer: 记忆层级（工作/短期/长期）
- EbbinghausForgetting: 艾宾浩斯遗忘曲线
  R(t) = e^(-t/S)，S = 记忆强度，每次访问S增大
- LayeredMemoryStore: 分层记忆存储
  - 工作记忆：容量7±2，快速衰减
  - 短期记忆：容量100，中等衰减
  - 长期记忆：容量大，缓慢衰减
- MemoryConsolidator: 记忆巩固器
  - 工作记忆→短期记忆：频繁访问的项目提升
  - 短期记忆→长期记忆：经过巩固窗口的项目提升
- SpacedRepetition: 间隔重复
  - 每次访问增强记忆强度

向后兼容: 保留原有 MemoryFirstPrinciplesEngine 接口
"""

import threading
import time
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from collections import deque, OrderedDict


# ============================================================
# 基础枚举与数据结构（向后兼容）
# ============================================================

class MemoryPriority(Enum):
    """记忆优先级（向后兼容）"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    EPHEMERAL = "ephemeral"


class MemoryLayerType(Enum):
    """记忆层级类型"""
    WORKING = "working"       # 工作记忆：即时、容量小、快速衰减
    SHORT_TERM = "short_term" # 短期记忆：近期、容量中、中等衰减
    LONG_TERM = "long_term"   # 长期记忆：巩固、容量大、缓慢衰减


# 层级配置：容量、衰减常数、巩固阈值
LAYER_CONFIG: Dict[MemoryLayerType, Dict[str, Any]] = {
    MemoryLayerType.WORKING: {
        "capacity": 7,           # 7±2 原则
        "decay_constant": 60.0,  # 60秒衰减常数（快速遗忘）
        "consolidation_threshold": 3,  # 访问3次后可巩固到短期
        "consolidation_window": 30.0,  # 30秒内需要被访问
    },
    MemoryLayerType.SHORT_TERM: {
        "capacity": 100,
        "decay_constant": 3600.0,  # 1小时衰减常数
        "consolidation_threshold": 5,  # 访问5次后可巩固到长期
        "consolidation_window": 3600.0,  # 1小时内需要被访问
    },
    MemoryLayerType.LONG_TERM: {
        "capacity": 10000,
        "decay_constant": 86400.0 * 30,  # 30天衰减常数
        "consolidation_threshold": float("inf"),  # 长期不再提升
        "consolidation_window": float("inf"),
    },
}


@dataclass
class MemoryItem:
    """
    记忆条目（增强版）

    新增字段：
    - memory_layer: 所在记忆层级
    - memory_strength: 记忆强度（影响遗忘曲线）
    - last_review_time: 上次复习时间
    - review_count: 复习次数
    - tags: 标签集合（用于关联检索）
    """
    item_id: str
    content: Any
    information_value: float = 0.0
    access_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    priority: MemoryPriority = MemoryPriority.MEDIUM
    # 阶段117新增字段
    memory_layer: MemoryLayerType = MemoryLayerType.WORKING
    memory_strength: float = 1.0       # 记忆强度S（越大越不易遗忘）
    last_review_time: float = field(default_factory=time.time)
    review_count: int = 0              # 间隔重复次数
    tags: set = field(default_factory=set)

    @property
    def retention_score(self) -> float:
        """
        保留分数（向后兼容）

        第一性原理：保留分数 = 信息价值 * 时效衰减 + 访问频率奖励
        """
        age_sec = time.time() - self.created_at
        if age_sec < 0:
            age_sec = 0.0
        try:
            time_decay = math.exp(-age_sec / 3600.0)
        except OverflowError:
            time_decay = 0.0

        access_bonus = min(1.0, max(0.0, self.access_count / 10.0))
        return self.information_value * time_decay + access_bonus * 0.2

    @property
    def recall_probability(self) -> float:
        """
        回忆概率（艾宾浩斯遗忘曲线）

        第一性原理：R(t) = e^(-t/S)
        - t = 距上次复习的时间
        - S = 记忆强度
        - R = 回忆概率 [0, 1]
        """
        time_since_review = time.time() - self.last_review_time
        if time_since_review < 0:
            time_since_review = 0.0

        config = LAYER_CONFIG.get(self.memory_layer, LAYER_CONFIG[MemoryLayerType.SHORT_TERM])
        decay_constant = config["decay_constant"]

        # 有效强度 = 记忆强度 × 层级衰减常数
        effective_strength = max(0.01, self.memory_strength * decay_constant)

        try:
            recall = math.exp(-time_since_review / effective_strength)
        except (OverflowError, ZeroDivisionError):
            recall = 0.0

        # 信息价值加成
        recall = recall * (0.5 + 0.5 * self.information_value)
        return max(0.0, min(1.0, recall))

    def access(self) -> None:
        """访问记忆（增强版：间隔重复增强强度）"""
        self.access_count += 1
        self.last_accessed = time.time()
        # 间隔重复：每次访问增强记忆强度
        self._reinforce()

    def review(self) -> None:
        """复习记忆（间隔重复）"""
        self.review_count += 1
        self.last_review_time = time.time()
        self._reinforce()

    def _reinforce(self) -> None:
        """
        增强记忆强度

        第一性原理：间隔重复增强记忆
        S_new = S_old * (1 + reinforcement_factor)
        reinforcement_factor 随复习次数递减（边际效应）
        """
        # 边际递减的增强因子
        reinforcement = 1.0 / (1.0 + self.review_count * 0.1)
        self.memory_strength *= (1.0 + reinforcement)
        # 上限防止无限增长
        self.memory_strength = min(100.0, self.memory_strength)


# ============================================================
# 阶段117新增：分层记忆存储
# ============================================================

class LayeredMemoryStore:
    """
    分层记忆存储

    第一性原理：
    - 工作记忆：容量极小（7±2），快速衰减，即时处理
    - 短期记忆：容量中等，中等衰减，近期信息
    - 长期记忆：容量大，缓慢衰减，巩固信息

    层级间通过巩固机制流动：
    工作记忆 →（频繁访问）→ 短期记忆 →（巩固窗口）→ 长期记忆
    """

    def __init__(self):
        self._layers: Dict[MemoryLayerType, OrderedDict[str, MemoryItem]] = {
            MemoryLayerType.WORKING: OrderedDict(),
            MemoryLayerType.SHORT_TERM: OrderedDict(),
            MemoryLayerType.LONG_TERM: OrderedDict(),
        }
        self._lock = threading.RLock()
        # 统计
        self._promotion_count = 0
        self._demotion_count = 0

    def add(self, item: MemoryItem, layer: Optional[MemoryLayerType] = None) -> bool:
        """添加记忆到指定层"""
        if layer is not None:
            item.memory_layer = layer
        with self._lock:
            target_layer = item.memory_layer
            capacity = LAYER_CONFIG[target_layer]["capacity"]
            store = self._layers[target_layer]

            if item.item_id in store:
                # 已存在，更新
                store[item.item_id] = item
                return True

            # 容量管理
            while len(store) >= capacity:
                self._evict_oldest(target_layer)

            store[item.item_id] = item
            return True

    def get(self, item_id: str) -> Optional[MemoryItem]:
        """获取记忆（跨层查找）"""
        with self._lock:
            for layer_store in self._layers.values():
                if item_id in layer_store:
                    return layer_store[item_id]
            return None

    def remove(self, item_id: str) -> bool:
        """移除记忆"""
        with self._lock:
            for layer_store in self._layers.values():
                if item_id in layer_store:
                    del layer_store[item_id]
                    return True
            return False

    def access(self, item_id: str) -> Optional[MemoryItem]:
        """访问记忆（更新访问计数和强度）"""
        with self._lock:
            item = self.get(item_id)
            if item is not None:
                item.access()
            return item

    def _evict_oldest(self, layer: MemoryLayerType) -> None:
        """驱逐最旧的记忆（LRU策略）"""
        store = self._layers[layer]
        if not store:
            return
        # 找到回忆概率最低的非关键记忆
        lowest_id = None
        lowest_prob = float("inf")
        for item_id, item in store.items():
            if item.priority == MemoryPriority.CRITICAL:
                continue
            prob = item.recall_probability
            if prob < lowest_prob:
                lowest_prob = prob
                lowest_id = item_id

        if lowest_id is None:
            # 全是关键记忆，驱逐最旧的
            lowest_id = next(iter(store))

        if lowest_id:
            del store[lowest_id]

    def promote(self, item_id: str, to_layer: MemoryLayerType) -> bool:
        """
        提升记忆到更高层

        第一性原理：频繁访问的记忆应被巩固到更持久的层
        """
        with self._lock:
            # 找到当前层
            current_layer = None
            for layer_type, store in self._layers.items():
                if item_id in store:
                    current_layer = layer_type
                    break

            if current_layer is None or current_layer == to_layer:
                return False

            item = self._layers[current_layer].pop(item_id)
            item.memory_layer = to_layer

            # 添加到目标层
            capacity = LAYER_CONFIG[to_layer]["capacity"]
            target_store = self._layers[to_layer]
            while len(target_store) >= capacity:
                self._evict_oldest(to_layer)
            target_store[item_id] = item

            self._promotion_count += 1
            return True

    def get_layer_items(self, layer: MemoryLayerType) -> List[MemoryItem]:
        """获取指定层的所有记忆"""
        with self._lock:
            return list(self._layers[layer].values())

    def get_all_items(self) -> List[MemoryItem]:
        """获取所有记忆"""
        with self._lock:
            all_items: List[MemoryItem] = []
            for store in self._layers.values():
                all_items.extend(store.values())
            return all_items

    def get_layer_count(self, layer: MemoryLayerType) -> int:
        """获取指定层记忆数"""
        with self._lock:
            return len(self._layers[layer])

    def get_total_count(self) -> int:
        """获取总记忆数"""
        with self._lock:
            return sum(len(store) for store in self._layers.values())

    def clear_layer(self, layer: MemoryLayerType) -> int:
        """清空指定层"""
        with self._lock:
            count = len(self._layers[layer])
            self._layers[layer].clear()
            return count

    def clear_all(self) -> None:
        """清空所有层"""
        with self._lock:
            for store in self._layers.values():
                store.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            layer_counts = {}
            layer_avg_recall = {}
            for layer_type, store in self._layers.items():
                layer_counts[layer_type.value] = len(store)
                if store:
                    avg_recall = sum(item.recall_probability for item in store.values()) / len(store)
                    layer_avg_recall[layer_type.value] = avg_recall
                else:
                    layer_avg_recall[layer_type.value] = 0.0

            return {
                "layer_counts": layer_counts,
                "layer_avg_recall": layer_avg_recall,
                "total_count": self.get_total_count(),
                "promotion_count": self._promotion_count,
                "demotion_count": self._demotion_count,
            }


# ============================================================
# 阶段117新增：记忆巩固器
# ============================================================

class MemoryConsolidator:
    """
    记忆巩固器

    第一性原理：
    - 工作记忆中的信息如果被频繁访问，应巩固到短期记忆
    - 短期记忆中的信息如果经过巩固窗口仍被保留，应巩固到长期记忆
    - 巩固是主动过程，定期执行

    巩固规则：
    1. 工作记忆 → 短期记忆：
       - 访问次数 >= consolidation_threshold
       - 在 consolidation_window 内被访问
    2. 短期记忆 → 长期记忆：
       - 访问次数 >= consolidation_threshold
       - 回忆概率 > 0.3（仍被记住）
    3. 低回忆概率的记忆被遗忘
    """

    def __init__(self, store: LayeredMemoryStore):
        self._store = store
        self._lock = threading.RLock()
        self._consolidation_count = 0
        self._forget_count = 0

    def consolidate(self) -> Dict[str, int]:
        """
        执行记忆巩固

        Returns: {"promoted_to_short": n, "promoted_to_long": n, "forgotten": n}
        """
        results = {"promoted_to_short": 0, "promoted_to_long": 0, "forgotten": 0}

        with self._lock:
            # 1. 工作记忆 → 短期记忆
            working_items = self._store.get_layer_items(MemoryLayerType.WORKING)
            working_config = LAYER_CONFIG[MemoryLayerType.WORKING]

            for item in working_items:
                if item.priority == MemoryPriority.CRITICAL:
                    # 关键记忆直接提升到长期
                    if self._store.promote(item.item_id, MemoryLayerType.LONG_TERM):
                        results["promoted_to_long"] += 1
                    continue

                if (item.access_count >= working_config["consolidation_threshold"] and
                    (time.time() - item.last_accessed) < working_config["consolidation_window"]):
                    if self._store.promote(item.item_id, MemoryLayerType.SHORT_TERM):
                        results["promoted_to_short"] += 1

            # 2. 短期记忆 → 长期记忆
            short_items = self._store.get_layer_items(MemoryLayerType.SHORT_TERM)
            short_config = LAYER_CONFIG[MemoryLayerType.SHORT_TERM]

            for item in short_items:
                if item.priority == MemoryPriority.CRITICAL:
                    if self._store.promote(item.item_id, MemoryLayerType.LONG_TERM):
                        results["promoted_to_long"] += 1
                    continue

                if (item.access_count >= short_config["consolidation_threshold"] and
                    item.recall_probability > 0.3):
                    if self._store.promote(item.item_id, MemoryLayerType.LONG_TERM):
                        results["promoted_to_long"] += 1

            # 3. 遗忘低回忆概率的记忆
            for layer_type in [MemoryLayerType.WORKING, MemoryLayerType.SHORT_TERM]:
                items = self._store.get_layer_items(layer_type)
                for item in items:
                    if item.priority == MemoryPriority.CRITICAL:
                        continue
                    if item.recall_probability < 0.01:
                        if self._store.remove(item.item_id):
                            results["forgotten"] += 1

            self._consolidation_count += 1
            self._forget_count += results["forgotten"]

        return results

    def review_item(self, item_id: str) -> bool:
        """
        复习特定记忆（间隔重复）

        第一性原理：主动复习增强记忆强度
        """
        item = self._store.get(item_id)
        if item is None:
            return False
        item.review()
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "consolidation_count": self._consolidation_count,
                "forget_count": self._forget_count,
            }


# ============================================================
# 增强记忆引擎（向后兼容 + 新能力）
# ============================================================

class MemoryFirstPrinciplesEngine:
    """
    记忆第一性原理引擎（阶段117增强版）

    新增能力:
    - 分层记忆存储（LayeredMemoryStore）
    - 艾宾浩斯遗忘曲线（recall_probability）
    - 记忆巩固器（MemoryConsolidator）
    - 间隔重复（review机制）

    向后兼容: 保留原有 store / retrieve / consolidate 接口
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
        self._items: Dict[str, MemoryItem] = {}  # 向后兼容的扁平存储
        self._lock = threading.RLock()
        self._stored_count = 0
        self._forgotten_count = 0

        # 阶段117新增能力
        self._layered_store = LayeredMemoryStore()
        self._consolidator = MemoryConsolidator(self._layered_store)

    # ============================================================
    # 原有接口（向后兼容）
    # ============================================================

    def evaluate_information_value(
        self,
        content: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """评估信息价值（向后兼容）"""
        content_str = str(content)
        novelty = 1.0

        with self._lock:
            for item in self._items.values():
                if str(item.content) == content_str:
                    novelty = 0.1
                    break
                similarity = self._string_similarity(content_str, str(item.content))
                novelty = min(novelty, 1.0 - similarity)

        if context and context.get("error_reduction_potential"):
            try:
                novelty *= (1.0 + float(context["error_reduction_potential"]))
                novelty = min(1.0, novelty)
            except (TypeError, ValueError):
                pass

        return novelty

    def _string_similarity(self, a: str, b: str) -> float:
        """简单字符串相似度"""
        if not a or not b:
            return 0.0
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
        存储记忆（向后兼容 + 分层存储）

        第一性原理：只有高价值信息才值得存储
        新增：同时存入分层存储的工作记忆层
        """
        with self._lock:
            # 阶段106修复：如果key已存在，直接覆盖更新
            if item_id in self._items:
                value = self.evaluate_information_value(content, context)
                item = MemoryItem(
                    item_id=item_id,
                    content=content,
                    information_value=value,
                    priority=self._items[item_id].priority,
                )
                self._items[item_id] = item
                self._stored_count += 1
                # 同步到分层存储
                self._layered_store.add(item)
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
            # 容量管理
            if len(self._items) >= self._capacity:
                self._forget_lowest_value()

            self._items[item_id] = item
            self._stored_count += 1
            # 同步到分层存储（新记忆进入工作记忆层）
            self._layered_store.add(item)

        return item

    def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        """检索记忆（向后兼容 + 分层查找）"""
        with self._lock:
            item = self._items.get(item_id)
        if item:
            item.access()
            return item
        # 尝试从分层存储查找
        return self._layered_store.access(item_id)

    def search_by_value(self, min_value: float = 0.5) -> List[MemoryItem]:
        """按价值搜索记忆（向后兼容）"""
        with self._lock:
            return [item for item in self._items.values() if item.information_value >= min_value]

    def _forget_lowest_value(self) -> None:
        """遗忘最低价值的记忆"""
        if not self._items:
            return

        lowest_id = None
        lowest_score = float('inf')

        for item_id, item in self._items.items():
            if item.priority == MemoryPriority.CRITICAL:
                continue
            score = item.retention_score
            if score < lowest_score:
                lowest_score = score
                lowest_id = item_id

        if lowest_id:
            del self._items[lowest_id]
            self._forgotten_count += 1

    def consolidate(self) -> int:
        """
        记忆巩固（向后兼容 + 分层巩固）

        第一性原理：清理低价值记忆，优化存储
        新增：执行分层记忆巩固
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

        # 执行分层巩固
        self._consolidator.consolidate()

        return forgotten

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            utilization = len(self._items) / self._capacity if self._capacity > 0 else 0.0
            return {
                "engine_id": self.engine_id,
                "items_count": len(self._items),
                "capacity": self._capacity,
                "stored_count": self._stored_count,
                "forgotten_count": self._forgotten_count,
                "utilization": utilization,
                "avg_information_value": sum(i.information_value for i in self._items.values()) / len(self._items) if self._items else 0,
                # 阶段117新增统计
                "layered_store_stats": self._layered_store.get_stats(),
                "consolidator_stats": self._consolidator.get_stats(),
            }

    def clear(self) -> None:
        """清空记忆"""
        with self._lock:
            self._items.clear()
            self._layered_store.clear_all()

    # ============================================================
    # 阶段117新增：分层记忆接口
    # ============================================================

    def store_in_layer(
        self,
        item_id: str,
        content: Any,
        layer: MemoryLayerType = MemoryLayerType.WORKING,
        information_value: Optional[float] = None,
        tags: Optional[set] = None,
    ) -> Optional[MemoryItem]:
        """
        存储到指定记忆层

        第一性原理：不同层有不同的容量和衰减特性
        """
        if information_value is None:
            information_value = self.evaluate_information_value(content)

        # 确定优先级
        if information_value > 0.9:
            priority = MemoryPriority.CRITICAL
        elif information_value > 0.7:
            priority = MemoryPriority.HIGH
        elif information_value > 0.4:
            priority = MemoryPriority.MEDIUM
        elif information_value > 0.2:
            priority = MemoryPriority.LOW
        else:
            priority = MemoryPriority.EPHEMERAL

        item = MemoryItem(
            item_id=item_id,
            content=content,
            information_value=information_value,
            priority=priority,
            memory_layer=layer,
            tags=tags or set(),
        )

        if self._layered_store.add(item):
            # 同步到扁平存储（向后兼容）
            with self._lock:
                self._items[item_id] = item
                self._stored_count += 1
            return item
        return None

    def retrieve_from_layer(self, item_id: str) -> Optional[MemoryItem]:
        """从分层存储检索记忆"""
        return self._layered_store.access(item_id)

    def review_memory(self, item_id: str) -> bool:
        """
        复习记忆（间隔重复）

        第一性原理：主动复习增强记忆强度，减缓遗忘
        """
        return self._consolidator.review_item(item_id)

    def consolidate_memory(self) -> Dict[str, int]:
        """
        执行记忆巩固

        第一性原理：工作记忆→短期记忆→长期记忆
        """
        return self._consolidator.consolidate()

    def get_layer_items(self, layer: MemoryLayerType) -> List[MemoryItem]:
        """获取指定层的记忆"""
        return self._layered_store.get_layer_items(layer)

    def get_recall_probability(self, item_id: str) -> float:
        """
        获取记忆的回忆概率

        第一性原理：艾宾浩斯遗忘曲线 R = e^(-t/S)
        """
        item = self._layered_store.get(item_id)
        if item is None:
            with self._lock:
                item = self._items.get(item_id)
        if item is None:
            return 0.0
        return item.recall_probability

    def search_by_tag(self, tag: str) -> List[MemoryItem]:
        """按标签搜索记忆"""
        with self._lock:
            return [item for item in self._items.values() if tag in item.tags]

    def search_by_recall(self, min_recall: float = 0.5) -> List[MemoryItem]:
        """按回忆概率搜索记忆"""
        all_items = self._layered_store.get_all_items()
        return [item for item in all_items if item.recall_probability >= min_recall]

    def promote_memory(self, item_id: str, to_layer: MemoryLayerType) -> bool:
        """手动提升记忆层级"""
        return self._layered_store.promote(item_id, to_layer)

    def get_layered_store(self) -> LayeredMemoryStore:
        """获取分层存储"""
        return self._layered_store

    def get_consolidator(self) -> MemoryConsolidator:
        """获取巩固器"""
        return self._consolidator


# ============================================================
# 便捷函数（向后兼容 + 新增）
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


def create_layered_memory_item(
    item_id: str,
    content: Any,
    layer: MemoryLayerType = MemoryLayerType.WORKING,
    information_value: float = 0.5,
    tags: Optional[set] = None,
) -> MemoryItem:
    """创建分层记忆条目"""
    return MemoryItem(
        item_id=item_id,
        content=content,
        information_value=information_value,
        memory_layer=layer,
        tags=tags or set(),
    )
