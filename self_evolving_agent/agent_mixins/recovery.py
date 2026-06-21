"""错误恢复Mixin — 阶段149从agent.py拆分"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from ..core.recovery import RecoveryStrategy, ErrorContext, HealthCheckResult


class RecoveryMixin:
    """错误恢复接口（阶段140）"""

    def execute_with_recovery(
        self,
        operation: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> Tuple[Any, Optional[ErrorContext]]:
        """带恢复策略执行操作（阶段140新增）"""
        return self._recovery.execute(operation, func, *args, **kwargs)

    def register_recovery_strategy(self, strategy: RecoveryStrategy) -> None:
        """注册恢复策略（阶段140新增）"""
        self._recovery.register_strategy(strategy)

    def get_recovery_strategy(self, name: str) -> Optional[RecoveryStrategy]:
        """获取恢复策略（阶段140新增）"""
        return self._recovery.get_strategy(name)

    def get_error_history(self, component: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取错误历史（阶段140新增）"""
        return self._recovery.get_error_history(component=component, limit=limit)

    def get_error_count(self, component: Optional[str] = None) -> int:
        """获取错误数（阶段140新增）"""
        return self._recovery.get_error_count(component)

    def clear_errors(self) -> None:
        """清空错误历史（阶段140新增）"""
        self._recovery.clear_errors()

    def register_health_check(
        self,
        component: str,
        check_func: Callable[[], HealthCheckResult],
    ) -> None:
        """注册健康检查（阶段140新增）"""
        self._recovery.register_health_check(component, check_func)

    def check_recovery_health(self, component: Optional[str] = None) -> Dict[str, Any]:
        """检查恢复健康状态（阶段140新增）"""
        return self._recovery.check_health(component)

    def get_system_health(self) -> Dict[str, Any]:
        """获取系统整体健康状态（阶段140新增）"""
        return self._recovery.get_system_health()

    def get_recovery_stats(self) -> Dict[str, Any]:
        """获取恢复统计（阶段140新增）"""
        return self._recovery.get_stats()

    def start_health_monitoring(self) -> None:
        """启动健康监控（阶段140新增）"""
        self._recovery.start_health_monitoring()

    def stop_health_monitoring(self) -> None:
        """停止健康监控（阶段140新增）"""
        self._recovery.stop_health_monitoring()
