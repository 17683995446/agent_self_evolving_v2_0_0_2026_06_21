"""
阶段91-95: 接口统一与协调
阶段99: 门面模式重构（消除迪米特法则违反）

第一性原理:
1. 统一接口降低复杂度：用户只需与一个接口交互
2. 协调避免冲突：多个引擎同时运行需要仲裁
3. 声明式优于命令式：告诉系统目标，而非步骤
4. 迪米特法则：只与直接朋友通信，不深入访问子引擎内部

设计原则:
- SystemCoordinator: 系统协调器（门面）
- 统一所有引擎的接口
- 提供声明式目标设置
- 自动协调各引擎冲突
- 通过门面方法访问子引擎能力（不直接访问 engine.sub_engine.method）
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
    from .llm_service import LLMService, create_llm_service
except ImportError:
    from unified_first_principles_engine import UnifiedFirstPrinciplesEngine, create_unified_engine
    from predictive_coding_engine import PrecisionWeight
    from drive_first_principles import DriveType
    from evolution_first_principles import GoalType
    from safety_first_principles import BoundaryType
    from efficiency_first_principles import ResourceType
    from consciousness_first_principles import ContentType, WorkspaceContent
    from free_will_first_principles import ChoiceSet
    from llm_service import LLMService, create_llm_service


class SystemCoordinator:
    """
    系统协调器（门面模式）

    统一接口，协调所有引擎，提供声明式交互。
    通过门面方法访问子引擎能力，不直接暴露 engine.sub_engine.method。
    """

    def __init__(self, coordinator_id: str = "coordinator", llm_service: Optional[LLMService] = None):
        self.coordinator_id = coordinator_id
        self._engine = create_unified_engine("unified")
        self._llm = llm_service
        self._lock = threading.RLock()
        self._running = False
        self._cycle_count = 0
        self._goals: Dict[str, Any] = {}
        self._observers: List[Callable[[Dict[str, Any]], None]] = []

    # ============================================================
    # 门面方法：封装对子引擎的访问（消除迪米特法则违反）
    # ============================================================

    def _update_evolution_progress(self, goal_type: str, level: float) -> None:
        """门面：更新进化目标进度"""
        goal_map = {"safe": GoalType.SAFE, "gain": GoalType.GAIN, "eff": GoalType.EFF}
        gt = goal_map.get(goal_type)
        if gt is not None:
            self._engine.evolution.update_progress(gt, level)

    def _record_resource_usage(self, cycle_id: str, resources: Dict[str, float], output_value: float = 0.0) -> None:
        """门面：记录能效使用"""
        self._engine.decision_coordinator.record_resource_usage(cycle_id, resources, output_value)

    def _get_recommended_action(self) -> Any:
        """门面：获取元认知推荐动作"""
        return self._engine.metacognition.get_recommended_action()

    def _get_dominant_emotion(self) -> Optional[str]:
        """门面：获取主导情感"""
        return self._engine.emotion.get_stats().get("dominant_emotion")

    def _get_conscious_content_ids(self) -> List[str]:
        """门面：获取意识内容ID列表"""
        return [c.content_id for c in self._engine.consciousness.get_conscious_contents()]

    # ============================================================
    # 声明式接口
    # ============================================================

    def set_goal(self, goal_type: str, target_level: float) -> None:
        """设置目标（声明式）"""
        with self._lock:
            self._goals[goal_type] = target_level
            self._update_evolution_progress(goal_type, target_level)

    def observe(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        观察环境状态

        第一性原理：感知是预测的反过程
        支持自然语言输入（通过LLM解析）
        """
        with self._lock:
            # 如果输入是自然语言文本，用LLM解析
            if self._llm and isinstance(state.get("text"), str):
                parsed = self._llm.parse_observation(state["text"])
                state = {**state, "parsed": parsed}

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
            context = context or {}
            # 评估驱力
            gaps = self._engine.evaluate_drives()

            # 做出决策
            choices = ChoiceSet(
                choice_id=f"act_{self._cycle_count}",
                options=[action, "wait", "alternative"],
                context=context,
            )
            decision_result = self._engine.make_consolidated_decision(choices)

            # 记录能效（通过门面方法）
            if "resources_used" in context:
                self._record_resource_usage(
                    f"act_{self._cycle_count}",
                    context["resources_used"],
                    context.get("output_value", 0.0),
                )

            return {
                "action_taken": decision_result["decision"].chosen_action,
                "decision": decision_result,
                "gaps": gaps,
            }

    def reflect(self) -> Dict[str, Any]:
        """
        反思当前状态

        第一性原理：元认知是优化的前提
        支持LLM生成自然语言反思报告
        """
        with self._lock:
            stats = self._engine.get_full_stats()
            result = {
                "cycle_count": self._cycle_count,
                "goals": self._goals,
                "engine_stats": stats,
                "recommended_action": self._get_recommended_action(),
                "dominant_emotion": self._get_dominant_emotion(),
                "consciousness_contents": self._get_conscious_content_ids(),
            }

            # 用LLM生成通俗易懂的反思报告
            if self._llm:
                try:
                    reflection_text = self._llm.generate_reflection(stats)
                    result["reflection_text"] = reflection_text
                except Exception:
                    pass

            return result

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
            self._cycle_count += 1
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

def create_coordinator(coordinator_id: str = "coordinator", llm_service: Optional[LLMService] = None) -> SystemCoordinator:
    """创建系统协调器"""
    return SystemCoordinator(coordinator_id=coordinator_id, llm_service=llm_service)
