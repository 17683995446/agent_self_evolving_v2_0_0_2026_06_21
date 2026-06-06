"""
阶段51: 审计日志接口标准化

第一性原理:
1. 系统的每一次关键操作都必须留下不可篡改的痕迹
2. 审计日志是事后追溯的唯一依据，必须完整、准确、有序
3. 日志必须防篡改：写入后不可修改、不可删除

设计原则:
- AuditEvent: 审计事件定义（谁、何时、做了什么、结果如何）
- AuditLog: 审计日志存储（追加-only）
- AuditLogReader: 审计日志查询
- 支持按时间、用户、操作类型查询
- 支持日志完整性校验
"""

import hashlib
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class AuditAction(Enum):
    """审计操作类型"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    CONFIG_CHANGE = "config_change"
    MODEL_DEPLOY = "model_deploy"
    SYSTEM_ACTION = "system_action"


class AuditResult(Enum):
    """操作结果"""
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str
    timestamp: float
    user_id: str
    action: AuditAction
    resource: str
    result: AuditResult
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    tenant_id: Optional[str] = None
    previous_hash: str = ""
    current_hash: str = ""

    def compute_hash(self) -> str:
        """计算事件哈希"""
        data = f"{self.event_id}:{self.timestamp}:{self.user_id}:{self.action.value}:{self.resource}:{self.result.value}:{self.previous_hash}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


# ============================================================
# 审计日志存储
# ============================================================

class AuditLog:
    """
    审计日志

    第一性原理：审计日志是追加-only的，一旦写入不可修改
    """

    def __init__(self):
        self._events: List[AuditEvent] = []
        self._lock = threading.Lock()
        self._last_hash = "0" * 16

    def append(self, event: AuditEvent) -> bool:
        """追加事件"""
        with self._lock:
            event.previous_hash = self._last_hash
            event.current_hash = event.compute_hash()
            self._events.append(event)
            self._last_hash = event.current_hash
            return True

    def log(
        self,
        user_id: str,
        action: AuditAction,
        resource: str,
        result: AuditResult,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> AuditEvent:
        """便捷记录方法"""
        event = AuditEvent(
            event_id=f"evt_{int(time.time() * 1000000)}_{len(self._events)}",
            timestamp=time.time(),
            user_id=user_id,
            action=action,
            resource=resource,
            result=result,
            details=details or {},
            ip_address=ip_address,
            tenant_id=tenant_id,
        )
        self.append(event)
        return event

    def query(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        resource: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """查询事件"""
        with self._lock:
            results = []
            for event in reversed(self._events):  # 最新的在前
                if len(results) >= limit:
                    break
                if user_id and event.user_id != user_id:
                    continue
                if action and event.action != action:
                    continue
                if resource and event.resource != resource:
                    continue
                if start_time and event.timestamp < start_time:
                    continue
                if end_time and event.timestamp > end_time:
                    continue
                results.append(event)
            return results

    def verify_integrity(self) -> bool:
        """验证日志完整性"""
        with self._lock:
            previous_hash = "0" * 16
            for event in self._events:
                if event.previous_hash != previous_hash:
                    return False
                expected_hash = event.compute_hash()
                if event.current_hash != expected_hash:
                    return False
                previous_hash = event.current_hash
            return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "total_events": len(self._events),
                "first_event_time": self._events[0].timestamp if self._events else None,
                "last_event_time": self._events[-1].timestamp if self._events else None,
                "integrity_verified": self.verify_integrity(),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_audit_log() -> AuditLog:
    """创建审计日志"""
    return AuditLog()
