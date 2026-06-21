"""
阶段138: 配置热更新 — 运行时配置 测试

第一性原理验证:
1. 可配置性 — 运行时调整配置
2. 无中断性 — 变更不中断服务
3. 一致性 — 原子性传播
4. 可追溯性 — 历史记录和回滚
5. 安全性 — 验证防止无效配置
"""

import os
import sys
import json
import time
import tempfile
import threading
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from self_evolving_agent.core.config_hot_reload import (
    ConfigChangeType,
    ConfigChangeRecord,
    ConfigHistory,
    ConfigTransaction,
    ConfigValidator,
    ConfigWatcher,
    ConfigReloadHandler,
    HotReloadManager,
    create_hot_reload_manager,
    get_global_hot_reload_manager,
)


# ============================================================
# 1. ConfigHistory 测试
# ============================================================

class TestConfigHistory:
    """配置历史管理测试"""

    def test_record_and_query(self):
        """测试记录和查询"""
        history = ConfigHistory()
        record = ConfigChangeRecord(
            change_id="chg_1",
            change_type=ConfigChangeType.SET,
            key="test.key",
            old_value=None,
            new_value=42,
            timestamp=time.time(),
        )
        history.record(record)
        assert history.count() == 1

        records = history.get_records()
        assert len(records) == 1
        assert records[0].key == "test.key"

    def test_query_by_key(self):
        """测试按键查询"""
        history = ConfigHistory()
        for i in range(5):
            history.record(ConfigChangeRecord(
                change_id=f"chg_{i}",
                change_type=ConfigChangeType.SET,
                key=f"key.{i % 2}",
                old_value=None,
                new_value=i,
                timestamp=time.time(),
            ))
        records = history.get_records(key="key.0")
        assert len(records) == 3
        assert all(r.key == "key.0" for r in records)

    def test_query_by_source(self):
        """测试按来源查询"""
        history = ConfigHistory()
        history.record(ConfigChangeRecord(
            change_id="chg_1", change_type=ConfigChangeType.SET,
            key="k", old_value=None, new_value=1, timestamp=time.time(), source="manual"
        ))
        history.record(ConfigChangeRecord(
            change_id="chg_2", change_type=ConfigChangeType.SET,
            key="k", old_value=1, new_value=2, timestamp=time.time(), source="file_watcher"
        ))
        assert len(history.get_records(source="manual")) == 1
        assert len(history.get_records(source="file_watcher")) == 1

    def test_get_by_id(self):
        """测试按ID查询"""
        history = ConfigHistory()
        record = ConfigChangeRecord(
            change_id="chg_unique", change_type=ConfigChangeType.SET,
            key="k", old_value=None, new_value=1, timestamp=time.time()
        )
        history.record(record)
        assert history.get_record("chg_unique") is not None
        assert history.get_record("nonexistent") is None

    def test_get_latest(self):
        """测试获取最新记录"""
        history = ConfigHistory()
        for i in range(3):
            history.record(ConfigChangeRecord(
                change_id=f"chg_{i}", change_type=ConfigChangeType.SET,
                key="k", old_value=i, new_value=i + 1, timestamp=time.time() + i
            ))
        latest = history.get_latest()
        assert latest is not None
        assert latest.new_value == 3

    def test_max_records_limit(self):
        """测试最大记录限制"""
        history = ConfigHistory(max_records=5)
        for i in range(10):
            history.record(ConfigChangeRecord(
                change_id=f"chg_{i}", change_type=ConfigChangeType.SET,
                key="k", old_value=i, new_value=i + 1, timestamp=time.time()
            ))
        assert history.count() == 5

    def test_clear(self):
        """测试清空历史"""
        history = ConfigHistory()
        history.record(ConfigChangeRecord(
            change_id="chg_1", change_type=ConfigChangeType.SET,
            key="k", old_value=None, new_value=1, timestamp=time.time()
        ))
        history.clear()
        assert history.count() == 0

    def test_next_id_unique(self):
        """测试ID生成唯一性"""
        history = ConfigHistory()
        ids = {history.next_id() for _ in range(100)}
        assert len(ids) == 100

    def test_to_dict(self):
        """测试记录转字典"""
        record = ConfigChangeRecord(
            change_id="chg_1", change_type=ConfigChangeType.SET,
            key="k", old_value=None, new_value=42, timestamp=time.time(),
            source="test", success=True
        )
        d = record.to_dict()
        assert d["change_id"] == "chg_1"
        assert d["change_type"] == "set"
        assert d["key"] == "k"
        assert d["new_value"] == 42
        assert d["source"] == "test"


# ============================================================
# 2. ConfigValidator 测试
# ============================================================

class TestConfigValidator:
    """配置验证器测试"""

    def test_add_type_rule(self):
        """测试类型检查规则"""
        validator = ConfigValidator()
        validator.add_type_rule("count", int)
        assert validator.validate("count", 42) is None
        assert validator.validate("count", "not_int") is not None

    def test_add_range_rule(self):
        """测试范围检查规则"""
        validator = ConfigValidator()
        validator.add_range_rule("level", min_val=0, max_val=100)
        assert validator.validate("level", 50) is None
        assert validator.validate("level", -1) is not None
        assert validator.validate("level", 101) is not None

    def test_add_choice_rule(self):
        """测试枚举选择规则"""
        validator = ConfigValidator()
        validator.add_choice_rule("env", ["dev", "staging", "prod"])
        assert validator.validate("env", "dev") is None
        assert validator.validate("env", "invalid") is not None

    def test_custom_rule(self):
        """测试自定义规则"""
        validator = ConfigValidator()
        validator.add_rule("name", lambda v: None if v and len(v) >= 3 else "Too short")
        assert validator.validate("name", "abc") is None
        assert validator.validate("name", "ab") is not None
        assert validator.validate("name", "") is not None

    def test_validate_all(self):
        """测试批量验证"""
        validator = ConfigValidator()
        validator.add_type_rule("count", int)
        validator.add_range_rule("level", min_val=0, max_val=10)
        errors = validator.validate_all({"count": 42, "level": 5})
        assert len(errors) == 0
        errors = validator.validate_all({"count": "bad", "level": 100})
        assert len(errors) == 2

    def test_no_rules_passes(self):
        """测试无规则时验证通过"""
        validator = ConfigValidator()
        assert validator.validate("any_key", "any_value") is None

    def test_rule_exception_handled(self):
        """测试规则异常处理"""
        validator = ConfigValidator()
        def bad_rule(v):
            raise RuntimeError("bad rule")
        validator.add_rule("k", bad_rule)
        result = validator.validate("k", "v")
        assert result is not None
        assert "bad rule" in result

    def test_get_rules(self):
        """测试获取规则统计"""
        validator = ConfigValidator()
        validator.add_type_rule("a", int)
        validator.add_range_rule("a", min_val=0, max_val=10)
        validator.add_type_rule("b", str)
        rules = validator.get_rules()
        assert rules["a"] == 2
        assert rules["b"] == 1


# ============================================================
# 3. HotReloadManager 基本操作测试
# ============================================================

class TestHotReloadManagerBasic:
    """热更新管理器基本操作测试"""

    def test_set_and_get(self):
        """测试设置和获取"""
        mgr = create_hot_reload_manager()
        ok, err = mgr.set("key1", "value1")
        assert ok
        assert err is None
        assert mgr.get("key1") == "value1"

    def test_nested_set_and_get(self):
        """测试嵌套配置"""
        mgr = create_hot_reload_manager()
        mgr.set("module.submodule.param", 42)
        assert mgr.get("module.submodule.param") == 42
        assert mgr.get("module.submodule") == {"param": 42}
        assert mgr.get("module") == {"submodule": {"param": 42}}

    def test_get_with_default(self):
        """测试默认值"""
        mgr = create_hot_reload_manager()
        assert mgr.get("nonexistent", "default") == "default"

    def test_has(self):
        """测试存在性检查"""
        mgr = create_hot_reload_manager()
        mgr.set("exists", True)
        assert mgr.has("exists")
        assert not mgr.has("not_exists")

    def test_delete(self):
        """测试删除"""
        mgr = create_hot_reload_manager()
        mgr.set("to_delete", "value")
        ok, _ = mgr.delete("to_delete")
        assert ok
        assert not mgr.has("to_delete")

    def test_delete_nonexistent(self):
        """测试删除不存在的键"""
        mgr = create_hot_reload_manager()
        ok, err = mgr.delete("nonexistent")
        assert not ok
        assert err is not None

    def test_snapshot(self):
        """测试快照"""
        mgr = create_hot_reload_manager()
        mgr.set("a", 1)
        mgr.set("b", 2)
        snap = mgr.snapshot()
        assert snap == {"a": 1, "b": 2}
        # 修改快照不应影响原配置
        snap["a"] = 999
        assert mgr.get("a") == 1

    def test_update_batch(self):
        """测试批量更新"""
        mgr = create_hot_reload_manager()
        ok, errors = mgr.update({"a": 1, "b": 2, "c": 3})
        assert ok
        assert len(errors) == 0
        assert mgr.get("a") == 1
        assert mgr.get("b") == 2
        assert mgr.get("c") == 3

    def test_update_with_validation_failure(self):
        """测试批量更新验证失败"""
        mgr = create_hot_reload_manager()
        mgr.validator.add_type_rule("a", int)
        ok, errors = mgr.update({"a": "not_int", "b": 2})
        assert not ok
        assert len(errors) > 0
        # 验证失败的键不应被设置
        assert not mgr.has("b")


# ============================================================
# 4. 验证集成测试
# ============================================================

class TestHotReloadManagerValidation:
    """热更新管理器验证集成测试"""

    def test_set_with_validation(self):
        """测试带验证的设置"""
        mgr = create_hot_reload_manager()
        mgr.validator.add_type_rule("count", int)
        ok, err = mgr.set("count", 42)
        assert ok
        ok, err = mgr.set("count", "bad")
        assert not ok
        assert err is not None
        assert mgr.get("count") == 42  # 原值不变

    def test_set_with_range_validation(self):
        """测试范围验证"""
        mgr = create_hot_reload_manager()
        mgr.validator.add_range_rule("level", min_val=0, max_val=100)
        ok, _ = mgr.set("level", 50)
        assert ok
        ok, err = mgr.set("level", 200)
        assert not ok
        assert err is not None


# ============================================================
# 5. 历史和回滚测试
# ============================================================

class TestHotReloadManagerHistory:
    """热更新管理器历史和回滚测试"""

    def test_history_recorded_on_set(self):
        """测试设置时记录历史"""
        mgr = create_hot_reload_manager()
        mgr.set("k", 1)
        history = mgr.get_history()
        assert len(history) == 1
        assert history[0]["key"] == "k"
        assert history[0]["new_value"] == 1

    def test_history_recorded_on_delete(self):
        """测试删除时记录历史"""
        mgr = create_hot_reload_manager()
        mgr.set("k", 1)
        mgr.delete("k")
        history = mgr.get_history()
        assert len(history) == 2
        assert history[1]["change_type"] == "delete"

    def test_rollback_set(self):
        """测试回滚设置操作"""
        mgr = create_hot_reload_manager()
        mgr.set("k", 1)
        mgr.set("k", 2)
        assert mgr.get("k") == 2

        history = mgr.get_history()
        # 回滚最后一次设置
        last_change_id = history[-1]["change_id"]
        ok, _ = mgr.rollback(last_change_id)
        assert ok
        assert mgr.get("k") == 1

    def test_rollback_delete(self):
        """测试回滚删除操作"""
        mgr = create_hot_reload_manager()
        mgr.set("k", "value")
        mgr.delete("k")
        assert not mgr.has("k")

        history = mgr.get_history()
        delete_id = history[-1]["change_id"]
        ok, _ = mgr.rollback(delete_id)
        assert ok
        assert mgr.get("k") == "value"

    def test_rollback_nonexistent(self):
        """测试回滚不存在的变更"""
        mgr = create_hot_reload_manager()
        ok, err = mgr.rollback("nonexistent_id")
        assert not ok
        assert err is not None

    def test_rollback_to_timestamp(self):
        """测试回滚到时间点"""
        mgr = create_hot_reload_manager()
        mgr.set("k1", 1)
        t = time.time()
        time.sleep(0.01)
        mgr.set("k2", 2)
        mgr.set("k3", 3)

        count = mgr.rollback_to(t)
        assert count == 2
        assert mgr.get("k1") == 1
        assert not mgr.has("k2")
        assert not mgr.has("k3")

    def test_history_query_by_key(self):
        """测试按键查询历史"""
        mgr = create_hot_reload_manager()
        mgr.set("a", 1)
        mgr.set("b", 2)
        mgr.set("a", 3)
        history = mgr.get_history(key="a")
        assert len(history) == 2
        assert all(h["key"] == "a" for h in history)


# ============================================================
# 6. 订阅通知测试
# ============================================================

class TestHotReloadManagerSubscription:
    """热更新管理器订阅通知测试"""

    def test_subscribe_and_notify(self):
        """测试订阅和通知"""
        mgr = create_hot_reload_manager()
        received = []
        mgr.subscribe("key", lambda k, old, new: received.append((k, old, new)))

        mgr.set("key", "value")
        assert len(received) == 1
        assert received[0] == ("key", None, "value")

    def test_subscribe_parent_namespace(self):
        """测试父级命名空间订阅"""
        mgr = create_hot_reload_manager()
        received = []
        mgr.subscribe("module", lambda k, old, new: received.append((k, old, new)))

        mgr.set("module.sub.param", 42)
        assert len(received) == 1
        assert received[0][0] == "module.sub.param"

    def test_unsubscribe(self):
        """测试取消订阅"""
        mgr = create_hot_reload_manager()
        received = []

        def callback(k, old, new):
            received.append(new)

        mgr.subscribe("key", callback)
        mgr.set("key", 1)
        assert len(received) == 1

        mgr.unsubscribe("key", callback)
        mgr.set("key", 2)
        assert len(received) == 1  # 未增加

    def test_no_notify_on_same_value(self):
        """测试相同值不通知（通过历史判断）"""
        mgr = create_hot_reload_manager()
        mgr.set("k", 1)
        initial_count = len(mgr.get_history())
        # 设置相同值仍会记录（因为set是无条件的）
        mgr.set("k", 1)
        assert len(mgr.get_history()) == initial_count + 1


# ============================================================
# 7. 事务测试
# ============================================================

class TestConfigTransaction:
    """配置事务测试"""

    def test_transaction_commit(self):
        """测试事务提交"""
        mgr = create_hot_reload_manager()
        tx = mgr.transaction()
        tx.set("a", 1)
        tx.set("b", 2)
        tx.set("c", 3)

        ok, errors = tx.commit()
        assert ok
        assert len(errors) == 0
        assert mgr.get("a") == 1
        assert mgr.get("b") == 2
        assert mgr.get("c") == 3

    def test_transaction_rollback_on_validation_failure(self):
        """测试验证失败时回滚"""
        mgr = create_hot_reload_manager()
        mgr.validator.add_type_rule("b", int)

        tx = mgr.transaction()
        tx.set("a", 1)
        tx.set("b", "not_int")  # 验证失败
        tx.set("c", 3)

        ok, errors = tx.commit()
        assert not ok
        assert len(errors) > 0
        # 所有变更都不应生效
        assert not mgr.has("a")
        assert not mgr.has("b")
        assert not mgr.has("c")

    def test_transaction_manual_rollback(self):
        """测试手动回滚"""
        mgr = create_hot_reload_manager()
        tx = mgr.transaction()
        tx.set("a", 1)
        tx.rollback()

        assert not mgr.has("a")

    def test_transaction_double_commit_raises(self):
        """测试重复提交抛异常"""
        mgr = create_hot_reload_manager()
        tx = mgr.transaction()
        tx.set("a", 1)
        tx.commit()
        with pytest.raises(RuntimeError):
            tx.commit()

    def test_transaction_after_rollback_raises(self):
        """测试回滚后操作抛异常"""
        mgr = create_hot_reload_manager()
        tx = mgr.transaction()
        tx.rollback()
        with pytest.raises(RuntimeError):
            tx.set("a", 1)

    def test_transaction_with_delete(self):
        """测试事务中的删除"""
        mgr = create_hot_reload_manager()
        mgr.set("to_del", "value")

        tx = mgr.transaction()
        tx.delete("to_del")
        tx.set("new", "value")
        ok, _ = tx.commit()
        assert ok
        assert not mgr.has("to_del")
        assert mgr.get("new") == "value"


# ============================================================
# 8. 文件监视器测试
# ============================================================

class TestConfigWatcher:
    """配置文件监视器测试"""

    def test_watch_existing_file(self):
        """测试监视存在的文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "value"}, f)
            path = f.name

        try:
            watcher = ConfigWatcher(poll_interval=0.1)
            received = []
            watcher.watch(path, lambda p, d: received.append((p, d)))

            # 修改文件
            time.sleep(0.2)
            with open(path, "w") as f:
                json.dump({"key": "new_value"}, f)

            time.sleep(0.5)
            watcher.check_once()
            assert len(received) > 0
            watcher.stop()
        finally:
            os.unlink(path)

    def test_watch_nonexistent_file(self):
        """测试监视不存在的文件"""
        watcher = ConfigWatcher()
        result = watcher.watch("/nonexistent/path/file.json", lambda p, d: None)
        assert not result

    def test_unwatch(self):
        """测试停止监视"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"k": "v"}, f)
            path = f.name

        try:
            watcher = ConfigWatcher()
            watcher.watch(path, lambda p, d: None)
            assert watcher.is_watching(path)
            watcher.unwatch(path)
            assert not watcher.is_watching(path)
            watcher.stop()
        finally:
            os.unlink(path)

    def test_check_once_no_change(self):
        """测试手动检查无变更"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"k": "v"}, f)
            path = f.name

        try:
            watcher = ConfigWatcher()
            watcher.watch(path, lambda p, d: None)
            changed = watcher.check_once()
            assert changed == 0
            watcher.stop()
        finally:
            os.unlink(path)

    def test_check_once_with_change(self):
        """测试手动检查有变更"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"k": "v"}, f)
            path = f.name

        try:
            watcher = ConfigWatcher(poll_interval=999.0)
            received = []
            watcher.watch(path, lambda p, d: received.append(d))
            # 立即停止轮询线程，避免与文件写入竞争
            watcher.stop()

            # 修改文件
            with open(path, "w") as f:
                json.dump({"k": "new"}, f)

            changed = watcher.check_once()
            assert changed == 1
            assert len(received) == 1
            assert received[0] == {"k": "new"}
        finally:
            os.unlink(path)

    def test_get_watched_files(self):
        """测试获取监视文件列表"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"k": "v"}, f)
            path = f.name

        try:
            watcher = ConfigWatcher()
            watcher.watch(path, lambda p, d: None)
            files = watcher.get_watched_files()
            assert len(files) == 1
            assert path in files[0] or files[0] in path
            watcher.stop()
        finally:
            os.unlink(path)


# ============================================================
# 9. 文件监视集成测试
# ============================================================

class TestHotReloadManagerFileWatch:
    """热更新管理器文件监视集成测试"""

    def test_watch_file_loads_initial(self):
        """测试监视文件时加载初始内容"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "initial"}, f)
            path = f.name

        try:
            mgr = create_hot_reload_manager()
            result = mgr.watch_file(path)
            assert result
            assert mgr.get("key") == "initial"
            mgr.stop_watcher()
        finally:
            os.unlink(path)

    def test_watch_file_with_namespace(self):
        """测试带命名空间的文件监视"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "namespaced"}, f)
            path = f.name

        try:
            mgr = create_hot_reload_manager()
            mgr.watch_file(path, namespace="module1")
            assert mgr.get("module1.key") == "namespaced"
            mgr.stop_watcher()
        finally:
            os.unlink(path)

    def test_watch_file_detects_changes(self):
        """测试检测文件变更"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "v1"}, f)
            path = f.name

        try:
            mgr = create_hot_reload_manager()
            mgr.watch_file(path)
            assert mgr.get("key") == "v1"

            # 修改文件
            with open(path, "w") as f:
                json.dump({"key": "v2"}, f)

            # 手动触发检查
            mgr.watcher.check_once()
            assert mgr.get("key") == "v2"
            mgr.stop_watcher()
        finally:
            os.unlink(path)

    def test_unwatch_file(self):
        """测试停止文件监视"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"k": "v"}, f)
            path = f.name

        try:
            mgr = create_hot_reload_manager()
            mgr.watch_file(path)
            assert mgr.watcher.is_watching(path)
            mgr.unwatch_file(path)
            assert not mgr.watcher.is_watching(path)
            mgr.stop_watcher()
        finally:
            os.unlink(path)


# ============================================================
# 10. 组件重载处理器测试
# ============================================================

class MockReloadHandler(ConfigReloadHandler):
    """模拟重载处理器"""

    def __init__(self, name: str):
        self._name = name
        self.changes = []
        self.reload_called = False
        self.reload_success = True
        self.reload_error = None

    @property
    def name(self) -> str:
        return self._name

    def on_config_change(self, key: str, old_value: Any, new_value: Any):
        self.changes.append((key, old_value, new_value))
        return True, None

    def on_reload_all(self):
        self.reload_called = True
        return self.reload_success, self.reload_error


class FailingHandler(ConfigReloadHandler):
    """总是失败的重载处理器"""

    @property
    def name(self) -> str:
        return "failing"

    def on_config_change(self, key: str, old_value: Any, new_value: Any):
        return False, "Handler failed"

    def on_reload_all(self):
        return False, "Reload failed"


class TestReloadHandler:
    """组件重载处理器测试"""

    def test_register_and_notify(self):
        """测试注册和通知"""
        mgr = create_hot_reload_manager()
        handler = MockReloadHandler("test_handler")
        mgr.register_handler(handler)

        mgr.set("key", "value")
        assert len(handler.changes) == 1
        assert handler.changes[0][0] == "key"

    def test_unregister(self):
        """测试注销处理器"""
        mgr = create_hot_reload_manager()
        handler = MockReloadHandler("test_handler")
        mgr.register_handler(handler)
        mgr.unregister_handler("test_handler")

        mgr.set("key", "value")
        assert len(handler.changes) == 0

    def test_reload_all(self):
        """测试全量重载"""
        mgr = create_hot_reload_manager()
        handler = MockReloadHandler("h1")
        mgr.register_handler(handler)

        results = mgr.reload_all()
        assert "h1" in results
        assert results["h1"][0] is True
        assert handler.reload_called

    def test_reload_all_with_failure(self):
        """测试全量重载失败"""
        mgr = create_hot_reload_manager()
        handler = FailingHandler()
        mgr.register_handler(handler)

        results = mgr.reload_all()
        assert results["failing"][0] is False
        assert "Reload failed" in results["failing"][1]

    def test_handler_exception_isolated(self):
        """测试处理器异常隔离"""

        class ExceptionHandler(ConfigReloadHandler):
            @property
            def name(self): return "exc"

            def on_config_change(self, key, old, new):
                raise RuntimeError("boom")

        mgr = create_hot_reload_manager()
        mgr.register_handler(ExceptionHandler())
        # 不应抛出异常
        ok, _ = mgr.set("key", "value")
        assert ok

    def test_multiple_handlers(self):
        """测试多个处理器"""
        mgr = create_hot_reload_manager()
        h1 = MockReloadHandler("h1")
        h2 = MockReloadHandler("h2")
        mgr.register_handler(h1)
        mgr.register_handler(h2)

        mgr.set("key", "value")
        assert len(h1.changes) == 1
        assert len(h2.changes) == 1


# ============================================================
# 11. 导入导出测试
# ============================================================

class TestImportExport:
    """导入导出测试"""

    def test_load_from_dict(self):
        """测试从字典加载"""
        mgr = create_hot_reload_manager()
        ok, errors = mgr.load_from_dict({"a": 1, "b": 2})
        assert ok
        assert mgr.get("a") == 1
        assert mgr.get("b") == 2

    def test_load_from_file(self):
        """测试从文件加载"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "file_value"}, f)
            path = f.name

        try:
            mgr = create_hot_reload_manager()
            ok, errors = mgr.load_from_file(path)
            assert ok
            assert mgr.get("key") == "file_value"
        finally:
            os.unlink(path)

    def test_load_from_nonexistent_file(self):
        """测试加载不存在的文件"""
        mgr = create_hot_reload_manager()
        ok, errors = mgr.load_from_file("/nonexistent/path.json")
        assert not ok
        assert len(errors) > 0

    def test_save_to_file(self):
        """测试保存到文件"""
        mgr = create_hot_reload_manager()
        mgr.set("key", "value")
        mgr.set("nested.key", 42)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            ok, err = mgr.save_to_file(path)
            assert ok
            with open(path, "r") as f:
                data = json.load(f)
            assert data["key"] == "value"
            assert data["nested"]["key"] == 42
        finally:
            os.unlink(path)


# ============================================================
# 12. 统计和第一性原理测试
# ============================================================

class TestStatsAndPrinciples:
    """统计和第一性原理测试"""

    def test_get_stats(self):
        """测试获取统计"""
        mgr = create_hot_reload_manager()
        mgr.set("a", 1)
        mgr.set("b", 2)
        mgr.validator.add_type_rule("a", int)

        stats = mgr.get_stats()
        assert stats["total_keys"] == 2
        assert stats["history_count"] == 2
        assert "a" in stats["validation_rules"]

    def test_get_history_with_limit(self):
        """测试获取历史带限制"""
        mgr = create_hot_reload_manager()
        for i in range(10):
            mgr.set("k", i)
        history = mgr.get_history(limit=5)
        assert len(history) == 5

    def test_configurability_principle(self):
        """第一性原理：可配置性 — 运行时调整"""
        mgr = create_hot_reload_manager()
        # 初始配置
        mgr.set("threshold", 100)
        assert mgr.get("threshold") == 100

        # 运行时调整
        mgr.set("threshold", 200)
        assert mgr.get("threshold") == 200

        # 调整不影响其他配置
        mgr.set("other", "value")
        assert mgr.get("threshold") == 200

    def test_consistency_principle(self):
        """第一性原理：一致性 — 原子性传播"""
        mgr = create_hot_reload_manager()
        # 事务保证原子性
        tx = mgr.transaction()
        tx.set("a", 1)
        tx.set("b", 2)
        tx.set("c", 3)
        ok, _ = tx.commit()
        assert ok
        # 所有变更同时生效
        assert mgr.get("a") == 1
        assert mgr.get("b") == 2
        assert mgr.get("c") == 3

    def test_traceability_principle(self):
        """第一性原理：可追溯性 — 历史记录"""
        mgr = create_hot_reload_manager()
        mgr.set("k", 1)
        mgr.set("k", 2)
        mgr.set("k", 3)

        history = mgr.get_history(key="k")
        assert len(history) == 3
        # 可以追溯每次变更
        assert history[0]["new_value"] == 1
        assert history[1]["old_value"] == 1
        assert history[2]["new_value"] == 3

    def test_safety_principle(self):
        """第一性原理：安全性 — 验证防止无效配置"""
        mgr = create_hot_reload_manager()
        mgr.validator.add_range_rule("port", min_val=1, max_val=65535)

        # 有效配置
        ok, _ = mgr.set("port", 8080)
        assert ok
        assert mgr.get("port") == 8080

        # 无效配置被拒绝
        ok, err = mgr.set("port", 99999)
        assert not ok
        assert err is not None
        # 原值不变
        assert mgr.get("port") == 8080

    def test_no_interruption_principle(self):
        """第一性原理：无中断性 — 变更不中断读取"""
        mgr = create_hot_reload_manager()
        mgr.set("k", "initial")

        results = []
        def reader():
            for _ in range(100):
                results.append(mgr.get("k"))
                time.sleep(0.001)

        t = threading.Thread(target=reader)
        t.start()

        # 同时修改配置
        for i in range(100):
            mgr.set("k", f"value_{i}")

        t.join()
        # 读取操作应全部成功（不抛异常）
        assert len(results) == 100
        assert all(r is not None for r in results)

    def test_global_manager_singleton(self):
        """测试全局管理器单例"""
        mgr1 = get_global_hot_reload_manager()
        mgr2 = get_global_hot_reload_manager()
        assert mgr1 is mgr2


# ============================================================
# 13. 边界条件测试
# ============================================================

class TestEdgeCases:
    """边界条件测试"""

    def test_empty_key(self):
        """测试空键"""
        mgr = create_hot_reload_manager()
        ok, _ = mgr.set("", "value")
        assert ok
        assert mgr.get("") == "value"

    def test_none_value(self):
        """测试None值"""
        mgr = create_hot_reload_manager()
        mgr.set("k", None)
        # None是有效值
        assert mgr.get("k") is None
        assert mgr.has("k")

    def test_complex_nested_value(self):
        """测试复杂嵌套值"""
        mgr = create_hot_reload_manager()
        complex_value = {
            "list": [1, 2, 3],
            "nested": {"a": {"b": {"c": "deep"}}},
            "mixed": [{"x": 1}, {"y": 2}],
        }
        mgr.set("complex", complex_value)
        result = mgr.get("complex")
        assert result == complex_value

    def test_deeply_nested_key(self):
        """测试深层嵌套键"""
        mgr = create_hot_reload_manager()
        mgr.set("a.b.c.d.e.f.g", "deep")
        assert mgr.get("a.b.c.d.e.f.g") == "deep"

    def test_overwrite_with_different_type(self):
        """测试用不同类型覆盖"""
        mgr = create_hot_reload_manager()
        mgr.set("k", "string")
        mgr.set("k", 42)
        assert mgr.get("k") == 42

    def test_unicode_values(self):
        """测试Unicode值"""
        mgr = create_hot_reload_manager()
        mgr.set("chinese", "你好世界")
        mgr.set("emoji", "🚀")
        assert mgr.get("chinese") == "你好世界"
        assert mgr.get("emoji") == "🚀"

    def test_concurrent_access(self):
        """测试并发访问"""
        mgr = create_hot_reload_manager()
        errors = []

        def writer():
            try:
                for i in range(50):
                    mgr.set(f"key_{i}", i)
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for i in range(50):
                    mgr.get(f"key_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(3)]
        threads += [threading.Thread(target=reader) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_large_config(self):
        """测试大量配置"""
        mgr = create_hot_reload_manager()
        for i in range(1000):
            mgr.set(f"key_{i}", i)
        assert mgr.get("key_500") == 500
        stats = mgr.get_stats()
        assert stats["total_keys"] >= 1000
