import sys
sys.path.insert(0, '/workspace')

import time
import threading
from self_evolving_agent.core.async_tasks import AsyncTaskExecutor, TaskPriority

executor = AsyncTaskExecutor(max_threads=1)
results = []
lock = threading.Lock()

def make_task(n, delay):
    def task():
        time.sleep(delay)
        with lock:
            results.append(n)
        return n
    return task

f1 = executor.submit(make_task(1, 0.05), priority=TaskPriority.LOW)
time.sleep(0.01)
f2 = executor.submit(make_task(2, 0.05), priority=TaskPriority.CRITICAL)

f1.result(timeout_ms=3000)
f2.result(timeout_ms=3000)

print("results:", results)
executor.shutdown()
