"""
自驱永续进化Agent系统 — 任务系统
阶段4（改进计划）：任务生成器解耦

第一性原理：任务孵化、评估、选择是三个独立过程
- TaskFactory：只生成候选任务
- TaskEvaluator：只评估候选任务
- TaskSelector：只选择最优任务
"""

import random
import numpy as np
from typing import Dict, Any, List, Optional
from collections import deque

from ..core.interfaces import (
    TaskFactory, TaskEvaluator, TaskSelector, TaskCandidate,
    DriveGaps, BaseModule, AgentMessage, MessageType
)


class GapDrivenTaskFactory(TaskFactory, BaseModule):
    """
    缺口驱动任务工厂

    第一性原理：任务来源于驱力缺口
    """

    def __init__(self, module_id: str = "task_factory"):
        BaseModule.__init__(self, module_id)
        self._action_templates = {
            "safe": ["monitor", "alert", "reduce_load", "check_status"],
            "gain": ["explore", "collect_data", "update_model", "increase_resolution"],
            "eff": ["optimize", "compress", "cache", "batch_process"],
        }

    def generate_candidates(self, gaps: DriveGaps,
                           state: Dict[str, Any]) -> List[TaskCandidate]:
        """
        基于驱力缺口生成候选任务

        每个显著的缺口生成对应的候选任务
        """
        candidates = []

        # 安全缺口驱动
        if gaps.safe_gap > 0.2:
            for action in self._action_templates["safe"]:
                candidates.append(TaskCandidate(
                    action=action,
                    params={"drive": "safe", "gap": gaps.safe_gap},
                    expected_benefit=gaps.safe_gap * 0.8,
                    cost=0.2,
                    success_probability=0.9,
                    info_value=0.1,
                ))

        # 收益缺口驱动
        if gaps.gain_gap > 0.2:
            for action in self._action_templates["gain"]:
                candidates.append(TaskCandidate(
                    action=action,
                    params={"drive": "gain", "gap": gaps.gain_gap},
                    expected_benefit=gaps.gain_gap * 0.9,
                    cost=0.3,
                    success_probability=0.7,
                    info_value=0.8,
                ))

        # 能效缺口驱动
        if gaps.eff_gap > 0.2:
            for action in self._action_templates["eff"]:
                candidates.append(TaskCandidate(
                    action=action,
                    params={"drive": "eff", "gap": gaps.eff_gap},
                    expected_benefit=gaps.eff_gap * 0.6,
                    cost=0.1,
                    success_probability=0.85,
                    info_value=0.3,
                ))

        # 如果没有显著缺口，生成一个维持任务
        if not candidates:
            candidates.append(TaskCandidate(
                action="maintain",
                params={"drive": "none"},
                expected_benefit=0.1,
                cost=0.05,
                success_probability=0.99,
                info_value=0.0,
            ))

        return candidates

    def initialize(self, config: Dict[str, Any]) -> None:
        self._action_templates = config.get("action_templates", self._action_templates)
        self._initialized = True

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.DRIVE_SIGNAL:
            gaps_data = message.payload.get("gaps", {})
            gaps = DriveGaps(
                safe_gap=gaps_data.get("safe_gap", 0),
                gain_gap=gaps_data.get("gain_gap", 0),
                eff_gap=gaps_data.get("eff_gap", 0),
            )
            state = message.payload.get("state", {})
            candidates = self.generate_candidates(gaps, state)
            return AgentMessage(
                msg_type=MessageType.TASK_CANDIDATE,
                source=self.module_id,
                payload={
                    "candidates": [
                        {
                            "task_id": c.task_id,
                            "action": c.action,
                            "params": c.params,
                            "expected_benefit": c.expected_benefit,
                            "cost": c.cost,
                            "success_probability": c.success_probability,
                            "info_value": c.info_value,
                        }
                        for c in candidates
                    ]
                }
            )
        return None


class BenefitCostEvaluator(TaskEvaluator, BaseModule):
    """
    收益-成本评估器

    评估候选任务的预期收益和成本
    """

    def __init__(self, module_id: str = "task_evaluator"):
        BaseModule.__init__(self, module_id)
        self._weights = {
            "benefit": 0.4,
            "cost": -0.3,
            "success": 0.2,
            "info": 0.1,
        }

    def evaluate(self, candidate: TaskCandidate,
                 state: Dict[str, Any]) -> TaskCandidate:
        """
        评估候选任务

        基于当前状态调整评估参数
        """
        # 根据系统负载调整成本估计
        load = state.get("cpu_usage", 0.5)
        adjusted_cost = candidate.cost * (1 + load)

        # 根据历史成功率调整成功概率
        historical_success = state.get("historical_success_rate", 0.5)
        adjusted_success = (candidate.success_probability + historical_success) / 2

        # 创建评估后的候选
        evaluated = TaskCandidate(
            task_id=candidate.task_id,
            action=candidate.action,
            params=candidate.params,
            expected_benefit=candidate.expected_benefit,
            cost=adjusted_cost,
            success_probability=adjusted_success,
            info_value=candidate.info_value,
        )

        return evaluated

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
                    expected_benefit=c_data.get("expected_benefit", 0),
                    cost=c_data.get("cost", 0),
                    success_probability=c_data.get("success_probability", 0.5),
                    info_value=c_data.get("info_value", 0),
                )
                evaluated_candidate = self.evaluate(candidate, state)
                evaluated.append({
                    "task_id": evaluated_candidate.task_id,
                    "action": evaluated_candidate.action,
                    "score": evaluated_candidate.score(self._weights),
                    "params": evaluated_candidate.params,
                })

            return AgentMessage(
                msg_type=MessageType.TASK_CANDIDATE,
                source=self.module_id,
                payload={"evaluated_candidates": evaluated},
            )
        return None


class ExplorationExploitationSelector(TaskSelector, BaseModule):
    """
    探索-利用选择器

    第一性原理：在已知最优和探索未知之间权衡
    """

    def __init__(self, module_id: str = "task_selector"):
        BaseModule.__init__(self, module_id)
        self._exploration_history: deque = deque(maxlen=100)
        self._exploitation_history: deque = deque(maxlen=100)

    def select(self, candidates: List[TaskCandidate],
               exploration_rate: float = 0.1) -> TaskCandidate:
        """
        选择最优任务

        策略：
        - 以 exploration_rate 的概率进行探索（随机选择）
        - 以 1 - exploration_rate 的概率进行利用（选择得分最高）
        """
        if not candidates:
            return TaskCandidate(action="noop")

        if len(candidates) == 1:
            return candidates[0]

        # 探索
        if random.random() < exploration_rate:
            selected = random.choice(candidates)
            self._exploration_history.append({
                "task_id": selected.task_id,
                "action": selected.action,
            })
            return selected

        # 利用：选择得分最高的
        scored = [(c.score(), c) for c in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        selected = scored[0][1]

        self._exploitation_history.append({
            "task_id": selected.task_id,
            "action": selected.action,
            "score": scored[0][0],
        })

        return selected

    def initialize(self, config: Dict[str, Any]) -> None:
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
            "exploration_count": len(self._exploration_history),
            "exploitation_count": len(self._exploitation_history),
        })
        return base


class TaskSystem(BaseModule):
    """
    统一任务系统

    协调任务工厂、评估器和选择器
    """

    def __init__(self, module_id: str = "task_system"):
        super().__init__(module_id)
        self._factory = GapDrivenTaskFactory()
        self._evaluator = BenefitCostEvaluator()
        self._selector = ExplorationExploitationSelector()
        self._exploration_rate = 0.1

    def process_gaps(self, gaps: DriveGaps, state: Dict[str, Any]) -> TaskCandidate:
        """
        完整的任务生成流程

        1. 生成候选
        2. 评估候选
        3. 选择最优
        """
        # 生成
        candidates = self._factory.generate_candidates(gaps, state)

        # 评估
        evaluated = [self._evaluator.evaluate(c, state) for c in candidates]

        # 选择
        selected = self._selector.select(evaluated, self._exploration_rate)

        return selected

    def initialize(self, config: Dict[str, Any]) -> None:
        self._exploration_rate = config.get("exploration_rate", self._exploration_rate)
        self._factory.initialize(config.get("factory", {}))
        self._evaluator.initialize(config.get("evaluator", {}))
        self._selector.initialize(config.get("selector", {}))
        self._initialized = True

    def start(self) -> None:
        self._running = True
        self._factory.start()
        self._evaluator.start()
        self._selector.start()

    def stop(self) -> None:
        self._running = False
        self._factory.stop()
        self._evaluator.stop()
        self._selector.stop()

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.msg_type == MessageType.DRIVE_SIGNAL:
            gaps_data = message.payload.get("gaps", {})
            gaps = DriveGaps(
                safe_gap=gaps_data.get("safe_gap", 0),
                gain_gap=gaps_data.get("gain_gap", 0),
                eff_gap=gaps_data.get("eff_gap", 0),
            )
            state = message.payload.get("state", {})
            selected = self.process_gaps(gaps, state)
            return AgentMessage(
                msg_type=MessageType.TASK_SELECTED,
                source=self.module_id,
                payload={
                    "selected_task": {
                        "task_id": selected.task_id,
                        "action": selected.action,
                        "params": selected.params,
                    }
                }
            )
        return None

    def get_state(self) -> Dict[str, Any]:
        base = super().get_state()
        base.update({
            "factory": self._factory.get_state(),
            "evaluator": self._evaluator.get_state(),
            "selector": self._selector.get_state(),
            "exploration_rate": self._exploration_rate,
        })
        return base
