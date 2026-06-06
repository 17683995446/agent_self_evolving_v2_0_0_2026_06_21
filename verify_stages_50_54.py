"""
验证阶段50-54: 多租户、审计日志、安全沙箱、数据版本控制、联邦学习
"""
import sys
import importlib.util
import time

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

mt = load_module("multi_tenant", "/workspace/self_evolving_agent/core/multi_tenant.py")
al = load_module("audit_log", "/workspace/self_evolving_agent/core/audit_log.py")
sb = load_module("sandbox", "/workspace/self_evolving_agent/core/sandbox.py")
dv = load_module("data_versioning", "/workspace/self_evolving_agent/core/data_versioning.py")
fl = load_module("federated_learning", "/workspace/self_evolving_agent/core/federated_learning.py")

print("=" * 60)
print("验证阶段50-54")
print("=" * 60)

# 阶段50: 多租户
def test_stage50():
    manager = mt.create_tenant_manager()
    manager.create_tenant("ta", "租户A", region="cn")
    manager.set_quota("ta", "cpu", 100.0)
    assert manager.get_quota("ta", "cpu") == 100.0
    mt.TenantContext.set_current_tenant("ta")
    assert mt.TenantContext.get_current_tenant_id() == "ta"
    mt.TenantContext.clear()
    assert mt.TenantContext.get_current_tenant_id() is None
    print("  [阶段50] 多租户 OK")

# 阶段51: 审计日志
def test_stage51():
    log = al.create_audit_log()
    e1 = log.log("alice", al.AuditAction.CREATE, "m1", al.AuditResult.SUCCESS)
    e2 = log.log("bob", al.AuditAction.UPDATE, "m1", al.AuditResult.SUCCESS)
    assert log.verify_integrity() is True
    assert e2.previous_hash == e1.current_hash
    assert len(log.query(user_id="alice")) == 1
    log._events[0].current_hash = "bad"
    assert log.verify_integrity() is False
    print("  [阶段51] 审计日志 OK")

# 阶段52: 安全沙箱
def compute_sum():
    return sum(range(100))

def sleep_short():
    time.sleep(2)

def test_stage52():
    ts = sb.create_thread_sandbox()
    task = sb.create_task("t1", compute_sum)
    limits = sb.ResourceLimit(max_execution_time_ms=2000)
    r = ts.execute(task, limits)
    assert r.status == sb.SandboxStatus.COMPLETED
    assert r.output == 4950

    task2 = sb.create_task("t2", sleep_short)
    limits2 = sb.ResourceLimit(max_execution_time_ms=100)
    r2 = ts.execute(task2, limits2)
    assert r2.status == sb.SandboxStatus.TIMEOUT
    print("  [阶段52] 安全沙箱 OK")

# 阶段53: 数据版本控制
def test_stage53():
    ds = dv.create_versioned_dataset("ds1")
    v1 = ds.commit([1, 2], author="alice", comment="init")
    v2 = ds.commit([1, 2, 3], author="bob", comment="add")
    assert ds.get_current_version().version_id == v2.version_id
    assert ds.checkout(v1.version_id) == [1, 2]
    ds.rollback(v1.version_id)
    assert ds.get_current_version().version_id == v1.version_id
    diff = ds.diff(v1.version_id, v2.version_id)
    assert diff["same"] is False
    print("  [阶段53] 数据版本控制 OK")

# 阶段54: 联邦学习
def test_stage54():
    server = fl.create_federated_server(fl.AggregationStrategyType.FEDAVG)
    c1 = fl.create_federated_client("c1")
    c2 = fl.create_federated_client("c2")
    server.register_client(c1)
    server.register_client(c2)
    result = server.run_round(min_clients=2)
    assert result["status"] == "completed"
    assert result["updates_received"] == 2
    stats = server.get_stats()
    assert stats["current_round"] == 1
    print("  [阶段54] 联邦学习 OK")

if __name__ == "__main__":
    test_stage50()
    test_stage51()
    test_stage52()
    test_stage53()
    test_stage54()
    print("=" * 60)
    print("阶段50-54全部验证通过 ✓")
    print("=" * 60)
