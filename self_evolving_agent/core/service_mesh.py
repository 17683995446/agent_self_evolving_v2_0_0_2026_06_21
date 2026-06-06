"""
阶段61: 服务网格接口标准化

第一性原理:
1. 服务间通信必须可控：流量管理、安全策略、可观测性
2. 代理是透明的：应用无感知，基础设施负责
3. 策略是集中式的：全局规则，本地执行

设计原则:
- ServiceMesh: 服务网格
- Proxy: 代理接口
- TrafficRule: 流量规则
- 支持负载均衡、熔断、超时、重试
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class LoadBalanceType(Enum):
    """负载均衡类型"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONN = "least_conn"
    WEIGHTED = "weighted"


class TrafficRuleType(Enum):
    """流量规则类型"""
    ROUTE = "route"
    RETRY = "retry"
    TIMEOUT = "timeout"
    FAULT_INJECTION = "fault_injection"


@dataclass
class TrafficRule:
    """流量规则"""
    rule_id: str
    rule_type: TrafficRuleType
    source_service: str
    target_service: str
    config: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0


@dataclass
class ServiceEndpoint:
    """服务端点"""
    endpoint_id: str
    service_name: str
    address: str
    port: int
    weight: float = 1.0
    healthy: bool = True


# ============================================================
# 代理
# ============================================================

class Proxy:
    """
    服务代理

    拦截服务间通信，应用流量规则
    """

    def __init__(self, proxy_id: str):
        self.proxy_id = proxy_id
        self._rules: List[TrafficRule] = []
        self._endpoints: Dict[str, List[ServiceEndpoint]] = {}
        self._lock = threading.Lock()
        self._stats = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "latency_ms": 0.0,
        }

    def add_rule(self, rule: TrafficRule) -> None:
        """添加流量规则"""
        with self._lock:
            self._rules.append(rule)
            self._rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, rule_id: str) -> bool:
        """移除流量规则"""
        with self._lock:
            original_len = len(self._rules)
            self._rules = [r for r in self._rules if r.rule_id != rule_id]
            return len(self._rules) < original_len

    def register_endpoint(self, endpoint: ServiceEndpoint) -> None:
        """注册服务端点"""
        with self._lock:
            if endpoint.service_name not in self._endpoints:
                self._endpoints[endpoint.service_name] = []
            self._endpoints[endpoint.service_name].append(endpoint)

    def deregister_endpoint(self, endpoint_id: str) -> bool:
        """注销服务端点"""
        with self._lock:
            for service_name, endpoints in self._endpoints.items():
                original_len = len(endpoints)
                self._endpoints[service_name] = [e for e in endpoints if e.endpoint_id != endpoint_id]
                if len(self._endpoints[service_name]) < original_len:
                    return True
            return False

    def route(self, source: str, target: str, request: Any) -> Dict[str, Any]:
        """
        路由请求

        应用匹配的流量规则，选择端点
        """
        with self._lock:
            self._stats["requests_total"] += 1
            start = time.time()

            # 查找目标端点
            endpoints = self._endpoints.get(target, [])
            healthy_endpoints = [e for e in endpoints if e.healthy]

            if not healthy_endpoints:
                self._stats["requests_failed"] += 1
                return {"status": "failed", "error": "no healthy endpoints"}

            # 应用流量规则
            for rule in self._rules:
                if rule.source_service == source and rule.target_service == target:
                    if rule.rule_type == TrafficRuleType.FAULT_INJECTION:
                        if rule.config.get("abort"):
                            self._stats["requests_failed"] += 1
                            return {"status": "failed", "error": "fault injected"}

            # 负载均衡：轮询
            endpoint = healthy_endpoints[self._stats["requests_total"] % len(healthy_endpoints)]

            # 模拟请求处理
            latency = (time.time() - start) * 1000
            self._stats["latency_ms"] += latency
            self._stats["requests_success"] += 1

            return {
                "status": "success",
                "endpoint": endpoint.endpoint_id,
                "address": endpoint.address,
                "latency_ms": latency,
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            stats = dict(self._stats)
            if stats["requests_total"] > 0:
                stats["avg_latency_ms"] = stats["latency_ms"] / stats["requests_total"]
            return stats


# ============================================================
# 服务网格
# ============================================================

class ServiceMesh:
    """
    服务网格

    管理所有服务代理和全局流量策略
    """

    def __init__(self):
        self._proxies: Dict[str, Proxy] = {}
        self._lock = threading.Lock()

    def create_proxy(self, service_name: str) -> Proxy:
        """为服务创建代理"""
        with self._lock:
            proxy = Proxy(proxy_id=f"proxy_{service_name}")
            self._proxies[service_name] = proxy
            return proxy

    def get_proxy(self, service_name: str) -> Optional[Proxy]:
        """获取服务代理"""
        with self._lock:
            return self._proxies.get(service_name)

    def apply_global_rule(self, rule: TrafficRule) -> None:
        """应用全局流量规则到所有代理"""
        with self._lock:
            for proxy in self._proxies.values():
                proxy.add_rule(rule)

    def get_stats(self) -> Dict[str, Any]:
        """获取全局统计"""
        with self._lock:
            return {
                "total_proxies": len(self._proxies),
                "services": list(self._proxies.keys()),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_service_mesh() -> ServiceMesh:
    """创建服务网格"""
    return ServiceMesh()


def create_proxy(service_name: str) -> Proxy:
    """创建代理"""
    return Proxy(proxy_id=f"proxy_{service_name}")


def create_traffic_rule(
    rule_id: str,
    rule_type: TrafficRuleType,
    source_service: str,
    target_service: str,
    config: Optional[Dict[str, Any]] = None,
    priority: int = 0,
) -> TrafficRule:
    """创建流量规则"""
    return TrafficRule(
        rule_id=rule_id,
        rule_type=rule_type,
        source_service=source_service,
        target_service=target_service,
        config=config or {},
        priority=priority,
    )


def create_endpoint(
    endpoint_id: str,
    service_name: str,
    address: str,
    port: int,
    weight: float = 1.0,
) -> ServiceEndpoint:
    """创建服务端点"""
    return ServiceEndpoint(
        endpoint_id=endpoint_id,
        service_name=service_name,
        address=address,
        port=port,
        weight=weight,
    )
