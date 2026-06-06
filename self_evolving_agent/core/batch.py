"""
阶段33: 批处理接口标准化

第一性原理:
1. 批处理是效率的核心机制。单个处理有固定开销，批处理摊薄了单位开销
2. 没有标准化的批处理接口，每个模块将自行实现不兼容的批处理逻辑
3. 批处理必须可配置：批量大小、超时、并发度

设计原则:
- 统一批处理接口：收集→处理→分发
- 支持动态批大小：根据负载自适应
- 支持超时触发：避免无限等待填满批次
- 支持错误隔离：批次中部分失败不影响其他
- 支持背压：下游慢时自动降速
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional, TypeVar, Generic, Tuple
from enum import Enum
from datetime import datetime
import threading
import queue
import time

T = TypeVar('T')
R = TypeVar('R')


class BatchStrategy(Enum):
    """批处理策略"""
    FIXED_SIZE = "fixed_size"       # 固定大小批次
    TIME_WINDOW = "time_window"     # 时间窗口
    DYNAMIC = "dynamic"             # 动态大小（根据负载）


class BatchStatus(Enum):
    """批次状态"""
    PENDING = "pending"             # 等待中
    PROCESSING = "processing"       # 处理中
    COMPLETED = "completed"         # 已完成
    PARTIAL_FAILURE = "partial"     # 部分失败
    FAILED = "failed"               # 完全失败


@dataclass
class BatchItem(Generic[T]):
    """批处理项"""
    item: T
    item_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult(Generic[R]):
    """批处理结果"""
    item_id: str
    result: Optional[R] = None
    error: Optional[str] = None
    success: bool = True
    processing_time_ms: float = 0.0


@dataclass
class Batch(Generic[T, R]):
    """批次"""
    batch_id: str
    items: List[BatchItem[T]]
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    results: List[BatchResult[R]] = field(default_factory=list)
    total_time_ms: float = 0.0


# ============================================================
# 批处理器接口
# ============================================================

class BatchProcessor(Generic[T, R]):
    """
    批处理器接口

    第一性原理：批处理的核心是将输入集合转换为输出集合
    """

    def process_batch(self, items: List[T]) -> List[BatchResult[R]]:
        """
        处理一批输入项

        Args:
            items: 输入项列表

        Returns:
            每个输入项对应的结果列表（顺序一致）
        """
        raise NotImplementedError


class FunctionBatchProcessor(BatchProcessor[T, R]):
    """基于函数的批处理器"""

    def __init__(self, process_fn: Callable[[List[T]], List[R]]):
        self._process_fn = process_fn

    def process_batch(self, items: List[T]) -> List[BatchResult[R]]:
        start = time.time()
        try:
            results = self._process_fn(items)
            return [
                BatchResult(
                    item_id=str(i),
                    result=result,
                    success=True,
                    processing_time_ms=(time.time() - start) * 1000 / len(items)
                )
                for i, result in enumerate(results)
            ]
        except Exception as e:
            # 全部失败
            return [
                BatchResult(
                    item_id=str(i),
                    error=str(e),
                    success=False,
                    processing_time_ms=(time.time() - start) * 1000
                )
                for i in range(len(items))
            ]


# ============================================================
# 批处理收集器
# ============================================================

class BatchCollector(Generic[T, R]):
    """
    批处理收集器

    收集输入项，在条件满足时触发批处理
    """

    def __init__(
        self,
        processor: BatchProcessor[T, R],
        max_batch_size: int = 100,
        max_wait_ms: float = 100.0,
        strategy: BatchStrategy = BatchStrategy.FIXED_SIZE,
        max_concurrent_batches: int = 4,
    ):
        self.processor = processor
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self.strategy = strategy
        self.max_concurrent_batches = max_concurrent_batches

        self._item_queue: queue.Queue = queue.Queue()      # 原始项队列
        self._batch_queue: queue.Queue = queue.Queue()     # 聚合批次队列
        self._results: Dict[str, BatchResult[R]] = {}
        self._result_lock = threading.Lock()
        self._running = False
        self._worker_threads: List[threading.Thread] = []
        self._batch_count = 0
        self._item_count = 0
        self._stats_lock = threading.Lock()

    def start(self) -> None:
        """启动批处理收集器"""
        if self._running:
            return
        self._running = True

        # 启动收集线程
        collector_thread = threading.Thread(target=self._collect_loop, daemon=True)
        collector_thread.start()
        self._worker_threads.append(collector_thread)

        # 启动工作线程
        for _ in range(self.max_concurrent_batches):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self._worker_threads.append(worker)

    def stop(self) -> None:
        """停止批处理收集器"""
        self._running = False
        # 添加空信号以唤醒线程
        self._item_queue.put(None)
        for _ in range(self.max_concurrent_batches):
            self._batch_queue.put(None)
        for t in self._worker_threads:
            t.join(timeout=2.0)

    def submit(self, item: T, item_id: Optional[str] = None,
               metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        提交一个项等待批处理

        Returns:
            item_id（可用于后续查询结果）
        """
        item_id = item_id or f"item_{self._item_count}_{id(item)}"
        batch_item = BatchItem(
            item=item,
            item_id=item_id,
            metadata=metadata or {}
        )
        self._item_queue.put(batch_item)

        with self._stats_lock:
            self._item_count += 1

        return item_id

    def get_result(self, item_id: str, timeout_ms: Optional[float] = None) -> Optional[BatchResult[R]]:
        """获取处理结果"""
        start = time.time()
        timeout_sec = timeout_ms / 1000.0 if timeout_ms else None

        while True:
            with self._result_lock:
                if item_id in self._results:
                    return self._results[item_id]

            if timeout_sec is not None:
                elapsed = time.time() - start
                if elapsed >= timeout_sec:
                    return None

            time.sleep(0.001)

    def _collect_loop(self) -> None:
        """收集循环：将 item_queue 中的项聚合成批次，放入 batch_queue"""
        batch_buffer: List[BatchItem[T]] = []
        last_batch_time = time.time()
        batch_id = 0

        while self._running:
            try:
                item = self._item_queue.get(timeout=0.01)
                if item is None:
                    break
                batch_buffer.append(item)
            except queue.Empty:
                pass

            now = time.time()
            elapsed_ms = (now - last_batch_time) * 1000

            should_flush = (
                len(batch_buffer) >= self.max_batch_size or
                (batch_buffer and elapsed_ms >= self.max_wait_ms)
            )

            if should_flush and batch_buffer:
                batch = Batch(
                    batch_id=f"batch_{batch_id}",
                    items=batch_buffer[:self.max_batch_size]
                )
                # 将剩余项保留
                batch_buffer = batch_buffer[self.max_batch_size:]
                if not batch_buffer:
                    last_batch_time = now
                batch_id += 1

                # 将批次放入批次队列
                self._batch_queue.put(batch)

    def _worker_loop(self) -> None:
        """工作循环：从 batch_queue 处理批次"""
        while self._running:
            try:
                batch = self._batch_queue.get(timeout=0.1)
                if batch is None:
                    break

                self._process_batch(batch)

            except queue.Empty:
                continue

    def _process_batch(self, batch: Batch[T, R]) -> None:
        """处理单个批次"""
        batch.status = BatchStatus.PROCESSING
        start = time.time()

        try:
            items = [item.item for item in batch.items]
            results = self.processor.process_batch(items)

            # 关联结果与 item_id
            for i, result in enumerate(results):
                if i < len(batch.items):
                    result.item_id = batch.items[i].item_id

            batch.results = results
            batch.status = BatchStatus.COMPLETED

            # 检查是否有失败
            if any(not r.success for r in results):
                if all(not r.success for r in results):
                    batch.status = BatchStatus.FAILED
                else:
                    batch.status = BatchStatus.PARTIAL_FAILURE

        except Exception as e:
            batch.status = BatchStatus.FAILED
            batch.results = [
                BatchResult(
                    item_id=item.item_id,
                    error=str(e),
                    success=False
                )
                for item in batch.items
            ]

        batch.processed_at = datetime.now()
        batch.total_time_ms = (time.time() - start) * 1000

        # 存储结果
        with self._result_lock:
            for result in batch.results:
                self._results[result.item_id] = result

        with self._stats_lock:
            self._batch_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            return {
                "item_count": self._item_count,
                "batch_count": self._batch_count,
                "pending_items": self._item_queue.qsize() + self._batch_queue.qsize(),
                "max_batch_size": self.max_batch_size,
                "max_wait_ms": self.max_wait_ms,
            }


# ============================================================
# 同步批处理工具
# ============================================================

class SyncBatcher(Generic[T, R]):
    """
    同步批处理工具

    用于不需要异步收集的场景，直接批量处理列表
    """

    def __init__(self, processor: BatchProcessor[T, R], batch_size: int = 100):
        self.processor = processor
        self.batch_size = batch_size

    def process(self, items: List[T]) -> List[BatchResult[R]]:
        """处理所有项，分批执行"""
        all_results: List[BatchResult[R]] = []

        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            results = self.processor.process_batch(batch)

            # 修正 item_id
            for j, result in enumerate(results):
                if i + j < len(items):
                    result.item_id = f"item_{i + j}"

            all_results.extend(results)

        return all_results


# ============================================================
# 便捷函数
# ============================================================

def batch_process(
    items: List[T],
    process_fn: Callable[[List[T]], List[R]],
    batch_size: int = 100
) -> List[R]:
    """
    便捷函数：同步批量处理

    Returns:
        结果列表（失败项返回None）
    """
    processor = FunctionBatchProcessor(process_fn)
    batcher = SyncBatcher(processor, batch_size)
    results = batcher.process(items)
    return [r.result for r in results]
