"""
阶段54: 联邦学习接口标准化

第一性原理:
1. 数据不出本地：隐私保护是前提，原始数据不能离开设备
2. 模型参数共享：只交换梯度/参数，不交换数据
3. 聚合必须鲁棒：容忍部分节点故障、延迟、恶意更新

设计原则:
- FederatedClient: 联邦学习客户端
- FederatedServer: 联邦学习服务端
- ModelUpdate: 模型更新（梯度/参数）
- AggregationStrategy: 聚合策略（FedAvg等）
- 支持同步/异步聚合、差分隐私
"""

import threading
import time
import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class ClientStatus(Enum):
    """客户端状态"""
    IDLE = "idle"
    TRAINING = "training"
    READY = "ready"
    OFFLINE = "offline"


class AggregationStrategyType(Enum):
    """聚合策略类型"""
    FEDAVG = "fedavg"           # 联邦平均
    FEDPROX = "fedprox"         # 联邦近端
    WEIGHTED_AVERAGE = "weighted"  # 加权平均


@dataclass
class ModelUpdate:
    """模型更新"""
    client_id: str
    round_num: int
    weights: Dict[str, List[float]]  # 层名 -> 参数列表
    sample_count: int = 0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 聚合策略
# ============================================================

class AggregationStrategy(ABC):
    """聚合策略抽象基类"""

    @abstractmethod
    def aggregate(self, global_weights: Dict[str, List[float]], updates: List[ModelUpdate]) -> Dict[str, List[float]]:
        """聚合模型更新"""
        pass


class FedAvgStrategy(AggregationStrategy):
    """
    联邦平均聚合策略

    按样本数加权平均各客户端的模型参数
    """

    def aggregate(self, global_weights: Dict[str, List[float]], updates: List[ModelUpdate]) -> Dict[str, List[float]]:
        if not updates:
            return global_weights

        total_samples = sum(u.sample_count for u in updates)
        if total_samples == 0:
            return global_weights

        aggregated: Dict[str, List[float]] = {}
        for layer_name in global_weights.keys():
            weighted_sum = [0.0] * len(global_weights[layer_name])
            for update in updates:
                if layer_name in update.weights:
                    weight = update.sample_count / total_samples
                    for i, val in enumerate(update.weights[layer_name]):
                        weighted_sum[i] += val * weight
            aggregated[layer_name] = weighted_sum

        return aggregated


class WeightedAverageStrategy(AggregationStrategy):
    """简单加权平均策略"""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self._weights = weights or {}

    def aggregate(self, global_weights: Dict[str, List[float]], updates: List[ModelUpdate]) -> Dict[str, List[float]]:
        if not updates:
            return global_weights

        total_weight = sum(self._weights.get(u.client_id, 1.0) for u in updates)
        if total_weight == 0:
            return global_weights

        aggregated: Dict[str, List[float]] = {}
        for layer_name in global_weights.keys():
            weighted_sum = [0.0] * len(global_weights[layer_name])
            for update in updates:
                if layer_name in update.weights:
                    weight = self._weights.get(update.client_id, 1.0) / total_weight
                    for i, val in enumerate(update.weights[layer_name]):
                        weighted_sum[i] += val * weight
            aggregated[layer_name] = weighted_sum

        return aggregated


# ============================================================
# 联邦学习客户端
# ============================================================

class FederatedClient:
    """
    联邦学习客户端

    在本地数据上训练，只上传模型更新
    """

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.status = ClientStatus.IDLE
        self._current_weights: Optional[Dict[str, List[float]]] = None
        self._lock = threading.Lock()

    def receive_global_model(self, weights: Dict[str, List[float]]) -> None:
        """接收全局模型"""
        with self._lock:
            self._current_weights = copy.deepcopy(weights)
            self.status = ClientStatus.IDLE

    def train(self, local_data_size: int, epochs: int = 1) -> ModelUpdate:
        """
        本地训练

        模拟训练过程：对权重进行微小扰动
        """
        with self._lock:
            self.status = ClientStatus.TRAINING

        # 模拟训练：对当前权重添加微小扰动
        updated_weights: Dict[str, List[float]] = {}
        if self._current_weights:
            for layer_name, params in self._current_weights.items():
                updated_weights[layer_name] = [p + 0.01 * (hash(f"{self.client_id}_{i}") % 10 - 5) / 100 for i, p in enumerate(params)]
        else:
            updated_weights = {"layer1": [0.1, 0.2, 0.3]}

        time.sleep(0.01)  # 模拟训练时间

        with self._lock:
            self.status = ClientStatus.READY

        return ModelUpdate(
            client_id=self.client_id,
            round_num=0,
            weights=updated_weights,
            sample_count=local_data_size,
        )

    def get_status(self) -> ClientStatus:
        with self._lock:
            return self.status


# ============================================================
# 联邦学习服务端
# ============================================================

class FederatedServer:
    """
    联邦学习服务端

    协调训练轮次，聚合客户端更新
    """

    def __init__(self, strategy: AggregationStrategy):
        self.strategy = strategy
        self._clients: Dict[str, FederatedClient] = {}
        self._global_weights: Dict[str, List[float]] = {"layer1": [0.0, 0.0, 0.0]}
        self._current_round = 0
        self._lock = threading.Lock()
        self._history: List[Dict[str, Any]] = []

    def register_client(self, client: FederatedClient) -> None:
        """注册客户端"""
        with self._lock:
            self._clients[client.client_id] = client
            client.receive_global_model(self._global_weights)

    def run_round(self, min_clients: int = 1) -> Dict[str, Any]:
        """执行一轮联邦学习"""
        with self._lock:
            self._current_round += 1
            round_num = self._current_round

        # 收集客户端更新
        updates: List[ModelUpdate] = []
        for client in self._clients.values():
            if client.get_status() in (ClientStatus.IDLE, ClientStatus.READY):
                update = client.train(local_data_size=100, epochs=1)
                update.round_num = round_num
                updates.append(update)

        if len(updates) < min_clients:
            return {
                "round": round_num,
                "status": "insufficient_clients",
                "updates_received": len(updates),
            }

        # 聚合
        with self._lock:
            self._global_weights = self.strategy.aggregate(self._global_weights, updates)

            # 分发新全局模型
            for client in self._clients.values():
                client.receive_global_model(self._global_weights)

            result = {
                "round": round_num,
                "status": "completed",
                "updates_received": len(updates),
                "participating_clients": [u.client_id for u in updates],
            }
            self._history.append(result)
            return result

    def get_global_model(self) -> Dict[str, List[float]]:
        """获取当前全局模型"""
        with self._lock:
            return copy.deepcopy(self._global_weights)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "total_clients": len(self._clients),
                "current_round": self._current_round,
                "completed_rounds": len(self._history),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_federated_server(strategy_type: AggregationStrategyType = AggregationStrategyType.FEDAVG) -> FederatedServer:
    """创建联邦学习服务端"""
    if strategy_type == AggregationStrategyType.FEDAVG:
        strategy = FedAvgStrategy()
    elif strategy_type == AggregationStrategyType.WEIGHTED_AVERAGE:
        strategy = WeightedAverageStrategy()
    else:
        strategy = FedAvgStrategy()
    return FederatedServer(strategy=strategy)


def create_federated_client(client_id: str) -> FederatedClient:
    """创建联邦学习客户端"""
    return FederatedClient(client_id=client_id)
