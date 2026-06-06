"""
阶段39: 超时接口标准化

第一性原理:
1. 任何操作都可能无限期阻塞。没有超时机制，系统会被慢操作拖垮
2. 超时是对"等待成本"的量化：超过可接受成本就放弃
3. 超时必须可配置、可观测、可降级

设计原则:
- 支持函数级超时包装
- 支持超时后取消/中断操作
- 可配置超时策略：固定超时、动态超时、自适应超时
- 与重试、熔断协同：超时是一种失败，触发重试和熔断计数
"""

import threading
import time
import signal
import sys
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar, Generic
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError


T = TypeVar('T')


class TimeoutStrategy(Enum):
    """超时策略"""
    FIXED = "fixed"           # 固定超时
    DYNAMIC = "dynamic"       # 动态计算（基于历史耗时）
    ADAPTIVE = "adaptive"     # 自适应（基于负载调整）


class TimeoutAction(Enum):
    """超时触发动作"""
    RAISE = "raise"           # 抛出TimeoutError
    RETURN_NONE = "return_none"  # 返回None
    FALLBACK = "fallback"     # 执行降级函数


@dataclass
class TimeoutResult(Generic[T]):
    """超时执行结果"""
    success: bool
    result: Optional[T] = None
    error: Optional[Exception] = None
    timed_out: bool = False
    elapsed_ms: float = 0.0


# ============================================================
# 超时控制器
# ============================================================

class TimeoutController:
    """
    超时控制器

    第一性原理：超时是资源保护机制，必须在独立线程/上下文中监控执行时间
    """

    def __init__(
        self,
        timeout_ms: float = 5000.0,
        strategy: TimeoutStrategy = TimeoutStrategy.FIXED,
        action: TimeoutAction = TimeoutAction.RAISE,
        fallback_fn: Optional[Callable] = None,
    ):
        self.timeout_ms = timeout_ms
        self.strategy = strategy
        self.action = action
        self.fallback_fn = fallback_fn
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._total_calls = 0
        self._total_timeouts = 0
        self._total_successes = 0
        self._elapsed_history: list[float] = []
        self._lock = threading.Lock()

    def execute(self, operation: Callable[..., T], *args, **kwargs) -> TimeoutResult[T]:
        """
        执行操作，带超时控制

        Args:
            operation: 要执行的操作
            *args, **kwargs: 传递给操作的参数

        Returns:
            执行结果
        """
        start = time.time()
        self._total_calls += 1

        # 计算实际超时时间
        actual_timeout = self._calculate_timeout()

        try:
            future = self._executor.submit(operation, *args, **kwargs)
            result = future.result(timeout=actual_timeout / 1000.0)
            elapsed = (time.time() - start) * 1000

            with self._lock:
                self._total_successes += 1
                self._elapsed_history.append(elapsed)
                # 保留最近100条记录
                if len(self._elapsed_history) > 100:
                    self._elapsed_history = self._elapsed_history[-100:]

            return TimeoutResult(
                success=True,
                result=result,
                elapsed_ms=elapsed,
            )
        except FutureTimeoutError:
            elapsed = (time.time() - start) * 1000
            with self._lock:
                self._total_timeouts += 1

            return self._handle_timeout(elapsed, *args, **kwargs)
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return TimeoutResult(
                success=False,
                error=e,
                elapsed_ms=elapsed,
            )

    def _calculate_timeout(self) -> float:
        """计算实际超时时间"""
        if self.strategy == TimeoutStrategy.FIXED:
            return self.timeout_ms
        elif self.strategy == TimeoutStrategy.DYNAMIC:
            # 基于历史P90动态调整
            if len(self._elapsed_history) >= 10:
                sorted_history = sorted(self._elapsed_history)
                p90_idx = int(len(sorted_history) * 0.9)
                p90 = sorted_history[min(p90_idx, len(sorted_history) - 1)]
                return max(p90 * 2, self.timeout_ms * 0.5)
            return self.timeout_ms
        elif self.strategy == TimeoutStrategy.ADAPTIVE:
            # 基于超时率自适应调整
            if self._total_calls > 20:
                timeout_rate = self._total_timeouts / self._total_calls
                if timeout_rate > 0.1:
                    # 超时率过高，放宽超时
                    return self.timeout_ms * 1.5
                elif timeout_rate < 0.01:
                    # 超时率很低，收紧超时
                    return self.timeout_ms * 0.8
            return self.timeout_ms
        return self.timeout_ms

    def _handle_timeout(self, elapsed_ms: float, *args, **kwargs) -> TimeoutResult:
        """处理超时"""
        if self.action == TimeoutAction.RAISE:
            return TimeoutResult(
                success=False,
                error=TimeoutError(f"Operation timed out after {elapsed_ms:.1f}ms"),
                timed_out=True,
                elapsed_ms=elapsed_ms,
            )
        elif self.action == TimeoutAction.RETURN_NONE:
            return TimeoutResult(
                success=True,
                result=None,
                timed_out=True,
                elapsed_ms=elapsed_ms,
            )
        elif self.action == TimeoutAction.FALLBACK and self.fallback_fn:
            return TimeoutResult(
                success=True,
                result=self.fallback_fn(*args, **kwargs),
                timed_out=True,
                elapsed_ms=elapsed_ms,
            )
        else:
            return TimeoutResult(
                success=False,
                error=TimeoutError("Operation timed out"),
                timed_out=True,
                elapsed_ms=elapsed_ms,
            )

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            timeout_rate = (self._total_timeouts / self._total_calls
                           if self._total_calls > 0 else 0.0)
            avg_elapsed = (sum(self._elapsed_history) / len(self._elapsed_history)
                          if self._elapsed_history else 0.0)
            return {
                "total_calls": self._total_calls,
                "total_timeouts": self._total_timeouts,
                "total_successes": self._total_successes,
                "timeout_rate": timeout_rate,
                "avg_elapsed_ms": avg_elapsed,
                "strategy": self.strategy.value,
                "timeout_ms": self.timeout_ms,
            }

    def shutdown(self) -> None:
        """关闭执行器"""
        self._executor.shutdown(wait=False)


# ============================================================
# 超时装饰器
# ============================================================

def timeout_protected(
    timeout_ms: float = 5000.0,
    action: TimeoutAction = TimeoutAction.RAISE,
    fallback_fn: Optional[Callable] = None,
):
    """
    超时保护装饰器

    自动为函数添加超时控制
    """
    controller = TimeoutController(
        timeout_ms=timeout_ms,
        action=action,
        fallback_fn=fallback_fn,
    )

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            result = controller.execute(func, *args, **kwargs)
            if result.success:
                return result.result
            raise result.error

        wrapper._timeout_controller = controller
        wrapper.get_timeout_stats = controller.get_stats
        return wrapper
    return decorator


# ============================================================
# 便捷函数
# ============================================================

def with_timeout(
    operation: Callable[..., T],
    timeout_ms: float,
    *args,
    **kwargs
) -> TimeoutResult[T]:
    """为单次操作添加超时"""
    controller = TimeoutController(timeout_ms=timeout_ms)
    try:
        return controller.execute(operation, *args, **kwargs)
    finally:
        controller.shutdown()


def create_timeout_controller(**kwargs) -> TimeoutController:
    """创建超时控制器"""
    return TimeoutController(**kwargs)
