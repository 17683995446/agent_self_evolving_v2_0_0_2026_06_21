"""
阶段53验证: 数据版本控制接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("dv", "/workspace/self_evolving_agent/core/data_versioning.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["dv"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段53验证: 数据版本控制接口标准化")
print("=" * 60)

# 测试1: 提交版本
def test_commit():
    ds = mod.create_versioned_dataset("ds1")
    v1 = ds.commit({"a": 1, "b": 2}, author="alice", comment="init")
    assert v1.version_id.startswith("v1_")
    assert v1.parent_id is None
    assert v1.author == "alice"
    assert v1.data_hash != ""
    print("  [test_commit] 提交版本 OK")

# 测试2: 检出历史版本
def test_checkout():
    ds = mod.create_versioned_dataset("ds2")
    v1 = ds.commit([1, 2, 3], author="alice", comment="v1")
    v2 = ds.commit([1, 2, 3, 4], author="bob", comment="v2")

    data1 = ds.checkout(v1.version_id)
    data2 = ds.checkout(v2.version_id)
    assert data1 == [1, 2, 3]
    assert data2 == [1, 2, 3, 4]
    print("  [test_checkout] 检出历史版本 OK")

# 测试3: 回滚
def test_rollback():
    ds = mod.create_versioned_dataset("ds3")
    v1 = ds.commit([1], author="alice", comment="v1")
    v2 = ds.commit([2], author="alice", comment="v2")
    assert ds.get_current_version().version_id == v2.version_id

    ds.rollback(v1.version_id)
    assert ds.get_current_version().version_id == v1.version_id
    print("  [test_rollback] 回滚 OK")

# 测试4: 标签
def test_tags():
    ds = mod.create_versioned_dataset("ds4")
    v1 = ds.commit([1], author="alice", comment="v1", tags=["release"])
    ds.tag(v1.version_id, "stable")

    versions = ds.find_by_tag("stable")
    assert len(versions) == 1
    assert "stable" in versions[0].tags
    print("  [test_tags] 标签 OK")

# 测试5: 差异比较
def test_diff():
    ds = mod.create_versioned_dataset("ds5")
    v1 = ds.commit([1, 2], author="alice", comment="v1")
    v2 = ds.commit([1, 2, 3], author="alice", comment="v2")

    diff = ds.diff(v1.version_id, v2.version_id)
    assert diff["same"] is False
    assert diff["size_b"] > diff["size_a"]
    print("  [test_diff] 差异比较 OK")

# 测试6: 版本控制器
def test_version_controller():
    vc = mod.create_version_controller()
    ds = vc.create_dataset("dataset_a")
    ds.commit([1], author="alice", comment="init")

    assert "dataset_a" in vc.list_datasets()
    retrieved = vc.get_dataset("dataset_a")
    assert retrieved.get_stats()["total_versions"] == 1
    print("  [test_version_controller] 版本控制器 OK")

# 测试7: 历史记录
def test_history():
    ds = mod.create_versioned_dataset("ds6")
    ds.commit([1], author="alice", comment="first")
    ds.commit([2], author="bob", comment="second")
    ds.commit([3], author="alice", comment="third")

    history = ds.get_history()
    assert len(history) == 3
    assert history[0].comment == "third"  # 倒序
    print("  [test_history] 历史记录 OK")

if __name__ == "__main__":
    test_commit()
    test_checkout()
    test_rollback()
    test_tags()
    test_diff()
    test_version_controller()
    test_history()
    print("=" * 60)
    print("阶段53验证通过 ✓")
    print("=" * 60)
