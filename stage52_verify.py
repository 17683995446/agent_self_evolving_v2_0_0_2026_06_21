"""
阶段52验证: 安全沙箱接口标准化
"""
import sys
import importlib.util
import time

spec = importlib.util.spec_from_file_location("sandbox", "/workspace/self_evolving_agent/core/sandbox.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["sandbox"] = mod
spec.loader.exec_module(mod)

# 顶层函数，可被pickle（用于进程沙箱）
def compute_sum():
    return sum(range(100))

def return_hello():
    return "hello from sandbox"

def sleep_two():
    time.sleep(2)

def multiply(x):
    return x * 2

def divide_by_zero():
    return 1 / 0

print("=" * 60)
print("阶段52验证: 安全沙箱接口标准化")
print("=" * 60)

# 测试1: 线程沙箱正常执行
def test_thread_sandbox_success():
    sandbox = mod.create_thread_sandbox()
    task = mod.create_task("t1", compute_sum)
    limits = mod.ResourceLimit(max_execution_time_ms=2000)
    result = sandbox.execute(task, limits)
    assert result.status == mod.SandboxStatus.COMPLETED
    assert result.output == 4950
    assert result.execution_time_ms < 2000
    print("  [test_thread_sandbox_success] 线程沙箱正常执行 OK")

# 测试2: 线程沙箱超时
def test_thread_sandbox_timeout():
    sandbox = mod.create_thread_sandbox()
    task = mod.create_task("t2", sleep_two)
    limits = mod.ResourceLimit(max_execution_time_ms=100)
    result = sandbox.execute(task, limits)
    assert result.status == mod.SandboxStatus.TIMEOUT
    assert "timeout" in result.error.lower()
    print("  [test_thread_sandbox_timeout] 线程沙箱超时 OK")

# 测试3: 线程沙箱异常捕获
def test_thread_sandbox_error():
    sandbox = mod.create_thread_sandbox()
    task = mod.create_task("t3", divide_by_zero)
    limits = mod.ResourceLimit(max_execution_time_ms=1000)
    result = sandbox.execute(task, limits)
    assert result.status == mod.SandboxStatus.ERROR
    assert result.error is not None
    print("  [test_thread_sandbox_error] 线程沙箱异常捕获 OK")

# 测试4: 进程沙箱正常执行
def test_process_sandbox_success():
    sandbox = mod.create_process_sandbox()
    task = mod.create_task("t4", return_hello)
    limits = mod.ResourceLimit(max_execution_time_ms=2000)
    result = sandbox.execute(task, limits)
    assert result.status == mod.SandboxStatus.COMPLETED
    assert result.output == "hello from sandbox"
    print("  [test_process_sandbox_success] 进程沙箱正常执行 OK")

# 测试5: 进程沙箱超时
def test_process_sandbox_timeout():
    sandbox = mod.create_process_sandbox()
    task = mod.create_task("t5", sleep_two)
    limits = mod.ResourceLimit(max_execution_time_ms=100)
    result = sandbox.execute(task, limits)
    assert result.status == mod.SandboxStatus.TIMEOUT
    print("  [test_process_sandbox_timeout] 进程沙箱超时 OK")

# 测试6: 沙箱管理器
def test_sandbox_manager():
    manager = mod.create_sandbox_manager()
    ts = mod.create_thread_sandbox()
    manager.register("thread1", ts)
    assert "thread1" in manager.list_sandboxes()

    task = mod.create_task("t6", multiply, 21)
    limits = mod.ResourceLimit(max_execution_time_ms=1000)
    result = manager.execute("thread1", task, limits)
    assert result.status == mod.SandboxStatus.COMPLETED
    assert result.output == 42
    print("  [test_sandbox_manager] 沙箱管理器 OK")

# 测试7: 资源限制默认值
def test_resource_limit_defaults():
    rl = mod.ResourceLimit()
    assert rl.max_execution_time_ms == 5000.0
    assert rl.max_memory_mb == 100.0
    assert rl.max_cpu_percent == 50.0
    assert rl.max_output_size == 10000
    print("  [test_resource_limit_defaults] 资源限制默认值 OK")

if __name__ == "__main__":
    test_thread_sandbox_success()
    test_thread_sandbox_timeout()
    test_thread_sandbox_error()
    test_process_sandbox_success()
    test_process_sandbox_timeout()
    test_sandbox_manager()
    test_resource_limit_defaults()
    print("=" * 60)
    print("阶段52验证通过 ✓")
    print("=" * 60)
