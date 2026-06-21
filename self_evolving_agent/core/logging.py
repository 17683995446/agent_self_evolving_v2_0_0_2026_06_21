"""
阶段28: 日志接口标准化

第一性原理:
1. 日志是系统的记忆，必须结构化、可查询、可关联
2. 非结构化的日志是信息黑洞，无法用于诊断和分析
3. 日志必须支持：级别、来源、上下文、关联ID、时间戳

设计原则:
- 结构化日志：每条日志是机器可解析的数据
- 分级输出：DEBUG/INFO/WARNING/ERROR/CRITICAL
- 上下文传递：支持trace_id关联分布式操作
- 多后端：支持控制台、文件、内存等多种输出
- 性能友好：异步写入，批量刷新
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional, TextIO
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod
import threading
import json
import sys
import queue
import uuid


class LogLevel(Enum):
    """日志级别"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class LogRecord:
    """
    结构化日志记录
    
    第一性原理：日志记录必须是自包含的信息单元
    """
    message: str
    level: LogLevel
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    trace_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None
    record_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "record_id": self.record_id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "level_value": self.level.value,
            "source": self.source,
            "message": self.message,
        }
        if self.trace_id:
            result["trace_id"] = self.trace_id
        if self.context:
            result["context"] = self.context
        if self.exception:
            result["exception"] = self.exception
        return result
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def to_text(self) -> str:
        """转换为人类可读的文本格式"""
        parts = [
            self.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            f"[{self.level.name:8}]",
            f"[{self.source:20}]",
        ]
        if self.trace_id:
            parts.append(f"[{self.trace_id}]")
        parts.append(self.message)
        
        line = " ".join(parts)
        
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            line += f" | {context_str}"
        
        if self.exception:
            line += f"\nException: {self.exception}"
        
        return line


# ============================================================
# 日志后端接口
# ============================================================

class LogBackend(ABC):
    """日志后端抽象基类"""
    
    @abstractmethod
    def write(self, record: LogRecord) -> None:
        """写入日志记录"""
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """刷新缓冲区"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """关闭后端"""
        pass
    
    def is_enabled_for(self, level: LogLevel) -> bool:
        """是否启用指定级别"""
        return True


class ConsoleBackend(LogBackend):
    """控制台日志后端"""
    
    def __init__(self, stream: TextIO = sys.stdout, min_level: LogLevel = LogLevel.DEBUG):
        self.stream = stream
        self.min_level = min_level
        self._lock = threading.Lock()
    
    def write(self, record: LogRecord) -> None:
        if record.level.value < self.min_level.value:
            return
        with self._lock:
            self.stream.write(record.to_text() + "\n")
    
    def flush(self) -> None:
        with self._lock:
            self.stream.flush()
    
    def close(self) -> None:
        pass
    
    def is_enabled_for(self, level: LogLevel) -> bool:
        return level.value >= self.min_level.value


class MemoryBackend(LogBackend):
    """内存日志后端（用于测试和调试）"""
    
    def __init__(self, max_records: int = 10000, min_level: LogLevel = LogLevel.DEBUG):
        self.records: List[LogRecord] = []
        self.max_records = max_records
        self.min_level = min_level
        self._lock = threading.Lock()
    
    def write(self, record: LogRecord) -> None:
        if record.level.value < self.min_level.value:
            return
        with self._lock:
            self.records.append(record)
            if len(self.records) > self.max_records:
                self.records = self.records[-self.max_records:]
    
    def flush(self) -> None:
        pass
    
    def close(self) -> None:
        pass
    
    def query(
        self,
        min_level: Optional[LogLevel] = None,
        source: Optional[str] = None,
        trace_id: Optional[str] = None,
        limit: int = 100
    ) -> List[LogRecord]:
        """查询日志记录"""
        with self._lock:
            results = self.records[:]
        
        if min_level:
            results = [r for r in results if r.level.value >= min_level.value]
        if source:
            results = [r for r in results if r.source == source]
        if trace_id:
            results = [r for r in results if r.trace_id == trace_id]
        
        return results[-limit:]
    
    def clear(self) -> None:
        with self._lock:
            self.records.clear()


class JsonFileBackend(LogBackend):
    """JSON文件日志后端（阶段179: 支持日志轮转）

    第一性原理:
    1. 日志是磁盘资源 — 必须有上限，避免撑满磁盘
    2. 轮转是运维刚需 — 按大小自动切割，保留历史备份
    3. 零依赖 — 不依赖 logging.handlers.RotatingFileHandler，自行实现
    """

    def __init__(
        self,
        filepath: str,
        min_level: LogLevel = LogLevel.INFO,
        max_bytes: int = 10 * 1024 * 1024,  # 阶段179: 默认10MB轮转
        backup_count: int = 5,
        enable_rotation: bool = True,
    ):
        self.filepath = filepath
        self.min_level = min_level
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.enable_rotation = enable_rotation
        self._lock = threading.Lock()
        self._file: Optional[TextIO] = None
        self._open()

    def _open(self) -> None:
        # 确保目录存在
        import os
        dir_path = os.path.dirname(self.filepath)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        self._file = open(self.filepath, "a", encoding="utf-8")

    def _should_rotate(self) -> bool:
        """检查是否需要轮转"""
        if not self.enable_rotation:
            return False
        try:
            import os
            current_size = os.path.getsize(self.filepath)
            return current_size >= self.max_bytes
        except OSError:
            return False

    def _rotate(self) -> None:
        """执行日志轮转（阶段179）

        将当前文件重命名为 .1，.1 重命名为 .2，依此类推，删除最旧的。
        """
        import os
        # 关闭当前文件
        if self._file:
            self._file.close()
            self._file = None
        # 轮转备份文件：.4 -> 删除, .3 -> .4, .2 -> .3, .1 -> .2
        for i in range(self.backup_count - 1, 0, -1):
            src = f"{self.filepath}.{i}"
            dst = f"{self.filepath}.{i + 1}"
            if os.path.exists(src):
                if os.path.exists(dst):
                    os.remove(dst)
                os.rename(src, dst)
        # 当前文件 -> .1
        if os.path.exists(self.filepath):
            os.rename(self.filepath, f"{self.filepath}.1")
        # 重新打开新文件
        self._open()

    def write(self, record: LogRecord) -> None:
        if record.level.value < self.min_level.value:
            return
        with self._lock:
            if self._file is None:
                self._open()
            # 阶段179: 写入前检查轮转，写入后flush确保磁盘大小准确
            if self._should_rotate():
                self._rotate()
            if self._file:
                self._file.write(record.to_json() + "\n")
                self._file.flush()

    def flush(self) -> None:
        with self._lock:
            if self._file:
                self._file.flush()

    def close(self) -> None:
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None

    def is_enabled_for(self, level: LogLevel) -> bool:
        return level.value >= self.min_level.value


# ============================================================
# 异步日志处理器
# ============================================================

class AsyncLogProcessor:
    """
    异步日志处理器
    
    使用后台线程批量处理日志，避免阻塞业务逻辑
    """
    
    def __init__(self, batch_size: int = 100, flush_interval: float = 1.0):
        self._queue: queue.Queue = queue.Queue(maxsize=10000)
        self._backends: List[LogBackend] = []
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def add_backend(self, backend: LogBackend) -> None:
        with self._lock:
            self._backends.append(backend)
    
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self._flush_all()
    
    def enqueue(self, record: LogRecord) -> bool:
        """将日志记录加入队列"""
        try:
            self._queue.put_nowait(record)
            return True
        except queue.Full:
            return False
    
    def _process_loop(self) -> None:
        import time
        last_flush = time.time()
        batch: List[LogRecord] = []
        
        while self._running:
            try:
                record = self._queue.get(timeout=0.1)
                batch.append(record)
                
                if len(batch) >= self._batch_size:
                    self._write_batch(batch)
                    batch = []
                    last_flush = time.time()
                
            except queue.Empty:
                if batch and time.time() - last_flush >= self._flush_interval:
                    self._write_batch(batch)
                    batch = []
                    last_flush = time.time()
        
        # 处理剩余记录
        if batch:
            self._write_batch(batch)
    
    def _write_batch(self, batch: List[LogRecord]) -> None:
        with self._lock:
            backends = self._backends[:]
        
        for record in batch:
            for backend in backends:
                try:
                    backend.write(record)
                except Exception:
                    pass
    
    def _flush_all(self) -> None:
        with self._lock:
            backends = self._backends[:]
        
        for backend in backends:
            try:
                backend.flush()
            except Exception:
                pass


# ============================================================
# 结构化日志器
# ============================================================

class StructuredLogger:
    """
    结构化日志器
    
    第一性原理：日志是系统的记忆，必须结构化、可查询、可关联
    """
    
    def __init__(self, source: str = "unknown", trace_id: Optional[str] = None):
        self.source = source
        self.trace_id = trace_id
        self._context: Dict[str, Any] = {}
        self._backends: List[LogBackend] = []
        self._async_processor: Optional[AsyncLogProcessor] = None
        self._min_level = LogLevel.DEBUG
    
    def with_context(self, **kwargs) -> 'StructuredLogger':
        """添加上下文并返回新日志器"""
        new_logger = StructuredLogger(self.source, self.trace_id)
        new_logger._context = {**self._context, **kwargs}
        new_logger._backends = self._backends
        new_logger._async_processor = self._async_processor
        new_logger._min_level = self._min_level
        return new_logger
    
    def with_trace(self, trace_id: str) -> 'StructuredLogger':
        """设置追踪ID并返回新日志器"""
        new_logger = self.with_context()
        new_logger.trace_id = trace_id
        return new_logger
    
    def add_backend(self, backend: LogBackend) -> None:
        self._backends.append(backend)
    
    def set_async_processor(self, processor: AsyncLogProcessor) -> None:
        self._async_processor = processor
    
    def set_min_level(self, level: LogLevel) -> None:
        self._min_level = level
    
    def _log(self, level: LogLevel, message: str, **kwargs) -> None:
        if level.value < self._min_level.value:
            return
        
        context = {**self._context, **kwargs}
        
        record = LogRecord(
            message=message,
            level=level,
            source=self.source,
            trace_id=self.trace_id,
            context=context if context else {},
        )
        
        if self._async_processor:
            self._async_processor.enqueue(record)
        else:
            for backend in self._backends:
                if backend.is_enabled_for(level):
                    backend.write(record)
    
    def debug(self, message: str, **kwargs) -> None:
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        exc_str = str(exception) if exception else None
        if exception:
            import traceback
            exc_str = traceback.format_exc()
        
        context = {**kwargs}
        record = LogRecord(
            message=message,
            level=LogLevel.ERROR,
            source=self.source,
            trace_id=self.trace_id,
            context=context,
            exception=exc_str,
        )
        
        if self._async_processor:
            self._async_processor.enqueue(record)
        else:
            for backend in self._backends:
                if backend.is_enabled_for(LogLevel.ERROR):
                    backend.write(record)
    
    def critical(self, message: str, **kwargs) -> None:
        self._log(LogLevel.CRITICAL, message, **kwargs)


# ============================================================
# 日志管理器
# ============================================================

class LogManager:
    """
    日志管理器
    
    管理全局日志配置和后端
    """
    
    _instance: Optional['LogManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'LogManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._backends: List[LogBackend] = []
        self._async_processor: Optional[AsyncLogProcessor] = None
        self._default_level = LogLevel.INFO
        self._loggers: Dict[str, StructuredLogger] = {}
    
    def add_backend(self, backend: LogBackend) -> None:
        self._backends.append(backend)
        if self._async_processor:
            self._async_processor.add_backend(backend)
    
    def enable_async(self, batch_size: int = 100, flush_interval: float = 1.0) -> None:
        self._async_processor = AsyncLogProcessor(batch_size, flush_interval)
        for backend in self._backends:
            self._async_processor.add_backend(backend)
        self._async_processor.start()
    
    def disable_async(self) -> None:
        if self._async_processor:
            self._async_processor.stop()
            self._async_processor = None
    
    def get_logger(self, source: str, trace_id: Optional[str] = None) -> StructuredLogger:
        """获取指定来源的日志器"""
        logger = StructuredLogger(source, trace_id)
        logger._backends = self._backends[:]
        logger._async_processor = self._async_processor
        logger._min_level = self._default_level
        return logger
    
    def set_default_level(self, level: LogLevel) -> None:
        self._default_level = level
    
    def flush(self) -> None:
        if self._async_processor:
            self._async_processor._flush_all()
        for backend in self._backends:
            backend.flush()
    
    def shutdown(self) -> None:
        self.disable_async()
        for backend in self._backends:
            backend.close()


# ============================================================
# 便捷函数
# ============================================================

def get_logger(source: str, trace_id: Optional[str] = None) -> StructuredLogger:
    """获取日志器"""
    return LogManager().get_logger(source, trace_id)
