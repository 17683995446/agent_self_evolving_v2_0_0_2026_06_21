"""
验证阶段56-60: 模型解释性、持续集成、模型蒸馏、自动化测试、部署编排
"""
import sys
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

exp = load_module("explainability", "/workspace/self_evolving_agent/core/explainability.py")
ci = load_module("ci_engine", "/workspace/self_evolving_agent/core/ci_engine.py")
md = load_module("model_distillation", "/workspace/self_evolving_agent/core/model_distillation.py")
at = load_module("auto_testing", "/workspace/self_evolving_agent/core/auto_testing.py")
do = load_module("deployment_orchestrator", "/workspace/self_evolving_agent/core/deployment_orchestrator.py")

print("=" * 60)
print("验证阶段56-60")
print("=" * 60)

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

# 阶段58: 模型蒸馏
def test_stage58():
    teacher = md.create_teacher_model({"f1": [1.0, 0.5], "f2": [0.3, 0.8]})
    student = md.create_student_model({"f1": [0.5], "f2": [0.5]})
    trainer = md.create_distillation_trainer(temperature=4.0, alpha=0.7, epochs=2)
    dataset = [
        {"input": {"f1": 1, "f2": 0}, "label": 0},
        {"input": {"f1": 0, "f2": 1}, "label": 1},
    ]
    result = trainer.train(teacher, student, dataset)
    assert result.compression_ratio == 2.0
    assert len(trainer.get_history()) == 2
    print("  [阶段58] 模型蒸馏 OK")

# 阶段59: 自动化测试
def test_stage59():
    suite = at.create_test_suite("s1")
    suite.add_test(at.create_test_case("t1", lambda: None))
    runner = at.create_test_runner()
    report = runner.run(suite)
    assert report.get_summary()["passed"] == 1
    print("  [阶段59] 自动化测试 OK")

# 阶段60: 部署编排
def test_stage60():
    orch = do.create_orchestrator()
    dep = do.create_deployment("d1", "svc1", "v2", do.DeploymentStrategyType.ROLLING, replicas=3)
    instances = orch.deploy(dep)
    assert len(instances) == 3
    orch.scale("svc1", 5)
    assert len(orch.get_instances("svc1")) == 5
    print("  [阶段60] 部署编排 OK")

if __name__ == "__main__":
    test_stage56()
    test_stage57()
    test_stage58()
    test_stage59()
    test_stage60()
    print("=" * 60)
    print("阶段56-60全部验证通过 ✓")
    print("=" * 60)
