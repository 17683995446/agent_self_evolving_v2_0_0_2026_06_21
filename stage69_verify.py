"""
阶段69验证: 日志分析接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("la", "/workspace/self_evolving_agent/core/log_analyzer.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["la"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段69验证: 日志分析接口标准化")
print("=" * 60)

# 测试1: 创建和解析日志
def test_parse_log():
    parser = mod.create_log_parser()
    parser.register_pattern("default", r"\[(.*?)\]\s+(\w+)\s+(.*)", ["timestamp", "level", "message"])

    entry = parser.parse("[1234567890] ERROR Connection failed", source="app1")
    assert entry.level == mod.LogLevel.ERROR
    assert entry.message == "Connection failed"
    assert entry.source == "app1"
    print("  [test_parse_log] 解析日志 OK")

# 测试2: 分析器添加和过滤
def test_analyzer_filter():
    analyzer = mod.create_log_analyzer()
    analyzer.add_entry(mod.create_log_entry(mod.LogLevel.INFO, "svc1", "started"))
    analyzer.add_entry(mod.create_log_entry(mod.LogLevel.ERROR, "svc1", "failed"))
    analyzer.add_entry(mod.create_log_entry(mod.LogLevel.ERROR, "svc2", "timeout"))

    errors = analyzer.filter_by_level(mod.LogLevel.ERROR)
    assert len(errors) == 2

    svc1_logs = analyzer.filter_by_source("svc1")
    assert len(svc1_logs) == 2
    print("  [test_analyzer_filter] 过滤 OK")

# 测试3: 搜索
def test_search():
    analyzer = mod.create_log_analyzer()
    analyzer.add_entry(mod.create_log_entry(mod.LogLevel.INFO, "svc1", "user login"))
    analyzer.add_entry(mod.create_log_entry(mod.LogLevel.INFO, "svc1", "user logout"))
    analyzer.add_entry(mod.create_log_entry(mod.LogLevel.ERROR, "svc1", "db error"))

    results = analyzer.search("user")
    assert len(results) == 2
    print("  [test_search] 搜索 OK")

# 测试4: 聚合统计
def test_aggregate():
    analyzer = mod.create_log_analyzer()
    for _ in range(5):
        analyzer.add_entry(mod.create_log_entry(mod.LogLevel.INFO, "svc1", "ok"))
    for _ in range(3):
        analyzer.add_entry(mod.create_log_entry(mod.LogLevel.ERROR, "svc1", "fail"))

    agg = analyzer.aggregate_by_level()
    assert agg["info"] == 5
    assert agg["error"] == 3
    print("  [test_aggregate] 聚合统计 OK")

# 测试5: 异常检测
def test_anomaly_detection():
    analyzer = mod.create_log_analyzer()
    for _ in range(10):
        analyzer.add_entry(mod.create_log_entry(mod.LogLevel.ERROR, "svc1", "error msg"))

    anomalies = analyzer.detect_anomalies(error_threshold=5)
    assert len(anomalies) == 1
    assert anomalies[0]["type"] == "error_spike"
    assert anomalies[0]["count"] == 10
    print("  [test_anomaly_detection] 异常检测 OK")

# 测试6: 统计信息
def test_stats():
    analyzer = mod.create_log_analyzer()
    analyzer.add_entry(mod.create_log_entry(mod.LogLevel.INFO, "svc1", "msg1"))
    analyzer.add_entry(mod.create_log_entry(mod.LogLevel.WARNING, "svc2", "msg2"))

    stats = analyzer.get_stats()
    assert stats["total_entries"] == 2
    assert "svc1" in stats["sources"]
    assert "svc2" in stats["sources"]
    print("  [test_stats] 统计信息 OK")

# 测试7: 清除
def test_clear():
    analyzer = mod.create_log_analyzer()
    analyzer.add_entry(mod.create_log_entry(mod.LogLevel.INFO, "svc1", "msg"))
    assert analyzer.get_stats()["total_entries"] == 1
    analyzer.clear()
    assert analyzer.get_stats()["total_entries"] == 0
    print("  [test_clear] 清除 OK")

if __name__ == "__main__":
    test_parse_log()
    test_analyzer_filter()
    test_search()
    test_aggregate()
    test_anomaly_detection()
    test_stats()
    test_clear()
    print("=" * 60)
    print("阶段69验证通过")
    print("=" * 60)
