"""分布式支持Mixin — 阶段149从agent.py拆分"""

from typing import Any, Optional

from ..core.distributed import NodeInfo, NodeRole, DistributedCoordinator, create_dist_coordinator


class DistributedMixin:
    """分布式支持接口（阶段131）"""

    def enable_distributed(
        self,
        node_id: Optional[str] = None,
        role: NodeRole = NodeRole.WORKER,
    ) -> DistributedCoordinator:
        """启用分布式模式（阶段131新增）"""
        if self._dist_coordinator is None:
            self._dist_coordinator = create_dist_coordinator(
                node_id=node_id or f"agent_{self.agent_id}",
                role=role,
            )
            self._dist_coordinator.start()
        return self._dist_coordinator

    def join_cluster(self, peer_agent: "SelfEvolvingAgent") -> bool:
        """加入集群（阶段131新增）"""
        if self._dist_coordinator is None:
            self.enable_distributed()
        if peer_agent._dist_coordinator is None:
            peer_agent.enable_distributed()
        return self._dist_coordinator.join_cluster(peer_agent._dist_coordinator)

    def get_cluster_status(self) -> dict:
        """获取集群状态（阶段131新增）"""
        if self._dist_coordinator is None:
            return {"distributed": False}
        return {"distributed": True, **self._dist_coordinator.status()}

    def assign_distributed_task(self, task_key: Optional[str] = None) -> Optional[NodeInfo]:
        """分配分布式任务（阶段131新增）"""
        if self._dist_coordinator is None:
            return None
        return self._dist_coordinator.assign_task(task_key)

    def set_distributed_state(self, key: str, value: Any) -> None:
        """设置分布式状态（阶段131新增）"""
        if self._dist_coordinator:
            self._dist_coordinator.set_state(key, value)

    def get_distributed_state(self, key: str, default: Any = None) -> Any:
        """获取分布式状态（阶段131新增）"""
        if self._dist_coordinator:
            return self._dist_coordinator.get_state(key, default)
        return default

    def publish_distributed_message(
        self,
        topic: str,
        payload: Any,
        target: str = "*",
    ) -> Optional[str]:
        """发布分布式消息（阶段131新增）"""
        if self._dist_coordinator:
            return self._dist_coordinator.publish(topic, payload, target)
        return None
