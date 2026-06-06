"""
阶段28: 日志接口标准化 — 验证测试

验证目标:
1. 日志记录可结构化输出（JSON/文本）
2. 不同级别日志正确过滤
3. 内存后端可查询
4. 上下文和trace_id正确传递
5. 异步处理器正常工作
6. 日志管理器单例正确
"""

import sys
import time
import io
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.logging import (
    LogLevel, LogRecord, LogBackend, ConsoleBackend, MemoryBackend,
    AsyncLogProcessor, StructuredLogger, LogManager, get_logger,
)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print('='*60)


def test_log_record_structure():
    """测试日志记录结构"""
    print_section("日志记录结构")
    
    record = LogRecord(
        message="Test message",
        level=LogLevel.INFO,
        source="test_module",
        trace_id="trace-123",
        context={"user_id": 42, "action": "login"},
    )
    
    assert record.message == "Test message"
    assert record.level == LogLevel.INFO
    assert record.source == "test_module"
    assert record.trace_id == "trace-123"
    assert record.context["user_id"] == 42
    assert len(record.record_id) == 8
    print(f"记录ID: {record.record_id}")
    print(f"来源: {record.source}")
    print(f"追踪ID: {record.trace_id}")
    
    # JSON输出
    json_str = record.to_json()
    assert "Test message" in json_str
    assert "INFO" in json_str
    assert "trace-123" in json_str
    print(f"JSON输出包含所有字段: True")
    
    # 字典输出
    d = record.to_dict()
    assert d["level"] == "INFO"
    assert d["source"] == "test_module"
    print(f"字典输出键: {list(d.keys())}")
    
    # 文本输出
    text = record.to_text()
    assert "INFO" in text
    assert "test_module" in text
    assert "user_id=42" in text
    print(f"文本输出: {text[:80]}...")
    
    print("\n日志记录结构测试通过!")
    return True


def test_console_backend():
    """测试控制台后端"""
    print_section("控制台后端")
    
    stream = io.StringIO()
    backend = ConsoleBackend(stream=stream, min_level=LogLevel.INFO)
    
    # INFO级别应写入
    record_info = LogRecord("Info msg", LogLevel.INFO, "test")
    backend.write(record_info)
    
    # DEBUG级别应被过滤
    record_debug = LogRecord("Debug msg", LogLevel.DEBUG, "test")
    backend.write(record_debug)
    
    output = stream.getvalue()
    assert "Info msg" in output
    assert "Debug msg" not in output
    print(f"输出包含INFO: True")
    print(f"输出不包含DEBUG: True")
    
    backend.close()
    print("\n控制台后端测试通过!")
    return True


def test_memory_backend_query():
    """测试内存后端查询"""
    print_section("内存后端查询")
    
    backend = MemoryBackend(min_level=LogLevel.DEBUG)
    
    # 写入多条日志
    backend.write(LogRecord("msg1", LogLevel.DEBUG, "module_a", trace_id="t1"))
    backend.write(LogRecord("msg2", LogLevel.INFO, "module_a", trace_id="t1"))
    backend.write(LogRecord("msg3", LogLevel.ERROR, "module_b", trace_id="t2"))
    backend.write(LogRecord("msg4", LogLevel.WARNING, "module_a", trace_id="t2"))
    
    # 查询所有
    all_records = backend.query()
    assert len(all_records) == 4
    print(f"总记录数: {len(all_records)}")
    
    # 按级别查询 (ERROR=40, 只有ERROR和更高级别)
    error_records = backend.query(min_level=LogLevel.ERROR)
    assert len(error_records) == 1  # 只有ERROR
    print(f"ERROR及以上: {len(error_records)}")
    
    # WARNING及以上 (WARNING=30, ERROR=40)
    warning_records = backend.query(min_level=LogLevel.WARNING)
    assert len(warning_records) == 2  # WARNING and ERROR
    print(f"WARNING及以上: {len(warning_records)}")
    
    # 按来源查询 (module_a: DEBUG, INFO, WARNING = 3条)
    module_a = backend.query(source="module_a")
    assert len(module_a) == 3
    print(f"module_a记录: {len(module_a)}")
    
    # 按trace_id查询 (t1: DEBUG, INFO = 2条)
    trace_t1 = backend.query(trace_id="t1")
    assert len(trace_t1) == 2
    print(f"trace t1记录: {len(trace_t1)}")
    
    # 限制数量
    limited = backend.query(limit=2)
    assert len(limited) == 2
    print(f"限制2条: {len(limited)}")
    
    backend.close()
    print("\n内存后端查询测试通过!")
    return True


def test_structured_logger():
    """测试结构化日志器"""
    print_section("结构化日志器")
    
    backend = MemoryBackend()
    logger = StructuredLogger("test_source")
    logger.add_backend(backend)
    
    # 各级别日志
    logger.debug("Debug message", detail="something")
    logger.info("Info message", user="alice")
    logger.warning("Warning message", count=3)
    logger.error("Error message")
    logger.critical("Critical message")
    
    records = backend.query()
    assert len(records) == 5
    
    levels = [r.level for r in records]
    assert LogLevel.DEBUG in levels
    assert LogLevel.CRITICAL in levels
    print(f"记录数: {len(records)}")
    print(f"级别分布: {[l.name for l in levels]}")
    
    # 检查上下文
    info_record = [r for r in records if r.level == LogLevel.INFO][0]
    assert info_record.context["user"] == "alice"
    print(f"INFO记录上下文: {info_record.context}")
    
    backend.close()
    print("\n结构化日志器测试通过!")
    return True


def test_logger_context():
    """测试日志器上下文传递"""
    print_section("日志器上下文传递")
    
    backend = MemoryBackend()
    logger = StructuredLogger("service")
    logger.add_backend(backend)
    
    # 添加上下文
    ctx_logger = logger.with_context(request_id="req-123", version="1.0")
    ctx_logger.info("Processing request")
    
    # 再添加trace
    trace_logger = ctx_logger.with_trace("trace-456")
    trace_logger.info("Sub-operation")
    
    records = backend.query()
    assert len(records) == 2
    
    # 第一条有上下文，无trace
    assert records[0].context["request_id"] == "req-123"
    assert records[0].trace_id is None
    print(f"第一条上下文: {records[0].context}")
    print(f"第一条trace: {records[0].trace_id}")
    
    # 第二条有上下文和trace
    assert records[1].context["request_id"] == "req-123"
    assert records[1].trace_id == "trace-456"
    print(f"第二条上下文: {records[1].context}")
    print(f"第二条trace: {records[1].trace_id}")
    
    backend.close()
    print("\n日志器上下文传递测试通过!")
    return True


def test_log_level_filtering():
    """测试日志级别过滤"""
    print_section("日志级别过滤")
    
    backend = MemoryBackend(min_level=LogLevel.WARNING)
    logger = StructuredLogger("test")
    logger.add_backend(backend)
    logger.set_min_level(LogLevel.WARNING)
    
    logger.debug("debug")
    logger.info("info")
    logger.warning("warning")
    logger.error("error")
    
    records = backend.query()
    assert len(records) == 2
    assert all(r.level.value >= LogLevel.WARNING.value for r in records)
    print(f"过滤后记录数: {len(records)}")
    print(f"所有记录级别 >= WARNING: True")
    
    backend.close()
    print("\n日志级别过滤测试通过!")
    return True


def test_async_processor():
    """测试异步处理器"""
    print_section("异步处理器")
    
    backend = MemoryBackend()
    processor = AsyncLogProcessor(batch_size=10, flush_interval=0.1)
    processor.add_backend(backend)
    processor.start()
    
    logger = StructuredLogger("async_test")
    logger.set_async_processor(processor)
    
    # 异步写入
    for i in range(5):
        logger.info(f"Message {i}")
    
    # 等待处理
    time.sleep(0.3)
    
    records = backend.query()
    assert len(records) == 5
    print(f"异步写入记录数: {len(records)}")
    
    processor.stop()
    backend.close()
    print("\n异步处理器测试通过!")
    return True


def test_log_manager_singleton():
    """测试日志管理器单例"""
    print_section("日志管理器单例")
    
    # 重置单例（测试需要）
    LogManager._instance = None
    
    manager1 = LogManager()
    manager2 = LogManager()
    
    assert manager1 is manager2
    print(f"两个实例相同: True")
    
    # 添加后端
    backend = MemoryBackend()
    manager1.add_backend(backend)
    
    # 从manager2获取的日志器也能使用后端
    logger = manager2.get_logger("test")
    logger.info("Hello from singleton")
    
    records = backend.query()
    assert len(records) == 1
    assert records[0].message == "Hello from singleton"
    print(f"单例后端共享: True")
    
    manager1.shutdown()
    print("\n日志管理器单例测试通过!")
    return True


def test_error_with_exception():
    """测试带异常的错误日志"""
    print_section("带异常的错误日志")
    
    backend = MemoryBackend()
    logger = StructuredLogger("test")
    logger.add_backend(backend)
    
    try:
        raise ValueError("Something went wrong")
    except Exception as e:
        logger.error("Operation failed", exception=e, operation="divide")
    
    records = backend.query(min_level=LogLevel.ERROR)
    assert len(records) == 1
    assert records[0].exception is not None
    assert "ValueError" in records[0].exception
    assert records[0].context["operation"] == "divide"
    print(f"异常信息包含ValueError: True")
    print(f"上下文: {records[0].context}")
    
    backend.close()
    print("\n带异常的错误日志测试通过!")
    return True


def test_get_logger_convenience():
    """测试便捷函数"""
    print_section("便捷函数")
    
    # 重置单例
    LogManager._instance = None
    
    backend = MemoryBackend()
    manager = LogManager()
    manager.add_backend(backend)
    
    logger = get_logger("my_module", trace_id="abc")
    logger.info("Using convenience function")
    
    records = backend.query()
    assert len(records) == 1
    assert records[0].source == "my_module"
    assert records[0].trace_id == "abc"
    print(f"便捷函数获取的日志器来源: {records[0].source}")
    print(f"便捷函数获取的日志器trace: {records[0].trace_id}")
    
    manager.shutdown()
    print("\n便捷函数测试通过!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("阶段28: 日志接口标准化 — 验证测试")
    print("="*60)
    
    tests = [
        test_log_record_structure,
        test_console_backend,
        test_memory_backend_query,
        test_structured_logger,
        test_logger_context,
        test_log_level_filtering,
        test_async_processor,
        test_log_manager_singleton,
        test_error_with_exception,
        test_get_logger_convenience,
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
