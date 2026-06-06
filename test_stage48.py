"""
阶段48测试: 工作流编排接口标准化
"""
import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.workflow import (
    Workflow, WorkflowStep, WorkflowEngine, WorkflowStatus,
    StepStatus, StepResult, create_workflow, create_step
)


def test_simple_workflow():
    """测试简单工作流"""
    wf = create_workflow("simple")
    wf.add_step(create_step("step1", lambda x: x + 1))

    engine = WorkflowEngine()
    engine.register(wf)

    results = engine.execute("simple", 10)
    assert results["step1"].status == StepStatus.SUCCESS
    assert results["step1"].output == 11
    assert wf.get_status() == WorkflowStatus.COMPLETED
    print("  [test_simple_workflow] 简单工作流 ✓")


def test_dependency_chain():
    """测试依赖链"""
    wf = create_workflow("chain")
    wf.add_step(create_step("a", lambda x: 1))
    wf.add_step(create_step("b", lambda x: x + 1, dependencies=["a"]))
    wf.add_step(create_step("c", lambda x: x + 1, dependencies=["b"]))

    engine = WorkflowEngine()
    engine.register(wf)
    results = engine.execute("chain")

    assert results["a"].output == 1
    assert results["b"].output == 2
    assert results["c"].output == 3
    print("  [test_dependency_chain] 依赖链 ✓")


def test_parallel_steps():
    """测试并行步骤"""
    wf = create_workflow("parallel")
    wf.add_step(create_step("a", lambda x: 1))
    wf.add_step(create_step("b", lambda x: 2))
    wf.add_step(create_step("c", lambda x: sum(x), dependencies=["a", "b"]))

    engine = WorkflowEngine()
    engine.register(wf)
    results = engine.execute("parallel")

    assert results["c"].output == 3  # sum([1, 2])
    print("  [test_parallel_steps] 并行步骤 ✓")


def test_step_retry():
    """测试步骤重试"""
    call_count = [0]

    def fail_twice(x):
        call_count[0] += 1
        if call_count[0] < 3:
            raise RuntimeError("fail")
        return "success"

    wf = create_workflow("retry")
    wf.add_step(create_step("r", fail_twice, retries=3))

    engine = WorkflowEngine()
    engine.register(wf)
    results = engine.execute("retry")

    assert results["r"].status == StepStatus.SUCCESS
    assert results["r"].output == "success"
    assert call_count[0] == 3
    print("  [test_step_retry] 步骤重试 ✓")


def test_step_failure():
    """测试步骤失败"""
    wf = create_workflow("fail")
    wf.add_step(create_step("a", lambda x: (_ for _ in ()).throw(RuntimeError("always fail"))))
    wf.add_step(create_step("b", lambda x: x, dependencies=["a"]))

    engine = WorkflowEngine()
    engine.register(wf)
    results = engine.execute("fail")

    assert results["a"].status == StepStatus.FAILED
    assert wf.get_status() == WorkflowStatus.FAILED
    print("  [test_step_failure] 步骤失败 ✓")


def test_conditional_step():
    """测试条件步骤"""
    wf = create_workflow("conditional")
    wf.add_step(create_step("a", lambda x: 100))
    wf.add_step(create_step("b", lambda x: x + 1,
                            dependencies=["a"],
                            condition=lambda ctx: ctx.get("a", 0) > 50))
    wf.add_step(create_step("c", lambda x: x - 1,
                            dependencies=["a"],
                            condition=lambda ctx: ctx.get("a", 0) <= 50))

    engine = WorkflowEngine()
    engine.register(wf)
    results = engine.execute("conditional")

    assert results["b"].status == StepStatus.SUCCESS
    assert results["b"].output == 101
    assert results["c"].status == StepStatus.SKIPPED
    print("  [test_conditional_step] 条件步骤 ✓")


def test_workflow_stats():
    """测试工作流统计"""
    wf = create_workflow("stats")
    wf.add_step(create_step("s1", lambda x: 1))
    wf.add_step(create_step("s2", lambda x: 2))

    engine = WorkflowEngine()
    engine.register(wf)
    engine.execute("stats")

    stats = wf.get_stats()
    assert stats["total_steps"] == 2
    assert stats["completed_steps"] == 2
    assert stats["status"] == "completed"
    print("  [test_workflow_stats] 工作流统计 ✓")


def test_step_result():
    """测试步骤结果"""
    result = StepResult(
        step_id="test",
        status=StepStatus.SUCCESS,
        output="data",
        elapsed_ms=50.0,
    )

    assert result.step_id == "test"
    assert result.status == StepStatus.SUCCESS
    assert result.output == "data"
    assert result.elapsed_ms == 50.0
    print("  [test_step_result] 步骤结果 ✓")


def test_workflow_not_found():
    """测试工作流不存在"""
    engine = WorkflowEngine()
    try:
        engine.execute("nonexistent")
        assert False, "应抛出异常"
    except ValueError as e:
        assert "not found" in str(e)
    print("  [test_workflow_not_found] 工作流不存在 ✓")


def test_complex_dag():
    """测试复杂DAG"""
    #    a
    #   / \
    #  b   c
    #   \ /
    #    d
    wf = create_workflow("dag")
    wf.add_step(create_step("a", lambda x: 1))
    wf.add_step(create_step("b", lambda x: x + 10, dependencies=["a"]))
    wf.add_step(create_step("c", lambda x: x + 100, dependencies=["a"]))
    wf.add_step(create_step("d", lambda x: sum(x), dependencies=["b", "c"]))

    engine = WorkflowEngine()
    engine.register(wf)
    results = engine.execute("dag")

    assert results["b"].output == 11
    assert results["c"].output == 101
    assert results["d"].output == 112  # sum([11, 101])
    print("  [test_complex_dag] 复杂DAG ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("阶段48测试: 工作流编排接口标准化")
    print("=" * 60)

    test_simple_workflow()
    test_dependency_chain()
    test_parallel_steps()
    test_step_retry()
    test_step_failure()
    test_conditional_step()
    test_workflow_stats()
    test_step_result()
    test_workflow_not_found()
    test_complex_dag()

    print("=" * 60)
    print("全部10项测试通过 ✓")
    print("=" * 60)
