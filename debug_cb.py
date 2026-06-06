import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.circuit_breaker import CircuitBreaker, CircuitState
import time

cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout_ms=100, success_threshold=1)

print("初始状态:", cb.state)

for i in range(3):
    result = cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
    print(f"  失败{i+1}: state={cb.state}, failure_count={cb.get_stats()['failure_count']}")

print("等待恢复超时...")
time.sleep(0.15)

print("调用成功操作...")
result = cb.call(lambda: "success")
print(f"  结果: success={result.success}, state={result.state}, current={cb.state}")
print(f"  stats: success_count={cb.get_stats()['success_count']}, half_open_calls={cb._half_open_calls}")
