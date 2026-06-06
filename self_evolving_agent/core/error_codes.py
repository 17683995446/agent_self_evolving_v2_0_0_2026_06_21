"""
阶段24: 错误码标准化

第一性原理:
1. 错误是信息传递的一种形式，必须在边界处明确
2. 没有统一错误码，调用方无法区分"可恢复错误"和"致命错误"
3. 错误码是接口契约的一部分，必须像输入输出类型一样严格定义

设计原则:
- 每个错误码唯一标识一种错误场景
- 错误码分层：系统级 / 模块级 / 业务级
- 错误码包含：代码、消息、严重级别、是否可恢复、建议操作
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ErrorSeverity(Enum):
    """错误严重级别"""
    DEBUG = "debug"           # 调试信息，不影响运行
    INFO = "info"             # 提示信息
    WARNING = "warning"       # 警告，可继续运行
    ERROR = "error"           # 错误，当前操作失败
    CRITICAL = "critical"     # 严重错误，模块可能不可用
    FATAL = "fatal"           # 致命错误，系统需要重启


class ErrorCategory(Enum):
    """错误分类（第一性原理：错误的根源类别）"""
    SYSTEM = "SYS"        # 系统级错误：内存、线程、IO
    NETWORK = "NET"       # 网络错误：连接、超时、协议
    VALIDATION = "VAL"    # 验证错误：输入非法、类型错误
    RESOURCE = "RES"      # 资源错误：不足、泄漏、竞争
    LOGIC = "LOG"         # 逻辑错误：状态不一致、算法失败
    CONFIG = "CFG"        # 配置错误：缺失、非法、不兼容
    INTERFACE = "IFC"     # 接口错误：版本不兼容、调用非法
    SECURITY = "SEC"      # 安全错误：权限、认证、注入


@dataclass(frozen=True)
class ErrorCode:
    """
    标准化错误码
    
    格式: CATEGORY_NUMBER (如 SYS_001, VAL_003)
    - CATEGORY: 3字母分类代码
    - NUMBER: 3位数字，每类从001开始
    
    第一性原理：错误码是接口的一部分，必须不可变、可比较、可哈希
    """
    code: str
    category: ErrorCategory
    severity: ErrorSeverity
    message_template: str
    recoverable: bool
    description: str
    suggested_action: str
    
    def __post_init__(self):
        # 验证格式
        if not isinstance(self.code, str) or len(self.code) < 7:
            raise ValueError(f"Invalid error code format: {self.code}")
    
    def format_message(self, **kwargs) -> str:
        """使用上下文填充消息模板"""
        try:
            return self.message_template.format(**kwargs)
        except KeyError as e:
            return f"{self.message_template} (context missing: {e})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category.value,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "description": self.description,
            "suggested_action": self.suggested_action,
        }


# ============================================================
# 系统级错误 (SYS_001 - SYS_099)
# ============================================================

SYS_UNKNOWN_ERROR = ErrorCode(
    code="SYS_001",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.ERROR,
    message_template="Unknown system error occurred: {detail}",
    recoverable=False,
    description="未预期的系统错误",
    suggested_action="查看系统日志，联系系统管理员"
)

SYS_INITIALIZATION_FAILED = ErrorCode(
    code="SYS_002",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.FATAL,
    message_template="System initialization failed: {component}",
    recoverable=False,
    description="系统组件初始化失败",
    suggested_action="检查组件配置和依赖，重启系统"
)

SYS_MODULE_NOT_FOUND = ErrorCode(
    code="SYS_003",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.ERROR,
    message_template="Required module not found: {module_name}",
    recoverable=False,
    description="请求的模块不存在或未加载",
    suggested_action="检查模块名称，确认模块已注册"
)

SYS_INTERNAL_STATE_CORRUPTED = ErrorCode(
    code="SYS_004",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.CRITICAL,
    message_template="Internal state corrupted in {component}: {detail}",
    recoverable=False,
    description="内部状态损坏",
    suggested_action="尝试重置组件状态，如无效则重启系统"
)

SYS_THREAD_POOL_EXHAUSTED = ErrorCode(
    code="SYS_005",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.ERROR,
    message_template="Thread pool exhausted: {pool_name}, active={active}, max={max_size}",
    recoverable=True,
    description="线程池资源耗尽",
    suggested_action="等待任务完成或增加线程池大小"
)

# ============================================================
# 验证错误 (VAL_001 - VAL_099)
# ============================================================

VAL_INVALID_TYPE = ErrorCode(
    code="VAL_001",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    message_template="Invalid type for field '{field}': expected {expected}, got {actual}",
    recoverable=True,
    description="字段类型不匹配",
    suggested_action="检查输入数据类型，进行类型转换"
)

VAL_MISSING_REQUIRED_FIELD = ErrorCode(
    code="VAL_002",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    message_template="Missing required field: {field}",
    recoverable=True,
    description="缺少必填字段",
    suggested_action="补充缺失的字段后重试"
)

VAL_OUT_OF_RANGE = ErrorCode(
    code="VAL_003",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    message_template="Field '{field}' value {value} out of range [{min}, {max}]",
    recoverable=True,
    description="数值超出允许范围",
    suggested_action="调整数值到有效范围内"
)

VAL_PATTERN_MISMATCH = ErrorCode(
    code="VAL_004",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    message_template="Field '{field}' does not match required pattern: {pattern}",
    recoverable=True,
    description="字符串格式不匹配",
    suggested_action="检查字段格式是否符合要求"
)

VAL_INVALID_VALUE = ErrorCode(
    code="VAL_005",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    message_template="Invalid value for field '{field}': {value} not in allowed values {allowed}",
    recoverable=True,
    description="字段值不在允许列表中",
    suggested_action="使用允许的值之一"
)

VAL_SCHEMA_VIOLATION = ErrorCode(
    code="VAL_006",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    message_template="Schema validation failed for {schema}: {detail}",
    recoverable=True,
    description="数据不符合Schema定义",
    suggested_action="对照Schema定义修正数据"
)

VAL_CUSTOM_VALIDATION_FAILED = ErrorCode(
    code="VAL_007",
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    message_template="Custom validation failed for '{field}': {reason}",
    recoverable=True,
    description="自定义验证规则未通过",
    suggested_action="根据验证规则修正数据"
)

# ============================================================
# 资源错误 (RES_001 - RES_099)
# ============================================================

RES_MEMORY_LIMIT_EXCEEDED = ErrorCode(
    code="RES_001",
    category=ErrorCategory.RESOURCE,
    severity=ErrorSeverity.CRITICAL,
    message_template="Memory limit exceeded: used={used_mb}MB, limit={limit_mb}MB",
    recoverable=True,
    description="内存使用超过限制",
    suggested_action="释放不必要的缓存，或增加内存限制"
)

RES_CPU_LIMIT_EXCEEDED = ErrorCode(
    code="RES_002",
    category=ErrorCategory.RESOURCE,
    severity=ErrorSeverity.WARNING,
    message_template="CPU usage exceeded threshold: {usage_percent}%",
    recoverable=True,
    description="CPU使用率超过阈值",
    suggested_action="降低任务并发度，或优化算法"
)

RES_DISK_SPACE_LOW = ErrorCode(
    code="RES_003",
    category=ErrorCategory.RESOURCE,
    severity=ErrorSeverity.WARNING,
    message_template="Disk space low: available={available_gb}GB, required={required_gb}GB",
    recoverable=True,
    description="磁盘空间不足",
    suggested_action="清理旧快照和日志，释放磁盘空间"
)

RES_RESOURCE_LEAK_DETECTED = ErrorCode(
    code="RES_004",
    category=ErrorCategory.RESOURCE,
    severity=ErrorSeverity.ERROR,
    message_template="Resource leak detected: {resource_type}, allocated={allocated}, released={released}",
    recoverable=False,
    description="检测到资源泄漏",
    suggested_action="检查资源释放逻辑，重启可能泄漏的模块"
)

# ============================================================
# 接口错误 (IFC_001 - IFC_099)
# ============================================================

IFC_VERSION_INCOMPATIBLE = ErrorCode(
    code="IFC_001",
    category=ErrorCategory.INTERFACE,
    severity=ErrorSeverity.ERROR,
    message_template="Interface version incompatible: {interface} required {required}, but current is {current}",
    recoverable=False,
    description="接口版本不兼容",
    suggested_action="升级或降级接口版本，查看兼容性矩阵"
)

IFC_INTERFACE_NOT_FOUND = ErrorCode(
    code="IFC_002",
    category=ErrorCategory.INTERFACE,
    severity=ErrorSeverity.ERROR,
    message_template="Interface not found: {interface}",
    recoverable=False,
    description="请求的接口未注册",
    suggested_action="检查接口名称，确认模块已加载"
)

IFC_MESSAGE_FORMAT_INVALID = ErrorCode(
    code="IFC_003",
    category=ErrorCategory.INTERFACE,
    severity=ErrorSeverity.ERROR,
    message_template="Invalid message format: {detail}",
    recoverable=True,
    description="消息格式不符合协议",
    suggested_action="检查消息结构是否符合序列化协议"
)

IFC_SERIALIZATION_FAILED = ErrorCode(
    code="IFC_004",
    category=ErrorCategory.INTERFACE,
    severity=ErrorSeverity.ERROR,
    message_template="Serialization failed: {format}, error={error}",
    recoverable=True,
    description="序列化/反序列化失败",
    suggested_action="检查数据是否包含不可序列化对象"
)

# ============================================================
# 配置错误 (CFG_001 - CFG_099)
# ============================================================

CFG_KEY_NOT_FOUND = ErrorCode(
    code="CFG_001",
    category=ErrorCategory.CONFIG,
    severity=ErrorSeverity.ERROR,
    message_template="Configuration key not found: {key}",
    recoverable=False,
    description="配置项不存在",
    suggested_action="检查配置键名，或设置默认值"
)

CFG_INVALID_VALUE = ErrorCode(
    code="CFG_002",
    category=ErrorCategory.CONFIG,
    severity=ErrorSeverity.ERROR,
    message_template="Invalid configuration value for '{key}': {value}, expected {expected}",
    recoverable=True,
    description="配置值非法",
    suggested_action="根据配置文档修正配置值"
)

CFG_TYPE_MISMATCH = ErrorCode(
    code="CFG_003",
    category=ErrorCategory.CONFIG,
    severity=ErrorSeverity.ERROR,
    message_template="Configuration type mismatch for '{key}': expected {expected}, got {actual}",
    recoverable=True,
    description="配置值类型不匹配",
    suggested_action="将配置值转换为正确类型"
)

# ============================================================
# 逻辑错误 (LOG_001 - LOG_099)
# ============================================================

LOG_STATE_TRANSITION_INVALID = ErrorCode(
    code="LOG_001",
    category=ErrorCategory.LOGIC,
    severity=ErrorSeverity.ERROR,
    message_template="Invalid state transition from {from_state} to {to_state}",
    recoverable=True,
    description="非法状态转换",
    suggested_action="检查状态机定义，确保转换合法"
)

LOG_PREDICTION_FAILED = ErrorCode(
    code="LOG_002",
    category=ErrorCategory.LOGIC,
    severity=ErrorSeverity.ERROR,
    message_template="Prediction failed: {reason}",
    recoverable=True,
    description="预测过程失败",
    suggested_action="检查输入数据和模型状态"
)

LOG_OPTIMIZATION_DIVERGED = ErrorCode(
    code="LOG_003",
    category=ErrorCategory.LOGIC,
    severity=ErrorSeverity.WARNING,
    message_template="Optimization diverged after {iterations} iterations",
    recoverable=True,
    description="优化过程发散",
    suggested_action="降低学习率，或检查梯度计算"
)

LOG_CIRCULAR_DEPENDENCY = ErrorCode(
    code="LOG_004",
    category=ErrorCategory.LOGIC,
    severity=ErrorSeverity.ERROR,
    message_template="Circular dependency detected: {cycle_path}",
    recoverable=False,
    description="检测到循环依赖",
    suggested_action="重构模块依赖关系，消除循环"
)

# ============================================================
# 安全错误 (SEC_001 - SEC_099)
# ============================================================

SEC_UNAUTHORIZED_ACCESS = ErrorCode(
    code="SEC_001",
    category=ErrorCategory.SECURITY,
    severity=ErrorSeverity.ERROR,
    message_template="Unauthorized access to {resource} from {source}",
    recoverable=False,
    description="未授权访问",
    suggested_action="检查访问权限配置"
)

SEC_VALIDATION_FAILED = ErrorCode(
    code="SEC_002",
    category=ErrorCategory.SECURITY,
    severity=ErrorSeverity.ERROR,
    message_template="Security validation failed: {detail}",
    recoverable=True,
    description="安全验证失败",
    suggested_action="检查输入是否符合安全规范"
)


# ============================================================
# 错误实例
# ============================================================

@dataclass
class AgentError:
    """
    标准化错误实例
    
    第一性原理：错误是信息，必须包含完整的上下文以便诊断
    """
    error_code: ErrorCode
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"           # 错误来源模块
    trace_id: Optional[str] = None    # 追踪ID，用于关联相关错误
    context: Dict[str, Any] = field(default_factory=dict)
    caused_by: Optional['AgentError'] = None  # 错误链
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "error_code": self.error_code.code,
            "category": self.error_code.category.value,
            "severity": self.error_code.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "recoverable": self.error_code.recoverable,
            "suggested_action": self.error_code.suggested_action,
        }
        if self.trace_id:
            result["trace_id"] = self.trace_id
        if self.context:
            result["context"] = self.context
        if self.caused_by:
            result["caused_by"] = self.caused_by.to_dict()
        return result
    
    def is_recoverable(self) -> bool:
        return self.error_code.recoverable
    
    def is_fatal(self) -> bool:
        return self.error_code.severity == ErrorSeverity.FATAL
    
    def get_severity_level(self) -> int:
        """返回严重级别数值，用于比较"""
        levels = {
            ErrorSeverity.DEBUG: 0,
            ErrorSeverity.INFO: 1,
            ErrorSeverity.WARNING: 2,
            ErrorSeverity.ERROR: 3,
            ErrorSeverity.CRITICAL: 4,
            ErrorSeverity.FATAL: 5,
        }
        return levels.get(self.error_code.severity, 3)


# ============================================================
# 错误注册表
# ============================================================

class ErrorRegistry:
    """
    错误码注册表
    
    第一性原理：所有错误必须可被发现、可查询、可文档化
    """
    
    def __init__(self):
        self._codes: Dict[str, ErrorCode] = {}
        self._register_builtin_errors()
    
    def _register_builtin_errors(self):
        """注册所有内置错误码"""
        import sys
        current_module = sys.modules[__name__]
        
        for name in dir(current_module):
            obj = getattr(current_module, name)
            if isinstance(obj, ErrorCode):
                self.register(obj)
    
    def register(self, error_code: ErrorCode) -> None:
        """注册错误码"""
        if error_code.code in self._codes:
            raise ValueError(f"Error code {error_code.code} already registered")
        self._codes[error_code.code] = error_code
    
    def get(self, code: str) -> Optional[ErrorCode]:
        """查询错误码"""
        return self._codes.get(code)
    
    def find_by_category(self, category: ErrorCategory) -> List[ErrorCode]:
        """按分类查找错误码"""
        return [code for code in self._codes.values() if code.category == category]
    
    def find_by_severity(self, severity: ErrorSeverity) -> List[ErrorCode]:
        """按严重级别查找错误码"""
        return [code for code in self._codes.values() if code.severity == severity]
    
    def list_all(self) -> List[ErrorCode]:
        """列出所有错误码"""
        return list(self._codes.values())
    
    def create_error(
        self,
        code: str,
        source: str = "unknown",
        trace_id: Optional[str] = None,
        **context
    ) -> AgentError:
        """
        根据错误码创建错误实例
        
        Args:
            code: 错误码字符串（如 "VAL_001"）
            source: 错误来源
            trace_id: 追踪ID
            **context: 用于格式化消息的上下文参数
        """
        error_code = self.get(code)
        if error_code is None:
            # 未知错误码，使用通用错误
            error_code = SYS_UNKNOWN_ERROR
            message = error_code.format_message(detail=f"Unknown error code: {code}")
        else:
            message = error_code.format_message(**context)
        
        return AgentError(
            error_code=error_code,
            message=message,
            source=source,
            trace_id=trace_id,
            context=context
        )
    
    def to_documentation(self) -> str:
        """生成错误码文档（Markdown格式）"""
        lines = [
            "# 错误码参考文档",
            "",
            "| 错误码 | 分类 | 严重级别 | 可恢复 | 描述 | 建议操作 |",
            "|--------|------|----------|--------|------|----------|",
        ]
        
        for code in sorted(self._codes.values(), key=lambda c: c.code):
            lines.append(
                f"| {code.code} | {code.category.value} | {code.severity.value} | "
                f"{'是' if code.recoverable else '否'} | {code.description} | {code.suggested_action} |"
            )
        
        return "\n".join(lines)


# 全局错误注册表实例
_global_registry = ErrorRegistry()


def get_error_registry() -> ErrorRegistry:
    """获取全局错误注册表"""
    return _global_registry


def create_error(code: str, source: str = "unknown", trace_id: Optional[str] = None, **context) -> AgentError:
    """快捷函数：根据错误码创建错误实例"""
    return _global_registry.create_error(code, source, trace_id, **context)


# ============================================================
# 异常类
# ============================================================

class AgentException(Exception):
    """
    Agent系统标准异常
    
    第一性原理：异常是错误的一种表现形式，必须携带完整的错误信息
    """
    
    def __init__(self, error: AgentError):
        self.error = error
        super().__init__(error.message)
    
    def to_dict(self) -> Dict[str, Any]:
        return self.error.to_dict()
    
    def is_recoverable(self) -> bool:
        return self.error.is_recoverable()


class ValidationException(AgentException):
    """验证错误异常"""
    pass


class InterfaceException(AgentException):
    """接口错误异常"""
    pass


class ResourceException(AgentException):
    """资源错误异常"""
    pass
