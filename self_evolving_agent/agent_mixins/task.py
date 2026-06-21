"""任务执行Mixin — 阶段149从agent.py拆分"""

from typing import Optional

from ..core.task_executor import TaskResult, TaskStatus, create_task


class TaskMixin:
    """端到端任务执行接口（阶段127）"""

    def execute_task(self, goal: str, task_id: str = None) -> TaskResult:
        """
        端到端执行任务（阶段127新增）

        Args:
            goal: 自然语言任务目标
            task_id: 可选任务ID（自动生成如果未提供）

        Returns:
            TaskResult: 任务执行结果
        """
        task = create_task(goal=goal, task_id=task_id)
        return self._task_executor.run(task)

    def submit_task(self, goal: str, task_id: str = None) -> str:
        """提交任务（不立即执行，阶段127新增）"""
        task = create_task(goal=goal, task_id=task_id)
        return self._task_executor.submit(task)

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果（阶段127新增）"""
        return self._task_executor.get_result(task_id)

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态（阶段127新增）"""
        return self._task_executor.get_status(task_id)
