"""
阶段55: 边缘计算接口标准化

第一性原理:
1. 计算应靠近数据源：减少延迟、节省带宽
2. 边缘资源受限：必须轻量、高效、可降级
3. 边缘-中心协同：本地预处理，云端深度分析

设计原则:
- EdgeDevice: 边缘设备接口
- EdgeTask: 边缘任务
- EdgeDeployment: 边缘部署配置
- EdgeRegistry: 边缘设备注册中心
- 支持模型压缩、离线运行、增量同步
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class DeviceStatus(Enum):
    """设备状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    DEGRADED = "degraded"  # 降级运行


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class EdgeDeployment:
    """边缘部署配置"""
    model_id: str
    compressed: bool = True
    max_memory_mb: float = 50.0
    max_latency_ms: float = 100.0
    allow_offline: bool = True
    sync_interval_sec: int = 300


@dataclass
class EdgeTask:
    """边缘任务"""
    task_id: str
    fn: Callable[..., Any]
    args: tuple = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout_ms: float = 1000.0


# ============================================================
# 边缘设备
# ============================================================

class EdgeDevice:
    """
    边缘设备

    模拟边缘节点的计算能力、资源限制和任务执行
    """

    def __init__(self, device_id: str, capabilities: Optional[Dict[str, Any]] = None):
        self.device_id = device_id
        self.capabilities = capabilities or {}
        self.status = DeviceStatus.ONLINE
        self._deployments: Dict[str, EdgeDeployment] = {}
        self._task_queue: List[EdgeTask] = []
        self._lock = threading.Lock()
        self._stats = {
            "tasks_executed": 0,
            "tasks_failed": 0,
            "total_latency_ms": 0.0,
        }

    def deploy(self, deployment: EdgeDeployment) -> bool:
        """部署模型/服务到边缘设备"""
        with self._lock:
            if self.status == DeviceStatus.OFFLINE:
                return False
            self._deployments[deployment.model_id] = deployment
            return True

    def undeploy(self, model_id: str) -> bool:
        """从边缘设备卸载模型"""
        with self._lock:
            if model_id in self._deployments:
                del self._deployments[model_id]
                return True
            return False

    def submit_task(self, task: EdgeTask) -> bool:
        """提交任务到设备"""
        with self._lock:
            if self.status in (DeviceStatus.OFFLINE, DeviceStatus.BUSY):
                return False
            self._task_queue.append(task)
            self._task_queue.sort(key=lambda t: t.priority.value)
            return True

    def execute_next(self) -> Optional[Dict[str, Any]]:
        """执行队列中的下一个任务"""
        with self._lock:
            if not self._task_queue:
                return None
            task = self._task_queue.pop(0)

        start = time.time()
        try:
            result = task.fn(*task.args, **task.kwargs)
            elapsed_ms = (time.time() - start) * 1000
            with self._lock:
                self._stats["tasks_executed"] += 1
                self._stats["total_latency_ms"] += elapsed_ms
            return {
                "task_id": task.task_id,
                "status": "success",
                "result": result,
                "elapsed_ms": elapsed_ms,
            }
        except Exception as e:
            with self._lock:
                self._stats["tasks_failed"] += 1
            return {
                "task_id": task.task_id,
                "status": "failed",
                "error": str(e),
            }

    def get_status(self) -> DeviceStatus:
        with self._lock:
            return self.status

    def set_status(self, status: DeviceStatus) -> None:
        with self._lock:
            self.status = status

    def get_deployments(self) -> List[str]:
        with self._lock:
            return list(self._deployments.keys())

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            stats = dict(self._stats)
            stats["queue_length"] = len(self._task_queue)
            stats["status"] = self.status.value
            return stats


# ============================================================
# 边缘注册中心
# ============================================================

class EdgeRegistry:
    """
    边缘设备注册中心

    管理所有边缘设备，支持任务调度和状态监控
    """

    def __init__(self):
        self._devices: Dict[str, EdgeDevice] = {}
        self._lock = threading.Lock()

    def register(self, device: EdgeDevice) -> None:
        """注册设备"""
        with self._lock:
            self._devices[device.device_id] = device

    def unregister(self, device_id: str) -> bool:
        """注销设备"""
        with self._lock:
            if device_id in self._devices:
                del self._devices[device_id]
                return True
            return False

    def get_device(self, device_id: str) -> Optional[EdgeDevice]:
        """获取设备"""
        with self._lock:
            return self._devices.get(device_id)

    def list_devices(self, status_filter: Optional[DeviceStatus] = None) -> List[EdgeDevice]:
        """列出设备"""
        with self._lock:
            devices = list(self._devices.values())
            if status_filter:
                devices = [d for d in devices if d.get_status() == status_filter]
            return devices

    def dispatch_task(self, task: EdgeTask, strategy: str = "round_robin") -> Optional[str]:
        """
        分发任务到合适的边缘设备

        Args:
            task: 任务
            strategy: 调度策略（round_robin / least_loaded）

        Returns:
            分配到的设备ID，或None
        """
        with self._lock:
            candidates = [
                d for d in self._devices.values()
                if d.get_status() in (DeviceStatus.ONLINE, DeviceStatus.DEGRADED)
            ]
            if not candidates:
                return None

            if strategy == "least_loaded":
                device = min(candidates, key=lambda d: d.get_stats()["queue_length"])
            else:
                # round_robin: 简单取第一个
                device = candidates[0]

            success = device.submit_task(task)
            return device.device_id if success else None

    def get_stats(self) -> Dict[str, Any]:
        """获取全局统计"""
        with self._lock:
            return {
                "total_devices": len(self._devices),
                "online": sum(1 for d in self._devices.values() if d.get_status() == DeviceStatus.ONLINE),
                "offline": sum(1 for d in self._devices.values() if d.get_status() == DeviceStatus.OFFLINE),
                "busy": sum(1 for d in self._devices.values() if d.get_status() == DeviceStatus.BUSY),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_edge_device(device_id: str, **capabilities) -> EdgeDevice:
    """创建边缘设备"""
    return EdgeDevice(device_id=device_id, capabilities=capabilities)


def create_edge_registry() -> EdgeRegistry:
    """创建边缘注册中心"""
    return EdgeRegistry()


def create_edge_task(task_id: str, fn: Callable[..., Any], *args, **kwargs) -> EdgeTask:
    """创建边缘任务"""
    return EdgeTask(task_id=task_id, fn=fn, args=args, kwargs=kwargs)
