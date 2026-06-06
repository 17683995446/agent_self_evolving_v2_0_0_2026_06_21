import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.circuit_breaker import CircuitBreaker, CircuitState
import time

cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout_ms=100)

for i in range(3):
    cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

time.sleep(0.15)

# 第一次成功
result = cb.call(lambda: "success")
print(f"第一次: success={result.success}, state={result.state}, current={cb.state}")
print(f"  stats: success_count={cb.get_stats()['success_count']}, half_open_calls={cb._half_open_calls}")

# 第二次成功
result = cb.call(lambda: "success")
print(f"第二次: success={result.success}, state={result.state}, current={cb.state}")
print(f"  stats: success_count={cb.get_stats()['success_count']}, half_open_calls={cb._half_open_calls}")
