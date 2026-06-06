"""
验证阶段53-57: 数据版本控制、联邦学习、边缘计算、模型解释性、持续集成
"""
import sys
import importlib.util
import time

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

dv = load_module("data_versioning", "/workspace/self_evolving_agent/core/data_versioning.py")
fl = load_module("federated_learning", "/workspace/self_evolving_agent/core/federated_learning.py")
ec = load_module("edge_computing", "/workspace/self_evolving_agent/core/edge_computing.py")
exp = load_module("explainability", "/workspace/self_evolving_agent/core/explainability.py")
ci = load_module("ci_engine", "/workspace/self_evolving_agent/core/ci_engine.py")

print("=" * 60)
print("验证阶段53-57")
print("=" * 60)

# 阶段53: 数据版本控制
def test_stage53():
    ds = dv.create_versioned_dataset("ds1")
    v1 = ds.commit([1, 2], author="alice", comment="init")
    v2 = ds.commit([1, 2, 3], author="bob", comment="add")
    assert ds.get_current_version().version_id == v2.version_id
    assert ds.checkout(v1.version_id) == [1, 2]
    ds.rollback(v1.version_id)
    assert ds.get_current_version().version_id == v1.version_id
    diff = ds.diff(v1.version_id, v2.version_id)
    assert diff["same"] is False
    print("  [阶段53] 数据版本控制 OK")

# 阶段54: 联邦学习
def test_stage54():
    server = fl.create_federated_server(fl.AggregationStrategyType.FEDAVG)
    c1 = fl.create_federated_client("c1")
    c2 = fl.create_federated_client("c2")
    server.register_client(c1)
    server.register_client(c2)
    result = server.run_round(min_clients=2)
    assert result["status"] == "completed"
    assert result["updates_received"] == 2
    stats = server.get_stats()
    assert stats["current_round"] == 1
    print("  [阶段54] 联邦学习 OK")

# 阶段55: 边缘计算
def test_stage55():
    registry = ec.create_edge_registry()
    d1 = ec.create_edge_device("edge1")
    registry.register(d1)
    task = ec.create_edge_task("t1", lambda x: x + 1, 5)
    assigned = registry.dispatch_task(task)
    assert assigned == "edge1"
    result = d1.execute_next()
    assert result["result"] == 6
    print("  [阶段55] 边缘计算 OK")

# 阶段56: 模型解释性
def test_stage56():
    explainer = exp.create_feature_importance_explainer(["f1", "f2"])
    explanation = explainer.explain({"f1": 10, "f2": 5}, prediction=1)
    assert explanation.explanation_type == exp.ExplanationType.FEATURE_IMPORTANCE
    assert len(explanation.feature_importances) == 2
    assert explanation.feature_importances[0].feature_name == "f1"
    print("  [阶段56] 模型解释性 OK")

# 阶段57: 持续集成
def test_stage57():
    pipeline = ci.create_pipeline("p1")
    pipeline.add_stage(ci.create_stage("build", lambda: "built"))
    pipeline.add_stage(ci.create_stage("test", lambda: "tested", dependencies=["build"]))
    engine = ci.create_ci_engine()
    engine.register_pipeline(pipeline)
    results = engine.run_pipeline("p1")
    assert results["build"].status == ci.StageStatus.SUCCESS
    assert results["test"].status == ci.StageStatus.SUCCESS
    assert pipeline.get_status() == ci.PipelineStatus.SUCCESS
    print("  [阶段57] 持续集成 OK")

if __name__ == "__main__":
    test_stage53()
    test_stage54()
    test_stage55()
    test_stage56()
    test_stage57()
    print("=" * 60)
    print("阶段53-57全部验证通过 ✓")
    print("=" * 60)
