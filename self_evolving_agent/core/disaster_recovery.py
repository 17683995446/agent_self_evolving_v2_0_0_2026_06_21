"""
阶段65: 灾备恢复接口标准化

第一性原理:
1. 灾难必然发生：硬件故障、网络中断、人为错误不可避免
2. 备份是最后的防线：没有备份就没有恢复
3. RTO/RPO是硬指标：恢复时间和数据丢失量必须可量化

设计原则:
- Backup: 备份定义
- RecoveryPoint: 恢复点
- DRPlan: 灾备计划
- DisasterRecoveryEngine: 灾备恢复引擎
- 支持全量/增量备份、跨区域复制、自动故障切换
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class BackupType(Enum):
    """备份类型"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class DRStatus(Enum):
    """灾备状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILOVER = "failover"
    RECOVERING = "recovering"


@dataclass
class Backup:
    """备份"""
    backup_id: str
    source: str
    backup_type: BackupType
    timestamp: float
    size_bytes: int = 0
    checksum: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryPoint:
    """恢复点"""
    rp_id: str
    backup_id: str
    timestamp: float
    data_loss_seconds: float = 0.0
    recovery_time_seconds: float = 0.0


@dataclass
class DRPlan:
    """灾备计划"""
    plan_id: str
    service_name: str
    rpo_seconds: float = 3600.0    # 恢复点目标
    rto_seconds: float = 300.0     # 恢复时间目标
    backup_schedule: str = "0 */6 * * *"  # 每6小时
    replication_regions: List[str] = field(default_factory=list)


# ============================================================
# 灾备恢复引擎
# ============================================================

class DisasterRecoveryEngine:
    """
    灾备恢复引擎

    管理备份、恢复点和故障切换
    """

    def __init__(self):
        self._backups: Dict[str, Backup] = {}
        self._plans: Dict[str, DRPlan] = {}
        self._status: Dict[str, DRStatus] = {}
        self._lock = threading.Lock()

    def create_backup(self, source: str, backup_type: BackupType, data_size: int = 0) -> Backup:
        """创建备份"""
        backup_id = f"backup_{source}_{int(time.time())}"
        backup = Backup(
            backup_id=backup_id,
            source=source,
            backup_type=backup_type,
            timestamp=time.time(),
            size_bytes=data_size,
            checksum=f"chk_{hash(backup_id) % 10000}",
        )
        with self._lock:
            self._backups[backup_id] = backup
        return backup

    def register_plan(self, plan: DRPlan) -> None:
        """注册灾备计划"""
        with self._lock:
            self._plans[plan.plan_id] = plan
            self._status[plan.service_name] = DRStatus.HEALTHY

    def get_latest_backup(self, source: str) -> Optional[Backup]:
        """获取最新备份"""
        with self._lock:
            backups = [b for b in self._backups.values() if b.source == source]
            if not backups:
                return None
            return max(backups, key=lambda b: b.timestamp)

    def recover(self, source: str, target_region: str = "primary") -> RecoveryPoint:
        """
        执行恢复

        从最新备份恢复到指定区域
        """
        start_time = time.time()
        backup = self.get_latest_backup(source)

        if backup is None:
            return RecoveryPoint(
                rp_id=f"rp_{source}_failed",
                backup_id="",
                timestamp=time.time(),
                data_loss_seconds=0.0,
                recovery_time_seconds=0.0,
            )

        # 模拟恢复过程
        recovery_time = time.time() - start_time + 0.1
        data_loss = time.time() - backup.timestamp

        return RecoveryPoint(
            rp_id=f"rp_{source}_{int(time.time())}",
            backup_id=backup.backup_id,
            timestamp=time.time(),
            data_loss_seconds=data_loss,
            recovery_time_seconds=recovery_time,
        )

    def check_rpo_compliance(self, plan_id: str) -> Dict[str, Any]:
        """检查RPO合规性"""
        with self._lock:
            plan = self._plans.get(plan_id)
        if plan is None:
            return {"compliant": False, "reason": "plan not found"}

        latest = self.get_latest_backup(plan.service_name)
        if latest is None:
            return {"compliant": False, "reason": "no backups"}

        elapsed = time.time() - latest.timestamp
        compliant = elapsed <= plan.rpo_seconds

        return {
            "compliant": compliant,
            "elapsed_seconds": elapsed,
            "rpo_seconds": plan.rpo_seconds,
            "latest_backup": latest.backup_id,
        }

    def failover(self, service_name: str, target_region: str) -> bool:
        """执行故障切换"""
        with self._lock:
            self._status[service_name] = DRStatus.FAILOVER
        # 模拟故障切换（在锁外执行）
        time.sleep(0.01)
        with self._lock:
            self._status[service_name] = DRStatus.HEALTHY
            return True

    def get_status(self, service_name: str) -> DRStatus:
        """获取服务灾备状态"""
        with self._lock:
            return self._status.get(service_name, DRStatus.HEALTHY)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "total_backups": len(self._backups),
                "total_plans": len(self._plans),
                "services": list(self._status.keys()),
            }


# ============================================================
# 便捷函数
# ============================================================

def create_disaster_recovery_engine() -> DisasterRecoveryEngine:
    """创建灾备恢复引擎"""
    return DisasterRecoveryEngine()


def create_dr_plan(
    plan_id: str,
    service_name: str,
    rpo_seconds: float = 3600.0,
    rto_seconds: float = 300.0,
    replication_regions: Optional[List[str]] = None,
) -> DRPlan:
    """创建灾备计划"""
    return DRPlan(
        plan_id=plan_id,
        service_name=service_name,
        rpo_seconds=rpo_seconds,
        rto_seconds=rto_seconds,
        replication_regions=replication_regions or [],
    )
