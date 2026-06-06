"""
阶段35: 事务接口标准化 — 验证测试

验证目标:
1. 事务开始、提交、回滚状态正确
2. 操作记录可回滚
3. 保存点可部分回滚
4. 参与者两阶段提交
5. 事务装饰器自动包装
6. 嵌套事务支持
"""

import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.transaction import (
    TransactionStatus, TransactionIsolation, TransactionContext,
    TransactionParticipant, TransactionManager,
    transactional, get_global_transaction_manager,
)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print('='*60)


class MockParticipant(TransactionParticipant):
    """模拟事务参与者"""

    def __init__(self, name: str, prepare_fail: bool = False):
        self.name = name
        self.prepare_fail = prepare_fail
        self.prepared = False
        self.committed = False
        self.rolled_back = False

    def prepare(self, ctx: TransactionContext) -> bool:
        self.prepared = True
        return not self.prepare_fail

    def commit(self, ctx: TransactionContext) -> None:
        self.committed = True

    def rollback(self, ctx: TransactionContext) -> None:
        self.rolled_back = True


def test_basic_transaction():
    """测试基本事务"""
    print_section("基本事务")

    manager = TransactionManager()
    ctx = manager.begin()

    assert ctx.status == TransactionStatus.ACTIVE
    print(f"事务状态: {ctx.status.value}")

    # 提交
    result = manager.commit(ctx.transaction_id)
    assert result == True
    assert manager.get_status(ctx.transaction_id) == TransactionStatus.COMMITTED
    print(f"提交后状态: {manager.get_status(ctx.transaction_id).value}")

    # 新事务
    ctx2 = manager.begin()
    result2 = manager.rollback(ctx2.transaction_id)
    assert result2 == True
    assert manager.get_status(ctx2.transaction_id) == TransactionStatus.ROLLED_BACK
    print(f"回滚后状态: {manager.get_status(ctx2.transaction_id).value}")

    print("\n基本事务测试通过!")
    return True


def test_transactional_decorator():
    """测试事务装饰器"""
    print_section("事务装饰器")

    manager = TransactionManager()
    call_log = []

    @transactional(manager)
    def successful_operation():
        call_log.append("execute")
        return 42

    @transactional(manager)
    def failing_operation():
        call_log.append("execute_fail")
        raise ValueError("Oops")

    # 成功操作
    result = successful_operation()
    assert result == 42
    print(f"成功操作结果: {result}")

    # 失败操作
    try:
        failing_operation()
        assert False, "应该抛出异常"
    except ValueError:
        pass
    print("失败操作正确回滚并抛出异常")

    print("\n事务装饰器测试通过!")
    return True


def test_participant_two_phase():
    """测试参与者两阶段提交"""
    print_section("参与者两阶段提交")

    manager = TransactionManager()
    ctx = manager.begin()

    p1 = MockParticipant("p1")
    p2 = MockParticipant("p2")

    manager.add_participant(ctx.transaction_id, p1)
    manager.add_participant(ctx.transaction_id, p2)

    # 提交
    manager.commit(ctx.transaction_id)

    assert p1.prepared == True
    assert p2.prepared == True
    assert p1.committed == True
    assert p2.committed == True
    print("所有参与者 prepared 和 committed")

    # 回滚场景
    ctx2 = manager.begin()
    p3 = MockParticipant("p3")
    manager.add_participant(ctx2.transaction_id, p3)
    manager.rollback(ctx2.transaction_id)

    assert p3.rolled_back == True
    print("回滚时参与者 rolled_back")

    print("\n参与者两阶段提交测试通过!")
    return True


def test_prepare_failure():
    """测试准备失败导致回滚"""
    print_section("准备失败")

    manager = TransactionManager()
    ctx = manager.begin()

    p1 = MockParticipant("p1")
    p2 = MockParticipant("p2", prepare_fail=True)

    manager.add_participant(ctx.transaction_id, p1)
    manager.add_participant(ctx.transaction_id, p2)

    # 提交应失败（因为p2准备失败）
    result = manager.commit(ctx.transaction_id)
    assert result == False
    assert manager.get_status(ctx.transaction_id) == TransactionStatus.ROLLED_BACK
    assert p1.rolled_back == True  # p1也应被回滚
    print("准备失败导致整体回滚: True")

    print("\n准备失败测试通过!")
    return True


def test_savepoint():
    """测试保存点"""
    print_section("保存点")

    manager = TransactionManager()
    ctx = manager.begin()

    rollback_log = []

    # 记录操作
    manager.record_operation(ctx.transaction_id, {
        "action": "op1",
        "rollback": lambda: rollback_log.append("rollback_op1")
    })
    manager.record_operation(ctx.transaction_id, {
        "action": "op2",
        "rollback": lambda: rollback_log.append("rollback_op2")
    })

    # 创建保存点
    manager.create_savepoint(ctx.transaction_id, "sp1")

    # 保存点后的操作
    manager.record_operation(ctx.transaction_id, {
        "action": "op3",
        "rollback": lambda: rollback_log.append("rollback_op3")
    })

    # 回滚到保存点
    result = manager.rollback_to_savepoint(ctx.transaction_id, "sp1")
    assert result == True
    assert "rollback_op3" in rollback_log
    assert "rollback_op2" not in rollback_log  # op2在保存点前，不应回滚
    print(f"回滚日志: {rollback_log}")

    # 事务仍活跃
    assert manager.is_active(ctx.transaction_id) == True
    print("保存点回滚后事务仍活跃: True")

    # 最终提交
    manager.commit(ctx.transaction_id)
    assert manager.get_status(ctx.transaction_id) == TransactionStatus.COMMITTED

    print("\n保存点测试通过!")
    return True


def test_recorded_operations_rollback():
    """测试记录操作回滚"""
    print_section("记录操作回滚")

    manager = TransactionManager()
    ctx = manager.begin()

    rollback_log = []

    # 记录多个操作
    for i in range(3):
        manager.record_operation(ctx.transaction_id, {
            "action": f"op_{i}",
            "rollback": lambda idx=i: rollback_log.append(f"rollback_{idx}")
        })

    # 回滚事务
    manager.rollback(ctx.transaction_id)

    # 回滚应按逆序执行
    assert rollback_log == ["rollback_2", "rollback_1", "rollback_0"]
    print(f"回滚顺序: {rollback_log}")

    print("\n记录操作回滚测试通过!")
    return True


def test_current_transaction():
    """测试当前事务"""
    print_section("当前事务")

    manager = TransactionManager()

    # 无事务
    assert manager.get_current() is None
    print("无当前事务: True")

    # 开始事务
    ctx = manager.begin()
    current = manager.get_current()
    assert current is not None
    assert current.transaction_id == ctx.transaction_id
    print(f"当前事务ID: {current.transaction_id}")

    # 提交后
    manager.commit(ctx.transaction_id)
    assert manager.get_current() is None
    print("提交后无当前事务: True")

    print("\n当前事务测试通过!")
    return True


def test_transaction_isolation():
    """测试事务隔离级别"""
    print_section("事务隔离级别")

    manager = TransactionManager()

    ctx1 = manager.begin(isolation=TransactionIsolation.READ_UNCOMMITTED)
    assert ctx1.isolation == TransactionIsolation.READ_UNCOMMITTED
    manager.commit(ctx1.transaction_id)

    ctx2 = manager.begin(isolation=TransactionIsolation.SERIALIZABLE)
    assert ctx2.isolation == TransactionIsolation.SERIALIZABLE
    manager.commit(ctx2.transaction_id)

    print(f"READ_UNCOMMITTED: {ctx1.isolation.value}")
    print(f"SERIALIZABLE: {ctx2.isolation.value}")

    print("\n事务隔离级别测试通过!")
    return True


def test_nested_transaction():
    """测试嵌套事务"""
    print_section("嵌套事务")

    manager = TransactionManager()

    # 外层事务
    parent = manager.begin()
    assert manager.get_current().transaction_id == parent.transaction_id

    # 内层事务
    child = manager.begin(parent_id=parent.transaction_id)
    assert child.parent_id == parent.transaction_id
    assert manager.get_current().transaction_id == child.transaction_id

    # 提交内层
    manager.commit(child.transaction_id)
    # 当前应回到外层
    assert manager.get_current().transaction_id == parent.transaction_id

    # 提交外层
    manager.commit(parent.transaction_id)
    assert manager.get_current() is None

    print("嵌套事务生命周期: 正确")

    print("\n嵌套事务测试通过!")
    return True


def test_global_manager():
    """测试全局事务管理器"""
    print_section("全局事务管理器")

    manager = get_global_transaction_manager()
    ctx = manager.begin()
    assert ctx.transaction_id is not None
    manager.commit(ctx.transaction_id)
    print("全局事务管理器可用")

    print("\n全局事务管理器测试通过!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("阶段35: 事务接口标准化 — 验证测试")
    print("="*60)

    tests = [
        test_basic_transaction,
        test_transactional_decorator,
        test_participant_two_phase,
        test_prepare_failure,
        test_savepoint,
        test_recorded_operations_rollback,
        test_current_transaction,
        test_transaction_isolation,
        test_nested_transaction,
        test_global_manager,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"\n[失败] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("="*60)
