"""
阶段37: 重试接口标准化

第一性原理:
1. 分布式系统中故障是常态而非异常
2. 重试是对瞬态故障的恢复机制，但必须有策略：退避、上限、可观测
3. 无限制的重试会放大故障，形成雪崩

设计原则:
- 可配置重试策略：固定间隔、线性退避、指数退避
- 可配置重试条件：哪些异常可重试
- 可配置最大重试次数和总超时
- 可观测：重试次数、成功率、延迟分布
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional, Type, Tuple
from enum import Enum
from datetime import datetime
import threading
import time
import random


class BackoffStrategy(Enum):
    """退避策略"""
    FIXED = "fixed"                 # 固定间隔
    LINEAR = "linear"               # 线性增加
    EXPONENTIAL = "exponential"     # 指数退避
    JITTER = "jitter"               # 带抖动的指数退避


@dataclass
class RetryResult:
    """重试结果"""
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    attempts: int = 0
    total_time_ms: float = 0.0
    last_error: Optional[str] = None


# ============================================================
# 重试策略
# ============================================================

class RetryPolicy:
    """
    重试策略

    第一性原理：重试必须有明确的边界和规则
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay_ms: float = 100.0,
        max_delay_ms: float = 30000.0,
        backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
        total_timeout_ms: Optional[float] = None,
    ):
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.backoff_strategy = backoff_strategy
        self.retryable_exceptions = retryable_exceptions or [Exception]
        self.total_timeout_ms = total_timeout_ms

    def is_retryable(self, exception: Exception) -> bool:
        """判断异常是否可重试"""
        return any(isinstance(exception, exc_type) for exc_type in self.retryable_exceptions)

    def calculate_delay(self, attempt: int) -> float:
        """
        计算第attempt次重试的延迟（毫秒）

        attempt从0开始：0表示第一次重试
        """
        if self.backoff_strategy == BackoffStrategy.FIXED:
            delay = self.base_delay_ms
        elif self.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.base_delay_ms * (attempt + 1)
        elif self.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.base_delay_ms * (2 ** attempt)
        elif self.backoff_strategy == BackoffStrategy.JITTER:
            base = self.base_delay_ms * (2 ** attempt)
            delay = base * (0.5 + random.random())  # 50%-150%抖动
        else:
            delay = self.base_delay_ms

        return min(delay, self.max_delay_ms)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_retries": self.max_retries,
            "base_delay_ms": self.base_delay_ms,
            "max_delay_ms": self.max_delay_ms,
            "backoff_strategy": self.backoff_strategy.value,
            "retryable_exceptions": [e.__name__ for e in self.retryable_exceptions],
            "total_timeout_ms": self.total_timeout_ms,
        }


# ============================================================
# 重试执行器
# ============================================================

class RetryExecutor:
    """
    重试执行器

    执行带重试策略的操作
    """

    def __init__(self, policy: RetryPolicy):
        self.policy = policy
        self._total_attempts = 0
        self._total_successes = 0
        self._total_failures = 0
        self._stats_lock = threading.Lock()

    def execute(self, operation: Callable, *args, **kwargs) -> RetryResult:
        """
        执行操作，带重试

        Args:
            operation: 要执行的操作
            *args, **kwargs: 传递给操作的参数

        Returns:
            重试结果
        """
        start = time.time()
        last_error = None
        actual_attempts = 0

        for attempt in range(self.policy.max_retries + 1):
            with self._stats_lock:
                self._total_attempts += 1
            actual_attempts += 1

            try:
                result = operation(*args, **kwargs)
                with self._stats_lock:
                    self._total_successes += 1
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=actual_attempts,
                    total_time_ms=(time.time() - start) * 1000,
                )
            except Exception as e:
                last_error = e

                # 最后一次尝试或不可重试
                if attempt >= self.policy.max_retries:
                    break
                if not self.policy.is_retryable(e):
                    break

                # 检查总超时
                if self.policy.total_timeout_ms is not None:
                    elapsed_ms = (time.time() - start) * 1000
                    if elapsed_ms >= self.policy.total_timeout_ms:
                        break

                # 等待后重试
                delay_ms = self.policy.calculate_delay(attempt)
                time.sleep(delay_ms / 1000.0)

        with self._stats_lock:
            self._total_failures += 1

        return RetryResult(
            success=False,
            error=last_error,
            attempts=actual_attempts,
            total_time_ms=(time.time() - start) * 1000,
            last_error=str(last_error) if last_error else None,
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            return {
                "total_attempts": self._total_attempts,
                "total_successes": self._total_successes,
                "total_failures": self._total_failures,
                "success_rate": (self._total_successes / self._total_attempts
                                if self._total_attempts > 0 else 0.0),
            }


# ============================================================
# 重试装饰器
# ============================================================

def retryable(policy: Optional[RetryPolicy] = None):
    """
    重试装饰器

    自动为函数添加重试逻辑
    """
    if policy is None:
        policy = RetryPolicy()

    def decorator(func: Callable) -> Callable:
        executor = RetryExecutor(policy)

        def wrapper(*args, **kwargs):
            result = executor.execute(func, *args, **kwargs)
            if result.success:
                return result.result
            raise result.error

        wrapper._retry_executor = executor
        wrapper.get_retry_stats = executor.get_stats
        return wrapper
    return decorator


# ============================================================
# 便捷函数
# ============================================================

def with_retry(
    operation: Callable,
    max_retries: int = 3,
    base_delay_ms: float = 100.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    *args,
    **kwargs
) -> RetryResult:
    """便捷函数：带重试执行操作"""
    policy = RetryPolicy(
        max_retries=max_retries,
        base_delay_ms=base_delay_ms,
        backoff_strategy=backoff_strategy,
        retryable_exceptions=retryable_exceptions,
    )
    executor = RetryExecutor(policy)
    return executor.execute(operation, *args, **kwargs)
