"""
阶段91-95: 接口统一与协调

第一性原理:
1. 统一接口降低复杂度：用户只需与一个接口交互
2. 协调避免冲突：多个引擎同时运行需要仲裁
3. 声明式优于命令式：告诉系统目标，而非步骤

设计原则:
- SystemCoordinator: 系统协调器
- 统一所有引擎的接口
- 提供声明式目标设置
- 自动协调各引擎冲突
"""

import threading
import time
from typing import Any, Callable, Dict, List, Optional

# 使用绝对导入回退
try:
    from .unified_first_principles_engine import UnifiedFirstPrinciplesEngine, create_unified_engine
    from .predictive_coding_engine import PrecisionWeight
    from .drive_first_principles import DriveType
    from .evolution_first_principles import GoalType
    from .safety_first_principles import BoundaryType
    from .efficiency_first_principles import ResourceType
    from .consciousness_first_principles import ContentType, WorkspaceContent
    from .free_will_first_principles import ChoiceSet
except ImportError:
    from unified_first_principles_engine import UnifiedFirstPrinciplesEngine, create_unified_engine
    from predictive_coding_engine import PrecisionWeight
    from drive_first_principles import DriveType
    from evolution_first_principles import GoalType
    from safety_first_principles import BoundaryType
    from efficiency_first_principles import ResourceType
    from consciousness_first_principles import ContentType, WorkspaceContent
    from free_will_first_principles import ChoiceSet


class SystemCoordinator:
    """
    系统协调器

    统一接口，协调所有引擎，提供声明式交互。
    """

    def __init__(self, coordinator_id: str = "coordinator"):
        self.coordinator_id = coordinator_id
        self._engine = create_unified_engine("unified")
        self._lock = threading.RLock()
        self._running = False
        self._cycle_count = 0
        self._goals: Dict[str, Any] = {}
        self._observers: List[Callable[[Dict[str, Any]], None]] = []

    # ============================================================
    # 声明式接口
    # ============================================================

    def set_goal(self, goal_type: str, target_level: float) -> None:
        """设置目标（声明式）"""
        with self._lock:
            self._goals[goal_type] = target_level

            # 映射到进化引擎
            if goal_type == "safe":
                self._engine.evolution.update_progress(GoalType.SAFE, target_level)
            elif goal_type == "gain":
                self._engine.evolution.update_progress(GoalType.GAIN, target_level)
            elif goal_type == "eff":
                self._engine.evolution.update_progress(GoalType.EFF, target_level)

    def observe(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        观察环境状态

        第一性原理：感知是预测的反过程
        """
        with self._lock:
            # 生成预测并比较
            module_id = state.get("module_id", "default")
            current = state.get("predicted", {})
            actual = state.get("actual", {})

            result = self._engine.perceive_and_predict(module_id, current, actual)
            self._cycle_count += 1

            # 通知观察者
            for observer in self._observers:
                try:
                    observer({"type": "perception", "data": result})
                except Exception:
                    pass

            return result

    def act(self, action: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行行动

        第一性原理：行动是减小驱力缺口的方式
        """
        with self._lock:
            # 评估驱力
            gaps = self._engine.evaluate_drives()

            # 做出决策
            choices = ChoiceSet(
                choice_id=f"act_{self._cycle_count}",
                options=[action, "wait", "alternative"],
                context=context or {},
            )
            decision_result = self._engine.make_consolidated_decision(choices)

            # 记录能效
            if context and "resources_used" in context:
                for rtype, amount in context["resources_used"].items():
                    try:
                        rt = ResourceType(rtype)
                        self._engine.efficiency.record_usage(
                            f"act_{self._cycle_count}", rt, amount,
                            context.get("output_value", 0.0),
                        )
                    except ValueError:
                        pass

            return {
                "action_taken": decision_result["decision"].chosen_action,
                "decision": decision_result,
                "gaps": gaps,
            }

    def reflect(self) -> Dict[str, Any]:
        """
        反思当前状态

        第一性原理：元认知是优化的前提
        """
        with self._lock:
            return {
                "cycle_count": self._cycle_count,
                "goals": self._goals,
                "engine_stats": self._engine.get_full_stats(),
                "recommended_action": self._engine.metacognition.get_recommended_action(),
                "dominant_emotion": self._engine.emotion.get_stats().get("dominant_emotion"),
                "consciousness_contents": [
                    c.content_id for c in self._engine.consciousness.get_conscious_contents()
                ],
            }

    # ============================================================
    # 协调接口
    # ============================================================

    def register_observer(self, observer: Callable[[Dict[str, Any]], None]) -> None:
        """注册状态观察者"""
        with self._lock:
            self._observers.append(observer)

    def run_cycle(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行完整协调周期"""
        with self._lock:
            return self._engine.run_integration_cycle(context or {})

    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        with self._lock:
            return {
                "coordinator_id": self.coordinator_id,
                "running": self._running,
                "cycle_count": self._cycle_count,
                "goals_count": len(self._goals),
                "engine_status": "healthy",
            }

    def start(self) -> None:
        """启动协调器"""
        with self._lock:
            self._running = True

    def stop(self) -> None:
        """停止协调器"""
        with self._lock:
            self._running = False


# ============================================================
# 便捷函数
# ============================================================

def create_coordinator(coordinator_id: str = "coordinator") -> SystemCoordinator:
    """创建系统协调器"""
    return SystemCoordinator(coordinator_id=coordinator_id)
