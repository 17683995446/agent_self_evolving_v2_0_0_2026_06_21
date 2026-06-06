"""
阶段43: 数据管道接口标准化

第一性原理:
1. 数据处理是流水线式的：输入 -> 转换 -> 输出
2. 每个处理步骤必须是纯函数：相同输入产生相同输出
3. 管道必须可组合、可观测、可回滚

设计原则:
- Source: 数据源接口
- Transform: 转换接口
- Sink: 数据汇接口
- Pipeline: 组合Source->Transform->Sink
- 支持中间数据校验和错误处理
- 可观测：每条记录的处理状态
"""

import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, TypeVar
from enum import Enum


T = TypeVar('T')
U = TypeVar('U')


class RecordStatus(Enum):
    """记录处理状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    FILTERED = "filtered"


@dataclass
class DataRecord(Generic[T]):
    """数据记录"""
    data: T
    record_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: RecordStatus = RecordStatus.PENDING
    error: Optional[str] = None

    def __post_init__(self):
        if not self.record_id:
            self.record_id = f"rec_{id(self)}"


# ============================================================
# 数据源接口
# ============================================================

class Source(ABC, Generic[T]):
    """
    数据源

    第一性原理：数据必须从一个确定的位置以确定的方式读取
    """

    @abstractmethod
    def read(self) -> Iterator[DataRecord[T]]:
        """读取数据记录"""
        pass

    @abstractmethod
    def has_more(self) -> bool:
        """是否还有更多数据"""
        pass

    def close(self) -> None:
        """关闭数据源"""
        pass


# ============================================================
# 转换接口
# ============================================================

class Transform(ABC, Generic[T, U]):
    """
    数据转换

    第一性原理：转换是纯函数，相同输入产生相同输出
    """

    @abstractmethod
    def transform(self, record: DataRecord[T]) -> Optional[DataRecord[U]]:
        """
        转换单条记录

        Returns:
            转换后的记录，或None表示过滤掉
        """
        pass

    def batch_transform(self, records: List[DataRecord[T]]) -> List[DataRecord[U]]:
        """批量转换（默认逐个调用）"""
        results = []
        for rec in records:
            try:
                out = self.transform(rec)
                if out is not None:
                    results.append(out)
            except Exception as e:
                rec.status = RecordStatus.FAILED
                rec.error = str(e)
        return results


# ============================================================
# 数据汇接口
# ============================================================

class Sink(ABC, Generic[T]):
    """
    数据汇

    第一性原理：数据必须写入一个确定的位置，写入结果必须可确认
    """

    @abstractmethod
    def write(self, record: DataRecord[T]) -> bool:
        """写入单条记录"""
        pass

    def batch_write(self, records: List[DataRecord[T]]) -> int:
        """批量写入，返回成功写入数量"""
        count = 0
        for rec in records:
            if self.write(rec):
                count += 1
        return count

    def close(self) -> None:
        """关闭数据汇"""
        pass


# ============================================================
# 函数式适配器
# ============================================================

class FunctionSource(Source[T]):
    """函数式数据源"""

    def __init__(self, data: List[T]):
        self._data = data
        self._index = 0

    def read(self) -> Iterator[DataRecord[T]]:
        while self.has_more():
            item = self._data[self._index]
            self._index += 1
            yield DataRecord(data=item)

    def has_more(self) -> bool:
        return self._index < len(self._data)


class FunctionTransform(Transform[T, U]):
    """函数式转换"""

    def __init__(self, fn: Callable[[T], U], name: str = "transform"):
        self.fn = fn
        self.name = name

    def transform(self, record: DataRecord[T]) -> Optional[DataRecord[U]]:
        try:
            result = self.fn(record.data)
            if result is None:
                record.status = RecordStatus.FILTERED
                return None
            out = DataRecord(data=result, metadata=dict(record.metadata))
            out.status = RecordStatus.SUCCESS
            return out
        except Exception as e:
            record.status = RecordStatus.FAILED
            record.error = str(e)
            raise


class FunctionSink(Sink[T]):
    """函数式数据汇"""

    def __init__(self, fn: Optional[Callable[[T], None]] = None):
        self.fn = fn
        self.written: List[T] = []

    def write(self, record: DataRecord[T]) -> bool:
        try:
            if self.fn:
                self.fn(record.data)
            self.written.append(record.data)
            record.status = RecordStatus.SUCCESS
            return True
        except Exception as e:
            record.status = RecordStatus.FAILED
            record.error = str(e)
            return False


# ============================================================
# 数据管道
# ============================================================

class DataPipeline(Generic[T, U]):
    """
    数据管道

    组合 Source -> [Transform] -> Sink
    """

    def __init__(
        self,
        source: Source[T],
        transforms: List[Transform],
        sink: Sink[U],
    ):
        self.source = source
        self.transforms = transforms
        self.sink = sink
        self._stats = {
            "read": 0,
            "written": 0,
            "failed": 0,
            "filtered": 0,
        }
        self._stats_lock = threading.Lock()

    def run(self) -> Dict[str, Any]:
        """
        运行管道

        Returns:
            执行统计
        """
        try:
            for record in self.source.read():
                record.status = RecordStatus.PROCESSING
                self._inc("read")

                current: Any = record
                failed = False

                for transform in self.transforms:
                    try:
                        current = transform.transform(current)
                        if current is None:
                            self._inc("filtered")
                            failed = True
                            break
                    except Exception:
                        self._inc("failed")
                        failed = True
                        break

                if failed:
                    continue

                # 写入
                try:
                    success = self.sink.write(current)
                    if success:
                        self._inc("written")
                    else:
                        self._inc("failed")
                except Exception:
                    self._inc("failed")

        finally:
            self.source.close()
            self.sink.close()

        return dict(self._stats)

    def _inc(self, key: str) -> None:
        with self._stats_lock:
            self._stats[key] += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._stats_lock:
            return dict(self._stats)


# ============================================================
# 便捷函数
# ============================================================

def create_pipeline(
    data: List[T],
    transforms: List[Callable[[Any], Any]],
    sink_fn: Optional[Callable[[Any], None]] = None,
) -> DataPipeline:
    """快速创建管道"""
    source = FunctionSource(data)
    transform_objs = [FunctionTransform(fn) for fn in transforms]
    sink = FunctionSink(sink_fn)
    return DataPipeline(source, transform_objs, sink)
