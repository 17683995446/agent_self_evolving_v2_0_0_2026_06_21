"""
阶段29: 健康检查接口

第一性原理:
1. 系统的健康状态必须可观测、可诊断
2. 没有健康检查，系统故障只能在完全崩溃后才发现
3. 健康检查必须分层：存活检查 / 就绪检查 / 深度检查

设计原则:
- 存活检查（Liveness）：系统是否还在运行
- 就绪检查（Readiness）：系统是否准备好接收请求
- 深度检查（Deep）：各组件是否正常工作
- 可扩展：支持自定义健康检查项
- 可聚合：系统健康由组件健康聚合得出
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod
import threading
import time


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"       # 健康
    DEGRADED = "degraded"     # 降级（部分功能受限）
    UNHEALTHY = "unhealthy"   # 不健康
    UNKNOWN = "unknown"       # 未知（未检查）


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    name: str
    status: HealthStatus
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


# ============================================================
# 健康检查器接口
# ============================================================

class HealthChecker(ABC):
    """健康检查器抽象基类"""
    
    @abstractmethod
    def check(self) -> HealthCheckResult:
        """执行健康检查"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """检查器名称"""
        pass
    
    @property
    def check_type(self) -> str:
        """检查类型：liveness / readiness / deep"""
        return "deep"


class LivenessChecker(HealthChecker):
    """存活检查器基类"""
    @property
    def check_type(self) -> str:
        return "liveness"


class ReadinessChecker(HealthChecker):
    """就绪检查器基类"""
    @property
    def check_type(self) -> str:
        return "readiness"


# ============================================================
# 内置检查器
# ============================================================

class MemoryHealthChecker(HealthChecker):
    """内存健康检查器"""
    
    def __init__(self, threshold_percent: float = 90.0):
        self.threshold_percent = threshold_percent
        self._name = "memory"
    
    @property
    def name(self) -> str:
        return self._name
    
    def check(self) -> HealthCheckResult:
        import psutil
        mem = psutil.virtual_memory()
        used_percent = mem.percent
        
        if used_percent >= self.threshold_percent:
            status = HealthStatus.UNHEALTHY
            message = f"Memory usage critical: {used_percent:.1f}%"
        elif used_percent >= self.threshold_percent * 0.8:
            status = HealthStatus.DEGRADED
            message = f"Memory usage high: {used_percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"Memory usage normal: {used_percent:.1f}%"
        
        return HealthCheckResult(
            name=self.name,
            status=status,
            message=message,
            metadata={
                "total_mb": mem.total / (1024 * 1024),
                "available_mb": mem.available / (1024 * 1024),
                "used_percent": used_percent,
            }
        )


class CPUHealthChecker(HealthChecker):
    """CPU健康检查器"""
    
    def __init__(self, threshold_percent: float = 90.0, interval: float = 0.1):
        self.threshold_percent = threshold_percent
        self.interval = interval
        self._name = "cpu"
    
    @property
    def name(self) -> str:
        return self._name
    
    def check(self) -> HealthCheckResult:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=self.interval)
        
        if cpu_percent >= self.threshold_percent:
            status = HealthStatus.UNHEALTHY
            message = f"CPU usage critical: {cpu_percent:.1f}%"
        elif cpu_percent >= self.threshold_percent * 0.8:
            status = HealthStatus.DEGRADED
            message = f"CPU usage high: {cpu_percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"CPU usage normal: {cpu_percent:.1f}%"
        
        return HealthCheckResult(
            name=self.name,
            status=status,
            message=message,
            metadata={"cpu_percent": cpu_percent, "cpu_count": psutil.cpu_count()}
        )


class DiskHealthChecker(HealthChecker):
    """磁盘健康检查器"""
    
    def __init__(self, threshold_percent: float = 90.0, path: str = "/"):
        self.threshold_percent = threshold_percent
        self.path = path
        self._name = "disk"
    
    @property
    def name(self) -> str:
        return self._name
    
    def check(self) -> HealthCheckResult:
        import psutil
        disk = psutil.disk_usage(self.path)
        used_percent = disk.percent
        
        if used_percent >= self.threshold_percent:
            status = HealthStatus.UNHEALTHY
            message = f"Disk usage critical: {used_percent:.1f}%"
        elif used_percent >= self.threshold_percent * 0.8:
            status = HealthStatus.DEGRADED
            message = f"Disk usage high: {used_percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"Disk usage normal: {used_percent:.1f}%"
        
        return HealthCheckResult(
            name=self.name,
            status=status,
            message=message,
            metadata={
                "total_gb": disk.total / (1024**3),
                "free_gb": disk.free / (1024**3),
                "used_percent": used_percent,
            }
        )


class SimpleHealthChecker(HealthChecker):
    """简单函数式健康检查器"""
    
    def __init__(self, name: str, check_fn: Callable[[], tuple], check_type: str = "deep"):
        self._name = name
        self._check_fn = check_fn
        self._check_type = check_type
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def check_type(self) -> str:
        return self._check_type
    
    def check(self) -> HealthCheckResult:
        start = time.time()
        try:
            status, message, metadata = self._check_fn()
            if isinstance(status, bool):
                status = HealthStatus.HEALTHY if status else HealthStatus.UNHEALTHY
            elif isinstance(status, str):
                status = HealthStatus(status)
            elif not isinstance(status, HealthStatus):
                status = HealthStatus.HEALTHY if status else HealthStatus.UNHEALTHY
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Check failed with exception: {e}"
            metadata = {}
        
        duration = (time.time() - start) * 1000
        
        return HealthCheckResult(
            name=self.name,
            status=status,
            message=message,
            duration_ms=duration,
            metadata=metadata if isinstance(metadata, dict) else {}
        )


# ============================================================
# 健康检查注册表
# ============================================================

class HealthRegistry:
    """健康检查注册表"""
    
    def __init__(self):
        self._checkers: Dict[str, HealthChecker] = {}
        self._lock = threading.RLock()
    
    def register(self, checker: HealthChecker) -> None:
        """注册健康检查器"""
        with self._lock:
            self._checkers[checker.name] = checker
    
    def unregister(self, name: str) -> bool:
        """注销健康检查器"""
        with self._lock:
            if name in self._checkers:
                del self._checkers[name]
                return True
            return False
    
    def get_checker(self, name: str) -> Optional[HealthChecker]:
        """获取健康检查器"""
        with self._lock:
            return self._checkers.get(name)
    
    def list_checkers(self, check_type: Optional[str] = None) -> List[HealthChecker]:
        """列出健康检查器"""
        with self._lock:
            checkers = list(self._checkers.values())
        
        if check_type:
            checkers = [c for c in checkers if c.check_type == check_type]
        
        return checkers
    
    def run_checks(self, check_type: Optional[str] = None) -> List[HealthCheckResult]:
        """运行健康检查"""
        checkers = self.list_checkers(check_type)
        results = []
        
        for checker in checkers:
            try:
                result = checker.check()
                results.append(result)
            except Exception as e:
                results.append(HealthCheckResult(
                    name=checker.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check execution failed: {e}",
                ))
        
        return results
    
    def get_overall_status(self, check_type: Optional[str] = None) -> HealthStatus:
        """获取整体健康状态"""
        results = self.run_checks(check_type)
        
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [r.status for r in results]
        
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        
        return HealthStatus.UNKNOWN


# ============================================================
# 健康检查端点
# ============================================================

@dataclass
class HealthReport:
    """健康检查报告"""
    overall_status: HealthStatus
    checks: List[HealthCheckResult]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "timestamp": self.timestamp.isoformat(),
            "checks": [c.to_dict() for c in self.checks],
            "healthy_count": sum(1 for c in self.checks if c.status == HealthStatus.HEALTHY),
            "unhealthy_count": sum(1 for c in self.checks if c.status == HealthStatus.UNHEALTHY),
        }


class HealthEndpoint:
    """
    健康检查端点
    
    提供标准化的健康检查接口
    """
    
    def __init__(self):
        self.registry = HealthRegistry()
    
    def liveness(self) -> HealthReport:
        """存活检查"""
        results = self.registry.run_checks("liveness")
        
        # 如果没有存活检查器，默认认为存活
        if not results:
            results = [HealthCheckResult(
                name="default",
                status=HealthStatus.HEALTHY,
                message="No liveness checks configured, assuming alive",
            )]
        
        overall = self._aggregate_status(results)
        return HealthReport(overall_status=overall, checks=results)
    
    def readiness(self) -> HealthReport:
        """就绪检查"""
        results = self.registry.run_checks("readiness")
        
        if not results:
            results = [HealthCheckResult(
                name="default",
                status=HealthStatus.HEALTHY,
                message="No readiness checks configured, assuming ready",
            )]
        
        overall = self._aggregate_status(results)
        return HealthReport(overall_status=overall, checks=results)
    
    def health(self) -> HealthReport:
        """完整健康检查"""
        results = self.registry.run_checks()
        overall = self.registry.get_overall_status()
        return HealthReport(overall_status=overall, checks=results)
    
    def _aggregate_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """聚合状态"""
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [r.status for r in results]
        
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        
        return HealthStatus.UNKNOWN


# ============================================================
# 便捷函数
# ============================================================

def create_health_endpoint() -> HealthEndpoint:
    """创建默认健康检查端点"""
    endpoint = HealthEndpoint()
    
    # 注册系统资源检查器
    try:
        import psutil
        endpoint.registry.register(MemoryHealthChecker())
        endpoint.registry.register(CPUHealthChecker())
        endpoint.registry.register(DiskHealthChecker())
    except ImportError:
        pass
    
    return endpoint
