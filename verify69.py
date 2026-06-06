import sys
sys.path.insert(0, "/workspace/self_evolving_agent/core")
import log_analyzer as mod

print("=" * 60)
print("阶段69验证: 日志分析接口标准化")
print("=" * 60)

parser = mod.create_log_parser()
parser.register_pattern("default", r"\[(.*?)\]\s+(\w+)\s+(.*)", ["timestamp", "level", "message"])
entry = parser.parse("[1234567890] ERROR Connection failed", source="app1")
assert entry.level == mod.LogLevel.ERROR
assert entry.message == "Connection failed"
print("  [解析日志] OK")

analyzer = mod.create_log_analyzer()
analyzer.add_entry(mod.create_log_entry(mod.LogLevel.INFO, "svc1", "started"))
analyzer.add_entry(mod.create_log_entry(mod.LogLevel.ERROR, "svc1", "failed"))
analyzer.add_entry(mod.create_log_entry(mod.LogLevel.ERROR, "svc2", "timeout"))
assert len(analyzer.filter_by_level(mod.LogLevel.ERROR)) == 2
assert len(analyzer.filter_by_source("svc1")) == 2
print("  [过滤] OK")

analyzer2 = mod.create_log_analyzer()
analyzer2.add_entry(mod.create_log_entry(mod.LogLevel.INFO, "svc1", "user login"))
analyzer2.add_entry(mod.create_log_entry(mod.LogLevel.INFO, "svc1", "user logout"))
analyzer2.add_entry(mod.create_log_entry(mod.LogLevel.ERROR, "svc1", "db error"))
assert len(analyzer2.search("user")) == 2
print("  [搜索] OK")

analyzer3 = mod.create_log_analyzer()
for _ in range(5):
    analyzer3.add_entry(mod.create_log_entry(mod.LogLevel.INFO, "svc1", "ok"))
for _ in range(3):
    analyzer3.add_entry(mod.create_log_entry(mod.LogLevel.ERROR, "svc1", "fail"))
agg = analyzer3.aggregate_by_level()
assert agg["info"] == 5
assert agg["error"] == 3
print("  [聚合统计] OK")

analyzer4 = mod.create_log_analyzer()
for _ in range(10):
    analyzer4.add_entry(mod.create_log_entry(mod.LogLevel.ERROR, "svc1", "error msg"))
anomalies = analyzer4.detect_anomalies(error_threshold=5)
assert len(anomalies) == 1
assert anomalies[0]["type"] == "error_spike"
assert anomalies[0]["count"] == 10
print("  [异常检测] OK")

analyzer5 = mod.create_log_analyzer()
analyzer5.add_entry(mod.create_log_entry(mod.LogLevel.INFO, "svc1", "msg1"))
analyzer5.add_entry(mod.create_log_entry(mod.LogLevel.WARNING, "svc2", "msg2"))
stats = analyzer5.get_stats()
assert stats["total_entries"] == 2
assert "svc1" in stats["sources"]
assert "svc2" in stats["sources"]
print("  [统计信息] OK")

analyzer6 = mod.create_log_analyzer()
analyzer6.add_entry(mod.create_log_entry(mod.LogLevel.INFO, "svc1", "msg"))
assert analyzer6.get_stats()["total_entries"] == 1
analyzer6.clear()
assert analyzer6.get_stats()["total_entries"] == 0
print("  [清除] OK")

print("=" * 60)
print("阶段69验证通过")
print("=" * 60)
