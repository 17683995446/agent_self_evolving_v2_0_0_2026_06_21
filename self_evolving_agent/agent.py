"""
自驱永续进化Agent系统 — 主Agent

第一性原理：Agent是模块的协调者，不是控制者
- 通过消息总线连接所有模块
- 不直接调用模块方法，只发送消息
- 每个模块独立运行，通过消息通信
"""

import time
import threading
from typing import Dict, Any, Optional

from .core.interfaces import BaseModule, AgentMessage, MessageType, MessagePriority
from .core.message_bus import LocalMessageBus
from .core.config_manager import ConfigurationManager

from .modules.predictor import MultiLayerPredictor, LinearPredictor, MovingAveragePredictor
from .modules.drive_engine import UnifiedDriveEngine
from .modules.memory import MemoryCoordinator
from .modules.optimizer import OptimizationStrategy
from .modules.evaluator import UnifiedEvaluator
from .modules.task_system import TaskSystem


class SelfEvolvingAgent:
    """
    自驱永续进化Agent

    核心循环：
    1. 感知环境 -> 状态更新消息
    2. 预测未来 -> 预测消息
    3. 计算驱力 -> 驱力消息
    4. 生成任务 -> 任务消息
    5. 执行任务 -> 动作消息
    6. 评估结果 -> 误差消息
    7. 优化模型 -> 学习消息
    """

    def __init__(self, agent_id: str = "self_evolving_agent"):
        self.agent_id = agent_id
        self._message_bus = LocalMessageBus(async_mode=True)
        self._config = ConfigurationManager()

        # 核心模块
        self._predictor: Optional[MultiLayerPredictor] = None
        self._drive_engine: Optional[UnifiedDriveEngine] = None
        self._memory: Optional[MemoryCoordinator] = None
        self._optimizer: Optional[OptimizationStrategy] = None
        self._evaluator: Optional[UnifiedEvaluator] = None
        self._task_system: Optional[TaskSystem] = None

        # 运行状态
        self._running = False
        self._main_loop_thread: Optional[threading.Thread] = None
        self._cycle_count = 0
        self._cycle_interval = 1.0  # 秒

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        初始化Agent

        创建并配置所有模块
        """
        self._config.update(config)

        # 创建消息总线
        self._message_bus.start()

        # 创建预测器
        self._predictor = MultiLayerPredictor("predictor")
        self._predictor.add_layer("low", LinearPredictor("predictor_low", window_size=5))
        self._predictor.add_layer("mid", MovingAveragePredictor("predictor_mid", window_size=20))
        self._predictor.add_layer("high", MovingAveragePredictor("predictor_high", window_size=100))

        # 创建驱力引擎
        self._drive_engine = UnifiedDriveEngine("drive_engine")

        # 创建记忆系统
        self._memory = MemoryCoordinator("memory")

        # 创建优化器
        self._optimizer = OptimizationStrategy("optimizer")

        # 创建评估器
        self._evaluator = UnifiedEvaluator("evaluator")

        # 创建任务系统
        self._task_system = TaskSystem("task_system")

        # 绑定消息总线
        modules = [
            self._predictor,
            self._drive_engine,
            self._memory,
            self._optimizer,
            self._evaluator,
            self._task_system,
        ]

        for module in modules:
            if module:
                module.attach_message_bus(self._message_bus)
                module.initialize(config.get(module.module_id, {}))

        # 订阅消息
        self._setup_subscriptions()

    def _setup_subscriptions(self) -> None:
        """设置消息订阅"""
        # 预测器订阅状态更新
        self._message_bus.subscribe(
            "predictor",
            [MessageType.STATE_UPDATE],
            lambda msg: self._handle_predictor_message(msg)
        )

        # 驱力引擎订阅状态更新
        self._message_bus.subscribe(
            "drive_engine",
            [MessageType.STATE_UPDATE],
            lambda msg: self._handle_drive_message(msg)
        )

        # 任务系统订阅驱力信号
        self._message_bus.subscribe(
            "task_system",
            [MessageType.DRIVE_SIGNAL],
            lambda msg: self._handle_task_message(msg)
        )

        # 评估器订阅预测结果和状态更新
        self._message_bus.subscribe(
            "evaluator",
            [MessageType.PREDICTION, MessageType.STATE_UPDATE],
            lambda msg: self._handle_evaluator_message(msg)
        )

        # 优化器订阅误差信号
        self._message_bus.subscribe(
            "optimizer",
            [MessageType.ERROR_SIGNAL],
            lambda msg: self._handle_optimizer_message(msg)
        )

        # 记忆系统订阅所有消息
        self._message_bus.subscribe_all(
            "memory",
            lambda msg: self._handle_memory_message(msg)
        )

    def _handle_predictor_message(self, message: AgentMessage) -> None:
        """处理预测器消息"""
        response = self._predictor.handle_message(message)
        if response:
            self._message_bus.publish(response)

    def _handle_drive_message(self, message: AgentMessage) -> None:
        """处理驱力消息"""
        response = self._drive_engine.handle_message(message)
        if response:
            self._message_bus.publish(response)

    def _handle_task_message(self, message: AgentMessage) -> None:
        """处理任务消息"""
        response = self._task_system.handle_message(message)
        if response:
            self._message_bus.publish(response)
            # 记录选中的任务
            self._handle_task_selected(response)

    def _handle_evaluator_message(self, message: AgentMessage) -> None:
        """处理评估器消息"""
        response = self._evaluator.handle_message(message)
        if response:
            self._message_bus.publish(response)

    def _handle_optimizer_message(self, message: AgentMessage) -> None:
        """处理优化器消息"""
        response = self._optimizer.handle_message(message)
        if response:
            self._message_bus.publish(response)

    def _handle_memory_message(self, message: AgentMessage) -> None:
        """处理记忆消息"""
        # 存储所有消息到记忆
        self._memory.store(
            key=f"msg_{message.msg_id}",
            data=message.to_dict(),
            metadata={"type": message.msg_type.name, "source": message.source},
        )

    def _handle_task_selected(self, message: AgentMessage) -> None:
        """处理任务选择"""
        task = message.payload.get("selected_task", {})
        print(f"[Agent] Selected task: {task.get('action')} ({task.get('task_id')})")

    def start(self) -> None:
        """启动Agent"""
        self._running = True

        # 启动所有模块
        modules = [
            self._predictor,
            self._drive_engine,
            self._memory,
            self._optimizer,
            self._evaluator,
            self._task_system,
        ]
        for module in modules:
            if module:
                module.start()

        # 启动主循环
        self._main_loop_thread = threading.Thread(
            target=self._main_loop,
            name="AgentMainLoop",
            daemon=True
        )
        self._main_loop_thread.start()

        print(f"[Agent] {self.agent_id} started")

    def stop(self) -> None:
        """停止Agent"""
        self._running = False

        if self._main_loop_thread and self._main_loop_thread.is_alive():
            self._main_loop_thread.join(timeout=2.0)

        # 停止所有模块
        modules = [
            self._predictor,
            self._drive_engine,
            self._memory,
            self._optimizer,
            self._evaluator,
            self._task_system,
        ]
        for module in modules:
            if module:
                module.stop()

        # 停止消息总线
        self._message_bus.stop()

        print(f"[Agent] {self.agent_id} stopped")

    def _main_loop(self) -> None:
        """主循环"""
        while self._running:
            self._cycle_count += 1

            # 模拟环境感知
            state = self._sense_environment()

            # 发送状态更新消息
            state_message = AgentMessage(
                msg_type=MessageType.STATE_UPDATE,
                source="environment",
                payload={"state": state, "cycle": self._cycle_count},
                priority=MessagePriority.NORMAL,
            )
            self._message_bus.publish(state_message)

            time.sleep(self._cycle_interval)

    def _sense_environment(self) -> Dict[str, Any]:
        """
        感知环境

        简化实现：生成模拟状态
        """
        import random
        import math

        # 模拟周期性变化 + 噪声
        t = self._cycle_count * 0.1
        base_value = math.sin(t) * 0.5 + 0.5

        return {
            "value": base_value + random.gauss(0, 0.05),
            "cpu_usage": random.uniform(0.2, 0.6),
            "memory_usage": random.uniform(0.3, 0.7),
            "task_completion_rate": random.uniform(0.7, 0.95),
            "uncertainty": random.uniform(0.1, 0.4),
            "cycle": self._cycle_count,
        }

    def get_state(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            "agent_id": self.agent_id,
            "running": self._running,
            "cycle_count": self._cycle_count,
            "message_bus": self._message_bus.get_stats(),
            "modules": {
                "predictor": self._predictor.get_model_state() if self._predictor else None,
                "drive_engine": self._drive_engine.get_state() if self._drive_engine else None,
                "memory": self._memory.get_state() if self._memory else None,
                "optimizer": self._optimizer.get_state() if self._optimizer else None,
                "evaluator": self._evaluator.get_state() if self._evaluator else None,
                "task_system": self._task_system.get_state() if self._task_system else None,
            },
        }

    def inject_state(self, state: Dict[str, Any]) -> None:
        """手动注入状态（用于测试）"""
        message = AgentMessage(
            msg_type=MessageType.STATE_UPDATE,
            source="external",
            payload={"state": state},
            priority=MessagePriority.HIGH,
        )
        self._message_bus.publish(message)


# ============================================================================
# 快速启动函数
# ============================================================================

def create_default_agent() -> SelfEvolvingAgent:
    """创建默认配置的Agent"""
    agent = SelfEvolvingAgent()

    config = {
        "predictor": {
            "layer_weights": {"low": 0.5, "mid": 0.3, "high": 0.2},
        },
        "drive_engine": {
            "safe": {"target_safety": 0.95, "anomaly_threshold": 2.0},
            "gain": {"target_uncertainty": 0.1},
            "eff": {"target_efficiency": 0.8},
        },
        "memory": {
            "stm": {"capacity": 7},
            "ltm": {"persist_path": None},
        },
        "optimizer": {
            "micro": {"learning_rate": 0.01, "max_iterations": 100},
            "structural": {"complexity_penalty": 0.1},
        },
        "evaluator": {
            "error": {},
            "feedback": {"error_threshold": 0.3},
        },
        "task_system": {
            "exploration_rate": 0.1,
            "factory": {},
            "evaluator": {},
            "selector": {},
        },
    }

    agent.initialize(config)
    return agent
