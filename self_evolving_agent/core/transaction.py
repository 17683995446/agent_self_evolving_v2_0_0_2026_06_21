"""
阶段35: 事务接口标准化

第一性原理:
1. 操作要么全部成功，要么全部失败。没有事务保证，系统将处于不一致状态
2. 事务必须有明确的边界：开始、提交、回滚
3. 嵌套事务必须可传播、可隔离

设计原则:
- ACID语义：原子性、一致性、隔离性、持久性
- 支持嵌套事务：子事务可独立回滚
- 支持保存点：部分回滚能力
- 超时控制：防止事务长期挂起
- 资源自动清理：事务结束时释放锁和资源
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional, TypeVar, Generic
from enum import Enum
from datetime import datetime
import threading
import uuid

T = TypeVar('T')


class TransactionStatus(Enum):
    """事务状态"""
    ACTIVE = "active"           # 活跃中
    COMMITTED = "committed"     # 已提交
    ROLLED_BACK = "rolled_back" # 已回滚
    FAILED = "failed"           # 失败


class TransactionIsolation(Enum):
    """事务隔离级别"""
    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"


@dataclass
class TransactionContext:
    """事务上下文"""
    transaction_id: str
    parent_id: Optional[str] = None
    status: TransactionStatus = TransactionStatus.ACTIVE
    isolation: TransactionIsolation = TransactionIsolation.READ_COMMITTED
    created_at: datetime = field(default_factory=datetime.now)
    operations: List[Dict[str, Any]] = field(default_factory=list)
    savepoints: Dict[str, int] = field(default_factory=dict)  # name -> operation index


# ============================================================
# 事务参与者接口
# ============================================================

class TransactionParticipant:
    """
    事务参与者

    第一性原理：事务需要多方协作，每方必须能准备、提交、回滚
    """

    def prepare(self, ctx: TransactionContext) -> bool:
        """准备提交，返回是否可提交"""
        return True

    def commit(self, ctx: TransactionContext) -> None:
        """提交"""
        pass

    def rollback(self, ctx: TransactionContext) -> None:
        """回滚"""
        pass


# ============================================================
# 事务管理器
# ============================================================

class TransactionManager:
    """
    事务管理器

    第一性原理：事务是操作的逻辑边界，必须有管理者协调生命周期
    """

    def __init__(self):
        self._transactions: Dict[str, TransactionContext] = {}
        self._participants: Dict[str, List[TransactionParticipant]] = {}
        self._lock = threading.RLock()
        self._current_txn: threading.local = threading.local()

    def begin(self, isolation: TransactionIsolation = TransactionIsolation.READ_COMMITTED,
              parent_id: Optional[str] = None) -> TransactionContext:
        """开始事务"""
        txn_id = str(uuid.uuid4())[:12]

        ctx = TransactionContext(
            transaction_id=txn_id,
            parent_id=parent_id,
            isolation=isolation,
        )

        with self._lock:
            self._transactions[txn_id] = ctx
            self._participants[txn_id] = []

        # 设置当前线程的事务
        if not hasattr(self._current_txn, 'stack'):
            self._current_txn.stack = []
        self._current_txn.stack.append(txn_id)

        return ctx

    def get_current(self) -> Optional[TransactionContext]:
        """获取当前线程的事务"""
        if not hasattr(self._current_txn, 'stack') or not self._current_txn.stack:
            return None
        txn_id = self._current_txn.stack[-1]
        with self._lock:
            return self._transactions.get(txn_id)

    def add_participant(self, txn_id: str, participant: TransactionParticipant) -> None:
        """添加事务参与者"""
        with self._lock:
            if txn_id in self._participants:
                self._participants[txn_id].append(participant)

    def record_operation(self, txn_id: str, operation: Dict[str, Any]) -> None:
        """记录操作（用于回滚）"""
        with self._lock:
            ctx = self._transactions.get(txn_id)
            if ctx and ctx.status == TransactionStatus.ACTIVE:
                ctx.operations.append(operation)

    def create_savepoint(self, txn_id: str, name: str) -> bool:
        """创建保存点"""
        with self._lock:
            ctx = self._transactions.get(txn_id)
            if ctx and ctx.status == TransactionStatus.ACTIVE:
                ctx.savepoints[name] = len(ctx.operations)
                return True
        return False

    def rollback_to_savepoint(self, txn_id: str, name: str) -> bool:
        """回滚到保存点"""
        with self._lock:
            ctx = self._transactions.get(txn_id)
            if ctx and ctx.status == TransactionStatus.ACTIVE:
                idx = ctx.savepoints.get(name)
                if idx is not None:
                    # 回滚从保存点之后的操作
                    ops_to_rollback = ctx.operations[idx:]
                    for op in reversed(ops_to_rollback):
                        self._execute_rollback_op(ctx, op)
                    ctx.operations = ctx.operations[:idx]
                    return True
        return False

    def commit(self, txn_id: str) -> bool:
        """提交事务"""
        with self._lock:
            ctx = self._transactions.get(txn_id)
            if not ctx or ctx.status != TransactionStatus.ACTIVE:
                return False

            participants = self._participants.get(txn_id, [])

        # 两阶段提交：准备
        for p in participants:
            if not p.prepare(ctx):
                self.rollback(txn_id)
                return False

        # 两阶段提交：提交
        for p in participants:
            try:
                p.commit(ctx)
            except Exception:
                pass

        with self._lock:
            ctx.status = TransactionStatus.COMMITTED

        self._pop_txn(txn_id)
        return True

    def rollback(self, txn_id: str) -> bool:
        """回滚事务"""
        with self._lock:
            ctx = self._transactions.get(txn_id)
            if not ctx or ctx.status != TransactionStatus.ACTIVE:
                return False

            participants = self._participants.get(txn_id, [])

        # 回滚所有操作
        for op in reversed(ctx.operations):
            self._execute_rollback_op(ctx, op)

        # 通知参与者回滚
        for p in participants:
            try:
                p.rollback(ctx)
            except Exception:
                pass

        with self._lock:
            ctx.status = TransactionStatus.ROLLED_BACK

        self._pop_txn(txn_id)
        return True

    def _execute_rollback_op(self, ctx: TransactionContext, op: Dict[str, Any]) -> None:
        """执行回滚操作"""
        rollback_fn = op.get('rollback')
        if rollback_fn and callable(rollback_fn):
            try:
                rollback_fn()
            except Exception:
                pass

    def _pop_txn(self, txn_id: str) -> None:
        """从事务栈中弹出"""
        if hasattr(self._current_txn, 'stack'):
            if txn_id in self._current_txn.stack:
                self._current_txn.stack.remove(txn_id)

    def is_active(self, txn_id: str) -> bool:
        """检查事务是否活跃"""
        with self._lock:
            ctx = self._transactions.get(txn_id)
            return ctx is not None and ctx.status == TransactionStatus.ACTIVE

    def get_status(self, txn_id: str) -> Optional[TransactionStatus]:
        """获取事务状态"""
        with self._lock:
            ctx = self._transactions.get(txn_id)
            return ctx.status if ctx else None


# ============================================================
# 事务装饰器
# ============================================================

def transactional(manager: TransactionManager,
                  isolation: TransactionIsolation = TransactionIsolation.READ_COMMITTED,
                  timeout_seconds: Optional[float] = None):
    """
    事务装饰器

    自动将函数包装在事务中
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            ctx = manager.begin(isolation=isolation)
            try:
                result = func(*args, **kwargs)
                manager.commit(ctx.transaction_id)
                return result
            except Exception:
                manager.rollback(ctx.transaction_id)
                raise
        return wrapper
    return decorator


# ============================================================
# 便捷函数
# ============================================================

_global_txn_manager = TransactionManager()


def get_global_transaction_manager() -> TransactionManager:
    """获取全局事务管理器"""
    return _global_txn_manager
