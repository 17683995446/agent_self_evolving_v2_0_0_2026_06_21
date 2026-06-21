"""生产部署Mixin — 阶段149从agent.py拆分"""

from typing import Any, Dict

from ..core.production import HealthResponse, CircuitBreaker


class ProductionMixin:
    """生产部署接口（阶段133）"""

    def start_production(self) -> bool:
        """启动生产模式（阶段133新增）"""
        return self._production.start()

    def stop_production(self) -> bool:
        """停止生产模式（阶段133新增）"""
        return self._production.stop()

    def get_production_status(self) -> Dict[str, Any]:
        """获取生产状态（阶段133新增）"""
        return self._production.status()

    def production_health_check(self) -> HealthResponse:
        """生产健康检查（阶段133新增）"""
        return self._production.health_check()

    def production_liveness(self) -> HealthResponse:
        """生产存活探针（阶段133新增）"""
        return self._production.liveness()

    def production_readiness(self) -> HealthResponse:
        """生产就绪探针（阶段133新增）"""
        return self._production.readiness()

    def check_rate_limit(self) -> bool:
        """检查限流（阶段133新增）"""
        return self._production.check_request_allowed()

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """获取熔断器（阶段133新增）"""
        return self._production.get_circuit_breaker(name)

    def set_resource_quota(self, name: str, limit: int) -> None:
        """设置资源配额（阶段133新增）"""
        self._production.resource_manager.set_quota(name, limit)

    def acquire_resource(self, name: str, amount: int = 1) -> bool:
        """获取资源（阶段133新增）"""
        return self._production.resource_manager.acquire(name, amount)

    def release_resource(self, name: str, amount: int = 1) -> None:
        """释放资源（阶段133新增）"""
        self._production.resource_manager.release(name, amount)
