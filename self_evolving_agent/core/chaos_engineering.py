"""
阶段62: 混沌工程接口标准化

第一性原理:
1. 系统必然故障：硬件、网络、软件都会出问题
2. 故障必须提前演练：生产环境的问题要在可控条件下暴露
3. 韧性是练出来的：只有经历过故障的系统才可靠

设计原则:
- ChaosExperiment: 混沌实验
- ChaosAttack: 故障注入攻击
- ChaosEngine: 混沌引擎
- 支持延迟注入、错误注入、资源耗尽、节点故障
"""

import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class AttackType(Enum):
    """攻击类型"""
    LATENCY = "latency"           # 延迟注入
    ERROR = "error"               # 错误注入
    CPU_HOG = "cpu_hog"           # CPU耗尽
    MEMORY_HOG = "memory_hog"     # 内存耗尽
    KILL = "kill"                 # 进程终止
    NETWORK_PARTITION = "network_partition"  # 网络分区


class ExperimentStatus(Enum):
    """实验状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"


@dataclass
class ChaosAttack:
    """混沌攻击定义"""
    attack_id: str
    attack_type: AttackType
    target: str
    config: Dict[str, Any] = field(default_factory=dict)
    duration_sec: float = 30.0


@dataclass
class ExperimentResult:
    """实验结果"""
    experiment_id: str
    status: ExperimentStatus
    attacks_executed: int = 0
    attacks_failed: int = 0
    observations: List[Dict[str, Any]] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0


# ============================================================
# 攻击执行器
# ============================================================

class AttackExecutor(ABC):
    """攻击执行器抽象基类"""

    @abstractmethod
    def execute(self, attack: ChaosAttack) -> bool:
        """执行攻击"""
        pass

    @abstractmethod
    def recover(self, attack: ChaosAttack) -> bool:
        """恢复攻击影响"""
        pass


class LatencyAttackExecutor(AttackExecutor):
    """延迟攻击执行器"""

    def execute(self, attack: ChaosAttack) -> bool:
        latency_ms = attack.config.get("latency_ms", 100)
        time.sleep(latency_ms / 1000.0)
        return True

    def recover(self, attack: ChaosAttack) -> bool:
        return True


class ErrorAttackExecutor(AttackExecutor):
    """错误攻击执行器"""

    def execute(self, attack: ChaosAttack) -> bool:
        error_rate = attack.config.get("error_rate", 0.5)
        # 模拟错误：基于攻击ID哈希决定是否失败
        should_fail = hash(attack.attack_id) % 100 < (error_rate * 100)
        return not should_fail  # 返回False表示攻击"成功"制造了故障

    def recover(self, attack: ChaosAttack) -> bool:
        return True


class KillAttackExecutor(AttackExecutor):
    """进程终止攻击执行器"""

    def execute(self, attack: ChaosAttack) -> bool:
        # 模拟进程终止
        return True

    def recover(self, attack: ChaosAttack) -> bool:
        # 模拟进程重启
        return True


# ============================================================
# 混沌实验
# ============================================================

class ChaosExperiment:
    """
    混沌实验

    定义一组有序的攻击序列
    """

    def __init__(self, experiment_id: str, hypothesis: str):
        self.experiment_id = experiment_id
        self.hypothesis = hypothesis
        self._attacks: List[ChaosAttack] = []
        self._status = ExperimentStatus.PENDING
        self._lock = threading.Lock()

    def add_attack(self, attack: ChaosAttack) -> None:
        """添加攻击"""
        with self._lock:
            self._attacks.append(attack)

    def get_attacks(self) -> List[ChaosAttack]:
        """获取攻击列表"""
        with self._lock:
            return list(self._attacks)

    def get_status(self) -> ExperimentStatus:
        with self._lock:
            return self._status

    def set_status(self, status: ExperimentStatus) -> None:
        with self._lock:
            self._status = status


# ============================================================
# 混沌引擎
# ============================================================

class ChaosEngine:
    """
    混沌引擎

    执行混沌实验，管理攻击执行器
    """

    def __init__(self):
        self._executors: Dict[AttackType, AttackExecutor] = {
            AttackType.LATENCY: LatencyAttackExecutor(),
            AttackType.ERROR: ErrorAttackExecutor(),
            AttackType.KILL: KillAttackExecutor(),
        }
        self._experiments: Dict[str, ChaosExperiment] = {}
        self._lock = threading.Lock()

    def register_executor(self, attack_type: AttackType, executor: AttackExecutor) -> None:
        """注册攻击执行器"""
        with self._lock:
            self._executors[attack_type] = executor

    def run_experiment(self, experiment: ChaosExperiment) -> ExperimentResult:
        """执行混沌实验"""
        experiment.set_status(ExperimentStatus.RUNNING)
        start_time = time.time()

        attacks_executed = 0
        attacks_failed = 0
        observations = []

        for attack in experiment.get_attacks():
            executor = self._executors.get(attack.attack_type)
            if executor is None:
                attacks_failed += 1
                observations.append({
                    "attack_id": attack.attack_id,
                    "status": "no_executor",
                })
                continue

            # 执行攻击
            success = executor.execute(attack)
            attacks_executed += 1

            observations.append({
                "attack_id": attack.attack_id,
                "type": attack.attack_type.value,
                "target": attack.target,
                "success": success,
            })

            # 等待攻击持续时间
            time.sleep(attack.duration_sec)

            # 恢复
            executor.recover(attack)

        end_time = time.time()
        experiment.set_status(ExperimentStatus.COMPLETED)

        result = ExperimentResult(
            experiment_id=experiment.experiment_id,
            status=ExperimentStatus.COMPLETED,
            attacks_executed=attacks_executed,
            attacks_failed=attacks_failed,
            observations=observations,
            start_time=start_time,
            end_time=end_time,
        )

        with self._lock:
            self._experiments[experiment.experiment_id] = experiment

        return result

    def stop_experiment(self, experiment_id: str) -> bool:
        """停止实验"""
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return False
            experiment.set_status(ExperimentStatus.STOPPED)
            return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "total_experiments": len(self._experiments),
                "executors": [e.value for e in self._executors.keys()],
            }


# ============================================================
# 便捷函数
# ============================================================

def create_chaos_engine() -> ChaosEngine:
    """创建混沌引擎"""
    return ChaosEngine()


def create_chaos_experiment(experiment_id: str, hypothesis: str) -> ChaosExperiment:
    """创建混沌实验"""
    return ChaosExperiment(experiment_id=experiment_id, hypothesis=hypothesis)


def create_chaos_attack(
    attack_id: str,
    attack_type: AttackType,
    target: str,
    config: Optional[Dict[str, Any]] = None,
    duration_sec: float = 1.0,
) -> ChaosAttack:
    """创建混沌攻击"""
    return ChaosAttack(
        attack_id=attack_id,
        attack_type=attack_type,
        target=target,
        config=config or {},
        duration_sec=duration_sec,
    )
