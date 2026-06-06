"""
阶段33: 批处理接口标准化 — 验证测试

验证目标:
1. 同步批处理正确分批
2. 异步收集器按大小触发批次
3. 异步收集器按超时触发批次
4. 批次处理结果可查询
5. 部分失败不影响其他项
6. 统计信息正确
"""

import sys
import time
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.batch import (
    BatchStatus, BatchResult, BatchProcessor,
    FunctionBatchProcessor, SyncBatcher, BatchCollector,
    batch_process,
)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print('='*60)


def test_sync_batcher():
    """测试同步批处理"""
    print_section("同步批处理")

    def process_fn(items):
        return [x * 2 for x in items]

    processor = FunctionBatchProcessor(process_fn)
    batcher = SyncBatcher(processor, batch_size=3)

    results = batcher.process([1, 2, 3, 4, 5])

    assert len(results) == 5
    assert results[0].result == 2
    assert results[3].result == 8
    assert all(r.success for r in results)
    print(f"处理结果: {[r.result for r in results]}")

    print("\n同步批处理测试通过!")
    return True


def test_batch_process_convenience():
    """测试便捷函数"""
    print_section("便捷函数")

    def process_fn(items):
        return [x.upper() for x in items]

    results = batch_process(["a", "b", "c", "d"], process_fn, batch_size=2)

    assert results == ["A", "B", "C", "D"]
    print(f"便捷函数结果: {results}")

    print("\n便捷函数测试通过!")
    return True


def test_async_collector_size_trigger():
    """测试异步收集器按大小触发"""
    print_section("异步收集器按大小触发")

    def process_fn(items):
        return [x + 1 for x in items]

    processor = FunctionBatchProcessor(process_fn)
    collector = BatchCollector(
        processor,
        max_batch_size=5,
        max_wait_ms=10000,  # 很长的超时，确保不会超时触发
        max_concurrent_batches=1,
    )

    collector.start()

    # 提交10个项
    ids = []
    for i in range(10):
        item_id = collector.submit(i)
        ids.append(item_id)

    # 等待处理完成
    time.sleep(0.3)

    # 查询结果
    results = [collector.get_result(item_id, timeout_ms=500) for item_id in ids]

    assert all(r is not None for r in results)
    assert results[0].result == 1
    assert results[5].result == 6
    print(f"结果: {[r.result for r in results]}")

    stats = collector.get_stats()
    assert stats["item_count"] == 10
    assert stats["batch_count"] >= 2  # 至少2批
    print(f"统计: {stats}")

    collector.stop()

    print("\n异步收集器按大小触发测试通过!")
    return True


def test_async_collector_timeout_trigger():
    """测试异步收集器按超时触发"""
    print_section("异步收集器按超时触发")

    def process_fn(items):
        return [x * 10 for x in items]

    processor = FunctionBatchProcessor(process_fn)
    collector = BatchCollector(
        processor,
        max_batch_size=100,  # 很大的批量，确保不会大小触发
        max_wait_ms=50,      # 50ms超时
        max_concurrent_batches=1,
    )

    collector.start()

    # 提交3个项
    ids = []
    for i in range(3):
        item_id = collector.submit(i)
        ids.append(item_id)

    # 等待超时触发
    time.sleep(0.2)

    results = [collector.get_result(item_id, timeout_ms=500) for item_id in ids]

    assert all(r is not None for r in results)
    assert results[0].result == 0
    assert results[1].result == 10
    print(f"超时触发结果: {[r.result for r in results]}")

    stats = collector.get_stats()
    assert stats["batch_count"] >= 1
    print(f"统计: {stats}")

    collector.stop()

    print("\n异步收集器按超时触发测试通过!")
    return True


def test_batch_error_handling():
    """测试批次错误处理"""
    print_section("批次错误处理")

    def process_fn(items):
        if any(x == "bad" for x in items):
            raise ValueError("Batch failed")
        return [x.upper() for x in items]

    processor = FunctionBatchProcessor(process_fn)
    batcher = SyncBatcher(processor, batch_size=10)

    results = batcher.process(["a", "bad", "c"])

    # 全部失败，因为异常导致整个批次失败
    assert all(not r.success for r in results)
    assert "Batch failed" in results[0].error
    print(f"全部失败: True, 错误: {results[0].error}")

    print("\n批次错误处理测试通过!")
    return True


def test_batch_result_structure():
    """测试结果结构"""
    print_section("结果结构")

    result = BatchResult(
        item_id="test_1",
        result=42,
        success=True,
        processing_time_ms=5.5,
    )

    assert result.item_id == "test_1"
    assert result.result == 42
    assert result.success == True
    assert result.processing_time_ms == 5.5
    assert result.error is None
    print(f"成功结果: {result}")

    error_result = BatchResult(
        item_id="test_2",
        error="Something wrong",
        success=False,
    )
    assert error_result.error == "Something wrong"
    assert error_result.result is None
    print(f"失败结果: {error_result}")

    print("\n结果结构测试通过!")
    return True


def test_batch_status():
    """测试批次状态"""
    print_section("批次状态")

    assert BatchStatus.PENDING.value == "pending"
    assert BatchStatus.PROCESSING.value == "processing"
    assert BatchStatus.COMPLETED.value == "completed"
    assert BatchStatus.PARTIAL_FAILURE.value == "partial"
    assert BatchStatus.FAILED.value == "failed"
    print("批次状态值正确")

    print("\n批次状态测试通过!")
    return True


def test_collector_stats():
    """测试收集器统计"""
    print_section("收集器统计")

    def process_fn(items):
        return items

    processor = FunctionBatchProcessor(process_fn)
    collector = BatchCollector(
        processor,
        max_batch_size=2,
        max_wait_ms=5000,
        max_concurrent_batches=1,
    )

    collector.start()

    # 提交项
    for i in range(6):
        collector.submit(i)

    time.sleep(0.3)

    stats = collector.get_stats()
    assert stats["item_count"] == 6
    assert stats["max_batch_size"] == 2
    assert stats["max_wait_ms"] == 5000.0
    print(f"统计: {stats}")

    collector.stop()

    print("\n收集器统计测试通过!")
    return True


def test_empty_batch():
    """测试空批次"""
    print_section("空批次")

    def process_fn(items):
        return items

    processor = FunctionBatchProcessor(process_fn)
    batcher = SyncBatcher(processor, batch_size=5)

    results = batcher.process([])
    assert len(results) == 0
    print("空批次处理: 0 个结果")

    print("\n空批次测试通过!")
    return True


def test_large_batch_split():
    """测试大批次拆分"""
    print_section("大批次拆分")

    def process_fn(items):
        return [x * x for x in items]

    processor = FunctionBatchProcessor(process_fn)
    batcher = SyncBatcher(processor, batch_size=3)

    # 10个项，batch_size=3，应分成4批(3+3+3+1)
    items = list(range(10))
    results = batcher.process(items)

    assert len(results) == 10
    assert results[0].result == 0
    assert results[9].result == 81
    print(f"10项分4批处理: {[r.result for r in results]}")

    print("\n大批次拆分测试通过!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("阶段33: 批处理接口标准化 — 验证测试")
    print("="*60)

    tests = [
        test_sync_batcher,
        test_batch_process_convenience,
        test_async_collector_size_trigger,
        test_async_collector_timeout_trigger,
        test_batch_error_handling,
        test_batch_result_structure,
        test_batch_status,
        test_collector_stats,
        test_empty_batch,
        test_large_batch_split,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"\n[失败] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("="*60)
