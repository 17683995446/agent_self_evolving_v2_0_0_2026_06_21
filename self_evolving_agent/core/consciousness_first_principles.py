"""
阶段120: 意识模型强化 — 全局工作空间 + 注意力

第一性原理:
1. 意识是全局广播：进入意识的内容被所有模块访问
2. 意识容量有限：需要竞争进入
3. 意识内容是当前最显著的信息
4. 注意力是选择机制：从大量信息中选择少数进入意识
5. 注意力有方向：自上而下（目标驱动）和自下而上（刺激驱动）
6. 意识有层级：前意识、意识、元意识

强化内容:
- AttentionMechanism: 注意力机制（自上而下/自下而上）
- AttentionSpotlight: 注意力聚光灯（聚焦/扩散）
- GlobalWorkspace: 增强全局工作空间（竞争、广播）
- ConsciousnessLevel: 意识层级
- ConsciousnessState: 意识状态（清醒、困倦、专注等）

向后兼容: 保留原有 WorkspaceContent / ConsciousnessFirstPrinciplesEngine 接口
"""

import threading
import time
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


# ============================================================
# 基础枚举与数据结构（向后兼容）
# ============================================================

class ContentType(Enum):
    """内容类型"""
    PERCEPTION = "perception"
    THOUGHT = "thought"
    MEMORY = "memory"
    EMOTION = "emotion"
    GOAL = "goal"
    ACTION = "action"


@dataclass
class WorkspaceContent:
    """工作空间内容（向后兼容）"""
    content_id: str
    content_type: ContentType
    content: Any
    salience: float = 0.5
    duration_ms: float = 500.0
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 阶段120新增：注意力机制
# ============================================================

class AttentionType(Enum):
    """注意力类型"""
    TOP_DOWN = "top_down"      # 自上而下（目标驱动）
    BOTTOM_UP = "bottom_up"    # 自下而上（刺激驱动）


class AttentionFocus(Enum):
    """注意力聚焦模式"""
    FOCUSED = "focused"    # 聚焦（窄范围高精度）
    DIFFUSE = "diffuse"    # 扩散（宽范围低精度）
    DIVIDED = "divided"    # 分配（多目标）


@dataclass
class AttentionTarget:
    """
    注意力目标

    第一性原理：注意力指向特定的内容，并分配资源
    """
    target_id: str
    content_id: str
    attention_type: AttentionType
    attention_weight: float = 0.5  # 注意力权重 [0, 1]
    focus_mode: AttentionFocus = AttentionFocus.FOCUSED
    timestamp: float = field(default_factory=time.time)


class AttentionMechanism:
    """
    注意力机制

    第一性原理：
    - 注意力是有限资源的分配机制
    - 自上而下：基于目标和期望选择信息
    - 自下而上：基于刺激的显著度选择信息
    - 注意力可以聚焦（高精度窄范围）或扩散（低精度宽范围）
    """

    def __init__(self, total_capacity: float = 1.0):
        self._total_capacity = total_capacity
        self._targets: Dict[str, AttentionTarget] = {}
        self._lock = threading.RLock()
        self._attention_history: List[Dict[str, Any]] = []

    def allocate_attention(
        self,
        content_id: str,
        attention_type: AttentionType,
        weight: float = 0.5,
        focus_mode: AttentionFocus = AttentionFocus.FOCUSED,
    ) -> AttentionTarget:
        """
        分配注意力

        第一性原理：注意力是有限资源，分配给重要内容
        """
        # 防御 NaN/Inf
        try:
            weight = float(weight)
        except (TypeError, ValueError):
            weight = 0.5
        if math.isnan(weight) or math.isinf(weight):
            weight = 0.5
        weight = max(0.0, min(1.0, weight))

        target_id = f"att_{int(time.time() * 1000)}_{len(self._targets)}"

        with self._lock:
            # 检查总容量
            current_total = sum(t.attention_weight for t in self._targets.values())
            available = max(0.0, self._total_capacity - current_total)

            # 如果请求的权重超过可用容量，按比例缩减
            if weight > available and available > 0:
                weight = available
            elif available <= 0:
                # 容量已满，需要释放最低权重的目标
                if self._targets:
                    min_id = min(self._targets, key=lambda k: self._targets[k].attention_weight)
                    if self._targets[min_id].attention_weight < weight:
                        del self._targets[min_id]
                    else:
                        weight = 0.0  # 无法分配

            target = AttentionTarget(
                target_id=target_id,
                content_id=content_id,
                attention_type=attention_type,
                attention_weight=weight,
                focus_mode=focus_mode,
            )
            self._targets[target_id] = target
            self._attention_history.append({
                "action": "allocate",
                "content_id": content_id,
                "weight": weight,
                "type": attention_type.value,
                "timestamp": time.time(),
            })

        return target

    def deallocate_attention(self, target_id: str) -> bool:
        """释放注意力"""
        with self._lock:
            if target_id in self._targets:
                del self._targets[target_id]
                return True
            return False

    def get_attention_for_content(self, content_id: str) -> float:
        """获取内容的总注意力权重"""
        with self._lock:
            total = sum(
                t.attention_weight for t in self._targets.values()
                if t.content_id == content_id
            )
        return total

    def get_total_attention(self) -> float:
        """获取总注意力"""
        with self._lock:
            return sum(t.attention_weight for t in self._targets.values())

    def get_available_capacity(self) -> float:
        """获取可用容量"""
        return max(0.0, self._total_capacity - self.get_total_attention())

    def get_targets(self) -> List[AttentionTarget]:
        """获取所有注意力目标"""
        with self._lock:
            return list(self._targets.values())

    def get_top_targets(self, n: int = 3) -> List[AttentionTarget]:
        """获取注意力最高的n个目标"""
        with self._lock:
            sorted_targets = sorted(
                self._targets.values(),
                key=lambda t: t.attention_weight,
                reverse=True,
            )
            return sorted_targets[:n]

    def shift_attention(
        self,
        from_content_id: str,
        to_content_id: str,
        weight: Optional[float] = None,
    ) -> bool:
        """
        转移注意力

        第一性原理：注意力可以从一个内容转移到另一个
        """
        with self._lock:
            # 找到源内容的注意力
            source_targets = [
                t for t in self._targets.values()
                if t.content_id == from_content_id
            ]
            if not source_targets:
                return False

            # 转移的权重
            if weight is None:
                weight = sum(t.attention_weight for t in source_targets)

            # 释放源注意力
            for t in source_targets:
                del self._targets[t.target_id]

        # 分配到新内容
        self.allocate_attention(
            to_content_id,
            AttentionType.TOP_DOWN,
            weight,
        )
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            top_down_count = sum(1 for t in self._targets.values() if t.attention_type == AttentionType.TOP_DOWN)
            bottom_up_count = sum(1 for t in self._targets.values() if t.attention_type == AttentionType.BOTTOM_UP)
            return {
                "total_capacity": self._total_capacity,
                "used_capacity": self.get_total_attention(),
                "available_capacity": self.get_available_capacity(),
                "target_count": len(self._targets),
                "top_down_count": top_down_count,
                "bottom_up_count": bottom_up_count,
                "history_length": len(self._attention_history),
            }

    def clear(self) -> None:
        """清空"""
        with self._lock:
            self._targets.clear()
            self._attention_history.clear()


# ============================================================
# 阶段120新增：意识层级
# ============================================================

class ConsciousnessLevel(Enum):
    """意识层级"""
    UNCONSCIOUS = 0      # 无意识
    PRE_CONSCIOUS = 1    # 前意识（可被唤起）
    CONSCIOUS = 2        # 意识（当前在工作空间）
    META_CONSCIOUS = 3   # 元意识（意识到自己在意识）


@dataclass
class ConsciousnessState:
    """
    意识状态

    第一性原理：意识有不同的状态和层级
    - level: 意识层级
    - arousal: 唤醒度 [0, 1]
    - awareness: 觉知度 [0, 1]
    - focus: 专注度 [0, 1]
    """
    level: ConsciousnessLevel = ConsciousnessLevel.PRE_CONSCIOUS
    arousal: float = 0.5
    awareness: float = 0.5
    focus: float = 0.5
    timestamp: float = field(default_factory=time.time)

    @property
    def is_conscious(self) -> bool:
        """是否有意识"""
        return self.level.value >= ConsciousnessLevel.CONSCIOUS.value

    @property
    def is_meta_conscious(self) -> bool:
        """是否元意识"""
        return self.level == ConsciousnessLevel.META_CONSCIOUS

    def update_level(self) -> None:
        """根据唤醒度和觉知度更新层级"""
        if self.arousal < 0.2:
            self.level = ConsciousnessLevel.UNCONSCIOUS
        elif self.arousal < 0.4 or self.awareness < 0.3:
            self.level = ConsciousnessLevel.PRE_CONSCIOUS
        elif self.awareness > 0.8 and self.focus > 0.7:
            self.level = ConsciousnessLevel.META_CONSCIOUS
        else:
            self.level = ConsciousnessLevel.CONSCIOUS


# ============================================================
# 意识第一性原理引擎（增强版）
# ============================================================

class ConsciousnessFirstPrinciplesEngine:
    """
    意识第一性原理引擎（阶段120增强版）

    新增能力:
    - 注意力机制（AttentionMechanism）
    - 意识层级（ConsciousnessLevel）
    - 意识状态（ConsciousnessState）
    - 增强全局工作空间（竞争、广播）

    向后兼容: 保留原有 broadcast / get_conscious_contents 接口
    """

    def __init__(self, engine_id: str = "consciousness_engine", capacity: int = 5):
        self.engine_id = engine_id
        self._capacity = capacity
        self._workspace: List[WorkspaceContent] = []
        self._stream: List[WorkspaceContent] = []
        self._lock = threading.RLock()
        self._cycle_count = 0

        # 阶段120新增组件
        self._attention = AttentionMechanism(total_capacity=1.0)
        self._state = ConsciousnessState()

    # ============================================================
    # 原有接口（向后兼容）
    # ============================================================

    def broadcast(self, content: WorkspaceContent) -> bool:
        """广播内容到全局工作空间（向后兼容）"""
        if content is None:
            return False
        # 防御 salience NaN/Inf
        try:
            content.salience = float(content.salience)
        except (TypeError, ValueError):
            content.salience = 0.5
        if math.isnan(content.salience) or math.isinf(content.salience):
            content.salience = 0.5
        content.salience = max(0.0, min(1.0, content.salience))

        with self._lock:
            if len(self._workspace) >= self._capacity:
                if not self._workspace:
                    # 容量为0且工作空间为空，无法广播
                    return False
                self._workspace.sort(key=lambda c: c.salience)
                if self._workspace[0].salience < content.salience:
                    evicted = self._workspace.pop(0)
                    evicted.duration_ms = (time.time() - evicted.timestamp) * 1000
                    self._stream.append(evicted)
                else:
                    return False

            self._workspace.append(content)
            self._workspace.sort(key=lambda c: c.salience, reverse=True)
            self._cycle_count += 1

            # 阶段120新增：自动分配注意力
            self._attention.allocate_attention(
                content.content_id,
                AttentionType.BOTTOM_UP,
                content.salience * 0.5,  # 显著度驱动注意力
            )

            # 更新意识状态
            self._update_consciousness_state()

            return True

    def get_conscious_contents(self) -> List[WorkspaceContent]:
        """获取当前意识内容（向后兼容）"""
        with self._lock:
            return list(self._workspace)

    def get_dominant_content(self) -> Optional[WorkspaceContent]:
        """获取主导意识内容（向后兼容）"""
        with self._lock:
            if self._workspace:
                return max(self._workspace, key=lambda c: c.salience)
            return None

    def is_in_consciousness(self, content_id: str) -> bool:
        """检查内容是否在意识中（向后兼容）"""
        with self._lock:
            return any(c.content_id == content_id for c in self._workspace)

    def update_salience(self, content_id: str, new_salience: float) -> bool:
        """更新内容显著度（向后兼容）"""
        try:
            new_salience = float(new_salience)
        except (TypeError, ValueError):
            return False
        if math.isnan(new_salience) or math.isinf(new_salience):
            return False
        new_salience = max(0.0, min(1.0, new_salience))

        with self._lock:
            for content in self._workspace:
                if content.content_id == content_id:
                    content.salience = new_salience
                    self._workspace.sort(key=lambda c: c.salience, reverse=True)
                    return True
        return False

    def clear_workspace(self) -> None:
        """清空工作空间（向后兼容）"""
        with self._lock:
            for content in self._workspace:
                content.duration_ms = (time.time() - content.timestamp) * 1000
                self._stream.append(content)
            self._workspace.clear()
            self._attention.clear()

    def get_stream(self, limit: int = 100) -> List[WorkspaceContent]:
        """获取意识流历史（向后兼容）"""
        with self._lock:
            return self._stream[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            dominant = self.get_dominant_content()
            base_stats = {
                "engine_id": self.engine_id,
                "workspace_size": len(self._workspace),
                "capacity": self._capacity,
                "stream_length": len(self._stream),
                "cycle_count": self._cycle_count,
                "dominant_content": dominant.content_id if dominant else None,
                "consciousness_utilization": len(self._workspace) / self._capacity if self._capacity > 0 else 0,
            }
            # 阶段120新增统计
            base_stats["attention_stats"] = self._attention.get_stats()
            base_stats["consciousness_level"] = self._state.level.value
            base_stats["consciousness_state"] = {
                "arousal": self._state.arousal,
                "awareness": self._state.awareness,
                "focus": self._state.focus,
                "is_conscious": self._state.is_conscious,
                "is_meta_conscious": self._state.is_meta_conscious,
            }
            return base_stats

    def reset(self) -> None:
        """重置"""
        with self._lock:
            self._workspace.clear()
            self._stream.clear()
            self._cycle_count = 0
            self._attention.clear()
            self._state = ConsciousnessState()

    # ============================================================
    # 阶段120新增：注意力接口
    # ============================================================

    def focus_attention(
        self,
        content_id: str,
        weight: float = 0.5,
        attention_type: AttentionType = AttentionType.TOP_DOWN,
        focus_mode: AttentionFocus = AttentionFocus.FOCUSED,
    ) -> AttentionTarget:
        """
        聚焦注意力

        第一性原理：自上而下的注意力基于目标选择信息
        """
        target = self._attention.allocate_attention(
            content_id, attention_type, weight, focus_mode,
        )
        # 更新意识状态
        self._update_consciousness_state()
        return target

    def release_attention(self, target_id: str) -> bool:
        """释放注意力"""
        result = self._attention.deallocate_attention(target_id)
        self._update_consciousness_state()
        return result

    def shift_attention(
        self,
        from_content_id: str,
        to_content_id: str,
        weight: Optional[float] = None,
    ) -> bool:
        """
        转移注意力

        第一性原理：注意力可以从一个内容转移到另一个
        """
        result = self._attention.shift_attention(from_content_id, to_content_id, weight)
        self._update_consciousness_state()
        return result

    def get_attention_targets(self) -> List[AttentionTarget]:
        """获取注意力目标"""
        return self._attention.get_targets()

    def get_top_attention_targets(self, n: int = 3) -> List[AttentionTarget]:
        """获取注意力最高的n个目标"""
        return self._attention.get_top_targets(n)

    def get_attention_for_content(self, content_id: str) -> float:
        """获取内容的注意力权重"""
        return self._attention.get_attention_for_content(content_id)

    # ============================================================
    # 阶段120新增：意识状态接口
    # ============================================================

    def update_consciousness_state(
        self,
        arousal: Optional[float] = None,
        awareness: Optional[float] = None,
        focus: Optional[float] = None,
    ) -> None:
        """更新意识状态"""
        with self._lock:
            if arousal is not None:
                try:
                    arousal = float(arousal)
                    if not (math.isnan(arousal) or math.isinf(arousal)):
                        self._state.arousal = max(0.0, min(1.0, arousal))
                except (TypeError, ValueError):
                    pass
            if awareness is not None:
                try:
                    awareness = float(awareness)
                    if not (math.isnan(awareness) or math.isinf(awareness)):
                        self._state.awareness = max(0.0, min(1.0, awareness))
                except (TypeError, ValueError):
                    pass
            if focus is not None:
                try:
                    focus = float(focus)
                    if not (math.isnan(focus) or math.isinf(focus)):
                        self._state.focus = max(0.0, min(1.0, focus))
                except (TypeError, ValueError):
                    pass
            self._state.update_level()
            self._state.timestamp = time.time()

    def _update_consciousness_state(self) -> None:
        """根据工作空间内容更新意识状态"""
        with self._lock:
            # 唤醒度基于工作空间使用率
            utilization = len(self._workspace) / self._capacity if self._capacity > 0 else 0
            self._state.arousal = max(self._state.arousal, utilization)

            # 觉知度基于注意力集中度
            attention_stats = self._attention.get_stats()
            if attention_stats["target_count"] > 0:
                top_targets = self._attention.get_top_targets(1)
                if top_targets:
                    self._state.awareness = max(self._state.awareness, top_targets[0].attention_weight)

            # 专注度基于最高注意力权重
            if attention_stats["target_count"] > 0:
                top_targets = self._attention.get_top_targets(1)
                if top_targets:
                    self._state.focus = max(self._state.focus, top_targets[0].attention_weight)

            self._state.update_level()

    def get_consciousness_level(self) -> ConsciousnessLevel:
        """获取意识层级"""
        with self._lock:
            return self._state.level

    def get_consciousness_state(self) -> ConsciousnessState:
        """获取意识状态"""
        with self._lock:
            return self._state

    def is_conscious(self) -> bool:
        """是否有意识"""
        with self._lock:
            return self._state.is_conscious

    def is_meta_conscious(self) -> bool:
        """是否元意识"""
        with self._lock:
            return self._state.is_meta_conscious

    def get_attention_mechanism(self) -> AttentionMechanism:
        """获取注意力机制"""
        return self._attention


# ============================================================
# 便捷函数（向后兼容 + 新增）
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


def create_attention_target(
    content_id: str,
    attention_type: AttentionType = AttentionType.TOP_DOWN,
    weight: float = 0.5,
    focus_mode: AttentionFocus = AttentionFocus.FOCUSED,
) -> AttentionTarget:
    """创建注意力目标"""
    return AttentionTarget(
        target_id=f"att_{int(time.time() * 1000)}",
        content_id=content_id,
        attention_type=attention_type,
        attention_weight=weight,
        focus_mode=focus_mode,
    )
