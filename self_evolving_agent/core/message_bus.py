"""
自驱永续进化Agent系统 — 消息总线实现
阶段2：消息总线标准化

第一性原理：模块间不直接连接，通过中介传递信息
类比：大脑神经元通过突触传递信号，不直接连接
"""

import threading
import queue
from typing import Dict, List, Callable, Optional
from collections import defaultdict
import heapq
import time

from .interfaces import (
    MessageBus, AgentMessage, MessageType, MessagePriority
)


class PriorityMessageQueue:
    """
    优先级消息队列

    第一性原理：重要信息必须优先处理
    使用堆实现O(log n)的优先级排序
    """

    def __init__(self):
        self._queue: List[tuple] = []  # (priority, timestamp, message)
        self._counter = 0
        self._lock = threading.Lock()

    def put(self, message: AgentMessage) -> None:
        """放入消息，按优先级排序"""
        with self._lock:
            # 优先级数值越小越优先
            priority = message.priority.value
            self._counter += 1
            heapq.heappush(self._queue, (priority, self._counter, message))

    def get(self, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """取出最高优先级的消息"""
        with self._lock:
            if not self._queue:
                return None
            return heapq.heappop(self._queue)[2]

    def empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0

    def size(self) -> int:
        with self._lock:
            return len(self._queue)


class LocalMessageBus(MessageBus):
    """
    本地消息总线实现

    支持：
    - 发布/订阅模式
    - 消息优先级
    - 同步/异步投递
    - 消息路由
    """

    def __init__(self, async_mode: bool = True, max_queue_size: int = 10000):
        super().__init__()
        self._subscribers: Dict[MessageType, Dict[str, Callable]] = defaultdict(dict)
        self._global_subscribers: Dict[str, Callable] = {}
        self._async_mode = async_mode
        self._message_queue = PriorityMessageQueue()
        self._running = False
        self._dispatcher_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._message_count = 0
        self._dropped_count = 0
        self._max_queue_size = max_queue_size

    def start(self) -> None:
        """启动消息总线"""
        self._running = True
        if self._async_mode:
            self._dispatcher_thread = threading.Thread(
                target=self._dispatch_loop,
                name="MessageBusDispatcher",
                daemon=True
            )
            self._dispatcher_thread.start()

    def stop(self) -> None:
        """停止消息总线"""
        self._running = False
        if self._dispatcher_thread and self._dispatcher_thread.is_alive():
            self._dispatcher_thread.join(timeout=2.0)

    def publish(self, message: AgentMessage) -> None:
        """
        发布消息

        第一性原理：发送者只负责发送，不关心谁接收
        """
        if not message.validate():
            raise ValueError(f"Invalid message: {message.msg_id}")

        if self._async_mode:
            # 异步模式：放入队列
            if self._message_queue.size() >= self._max_queue_size:
                self._dropped_count += 1
                return
            self._message_queue.put(message)
            self._message_count += 1
        else:
            # 同步模式：直接投递
            self._deliver(message)

    def subscribe(self, module_id: str, msg_types: List[MessageType],
                  handler: Callable[[AgentMessage], None]) -> None:
        """
        订阅特定类型的消息

        Args:
            module_id: 订阅者模块ID
            msg_types: 感兴趣的消息类型列表
            handler: 消息处理函数
        """
        with self._lock:
            for msg_type in msg_types:
                self._subscribers[msg_type][module_id] = handler

    def subscribe_all(self, module_id: str,
                      handler: Callable[[AgentMessage], None]) -> None:
        """订阅所有消息类型"""
        with self._lock:
            self._global_subscribers[module_id] = handler

    def unsubscribe(self, module_id: str, msg_types: List[MessageType]) -> None:
        """取消订阅"""
        with self._lock:
            for msg_type in msg_types:
                if module_id in self._subscribers[msg_type]:
                    del self._subscribers[msg_type][module_id]

    def unsubscribe_all(self, module_id: str) -> None:
        """取消所有订阅"""
        with self._lock:
            for msg_type in self._subscribers:
                if module_id in self._subscribers[msg_type]:
                    del self._subscribers[msg_type][module_id]
            if module_id in self._global_subscribers:
                del self._global_subscribers[module_id]

    def route(self, message: AgentMessage) -> List[str]:
        """
        确定消息的接收者列表

        第一性原理：消息路由是独立决策，与消息内容无关
        """
        recipients = []

        with self._lock:
            # 特定类型订阅者
            if message.msg_type in self._subscribers:
                for module_id in self._subscribers[message.msg_type]:
                    # 如果消息有指定目标，只发给目标
                    if message.target is None or message.target == module_id:
                        recipients.append(module_id)

            # 全局订阅者
            for module_id in self._global_subscribers:
                if message.target is None or message.target == module_id:
                    recipients.append(module_id)

        return recipients

    def _dispatch_loop(self) -> None:
        """异步分发循环"""
        while self._running:
            message = self._message_queue.get(timeout=0.1)
            if message is not None:
                self._deliver(message)
            else:
                time.sleep(0.001)

    def _deliver(self, message: AgentMessage) -> None:
        """投递消息到所有订阅者"""
        recipients = self.route(message)

        with self._lock:
            for module_id in recipients:
                # 先检查特定类型处理器
                handler = None
                if message.msg_type in self._subscribers:
                    handler = self._subscribers[message.msg_type].get(module_id)

                # 再检查全局处理器
                if handler is None:
                    handler = self._global_subscribers.get(module_id)

                if handler:
                    try:
                        handler(message)
                    except Exception as e:
                        # 消息处理异常不应影响其他接收者
                        print(f"Error delivering message to {module_id}: {e}")

    def get_stats(self) -> Dict:
        """获取消息总线统计信息"""
        return {
            "total_messages": self._message_count,
            "dropped_messages": self._dropped_count,
            "queue_size": self._message_queue.size(),
            "subscriber_count": sum(
                len(subs) for subs in self._subscribers.values()
            ),
            "global_subscriber_count": len(self._global_subscribers),
            "running": self._running,
            "async_mode": self._async_mode,
        }
