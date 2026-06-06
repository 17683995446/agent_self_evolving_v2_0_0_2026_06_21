"""
阶段51测试: 审计日志接口标准化
"""
import sys
sys.path.insert(0, '/workspace')

import time
from self_evolving_agent.core.audit_log import (
    AuditLog, AuditEvent, AuditAction, AuditResult, create_audit_log
)


def test_log_event():
    """测试记录事件"""
    log = create_audit_log()
    event = log.log(
        user_id="user_1",
        action=AuditAction.CREATE,
        resource="model_v1",
        result=AuditResult.SUCCESS,
        details={"version": "1.0"},
    )

    assert event.user_id == "user_1"
    assert event.action == AuditAction.CREATE
    assert event.result == AuditResult.SUCCESS
    assert event.current_hash != ""
    print("  [test_log_event] 记录事件 ✓")


def test_query_by_user():
    """测试按用户查询"""
    log = create_audit_log()
    log.log("alice", AuditAction.CREATE, "res1", AuditResult.SUCCESS)
    log.log("bob", AuditAction.READ, "res2", AuditResult.SUCCESS)
    log.log("alice", AuditAction.UPDATE, "res1", AuditResult.SUCCESS)

    results = log.query(user_id="alice")
    assert len(results) == 2
    assert all(r.user_id == "alice" for r in results)
    print("  [test_query_by_user] 按用户查询 ✓")


def test_query_by_action():
    """测试按操作类型查询"""
    log = create_audit_log()
    log.log("user", AuditAction.CREATE, "r1", AuditResult.SUCCESS)
    log.log("user", AuditAction.READ, "r2", AuditResult.SUCCESS)
    log.log("user", AuditAction.DELETE, "r3", AuditResult.SUCCESS)

    results = log.query(action=AuditAction.READ)
    assert len(results) == 1
    assert results[0].action == AuditAction.READ
    print("  [test_query_by_action] 按操作查询 ✓")


def test_integrity_verification():
    """测试完整性校验"""
    log = create_audit_log()
    log.log("user", AuditAction.CREATE, "r1", AuditResult.SUCCESS)
    log.log("user", AuditAction.UPDATE, "r2", AuditResult.SUCCESS)
    log.log("user", AuditAction.DELETE, "r3", AuditResult.FAILURE)

    assert log.verify_integrity() is True
    print("  [test_integrity_verification] 完整性校验 ✓")


def test_integrity_tampered():
    """测试篡改检测"""
    log = create_audit_log()
    log.log("user", AuditAction.CREATE, "r1", AuditResult.SUCCESS)
    log.log("user", AuditAction.UPDATE, "r2", AuditResult.SUCCESS)

    # 篡改事件
    log._events[0].current_hash = "tampered"

    assert log.verify_integrity() is False
    print("  [test_integrity_tampered] 篡改检测 ✓")


def test_chain_hash():
    """测试哈希链"""
    log = create_audit_log()
    e1 = log.log("user", AuditAction.CREATE, "r1", AuditResult.SUCCESS)
    e2 = log.log("user", AuditAction.UPDATE, "r2", AuditResult.SUCCESS)

    # 第二个事件的previous_hash应等于第一个事件的current_hash
    assert e2.previous_hash == e1.current_hash
    print("  [test_chain_hash] 哈希链 ✓")


def test_log_stats():
    """测试日志统计"""
    log = create_audit_log()
    assert log.get_stats()["total_events"] == 0

    log.log("user", AuditAction.CREATE, "r1", AuditResult.SUCCESS)
    stats = log.get_stats()

    assert stats["total_events"] == 1
    assert stats["integrity_verified"] is True
    assert stats["first_event_time"] is not None
    print("  [test_log_stats] 日志统计 ✓")


def test_query_limit():
    """测试查询限制"""
    log = create_audit_log()
    for i in range(20):
        log.log("user", AuditAction.CREATE, f"r{i}", AuditResult.SUCCESS)

    results = log.query(limit=5)
    assert len(results) == 5
    print("  [test_query_limit] 查询限制 ✓")


def test_query_by_resource():
    """测试按资源查询"""
    log = create_audit_log()
    log.log("user", AuditAction.CREATE, "model_a", AuditResult.SUCCESS)
    log.log("user", AuditAction.READ, "model_b", AuditResult.SUCCESS)
    log.log("user", AuditAction.UPDATE, "model_a", AuditResult.SUCCESS)

    results = log.query(resource="model_a")
    assert len(results) == 2
    print("  [test_query_by_resource] 按资源查询 ✓")


def test_query_by_time():
    """测试按时间查询"""
    log = create_audit_log()
    start = time.time()
    log.log("user", AuditAction.CREATE, "r1", AuditResult.SUCCESS)
    time.sleep(0.05)
    middle = time.time()
    log.log("user", AuditAction.UPDATE, "r2", AuditResult.SUCCESS)
    time.sleep(0.05)
    end = time.time()

    results = log.query(start_time=middle, end_time=end)
    assert len(results) == 1
    assert results[0].action == AuditAction.UPDATE
    print("  [test_query_by_time] 按时间查询 ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("阶段51测试: 审计日志接口标准化")
    print("=" * 60)

    test_log_event()
    test_query_by_user()
    test_query_by_action()
    test_integrity_verification()
    test_integrity_tampered()
    test_chain_hash()
    test_log_stats()
    test_query_limit()
    test_query_by_resource()
    test_query_by_time()

    print("=" * 60)
    print("全部10项测试通过 ✓")
    print("=" * 60)
