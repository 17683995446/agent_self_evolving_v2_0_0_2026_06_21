"""
阶段127: 端到端任务执行器

第一性原理:
1. 任务 = 目标 + 约束 + 上下文
2. 执行 = 规划 → 行动 → 验证 → 反思
3. 每一步都可持久化，支持恢复
4. 错误可恢复时重试，不可恢复时降级
5. 规划优先使用规则（确定性），LLM辅助增强（语义性）

提供:
- Task: 任务定义
- TaskStep: 任务步骤
- TaskPlan: 任务规划
- TaskResult: 任务结果
- TaskPlanner: 任务规划器（规则+LLM协同）
- TaskExecutor: 端到端任务执行器
"""

import time
import threading
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


# ============================================================
# 数据结构
# ============================================================

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"            # 待处理
    PLANNING = "planning"          # 规划中
    READY = "ready"                # 已规划，待执行
    EXECUTING = "executing"        # 执行中
    VERIFYING = "verifying"        # 验证中
    COMPLETED = "completed"        # 已完成
    FAILED = "failed"              # 失败
    CANCELLED = "cancelled"        # 已取消
    PAUSED = "paused"              # 已暂停


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    READY = "ready"                # 依赖已满足，可执行
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"            # 跳过（条件不满足）


@dataclass
class Task:
    """任务定义"""
    task_id: str
    goal: str                                      # 自然语言目标
    constraints: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "constraints": self.constraints,
            "context": self.context,
            "priority": self.priority,
            "created_at": self.created_at,
            "deadline": self.deadline,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(
            task_id=data.get("task_id", ""),
            goal=data.get("goal", ""),
            constraints=data.get("constraints", {}),
            context=data.get("context", {}),
            priority=data.get("priority", 0),
            created_at=data.get("created_at", time.time()),
            deadline=data.get("deadline"),
            tags=data.get("tags", []),
        )


@dataclass
class TaskStep:
    """任务步骤"""
    step_id: str
    description: str                               # 自然语言描述
    action_type: str                               # 动作类型（read/write/list/execute/get...）
    target: str                                    # 动作目标
    parameters: Dict[str, Any] = field(default_factory=dict)
    env_id: Optional[str] = None                   # 指定环境（None=默认）
    dependencies: List[str] = field(default_factory=list)  # 依赖的步骤ID
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None        # 执行结果
    output_key: Optional[str] = None               # 输出键名（用于后续步骤引用）
    retry_count: int = 0
    max_retries: int = 3
    condition: Optional[str] = None                # 执行条件（表达式）
    started_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "action_type": self.action_type,
            "target": self.target,
            "parameters": self.parameters,
            "env_id": self.env_id,
            "dependencies": list(self.dependencies),
            "status": self.status.value,
            "result": self.result,
            "output_key": self.output_key,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "condition": self.condition,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskStep":
        return cls(
            step_id=data.get("step_id", ""),
            description=data.get("description", ""),
            action_type=data.get("action_type", ""),
            target=data.get("target", ""),
            parameters=data.get("parameters", {}),
            env_id=data.get("env_id"),
            dependencies=data.get("dependencies", []),
            status=StepStatus(data.get("status", "pending")),
            result=data.get("result"),
            output_key=data.get("output_key"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            condition=data.get("condition"),
            started_at=data.get("started_at", 0.0),
            completed_at=data.get("completed_at", 0.0),
        )


@dataclass
class TaskPlan:
    """任务规划"""
    plan_id: str
    task_id: str
    steps: List[TaskStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    reasoning: Optional[Dict[str, Any]] = None     # 规划推理过程

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskPlan":
        return cls(
            plan_id=data.get("plan_id", ""),
            task_id=data.get("task_id", ""),
            steps=[TaskStep.from_dict(s) for s in data.get("steps", [])],
            created_at=data.get("created_at", time.time()),
            reasoning=data.get("reasoning"),
        )

    def get_step(self, step_id: str) -> Optional[TaskStep]:
        """获取步骤"""
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return None

    def get_ready_steps(self) -> List[TaskStep]:
        """获取可执行步骤（依赖已完成）"""
        completed_ids = {
            s.step_id for s in self.steps if s.status == StepStatus.COMPLETED
        }
        ready = []
        for s in self.steps:
            if s.status != StepStatus.PENDING:
                continue
            if all(dep in completed_ids for dep in s.dependencies):
                ready.append(s)
        return ready

    def is_complete(self) -> bool:
        """是否所有步骤都已完成"""
        if not self.steps:
            return True
        return all(
            s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
            for s in self.steps
        )

    def has_failed(self) -> bool:
        """是否有失败步骤（且无法重试）"""
        for s in self.steps:
            if s.status == StepStatus.FAILED and s.retry_count >= s.max_retries:
                return True
        return False


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    success: bool
    status: TaskStatus
    plan: Optional[TaskPlan] = None
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: float = 0.0
    completed_at: float = 0.0
    steps_completed: int = 0
    steps_total: int = 0
    steps_failed: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "status": self.status.value,
            "plan": self.plan.to_dict() if self.plan else None,
            "outputs": self.outputs,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "steps_completed": self.steps_completed,
            "steps_total": self.steps_total,
            "steps_failed": self.steps_failed,
            "duration_ms": self.duration_ms,
        }


# ============================================================
# 任务规划器
# ============================================================

class TaskPlanner:
    """
    任务规划器

    第一性原理：
    - 规划 = 将目标分解为可执行步骤序列
    - 规则优先（确定性），LLM辅助（语义性）
    - 每个步骤映射到一个环境动作
    - 步骤间可有依赖关系（DAG）
    """

    # 动作模式匹配规则（按优先级排序）
    ACTION_PATTERNS: List[Dict[str, Any]] = [
        # 文件读取
        {
            "pattern": r"(?:read|读取|查看|cat)\s*(?:file\s+|文件\s*)?\s*(.+)",
            "action_type": "read",
            "target_group": 1,
            "env_hint": "filesystem",
        },
        # 文件写入
        {
            "pattern": r"(?:write|写入|保存|save)\s*(?:file\s+|文件\s*)?\s*(.+?)(?:\s+with\s+|\s+内容[:：]\s*|\s+content[:：]\s*)(.+)",
            "action_type": "write",
            "target_group": 1,
            "params": {"content_group": 2},
            "env_hint": "filesystem",
        },
        # 目录列表
        {
            "pattern": r"(?:list|列出|ls|dir)\s*(?:dir(?:ectory)?\s+|目录\s*)?\s*(.+)",
            "action_type": "list",
            "target_group": 1,
            "env_hint": "filesystem",
        },
        # 创建目录
        {
            "pattern": r"(?:mkdir|create\s+dir|创建目录)\s+(.+)",
            "action_type": "mkdir",
            "target_group": 1,
            "env_hint": "filesystem",
        },
        # 删除
        {
            "pattern": r"(?:delete|remove|删除|rm)\s+(.+)",
            "action_type": "delete",
            "target_group": 1,
            "env_hint": "filesystem",
        },
        # HTTP GET
        {
            "pattern": r"(?:fetch|get|获取|请求)\s+(?:url\s+)?(https?://\S+)",
            "action_type": "get",
            "target_group": 1,
            "env_hint": "http",
        },
        # 命令执行
        {
            "pattern": r"(?:execute|run|执行|运行)\s+(?:command\s+)?(.+)",
            "action_type": "execute",
            "target_group": 1,
            "env_hint": "command",
        },
        # 观察
        {
            "pattern": r"(?:observe|感知|观察)\s*(.*)",
            "action_type": "observe",
            "target_group": 1,
            "env_hint": None,
        },
    ]

    def __init__(self, llm_coordinator=None):
        self._llm_coordinator = llm_coordinator
        self._lock = threading.RLock()

    def plan(self, task: Task) -> TaskPlan:
        """
        规划任务

        第一性原理：
        - 优先使用规则解析（确定性）
        - LLM辅助分解复杂目标（语义性）
        - 规则失败时降级到单步执行
        """
        plan_id = f"plan_{task.task_id}_{int(time.time() * 1000)}"

        # 尝试规则解析
        steps = self._plan_by_rules(task)
        reasoning = {"method": "rules", "step_count": len(steps)}

        # 如果规则解析失败且有LLM，尝试LLM辅助
        if not steps and self._llm_coordinator is not None:
            llm_steps, llm_reasoning = self._plan_by_llm(task)
            if llm_steps:
                steps = llm_steps
                reasoning = {"method": "llm", "step_count": len(steps), "llm": llm_reasoning}

        # 如果都失败，创建单步兜底
        if not steps:
            steps = [TaskStep(
                step_id=f"step_{task.task_id}_fallback",
                description=f"执行目标: {task.goal}",
                action_type="observe",
                target="default",
                parameters={"goal": task.goal},
            )]
            reasoning = {"method": "fallback", "step_count": 1}

        return TaskPlan(
            plan_id=plan_id,
            task_id=task.task_id,
            steps=steps,
            reasoning=reasoning,
        )

    def _plan_by_rules(self, task: Task) -> List[TaskStep]:
        """规则解析规划"""
        # 防御：空目标
        if not task.goal or not task.goal.strip():
            return []

        goal = task.goal.strip()
        steps: List[TaskStep] = []

        # 尝试按分隔符分解多个子目标
        sub_goals = self._split_goals(goal)

        prev_step_id: Optional[str] = None
        for i, sub_goal in enumerate(sub_goals):
            step = self._parse_single_action(sub_goal, task.task_id, i)
            if step is not None:
                # 串行依赖（前一步完成后才执行下一步）
                if prev_step_id and not step.dependencies:
                    step.dependencies = [prev_step_id]
                steps.append(step)
                prev_step_id = step.step_id

        return steps

    def _split_goals(self, goal: str) -> List[str]:
        """分解多个子目标"""
        # 按分号、换行、"然后"、"then"分解
        parts = re.split(r'[;\n]|(?:然后)|(?:then)', goal, flags=re.IGNORECASE)
        return [p.strip() for p in parts if p.strip()]

    def _parse_single_action(
        self,
        sub_goal: str,
        task_id: str,
        index: int,
    ) -> Optional[TaskStep]:
        """解析单个动作"""
        for pattern_def in self.ACTION_PATTERNS:
            match = re.match(pattern_def["pattern"], sub_goal, re.IGNORECASE)
            if match:
                target = match.group(pattern_def["target_group"]).strip()
                params: Dict[str, Any] = {}

                # 提取额外参数
                if "params" in pattern_def:
                    for param_name, group_idx in pattern_def["params"].items():
                        try:
                            params[param_name.replace("_group", "")] = match.group(group_idx)
                        except (IndexError, AttributeError):
                            pass

                step_id = f"step_{task_id}_{index}"
                return TaskStep(
                    step_id=step_id,
                    description=sub_goal,
                    action_type=pattern_def["action_type"],
                    target=target,
                    parameters=params,
                    env_id=pattern_def.get("env_hint"),
                    output_key=f"output_{index}",
                )

        # 无法匹配，创建通用观察步骤
        return TaskStep(
            step_id=f"step_{task_id}_{index}",
            description=sub_goal,
            action_type="observe",
            target="default",
            parameters={"goal": sub_goal},
            output_key=f"output_{index}",
        )

    def _plan_by_llm(self, task: Task) -> tuple:
        """LLM辅助规划"""
        try:
            from .llm_reasoning_coordinator import (
                ReasoningTask, TaskType, ReasoningMode, create_reasoning_task,
            )
            reasoning_task = create_reasoning_task(
                task_id=f"plan_{task.task_id}",
                query=f"将以下目标分解为可执行步骤: {task.goal}",
                task_type=TaskType.ANALYSIS,
                context=task.context,
                mode=ReasoningMode.HYBRID,
            )
            result = self._llm_coordinator.reason(reasoning_task)
            if not result.success:
                return [], {"success": False, "error": result.error}

            # 从LLM结果中提取步骤（简化：将回答作为单步描述）
            # 实际生产中应解析JSON结构化输出
            steps = [TaskStep(
                step_id=f"step_{task.task_id}_llm_0",
                description=result.answer[:500],
                action_type="observe",
                target="default",
                parameters={"llm_plan": result.answer, "goal": task.goal},
                output_key="output_llm_0",
            )]
            return steps, {
                "success": True,
                "confidence": result.confidence,
                "sources": result.sources,
            }
        except Exception as e:
            return [], {"success": False, "error": str(e)}


# ============================================================
# 端到端任务执行器
# ============================================================

class TaskExecutor:
    """
    端到端任务执行器

    第一性原理：
    1. 执行 = 规划 → 行动 → 验证 → 持久化
    2. 每步执行后保存检查点，支持恢复
    3. 失败时重试，超过阈值则降级
    4. 步骤间通过输出键传递数据
    5. 线程安全：支持并发任务提交

    生命周期:
    submit → plan → execute → (verify → checkpoint) per step → complete
    """

    def __init__(
        self,
        env_manager,
        llm_coordinator=None,
        persistence=None,
        coordinator=None,
        executor_id: str = "task_executor",
    ):
        self.executor_id = executor_id
        self._env_manager = env_manager
        self._llm_coordinator = llm_coordinator
        self._persistence = persistence
        self._coordinator = coordinator
        self._planner = TaskPlanner(llm_coordinator)

        self._lock = threading.RLock()
        self._tasks: Dict[str, Task] = {}
        self._plans: Dict[str, TaskPlan] = {}
        self._results: Dict[str, TaskResult] = {}
        self._status: Dict[str, TaskStatus] = {}
        self._outputs: Dict[str, Dict[str, Any]] = {}  # task_id → step outputs

        self._observers: List[Callable[[str, Dict[str, Any]], None]] = []
        self._max_tasks = 10000
        self._checkpoint_interval = 1  # 每N步保存检查点

    # ============================================================
    # 公开接口
    # ============================================================

    def submit(self, task: Task) -> str:
        """
        提交任务

        返回 task_id
        """
        with self._lock:
            # 防御：任务ID冲突
            if task.task_id in self._tasks:
                raise ValueError(f"Task already exists: {task.task_id}")

            self._tasks[task.task_id] = task
            self._status[task.task_id] = TaskStatus.PENDING
            self._outputs[task.task_id] = {}

            # 容量限制
            if len(self._tasks) > self._max_tasks:
                self._evict_old_tasks()

        self._notify(task.task_id, {"event": "submitted", "goal": task.goal})
        return task.task_id

    def plan(self, task_id: str) -> Optional[TaskPlan]:
        """规划任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            self._status[task_id] = TaskStatus.PLANNING

        plan = self._planner.plan(task)

        with self._lock:
            self._plans[task_id] = plan
            self._status[task_id] = TaskStatus.READY

        self._notify(task_id, {"event": "planned", "step_count": len(plan.steps)})
        return plan

    def execute(self, task_id: str) -> TaskResult:
        """
        执行任务（端到端）

        第一性原理：
        - 规划（如未规划）
        - 按依赖顺序执行步骤
        - 每步验证 + 检查点
        - 失败重试，超阈值降级
        """
        start_time = time.time()

        # 防御：任务不存在
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return TaskResult(
                    task_id=task_id,
                    success=False,
                    status=TaskStatus.FAILED,
                    error=f"Task not found: {task_id}",
                    started_at=start_time,
                    completed_at=time.time(),
                )
            current_status = self._status.get(task_id)

        # 如果已完成/已取消，直接返回
        if current_status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            return self._results.get(task_id, TaskResult(
                task_id=task_id,
                success=current_status == TaskStatus.COMPLETED,
                status=current_status,
            ))

        # 规划（如未规划）
        plan = self._plans.get(task_id)
        if plan is None:
            plan = self.plan(task_id)
            if plan is None:
                return TaskResult(
                    task_id=task_id,
                    success=False,
                    status=TaskStatus.FAILED,
                    error="Planning failed",
                    started_at=start_time,
                    completed_at=time.time(),
                )

        # 执行
        with self._lock:
            self._status[task_id] = TaskStatus.EXECUTING

        self._notify(task_id, {"event": "executing", "step_count": len(plan.steps)})

        error_msg: Optional[str] = None
        step_count = 0

        while not plan.is_complete() and not plan.has_failed():
            ready_steps = plan.get_ready_steps()
            if not ready_steps:
                # 无可执行步骤且未完成 → 死锁
                error_msg = "No ready steps but plan not complete (possible deadlock)"
                break

            for step in ready_steps:
                step_count += 1
                step_result = self._execute_step(task_id, step, plan)

                # 检查点
                if step_count % self._checkpoint_interval == 0:
                    self._save_checkpoint(task_id, plan)

                if not step_result and step.status == StepStatus.FAILED:
                    if step.retry_count >= step.max_retries:
                        error_msg = f"Step {step.step_id} failed after {step.retry_count} retries"
                        break

            if error_msg:
                break

        # 构建结果
        completed_at = time.time()
        steps_completed = sum(1 for s in plan.steps if s.status == StepStatus.COMPLETED)
        steps_failed = sum(1 for s in plan.steps if s.status == StepStatus.FAILED)
        steps_total = len(plan.steps)

        success = plan.is_complete() and error_msg is None
        final_status = TaskStatus.COMPLETED if success else TaskStatus.FAILED

        result = TaskResult(
            task_id=task_id,
            success=success,
            status=final_status,
            plan=plan,
            outputs=dict(self._outputs.get(task_id, {})),
            error=error_msg,
            started_at=start_time,
            completed_at=completed_at,
            steps_completed=steps_completed,
            steps_total=steps_total,
            steps_failed=steps_failed,
            duration_ms=(completed_at - start_time) * 1000,
        )

        with self._lock:
            self._results[task_id] = result
            self._status[task_id] = final_status

        # 最终检查点
        self._save_checkpoint(task_id, plan)

        self._notify(task_id, {
            "event": "completed" if success else "failed",
            "steps_completed": steps_completed,
            "steps_total": steps_total,
            "duration_ms": result.duration_ms,
        })

        return result

    def run(self, task: Task) -> TaskResult:
        """便捷方法：提交+规划+执行"""
        self.submit(task)
        return self.execute(task.task_id)

    def resume(self, task_id: str) -> TaskResult:
        """从检查点恢复执行"""
        # 加载检查点
        if self._persistence is None:
            return TaskResult(
                task_id=task_id,
                success=False,
                status=TaskStatus.FAILED,
                error="No persistence available for resume",
            )

        checkpoint = self._persistence.load_checkpoint(f"task_{task_id}")
        if checkpoint is None:
            return TaskResult(
                task_id=task_id,
                success=False,
                status=TaskStatus.FAILED,
                error="No checkpoint found",
            )

        # 恢复计划
        plan_data = checkpoint.get("plan")
        if plan_data:
            plan = TaskPlan.from_dict(plan_data)
            with self._lock:
                self._plans[task_id] = plan
                self._outputs[task_id] = checkpoint.get("outputs", {})

        return self.execute(task_id)

    def cancel(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            if task_id not in self._tasks:
                return False
            self._status[task_id] = TaskStatus.CANCELLED

        self._notify(task_id, {"event": "cancelled"})
        return True

    def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        with self._lock:
            return self._status.get(task_id)

    def get_plan(self, task_id: str) -> Optional[TaskPlan]:
        """获取任务计划"""
        with self._lock:
            return self._plans.get(task_id)

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        with self._lock:
            return self._results.get(task_id)

    def get_outputs(self, task_id: str) -> Dict[str, Any]:
        """获取任务输出"""
        with self._lock:
            return dict(self._outputs.get(task_id, {}))

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[str]:
        """列出任务"""
        with self._lock:
            if status is None:
                return list(self._tasks.keys())
            return [
                tid for tid, s in self._status.items() if s == status
            ]

    def register_observer(
        self,
        observer: Callable[[str, Dict[str, Any]], None],
    ) -> None:
        """注册任务事件观察者"""
        with self._lock:
            self._observers.append(observer)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total = len(self._tasks)
            by_status: Dict[str, int] = {}
            for s in self._status.values():
                by_status[s.value] = by_status.get(s.value, 0) + 1
            return {
                "executor_id": self.executor_id,
                "total_tasks": total,
                "by_status": by_status,
                "max_tasks": self._max_tasks,
            }

    def clear_completed(self) -> int:
        """清除已完成/失败的任务"""
        with self._lock:
            to_remove = [
                tid for tid, s in self._status.items()
                if s in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
            ]
            for tid in to_remove:
                self._tasks.pop(tid, None)
                self._plans.pop(tid, None)
                self._results.pop(tid, None)
                self._status.pop(tid, None)
                self._outputs.pop(tid, None)
            return len(to_remove)

    # ============================================================
    # 内部实现
    # ============================================================

    def _execute_step(
        self,
        task_id: str,
        step: TaskStep,
        plan: TaskPlan,
    ) -> bool:
        """
        执行单个步骤

        返回是否成功
        """
        # 检查条件
        if step.condition and not self._evaluate_condition(step, plan):
            step.status = StepStatus.SKIPPED
            self._notify(task_id, {"event": "step_skipped", "step_id": step.step_id})
            return True

        step.status = StepStatus.EXECUTING
        step.started_at = time.time()

        self._notify(task_id, {"event": "step_started", "step_id": step.step_id})

        # 替换参数中的输出引用
        params = self._resolve_references(step.parameters, task_id)

        # 解析环境ID（阶段127：env_hint可能不匹配实际注册的ID）
        resolved_env_id = self._resolve_env_id(step.env_id, step.action_type)

        # 构建环境动作
        from .environment_interface import EnvironmentAction, create_environment_action

        action = create_environment_action(
            action_type=step.action_type,
            target=step.target,
            parameters=params,
        )

        # 执行（带重试）
        success = False
        last_error: Optional[str] = None

        while step.retry_count <= step.max_retries:
            try:
                result = self._env_manager.act(action, resolved_env_id)

                if result.success:
                    step.result = {
                        "success": True,
                        "output": self._serialize_output(result.output),
                        "duration": result.duration,
                    }
                    step.status = StepStatus.COMPLETED
                    step.completed_at = time.time()
                    success = True

                    # 存储输出
                    if step.output_key:
                        with self._lock:
                            self._outputs.setdefault(task_id, {})[step.output_key] = (
                                self._serialize_output(result.output)
                            )
                    break
                else:
                    last_error = result.error or "Action failed"
                    step.retry_count += 1
                    if step.retry_count <= step.max_retries:
                        time.sleep(min(0.1 * step.retry_count, 1.0))

            except Exception as e:
                last_error = str(e)
                step.retry_count += 1
                if step.retry_count <= step.max_retries:
                    time.sleep(min(0.1 * step.retry_count, 1.0))

        if not success:
            step.result = {
                "success": False,
                "error": last_error,
                "retries": step.retry_count,
            }
            step.status = StepStatus.FAILED
            step.completed_at = time.time()
            self._notify(task_id, {
                "event": "step_failed",
                "step_id": step.step_id,
                "error": last_error,
            })
        else:
            self._notify(task_id, {
                "event": "step_completed",
                "step_id": step.step_id,
                "duration": step.completed_at - step.started_at,
            })

        return success

    def _resolve_references(
        self,
        params: Dict[str, Any],
        task_id: str,
    ) -> Dict[str, Any]:
        """
        解析参数中的输出引用

        格式: ${output_<index>} 或 ${output_key}
        """
        with self._lock:
            outputs = self._outputs.get(task_id, {})

        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                ref_key = value[2:-1]
                resolved[key] = outputs.get(ref_key, value)
            else:
                resolved[key] = value
        return resolved

    def _resolve_env_id(
        self,
        env_id: Optional[str],
        action_type: str,
    ) -> Optional[str]:
        """
        解析环境ID

        第一性原理：
        - 规划器生成的env_id是"提示"（如filesystem/http/command）
        - 实际注册的环境ID可能不同（如fs/web/shell）
        - 解析策略：精确匹配 → 类型匹配 → 默认环境
        """
        # 无提示 → 使用默认
        if env_id is None:
            return None

        # 精确匹配
        registered_ids = self._env_manager.get_environment_ids()
        if env_id in registered_ids:
            return env_id

        # 类型匹配：根据action_type推断环境类型
        type_mapping = {
            "read": "filesystem", "write": "filesystem", "list": "filesystem",
            "delete": "filesystem", "mkdir": "filesystem",
            "get": "http", "post": "http", "put": "http", "delete_http": "http",
            "execute": "command",
            "observe": None,
        }
        expected_type = type_mapping.get(action_type)

        if expected_type:
            # 尝试按ID名称匹配已注册环境
            for rid in registered_ids:
                if expected_type in rid.lower() or rid.lower() in expected_type:
                    return rid

            # 检查环境的实际类型（通过类名）
            type_class_map = {
                "filesystem": "FilesystemEnvironment",
                "http": "HTTPEnvironment",
                "command": "CommandEnvironment",
                "simulated": "SimulatedEnvironment",
            }
            expected_class = type_class_map.get(expected_type)
            if expected_class:
                for rid in registered_ids:
                    env = self._env_manager.get_environment(rid)
                    if env is None:
                        continue
                    if type(env).__name__ == expected_class:
                        return rid

        # 回退到默认环境
        return None

    def _evaluate_condition(self, step: TaskStep, plan: TaskPlan) -> bool:
        """评估步骤条件（简化版：只支持输出存在性检查）"""
        if not step.condition:
            return True
        try:
            # 简化：条件格式为 "exists:output_key"
            if step.condition.startswith("exists:"):
                key = step.condition[7:]
                for s in plan.steps:
                    if s.output_key == key and s.status == StepStatus.COMPLETED:
                        return True
                return False
            return True
        except Exception:
            return True

    def _serialize_output(self, output: Any) -> Any:
        """序列化输出（确保可JSON化）"""
        if output is None:
            return None
        if isinstance(output, (str, int, float, bool)):
            return output
        if isinstance(output, dict):
            return {str(k): self._serialize_output(v) for k, v in output.items()}
        if isinstance(output, (list, tuple)):
            return [self._serialize_output(item) for item in output]
        # 其他类型转为字符串
        try:
            return str(output)
        except Exception:
            return "<unserializable>"

    def _save_checkpoint(self, task_id: str, plan: TaskPlan) -> None:
        """保存检查点"""
        if self._persistence is None:
            return
        try:
            with self._lock:
                state = {
                    "task_id": task_id,
                    "plan": plan.to_dict(),
                    "outputs": dict(self._outputs.get(task_id, {})),
                    "status": self._status.get(task_id, TaskStatus.EXECUTING).value,
                    "timestamp": time.time(),
                }
            self._persistence.save_checkpoint(f"task_{task_id}", state)
        except Exception:
            pass

    def _notify(self, task_id: str, event: Dict[str, Any]) -> None:
        """通知观察者"""
        observers = list(self._observers)
        for observer in observers:
            try:
                observer(task_id, event)
            except Exception:
                pass

    def _evict_old_tasks(self) -> None:
        """淘汰旧任务（LRU）"""
        # 按创建时间排序，淘汰最旧的已完成任务
        completed = [
            (tid, t.created_at)
            for tid, t in self._tasks.items()
            if self._status.get(tid) in (
                TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED
            )
        ]
        completed.sort(key=lambda x: x[1])

        # 淘汰10%
        evict_count = max(1, len(self._tasks) // 10)
        for tid, _ in completed[:evict_count]:
            self._tasks.pop(tid, None)
            self._plans.pop(tid, None)
            self._results.pop(tid, None)
            self._status.pop(tid, None)
            self._outputs.pop(tid, None)


# ============================================================
# 便捷函数
# ============================================================

def create_task(
    goal: str,
    task_id: Optional[str] = None,
    constraints: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    priority: int = 0,
) -> Task:
    """创建任务"""
    if task_id is None:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
    return Task(
        task_id=task_id,
        goal=goal,
        constraints=constraints or {},
        context=context or {},
        priority=priority,
    )


def create_task_executor(
    env_manager,
    llm_coordinator=None,
    persistence=None,
    coordinator=None,
    executor_id: str = "task_executor",
) -> TaskExecutor:
    """创建任务执行器"""
    return TaskExecutor(
        env_manager=env_manager,
        llm_coordinator=llm_coordinator,
        persistence=persistence,
        coordinator=coordinator,
        executor_id=executor_id,
    )
