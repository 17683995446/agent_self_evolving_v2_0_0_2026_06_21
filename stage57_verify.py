"""
阶段57验证: 持续集成接口标准化
"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("ci", "/workspace/self_evolving_agent/core/ci_engine.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["ci"] = mod
spec.loader.exec_module(mod)

print("=" * 60)
print("阶段57验证: 持续集成接口标准化")
print("=" * 60)

# 测试1: 创建流水线和阶段
def test_pipeline_creation():
    pipeline = mod.create_pipeline("p1")
    stage = mod.create_stage("s1", lambda: "ok")
    pipeline.add_stage(stage)
    assert pipeline.get_stats()["total_stages"] == 1
    print("  [test_pipeline_creation] 创建流水线 OK")

# 测试2: 执行简单流水线
def test_pipeline_run():
    pipeline = mod.create_pipeline("p2")
    pipeline.add_stage(mod.create_stage("build", lambda: "built"))
    pipeline.add_stage(mod.create_stage("test", lambda: "tested", dependencies=["build"]))

    engine = mod.create_ci_engine()
    engine.register_pipeline(pipeline)
    results = engine.run_pipeline("p2")

    assert results["build"].status == mod.StageStatus.SUCCESS
    assert results["test"].status == mod.StageStatus.SUCCESS
    assert pipeline.get_status() == mod.PipelineStatus.SUCCESS
    print("  [test_pipeline_run] 执行流水线 OK")

# 测试3: 阶段失败
def test_stage_failure():
    pipeline = mod.create_pipeline("p3")
    pipeline.add_stage(mod.create_stage("build", lambda: "built"))
    pipeline.add_stage(mod.create_stage("test", lambda: 1 / 0, dependencies=["build"]))

    engine = mod.create_ci_engine()
    engine.register_pipeline(pipeline)
    results = engine.run_pipeline("p3")

    assert results["build"].status == mod.StageStatus.SUCCESS
    assert results["test"].status == mod.StageStatus.FAILED
    assert pipeline.get_status() == mod.PipelineStatus.FAILED
    print("  [test_stage_failure] 阶段失败 OK")

# 测试4: 阶段重试
def test_stage_retry():
    call_count = [0]
    def flaky():
        call_count[0] += 1
        if call_count[0] < 3:
            raise RuntimeError("fail")
        return "ok"

    pipeline = mod.create_pipeline("p4")
    pipeline.add_stage(mod.create_stage("retry_test", flaky, retries=3))

    engine = mod.create_ci_engine()
    engine.register_pipeline(pipeline)
    results = engine.run_pipeline("p4")

    assert results["retry_test"].status == mod.StageStatus.SUCCESS
    assert call_count[0] == 3
    print("  [test_stage_retry] 阶段重试 OK")

# 测试5: 构建产物管理
def test_artifact_management():
    engine = mod.create_ci_engine()
    artifact = mod.BuildArtifact(
        artifact_id="art1",
        name="model.bin",
        path="/build/model.bin",
        checksum="abc123",
    )
    engine.store_artifact(artifact)
    retrieved = engine.get_artifact("art1")
    assert retrieved is not None
    assert retrieved.name == "model.bin"
    assert len(engine.list_artifacts()) == 1
    print("  [test_artifact_management] 构建产物管理 OK")

# 测试6: 并行阶段（无依赖）
def test_parallel_stages():
    pipeline = mod.create_pipeline("p5")
    pipeline.add_stage(mod.create_stage("lint", lambda: "linted"))
    pipeline.add_stage(mod.create_stage("format", lambda: "formatted"))

    engine = mod.create_ci_engine()
    engine.register_pipeline(pipeline)
    results = engine.run_pipeline("p5")

    assert results["lint"].status == mod.StageStatus.SUCCESS
    assert results["format"].status == mod.StageStatus.SUCCESS
    print("  [test_parallel_stages] 并行阶段 OK")

if __name__ == "__main__":
    test_pipeline_creation()
    test_pipeline_run()
    test_stage_failure()
    test_stage_retry()
    test_artifact_management()
    test_parallel_stages()
    print("=" * 60)
    print("阶段57验证通过 ✓")
    print("=" * 60)
