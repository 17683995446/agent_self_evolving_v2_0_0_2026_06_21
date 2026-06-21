"""
阶段116: 学习算法强化 — 在线学习 + 经验回放

第一性原理:
1. 减小预测误差是学习的唯一动力：没有误差就没有学习
2. 学习是参数空间的梯度下降：沿误差减小的方向更新
3. 所有参数更新必须可追溯到误差信号
4. 经验是宝贵的：过去的经验应被复用以强化学习
5. 学习率应自适应：误差稳定下降时增大，震荡时减小

强化内容:
- Experience: 经验元组（状态、动作、奖励、下一状态）
- ExperienceReplayBuffer: 经验回放缓冲区
  - 存储经验、随机采样、优先级回放
- OnlineLearner: 在线学习器
  - 自适应学习率、动量加速、梯度裁剪
- LearningRateScheduler: 学习率调度器
  - 预热、衰减、循环、自适应
- EnhancedLearningEngine: 整合以上能力

向后兼容: 保留原有 LearningFirstPrinciplesEngine 接口
"""

import threading
import time
import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
from collections import deque


# ============================================================
# 基础枚举与数据结构（向后兼容）
# ============================================================

class UpdateType(Enum):
    """更新类型"""
    GRADIENT_DESCENT = "gradient_descent"
    ERROR_CORRECTION = "error_correction"
    PREDICTION_UPDATE = "prediction_update"
    HEURISTIC = "heuristic"


class LRScheduleType(Enum):
    """学习率调度类型"""
    CONSTANT = "constant"      # 恒定
    DECAY = "decay"            # 指数衰减
    WARMUP = "warmup"          # 预热
    CYCLICAL = "cyclical"      # 循环
    ADAPTIVE = "adaptive"      # 自适应（基于误差趋势）


@dataclass
class LearningSignal:
    """学习信号（向后兼容）"""
    signal_id: str
    error_magnitude: float = 0.0
    error_source: str = "unknown"
    precision: float = 1.0
    timestamp: float = field(default_factory=time.time)

    @property
    def is_valid(self) -> bool:
        return self.error_magnitude > 0.0


@dataclass
class ParameterUpdate:
    """参数更新（向后兼容）"""
    update_id: str
    parameter_name: str
    delta: float = 0.0
    learning_rate: float = 0.01
    signal_id: str = ""
    update_type: UpdateType = UpdateType.GRADIENT_DESCENT
    timestamp: float = field(default_factory=time.time)

    @property
    def update_magnitude(self) -> float:
        return abs(self.delta)


# ============================================================
# 阶段116新增：经验
# ============================================================

@dataclass
class Experience:
    """
    经验元组

    第一性原理：
    - 经验是学习的原材料
    - 每条经验记录：状态、动作、奖励、下一状态
    - 奖励信号驱动强化学习
    - TD误差 = 实际奖励 - 预期奖励
    """
    experience_id: str
    state: Dict[str, float]
    action: str
    reward: float
    next_state: Dict[str, float]
    timestamp: float = field(default_factory=time.time)
    # 优先级回放相关
    td_error: float = 0.0       # TD误差（用于优先级）
    priority: float = 1.0       # 采样优先级
    visit_count: int = 0        # 被采样次数
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def importance(self) -> float:
        """重要性 = |TD误差| + ε（防止零优先级）"""
        return abs(self.td_error) + 0.01


# ============================================================
# 阶段116新增：经验回放缓冲区
# ============================================================

class ExperienceReplayBuffer:
    """
    经验回放缓冲区

    第一性原理：
    - 经验是宝贵的，应被复用
    - 随机采样打破时间相关性
    - 优先级回放：高TD误差的经验更重要
    - 缓冲区有容量上限，旧经验被淘汰

    支持两种采样模式：
    1. 均匀随机采样
    2. 优先级回放（基于TD误差）
    """

    def __init__(self, capacity: int = 10000, seed: Optional[int] = None):
        self._buffer: deque = deque(maxlen=capacity)
        self._index: Dict[str, int] = {}  # experience_id -> buffer index
        self._lock = threading.RLock()
        self._capacity = capacity
        self._rng = random.Random(seed) if seed is not None else random.Random()
        # 优先级回放参数
        self._alpha = 0.6  # 优先级强度（0=均匀，1=完全优先级）
        self._beta = 0.4   # 重要性采样补偿（0=不补偿，1=完全补偿）

    def add(self, experience: Experience) -> bool:
        """添加经验"""
        with self._lock:
            if experience.experience_id in self._index:
                return False  # 已存在
            self._buffer.append(experience)
            self._index[experience.experience_id] = len(self._buffer) - 1
            # 重建索引（deque可能淘汰了旧元素）
            self._rebuild_index()
            return True

    def _rebuild_index(self) -> None:
        """重建索引"""
        self._index.clear()
        for i, exp in enumerate(self._buffer):
            self._index[exp.experience_id] = i

    def sample(self, batch_size: int = 32, prioritized: bool = False) -> List[Experience]:
        """
        采样经验

        第一性原理：
        - 均匀采样：每条经验等概率被选中
        - 优先级采样：高TD误差的经验更可能被选中
        """
        with self._lock:
            if not self._buffer:
                return []
            n = min(batch_size, len(self._buffer))
            if prioritized:
                return self._priority_sample(n)
            else:
                return self._uniform_sample(n)

    def _uniform_sample(self, n: int) -> List[Experience]:
        """均匀随机采样"""
        buffer_list = list(self._buffer)
        sampled = self._rng.sample(buffer_list, n)
        for exp in sampled:
            exp.visit_count += 1
        return sampled

    def _priority_sample(self, n: int) -> List[Experience]:
        """优先级采样"""
        buffer_list = list(self._buffer)
        # 计算采样概率
        priorities = [exp.importance ** self._alpha for exp in buffer_list]
        total = sum(priorities)
        if total <= 0:
            return self._uniform_sample(n)
        probs = [p / total for p in priorities]
        # 加权随机采样
        indices = self._rng.choices(range(len(buffer_list)), weights=probs, k=n)
        sampled = [buffer_list[i] for i in indices]
        for exp in sampled:
            exp.visit_count += 1
        return sampled

    def update_priorities(self, updates: Dict[str, float]) -> None:
        """
        更新经验优先级

        Args:
            updates: {experience_id: new_td_error}
        """
        with self._lock:
            for exp_id, td_error in updates.items():
                idx = self._index.get(exp_id)
                if idx is not None and idx < len(self._buffer):
                    self._buffer[idx].td_error = td_error
                    self._buffer[idx].priority = abs(td_error) + 0.01

    def get_experience(self, experience_id: str) -> Optional[Experience]:
        """获取特定经验"""
        with self._lock:
            idx = self._index.get(experience_id)
            if idx is not None and idx < len(self._buffer):
                return self._buffer[idx]
            return None

    def remove(self, experience_id: str) -> bool:
        """移除经验"""
        with self._lock:
            idx = self._index.get(experience_id)
            if idx is None:
                return False
            del self._buffer[idx]
            self._rebuild_index()
            return True

    def clear(self) -> None:
        """清空缓冲区"""
        with self._lock:
            self._buffer.clear()
            self._index.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)

    @property
    def capacity(self) -> int:
        return self._capacity

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            if not self._buffer:
                return {
                    "size": 0,
                    "capacity": self._capacity,
                    "avg_td_error": 0.0,
                    "avg_visit_count": 0.0,
                    "alpha": self._alpha,
                    "beta": self._beta,
                }
            avg_td = sum(e.td_error for e in self._buffer) / len(self._buffer)
            avg_visit = sum(e.visit_count for e in self._buffer) / len(self._buffer)
            return {
                "size": len(self._buffer),
                "capacity": self._capacity,
                "avg_td_error": avg_td,
                "avg_visit_count": avg_visit,
                "alpha": self._alpha,
                "beta": self._beta,
            }

    def set_priority_params(self, alpha: float, beta: float) -> None:
        """设置优先级参数"""
        with self._lock:
            self._alpha = max(0.0, min(1.0, alpha))
            self._beta = max(0.0, min(1.0, beta))


# ============================================================
# 阶段116新增：学习率调度器
# ============================================================

class LearningRateScheduler:
    """
    学习率调度器

    第一性原理：
    - 学习率控制参数更新步长
    - 太大：震荡不收敛
    - 太小：收敛太慢
    - 自适应：根据误差趋势动态调整

    支持的调度策略：
    1. CONSTANT: 恒定学习率
    2. DECAY: 指数衰减 lr = base_lr × decay^step
    3. WARMUP: 预热 lr = base_lr × min(1.0, step/warmup_steps)
    4. CYCLICAL: 循环 lr 在 [min_lr, max_lr] 间三角波振荡
    5. ADAPTIVE: 自适应 根据误差趋势调整
    """

    def __init__(
        self,
        base_lr: float = 0.01,
        schedule_type: LRScheduleType = LRScheduleType.CONSTANT,
        decay_rate: float = 0.99,
        warmup_steps: int = 100,
        min_lr: float = 0.0001,
        max_lr: float = 0.1,
        cycle_steps: int = 1000,
    ):
        self._base_lr = max(1e-6, base_lr)
        self._schedule_type = schedule_type
        self._decay_rate = max(0.0, min(1.0, decay_rate))
        self._warmup_steps = max(1, warmup_steps)
        self._min_lr = max(1e-6, min_lr)
        self._max_lr = max(self._min_lr, max_lr)
        self._cycle_steps = max(1, cycle_steps)
        self._step_count = 0
        self._lock = threading.RLock()
        # 自适应参数
        self._error_history: deque = deque(maxlen=100)
        self._adaptive_factor = 1.0

    def step(self, error: Optional[float] = None) -> float:
        """
        前进一步，返回当前学习率

        Args:
            error: 当前误差（自适应模式需要）
        """
        with self._lock:
            self._step_count += 1
            if error is not None:
                self._error_history.append(error)
                if self._schedule_type == LRScheduleType.ADAPTIVE:
                    self._update_adaptive_factor()

            return self.get_lr()

    def get_lr(self) -> float:
        """获取当前学习率"""
        with self._lock:
            if self._schedule_type == LRScheduleType.CONSTANT:
                return self._base_lr
            elif self._schedule_type == LRScheduleType.DECAY:
                return self._base_lr * (self._decay_rate ** self._step_count)
            elif self._schedule_type == LRScheduleType.WARMUP:
                factor = min(1.0, self._step_count / self._warmup_steps)
                return self._base_lr * factor
            elif self._schedule_type == LRScheduleType.CYCLICAL:
                cycle = (self._step_count % self._cycle_steps) / self._cycle_steps
                # 三角波
                if cycle < 0.5:
                    factor = cycle * 2  # 0→1
                else:
                    factor = 2 - cycle * 2  # 1→0
                return self._min_lr + (self._max_lr - self._min_lr) * factor
            elif self._schedule_type == LRScheduleType.ADAPTIVE:
                return self._base_lr * self._adaptive_factor
            return self._base_lr

    def _update_adaptive_factor(self) -> None:
        """
        更新自适应因子

        第一性原理：
        - 误差持续下降 → 增大学习率（方向正确，加速）
        - 误差震荡 → 减小学习率（可能步长太大）
        - 误差停滞 → 微增学习率（跳出局部最优）
        """
        if len(self._error_history) < 10:
            return
        recent = list(self._error_history)
        # 比较前半段和后半段的均值
        mid = len(recent) // 2
        early_avg = sum(recent[:mid]) / max(1, mid)
        late_avg = sum(recent[mid:]) / max(1, len(recent) - mid)

        if early_avg <= 0:
            return

        trend = (early_avg - late_avg) / early_avg  # 正=下降，负=上升

        # 计算震荡度（标准差）
        mean = sum(recent) / len(recent)
        variance = sum((x - mean) ** 2 for x in recent) / len(recent)
        std = math.sqrt(max(0.0, variance))
        oscillation = std / max(0.01, mean) if mean > 0 else 0.0

        if trend > 0.05 and oscillation < 0.3:
            # 误差下降且稳定 → 增大学习率
            self._adaptive_factor = min(2.0, self._adaptive_factor * 1.05)
        elif oscillation > 0.5:
            # 震荡严重 → 减小学习率
            self._adaptive_factor = max(0.1, self._adaptive_factor * 0.9)
        elif abs(trend) < 0.02:
            # 停滞 → 微增
            self._adaptive_factor = min(2.0, self._adaptive_factor * 1.01)

    def reset(self) -> None:
        """重置调度器"""
        with self._lock:
            self._step_count = 0
            self._error_history.clear()
            self._adaptive_factor = 1.0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "base_lr": self._base_lr,
                "current_lr": self.get_lr(),
                "schedule_type": self._schedule_type.value,
                "step_count": self._step_count,
                "adaptive_factor": self._adaptive_factor,
                "error_history_size": len(self._error_history),
            }


# ============================================================
# 阶段116新增：在线学习器
# ============================================================

class OnlineLearner:
    """
    在线学习器

    第一性原理：
    - 在线学习：数据流式到达，逐个处理
    - 动量：累积梯度方向，加速收敛
    - 梯度裁剪：防止梯度爆炸
    - 自适应学习率：根据误差趋势调整

    动量更新公式:
    v_t = momentum × v_{t-1} + lr × gradient
    param_t = param_{t-1} - v_t
    """

    def __init__(
        self,
        momentum: float = 0.9,
        max_gradient: float = 10.0,
        scheduler: Optional[LearningRateScheduler] = None,
    ):
        self._momentum = max(0.0, min(0.99, momentum))
        self._max_gradient = max(0.01, max_gradient)
        self._scheduler = scheduler or LearningRateScheduler()
        # 参数及其动量
        self._params: Dict[str, float] = {}
        self._velocities: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._update_count = 0

    def set_parameter(self, name: str, value: float) -> None:
        """设置参数初始值"""
        with self._lock:
            self._params[name] = value
            self._velocities.setdefault(name, 0.0)

    def get_parameter(self, name: str) -> float:
        """获取参数值"""
        with self._lock:
            return self._params.get(name, 0.0)

    def update(
        self,
        parameter_name: str,
        gradient: float,
        error: Optional[float] = None,
    ) -> float:
        """
        在线参数更新（带动量和梯度裁剪）

        第一性原理：
        1. 梯度裁剪：防止梯度爆炸
        2. 动量累积：加速一致方向的更新
        3. 学习率调度：自适应步长

        Returns: 参数更新量
        """
        with self._lock:
            # 防御 NaN/Inf（在裁剪之前检查，因为 min/max 与 NaN 的行为不确定）
            if math.isnan(gradient) or math.isinf(gradient):
                return 0.0

            # 梯度裁剪
            clipped_grad = max(-self._max_gradient, min(self._max_gradient, gradient))

            # 获取学习率
            lr = self._scheduler.step(error)

            # 动量更新
            old_velocity = self._velocities.get(parameter_name, 0.0)
            new_velocity = self._momentum * old_velocity + lr * clipped_grad
            self._velocities[parameter_name] = new_velocity

            # 参数更新
            old_param = self._params.get(parameter_name, 0.0)
            new_param = old_param - new_velocity
            self._params[parameter_name] = new_param

            self._update_count += 1
            return new_velocity  # 返回更新量

    def batch_update(
        self,
        gradients: Dict[str, float],
        error: Optional[float] = None,
    ) -> Dict[str, float]:
        """批量更新"""
        results: Dict[str, float] = {}
        with self._lock:
            for name, grad in gradients.items():
                results[name] = self.update(name, grad, error)
        return results

    def reset_momentum(self) -> None:
        """重置动量"""
        with self._lock:
            for name in self._velocities:
                self._velocities[name] = 0.0

    def get_all_parameters(self) -> Dict[str, float]:
        """获取所有参数"""
        with self._lock:
            return dict(self._params)

    def get_scheduler(self) -> LearningRateScheduler:
        """获取调度器"""
        return self._scheduler

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "update_count": self._update_count,
                "parameter_count": len(self._params),
                "momentum": self._momentum,
                "max_gradient": self._max_gradient,
                "scheduler_stats": self._scheduler.get_stats(),
            }


# ============================================================
# 增强学习引擎（向后兼容 + 新能力）
# ============================================================

class LearningFirstPrinciplesEngine:
    """
    学习第一性原理引擎（阶段116增强版）

    新增能力:
    - 经验回放缓冲区（ExperienceReplayBuffer）
    - 在线学习器（OnlineLearner）带动量和梯度裁剪
    - 学习率调度器（LearningRateScheduler）
    - 经验回放学习

    向后兼容: 保留原有 create_signal / propose_update / learn_from_error 接口
    """

    def __init__(self, engine_id: str = "learning_engine"):
        self.engine_id = engine_id
        self._signals: Dict[str, LearningSignal] = {}
        self._updates: Dict[str, ParameterUpdate] = {}
        self._parameters: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._cycle_count = 0
        self._rejected_updates = 0

        # 阶段116新增能力
        self._replay_buffer = ExperienceReplayBuffer()
        self._online_learner = OnlineLearner()
        self._scheduler = self._online_learner.get_scheduler()

    # ============================================================
    # 原有接口（向后兼容）
    # ============================================================

    def create_signal(
        self,
        error_magnitude: float,
        error_source: str = "unknown",
        precision: float = 1.0,
    ) -> Optional[LearningSignal]:
        """创建学习信号（向后兼容）"""
        if error_magnitude <= 0.0:
            return None

        signal = LearningSignal(
            signal_id=f"sig_{int(time.time() * 1000)}_{self._cycle_count}",
            error_magnitude=error_magnitude,
            error_source=error_source,
            precision=max(0.0, min(1.0, precision)),
        )

        with self._lock:
            self._signals[signal.signal_id] = signal

        return signal

    def propose_update(
        self,
        parameter_name: str,
        delta: float,
        signal_id: str,
        learning_rate: float = 0.01,
        update_type: UpdateType = UpdateType.GRADIENT_DESCENT,
    ) -> Optional[ParameterUpdate]:
        """提议参数更新（向后兼容）"""
        with self._lock:
            signal = self._signals.get(signal_id)

        if signal is None or not signal.is_valid:
            with self._lock:
                self._rejected_updates += 1
            return None

        update = ParameterUpdate(
            update_id=f"upd_{int(time.time() * 1000)}_{self._cycle_count}",
            parameter_name=parameter_name,
            delta=delta * signal.precision * learning_rate,
            learning_rate=learning_rate,
            signal_id=signal_id,
            update_type=update_type,
        )

        with self._lock:
            self._updates[update.update_id] = update
            self._cycle_count += 1

        return update

    def apply_update(self, update: ParameterUpdate) -> bool:
        """应用参数更新（向后兼容）"""
        with self._lock:
            current = self._parameters.get(update.parameter_name, 0.0)
            self._parameters[update.parameter_name] = current + update.delta
            # 同步到在线学习器
            self._online_learner.set_parameter(update.parameter_name, self._parameters[update.parameter_name])
            return True

    def learn_from_error(
        self,
        parameter_name: str,
        error_magnitude: float,
        delta: float,
        error_source: str = "unknown",
        learning_rate: float = 0.01,
    ) -> Optional[ParameterUpdate]:
        """从误差学习（向后兼容）"""
        signal = self.create_signal(error_magnitude, error_source)
        if signal is None:
            return None

        update = self.propose_update(
            parameter_name=parameter_name,
            delta=delta,
            signal_id=signal.signal_id,
            learning_rate=learning_rate,
        )

        if update:
            self.apply_update(update)

        return update

    def get_parameter(self, name: str) -> float:
        """获取参数值（向后兼容）"""
        with self._lock:
            return self._parameters.get(name, 0.0)

    def set_parameter(self, name: str, value: float) -> None:
        """直接设置参数（向后兼容）"""
        with self._lock:
            self._parameters[name] = value
            self._online_learner.set_parameter(name, value)

    def trace_update_to_error(self, update_id: str) -> Optional[LearningSignal]:
        """追溯更新到误差信号（向后兼容）"""
        with self._lock:
            update = self._updates.get(update_id)
            if update is None:
                return None
            return self._signals.get(update.signal_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "engine_id": self.engine_id,
                "signals_count": len(self._signals),
                "updates_count": len(self._updates),
                "parameters_count": len(self._parameters),
                "cycle_count": self._cycle_count,
                "rejected_updates": self._rejected_updates,
                "total_error_processed": sum(s.error_magnitude for s in self._signals.values()),
                # 阶段116新增统计
                "replay_buffer_stats": self._replay_buffer.get_stats(),
                "online_learner_stats": self._online_learner.get_stats(),
            }

    def clear_history(self) -> None:
        """清除历史（向后兼容）"""
        with self._lock:
            self._signals.clear()
            self._updates.clear()
            self._rejected_updates = 0

    # ============================================================
    # 阶段116新增：经验回放接口
    # ============================================================

    def add_experience(
        self,
        state: Dict[str, float],
        action: str,
        reward: float,
        next_state: Dict[str, float],
        td_error: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Experience]:
        """
        添加经验到回放缓冲区

        第一性原理：经验是学习的原材料
        """
        exp = Experience(
            experience_id=f"exp_{int(time.time() * 1000000)}_{self._cycle_count}",
            state=dict(state),
            action=action,
            reward=reward,
            next_state=dict(next_state),
            td_error=td_error,
            priority=abs(td_error) + 0.01,
            metadata=metadata or {},
        )
        if self._replay_buffer.add(exp):
            return exp
        return None

    def sample_experiences(self, batch_size: int = 32, prioritized: bool = False) -> List[Experience]:
        """从回放缓冲区采样经验"""
        return self._replay_buffer.sample(batch_size, prioritized)

    def update_experience_priorities(self, updates: Dict[str, float]) -> None:
        """更新经验优先级"""
        self._replay_buffer.update_priorities(updates)

    def replay_learn(
        self,
        batch_size: int = 32,
        prioritized: bool = True,
        learning_fn: Optional[Callable[[Experience], Tuple[str, float, float]]] = None,
    ) -> List[ParameterUpdate]:
        """
        经验回放学习

        第一性原理：复用过去经验强化学习

        Args:
            batch_size: 采样批量
            prioritized: 是否使用优先级回放
            learning_fn: 学习函数 (experience) -> (parameter_name, gradient, error)
                        如果为None，使用默认学习逻辑

        Returns: 应用的参数更新列表
        """
        experiences = self.sample_experiences(batch_size, prioritized)
        if not experiences:
            return []

        updates: List[ParameterUpdate] = []
        priority_updates: Dict[str, float] = {}

        for exp in experiences:
            if learning_fn is not None:
                param_name, gradient, error = learning_fn(exp)
            else:
                # 默认学习逻辑：用奖励信号更新参数
                param_name = f"param_{exp.action}"
                # 梯度 = -reward（奖励为正时减小参数，增大预期）
                # 实际上应该根据具体任务定义，这里用简单启发式
                gradient = -exp.reward * 0.1
                error = abs(exp.td_error) if exp.td_error != 0 else 0.01

            # 使用在线学习器更新
            update_delta = self._online_learner.update(param_name, gradient, error)

            if abs(update_delta) > 0:
                # 创建更新记录
                signal = self.create_signal(error, f"replay_{exp.experience_id}")
                if signal is not None:
                    update = ParameterUpdate(
                        update_id=f"upd_replay_{int(time.time() * 1000000)}_{self._cycle_count}",
                        parameter_name=param_name,
                        delta=update_delta,
                        learning_rate=self._scheduler.get_lr(),
                        signal_id=signal.signal_id,
                        update_type=UpdateType.ERROR_CORRECTION,
                    )
                    with self._lock:
                        self._updates[update.update_id] = update
                        self._parameters[param_name] = self._online_learner.get_parameter(param_name)
                        self._cycle_count += 1
                    updates.append(update)

                # 更新经验优先级（TD误差减小）
                new_td = exp.td_error * 0.9  # 衰减TD误差
                priority_updates[exp.experience_id] = new_td

        # 批量更新优先级
        if priority_updates:
            self._replay_buffer.update_priorities(priority_updates)

        return updates

    def get_replay_buffer(self) -> ExperienceReplayBuffer:
        """获取回放缓冲区"""
        return self._replay_buffer

    def get_online_learner(self) -> OnlineLearner:
        """获取在线学习器"""
        return self._online_learner

    def get_scheduler(self) -> LearningRateScheduler:
        """获取学习率调度器"""
        return self._scheduler

    # ============================================================
    # 阶段116新增：在线学习接口
    # ============================================================

    def online_update(
        self,
        parameter_name: str,
        gradient: float,
        error: Optional[float] = None,
    ) -> float:
        """
        在线参数更新（带动量、梯度裁剪、自适应学习率）

        第一性原理：数据流式到达，逐个处理
        """
        delta = self._online_learner.update(parameter_name, gradient, error)
        with self._lock:
            self._parameters[parameter_name] = self._online_learner.get_parameter(parameter_name)
        return delta

    def online_batch_update(
        self,
        gradients: Dict[str, float],
        error: Optional[float] = None,
    ) -> Dict[str, float]:
        """批量在线更新"""
        results = self._online_learner.batch_update(gradients, error)
        with self._lock:
            for name in gradients:
                self._parameters[name] = self._online_learner.get_parameter(name)
        return results

    def set_schedule_type(
        self,
        schedule_type: LRScheduleType,
        base_lr: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        """设置学习率调度策略"""
        with self._lock:
            if base_lr is not None:
                self._scheduler._base_lr = max(1e-6, base_lr)
            self._scheduler._schedule_type = schedule_type
            for key, val in kwargs.items():
                if hasattr(self._scheduler, f"_{key}"):
                    setattr(self._scheduler, f"_{key}", val)


# ============================================================
# 便捷函数（向后兼容 + 新增）
# ============================================================

def create_learning_engine(engine_id: str = "learning_engine") -> LearningFirstPrinciplesEngine:
    """创建学习引擎"""
    return LearningFirstPrinciplesEngine(engine_id=engine_id)


def create_learning_signal(
    error_magnitude: float,
    error_source: str = "unknown",
    precision: float = 1.0,
) -> Optional[LearningSignal]:
    """创建学习信号"""
    if error_magnitude <= 0.0:
        return None
    return LearningSignal(
        signal_id=f"sig_{int(time.time() * 1000)}",
        error_magnitude=error_magnitude,
        error_source=error_source,
        precision=precision,
    )


def create_parameter_update(
    parameter_name: str,
    delta: float,
    signal_id: str,
    learning_rate: float = 0.01,
) -> ParameterUpdate:
    """创建参数更新"""
    return ParameterUpdate(
        update_id=f"upd_{int(time.time() * 1000)}",
        parameter_name=parameter_name,
        delta=delta * learning_rate,
        learning_rate=learning_rate,
        signal_id=signal_id,
    )


def create_experience(
    state: Dict[str, float],
    action: str,
    reward: float,
    next_state: Dict[str, float],
    td_error: float = 0.0,
) -> Experience:
    """创建经验"""
    return Experience(
        experience_id=f"exp_{int(time.time() * 1000000)}",
        state=state,
        action=action,
        reward=reward,
        next_state=next_state,
        td_error=td_error,
    )


def create_lr_scheduler(
    base_lr: float = 0.01,
    schedule_type: LRScheduleType = LRScheduleType.CONSTANT,
) -> LearningRateScheduler:
    """创建学习率调度器"""
    return LearningRateScheduler(base_lr=base_lr, schedule_type=schedule_type)
