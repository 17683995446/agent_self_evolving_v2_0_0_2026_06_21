"""
阶段51验证: 审计日志接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location(
    "audit_log", "/workspace/self_evolving_agent/core/audit_log.py"
)
audit_log_module = importlib.util.module_from_spec(spec)
sys.modules["audit_log"] = audit_log_module
spec.loader.exec_module(audit_log_module)

AuditLog = audit_log_module.AuditLog
AuditEvent = audit_log_module.AuditEvent
AuditAction = audit_log_module.AuditAction
AuditResult = audit_log_module.AuditResult
create_audit_log = audit_log_module.create_audit_log

def test_log_event():
    log = create_audit_log()
    event = log.log("user_1", AuditAction.CREATE, "model_v1", AuditResult.SUCCESS, details={"version": "1.0"})
    assert event.user_id == "user_1"
    assert event.action == AuditAction.CREATE
    assert event.result == AuditResult.SUCCESS
    assert event.current_hash != ""
    print("  [test_log_event] 记录事件 OK")

def test_query_by_user():
    log = create_audit_log()
    log.log("alice", AuditAction.CREATE, "res1", AuditResult.SUCCESS)
    log.log("bob", AuditAction.READ, "res2", AuditResult.SUCCESS)
    log.log("alice", AuditAction.UPDATE, "res1", AuditResult.SUCCESS)
    results = log.query(user_id="alice")
    assert len(results) == 2
    print("  [test_query_by_user] 按用户查询 OK")

def test_integrity():
    log = create_audit_log()
    log.log("user", AuditAction.CREATE, "r1", AuditResult.SUCCESS)
    log.log("user", AuditAction.UPDATE, "r2", AuditResult.SUCCESS)
    assert log.verify_integrity() is True
    log._events[0].current_hash = "tampered"
    assert log.verify_integrity() is False
    print("  [test_integrity] 完整性校验 OK")

def test_chain():
    log = create_audit_log()
    e1 = log.log("user", AuditAction.CREATE, "r1", AuditResult.SUCCESS)
    e2 = log.log("user", AuditAction.UPDATE, "r2", AuditResult.SUCCESS)
    assert e2.previous_hash == e1.current_hash
    print("  [test_chain] 哈希链 OK")

if __name__ == "__main__":
    print("=" * 50)
    print("阶段51验证: 审计日志接口标准化")
    print("=" * 50)
    test_log_event()
    test_query_by_user()
    test_integrity()
    test_chain()
    print("=" * 50)
    print("阶段51验证通过")
    print("=" * 50)
