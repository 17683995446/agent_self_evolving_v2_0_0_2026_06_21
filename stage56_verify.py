"""
阶段56验证: 模型解释性接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("exp", "/workspace/self_evolving_agent/core/explainability.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["exp"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段56验证: 模型解释性接口标准化")
print("=" * 60)

# 测试1: 特征重要性解释器（dict输入）
def test_feature_importance_dict():
    explainer = mod.create_feature_importance_explainer(["f1", "f2", "f3"])
    input_data = {"f1": 10, "f2": 5, "f3": -3}
    explanation = explainer.explain(input_data, prediction=1)
    assert explanation.explanation_type == mod.ExplanationType.FEATURE_IMPORTANCE
    assert len(explanation.feature_importances) == 3
    assert explanation.feature_importances[0].feature_name == "f1"  # 最大值
    assert explanation.confidence == 0.8
    print("  [test_feature_importance_dict] 特征重要性(dict) OK")

# 测试2: 特征重要性解释器（list输入）
def test_feature_importance_list():
    explainer = mod.create_feature_importance_explainer(["a", "b"])
    explanation = explainer.explain([5, -5], prediction=0)
    assert len(explanation.feature_importances) == 2
    assert abs(explanation.feature_importances[0].importance - 0.5) < 0.001
    print("  [test_feature_importance_list] 特征重要性(list) OK")

# 测试3: 反事实解释器
def test_counterfactual():
    def model_fn(data):
        return 1 if data.get("x", 0) + data.get("y", 0) > 5 else 0

    explainer = mod.create_counterfactual_explainer(model_fn, ["x", "y"])
    explanation = explainer.explain({"x": 3, "y": 2}, prediction=0)
    assert explanation.explanation_type == mod.ExplanationType.COUNTERFACTUAL
    assert any(f.importance > 0 for f in explanation.feature_importances)
    print("  [test_counterfactual] 反事实解释 OK")

# 测试4: 解释管理器
def test_explanation_manager():
    manager = mod.create_explanation_manager()
    explainer = mod.create_feature_importance_explainer(["a", "b"])
    manager.register("fi", explainer)
    assert "fi" in manager.list_explainers()

    explanation = manager.explain("fi", {"a": 1, "b": 2}, prediction=1)
    assert explanation is not None
    assert explanation.explanation_type == mod.ExplanationType.FEATURE_IMPORTANCE
    print("  [test_explanation_manager] 解释管理器 OK")

# 测试5: 批量解释
def test_batch_explain():
    explainer = mod.create_feature_importance_explainer(["f1", "f2"])
    explanations = explainer.explain_batch(
        [{"f1": 1, "f2": 2}, {"f1": 3, "f2": 1}],
        [1, 0]
    )
    assert len(explanations) == 2
    assert all(e.explanation_type == mod.ExplanationType.FEATURE_IMPORTANCE for e in explanations)
    print("  [test_batch_explain] 批量解释 OK")

# 测试6: 特征重要性排序
def test_importance_sorting():
    explainer = mod.create_feature_importance_explainer(["a", "b", "c"])
    explanation = explainer.explain({"a": 1, "b": 100, "c": 50}, prediction=1)
    importances = explanation.feature_importances
    assert importances[0].feature_name == "b"
    assert importances[1].feature_name == "c"
    assert importances[2].feature_name == "a"
    print("  [test_importance_sorting] 重要性排序 OK")

if __name__ == "__main__":
    test_feature_importance_dict()
    test_feature_importance_list()
    test_counterfactual()
    test_explanation_manager()
    test_batch_explain()
    test_importance_sorting()
    print("=" * 60)
    print("阶段56验证通过 ✓")
    print("=" * 60)
