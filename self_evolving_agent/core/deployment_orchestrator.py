"""
阶段60: 部署编排接口标准化

第一性原理:
1. 部署是交付的最终环节：代码必须能稳定运行在生产环境
2. 编排是资源的最优分配：服务应该运行在最适合的节点上
3. 回滚是安全的底线：新版本失败时必须能立即恢复

设计原则:
- Deployment: 部署定义
- DeploymentStrategy: 部署策略（滚动/蓝绿/金丝雀）
- Orchestrator: 编排器
- ServiceInstance: 服务实例
- 支持健康检查、自动扩缩容、优雅停机
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class DeploymentStrategyType(Enum):
    """部署策略类型"""
    ROLLING = "rolling"           # 滚动更新
    BLUE_GREEN = "blue_green"     # 蓝绿部署
    CANARY = "canary"             # 金丝雀发布
    RECREATE = "recreate"         # 重建


class InstanceStatus(Enum):
    """实例状态"""
    PENDING = "pending"
    RUNNING = "running"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    TERMINATING = "terminating"
    STOPPED = "stopped"


@dataclass
class ServiceInstance:
    """服务实例"""
    instance_id: str
    service_name: str
    version: str
    node_id: str
    status: InstanceStatus = InstanceStatus.PENDING
    start_time: float = field(default_factory=time.time)
    health_checks: int = 0
    failed_checks: int = 0


@dataclass
class Deployment:
    """部署定义"""
    deployment_id: str
    service_name: str
    version: str
    strategy: DeploymentStrategyType
    replicas: int = 1
    config: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 部署策略
# ============================================================

class DeploymentStrategy:
    """部署策略基类"""

    def execute(self, deployment: Deployment, instances: List[ServiceInstance]) -> List[ServiceInstance]:
        """执行部署策略"""
        raise NotImplementedError


class RollingStrategy(DeploymentStrategy):
    """滚动更新策略"""

    def execute(self, deployment: Deployment, instances: List[ServiceInstance]) -> List[ServiceInstance]:
        """逐个替换实例"""
        new_instances = []
        for i in range(deployment.replicas):
            instance = ServiceInstance(
                instance_id=f"{deployment.deployment_id}_v{deployment.version}_{i}",
                service_name=deployment.service_name,
                version=deployment.version,
                node_id=f"node_{i % 3}",
                status=InstanceStatus.RUNNING,
            )
            new_instances.append(instance)
        return new_instances


class BlueGreenStrategy(DeploymentStrategy):
    """蓝绿部署策略"""

    def execute(self, deployment: Deployment, instances: List[ServiceInstance]) -> List[ServiceInstance]:
        """创建全新环境后切换"""
        new_instances = []
        for i in range(deployment.replicas):
            instance = ServiceInstance(
                instance_id=f"{deployment.deployment_id}_green_{i}",
                service_name=deployment.service_name,
                version=deployment.version,
                node_id=f"green_node_{i}",
                status=InstanceStatus.HEALTHY,
            )
            new_instances.append(instance)
        return new_instances


class CanaryStrategy(DeploymentStrategy):
    """金丝雀发布策略"""

    def __init__(self, canary_percent: float = 10.0):
        self.canary_percent = canary_percent

    def execute(self, deployment: Deployment, instances: List[ServiceInstance]) -> List[ServiceInstance]:
        """先部署少量实例验证"""
        canary_count = max(1, int(deployment.replicas * self.canary_percent / 100))
        new_instances = []
        for i in range(canary_count):
            instance = ServiceInstance(
                instance_id=f"{deployment.deployment_id}_canary_{i}",
                service_name=deployment.service_name,
                version=deployment.version,
                node_id=f"canary_node_{i}",
                status=InstanceStatus.RUNNING,
            )
            new_instances.append(instance)
        return new_instances


# ============================================================
# 编排器
# ============================================================

class Orchestrator:
    """
    部署编排器

    管理服务实例的生命周期和部署策略执行
    """

    def __init__(self):
        self._instances: Dict[str, ServiceInstance] = {}
        self._deployments: Dict[str, Deployment] = {}
        self._lock = threading.Lock()

    def deploy(self, deployment: Deployment) -> List[ServiceInstance]:
        """执行部署"""
        strategy = self._create_strategy(deployment.strategy)
        instances = strategy.execute(deployment, list(self._instances.values()))

        with self._lock:
            self._deployments[deployment.deployment_id] = deployment
            for instance in instances:
                self._instances[instance.instance_id] = instance

        return instances

    def _create_strategy(self, strategy_type: DeploymentStrategyType) -> DeploymentStrategy:
        """创建部署策略"""
        if strategy_type == DeploymentStrategyType.ROLLING:
            return RollingStrategy()
        elif strategy_type == DeploymentStrategyType.BLUE_GREEN:
            return BlueGreenStrategy()
        elif strategy_type == DeploymentStrategyType.CANARY:
            return CanaryStrategy()
        else:
            return RollingStrategy()

    def scale(self, service_name: str, target_replicas: int) -> bool:
        """扩缩容服务"""
        with self._lock:
            service_instances = [
                inst for inst in self._instances.values()
                if inst.service_name == service_name and inst.status != InstanceStatus.STOPPED
            ]
            current = len(service_instances)

            if target_replicas > current:
                # 扩容
                for i in range(current, target_replicas):
                    instance = ServiceInstance(
                        instance_id=f"{service_name}_scale_{i}_{int(time.time())}",
                        service_name=service_name,
                        version=service_instances[0].version if service_instances else "v1",
                        node_id=f"node_{i % 3}",
                        status=InstanceStatus.RUNNING,
                    )
                    self._instances[instance.instance_id] = instance
                return True
            elif target_replicas < current:
                # 缩容：保留前target_replicas个，标记其余为terminating
                to_remove = service_instances[target_replicas:]
                for inst in to_remove:
                    inst.status = InstanceStatus.TERMINATING
                return True
            return True

    def health_check(self, instance_id: str) -> bool:
        """健康检查"""
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance is None:
                return False
            instance.health_checks += 1
            # 模拟健康检查（基于实例ID哈希）
            is_healthy = hash(instance_id) % 10 != 0
            if not is_healthy:
                instance.failed_checks += 1
                instance.status = InstanceStatus.UNHEALTHY
            else:
                instance.status = InstanceStatus.HEALTHY
            return is_healthy

    def rollback(self, deployment_id: str) -> bool:
        """回滚部署"""
        with self._lock:
            deployment = self._deployments.get(deployment_id)
            if deployment is None:
                return False
            # 标记该部署的所有实例为停止
            for instance in self._instances.values():
                if instance.instance_id.startswith(deployment_id):
                    instance.status = InstanceStatus.STOPPED
            return True

    def get_instances(self, service_name: Optional[str] = None) -> List[ServiceInstance]:
        """获取实例列表"""
        with self._lock:
            instances = list(self._instances.values())
            if service_name:
                instances = [i for i in instances if i.service_name == service_name]
            return instances

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "total_instances": len(self._instances),
                "total_deployments": len(self._deployments),
                "healthy": sum(1 for i in self._instances.values() if i.status == InstanceStatus.HEALTHY),
                "running": sum(1 for i in self._instances.values() if i.status == InstanceStatus.RUNNING),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_orchestrator() -> Orchestrator:
    """创建编排器"""
    return Orchestrator()


def create_deployment(
    deployment_id: str,
    service_name: str,
    version: str,
    strategy: DeploymentStrategyType = DeploymentStrategyType.ROLLING,
    replicas: int = 1,
) -> Deployment:
    """创建部署定义"""
    return Deployment(
        deployment_id=deployment_id,
        service_name=service_name,
        version=version,
        strategy=strategy,
        replicas=replicas,
    )
