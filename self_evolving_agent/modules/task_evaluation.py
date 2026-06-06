"""
自驱永续进化Agent系统 — 任务评估公式化
阶段16：任务评估公式化

第一性原理：任务评估 = 收益 - 成本 + 信息价值
选择最优任务 = 最大化评估得分

数学公式：
Score = w_b * Benefit - w_c * Cost + w_s * SuccessProb + w_i * InfoValue

其中：
- Benefit = 预期收益（解决驱力缺口的程度）
- Cost = 执行成本（资源消耗）
- SuccessProb = 成功概率
- InfoValue = 信息价值（探索价值）
- w_b, w_c, w_s, w_i = 权重系数
"""

import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import deque

from ..core.interfaces import (
    TaskEvaluator, TaskSelector, TaskCandidate,
    BaseModule, AgentMessage, MessageType
)


@dataclass
class EvaluationComponents:
    """评估分量"""
    benefit: float        # 预期收益
    cost: float           # 执行成本
    success_prob: float   # 成功概率
    info_value: float     # 信息价值
    risk: float           # 风险

    def compute_score(self, weights: Dict[str, float]) -> float:
        """
        计算综合得分

        Score = w_b * Benefit - w_c * Cost + w_s * SuccessProb + w_i * InfoValue - w_r * Risk
        """
        score = (
            weights.get("benefit", 0.4) * self.benefit -
            weights.get("cost", 0.3) * self.cost +
            weights.get("success", 0.2) * self.success_prob +
            weights.get("info", 0.1) * self.info_value -
            weights.get("risk", 0.0) * self.risk
        )
        return score


class FormulaTaskEvaluator(TaskEvaluator, BaseModule):
    """
    公式化任务评估器

    每个分量有明确的计算公式
    """

    def __init__(self, module_id: str = "formula_evaluator"):
        BaseModule.__init__(self, module_id)
        self._weights = {
            "benefit": 0.4,
            "cost": 0.3,
            "success": 0.2,
            "info": 0.1,
            "risk": 0.0,
        }
        self._evaluation_history: deque = deque(maxlen=100)

    def evaluate(self, candidate: TaskCandidate,
                 state: Dict[str, Any]) -> TaskCandidate:
        """
        评估候选任务

        计算每个分量并填充到候选任务中
        """
        # 计算各分量
        components = self._compute_components(candidate, state)

        # 计算综合得分
        score = components.compute_score(self._weights)

        # 更新候选任务的评估字段
        candidate.expected_benefit = components.benefit
        candidate.cost = components.cost
        candidate.success_probability = components.success_prob
        candidate.info_value = components.info_value

        # 记录历史
        self._evaluation_history.append({
            "task_id": candidate.task_id,
            "action": candidate.action,
            "components": {
                "benefit": components.benefit,
                "cost": components.cost,
                "success_prob": components.success_prob,
                "info_value": components.info_value,
                "risk": components.risk,
            },
            "score": score,
        })

        return candidate

    def _compute_components(self, candidate: TaskCandidate,
                            state: Dict[str, Any]) -> EvaluationComponents:
        """
        计算评估分量

        公式：
        - Benefit = gap_reduction * impact_factor
        - Cost = resource_usage / resource_available
        - SuccessProb = historical_success * difficulty_factor
        - InfoValue = novelty * uncertainty
        - Risk = failure_cost * failure_probability
        """
        params = candidate.params

        # 收益 = 缺口减少量 × 影响因子
        gap = params.get("gap", 0.5)
        impact_factor = 1.0  # 可配置
        benefit = min(1.0, gap * impact_factor)

        # 成本 = 资源使用 / 可用资源
        cpu_usage = state.get("cpu_usage", 0.5)
        memory_usage = state.get("memory_usage", 0.5)
        resource_available = max(0.1, 1.0 - (cpu_usage + memory_usage) / 2)
        resource_usage = 0.2  # 假设任务消耗20%资源
        cost = min(1.0, resource_usage / resource_available)

        # 成功概率 = 历史成功率 × 难度因子
        historical_success = state.get("historical_success_rate", 0.7)
        difficulty = params.get("difficulty", 0.5)
        difficulty_factor = 1.0 - difficulty * 0.5
        success_prob = min(1.0, historical_success * difficulty_factor)

        # 信息价值 = 新颖性 × 不确定性
        novelty = params.get("novelty", 0.5)
        uncertainty = state.get("uncertainty", 0.3)
        info_value = min(1.0, novelty * uncertainty)

        # 风险 = 失败成本 × 失败概率
        failure_cost = params.get("failure_cost", 0.3)
        failure_prob = 1.0 - success_prob
        risk = min(1.0, failure_cost * failure_prob)

        return EvaluationComponents(
            benefit=benefit,
            cost=cost,
            success_prob=success_prob,
            info_value=info_value,
            risk=risk,
        )

    def get_evaluation_formula(self) -> str:
        """获取评估公式"""
        return (
            "Score = w_b * Benefit - w_c * Cost + "
            "w_s * SuccessProb + w_i * InfoValue - w_r * Risk"
        )

    def get_component_breakdown(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取指定任务的评估分解"""
        for record in self._evaluation_history:
            if record["task_id"] == task_id:
                return record["components"]
        return None

    def initialize(self, config: Dict[str, Any]) -> None:
        self._weights = config.get("weights", self._weights)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.TASK_CANDIDATE:
            candidates_data = message.payload.get("candidates", [])
            state = message.payload.get("state", {})

            evaluated = []
            for c_data in candidates_data:
                candidate = TaskCandidate(
                    task_id=c_data.get("task_id", ""),
                    action=c_data.get("action", ""),
                    params=c_data.get("params", {}),
                )
                evaluated_candidate = self.evaluate(candidate, state)
                evaluated.append({
                    "task_id": evaluated_candidate.task_id,
                    "action": evaluated_candidate.action,
                    "score": evaluated_candidate.score(self._weights),
                    "components": {
                        "benefit": evaluated_candidate.expected_benefit,
                        "cost": evaluated_candidate.cost,
                        "success_prob": evaluated_candidate.success_probability,
                        "info_value": evaluated_candidate.info_value,
                    },
                })

            return AgentMessage(
                msg_type=MessageType.TASK_CANDIDATE,
                source=self.module_id,
                payload={"evaluated_candidates": evaluated},
            )
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        base.update({
            "weights": self._weights,
            "evaluation_history_size": len(self._evaluation_history),
            "formula": self.get_evaluation_formula(),
        })
        return base


class UCBTaskSelector(TaskSelector, BaseModule):
    """
    UCB (Upper Confidence Bound) 任务选择器

    数学：
    UCB = Score + c * sqrt(ln(N) / n_i)

    其中：
    - Score = 任务的平均得分
    - c = 探索参数
    - N = 总选择次数
    - n_i = 任务i的选择次数

    第一性原理：在已知最优和探索未知之间权衡
    """

    def __init__(self, module_id: str = "ucb_selector",
                 exploration_constant: float = 1.414):
        BaseModule.__init__(self, module_id)
        self.c = exploration_constant
        self._selection_counts: Dict[str, int] = {}
        self._total_selections = 0
        self._score_sums: Dict[str, float] = {}

    def select(self, candidates: List[TaskCandidate],
               exploration_rate: float = 0.1) -> TaskCandidate:
        """
        使用UCB选择最优任务

        如果只有一个候选，直接返回
        """
        if not candidates:
            return TaskCandidate(action="noop")

        if len(candidates) == 1:
            return candidates[0]

        # 计算每个候选的UCB值
        ucb_values = []
        for candidate in candidates:
            task_id = candidate.task_id

            # 平均得分
            if task_id in self._selection_counts and self._selection_counts[task_id] > 0:
                avg_score = self._score_sums.get(task_id, 0) / self._selection_counts[task_id]
            else:
                avg_score = candidate.score() if hasattr(candidate, 'score') else 0.5

            # 探索项
            if task_id in self._selection_counts and self._selection_counts[task_id] > 0:
                exploration = self.c * np.sqrt(
                    np.log(self._total_selections + 1) / self._selection_counts[task_id]
                )
            else:
                # 从未选择的任务给予高探索值
                exploration = float('inf') if self._total_selections > 0 else 0

            ucb_value = avg_score + exploration_rate * exploration
            ucb_values.append((ucb_value, candidate))

        # 选择UCB值最高的
        ucb_values.sort(key=lambda x: x[0], reverse=True)
        selected = ucb_values[0][1]

        # 更新统计
        self._total_selections += 1
        self._selection_counts[selected.task_id] = self._selection_counts.get(selected.task_id, 0) + 1

        return selected

    def update_score(self, task_id: str, score: float) -> None:
        """更新任务的得分统计"""
        if task_id not in self._score_sums:
            self._score_sums[task_id] = 0
        self._score_sums[task_id] += score

    def initialize(self, config: Dict[str, Any]) -> None:
        self.c = config.get("exploration_constant", self.c)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.TASK_CANDIDATE:
            candidates_data = message.payload.get("evaluated_candidates", [])
            exploration_rate = message.payload.get("exploration_rate", 0.1)

            candidates = [
                TaskCandidate(
                    task_id=c.get("task_id", ""),
                    action=c.get("action", ""),
                    params=c.get("params", {}),
                )
                for c in candidates_data
            ]

            selected = self.select(candidates, exploration_rate)
            return AgentMessage(
                msg_type=MessageType.TASK_SELECTED,
                source=self.module_id,
                payload={
                    "selected_task": {
                        "task_id": selected.task_id,
                        "action": selected.action,
                        "params": selected.params,
                    },
                    "exploration_rate": exploration_rate,
                }
            )
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        base.update({
            "total_selections": self._total_selections,
            "unique_tasks": len(self._selection_counts),
            "exploration_constant": self.c,
        })
        return base
