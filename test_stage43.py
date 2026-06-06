"""
阶段43测试: 数据管道接口标准化
"""
import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.data_pipeline import (
    DataRecord, RecordStatus, FunctionSource, FunctionTransform,
    FunctionSink, DataPipeline, create_pipeline
)


def test_function_source():
    """测试函数式数据源"""
    source = FunctionSource([1, 2, 3])
    records = list(source.read())

    assert len(records) == 3
    assert records[0].data == 1
    assert records[1].data == 2
    assert records[2].data == 3
    print("  [test_function_source] 函数式数据源 ✓")


def test_function_transform():
    """测试函数式转换"""
    transform = FunctionTransform(lambda x: x * 2)
    record = DataRecord(data=5)

    result = transform.transform(record)
    assert result.data == 10
    assert result.status == RecordStatus.SUCCESS
    print("  [test_function_transform] 函数式转换 ✓")


def test_transform_filter():
    """测试转换过滤"""
    transform = FunctionTransform(lambda x: x if x > 0 else None)

    r1 = DataRecord(data=5)
    result1 = transform.transform(r1)
    assert result1 is not None

    r2 = DataRecord(data=-1)
    result2 = transform.transform(r2)
    assert result2 is None
    assert r2.status == RecordStatus.FILTERED
    print("  [test_transform_filter] 转换过滤 ✓")


def test_function_sink():
    """测试函数式数据汇"""
    sink = FunctionSink()
    record = DataRecord(data="hello")

    success = sink.write(record)
    assert success is True
    assert len(sink.written) == 1
    assert sink.written[0] == "hello"
    print("  [test_function_sink] 函数式数据汇 ✓")


def test_pipeline_basic():
    """测试基本管道"""
    pipeline = create_pipeline(
        data=[1, 2, 3, 4, 5],
        transforms=[lambda x: x * 2, lambda x: x + 1],
    )

    stats = pipeline.run()
    assert stats["read"] == 5
    assert stats["written"] == 5
    assert stats["failed"] == 0
    assert pipeline.sink.written == [3, 5, 7, 9, 11]
    print("  [test_pipeline_basic] 基本管道 ✓")


def test_pipeline_with_filter():
    """测试带过滤的管道"""
    pipeline = create_pipeline(
        data=[1, 2, 3, 4, 5, 6],
        transforms=[
            lambda x: x if x % 2 == 0 else None,  # 只保留偶数
            lambda x: x * 10,
        ],
    )

    stats = pipeline.run()
    assert stats["read"] == 6
    assert stats["filtered"] == 3  # 1, 3, 5 被过滤
    assert stats["written"] == 3   # 2, 4, 6
    assert pipeline.sink.written == [20, 40, 60]
    print("  [test_pipeline_with_filter] 带过滤管道 ✓")


def test_pipeline_with_error():
    """测试带错误的管道"""
    pipeline = create_pipeline(
        data=[1, 2, 0, 4],
        transforms=[lambda x: 10 // x],  # 0会除零错误
    )

    stats = pipeline.run()
    assert stats["read"] == 4
    assert stats["failed"] == 1  # 0导致失败
    assert stats["written"] == 3  # 1, 2, 4
    print("  [test_pipeline_with_error] 带错误管道 ✓")


def test_pipeline_stats():
    """测试管道统计"""
    pipeline = create_pipeline(
        data=[1, 2, 3],
        transforms=[lambda x: x],
    )

    pipeline.run()
    stats = pipeline.get_stats()
    assert stats["read"] == 3
    assert stats["written"] == 3
    print("  [test_pipeline_stats] 管道统计 ✓")


def test_data_record():
    """测试数据记录"""
    record = DataRecord(data="test", metadata={"key": "value"})
    assert record.status == RecordStatus.PENDING
    assert record.record_id != ""
    assert record.metadata["key"] == "value"
    print("  [test_data_record] 数据记录 ✓")


def test_batch_transform():
    """测试批量转换"""
    transform = FunctionTransform(lambda x: x.upper())
    records = [DataRecord(data="a"), DataRecord(data="b")]

    results = transform.batch_transform(records)
    assert len(results) == 2
    assert results[0].data == "A"
    assert results[1].data == "B"
    print("  [test_batch_transform] 批量转换 ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("阶段43测试: 数据管道接口标准化")
    print("=" * 60)

    test_function_source()
    test_function_transform()
    test_transform_filter()
    test_function_sink()
    test_pipeline_basic()
    test_pipeline_with_filter()
    test_pipeline_with_error()
    test_pipeline_stats()
    test_data_record()
    test_batch_transform()

    print("=" * 60)
    print("全部10项测试通过 ✓")
    print("=" * 60)
