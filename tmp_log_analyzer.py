"""
阶段69: 日志分析接口标准化

第一性原理:
1. 日志是系统的黑匣子：记录了发生的一切
2. 结构化日志才能被分析：纯文本难以查询
3. 模式识别是核心：异常往往隐藏在模式变化中

设计原则:
- LogEntry: 日志条目
- LogParser: 日志解析器
- LogAnalyzer: 日志分析器
- 支持结构化解析、模式匹配、异常检测、聚合统计
"""

import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: float
    level: LogLevel
    source: str
    message: str
    fields: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 日志解析器
# ============================================================

class LogParser:
    """
    日志解析器

    将原始日志文本解析为结构化日志条目
    """

    def __init__(self):
        self._patterns: Dict[str, re.Pattern] = {}

    def register_pattern(self, name: str, pattern: str, field_names: List[str]) -> None:
        """注册解析模式"""
        self._patterns[name] = {
            "regex": re.compile(pattern),
            "fields": field_names,
        }

    def parse(self, raw_log: str, source: str = "unknown") -> Optional[LogEntry]:
        """解析原始日志"""
        # 尝试匹配所有模式
        for pattern_name, pattern_info in self._patterns.items():
            match = pattern_info["regex"].match(raw_log)
            if match:
                groups = match.groups()
                fields = {}
                for i, field_name in enumerate(pattern_info["fields"]):
                    if i < len(groups):
                        fields[field_name] = groups[i]

                # 提取级别
                level_str = fields.get("level", "info").upper()
                level = LogLevel.INFO
                try:
                    level = LogLevel[level_str]
                except KeyError:
                    pass

                # 提取时间戳
                ts_str = fields.get("timestamp", "")
                timestamp = time.time()
                if ts_str:
                    try:
                        timestamp = float(ts_str)
                    except ValueError:
                        pass

                return LogEntry(
                    timestamp=timestamp,
                    level=level,
                    source=source,
                    message=fields.get("message", raw_log),
                    fields=fields,
                )

        # 无法匹配，返回原始条目
        return LogEntry(
            timestamp=time.time(),
            level=LogLevel.INFO,
            source=source,
            message=raw_log,
        )


# ============================================================
# 日志分析器
# ============================================================

class LogAnalyzer:
    """
    日志分析器

    对结构化日志进行分析和聚合
    """

    def __init__(self):
        self._entries: List[LogEntry] = []
        self._lock = threading.Lock()

    def add_entry(self, entry: LogEntry) -> None:
        """添加日志条目"""
        with self._lock:
            self._entries.append(entry)

    def add_entries(self, entries: List[LogEntry]) -> None:
        """批量添加"""
        with self._lock:
            self._entries.extend(entries)

    def filter_by_level(self, level: LogLevel) -> List[LogEntry]:
        """按级别过滤"""
        with self._lock:
            return [e for e in self._entries if e.level == level]

    def filter_by_source(self, source: str) -> List[LogEntry]:
        """按来源过滤"""
        with self._lock:
            return [e for e in self._entries if e.source == source]

    def search(self, keyword: str) -> List[LogEntry]:
        """关键词搜索"""
        with self._lock:
            return [e for e in self._entries if keyword in e.message]

    def aggregate_by_level(self) -> Dict[str, int]:
        """按级别聚合统计"""
        with self._lock:
            result: Dict[str, int] = {}
            for entry in self._entries:
                level = entry.level.value
                result[level] = result.get(level, 0) + 1
            return result

    def detect_anomalies(self, error_threshold: int = 5) -> List[Dict[str, Any]]:
        """
        异常检测

        检测错误级别日志是否超过阈值
        """
        with self._lock:
            errors = [e for e in self._entries if e.level in (LogLevel.ERROR, LogLevel.CRITICAL)]

        if len(errors) >= error_threshold:
            return [{
                "type": "error_spike",
                "count": len(errors),
                "threshold": error_threshold,
                "samples": [e.message for e in errors[:3]],
            }]
        return []

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "total_entries": len(self._entries),
                "by_level": self.aggregate_by_level(),
                "sources": list(set(e.source for e in self._entries)),
            }

    def clear(self) -> None:
        """清除日志"""
        with self._lock:
            self._entries = []


# ============================================================
# 便捷函数
# ============================================================

def create_log_parser() -> LogParser:
    """创建日志解析器"""
    return LogParser()


def create_log_analyzer() -> LogAnalyzer:
    """创建日志分析器"""
    return LogAnalyzer()


def create_log_entry(
    level: LogLevel,
    source: str,
    message: str,
    timestamp: Optional[float] = None,
    fields: Optional[Dict[str, Any]] = None,
) -> LogEntry:
    """创建日志条目"""
    return LogEntry(
        timestamp=timestamp or time.time(),
        level=level,
        source=source,
        message=message,
        fields=fields or {},
    )
