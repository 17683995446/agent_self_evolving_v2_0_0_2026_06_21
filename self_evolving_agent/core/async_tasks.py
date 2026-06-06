"""
阶段41: 异步任务接口标准化

第一性原理:
1. 异步是对等待时间的利用：当一个任务阻塞时，CPU应该处理其他任务
2. 任务必须有明确的生命周期：提交->排队->执行->完成/失败/取消
3. 任务结果必须可查询、可等待、可回调

设计原则:
- 任务队列：优先级队列，支持FIFO/LIFO/优先级
- 线程池执行器：可配置核心/最大线程数
- 任务Future：查询状态、获取结果、取消
- 任务链：then/compose支持
- 可观测：队列长度、活跃任务、已完成任务
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TypeVar, Generic, List
from enum import Enum
from queue import PriorityQueue, Empty
from concurrent.futures import ThreadPoolExecutor, Future as ConcurrentFuture


T = TypeVar('T')
R = TypeVar('R')


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"       # 排队中
    RUNNING = "running"       # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class TaskResult(Generic[T]):
    """任务结果"""
    task_id: str
    status: TaskStatus
    result: Optional[T] = None
    error: Optional[Exception] = None
    elapsed_ms: float = 0.0


@dataclass(order=True)
class _QueuedTask:
    """队列中的任务（内部使用）"""
    priority: int
    seq: int
    task_id: str = field(compare=False)
    fn: Callable = field(compare=False)
    args: tuple = field(compare=False)
    kwargs: dict = field(compare=False)
    future: 'TaskFuture' = field(compare=False)


# ============================================================
# 任务Future
# ============================================================

class TaskFuture(Generic[T]):
    """
    任务Future

    代表一个异步任务的将来结果
    """

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._status = TaskStatus.PENDING
        self._result: Optional[T] = None
        self._error: Optional[Exception] = None
        self._event = threading.Event()
        self._callbacks: list[Callable[[TaskResult[T]], None]] = []
        self._lock = threading.Lock()
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None

    @property
    def status(self) -> TaskStatus:
        """当前状态"""
        with self._lock:
            return self._status

    def done(self) -> bool:
        """是否已完成（成功/失败/取消）"""
        with self._lock:
            return self._status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    def cancel(self) -> bool:
        """取消任务"""
        with self._lock:
            if self._status == TaskStatus.PENDING:
                self._status = TaskStatus.CANCELLED
                self._event.set()
                self._invoke_callbacks()
                return True
            return False

    def result(self, timeout_ms: Optional[float] = None) -> Optional[T]:
        """阻塞等待结果"""
        timeout = timeout_ms / 1000.0 if timeout_ms is not None else None
        if not self._event.wait(timeout=timeout):
            raise TimeoutError(f"Task {self.task_id} result timeout")

        with self._lock:
            if self._status == TaskStatus.CANCELLED:
                raise RuntimeError(f"Task {self.task_id} was cancelled")
            if self._error:
                raise self._error
            return self._result

    def then(self, callback: Callable[[T], R]) -> 'TaskFuture[R]':
        """注册完成回调，返回新Future"""
        new_future = TaskFuture[R](f"{self.task_id}_then")

        def on_complete(result: TaskResult[T]):
            if result.status == TaskStatus.COMPLETED and result.result is not None:
                try:
                    new_result = callback(result.result)
                    new_future._complete(new_result)
                except Exception as e:
                    new_future._fail(e)
            elif result.status == TaskStatus.FAILED:
                new_future._fail(result.error or Exception("Previous task failed"))
            else:
                new_future._fail(RuntimeError("Previous task cancelled"))

        self.add_callback(on_complete)
        return new_future

    def add_callback(self, callback: Callable[[TaskResult[T]], None]) -> None:
        """添加状态变更回调"""
        with self._lock:
            if self._status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                # 已完成，立即触发
                callback(self._get_result())
            else:
                self._callbacks.append(callback)

    def _start(self) -> None:
        """标记开始执行"""
        with self._lock:
            if self._status == TaskStatus.PENDING:
                self._status = TaskStatus.RUNNING
                self._start_time = time.time()

    def _complete(self, result: T) -> None:
        """标记完成"""
        with self._lock:
            self._status = TaskStatus.COMPLETED
            self._result = result
            self._end_time = time.time()
            self._event.set()
            self._invoke_callbacks()

    def _fail(self, error: Exception) -> None:
        """标记失败"""
        with self._lock:
            self._status = TaskStatus.FAILED
            self._error = error
            self._end_time = time.time()
            self._event.set()
            self._invoke_callbacks()

    def _get_result(self) -> TaskResult[T]:
        """获取结果对象"""
        elapsed = 0.0
        if self._start_time:
            end = self._end_time or time.time()
            elapsed = (end - self._start_time) * 1000
        return TaskResult(
            task_id=self.task_id,
            status=self._status,
            result=self._result,
            error=self._error,
            elapsed_ms=elapsed,
        )

    def _invoke_callbacks(self) -> None:
        """触发回调"""
        result = self._get_result()
        for cb in self._callbacks:
            try:
                cb(result)
            except Exception:
                pass
        self._callbacks.clear()


# ============================================================
# 异步任务执行器
# ============================================================

class AsyncTaskExecutor:
    """
    异步任务执行器

    第一性原理：任务的执行需要调度器、执行器和状态管理的分离
    """

    def __init__(
        self,
        core_threads: int = 2,
        max_threads: int = 10,
        queue_capacity: int = 100,
    ):
        self.core_threads = core_threads
        self.max_threads = max_threads
        self.queue_capacity = queue_capacity

        self._queue: PriorityQueue = PriorityQueue(maxsize=queue_capacity)
        self._executor = ThreadPoolExecutor(
            max_workers=max_threads,
            thread_name_prefix="async_task"
        )
        self._tasks: dict[str, TaskFuture] = {}
        self._seq = 0
        self._seq_lock = threading.Lock()
        self._shutdown = False
        self._stats_lock = threading.Lock()
        self._total_submitted = 0
        self._total_completed = 0
        self._total_failed = 0
        self._total_cancelled = 0

        # 启动调度线程
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

    def submit(
        self,
        fn: Callable[..., T],
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        **kwargs
    ) -> TaskFuture[T]:
        """提交任务"""
        if self._shutdown:
            raise RuntimeError("Executor is shutdown")

        task_id = str(uuid.uuid4())[:8]
        future = TaskFuture[T](task_id)

        with self._seq_lock:
            self._seq += 1
            seq = self._seq

        queued = _QueuedTask(
            priority=priority.value,
            seq=seq,
            task_id=task_id,
            fn=fn,
            args=args,
            kwargs=kwargs,
            future=future,
        )

        try:
            self._queue.put(queued, block=False)
            with self._stats_lock:
                self._total_submitted += 1
            self._tasks[task_id] = future
            return future
        except Exception as e:
            future._fail(e)
            raise RuntimeError(f"Task queue full (capacity={self.queue_capacity})")

    def _scheduler_loop(self) -> None:
        """调度循环"""
        while not self._shutdown:
            try:
                queued = self._queue.get(timeout=0.5)
                if queued.future.status == TaskStatus.CANCELLED:
                    with self._stats_lock:
                        self._total_cancelled += 1
                    continue

                self._executor.submit(self._execute_task, queued)
            except Empty:
                continue
            except Exception:
                continue

    def _execute_task(self, queued: _QueuedTask) -> None:
        """执行任务"""
        future = queued.future
        if future.status == TaskStatus.CANCELLED:
            return

        future._start()
        try:
            result = queued.fn(*queued.args, **queued.kwargs)
            future._complete(result)
            with self._stats_lock:
                self._total_completed += 1
        except Exception as e:
            future._fail(e)
            with self._stats_lock:
                self._total_failed += 1

    def get_task(self, task_id: str) -> Optional[TaskFuture]:
        """获取任务Future"""
        return self._tasks.get(task_id)

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            return {
                "total_submitted": self._total_submitted,
                "total_completed": self._total_completed,
                "total_failed": self._total_failed,
                "total_cancelled": self._total_cancelled,
                "queue_size": self._queue.qsize(),
                "active_tasks": self._total_submitted - self._total_completed - self._total_failed - self._total_cancelled,
            }

    def shutdown(self, wait: bool = True) -> None:
        """关闭执行器"""
        self._shutdown = True
        self._executor.shutdown(wait=wait)


# ============================================================
# 便捷函数
# ============================================================

def create_async_executor(**kwargs) -> AsyncTaskExecutor:
    """创建异步任务执行器"""
    return AsyncTaskExecutor(**kwargs)
