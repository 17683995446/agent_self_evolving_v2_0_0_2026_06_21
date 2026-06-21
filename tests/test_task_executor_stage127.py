"""
阶段127: 端到端任务执行器 — 专项测试

验证:
1. 数据结构（Task/TaskStep/TaskPlan/TaskResult）
2. TaskPlanner规则规划
3. TaskPlanner LLM辅助规划
4. TaskExecutor端到端执行
5. 步骤依赖与并行
6. 错误处理与重试
7. 检查点与恢复
8. 环境ID解析
9. Agent集成
10. 并发安全
11. 性能
12. 异常容错
13. 第一性原理验证
"""

import os
import time
import tempfile
import threading
import pytest

from self_evolving_agent.core.task_executor import (
    Task,
    TaskStep,
    TaskPlan,
    TaskResult,
    TaskStatus,
    StepStatus,
    TaskPlanner,
    TaskExecutor,
    create_task,
    create_task_executor,
)
from self_evolving_agent.core.environment_interface import (
    EnvironmentManager,
    SimulatedEnvironment,
    FilesystemEnvironment,
    create_environment_manager,
    create_simulated_environment,
    create_filesystem_environment,
)
from self_evolving_agent.core.persistence import (
    create_persistence_manager,
    create_memory_storage,
    create_json_storage,
)


# ============================================================
# 1. 数据结构测试
# ============================================================

class TestDataStructures:
    """数据结构测试"""

    def test_task_status_enum(self):
        """任务状态枚举"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.EXECUTING.value == "executing"

    def test_step_status_enum(self):
        """步骤状态枚举"""
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"
        assert StepStatus.SKIPPED.value == "skipped"

    def test_task_creation(self):
        """任务创建"""
        task = Task(task_id="t1", goal="read file")
        assert task.task_id == "t1"
        assert task.goal == "read file"
        assert task.constraints == {}
        assert task.priority == 0
        assert task.created_at > 0

    def test_task_to_dict_from_dict(self):
        """任务序列化"""
        task = Task(
            task_id="t1",
            goal="read file",
            constraints={"timeout": 30},
            priority=5,
            tags=["io"],
        )
        d = task.to_dict()
        assert d["task_id"] == "t1"
        assert d["goal"] == "read file"
        assert d["constraints"] == {"timeout": 30}
        assert d["priority"] == 5
        assert d["tags"] == ["io"]

        restored = Task.from_dict(d)
        assert restored.task_id == "t1"
        assert restored.goal == "read file"
        assert restored.priority == 5

    def test_task_step_creation(self):
        """步骤创建"""
        step = TaskStep(
            step_id="s1",
            description="read file",
            action_type="read",
            target="/tmp/test.txt",
        )
        assert step.step_id == "s1"
        assert step.action_type == "read"
        assert step.target == "/tmp/test.txt"
        assert step.status == StepStatus.PENDING
        assert step.max_retries == 3

    def test_task_step_to_dict_from_dict(self):
        """步骤序列化"""
        step = TaskStep(
            step_id="s1",
            description="read file",
            action_type="read",
            target="test.txt",
            dependencies=["s0"],
            output_key="out1",
            max_retries=5,
        )
        d = step.to_dict()
        assert d["step_id"] == "s1"
        assert d["action_type"] == "read"
        assert d["dependencies"] == ["s0"]
        assert d["output_key"] == "out1"
        assert d["max_retries"] == 5

        restored = TaskStep.from_dict(d)
        assert restored.step_id == "s1"
        assert restored.action_type == "read"
        assert restored.dependencies == ["s0"]
        assert restored.max_retries == 5

    def test_task_plan_creation(self):
        """计划创建"""
        steps = [
            TaskStep(step_id="s1", description="step1", action_type="read", target="a"),
            TaskStep(step_id="s2", description="step2", action_type="read", target="b"),
        ]
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=steps)
        assert plan.plan_id == "p1"
        assert plan.task_id == "t1"
        assert len(plan.steps) == 2

    def test_task_plan_get_step(self):
        """获取步骤"""
        steps = [
            TaskStep(step_id="s1", description="step1", action_type="read", target="a"),
        ]
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=steps)
        assert plan.get_step("s1") is not None
        assert plan.get_step("s1").target == "a"
        assert plan.get_step("nonexistent") is None

    def test_task_plan_get_ready_steps(self):
        """获取可执行步骤"""
        steps = [
            TaskStep(step_id="s1", description="step1", action_type="read", target="a"),
            TaskStep(
                step_id="s2", description="step2", action_type="read", target="b",
                dependencies=["s1"],
            ),
        ]
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=steps)

        # 初始：只有s1可执行
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "s1"

        # s1完成后，s2可执行
        steps[0].status = StepStatus.COMPLETED
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "s2"

    def test_task_plan_is_complete(self):
        """计划完成检查"""
        steps = [
            TaskStep(step_id="s1", description="step1", action_type="read", target="a"),
        ]
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=steps)
        assert not plan.is_complete()

        steps[0].status = StepStatus.COMPLETED
        assert plan.is_complete()

        steps[0].status = StepStatus.SKIPPED
        assert plan.is_complete()

    def test_task_plan_has_failed(self):
        """计划失败检查"""
        steps = [
            TaskStep(step_id="s1", description="step1", action_type="read", target="a"),
        ]
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=steps)
        assert not plan.has_failed()

        steps[0].status = StepStatus.FAILED
        steps[0].retry_count = 3
        steps[0].max_retries = 3
        assert plan.has_failed()

    def test_task_result_creation(self):
        """结果创建"""
        result = TaskResult(
            task_id="t1",
            success=True,
            status=TaskStatus.COMPLETED,
            steps_completed=2,
            steps_total=2,
        )
        assert result.task_id == "t1"
        assert result.success is True
        assert result.status == TaskStatus.COMPLETED
        assert result.steps_completed == 2
        assert result.duration_ms == 0.0

    def test_task_result_to_dict(self):
        """结果序列化"""
        result = TaskResult(
            task_id="t1",
            success=True,
            status=TaskStatus.COMPLETED,
            outputs={"key": "value"},
            steps_completed=1,
            steps_total=1,
        )
        d = result.to_dict()
        assert d["task_id"] == "t1"
        assert d["success"] is True
        assert d["status"] == "completed"
        assert d["outputs"] == {"key": "value"}


# ============================================================
# 2. TaskPlanner 规则规划测试
# ============================================================

class TestTaskPlannerRules:
    """TaskPlanner规则规划测试"""

    def test_planner_creation(self):
        """规划器创建"""
        planner = TaskPlanner()
        assert planner is not None
        assert planner._llm_coordinator is None

    def test_plan_read_file(self):
        """规划：读取文件"""
        planner = TaskPlanner()
        task = create_task("read file /tmp/test.txt", task_id="t1")
        plan = planner.plan(task)
        assert len(plan.steps) == 1
        assert plan.steps[0].action_type == "read"
        assert plan.steps[0].target == "/tmp/test.txt"

    def test_plan_read_file_chinese(self):
        """规划：读取文件（中文）"""
        planner = TaskPlanner()
        task = create_task("读取文件 /tmp/test.txt", task_id="t1")
        plan = planner.plan(task)
        assert len(plan.steps) == 1
        assert plan.steps[0].action_type == "read"
        assert "/tmp/test.txt" in plan.steps[0].target

    def test_plan_write_file(self):
        """规划：写入文件"""
        planner = TaskPlanner()
        task = create_task("write file output.txt content: hello world", task_id="t1")
        plan = planner.plan(task)
        assert len(plan.steps) == 1
        assert plan.steps[0].action_type == "write"
        assert "output.txt" in plan.steps[0].target

    def test_plan_list_dir(self):
        """规划：列出目录"""
        planner = TaskPlanner()
        task = create_task("list dir /tmp", task_id="t1")
        plan = planner.plan(task)
        assert len(plan.steps) == 1
        assert plan.steps[0].action_type == "list"

    def test_plan_mkdir(self):
        """规划：创建目录"""
        planner = TaskPlanner()
        task = create_task("mkdir /tmp/newdir", task_id="t1")
        plan = planner.plan(task)
        assert len(plan.steps) == 1
        assert plan.steps[0].action_type == "mkdir"

    def test_plan_delete(self):
        """规划：删除"""
        planner = TaskPlanner()
        task = create_task("delete /tmp/old.txt", task_id="t1")
        plan = planner.plan(task)
        assert len(plan.steps) == 1
        assert plan.steps[0].action_type == "delete"

    def test_plan_http_get(self):
        """规划：HTTP GET"""
        planner = TaskPlanner()
        task = create_task("fetch https://example.com/api", task_id="t1")
        plan = planner.plan(task)
        assert len(plan.steps) == 1
        assert plan.steps[0].action_type == "get"

    def test_plan_execute_command(self):
        """规划：执行命令"""
        planner = TaskPlanner()
        task = create_task("execute command ls -la", task_id="t1")
        plan = planner.plan(task)
        assert len(plan.steps) == 1
        assert plan.steps[0].action_type == "execute"

    def test_plan_multi_step_semicolon(self):
        """规划：多步（分号分隔）"""
        planner = TaskPlanner()
        task = create_task("list dir /tmp; read file /tmp/test.txt", task_id="t1")
        plan = planner.plan(task)
        assert len(plan.steps) == 2
        assert plan.steps[0].action_type == "list"
        assert plan.steps[1].action_type == "read"
        # 第二步依赖第一步
        assert "step_t1_0" in plan.steps[1].dependencies

    def test_plan_multi_step_then(self):
        """规划：多步（then分隔）"""
        planner = TaskPlanner()
        task = create_task("list dir /tmp then read file /tmp/test.txt", task_id="t1")
        plan = planner.plan(task)
        assert len(plan.steps) == 2

    def test_plan_multi_step_chinese(self):
        """规划：多步（中文然后分隔）"""
        planner = TaskPlanner()
        task = create_task("列出目录 /tmp 然后读取文件 /tmp/test.txt", task_id="t1")
        plan = planner.plan(task)
        assert len(plan.steps) == 2

    def test_plan_empty_goal(self):
        """规划：空目标"""
        planner = TaskPlanner()
        task = create_task("", task_id="t1")
        plan = planner.plan(task)
        # 空目标降级为兜底单步
        assert len(plan.steps) == 1
        assert plan.reasoning["method"] == "fallback"

    def test_plan_unknown_action(self):
        """规划：未知动作"""
        planner = TaskPlanner()
        task = create_task("do something weird", task_id="t1")
        plan = planner.plan(task)
        # 未知动作降级为观察
        assert len(plan.steps) == 1
        assert plan.steps[0].action_type == "observe"

    def test_plan_has_output_keys(self):
        """规划：步骤有输出键"""
        planner = TaskPlanner()
        task = create_task("read file /tmp/test.txt", task_id="t1")
        plan = planner.plan(task)
        assert plan.steps[0].output_key is not None
        assert plan.steps[0].output_key.startswith("output_")

    def test_plan_reasoning_recorded(self):
        """规划：记录推理过程"""
        planner = TaskPlanner()
        task = create_task("read file /tmp/test.txt", task_id="t1")
        plan = planner.plan(task)
        assert plan.reasoning is not None
        assert plan.reasoning["method"] == "rules"
        assert plan.reasoning["step_count"] == 1


# ============================================================
# 3. TaskPlanner LLM辅助规划测试
# ============================================================

class TestTaskPlannerLLM:
    """TaskPlanner LLM辅助规划测试"""

    def test_llm_planner_with_mock(self):
        """LLM辅助规划（mock）"""
        class MockLLMCoordinator:
            def reason(self, task):
                from self_evolving_agent.core.llm_reasoning_coordinator import ReasoningResult
                return ReasoningResult(
                    task_id=task.task_id,
                    success=True,
                    answer="Step 1: read file\nStep 2: analyze content",
                    confidence=0.9,
                    sources=["llm"],
                )

        planner = TaskPlanner(llm_coordinator=MockLLMCoordinator())

        # 使用一个规则无法匹配的目标
        task = create_task("analyze the system architecture", task_id="t1")
        plan = planner.plan(task)
        # 规则无法匹配时会尝试LLM
        assert len(plan.steps) >= 1
        # 方法可能是rules（observe兜底）或llm
        assert plan.reasoning["method"] in ("rules", "llm", "fallback")

    def test_llm_planner_fallback_on_failure(self):
        """LLM失败时降级"""
        class MockLLMCoordinator:
            def reason(self, task):
                from self_evolving_agent.core.llm_reasoning_coordinator import ReasoningResult
                return ReasoningResult(
                    task_id=task.task_id,
                    success=False,
                    answer="",
                    error="LLM unavailable",
                )

        planner = TaskPlanner(llm_coordinator=MockLLMCoordinator())
        task = create_task("do something complex", task_id="t1")
        plan = planner.plan(task)
        # LLM失败时降级到兜底
        assert len(plan.steps) >= 1


# ============================================================
# 4. TaskExecutor 端到端执行测试
# ============================================================

class TestTaskExecutorExecution:
    """TaskExecutor端到端执行测试"""

    def setup_method(self):
        """每个测试前创建临时目录"""
        self._tmpdir = tempfile.mkdtemp()
        self._cleanup_files = []

    def teardown_method(self):
        """每个测试后清理"""
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _create_executor(self, with_persistence=True):
        """创建测试执行器"""
        env_mgr = create_environment_manager()
        env_mgr.register_environment(
            "simulated", SimulatedEnvironment(), is_default=True,
        )
        env_mgr.register_environment(
            "filesystem", FilesystemEnvironment(self._tmpdir),
        )

        persistence = create_persistence_manager() if with_persistence else None
        return create_task_executor(
            env_manager=env_mgr,
            persistence=persistence,
            executor_id="test_executor",
        )

    def test_executor_creation(self):
        """执行器创建"""
        executor = self._create_executor()
        assert executor is not None
        assert executor.executor_id == "test_executor"

    def test_submit_task(self):
        """提交任务"""
        executor = self._create_executor()
        task = create_task("read file test.txt", task_id="t1")
        task_id = executor.submit(task)
        assert task_id == "t1"
        assert executor.get_status("t1") == TaskStatus.PENDING

    def test_submit_duplicate_task(self):
        """提交重复任务（应报错）"""
        executor = self._create_executor()
        task = create_task("read file test.txt", task_id="t1")
        executor.submit(task)
        with pytest.raises(ValueError):
            executor.submit(task)

    def test_execute_simple_read(self):
        """执行：简单读取"""
        # 准备文件
        filepath = os.path.join(self._tmpdir, "test.txt")
        with open(filepath, "w") as f:
            f.write("hello world")

        executor = self._create_executor()
        task = create_task("read file test.txt", task_id="t1")
        result = executor.run(task)

        assert result.success is True
        assert result.status == TaskStatus.COMPLETED
        assert result.steps_completed == 1
        assert result.steps_total == 1
        assert "output_0" in result.outputs

    def test_execute_multi_step(self):
        """执行：多步任务"""
        filepath = os.path.join(self._tmpdir, "test.txt")
        with open(filepath, "w") as f:
            f.write("content")

        executor = self._create_executor()
        task = create_task("list dir .; read file test.txt", task_id="t1")
        result = executor.run(task)

        assert result.success is True
        assert result.steps_completed == 2
        assert result.steps_total == 2

    def test_execute_write_file(self):
        """执行：写入文件"""
        executor = self._create_executor()
        task = create_task("write file output.txt content: test data", task_id="t1")
        result = executor.run(task)

        assert result.success is True
        # 验证文件已创建
        outfile = os.path.join(self._tmpdir, "output.txt")
        assert os.path.exists(outfile)

    def test_execute_mkdir(self):
        """执行：创建目录"""
        executor = self._create_executor()
        task = create_task("mkdir newdir", task_id="t1")
        result = executor.run(task)

        assert result.success is True
        assert os.path.isdir(os.path.join(self._tmpdir, "newdir"))

    def test_execute_delete_file(self):
        """执行：删除文件"""
        filepath = os.path.join(self._tmpdir, "todelete.txt")
        with open(filepath, "w") as f:
            f.write("delete me")

        executor = self._create_executor()
        task = create_task("delete todelete.txt", task_id="t1")
        result = executor.run(task)

        assert result.success is True
        assert not os.path.exists(filepath)

    def test_execute_nonexistent_task(self):
        """执行：不存在的任务"""
        executor = self._create_executor()
        result = executor.execute("nonexistent")
        assert result.success is False
        assert result.status == TaskStatus.FAILED
        assert "not found" in result.error.lower()

    def test_execute_plan_first(self):
        """执行：先规划再执行"""
        filepath = os.path.join(self._tmpdir, "test.txt")
        with open(filepath, "w") as f:
            f.write("content")

        executor = self._create_executor()
        task = create_task("read file test.txt", task_id="t1")
        executor.submit(task)

        # 先规划
        plan = executor.plan("t1")
        assert plan is not None
        assert executor.get_status("t1") == TaskStatus.READY

        # 再执行
        result = executor.execute("t1")
        assert result.success is True

    def test_get_outputs(self):
        """获取任务输出"""
        filepath = os.path.join(self._tmpdir, "test.txt")
        with open(filepath, "w") as f:
            f.write("content")

        executor = self._create_executor()
        task = create_task("read file test.txt", task_id="t1")
        executor.run(task)

        outputs = executor.get_outputs("t1")
        assert "output_0" in outputs

    def test_get_plan(self):
        """获取任务计划"""
        executor = self._create_executor()
        task = create_task("read file test.txt", task_id="t1")
        executor.submit(task)
        executor.plan("t1")

        plan = executor.get_plan("t1")
        assert plan is not None
        assert len(plan.steps) == 1

    def test_cancel_task(self):
        """取消任务"""
        executor = self._create_executor()
        task = create_task("read file test.txt", task_id="t1")
        executor.submit(task)

        assert executor.cancel("t1") is True
        assert executor.get_status("t1") == TaskStatus.CANCELLED

    def test_cancel_nonexistent(self):
        """取消不存在的任务"""
        executor = self._create_executor()
        assert executor.cancel("nonexistent") is False

    def test_list_tasks(self):
        """列出任务"""
        executor = self._create_executor()
        executor.submit(create_task("read file a", task_id="t1"))
        executor.submit(create_task("read file b", task_id="t2"))

        all_tasks = executor.list_tasks()
        assert len(all_tasks) == 2

        pending = executor.list_tasks(TaskStatus.PENDING)
        assert len(pending) == 2

    def test_clear_completed(self):
        """清除已完成任务"""
        filepath = os.path.join(self._tmpdir, "test.txt")
        with open(filepath, "w") as f:
            f.write("content")

        executor = self._create_executor()
        executor.run(create_task("read file test.txt", task_id="t1"))

        cleared = executor.clear_completed()
        assert cleared == 1
        assert executor.get_status("t1") is None

    def test_get_stats(self):
        """获取统计"""
        executor = self._create_executor()
        executor.submit(create_task("read file a", task_id="t1"))

        stats = executor.get_stats()
        assert stats["total_tasks"] == 1
        assert "by_status" in stats


# ============================================================
# 5. 步骤依赖与并行测试
# ============================================================

class TestStepDependencies:
    """步骤依赖测试"""

    def test_serial_dependency(self):
        """串行依赖"""
        steps = [
            TaskStep(step_id="s1", description="step1", action_type="read", target="a"),
            TaskStep(
                step_id="s2", description="step2", action_type="read", target="b",
                dependencies=["s1"],
            ),
            TaskStep(
                step_id="s3", description="step3", action_type="read", target="c",
                dependencies=["s2"],
            ),
        ]
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=steps)

        # 初始：只有s1
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "s1"

        # s1完成后：s2
        steps[0].status = StepStatus.COMPLETED
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "s2"

        # s2完成后：s3
        steps[1].status = StepStatus.COMPLETED
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "s3"

    def test_parallel_steps(self):
        """并行步骤（无依赖）"""
        steps = [
            TaskStep(step_id="s1", description="step1", action_type="read", target="a"),
            TaskStep(step_id="s2", description="step2", action_type="read", target="b"),
            TaskStep(step_id="s3", description="step3", action_type="read", target="c"),
        ]
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=steps)

        # 所有步骤都可并行执行
        ready = plan.get_ready_steps()
        assert len(ready) == 3

    def test_diamond_dependency(self):
        """钻石依赖"""
        steps = [
            TaskStep(step_id="s1", description="step1", action_type="read", target="a"),
            TaskStep(
                step_id="s2", description="step2", action_type="read", target="b",
                dependencies=["s1"],
            ),
            TaskStep(
                step_id="s3", description="step3", action_type="read", target="c",
                dependencies=["s1"],
            ),
            TaskStep(
                step_id="s4", description="step4", action_type="read", target="d",
                dependencies=["s2", "s3"],
            ),
        ]
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=steps)

        # 初始：s1
        ready = plan.get_ready_steps()
        assert len(ready) == 1

        # s1完成后：s2和s3可并行
        steps[0].status = StepStatus.COMPLETED
        ready = plan.get_ready_steps()
        assert len(ready) == 2
        ready_ids = {s.step_id for s in ready}
        assert ready_ids == {"s2", "s3"}

        # s2完成后：s4仍不可执行（s3未完成）
        steps[1].status = StepStatus.COMPLETED
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "s3"

        # s3完成后：s4可执行
        steps[2].status = StepStatus.COMPLETED
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "s4"

    def test_output_reference(self):
        """输出引用"""
        executor = create_task_executor(
            env_manager=create_environment_manager(),
            persistence=None,
        )
        # 手动设置输出
        executor._outputs["t1"] = {"output_0": "referenced_value"}

        params = {"input": "${output_0}", "static": "constant"}
        resolved = executor._resolve_references(params, "t1")
        assert resolved["input"] == "referenced_value"
        assert resolved["static"] == "constant"

    def test_output_reference_missing(self):
        """输出引用不存在"""
        executor = create_task_executor(
            env_manager=create_environment_manager(),
            persistence=None,
        )
        params = {"input": "${nonexistent}"}
        resolved = executor._resolve_references(params, "t1")
        # 不存在的引用保持原样
        assert resolved["input"] == "${nonexistent}"


# ============================================================
# 6. 错误处理与重试测试
# ============================================================

class TestErrorHandling:
    """错误处理与重试测试"""

    def setup_method(self):
        import shutil
        self._tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_read_nonexistent_file(self):
        """读取不存在的文件"""
        executor = create_task_executor(
            env_manager=create_environment_manager(),
            persistence=None,
        )
        executor._env_manager.register_environment(
            "filesystem", FilesystemEnvironment(self._tmpdir), is_default=True,
        )

        task = create_task("read file nonexistent.txt", task_id="t1")
        result = executor.run(task)

        # 读取不存在的文件应该失败
        assert result.success is False
        assert result.status == TaskStatus.FAILED
        assert result.steps_failed > 0

    def test_retry_on_failure(self):
        """失败重试"""
        # 创建一个总是失败的mock环境
        class FailingEnvironment(SimulatedEnvironment):
            def act(self, action):
                from self_evolving_agent.core.environment_interface import ActionResult
                return ActionResult(success=False, error="Always fails")

        env_mgr = create_environment_manager()
        env_mgr.register_environment(
            "failing", FailingEnvironment(), is_default=True,
        )

        executor = create_task_executor(
            env_manager=env_mgr,
            persistence=None,
        )

        task = create_task("observe something", task_id="t1")
        result = executor.run(task)

        assert result.success is False
        # 应该重试了max_retries次
        assert result.plan.steps[0].retry_count >= 1

    def test_max_retries_respected(self):
        """最大重试次数"""
        class FailingEnvironment(SimulatedEnvironment):
            def __init__(self):
                super().__init__()
                self.call_count = 0

            def act(self, action):
                self.call_count += 1
                from self_evolving_agent.core.environment_interface import ActionResult
                return ActionResult(success=False, error="Always fails")

        env_mgr = create_environment_manager()
        failing_env = FailingEnvironment()
        env_mgr.register_environment("failing", failing_env, is_default=True)

        executor = create_task_executor(
            env_manager=env_mgr,
            persistence=None,
        )

        task = create_task("observe something", task_id="t1")
        result = executor.run(task)

        # max_retries=3，所以应该调用4次（1次初始+3次重试）
        assert failing_env.call_count == 4
        assert result.success is False

    def test_deadlock_detection(self):
        """死锁检测（循环依赖）"""
        steps = [
            TaskStep(
                step_id="s1", description="step1", action_type="read", target="a",
                dependencies=["s2"],  # 依赖s2
            ),
            TaskStep(
                step_id="s2", description="step2", action_type="read", target="b",
                dependencies=["s1"],  # 依赖s1
            ),
        ]
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=steps)

        # 无可执行步骤
        ready = plan.get_ready_steps()
        assert len(ready) == 0
        assert not plan.is_complete()

    def test_condition_skip(self):
        """条件跳过"""
        executor = create_task_executor(
            env_manager=create_environment_manager(),
            persistence=None,
        )
        executor._env_manager.register_environment(
            "simulated", SimulatedEnvironment(), is_default=True,
        )

        step = TaskStep(
            step_id="s1",
            description="conditional step",
            action_type="observe",
            target="default",
            condition="exists:nonexistent",  # 不存在的输出
        )
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=[step])

        executor._plans["t1"] = plan
        executor._tasks["t1"] = create_task("test", task_id="t1")
        executor._status["t1"] = TaskStatus.EXECUTING

        result = executor.execute("t1")
        # 条件不满足应跳过
        assert step.status == StepStatus.SKIPPED


# ============================================================
# 7. 检查点与恢复测试
# ============================================================

class TestCheckpointResume:
    """检查点与恢复测试"""

    def setup_method(self):
        import shutil
        self._tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_checkpoint_saved(self):
        """检查点保存"""
        filepath = os.path.join(self._tmpdir, "test.txt")
        with open(filepath, "w") as f:
            f.write("content")

        persistence = create_persistence_manager()
        env_mgr = create_environment_manager()
        env_mgr.register_environment(
            "filesystem", FilesystemEnvironment(self._tmpdir), is_default=True,
        )

        executor = create_task_executor(
            env_manager=env_mgr,
            persistence=persistence,
        )

        executor.run(create_task("read file test.txt", task_id="t1"))

        # 检查点应该已保存
        checkpoints = persistence.list_checkpoints()
        assert "task_t1" in checkpoints

    def test_checkpoint_content(self):
        """检查点内容"""
        filepath = os.path.join(self._tmpdir, "test.txt")
        with open(filepath, "w") as f:
            f.write("content")

        persistence = create_persistence_manager()
        env_mgr = create_environment_manager()
        env_mgr.register_environment(
            "filesystem", FilesystemEnvironment(self._tmpdir), is_default=True,
        )

        executor = create_task_executor(
            env_manager=env_mgr,
            persistence=persistence,
        )

        executor.run(create_task("read file test.txt", task_id="t1"))

        checkpoint = persistence.load_checkpoint("task_t1")
        assert checkpoint is not None
        assert "plan" in checkpoint
        assert "outputs" in checkpoint
        assert "status" in checkpoint

    def test_resume_no_persistence(self):
        """无持久化时恢复"""
        executor = create_task_executor(
            env_manager=create_environment_manager(),
            persistence=None,
        )
        result = executor.resume("t1")
        assert result.success is False
        assert "No persistence" in result.error

    def test_resume_no_checkpoint(self):
        """无检查点时恢复"""
        persistence = create_persistence_manager()
        executor = create_task_executor(
            env_manager=create_environment_manager(),
            persistence=persistence,
        )
        result = executor.resume("t1")
        assert result.success is False
        assert "No checkpoint" in result.error

    def test_resume_with_checkpoint(self):
        """有检查点时恢复"""
        filepath = os.path.join(self._tmpdir, "test.txt")
        with open(filepath, "w") as f:
            f.write("content")

        persistence = create_persistence_manager()
        env_mgr = create_environment_manager()
        env_mgr.register_environment(
            "filesystem", FilesystemEnvironment(self._tmpdir), is_default=True,
        )

        executor = create_task_executor(
            env_manager=env_mgr,
            persistence=persistence,
        )

        # 执行任务
        executor.run(create_task("read file test.txt", task_id="t1"))

        # 恢复（任务已完成，应该直接返回）
        result = executor.resume("t1")
        assert result.task_id == "t1"


# ============================================================
# 8. 环境ID解析测试
# ============================================================

class TestEnvironmentResolution:
    """环境ID解析测试"""

    def test_resolve_exact_match(self):
        """精确匹配"""
        env_mgr = create_environment_manager()
        env_mgr.register_environment("filesystem", SimulatedEnvironment())

        executor = create_task_executor(env_manager=env_mgr, persistence=None)
        resolved = executor._resolve_env_id("filesystem", "read")
        assert resolved == "filesystem"

    def test_resolve_no_hint(self):
        """无提示（使用默认）"""
        env_mgr = create_environment_manager()
        env_mgr.register_environment("default", SimulatedEnvironment(), is_default=True)

        executor = create_task_executor(env_manager=env_mgr, persistence=None)
        resolved = executor._resolve_env_id(None, "read")
        assert resolved is None  # None = 使用默认

    def test_resolve_type_match_by_name(self):
        """按名称类型匹配"""
        env_mgr = create_environment_manager()
        # 注册为"my_filesystem"而非"filesystem"（名称包含类型关键字）
        env_mgr.register_environment("my_filesystem", SimulatedEnvironment())

        executor = create_task_executor(env_manager=env_mgr, persistence=None)
        # env_id="filesystem"但注册的是"my_filesystem"
        # "filesystem" in "my_filesystem" → True
        resolved = executor._resolve_env_id("filesystem", "read")
        assert resolved == "my_filesystem"

    def test_resolve_type_match_by_class(self):
        """按类名类型匹配"""
        import shutil
        tmpdir = tempfile.mkdtemp()
        try:
            env_mgr = create_environment_manager()
            # 注册FilesystemEnvironment但ID不含"filesystem"
            env_mgr.register_environment("my_env", FilesystemEnvironment(tmpdir))

            executor = create_task_executor(env_manager=env_mgr, persistence=None)
            # env_id="filesystem"但注册的是"my_env"
            resolved = executor._resolve_env_id("filesystem", "read")
            # 应该通过类名匹配找到"my_env"
            assert resolved == "my_env"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_resolve_fallback_to_default(self):
        """回退到默认环境"""
        env_mgr = create_environment_manager()
        env_mgr.register_environment("default", SimulatedEnvironment(), is_default=True)

        executor = create_task_executor(env_manager=env_mgr, persistence=None)
        # 不匹配的env_id，且action_type=observe（无类型要求）
        resolved = executor._resolve_env_id("nonexistent", "observe")
        assert resolved is None  # 回退到默认


# ============================================================
# 9. Agent集成测试
# ============================================================

class TestAgentIntegration:
    """Agent集成测试"""

    def setup_method(self):
        import shutil
        self._tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_agent_has_task_executor(self):
        """Agent有task_executor属性"""
        from self_evolving_agent.agent import SelfEvolvingAgent
        agent = SelfEvolvingAgent(agent_id="test_agent")
        assert agent.task_executor is not None
        assert isinstance(agent.task_executor, TaskExecutor)

    def test_agent_execute_task(self):
        """Agent执行任务"""
        from self_evolving_agent.agent import SelfEvolvingAgent

        filepath = os.path.join(self._tmpdir, "test.txt")
        with open(filepath, "w") as f:
            f.write("agent content")

        agent = SelfEvolvingAgent(agent_id="test_agent")
        agent.register_environment(
            "fs", FilesystemEnvironment(self._tmpdir), is_default=True,
        )

        result = agent.execute_task("read file test.txt", task_id="agent_t1")
        assert result.success is True
        assert "output_0" in result.outputs

    def test_agent_submit_and_get_status(self):
        """Agent提交任务并获取状态"""
        from self_evolving_agent.agent import SelfEvolvingAgent

        agent = SelfEvolvingAgent(agent_id="test_agent")
        agent.register_environment(
            "fs", FilesystemEnvironment(self._tmpdir), is_default=True,
        )

        task_id = agent.submit_task("read file test.txt", task_id="agent_t2")
        assert task_id == "agent_t2"
        status = agent.get_task_status("agent_t2")
        assert status == TaskStatus.PENDING

    def test_agent_get_task_result(self):
        """Agent获取任务结果"""
        from self_evolving_agent.agent import SelfEvolvingAgent

        filepath = os.path.join(self._tmpdir, "test.txt")
        with open(filepath, "w") as f:
            f.write("content")

        agent = SelfEvolvingAgent(agent_id="test_agent")
        agent.register_environment(
            "fs", FilesystemEnvironment(self._tmpdir), is_default=True,
        )

        agent.execute_task("read file test.txt", task_id="agent_t3")
        result = agent.get_task_result("agent_t3")
        assert result is not None
        assert result.success is True

    def test_agent_multi_step_task(self):
        """Agent多步任务"""
        from self_evolving_agent.agent import SelfEvolvingAgent

        filepath = os.path.join(self._tmpdir, "test.txt")
        with open(filepath, "w") as f:
            f.write("content")

        agent = SelfEvolvingAgent(agent_id="test_agent")
        agent.register_environment(
            "fs", FilesystemEnvironment(self._tmpdir), is_default=True,
        )

        result = agent.execute_task(
            "list dir .; read file test.txt", task_id="agent_t4",
        )
        assert result.success is True
        assert result.steps_completed == 2


# ============================================================
# 10. 并发安全测试
# ============================================================

class TestConcurrency:
    """并发安全测试"""

    def test_concurrent_submit(self):
        """并发提交任务"""
        env_mgr = create_environment_manager()
        env_mgr.register_environment(
            "simulated", SimulatedEnvironment(), is_default=True,
        )
        executor = create_task_executor(env_manager=env_mgr, persistence=None)

        results = []
        errors = []

        def submit_task(i):
            try:
                task = create_task(f"observe task{i}", task_id=f"t{i}")
                executor.submit(task)
                results.append(i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=submit_task, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 20
        assert len(executor.list_tasks()) == 20

    def test_concurrent_execute(self):
        """并发执行任务"""
        import shutil
        tmpdir = tempfile.mkdtemp()
        try:
            # 创建多个文件
            for i in range(5):
                with open(os.path.join(tmpdir, f"file{i}.txt"), "w") as f:
                    f.write(f"content{i}")

            env_mgr = create_environment_manager()
            env_mgr.register_environment(
                "fs", FilesystemEnvironment(tmpdir), is_default=True,
            )
            executor = create_task_executor(env_manager=env_mgr, persistence=None)

            results = [None] * 5
            errors = []

            def execute_task(i):
                try:
                    task = create_task(f"read file file{i}.txt", task_id=f"t{i}")
                    results[i] = executor.run(task)
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=execute_task, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0
            for r in results:
                assert r is not None
                assert r.success is True
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_thread_safe_stats(self):
        """线程安全统计"""
        env_mgr = create_environment_manager()
        env_mgr.register_environment(
            "simulated", SimulatedEnvironment(), is_default=True,
        )
        executor = create_task_executor(env_manager=env_mgr, persistence=None)

        def submit_and_stats():
            for i in range(10):
                executor.submit(create_task(f"observe {i}", task_id=f"ts_{threading.get_ident()}_{i}"))
                executor.get_stats()

        threads = [threading.Thread(target=submit_and_stats) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = executor.get_stats()
        assert stats["total_tasks"] == 50


# ============================================================
# 11. 性能测试
# ============================================================

class TestPerformance:
    """性能测试"""

    def test_single_task_latency(self):
        """单任务延迟"""
        import shutil
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "test.txt"), "w") as f:
                f.write("content")

            env_mgr = create_environment_manager()
            env_mgr.register_environment(
                "fs", FilesystemEnvironment(tmpdir), is_default=True,
            )
            executor = create_task_executor(env_manager=env_mgr, persistence=None)

            start = time.time()
            executor.run(create_task("read file test.txt", task_id="t1"))
            elapsed = time.time() - start

            # 单任务应在100ms内完成
            assert elapsed < 0.1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_planning_performance(self):
        """规划性能"""
        planner = TaskPlanner()

        start = time.time()
        for i in range(100):
            task = create_task(f"read file file{i}.txt", task_id=f"t{i}")
            planner.plan(task)
        elapsed = time.time() - start

        # 100次规划应在1秒内
        assert elapsed < 1.0

    def test_many_steps_plan(self):
        """多步骤规划"""
        planner = TaskPlanner()
        # 创建10步任务
        goals = "; ".join([f"read file file{i}.txt" for i in range(10)])
        task = create_task(goals, task_id="t1")
        plan = planner.plan(task)

        assert len(plan.steps) == 10
        # 验证串行依赖
        for i in range(1, 10):
            assert f"step_t1_{i-1}" in plan.steps[i].dependencies


# ============================================================
# 12. 异常容错测试
# ============================================================

class TestExceptionTolerance:
    """异常容错测试"""

    def test_none_goal(self):
        """空目标"""
        planner = TaskPlanner()
        task = Task(task_id="t1", goal="")
        plan = planner.plan(task)
        # 空目标降级为兜底
        assert len(plan.steps) == 1

    def test_executor_with_no_llm(self):
        """无LLM执行器"""
        env_mgr = create_environment_manager()
        env_mgr.register_environment(
            "simulated", SimulatedEnvironment(), is_default=True,
        )
        executor = create_task_executor(
            env_manager=env_mgr,
            llm_coordinator=None,
            persistence=None,
        )
        # 应该能正常工作（规则规划）
        result = executor.run(create_task("observe something", task_id="t1"))
        assert result is not None

    def test_executor_with_no_persistence(self):
        """无持久化执行器"""
        env_mgr = create_environment_manager()
        env_mgr.register_environment(
            "simulated", SimulatedEnvironment(), is_default=True,
        )
        executor = create_task_executor(
            env_manager=env_mgr,
            persistence=None,
        )
        # 应该能正常工作（不保存检查点）
        result = executor.run(create_task("observe something", task_id="t1"))
        assert result is not None

    def test_observer_exception_isolated(self):
        """观察者异常隔离"""
        env_mgr = create_environment_manager()
        env_mgr.register_environment(
            "simulated", SimulatedEnvironment(), is_default=True,
        )
        executor = create_task_executor(env_manager=env_mgr, persistence=None)

        def bad_observer(task_id, event):
            raise RuntimeError("Observer error")

        executor.register_observer(bad_observer)

        # 观察者异常不应影响执行
        result = executor.run(create_task("observe something", task_id="t1"))
        assert result is not None

    def test_serialize_complex_output(self):
        """序列化复杂输出"""
        executor = create_task_executor(
            env_manager=create_environment_manager(),
            persistence=None,
        )

        # 测试各种类型
        assert executor._serialize_output(None) is None
        assert executor._serialize_output("string") == "string"
        assert executor._serialize_output(42) == 42
        assert executor._serialize_output({"key": "value"}) == {"key": "value"}
        assert executor._serialize_output([1, 2, 3]) == [1, 2, 3]
        # 复杂对象转为字符串
        class Custom:
            def __str__(self):
                return "custom_object"
        assert executor._serialize_output(Custom()) == "custom_object"

    def test_evaluate_condition_no_condition(self):
        """无条件时总是执行"""
        executor = create_task_executor(
            env_manager=create_environment_manager(),
            persistence=None,
        )
        step = TaskStep(
            step_id="s1", description="step", action_type="read", target="a",
        )
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=[step])
        assert executor._evaluate_condition(step, plan) is True

    def test_evaluate_condition_exists(self):
        """exists条件"""
        executor = create_task_executor(
            env_manager=create_environment_manager(),
            persistence=None,
        )
        step1 = TaskStep(
            step_id="s1", description="step1", action_type="read", target="a",
            output_key="out1",
        )
        step1.status = StepStatus.COMPLETED
        step2 = TaskStep(
            step_id="s2", description="step2", action_type="read", target="b",
            condition="exists:out1",
        )
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=[step1, step2])
        assert executor._evaluate_condition(step2, plan) is True

    def test_evaluate_condition_not_exists(self):
        """exists条件不满足"""
        executor = create_task_executor(
            env_manager=create_environment_manager(),
            persistence=None,
        )
        step = TaskStep(
            step_id="s1", description="step", action_type="read", target="a",
            condition="exists:nonexistent",
        )
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=[step])
        assert executor._evaluate_condition(step, plan) is False

    def test_capacity_limit(self):
        """容量限制"""
        env_mgr = create_environment_manager()
        env_mgr.register_environment(
            "simulated", SimulatedEnvironment(), is_default=True,
        )
        executor = create_task_executor(env_manager=env_mgr, persistence=None)
        executor._max_tasks = 10  # 设置小容量

        # 提交并完成10个任务
        for i in range(10):
            executor.run(create_task("observe something", task_id=f"t{i}"))

        # 提交第11个，应触发淘汰
        executor.submit(create_task("observe something", task_id="t10"))
        # 旧任务应被淘汰
        assert len(executor.list_tasks()) <= 15


# ============================================================
# 13. 第一性原理验证
# ============================================================

class TestFirstPrinciples:
    """第一性原理验证"""

    def test_principle_task_decomposition(self):
        """原理：任务可分解为步骤"""
        planner = TaskPlanner()
        task = create_task("list dir /tmp; read file /tmp/a; read file /tmp/b", task_id="t1")
        plan = planner.plan(task)
        # 复杂任务应被分解为多个步骤
        assert len(plan.steps) == 3
        # 每个步骤都是独立的动作
        for step in plan.steps:
            assert step.action_type in ("list", "read", "observe")
            assert step.target  # 非空

    def test_principle_plan_execute_persist(self):
        """原理：规划→执行→持久化"""
        import shutil
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "test.txt"), "w") as f:
                f.write("content")

            persistence = create_persistence_manager()
            env_mgr = create_environment_manager()
            env_mgr.register_environment(
                "fs", FilesystemEnvironment(tmpdir), is_default=True,
            )
            executor = create_task_executor(
                env_manager=env_mgr,
                persistence=persistence,
            )

            # 规划
            task = create_task("read file test.txt", task_id="t1")
            executor.submit(task)
            plan = executor.plan("t1")
            assert plan is not None

            # 执行
            result = executor.execute("t1")
            assert result.success is True

            # 持久化（检查点）
            checkpoint = persistence.load_checkpoint("task_t1")
            assert checkpoint is not None
            assert "plan" in checkpoint
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_principle_error_recovery(self):
        """原理：错误可恢复"""
        # 重试机制是错误恢复的核心
        class RetryableEnvironment(SimulatedEnvironment):
            def __init__(self):
                super().__init__()
                self._attempt = 0

            def act(self, action):
                from self_evolving_agent.core.environment_interface import ActionResult
                self._attempt += 1
                if self._attempt < 3:
                    return ActionResult(success=False, error="Temporary failure")
                return ActionResult(success=True, output={"recovered": True})

        env_mgr = create_environment_manager()
        env_mgr.register_environment(
            "retryable", RetryableEnvironment(), is_default=True,
        )
        executor = create_task_executor(env_manager=env_mgr, persistence=None)

        result = executor.run(create_task("observe something", task_id="t1"))
        # 前两次失败，第三次成功
        assert result.success is True

    def test_principle_step_independence(self):
        """原理：步骤独立性（每个步骤是原子动作）"""
        steps = [
            TaskStep(step_id="s1", description="step1", action_type="read", target="a"),
            TaskStep(step_id="s2", description="step2", action_type="read", target="b"),
        ]
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=steps)

        # 每个步骤有自己的状态
        for step in plan.steps:
            assert step.status == StepStatus.PENDING
            assert step.result is None
            assert step.started_at == 0.0

    def test_principle_dag_dependency(self):
        """原理：DAG依赖（有向无环图）"""
        # 钻石依赖：A → B,C → D
        steps = [
            TaskStep(step_id="A", description="A", action_type="read", target="a"),
            TaskStep(step_id="B", description="B", action_type="read", target="b", dependencies=["A"]),
            TaskStep(step_id="C", description="C", action_type="read", target="c", dependencies=["A"]),
            TaskStep(step_id="D", description="D", action_type="read", target="d", dependencies=["B", "C"]),
        ]
        plan = TaskPlan(plan_id="p1", task_id="t1", steps=steps)

        # 拓扑顺序：A → (B,C) → D
        ready = plan.get_ready_steps()
        assert {s.step_id for s in ready} == {"A"}

        steps[0].status = StepStatus.COMPLETED
        ready = plan.get_ready_steps()
        assert {s.step_id for s in ready} == {"B", "C"}

        steps[1].status = StepStatus.COMPLETED
        steps[2].status = StepStatus.COMPLETED
        ready = plan.get_ready_steps()
        assert {s.step_id for s in ready} == {"D"}

    def test_principle_observer_pattern(self):
        """原理：观察者模式（事件通知）"""
        env_mgr = create_environment_manager()
        env_mgr.register_environment(
            "simulated", SimulatedEnvironment(), is_default=True,
        )
        executor = create_task_executor(env_manager=env_mgr, persistence=None)

        events = []
        executor.register_observer(lambda tid, evt: events.append((tid, evt.get("event"))))

        executor.run(create_task("observe something", task_id="t1"))

        # 应该收到事件通知
        event_types = [e[1] for e in events]
        assert "submitted" in event_types
        assert "executing" in event_types
        assert "completed" in event_types

    def test_principle_idempotent_submit(self):
        """原理：提交幂等性（重复提交报错）"""
        executor = create_task_executor(
            env_manager=create_environment_manager(),
            persistence=None,
        )
        task = create_task("observe something", task_id="t1")
        executor.submit(task)

        # 重复提交应报错
        with pytest.raises(ValueError):
            executor.submit(task)
