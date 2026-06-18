"""
自驱永续进化Agent系统 — 主Agent（架构B统一入口）

阶段96: 统一两套架构
第一性原理：单一职责 + 依赖抽象
- SelfEvolvingAgent 现在是 SystemCoordinator 的薄包装层
- 不再直接依赖 modules/ 中的具体实现
- 通过 SystemCoordinator 统一访问 15 个第一性原理引擎
- 保留消息总线用于事件通知（向后兼容）
"""

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .core.interfaces import AgentMessage, MessagePriority, MessageType
from .core.message_bus import LocalMessageBus
from .core.config_manager import ConfigurationManager
from .core.system_coordinator import SystemCoordinator, create_coordinator
from .core.llm_service import LLMService, create_llm_service


class SelfEvolvingAgent:
    """
    自驱永续进化Agent（架构B统一入口）

    通过 SystemCoordinator 协调 15 个第一性原理引擎：
    预测编码、驱力、学习、探索、记忆、进化、安全、能效、
    社交、创造、因果、元认知、情感、意识、自由意志

    核心循环（声明式）：
    1. observe(state)  -> 感知 + 预测 + 误差
    2. act(action)     -> 决策 + 行动
    3. reflect()       -> 元认知 + 反思
    4. run_cycle()     -> 完整整合周期
    """

    def __init__(
        self,
        agent_id: str = "self_evolving_agent",
        llm_service: Optional[LLMService] = None,
        use_message_bus: bool = True,
    ):
        self.agent_id = agent_id

        # 架构B：统一协调器（持有 UnifiedFirstPrinciplesEngine）
        self._coordinator = create_coordinator(
            coordinator_id=agent_id,
            llm_service=llm_service,
        )

        # 消息总线（用于事件通知，向后兼容架构A的订阅者）
        self._message_bus = LocalMessageBus(async_mode=True) if use_message_bus else None
        self._config = ConfigurationManager()

        # 运行状态
        self._running = False
        self._main_loop_thread: Optional[threading.Thread] = None
        self._cycle_count = 0
        self._cycle_interval = 1.0  # 秒
        self._observers: List[Callable[[Dict[str, Any]], None]] = []

    # ============================================================
    # 属性访问（向后兼容）
    # ============================================================

    @property
    def coordinator(self) -> SystemCoordinator:
        """暴露底层协调器（供高级用户直接访问）"""
        return self._coordinator

    @property
    def engine(self):
        """暴露底层统一引擎（向后兼容架构A的属性访问）"""
        return self._coordinator._engine

    @property
    def message_bus(self) -> Optional[LocalMessageBus]:
        return self._message_bus

    # ============================================================
    # 初始化
    # ============================================================

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        初始化Agent

        config 字段（全部可选）：
        - cycle_interval: 主循环间隔（秒）
        - goals: {"safe": 0.95, "gain": 0.8, "eff": 0.85}
        - llm: LLM 配置（api_key, model, base_url）
        """
        self._config.update(config)
        self._cycle_interval = config.get("cycle_interval", self._cycle_interval)

        # 启动消息总线（如果启用）
        if self._message_bus:
            self._message_bus.start()

        # 设置声明式目标
        for goal_type, target_level in config.get("goals", {}).items():
            self._coordinator.set_goal(goal_type, float(target_level))

    def _setup_subscriptions(self) -> None:
        """设置消息订阅（向后兼容接口）"""
        if not self._message_bus:
            return
        # 记忆系统订阅所有消息（保留架构A的事件流）
        self._message_bus.subscribe_all(
            "memory",
            lambda msg: self._handle_memory_message(msg),
        )

    def _handle_memory_message(self, message: AgentMessage) -> None:
        """处理记忆消息（向后兼容）"""
        # 通过协调器的引擎存储到记忆系统
        try:
            self._coordinator._engine.memory.store(
                key=f"msg_{message.msg_id}",
                data=message.to_dict(),
                context={"type": message.msg_type.name, "source": message.source},
            )
        except Exception:
            pass

    # ============================================================
    # 声明式接口（委托给 SystemCoordinator）
    # ============================================================

    def set_goal(self, goal_type: str, target_level: float) -> None:
        """设置目标（声明式）"""
        self._coordinator.set_goal(goal_type, target_level)

    def observe(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """观察环境状态"""
        result = self._coordinator.observe(state)
        self._publish_state_update(state)
        return result

    def act(self, action: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行行动"""
        return self._coordinator.act(action, context)

    def reflect(self) -> Dict[str, Any]:
        """反思当前状态"""
        return self._coordinator.reflect()

    def run_cycle(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行完整协调周期"""
        return self._coordinator.run_cycle(context or {})

    def inject_state(self, state: Dict[str, Any]) -> None:
        """手动注入状态（用于测试）"""
        self.observe(state)

    def register_observer(self, observer: Callable[[Dict[str, Any]], None]) -> None:
        """注册状态观察者"""
        self._observers.append(observer)
        self._coordinator.register_observer(observer)

    # ============================================================
    # 生命周期
    # ============================================================

    def start(self) -> None:
        """启动Agent"""
        self._running = True
        self._coordinator.start()
        self._setup_subscriptions()

        self._main_loop_thread = threading.Thread(
            target=self._main_loop,
            name="AgentMainLoop",
            daemon=True,
        )
        self._main_loop_thread.start()

    def stop(self) -> None:
        """停止Agent"""
        self._running = False
        if self._main_loop_thread and self._main_loop_thread.is_alive():
            self._main_loop_thread.join(timeout=2.0)
        self._coordinator.stop()
        if self._message_bus:
            self._message_bus.stop()

    def _main_loop(self) -> None:
        """主循环：周期性感知环境"""
        while self._running:
            self._cycle_count += 1
            state = self._sense_environment()
            try:
                self.observe(state)
            except Exception:
                pass
            time.sleep(self._cycle_interval)

    def _sense_environment(self) -> Dict[str, Any]:
        """感知环境（模拟）"""
        import math
        import random

        t = self._cycle_count * 0.1
        base_value = math.sin(t) * 0.5 + 0.5
        return {
            "module_id": "env",
            "predicted": {"value": base_value},
            "actual": {"value": base_value + random.gauss(0, 0.05)},
            "cycle": self._cycle_count,
        }

    def _publish_state_update(self, state: Dict[str, Any]) -> None:
        """发布状态更新消息（向后兼容）"""
        if not self._message_bus:
            return
        try:
            message = AgentMessage(
                msg_type=MessageType.STATE_UPDATE,
                source="environment",
                payload={"state": state, "cycle": self._cycle_count},
                priority=MessagePriority.NORMAL,
            )
            self._message_bus.publish(message)
        except Exception:
            pass

    # ============================================================
    # 状态查询
    # ============================================================

    def get_state(self) -> Dict[str, Any]:
        """获取Agent状态（统一架构A/B的字段）"""
        engine = self._coordinator._engine
        # 优先使用协调器的周期计数（observe/act/run_cycle 都会递增）
        cycle_count = max(self._cycle_count, self._coordinator._cycle_count)
        return {
            "agent_id": self.agent_id,
            "running": self._running,
            "cycle_count": cycle_count,
            "coordinator": self._coordinator.get_status(),
            "message_bus": self._message_bus.get_stats() if self._message_bus else None,
            # 向后兼容字段（架构A的调用者期望）
            "modules": {
                "predictor": engine.predictive_coding.get_stats() if engine else None,
                "drive_engine": engine.drive.get_stats() if engine else None,
                "memory": engine.memory.get_stats() if engine else None,
                "optimizer": None,  # 已合并到 efficiency + learning
                "evaluator": None,  # 已合并到 predictive_coding
                "task_system": None,  # 已合并到 free_will
            },
        }


# ============================================================
# 快速启动函数
# ============================================================

def create_default_agent(
    llm_api_key: Optional[str] = None,
    llm_model: str = "Qwen/Qwen2.5-7B-Instruct",
) -> SelfEvolvingAgent:
    """
    创建默认配置的Agent

    Args:
        llm_api_key: 硅基流动 API Key（可选，启用LLM能力）
        llm_model: LLM 模型名（默认 Qwen2.5-7B-Instruct，免费）
    """
    llm_service = None
    if llm_api_key:
        llm_service = create_llm_service(
            api_key=llm_api_key,
            model=llm_model,
        )

    agent = SelfEvolvingAgent(llm_service=llm_service)

    config = {
        "cycle_interval": 1.0,
        "goals": {
            "safe": 0.95,
            "gain": 0.8,
            "eff": 0.85,
        },
    }
    agent.initialize(config)
    return agent


def create_default_agent_with_llm(api_key: str) -> SelfEvolvingAgent:
    """创建带LLM能力的默认Agent（便捷函数）"""
    return create_default_agent(llm_api_key=api_key)
