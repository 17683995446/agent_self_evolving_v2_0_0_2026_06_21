"""
阶段143: HTTP API端到端示例

本示例演示如何通过HTTP API与Agent系统交互，覆盖阶段134-142的所有API端点。

运行方式:
    1. 先启动API服务: python main.py
    2. 运行本示例: python -m examples.api_workflow
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# 默认API地址
DEFAULT_BASE_URL = "http://localhost:8080"


class AgentAPIClient:
    """Agent HTTP API客户端"""

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session() if HAS_REQUESTS else None

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if not self.session:
            raise RuntimeError("requests库未安装")
        resp = self.session.request(method, url, **kwargs)
        return resp.json()

    # ---------- 基础API ----------

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/api/health")

    def get_state(self) -> Dict[str, Any]:
        return self._request("GET", "/api/state")

    def observe(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/api/observe", json={"state": state})

    def act(self, action: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        return self._request("POST", "/api/act", json={"action": action, "context": context or {}})

    # ---------- 多租户API（阶段142） ----------

    def list_tenants(self, state: Optional[str] = None) -> Dict[str, Any]:
        params = {"state": state} if state else {}
        return self._request("GET", "/api/tenants", params=params)

    def create_tenant(self, name: str, tenant_id: Optional[str] = None,
                      quota: Optional[Dict] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        payload = {"name": name}
        if tenant_id:
            payload["tenant_id"] = tenant_id
        if quota:
            payload["quota"] = quota
        if metadata:
            payload["metadata"] = metadata
        return self._request("POST", "/api/tenants", json=payload)

    def get_tenant(self, tenant_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/tenants/{tenant_id}")

    def update_tenant(self, tenant_id: str, **kwargs) -> Dict[str, Any]:
        return self._request("PUT", f"/api/tenants/{tenant_id}", json=kwargs)

    def delete_tenant(self, tenant_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/api/tenants/{tenant_id}")

    def suspend_tenant(self, tenant_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/api/tenants/{tenant_id}/suspend")

    def resume_tenant(self, tenant_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/api/tenants/{tenant_id}/resume")

    def terminate_tenant(self, tenant_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/api/tenants/{tenant_id}/terminate")

    def check_tenant_quota(self, tenant_id: str, resource: str = "requests_per_minute",
                           amount: int = 1) -> Dict[str, Any]:
        params = {"resource": resource, "amount": str(amount)}
        return self._request("GET", f"/api/tenants/{tenant_id}/quota", params=params)

    def get_tenant_usage(self, tenant_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/tenants/{tenant_id}/usage")

    def get_tenant_data(self, tenant_id: str, key: Optional[str] = None) -> Dict[str, Any]:
        params = {"key": key} if key else {}
        return self._request("GET", f"/api/tenants/{tenant_id}/data", params=params)

    def set_tenant_data(self, tenant_id: str, key: str, value: Any) -> Dict[str, Any]:
        return self._request("POST", f"/api/tenants/{tenant_id}/data", json={"key": key, "value": value})

    def delete_tenant_data(self, tenant_id: str, key: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/api/tenants/{tenant_id}/data/{key}")

    def execute_in_tenant(self, tenant_id: str, operation: str = "noop") -> Dict[str, Any]:
        return self._request("POST", f"/api/tenants/{tenant_id}/execute", json={"operation": operation})

    def get_tenant_stats(self) -> Dict[str, Any]:
        return self._request("GET", "/api/tenants/stats")

    # ---------- 配置API（阶段138） ----------

    def get_config(self, key: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/config/{key}")

    def set_config(self, key: str, value: Any) -> Dict[str, Any]:
        return self._request("POST", f"/api/config/{key}", json={"value": value})

    def get_all_config(self) -> Dict[str, Any]:
        return self._request("GET", "/api/config")

    def get_config_history(self, key: Optional[str] = None) -> Dict[str, Any]:
        params = {"key": key} if key else {}
        return self._request("GET", "/api/config/history", params=params)

    # ---------- 安全API（阶段139） ----------

    def list_users(self) -> Dict[str, Any]:
        return self._request("GET", "/api/security/users")

    def create_user(self, username: str, roles: Optional[list] = None) -> Dict[str, Any]:
        payload = {"username": username}
        if roles:
            payload["roles"] = roles
        return self._request("POST", "/api/security/users", json=payload)

    def get_audit_events(self, limit: int = 10) -> Dict[str, Any]:
        return self._request("GET", "/api/security/audit", params={"limit": limit})

    # ---------- 恢复API（阶段140） ----------

    def get_recovery_stats(self) -> Dict[str, Any]:
        return self._request("GET", "/api/recovery/stats")

    def get_system_health(self) -> Dict[str, Any]:
        return self._request("GET", "/api/recovery/health")

    # ---------- 基准测试API（阶段141） ----------

    def get_benchmark_results(self) -> Dict[str, Any]:
        return self._request("GET", "/api/benchmark/results")

    def get_benchmark_summary(self) -> Dict[str, Any]:
        return self._request("GET", "/api/benchmark/summary")


def example_api_workflow(base_url: str = DEFAULT_BASE_URL) -> Dict[str, Any]:
    """
    HTTP API端到端工作流示例

    演示通过HTTP API完成完整的租户管理工作流。
    """
    if not HAS_REQUESTS:
        print("[跳过] requests库未安装，无法运行HTTP API示例")
        return {"skipped": True, "reason": "requests not installed"}

    print("\n[HTTP API示例] 端到端工作流")
    print("-" * 50)

    client = AgentAPIClient(base_url)

    results = {}

    # 1. 健康检查
    try:
        health = client.health()
        results["health"] = health
        print(f"  1. 健康检查: {health.get('status', 'unknown')}")
    except Exception as e:
        print(f"  1. 健康检查失败: {e}")
        results["health_error"] = str(e)
        return results

    # 2. 创建租户
    try:
        tenant = client.create_tenant(
            name="API Demo Tenant",
            tenant_id="api_demo_tenant",
            quota={"max_requests_per_minute": 100, "max_concurrent_tasks": 5},
            metadata={"source": "api_example"},
        )
        results["tenant_created"] = tenant
        print(f"  2. 创建租户: {tenant.get('tenant_id')}")
    except Exception as e:
        print(f"  2. 创建租户失败: {e}")
        results["tenant_error"] = str(e)

    # 3. 设置租户数据
    try:
        client.set_tenant_data("api_demo_tenant", "config", {"theme": "dark"})
        data = client.get_tenant_data("api_demo_tenant", "config")
        results["tenant_data"] = data
        print(f"  3. 租户数据: {data}")
    except Exception as e:
        print(f"  3. 设置租户数据失败: {e}")

    # 4. 检查配额
    try:
        quota = client.check_tenant_quota("api_demo_tenant", "requests_per_minute")
        results["quota_check"] = quota
        print(f"  4. 配额检查: allowed={quota.get('allowed')}")
    except Exception as e:
        print(f"  4. 配额检查失败: {e}")

    # 5. 在租户作用域执行
    try:
        exec_result = client.execute_in_tenant("api_demo_tenant", "process_data")
        results["execution"] = exec_result
        print(f"  5. 租户执行: {exec_result}")
    except Exception as e:
        print(f"  5. 租户执行失败: {e}")

    # 6. 获取统计
    try:
        stats = client.get_tenant_stats()
        results["stats"] = stats
        print(f"  6. 租户统计: {stats}")
    except Exception as e:
        print(f"  6. 获取统计失败: {e}")

    # 7. 暂停与恢复
    try:
        client.suspend_tenant("api_demo_tenant")
        print(f"  7. 租户已暂停")
        client.resume_tenant("api_demo_tenant")
        print(f"     租户已恢复")
    except Exception as e:
        print(f"  7. 暂停/恢复失败: {e}")

    # 8. 清理
    try:
        client.terminate_tenant("api_demo_tenant")
        client.delete_tenant("api_demo_tenant")
        print(f"  8. 租户已清理")
    except Exception as e:
        print(f"  8. 清理失败: {e}")

    return results


if __name__ == "__main__":
    example_api_workflow()
