"""
自驱永续进化Agent系统 — 统一接口规范
阶段1：定义统一接口规范

第一性原理：信息必须在边界处明确传递
- 每个模块必须有明确的输入、输出和契约
- 模块间不直接依赖实现，只依赖接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic
from enum import Enum, auto
from datetime import datetime
import uuid


# ============================================================================
# 接口版本管理
# ============================================================================

INTERFACE_VERSION = "1.0.0"


class InterfaceVersion:
    """接口版本管理，确保模块间兼容性"""

    def __init__(self, major: int, minor: int, patch: int):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def is_compatible_with(self, other: "InterfaceVersion") -> bool:
        """主版本相同则兼容"""
        return self.major == other.major


# ============================================================================
# 标准消息格式
# ============================================================================

class MessageType(Enum):
    """标准消息类型"""
    STATE_UPDATE = auto()      # 状态更新
    PREDICTION = auto()        # 预测结果
    ERROR_SIGNAL = auto()      # 误差信号
    DRIVE_SIGNAL = auto()      # 驱力信号
    TASK_CANDIDATE = auto()    # 候选任务
    TASK_SELECTED = auto()     # 选定任务
    ACTION_EXECUTED = auto()   # 动作执行
    LEARNING_SIGNAL = auto()   # 学习信号
    SYSTEM_EVENT = auto()      # 系统事件


class MessagePriority(Enum):
    """消息优先级"""
    CRITICAL = 0    # 关键：立即处理
    HIGH = 1        # 高：优先处理
    NORMAL = 2      # 正常：按序处理
    LOW = 3         # 低：可延迟处理
    BACKGROUND = 4  # 后台：空闲时处理


@dataclass
class AgentMessage:
    """
    标准消息格式

    第一性原理：信息传递必须有明确的来源、目标、内容和时间戳
    """
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    msg_type: MessageType = MessageType.SYSTEM_EVENT
    source: str = ""           # 来源模块ID
    target: Optional[str] = None  # 目标模块ID（None表示广播）
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    priority: MessagePriority = MessagePriority.NORMAL
    version: str = INTERFACE_VERSION

    def validate(self) -> bool:
        """验证消息格式完整性"""
        return (
            self.msg_id and
            self.source and
            isinstance(self.payload, dict)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type.name,
            "source": self.source,
            "target": self.target,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.name,
            "version": self.version,
        }


# ============================================================================
# 基础模块抽象类
# ============================================================================

class BaseModule(ABC):
    """
    所有模块的抽象基类

    第一性原理：每个模块必须有明确的身份、生命周期和通信方式
    - 身份：module_id
    - 生命周期：initialize -> start -> process -> stop
    - 通信：通过handle_message接收消息，通过send_message发送消息
    """

    def __init__(self, module_id: str, version: InterfaceVersion = None):
        self.module_id = module_id
        self.version = version or InterfaceVersion(1, 0, 0)
        self._initialized = False
        self._running = False
        self._message_bus: Optional["MessageBus"] = None

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化模块，接收配置参数"""
        pass

    @abstractmethod
    def start(self) -> None:
        """启动模块"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止模块"""
        pass

    @abstractmethod
    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """
        处理接收到的消息

        第一性原理：模块只处理自己能理解的消息，不理解的忽略或转发
        """
        pass

    def send_message(self, message: AgentMessage) -> None:
        """发送消息到消息总线"""
        if self._message_bus is not None:
            self._message_bus.publish(message)

    def attach_message_bus(self, bus: "MessageBus") -> None:
        """绑定消息总线"""
        self._message_bus = bus

    def is_initialized(self) -> bool:
        return self._initialized

    def is_running(self) -> bool:
        return self._running

    def get_state(self) -> Dict[str, Any]:
        """获取模块当前状态（用于监控和调试）"""
        return {
            "module_id": self.module_id,
            "version": str(self.version),
            "initialized": self._initialized,
            "running": self._running,
        }


# ============================================================================
# 消息总线接口
# ============================================================================

class MessageBus(ABC):
    """
    消息总线抽象接口

    第一性原理：模块间不直接连接，通过中介传递信息
    类比：大脑神经元通过突触传递信号，不直接连接
    """

    @abstractmethod
    def publish(self, message: AgentMessage) -> None:
        """发布消息"""
        pass

    @abstractmethod
    def subscribe(self, module_id: str, msg_types: List[MessageType],
                  handler: Callable[[AgentMessage], None]) -> None:
        """订阅特定类型的消息"""
        pass

    @abstractmethod
    def unsubscribe(self, module_id: str, msg_types: List[MessageType]) -> None:
        """取消订阅"""
        pass

    @abstractmethod
    def route(self, message: AgentMessage) -> List[str]:
        """确定消息的接收者列表"""
        pass


# ============================================================================
# 预测器接口
# ============================================================================

@dataclass
class Prediction:
    """预测结果标准格式"""
    predicted_state: Dict[str, Any]
    confidence: float           # 置信度 [0, 1]
    uncertainty: float          # 不确定性 [0, 1]
    horizon: int                # 预测步长
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Predictor(ABC):
    """
    预测器抽象接口

    第一性原理：不同层级的预测本质相同，只是时间尺度不同
    """

    @abstractmethod
    def predict(self, current_state: Dict[str, Any],
                horizon: int = 1) -> Prediction:
        """
        基于当前状态预测未来状态

        Args:
            current_state: 当前环境状态
            horizon: 预测步长

        Returns:
            Prediction: 预测结果
        """
        pass

    @abstractmethod
    def update(self, actual_state: Dict[str, Any],
               predicted_state: Dict[str, Any]) -> None:
        """
        根据实际结果更新模型

        第一性原理：预测必须根据反馈不断修正
        """
        pass

    @abstractmethod
    def get_model_state(self) -> Dict[str, Any]:
        """获取模型内部状态（用于保存和恢复）"""
        pass


# ============================================================================
# 驱力接口
# ============================================================================

@dataclass
class DriveGaps:
    """
    驱力缺口标准输出

    第一性原理：动机系统只负责产生驱力，不负责选择行为
    """
    safe_gap: float     # 安全驱力缺口 [0, 1]
    gain_gap: float     # 收益驱力缺口 [0, 1]
    eff_gap: float      # 能效驱力缺口 [0, 1]
    timestamp: datetime = field(default_factory=datetime.now)

    def validate(self) -> bool:
        """验证所有缺口在有效范围内"""
        return all(0 <= gap <= 1 for gap in [self.safe_gap, self.gain_gap, self.eff_gap])


class DriveEngine(ABC):
    """
    驱力引擎抽象接口

    第一性原理：动机只负责产生驱力，不负责选择行为
    """

    @abstractmethod
    def compute_gaps(self, state: Dict[str, Any]) -> DriveGaps:
        """
        计算当前状态的驱力缺口

        Returns:
            DriveGaps: 三个标量值，分别代表安全、收益、能效缺口
        """
        pass

    @abstractmethod
    def update_targets(self, new_targets: Dict[str, float]) -> None:
        """更新目标值"""
        pass


# ============================================================================
# 优化器接口
# ============================================================================

@dataclass
class OptimizationResult:
    """优化结果"""
    success: bool
    model_state: Dict[str, Any]
    iterations: int
    error_before: float
    error_after: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class Optimizer(ABC):
    """
    优化器抽象接口

    第一性原理：两种优化是不同策略，应对不同场景
    """

    @abstractmethod
    def optimize(self, model: Predictor,
                 error_signal: Dict[str, Any]) -> OptimizationResult:
        """
        优化预测模型

        Args:
            model: 待优化的预测模型
            error_signal: 误差信号

        Returns:
            OptimizationResult: 优化结果
        """
        pass

    @abstractmethod
    def can_handle(self, error_signal: Dict[str, Any]) -> bool:
        """判断此优化器是否能处理给定的误差信号"""
        pass


# ============================================================================
# 记忆系统接口
# ============================================================================

class Memory(ABC):
    """
    记忆系统抽象接口

    第一性原理：工作记忆和长期记忆是不同生理结构
    """

    @abstractmethod
    def store(self, key: str, data: Any, metadata: Dict[str, Any] = None) -> bool:
        """存储数据"""
        pass

    @abstractmethod
    def retrieve(self, key: str) -> Optional[Any]:
        """检索数据"""
        pass

    @abstractmethod
    def forget(self, key: str) -> bool:
        """遗忘数据"""
        pass

    @abstractmethod
    def query(self, criteria: Dict[str, Any]) -> List[Any]:
        """按条件查询"""
        pass


# ============================================================================
# 评估器接口
# ============================================================================

@dataclass
class ErrorMetrics:
    """误差指标标准格式"""
    prediction_error: float     # 预测误差
    complexity_cost: float      # 模型复杂度代价
    free_energy: float          # 自由能
    timestamp: datetime = field(default_factory=datetime.now)


class ErrorCalculator(ABC):
    """
    误差计算器

    第一性原理：误差是客观度量，反馈是主观解释
    """

    @abstractmethod
    def calculate(self, predicted: Dict[str, Any],
                  actual: Dict[str, Any]) -> ErrorMetrics:
        """计算预测与实际之间的误差"""
        pass


class FeedbackGenerator(ABC):
    """
    反馈生成器

    将客观误差转化为主观反馈信号
    """

    @abstractmethod
    def generate(self, error_metrics: ErrorMetrics) -> Dict[str, Any]:
        """基于误差生成反馈信号"""
        pass


# ============================================================================
# 任务系统接口
# ============================================================================

@dataclass
class TaskCandidate:
    """候选任务标准格式"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    expected_benefit: float = 0.0
    cost: float = 0.0
    success_probability: float = 0.5
    info_value: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def score(self, weights: Dict[str, float] = None) -> float:
        """计算任务得分"""
        w = weights or {"benefit": 0.4, "cost": -0.3, "success": 0.2, "info": 0.1}
        return (
            w.get("benefit", 0) * self.expected_benefit +
            w.get("cost", 0) * self.cost +
            w.get("success", 0) * self.success_probability +
            w.get("info", 0) * self.info_value
        )


class TaskFactory(ABC):
    """任务工厂：生成候选任务"""

    @abstractmethod
    def generate_candidates(self, gaps: DriveGaps,
                           state: Dict[str, Any]) -> List[TaskCandidate]:
        """基于驱力缺口生成候选任务"""
        pass


class TaskEvaluator(ABC):
    """任务评估器：评估候选任务"""

    @abstractmethod
    def evaluate(self, candidate: TaskCandidate,
                 state: Dict[str, Any]) -> TaskCandidate:
        """评估并填充候选任务的得分字段"""
        pass


class TaskSelector(ABC):
    """任务选择器：选择最优任务"""

    @abstractmethod
    def select(self, candidates: List[TaskCandidate],
               exploration_rate: float = 0.1) -> TaskCandidate:
        """
        选择最优任务

        Args:
            candidates: 候选任务列表
            exploration_rate: 探索率 [0, 1]
        """
        pass


# ============================================================================
# 配置管理接口
# ============================================================================

class ConfigurationManager(ABC):
    """
    配置管理器

    第一性原理：系统的行为应由外部规则决定，而非内部固化
    """

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """设置配置项"""
        pass

    @abstractmethod
    def load(self, source: str) -> None:
        """从外部源加载配置"""
        pass

    @abstractmethod
    def subscribe(self, key: str, callback: Callable[[Any], None]) -> None:
        """订阅配置变更"""
        pass
