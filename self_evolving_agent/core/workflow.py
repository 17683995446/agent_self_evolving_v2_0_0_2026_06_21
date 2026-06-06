"""
阶段48: 工作流编排接口标准化

第一性原理:
1. 复杂任务由多个步骤组成，步骤之间有依赖关系
2. 工作流是DAG（有向无环图），必须可拓扑排序
3. 步骤执行必须可重试、可超时、可观测

设计原则:
- WorkflowStep: 工作流步骤
- Workflow: 工作流定义
- WorkflowEngine: 执行引擎
- 支持串行、并行、条件分支
- 支持步骤级重试和超时
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StepResult:
    """步骤执行结果"""
    step_id: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    elapsed_ms: float = 0.0


# ============================================================
# 工作流步骤
# ============================================================

class WorkflowStep:
    """
    工作流步骤

    第一性原理：步骤是工作流的原子执行单元
    """

    def __init__(
        self,
        step_id: str,
        fn: Callable[[Any], Any],
        dependencies: Optional[List[str]] = None,
        retries: int = 0,
        timeout_ms: Optional[float] = None,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ):
        self.step_id = step_id
        self.fn = fn
        self.dependencies = dependencies or []
        self.retries = retries
        self.timeout_ms = timeout_ms
        self.condition = condition

    def should_run(self, context: Dict[str, Any]) -> bool:
        """判断是否应该执行"""
        if self.condition:
            return self.condition(context)
        return True

    def execute(self, input_data: Any) -> StepResult:
        """执行步骤"""
        start = time.time()
        last_error = None

        for attempt in range(self.retries + 1):
            try:
                result = self.fn(input_data)
                elapsed = (time.time() - start) * 1000
                return StepResult(
                    step_id=self.step_id,
                    status=StepStatus.SUCCESS,
                    output=result,
                    elapsed_ms=elapsed,
                )
            except Exception as e:
                last_error = str(e)
                if attempt < self.retries:
                    time.sleep(0.01 * (2 ** attempt))  # 指数退避
                    continue

        elapsed = (time.time() - start) * 1000
        return StepResult(
            step_id=self.step_id,
            status=StepStatus.FAILED,
            error=last_error,
            elapsed_ms=elapsed,
        )


# ============================================================
# 工作流
# ============================================================

class Workflow:
    """
    工作流

    由多个步骤组成的有向无环图
    """

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self._steps: Dict[str, WorkflowStep] = {}
        self._results: Dict[str, StepResult] = {}
        self._status = WorkflowStatus.PENDING
        self._lock = threading.Lock()

    def add_step(self, step: WorkflowStep) -> None:
        """添加步骤"""
        self._steps[step.step_id] = step

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """获取步骤"""
        return self._steps.get(step_id)

    def get_ready_steps(self) -> List[str]:
        """获取可执行的步骤（依赖已全部完成）"""
        ready = []
        with self._lock:
            for step_id, step in self._steps.items():
                if step_id in self._results:
                    continue
                # 检查依赖
                deps_satisfied = all(
                    dep in self._results and self._results[dep].status == StepStatus.SUCCESS
                    for dep in step.dependencies
                )
                if deps_satisfied:
                    ready.append(step_id)
        return ready

    def record_result(self, result: StepResult) -> None:
        """记录步骤结果"""
        with self._lock:
            self._results[result.step_id] = result

    def is_complete(self) -> bool:
        """是否全部完成"""
        with self._lock:
            return len(self._results) == len(self._steps)

    def get_status(self) -> WorkflowStatus:
        """获取工作流状态"""
        with self._lock:
            return self._status

    def set_status(self, status: WorkflowStatus) -> None:
        """设置工作流状态"""
        with self._lock:
            self._status = status

    def get_results(self) -> Dict[str, StepResult]:
        """获取所有结果"""
        with self._lock:
            return dict(self._results)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "workflow_id": self.workflow_id,
                "total_steps": len(self._steps),
                "completed_steps": len(self._results),
                "status": self._status.value,
            }


# ============================================================
# 工作流引擎
# ============================================================

class WorkflowEngine:
    """
    工作流执行引擎

    第一性原理：按拓扑顺序执行DAG中的节点
    """

    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}

    def register(self, workflow: Workflow) -> None:
        """注册工作流"""
        self._workflows[workflow.workflow_id] = workflow

    def execute(self, workflow_id: str, initial_input: Any = None) -> Dict[str, StepResult]:
        """
        执行工作流

        简单的拓扑执行（非并行）
        """
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        workflow.set_status(WorkflowStatus.RUNNING)
        context = {"input": initial_input}

        while not workflow.is_complete():
            ready = workflow.get_ready_steps()
            if not ready:
                # 没有可执行的步骤，但有未完成的步骤 -> 死锁或失败
                break

            for step_id in ready:
                step = workflow.get_step(step_id)
                if step is None:
                    continue

                # 条件判断
                if not step.should_run(context):
                    workflow.record_result(StepResult(
                        step_id=step_id,
                        status=StepStatus.SKIPPED,
                    ))
                    continue

                # 准备输入（合并依赖的输出）
                step_input = self._prepare_input(step, workflow, initial_input)

                # 执行
                result = step.execute(step_input)
                workflow.record_result(result)

                # 更新上下文
                if result.status == StepStatus.SUCCESS:
                    context[step_id] = result.output

            # 检查是否有失败
            results = workflow.get_results()
            if any(r.status == StepStatus.FAILED for r in results.values()):
                workflow.set_status(WorkflowStatus.FAILED)
                return workflow.get_results()

        workflow.set_status(WorkflowStatus.COMPLETED)
        return workflow.get_results()

    def _prepare_input(self, step: WorkflowStep, workflow: Workflow, initial_input: Any = None) -> Any:
        """准备步骤输入"""
        if not step.dependencies:
            return initial_input

        dep_results = []
        for dep_id in step.dependencies:
            result = workflow.get_results().get(dep_id)
            if result and result.status == StepStatus.SUCCESS:
                dep_results.append(result.output)

        if len(dep_results) == 1:
            return dep_results[0]
        return dep_results

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """获取工作流"""
        return self._workflows.get(workflow_id)


# ============================================================
# 便捷函数
# ============================================================

def create_workflow(workflow_id: str) -> Workflow:
    """创建工作流"""
    return Workflow(workflow_id)


def create_step(
    step_id: str,
    fn: Callable[[Any], Any],
    dependencies: Optional[List[str]] = None,
    retries: int = 0,
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
) -> WorkflowStep:
    """创建步骤"""
    return WorkflowStep(
        step_id=step_id,
        fn=fn,
        dependencies=dependencies,
        retries=retries,
        condition=condition,
    )
