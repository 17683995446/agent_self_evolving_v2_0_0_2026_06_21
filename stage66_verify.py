"""
阶段66验证: 性能剖析接口标准化
"""
import sys
import importlib.util
import time

spec = importlib.util.spec_from_file_location("pf", "/workspace/self_evolving_agent/core/profiler.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["pf"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段66验证: 性能剖析接口标准化")
print("=" * 60)

# 测试1: 创建和启动剖析器
def test_profiler_lifecycle():
    profiler = mod.create_profiler("p1")
    profiler.start()
    assert profiler.get_stats()["running"] is True
    profiler.stop()
    assert profiler.get_stats()["running"] is False
    print("  [test_profiler_lifecycle] 生命周期 OK")

# 测试2: 记录样本
def test_record_sample():
    profiler = mod.create_profiler("p2")
    sample = mod.create_profile_sample("s1", mod.ProfileType.CPU, 50.0, "func_a")
    profiler.record(sample)
    assert profiler.get_stats()["total_samples"] == 1
    print("  [test_record_sample] 记录样本 OK")

# 测试3: 剖析函数
def test_profile_function():
    profiler = mod.create_profiler("p3")
    def slow_fn():
        time.sleep(0.05)
        return 42

    result = profiler.profile_function(slow_fn)
    assert result["result"] == 42
    assert result["elapsed_ms"] >= 50
    assert profiler.get_stats()["total_samples"] == 1
    print("  [test_profile_function] 剖析函数 OK")

# 测试4: 生成报告
def test_generate_report():
    profiler = mod.create_profiler("p4")
    profiler.record(mod.create_profile_sample("s1", mod.ProfileType.LATENCY, 100.0, "fn1"))
    profiler.record(mod.create_profile_sample("s2", mod.ProfileType.LATENCY, 200.0, "fn1"))
    profiler.record(mod.create_profile_sample("s3", mod.ProfileType.LATENCY, 50.0, "fn2"))

    report = profiler.generate_report(mod.ProfileType.LATENCY)
    assert report.total_samples == 3
    assert report.avg_value == 350.0 / 3
    assert report.max_value == 200.0
    assert report.min_value == 50.0
    assert len(report.hotspots) == 2
    assert report.hotspots[0]["context"] == "fn1"  # fn1 total = 300
    print("  [test_generate_report] 生成报告 OK")

# 测试5: 清除样本
def test_clear():
    profiler = mod.create_profiler("p5")
    profiler.record(mod.create_profile_sample("s1", mod.ProfileType.CPU, 10.0))
    assert profiler.get_stats()["total_samples"] == 1
    profiler.clear()
    assert profiler.get_stats()["total_samples"] == 0
    print("  [test_clear] 清除样本 OK")

# 测试6: 空报告
def test_empty_report():
    profiler = mod.create_profiler("p6")
    report = profiler.generate_report(mod.ProfileType.MEMORY)
    assert report.total_samples == 0
    assert report.avg_value == 0.0
    print("  [test_empty_report] 空报告 OK")

if __name__ == "__main__":
    test_profiler_lifecycle()
    test_record_sample()
    test_profile_function()
    test_generate_report()
    test_clear()
    test_empty_report()
    print("=" * 60)
    print("阶段66验证通过 ✓")
    print("=" * 60)
