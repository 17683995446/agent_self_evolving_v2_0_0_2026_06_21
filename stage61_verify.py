"""
阶段61验证: 服务网格接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("sm", "/workspace/self_evolving_agent/core/service_mesh.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["sm"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段61验证: 服务网格接口标准化")
print("=" * 60)

# 测试1: 创建代理和端点
def test_proxy_endpoint():
    proxy = mod.create_proxy("svc_a")
    ep = mod.create_endpoint("ep1", "svc_b", "10.0.0.1", 8080)
    proxy.register_endpoint(ep)

    result = proxy.route("svc_a", "svc_b", {"data": "test"})
    assert result["status"] == "success"
    assert result["endpoint"] == "ep1"
    print("  [test_proxy_endpoint] 代理端点 OK")

# 测试2: 流量规则
def test_traffic_rule():
    proxy = mod.create_proxy("svc_c")
    ep = mod.create_endpoint("ep2", "svc_d", "10.0.0.2", 9090)
    proxy.register_endpoint(ep)

    rule = mod.create_traffic_rule("r1", mod.TrafficRuleType.FAULT_INJECTION, "svc_c", "svc_d", config={"abort": True})
    proxy.add_rule(rule)

    result = proxy.route("svc_c", "svc_d", {})
    assert result["status"] == "failed"
    assert "fault" in result["error"]
    print("  [test_traffic_rule] 流量规则 OK")

# 测试3: 服务网格全局规则
def test_service_mesh_global():
    mesh = mod.create_service_mesh()
    mesh.create_proxy("svc1")
    mesh.create_proxy("svc2")

    rule = mod.create_traffic_rule("global", mod.TrafficRuleType.RETRY, "*", "*")
    mesh.apply_global_rule(rule)

    stats = mesh.get_stats()
    assert stats["total_proxies"] == 2
    print("  [test_service_mesh_global] 全局规则 OK")

# 测试4: 无健康端点
def test_no_healthy_endpoints():
    proxy = mod.create_proxy("svc_e")
    ep = mod.create_endpoint("ep3", "svc_f", "10.0.0.3", 8080, weight=1.0)
    ep.healthy = False
    proxy.register_endpoint(ep)

    result = proxy.route("svc_e", "svc_f", {})
    assert result["status"] == "failed"
    print("  [test_no_healthy_endpoints] 无健康端点 OK")

# 测试5: 代理统计
def test_proxy_stats():
    proxy = mod.create_proxy("svc_g")
    ep = mod.create_endpoint("ep4", "svc_h", "10.0.0.4", 8080)
    proxy.register_endpoint(ep)

    for _ in range(5):
        proxy.route("svc_g", "svc_h", {})

    stats = proxy.get_stats()
    assert stats["requests_total"] == 5
    assert stats["requests_success"] == 5
    print("  [test_proxy_stats] 代理统计 OK")

# 测试6: 规则优先级
def test_rule_priority():
    proxy = mod.create_proxy("svc_i")
    rule1 = mod.create_traffic_rule("r1", mod.TrafficRuleType.ROUTE, "svc_i", "svc_j", priority=1)
    rule2 = mod.create_traffic_rule("r2", mod.TrafficRuleType.ROUTE, "svc_i", "svc_j", priority=5)
    proxy.add_rule(rule1)
    proxy.add_rule(rule2)

    assert proxy._rules[0].rule_id == "r2"  # higher priority first
    print("  [test_rule_priority] 规则优先级 OK")

if __name__ == "__main__":
    test_proxy_endpoint()
    test_traffic_rule()
    test_service_mesh_global()
    test_no_healthy_endpoints()
    test_proxy_stats()
    test_rule_priority()
    print("=" * 60)
    print("阶段61验证通过 ✓")
    print("=" * 60)
