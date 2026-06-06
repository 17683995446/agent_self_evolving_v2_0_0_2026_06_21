"""
阶段30: 指标收集接口 — 验证测试

验证目标:
1. Counter单调递增，支持标签和速率计算
2. Gauge可增可减，支持当前值查询
3. Histogram正确分桶，支持百分位数
4. Summary计算分位数，支持过期过滤
5. 注册表管理指标，支持Prometheus导出
6. 标签维度正确聚合
"""

import sys
import time
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.metrics import (
    MetricType, Counter, Gauge, Histogram, Summary,
    MetricsRegistry, create_counter, create_gauge,
)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print('='*60)


def test_counter():
    """测试计数器"""
    print_section("计数器")
    
    counter = Counter("requests_total", "Total requests", label_names=["method"])
    
    # 增加计数
    counter.inc(1, {"method": "GET"})
    counter.inc(1, {"method": "GET"})
    counter.inc(1, {"method": "POST"})
    
    # 查询总计
    assert counter.get_total({"method": "GET"}) == 2
    assert counter.get_total({"method": "POST"}) == 1
    assert counter.get_total() == 3
    print(f"GET总计: {counter.get_total({'method': 'GET'})}")
    print(f"POST总计: {counter.get_total({'method': 'POST'})}")
    print(f"全部总计: {counter.get_total()}")
    
    # 负值应被拒绝
    try:
        counter.inc(-1)
        assert False, "应该抛出异常"
    except ValueError as e:
        print(f"负值正确拒绝: {e}")
    
    # 类型检查
    assert counter.metric_type == MetricType.COUNTER
    print(f"类型: {counter.metric_type.value}")
    
    print("\n计数器测试通过!")
    return True


def test_gauge():
    """测试仪表盘"""
    print_section("仪表盘")
    
    gauge = Gauge("temperature", "CPU temperature", unit="celsius",
                  label_names=["core"])
    
    # 设置值（不带标签 = 空标签键）
    gauge.set(45.5)
    assert gauge.get_current() == 45.5
    print(f"初始值: {gauge.get_current()}")
    
    # 增加（不带标签）
    gauge.inc(5.0)
    assert gauge.get_current() == 50.5
    print(f"增加后: {gauge.get_current()}")
    
    # 减少（不带标签）
    gauge.dec(10.0)
    assert gauge.get_current() == 40.5
    print(f"减少后: {gauge.get_current()}")
    
    # 带标签
    gauge.set(30.0, {"core": "0"})
    gauge.set(35.0, {"core": "1"})
    assert gauge.get_current({"core": "0"}) == 30.0
    assert gauge.get_current({"core": "1"}) == 35.0
    # 全部聚合 = 空标签(40.5) + core0(30.0) + core1(35.0) = 105.5
    assert gauge.get_current() == 105.5
    print(f"core0: {gauge.get_current({'core': '0'})}")
    print(f"core1: {gauge.get_current({'core': '1'})}")
    print(f"总和: {gauge.get_current()}")
    
    print("\n仪表盘测试通过!")
    return True


def test_histogram():
    """测试直方图"""
    print_section("直方图")
    
    hist = Histogram(
        "request_duration",
        "Request duration",
        unit="seconds",
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
    )
    
    # 记录观测值
    values = [0.05, 0.2, 0.3, 0.8, 1.5, 3.0]
    for v in values:
        hist.observe(v)
    
    # 检查计数
    assert hist.get_count() == 6
    print(f"总观测数: {hist.get_count()}")
    
    # 检查桶计数
    buckets = hist.get_bucket_counts()
    assert buckets[0.1] == 1   # 只有0.05
    assert buckets[0.5] == 3   # 0.05, 0.2, 0.3
    assert buckets[1.0] == 4   # + 0.8
    assert buckets[2.0] == 5   # + 1.5
    assert buckets[5.0] == 6   # + 3.0
    print(f"桶0.1: {buckets[0.1]}")
    print(f"桶0.5: {buckets[0.5]}")
    print(f"桶5.0: {buckets[5.0]}")
    
    # 检查总和
    assert abs(hist.get_sum() - sum(values)) < 0.001
    print(f"总和: {hist.get_sum()}")
    
    # 百分位数
    p50 = hist.get_percentile(50)
    assert 0.2 <= p50 <= 0.8
    print(f"P50: {p50}")
    
    print("\n直方图测试通过!")
    return True


def test_summary():
    """测试摘要"""
    print_section("摘要")
    
    summary = Summary("response_size", "Response size", unit="bytes")
    
    # 记录值
    values = [100, 200, 300, 400, 500]
    for v in values:
        summary.observe(v)
    
    # 计数和总和
    assert summary.get_count() == 5
    assert summary.get_sum() == 1500
    assert summary.get_average() == 300.0
    print(f"计数: {summary.get_count()}")
    print(f"总和: {summary.get_sum()}")
    print(f"平均值: {summary.get_average()}")
    
    # 分位数
    quantiles = summary.get_quantiles()
    assert quantiles[0.5] == 300  # 中位数
    assert quantiles[0.9] == 500  # 90分位
    print(f"分位数: {quantiles}")
    
    print("\n摘要测试通过!")
    return True


def test_metrics_registry():
    """测试指标注册表"""
    print_section("指标注册表")
    
    registry = MetricsRegistry()
    
    # 创建指标
    c = registry.counter("http_requests", "HTTP requests")
    g = registry.gauge("active_connections", "Active connections")
    h = registry.histogram("latency", "Request latency")
    s = registry.summary("payload_size", "Payload size")
    
    # 列出指标
    metrics = registry.list_metrics()
    assert len(metrics) == 4
    print(f"注册指标数: {len(metrics)}")
    
    # 获取指标
    assert registry.get("http_requests") is c
    assert registry.get("nonexistent") is None
    print("获取指标: 通过")
    
    # 重复注册应失败
    try:
        registry.counter("http_requests", "Duplicate")
        assert False, "应该抛出异常"
    except ValueError as e:
        print(f"重复注册正确拒绝: {e}")
    
    print("\n指标注册表测试通过!")
    return True


def test_prometheus_export():
    """测试Prometheus格式导出"""
    print_section("Prometheus格式导出")
    
    registry = MetricsRegistry()
    
    counter = registry.counter("requests", "Total requests", label_names=["method"])
    counter.inc(10, {"method": "GET"})
    counter.inc(5, {"method": "POST"})
    
    gauge = registry.gauge("temperature", "Temperature")
    gauge.set(42.5)
    
    output = registry.to_prometheus_format()
    
    assert "# HELP requests Total requests" in output
    assert "# TYPE requests counter" in output
    assert 'requests{method="GET"} 10' in output
    assert 'requests{method="POST"} 5' in output
    assert "# HELP temperature Temperature" in output
    assert "temperature 42.5" in output
    
    print(f"导出内容预览:\n{output[:300]}...")
    
    print("\nPrometheus格式导出测试通过!")
    return True


def test_counter_rate():
    """测试计数器速率"""
    print_section("计数器速率")
    
    counter = Counter("events", "Events")
    
    # 快速增加
    for i in range(5):
        counter.inc(1)
        time.sleep(0.05)
    
    rate = counter.get_rate(window_seconds=10)
    assert rate > 0
    print(f"速率: {rate:.2f} events/second")
    
    # 空计数器
    empty = Counter("empty", "Empty")
    assert empty.get_rate() == 0.0
    print(f"空计数器速率: {empty.get_rate()}")
    
    print("\n计数器速率测试通过!")
    return True


def test_histogram_with_labels():
    """测试带标签的直方图"""
    print_section("带标签的直方图")
    
    hist = Histogram("api_latency", "API latency", unit="ms",
                     label_names=["endpoint"],
                     buckets=[10, 50, 100, 500])
    
    hist.observe(5, {"endpoint": "/users"})
    hist.observe(20, {"endpoint": "/users"})
    hist.observe(200, {"endpoint": "/reports"})
    
    # 按标签查询
    users_buckets = hist.get_bucket_counts({"endpoint": "/users"})
    assert users_buckets[10] == 1
    assert users_buckets[50] == 2
    print(f"/users桶10: {users_buckets[10]}")
    print(f"/users桶50: {users_buckets[50]}")
    
    reports_buckets = hist.get_bucket_counts({"endpoint": "/reports"})
    assert reports_buckets[500] == 1
    print(f"/reports桶500: {reports_buckets[500]}")
    
    # 全部聚合
    all_buckets = hist.get_bucket_counts()
    assert all_buckets[50] == 2
    assert all_buckets[500] == 3
    print(f"全部桶500: {all_buckets[500]}")
    
    print("\n带标签的直方图测试通过!")
    return True


def test_metric_base_class():
    """测试指标基类"""
    print_section("指标基类")
    
    from self_evolving_agent.core.metrics import Metric
    
    metric = Metric("test", "Test metric", MetricType.GAUGE)
    
    # 观测值
    metric.observe(10)
    metric.observe(20)
    
    values = metric.get_values()
    assert len(values) == 2
    assert values[0].value == 10
    assert values[1].value == 20
    print(f"值数量: {len(values)}")
    
    # 最新值
    latest = metric.get_latest()
    assert latest.value == 20
    print(f"最新值: {latest.value}")
    
    # 字典表示
    d = metric.to_dict()
    assert d["name"] == "test"
    assert d["type"] == "gauge"
    print(f"字典: {d}")
    
    print("\n指标基类测试通过!")
    return True


def test_global_registry():
    """测试全局注册表便捷函数"""
    print_section("全局注册表便捷函数")
    
    # 使用便捷函数
    c = create_counter("global_counter", "A global counter")
    g = create_gauge("global_gauge", "A global gauge")
    
    from self_evolving_agent.core.metrics import get_metrics_registry
    registry = get_metrics_registry()
    
    assert registry.get("global_counter") is c
    assert registry.get("global_gauge") is g
    print("便捷函数创建的指标在全局注册表中: True")
    
    print("\n全局注册表便捷函数测试通过!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("阶段30: 指标收集接口 — 验证测试")
    print("="*60)
    
    tests = [
        test_counter,
        test_gauge,
        test_histogram,
        test_summary,
        test_metrics_registry,
        test_prometheus_export,
        test_counter_rate,
        test_histogram_with_labels,
        test_metric_base_class,
        test_global_registry,
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
