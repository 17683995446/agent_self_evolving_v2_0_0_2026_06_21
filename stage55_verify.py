"""
阶段55验证: 边缘计算接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("ec", "/workspace/self_evolving_agent/core/edge_computing.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["ec"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段55验证: 边缘计算接口标准化")
print("=" * 60)

# 测试1: 创建设备
def test_create_device():
    device = mod.create_edge_device("dev1", cpu=4, memory=8)
    assert device.device_id == "dev1"
    assert device.get_status() == mod.DeviceStatus.ONLINE
    print("  [test_create_device] 创建设备 OK")

# 测试2: 部署和卸载
def test_deploy_undeploy():
    device = mod.create_edge_device("dev2")
    dep = mod.EdgeDeployment(model_id="model_v1", compressed=True, max_memory_mb=32)
    assert device.deploy(dep) is True
    assert "model_v1" in device.get_deployments()
    assert device.undeploy("model_v1") is True
    assert "model_v1" not in device.get_deployments()
    print("  [test_deploy_undeploy] 部署卸载 OK")

# 测试3: 任务提交和执行
def test_task_execution():
    device = mod.create_edge_device("dev3")
    task = mod.create_edge_task("t1", lambda x: x * 2, 21)
    assert device.submit_task(task) is True
    result = device.execute_next()
    assert result is not None
    assert result["status"] == "success"
    assert result["result"] == 42
    print("  [test_task_execution] 任务执行 OK")

# 测试4: 任务优先级
def test_task_priority():
    device = mod.create_edge_device("dev4")
    t1 = mod.EdgeTask(task_id="t1", fn=lambda: 1, priority=mod.TaskPriority.NORMAL)
    t2 = mod.EdgeTask(task_id="t2", fn=lambda: 2, priority=mod.TaskPriority.CRITICAL)
    t3 = mod.EdgeTask(task_id="t3", fn=lambda: 3, priority=mod.TaskPriority.HIGH)
    device.submit_task(t1)
    device.submit_task(t2)
    device.submit_task(t3)

    r1 = device.execute_next()
    r2 = device.execute_next()
    r3 = device.execute_next()
    assert r1["result"] == 2  # CRITICAL first
    assert r2["result"] == 3  # HIGH second
    assert r3["result"] == 1  # NORMAL last
    print("  [test_task_priority] 任务优先级 OK")

# 测试5: 离线设备拒绝任务
def test_offline_reject():
    device = mod.create_edge_device("dev5")
    device.set_status(mod.DeviceStatus.OFFLINE)
    task = mod.create_edge_task("t1", lambda: 1)
    assert device.submit_task(task) is False
    print("  [test_offline_reject] 离线拒绝 OK")

# 测试6: 注册中心调度
def test_registry_dispatch():
    registry = mod.create_edge_registry()
    d1 = mod.create_edge_device("edge1")
    d2 = mod.create_edge_device("edge2")
    registry.register(d1)
    registry.register(d2)

    task = mod.create_edge_task("t1", lambda: "done")
    assigned = registry.dispatch_task(task, strategy="round_robin")
    assert assigned in ("edge1", "edge2")

    stats = registry.get_stats()
    assert stats["total_devices"] == 2
    assert stats["online"] == 2
    print("  [test_registry_dispatch] 注册中心调度 OK")

# 测试7: 设备统计
def test_device_stats():
    device = mod.create_edge_device("dev6")
    device.submit_task(mod.create_edge_task("t1", lambda: 1))
    device.execute_next()
    stats = device.get_stats()
    assert stats["tasks_executed"] == 1
    assert stats["queue_length"] == 0
    print("  [test_device_stats] 设备统计 OK")

if __name__ == "__main__":
    test_create_device()
    test_deploy_undeploy()
    test_task_execution()
    test_task_priority()
    test_offline_reject()
    test_registry_dispatch()
    test_device_stats()
    print("=" * 60)
    print("阶段55验证通过 ✓")
    print("=" * 60)
