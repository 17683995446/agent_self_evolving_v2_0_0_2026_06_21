"""
自驱永续进化Agent系统 — 标准数据交换格式
阶段19：定义标准数据交换格式

第一性原理：信息传递必须有明确的结构，接收方必须能验证数据完整性

所有模块间交换的数据必须使用本文件定义的 Schema，确保：
1. 类型安全
2. 结构明确
3. 可验证
4. 可序列化
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import uuid


# ============================================================================
# 基础Schema
# ============================================================================

@dataclass
class VectorData:
    """向量数据"""
    values: List[float]
    dimension: int = field(init=False)

    def __post_init__(self):
        self.dimension = len(self.values)

    def validate(self) -> bool:
        return len(self.values) == self.dimension and all(isinstance(v, (int, float)) for v in self.values)


@dataclass
class StateVector:
    """状态向量"""
    data: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)

    def validate(self) -> bool:
        return all(isinstance(v, (int, float)) for v in self.data.values())

    def to_array(self) -> List[float]:
        return list(self.data.values())


# ============================================================================
# 预测相关Schema
# ============================================================================

@dataclass
class PredictionSchema:
    """预测结果标准格式"""
    predicted_state: Dict[str, float]
    confidence: float  # [0, 1]
    uncertainty: float  # [0, 1]
    horizon: int = 1
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        return (
            0 <= self.confidence <= 1 and
            0 <= self.uncertainty <= 1 and
            self.horizon >= 1 and
            isinstance(self.predicted_state, dict)
        )


@dataclass
class PredictionErrorSchema:
    """预测误差标准格式"""
    prediction_error: float
    complexity_cost: float
    free_energy: float
    timestamp: datetime = field(default_factory=datetime.now)

    def validate(self) -> bool:
        return all(v >= 0 for v in [self.prediction_error, self.complexity_cost, self.free_energy])


# ============================================================================
# 驱力相关Schema
# ============================================================================

@dataclass
class DriveGapsSchema:
    """驱力缺口标准格式"""
    safe_gap: float  # [0, 1]
    gain_gap: float  # [0, 1]
    eff_gap: float  # [0, 1]
    timestamp: datetime = field(default_factory=datetime.now)

    def validate(self) -> bool:
        return all(0 <= gap <= 1 for gap in [self.safe_gap, self.gain_gap, self.eff_gap])

    def max_gap(self) -> str:
        """返回最大缺口类型"""
        gaps = {"safe": self.safe_gap, "gain": self.gain_gap, "eff": self.eff_gap}
        return max(gaps, key=gaps.get)


@dataclass
class DriveWeightsSchema:
    """驱力权重标准格式"""
    safe: float
    gain: float
    eff: float

    def validate(self) -> bool:
        total = self.safe + self.gain + self.eff
        return all(w >= 0 for w in [self.safe, self.gain, self.eff]) and abs(total - 1.0) < 1e-6


# ============================================================================
# 任务相关Schema
# ============================================================================

@dataclass
class TaskCandidateSchema:
    """候选任务标准格式"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    expected_benefit: float = 0.0
    cost: float = 0.0
    success_probability: float = 0.5
    info_value: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def validate(self) -> bool:
        return (
            self.action and
            0 <= self.success_probability <= 1 and
            self.cost >= 0
        )

    def score(self, weights: Dict[str, float] = None) -> float:
        """计算任务得分"""
        w = weights or {"benefit": 0.4, "cost": -0.3, "success": 0.2, "info": 0.1}
        return (
            w.get("benefit", 0) * self.expected_benefit +
            w.get("cost", 0) * self.cost +
            w.get("success", 0) * self.success_probability +
            w.get("info", 0) * self.info_value
        )


@dataclass
class TaskSelectionSchema:
    """任务选择结果标准格式"""
    selected_task: TaskCandidateSchema
    exploration_rate: float = 0.1
    selection_method: str = "ucb"
    timestamp: datetime = field(default_factory=datetime.now)

    def validate(self) -> bool:
        return self.selected_task.validate() and 0 <= self.exploration_rate <= 1


# ============================================================================
# 优化相关Schema
# ============================================================================

@dataclass
class OptimizationResultSchema:
    """优化结果标准格式"""
    success: bool
    error_before: float
    error_after: float
    iterations: int
    model_state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def validate(self) -> bool:
        return (
            self.error_before >= 0 and
            self.error_after >= 0 and
            self.iterations >= 0
        )

    def improvement(self) -> float:
        """计算改进程度"""
        if self.error_before == 0:
            return 0.0
        return (self.error_before - self.error_after) / self.error_before


# ============================================================================
# 消息相关Schema
# ============================================================================

@dataclass
class MessagePayloadSchema:
    """消息载荷标准格式"""
    data_type: str  # 数据类型标识
    content: Dict[str, Any]  # 实际数据
    encoding: str = "json"  # 编码方式

    def validate(self) -> bool:
        return self.data_type and isinstance(self.content, dict)


@dataclass
class SystemEventSchema:
    """系统事件标准格式"""
    event_type: str
    severity: str = "info"  # info, warning, error, critical
    source: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def validate(self) -> bool:
        return self.event_type and self.severity in ["info", "warning", "error", "critical"]


# ============================================================================
# 记忆相关Schema
# ============================================================================

@dataclass
class MemoryEntrySchema:
    """记忆条目标准格式"""
    key: str
    data: Any
    timestamp: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        return bool(self.key)

    def touch(self) -> None:
        """更新访问信息"""
        self.access_count += 1
        self.last_access = datetime.now()


# ============================================================================
# 配置相关Schema
# ============================================================================

@dataclass
class ModuleConfigSchema:
    """模块配置标准格式"""
    module_id: str
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)

    def validate(self) -> bool:
        return bool(self.module_id)


@dataclass
class SystemConfigSchema:
    """系统配置标准格式"""
    version: str = "1.0.0"
    modules: Dict[str, ModuleConfigSchema] = field(default_factory=dict)
    global_params: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        return bool(self.version)


# ============================================================================
# 验证工具
# ============================================================================

class SchemaValidator:
    """Schema验证器"""

    @staticmethod
    def validate(obj: Any) -> tuple[bool, List[str]]:
        """
        验证对象是否符合Schema规范

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        if hasattr(obj, 'validate'):
            try:
                if not obj.validate():
                    errors.append(f"Validation failed for {type(obj).__name__}")
            except Exception as e:
                errors.append(f"Validation error: {e}")
        else:
            errors.append(f"Object {type(obj).__name__} has no validate method")

        return len(errors) == 0, errors

    @staticmethod
    def validate_batch(objects: List[Any]) -> Dict[str, tuple[bool, List[str]]]:
        """批量验证"""
        return {
            f"obj_{i}": SchemaValidator.validate(obj)
            for i, obj in enumerate(objects)
        }


# ============================================================================
# 序列化工具
# ============================================================================

class SchemaSerializer:
    """Schema序列化器"""

    @staticmethod
    def to_dict(obj: Any) -> Dict[str, Any]:
        """将Schema对象转换为字典"""
        if hasattr(obj, '__dataclass_fields__'):
            result = asdict(obj)
            # 处理datetime
            for key, value in result.items():
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
            return result
        raise ValueError(f"Object {type(obj).__name__} is not a dataclass")

    @staticmethod
    def from_dict(cls: type, data: Dict[str, Any]) -> Any:
        """从字典创建Schema对象"""
        # 处理datetime字符串
        for key, value in data.items():
            if isinstance(value, str) and 'T' in value:
                try:
                    data[key] = datetime.fromisoformat(value)
                except ValueError:
                    pass
        return cls(**data)
