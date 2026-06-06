"""
阶段65验证: 灾备恢复接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("dr", "/workspace/self_evolving_agent/core/disaster_recovery.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["dr"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段65验证: 灾备恢复接口标准化")
print("=" * 60)

# 测试1: 创建备份
def test_create_backup():
    engine = mod.create_disaster_recovery_engine()
    backup = engine.create_backup("db1", mod.BackupType.FULL, data_size=1024)
    assert backup.source == "db1"
    assert backup.backup_type == mod.BackupType.FULL
    assert backup.size_bytes == 1024
    assert backup.checksum != ""
    print("  [test_create_backup] 创建备份 OK")

# 测试2: 获取最新备份
def test_latest_backup():
    engine = mod.create_disaster_recovery_engine()
    engine.create_backup("db1", mod.BackupType.FULL)
    engine.create_backup("db1", mod.BackupType.INCREMENTAL)
    latest = engine.get_latest_backup("db1")
    assert latest is not None
    assert latest.backup_type == mod.BackupType.INCREMENTAL
    print("  [test_latest_backup] 获取最新备份 OK")

# 测试3: 恢复
def test_recover():
    engine = mod.create_disaster_recovery_engine()
    engine.create_backup("db1", mod.BackupType.FULL)
    rp = engine.recover("db1", target_region="secondary")
    assert rp.backup_id != ""
    assert rp.recovery_time_seconds > 0
    print("  [test_recover] 恢复 OK")

# 测试4: 灾备计划和RPO合规
def test_rpo_compliance():
    engine = mod.create_disaster_recovery_engine()
    plan = mod.create_dr_plan("plan1", "svc1", rpo_seconds=3600)
    engine.register_plan(plan)
    engine.create_backup("svc1", mod.BackupType.FULL)

    compliance = engine.check_rpo_compliance("plan1")
    assert compliance["compliant"] is True
    assert compliance["elapsed_seconds"] < 3600
    print("  [test_rpo_compliance] RPO合规 OK")

# 测试5: 故障切换
def test_failover():
    engine = mod.create_disaster_recovery_engine()
    plan = mod.create_dr_plan("plan2", "svc2")
    engine.register_plan(plan)

    assert engine.get_status("svc2") == mod.DRStatus.HEALTHY
    engine.failover("svc2", "region_b")
    assert engine.get_status("svc2") == mod.DRStatus.HEALTHY
    print("  [test_failover] 故障切换 OK")

# 测试6: 统计信息
def test_stats():
    engine = mod.create_disaster_recovery_engine()
    engine.create_backup("db1", mod.BackupType.FULL)
    plan = mod.create_dr_plan("plan1", "svc1")
    engine.register_plan(plan)

    stats = engine.get_stats()
    assert stats["total_backups"] == 1
    assert stats["total_plans"] == 1
    assert "svc1" in stats["services"]
    print("  [test_stats] 统计信息 OK")

if __name__ == "__main__":
    test_create_backup()
    test_latest_backup()
    test_recover()
    test_rpo_compliance()
    test_failover()
    test_stats()
    print("=" * 60)
    print("阶段65验证通过 ✓")
    print("=" * 60)
