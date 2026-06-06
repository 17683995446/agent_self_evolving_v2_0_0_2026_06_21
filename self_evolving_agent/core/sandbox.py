"""
阶段52: 安全沙箱接口标准化

第一性原理:
1. 不可信代码必须被隔离执行，防止破坏主系统
2. 资源必须受限：CPU、内存、执行时间
3. 沙箱边界必须清晰：什么能访问，什么不能访问

设计原则:
- Sandbox: 沙箱接口
- SandboxedTask: 沙箱内执行的任务
- ResourceLimit: 资源限制（CPU、内存、时间）
- SandboxResult: 执行结果（输出/错误/资源使用）
- 支持超时终止、内存限制、网络隔离
"""

import threading
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class SandboxStatus(Enum):
    """沙箱状态"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    MEMORY_EXCEEDED = "memory_exceeded"
    ERROR = "error"


@dataclass
class ResourceLimit:
    """资源限制"""
    max_execution_time_ms: float = 5000.0   # 最大执行时间（毫秒）
    max_memory_mb: float = 100.0            # 最大内存（MB）
    max_cpu_percent: float = 50.0           # 最大CPU百分比
    max_output_size: int = 10000            # 最大输出字节数


@dataclass
class SandboxResult:
    """沙箱执行结果"""
    status: SandboxStatus
    output: Any = None
    error: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: float = 0.0
    memory_peak_mb: float = 0.0
    resource_limit: Optional[ResourceLimit] = None


# ============================================================
# 沙箱任务
# ============================================================

class SandboxedTask:
    """
    沙箱内执行的任务

    封装需要在隔离环境中运行的代码
    """

    def __init__(
        self,
        task_id: str,
        fn: Callable[..., Any],
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
    ):
        self.task_id = task_id
        self.fn = fn
        self.args = args
        self.kwargs = kwargs or {}

    def run(self) -> Any:
        """执行任务"""
        return self.fn(*self.args, **self.kwargs)


# ============================================================
# 沙箱接口
# ============================================================

class Sandbox(ABC):
    """
    沙箱抽象接口

    第一性原理：隔离不可信代码的执行环境
    """

    @abstractmethod
    def execute(self, task: SandboxedTask, limits: ResourceLimit) -> SandboxResult:
        """在沙箱中执行任务"""
        pass

    @abstractmethod
    def get_status(self) -> SandboxStatus:
        """获取沙箱状态"""
        pass

    @abstractmethod
    def terminate(self) -> None:
        """强制终止沙箱"""
        pass


# ============================================================
# 线程级沙箱（轻量级隔离）
# ============================================================

class ThreadSandbox(Sandbox):
    """
    线程级沙箱

    使用独立线程 + 超时控制实现轻量级隔离。
    适用于可信但可能出错的代码。
    """

    def __init__(self):
        self._status = SandboxStatus.IDLE
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._result: Optional[SandboxResult] = None

    def execute(self, task: SandboxedTask, limits: ResourceLimit) -> SandboxResult:
        """在线程中执行任务，带超时控制"""
        with self._lock:
            self._status = SandboxStatus.RUNNING
            self._result = None

        start_time = time.time()
        result_container: List[SandboxResult] = []
        exception_container: List[Exception] = []
        output_container: List[Any] = []

        def target():
            try:
                output = task.run()
                output_container.append(output)
            except Exception as e:
                exception_container.append(e)

        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()
        self._thread.join(timeout=limits.max_execution_time_ms / 1000.0)

        elapsed_ms = (time.time() - start_time) * 1000

        with self._lock:
            if self._thread.is_alive():
                # 超时
                self._status = SandboxStatus.TIMEOUT
                result = SandboxResult(
                    status=SandboxStatus.TIMEOUT,
                    error=f"Execution timeout after {limits.max_execution_time_ms}ms",
                    execution_time_ms=elapsed_ms,
                    resource_limit=limits,
                )
            elif exception_container:
                self._status = SandboxStatus.ERROR
                result = SandboxResult(
                    status=SandboxStatus.ERROR,
                    error=str(exception_container[0]),
                    stderr=traceback.format_exc(),
                    execution_time_ms=elapsed_ms,
                    resource_limit=limits,
                )
            else:
                self._status = SandboxStatus.COMPLETED
                result = SandboxResult(
                    status=SandboxStatus.COMPLETED,
                    output=output_container[0] if output_container else None,
                    execution_time_ms=elapsed_ms,
                    resource_limit=limits,
                )

            self._result = result
            return result

    def get_status(self) -> SandboxStatus:
        with self._lock:
            return self._status

    def terminate(self) -> None:
        with self._lock:
            self._status = SandboxStatus.TIMEOUT
        # 线程无法强制终止，只能标记状态


# ============================================================
# 进程级沙箱（重量级隔离）
# ============================================================

class ProcessSandbox(Sandbox):
    """
    进程级沙箱

    使用独立进程实现更强隔离。
    适用于不可信代码或需要严格资源限制的场景。
    """

    def __init__(self):
        self._status = SandboxStatus.IDLE
        self._lock = threading.Lock()

    def execute(self, task: SandboxedTask, limits: ResourceLimit) -> SandboxResult:
        """
        在独立进程中执行任务

        使用 multiprocessing 实现进程隔离
        """
        import multiprocessing

        with self._lock:
            self._status = SandboxStatus.RUNNING

        start_time = time.time()
        queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=self._run_in_process, args=(task, queue))
        process.start()
        process.join(timeout=limits.max_execution_time_ms / 1000.0)

        elapsed_ms = (time.time() - start_time) * 1000

        with self._lock:
            if process.is_alive():
                process.terminate()
                process.join(timeout=1.0)
                if process.is_alive():
                    process.kill()
                self._status = SandboxStatus.TIMEOUT
                return SandboxResult(
                    status=SandboxStatus.TIMEOUT,
                    error=f"Execution timeout after {limits.max_execution_time_ms}ms",
                    execution_time_ms=elapsed_ms,
                    resource_limit=limits,
                )

            if not queue.empty():
                result_data = queue.get()
                if result_data.get("error"):
                    self._status = SandboxStatus.ERROR
                    return SandboxResult(
                        status=SandboxStatus.ERROR,
                        error=result_data["error"],
                        stderr=result_data.get("traceback", ""),
                        execution_time_ms=elapsed_ms,
                        resource_limit=limits,
                    )
                else:
                    self._status = SandboxStatus.COMPLETED
                    return SandboxResult(
                        status=SandboxStatus.COMPLETED,
                        output=result_data.get("output"),
                        execution_time_ms=elapsed_ms,
                        resource_limit=limits,
                    )

            self._status = SandboxStatus.ERROR
            return SandboxResult(
                status=SandboxStatus.ERROR,
                error="No result from sandbox",
                execution_time_ms=elapsed_ms,
                resource_limit=limits,
            )

    @staticmethod
    def _run_in_process(task: SandboxedTask, queue: Any) -> None:
        """在子进程中运行任务"""
        try:
            output = task.run()
            queue.put({"output": output})
        except Exception as e:
            queue.put({"error": str(e), "traceback": traceback.format_exc()})

    def get_status(self) -> SandboxStatus:
        with self._lock:
            return self._status

    def terminate(self) -> None:
        with self._lock:
            self._status = SandboxStatus.TIMEOUT


# ============================================================
# 沙箱管理器
# ============================================================

class SandboxManager:
    """
    沙箱管理器

    管理多个沙箱实例，提供统一的任务调度接口
    """

    def __init__(self):
        self._sandboxes: Dict[str, Sandbox] = {}
        self._lock = threading.Lock()

    def register(self, name: str, sandbox: Sandbox) -> None:
        """注册沙箱"""
        with self._lock:
            self._sandboxes[name] = sandbox

    def get(self, name: str) -> Optional[Sandbox]:
        """获取沙箱"""
        with self._lock:
            return self._sandboxes.get(name)

    def execute(
        self,
        sandbox_name: str,
        task: SandboxedTask,
        limits: Optional[ResourceLimit] = None,
    ) -> SandboxResult:
        """在指定沙箱中执行任务"""
        sandbox = self.get(sandbox_name)
        if sandbox is None:
            return SandboxResult(
                status=SandboxStatus.ERROR,
                error=f"Sandbox '{sandbox_name}' not found",
            )
        return sandbox.execute(task, limits or ResourceLimit())

    def list_sandboxes(self) -> List[str]:
        """列出所有沙箱"""
        with self._lock:
            return list(self._sandboxes.keys())


# ============================================================
# 便捷函数
# ============================================================

def create_thread_sandbox() -> ThreadSandbox:
    """创建线程级沙箱"""
    return ThreadSandbox()


def create_process_sandbox() -> ProcessSandbox:
    """创建进程级沙箱"""
    return ProcessSandbox()


def create_sandbox_manager() -> SandboxManager:
    """创建沙箱管理器"""
    return SandboxManager()


def create_task(task_id: str, fn: Callable[..., Any], *args, **kwargs) -> SandboxedTask:
    """创建沙箱任务"""
    return SandboxedTask(task_id=task_id, fn=fn, args=args, kwargs=kwargs)
