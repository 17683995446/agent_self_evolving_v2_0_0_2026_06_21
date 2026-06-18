"""
阶段83: 情感第一性原理化

第一性原理:
1. 情感是信息价值的快速评估：无需理性分析即可判断重要性
2. 情感驱动注意力分配：重要信息优先处理
3. 情感状态影响决策倾向

设计原则:
- EmotionState: 情感状态
- EmotionalSignal: 情感信号
- EmotionFirstPrinciplesEngine: 情感引擎
- 情感作为信息价值的快速标记
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class EmotionType(Enum):
    """情感类型"""
    INTEREST = "interest"          # 兴趣（高信息价值）
    CONFUSION = "confusion"        # 困惑（预测失败）
    SATISFACTION = "satisfaction"  # 满足（预测成功）
    CONCERN = "concern"            # 担忧（潜在威胁）
    SURPRISE = "surprise"          # 惊奇（意外信息）
    BOREDOM = "boredom"            # 无聊（低信息价值）


@dataclass
class EmotionState:
    """情感状态"""
    state_id: str
    emotions: Dict[EmotionType, float] = field(default_factory=dict)  # 各情感强度 [0,1]
    dominant_emotion: Optional[EmotionType] = None
    valence: float = 0.0              # 效价 [-1, 1]，正=愉悦，负=不悦
    arousal: float = 0.0              # 唤醒度 [0, 1]
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.emotions:
            self.emotions = {et: 0.0 for et in EmotionType}
        self._update_dominant()

    def _update_dominant(self) -> None:
        if self.emotions:
            self.dominant_emotion = max(self.emotions, key=lambda k: self.emotions[k])
            max_val = self.emotions[self.dominant_emotion]
            if max_val < 0.1:
                self.dominant_emotion = None


@dataclass
class EmotionalSignal:
    """情感信号"""
    signal_id: str
    emotion_type: EmotionType
    intensity: float = 0.5            # 强度 [0,1]
    trigger: str = "unknown"          # 触发源
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 情感第一性原理引擎
# ============================================================

class EmotionFirstPrinciplesEngine:
    """
    情感第一性原理引擎

    核心原则：情感是信息价值的快速评估信号

    第一性原理推导:
    1. 系统持续接收信息
    2. 信息有价值高低之分
    3. 理性评估太慢，需要快速标记
    4. 情感 = 快速价值标记
    5. 情感强度 ∝ 信息价值 / 预期差异
    """

    def __init__(self, engine_id: str = "emotion_engine"):
        self.engine_id = engine_id
        self._state = EmotionState(state_id="current")
        self._signals: List[EmotionalSignal] = []
        self._lock = threading.RLock()
        self._cycle_count = 0

    def process_event(
        self,
        event_type: str,
        prediction_error: float = 0.0,
        information_value: float = 0.5,
        outcome: Optional[str] = None,
    ) -> EmotionState:
        """
        处理事件，更新情感状态

        第一性原理：情感是对事件的快速价值评估
        """
        # 根据事件特征推断情感
        emotion_changes: Dict[EmotionType, float] = {}

        # 阶段104修复：钳制输入到 [0,1]，防止负值产生负情感强度
        prediction_error = max(0.0, min(1.0, prediction_error or 0.0))
        information_value = max(0.0, min(1.0, information_value or 0.0))

        if prediction_error > 0.5:
            emotion_changes[EmotionType.SURPRISE] = min(1.0, prediction_error)
            emotion_changes[EmotionType.CONFUSION] = min(1.0, prediction_error * 0.7)

        if information_value > 0.7:
            emotion_changes[EmotionType.INTEREST] = min(1.0, information_value)
        elif information_value < 0.2:
            emotion_changes[EmotionType.BOREDOM] = min(1.0, 1.0 - information_value)

        if outcome == "success":
            emotion_changes[EmotionType.SATISFACTION] = 0.8
        elif outcome == "failure":
            emotion_changes[EmotionType.CONCERN] = 0.7

        with self._lock:
            for emotion, delta in emotion_changes.items():
                current = self._state.emotions.get(emotion, 0.0)
                # 阶段104修复：钳制到 [0, 1]，防止负值
                self._state.emotions[emotion] = max(0.0, min(1.0, current + delta))

            # 衰减其他情感
            for emotion in self._state.emotions:
                if emotion not in emotion_changes:
                    self._state.emotions[emotion] = max(0.0, self._state.emotions[emotion] * 0.9)

            self._state._update_dominant()
            self._state.timestamp = time.time()

            # 计算效价和唤醒度
            positive = self._state.emotions.get(EmotionType.SATISFACTION, 0.0) + self._state.emotions.get(EmotionType.INTEREST, 0.0)
            negative = self._state.emotions.get(EmotionType.CONCERN, 0.0) + self._state.emotions.get(EmotionType.CONFUSION, 0.0)
            self._state.valence = positive - negative
            self._state.arousal = max(self._state.emotions.values()) if self._state.emotions else 0.0

            self._cycle_count += 1

        return self._state

    def get_attention_bias(self) -> Dict[str, float]:
        """
        获取注意力偏向

        第一性原理：情感决定注意力分配
        """
        with self._lock:
            state = self._state

        bias = {
            "novelty_seeking": state.emotions.get(EmotionType.INTEREST, 0.0) + state.emotions.get(EmotionType.SURPRISE, 0.0),
            "risk_aversion": state.emotions.get(EmotionType.CONCERN, 0.0),
            "exploration": state.emotions.get(EmotionType.INTEREST, 0.0) * (1.0 - state.emotions.get(EmotionType.BOREDOM, 0.0)),
            "persistence": state.emotions.get(EmotionType.SATISFACTION, 0.0),
        }

        return bias

    def should_attend(self, information_value: float) -> bool:
        """
        是否应该关注

        第一性原理：情感状态调节注意力阈值
        """
        with self._lock:
            boredom = self._state.emotions.get(EmotionType.BOREDOM, 0.0)
            interest = self._state.emotions.get(EmotionType.INTEREST, 0.0)

        # 无聊时降低阈值，兴趣高时也降低阈值
        threshold = 0.5 - boredom * 0.3 - interest * 0.2
        threshold = max(0.1, min(0.8, threshold))

        return information_value >= threshold

    def get_recommended_mood(self) -> str:
        """获取推荐心境"""
        with self._lock:
            state = self._state

        if state.valence > 0.3 and state.arousal > 0.5:
            return "excited"
        elif state.valence > 0.3:
            return "content"
        elif state.valence < -0.3 and state.arousal > 0.5:
            return "anxious"
        elif state.valence < -0.3:
            return "sad"
        elif state.arousal > 0.5:
            return "alert"
        return "neutral"

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "engine_id": self.engine_id,
                "cycle_count": self._cycle_count,
                "dominant_emotion": self._state.dominant_emotion.value if self._state.dominant_emotion else None,
                "valence": self._state.valence,
                "arousal": self._state.arousal,
                "attention_bias": self.get_attention_bias(),
                "recommended_mood": self.get_recommended_mood(),
            }

    def reset(self) -> None:
        """重置"""
        with self._lock:
            self._state = EmotionState(state_id="current")
            self._signals.clear()
            self._cycle_count = 0


# ============================================================
# 便捷函数
# ============================================================

def create_emotion_engine(engine_id: str = "emotion_engine") -> EmotionFirstPrinciplesEngine:
    """创建情感引擎"""
    return EmotionFirstPrinciplesEngine(engine_id=engine_id)
