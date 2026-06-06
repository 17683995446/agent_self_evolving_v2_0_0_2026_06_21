"""
阶段36: 限流接口标准化

第一性原理:
1. 系统的承载能力有上限，超过上限的请求将导致服务质量下降甚至崩溃
2. 限流是对系统边界的保护，必须可配置、可观测、可降级
3. 限流算法决定公平性和精确性

设计原则:
- 支持多种算法：令牌桶、漏桶、固定窗口、滑动窗口
- 支持分级限流：全局/用户/接口
- 支持降级策略：拒绝/排队/降级
- 可观测：当前速率、限流次数、等待时间
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional
from enum import Enum
from datetime import datetime
import threading
import time


class RateLimitAlgorithm(Enum):
    """限流算法"""
    TOKEN_BUCKET = "token_bucket"       # 令牌桶
    LEAKY_BUCKET = "leaky_bucket"       # 漏桶
    FIXED_WINDOW = "fixed_window"       # 固定窗口
    SLIDING_WINDOW = "sliding_window"   # 滑动窗口


class RateLimitAction(Enum):
    """限流触发后的动作"""
    REJECT = "reject"           # 直接拒绝
    WAIT = "wait"               # 等待
    DOWNGRADE = "downgrade"     # 降级


@dataclass
class RateLimitResult:
    """限流检查结果"""
    allowed: bool
    tokens_remaining: float
    retry_after_ms: float = 0.0
    action: RateLimitAction = RateLimitAction.REJECT


# ============================================================
# 限流器接口
# ============================================================

class RateLimiter:
    """
    限流器接口

    第一性原理：限流是对请求速率的约束，必须有明确的语义和实现
    """

    def acquire(self, tokens: float = 1.0) -> RateLimitResult:
        """
        尝试获取令牌

        Args:
            tokens: 请求的令牌数

        Returns:
            限流结果
        """
        raise NotImplementedError

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        raise NotImplementedError


# ============================================================
# 令牌桶限流器
# ============================================================

class TokenBucketRateLimiter(RateLimiter):
    """
    令牌桶限流器

    以固定速率生成令牌，请求消耗令牌。允许突发流量。
    """

    def __init__(self, rate_per_second: float, burst_size: float):
        self.rate_per_second = rate_per_second
        self.burst_size = burst_size

        self._tokens = burst_size
        self._last_update = time.time()
        self._total_requests = 0
        self._rejected_requests = 0
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> RateLimitResult:
        with self._lock:
            self._total_requests += 1
            now = time.time()
            elapsed = now - self._last_update

            # 补充令牌
            self._tokens = min(
                self.burst_size,
                self._tokens + elapsed * self.rate_per_second
            )
            self._last_update = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return RateLimitResult(
                    allowed=True,
                    tokens_remaining=self._tokens,
                )

            # 计算需要等待多久
            tokens_needed = tokens - self._tokens
            wait_ms = (tokens_needed / self.rate_per_second) * 1000
            self._rejected_requests += 1

            return RateLimitResult(
                allowed=False,
                tokens_remaining=self._tokens,
                retry_after_ms=wait_ms,
            )

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "algorithm": "token_bucket",
                "rate_per_second": self.rate_per_second,
                "burst_size": self.burst_size,
                "tokens": self._tokens,
                "total_requests": self._total_requests,
                "rejected_requests": self._rejected_requests,
                "rejection_rate": (self._rejected_requests / self._total_requests
                                   if self._total_requests > 0 else 0.0),
            }


# ============================================================
# 固定窗口限流器
# ============================================================

class FixedWindowRateLimiter(RateLimiter):
    """
    固定窗口限流器

    每个时间窗口内允许固定数量的请求。
    """

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

        self._current_window = int(time.time() / window_seconds)
        self._current_count = 0
        self._total_requests = 0
        self._rejected_requests = 0
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> RateLimitResult:
        with self._lock:
            self._total_requests += 1
            now = time.time()
            window = int(now / self.window_seconds)

            if window != self._current_window:
                self._current_window = window
                self._current_count = 0

            if self._current_count < self.max_requests:
                self._current_count += 1
                remaining = self.max_requests - self._current_count
                return RateLimitResult(
                    allowed=True,
                    tokens_remaining=remaining,
                )

            # 计算下个窗口开始时间
            next_window = (window + 1) * self.window_seconds
            wait_ms = (next_window - now) * 1000
            self._rejected_requests += 1

            return RateLimitResult(
                allowed=False,
                tokens_remaining=0,
                retry_after_ms=wait_ms,
            )

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "algorithm": "fixed_window",
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "current_count": self._current_count,
                "total_requests": self._total_requests,
                "rejected_requests": self._rejected_requests,
            }


# ============================================================
# 滑动窗口限流器
# ============================================================

class SlidingWindowRateLimiter(RateLimiter):
    """
    滑动窗口限流器

    记录每个请求的时间戳，精确控制窗口内的请求数。
    """

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

        self._requests: List[float] = []
        self._total_requests = 0
        self._rejected_requests = 0
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> RateLimitResult:
        with self._lock:
            self._total_requests += 1
            now = time.time()
            window_start = now - self.window_seconds

            # 清理过期请求
            self._requests = [t for t in self._requests if t > window_start]

            if len(self._requests) < self.max_requests:
                self._requests.append(now)
                remaining = self.max_requests - len(self._requests)
                return RateLimitResult(
                    allowed=True,
                    tokens_remaining=remaining,
                )

            # 计算最早请求何时滑出窗口
            earliest = self._requests[0]
            wait_ms = (earliest + self.window_seconds - now) * 1000
            self._rejected_requests += 1

            return RateLimitResult(
                allowed=False,
                tokens_remaining=0,
                retry_after_ms=max(0, wait_ms),
            )

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            active = len([t for t in self._requests if t > window_start])
            return {
                "algorithm": "sliding_window",
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "current_requests": active,
                "total_requests": self._total_requests,
                "rejected_requests": self._rejected_requests,
            }


# ============================================================
# 分级限流管理器
# ============================================================

class TieredRateLimiter:
    """
    分级限流管理器

    支持多个层级的限流：全局、用户、接口等
    """

    def __init__(self):
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock = threading.Lock()

    def register(self, name: str, limiter: RateLimiter) -> None:
        """注册限流器"""
        with self._lock:
            self._limiters[name] = limiter

    def acquire(self, names: List[str], tokens: float = 1.0) -> Dict[str, RateLimitResult]:
        """
        在多个层级获取许可

        所有层级都通过才算成功
        """
        results = {}
        all_allowed = True

        for name in names:
            limiter = self._limiters.get(name)
            if limiter:
                result = limiter.acquire(tokens)
                results[name] = result
                if not result.allowed:
                    all_allowed = False
            else:
                results[name] = RateLimitResult(allowed=True, tokens_remaining=float('inf'))

        return results

    def acquire_all(self, tokens: float = 1.0) -> Dict[str, RateLimitResult]:
        """在所有层级获取许可"""
        with self._lock:
            names = list(self._limiters.keys())
        return self.acquire(names, tokens)

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有层级统计"""
        with self._lock:
            return {name: limiter.get_stats() for name, limiter in self._limiters.items()}


# ============================================================
# 便捷函数
# ============================================================

def create_rate_limiter(algorithm: RateLimitAlgorithm, **kwargs) -> RateLimiter:
    """创建限流器"""
    if algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
        return TokenBucketRateLimiter(
            rate_per_second=kwargs.get('rate_per_second', 10.0),
            burst_size=kwargs.get('burst_size', 20.0),
        )
    elif algorithm == RateLimitAlgorithm.FIXED_WINDOW:
        return FixedWindowRateLimiter(
            max_requests=kwargs.get('max_requests', 100),
            window_seconds=kwargs.get('window_seconds', 60.0),
        )
    elif algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
        return SlidingWindowRateLimiter(
            max_requests=kwargs.get('max_requests', 100),
            window_seconds=kwargs.get('window_seconds', 60.0),
        )
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
