"""
阶段26: 事件订阅发布规范化

第一性原理:
1. 模块间通信是系统的神经系统，必须有明确的信号类型、路由规则和投递保证
2. 没有规范化的事件机制，模块将形成隐式耦合（直接调用、共享状态）
3. 事件是信息的载体，必须包含：来源、类型、时间、优先级、有效载荷

设计原则:
- 事件类型显式定义，禁止裸字符串
- 支持同步/异步投递
- 支持优先级和过滤
- 支持事件链和追踪
- 发布者和订阅者完全解耦
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional, Set, Tuple
from enum import Enum, auto
from datetime import datetime
import threading
import queue
import uuid
from abc import ABC, abstractmethod


class EventPriority(Enum):
    """事件优先级"""
    CRITICAL = 0    # 关键：立即处理，阻塞其他事件
    HIGH = 1        # 高：优先处理
    NORMAL = 2      # 正常：默认优先级
    LOW = 3         # 低：空闲时处理
    BACKGROUND = 4  # 后台：不紧急


class DeliveryMode(Enum):
    """投递模式"""
    SYNC = "sync"       # 同步：发布者等待所有订阅者处理完成
    ASYNC = "async"     # 异步：发布者不等待，事件入队列
    BROADCAST = "broadcast"  # 广播：异步投递，不保证顺序


@dataclass(frozen=True)
class EventType:
    """
    标准化事件类型
    
    第一性原理：事件类型是接口契约的一部分，必须不可变、可比较
    格式: domain.action (如 state.updated, task.completed)
    """
    domain: str
    action: str
    version: str = "1.0"
    
    def __post_init__(self):
        if not self.domain or not self.action:
            raise ValueError("Domain and action must not be empty")
    
    @property
    def full_name(self) -> str:
        return f"{self.domain}.{self.action}"
    
    def __str__(self) -> str:
        return self.full_name
    
    def matches(self, pattern: str) -> bool:
        """
        匹配通配符模式
        
        支持:
        - exact.match (精确匹配)
        - domain.* (匹配domain下所有action)
        - *.action (匹配所有domain下的action)
        - *.* (匹配所有)
        """
        if pattern == "*.*" or pattern == "*":
            return True
        
        parts = pattern.split(".")
        if len(parts) != 2:
            return self.full_name == pattern
        
        domain_pat, action_pat = parts
        domain_match = domain_pat == "*" or domain_pat == self.domain
        action_match = action_pat == "*" or action_pat == self.action
        return domain_match and action_match


# 预定义标准事件类型
class StandardEvents:
    """标准事件类型常量"""
    STATE_UPDATED = EventType("state", "updated")
    PREDICTION_MADE = EventType("prediction", "made")
    DRIVE_GAPS_COMPUTED = EventType("drive", "gaps_computed")
    TASK_CREATED = EventType("task", "created")
    TASK_COMPLETED = EventType("task", "completed")
    TASK_FAILED = EventType("task", "failed")
    ERROR_OCCURRED = EventType("error", "occurred")
    MODULE_STARTED = EventType("module", "started")
    MODULE_STOPPED = EventType("module", "stopped")
    CONFIG_CHANGED = EventType("config", "changed")
    SYSTEM_SHUTDOWN = EventType("system", "shutdown")


@dataclass
class AgentEvent:
    """
    标准化事件
    
    第一性原理：事件是信息的完整载体，必须自描述、可追踪
    """
    event_type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    correlation_id: Optional[str] = None  # 关联ID，用于追踪事件链
    causation_id: Optional[str] = None    # 因果ID，记录由哪个事件触发
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "type": self.event_type.full_name,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.name,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
        }
    
    def derive(self, event_type: EventType, payload: Optional[Dict[str, Any]] = None) -> 'AgentEvent':
        """派生新事件，保持追踪链"""
        return AgentEvent(
            event_type=event_type,
            payload=payload or {},
            source=self.source,
            priority=self.priority,
            correlation_id=self.correlation_id or self.event_id,
            causation_id=self.event_id,
        )


# ============================================================
# 订阅者接口
# ============================================================

class EventHandler(ABC):
    """
    事件处理器抽象基类
    
    第一性原理：订阅者必须显式声明自己处理什么、如何过滤
    """
    
    @abstractmethod
    def can_handle(self, event_type: EventType) -> bool:
        """判断是否可处理该事件类型"""
        pass
    
    @abstractmethod
    def handle(self, event: AgentEvent) -> None:
        """处理事件"""
        pass
    
    def get_priority(self) -> int:
        """处理器优先级（数值越小越优先）"""
        return 100


@dataclass
class Subscription:
    """订阅记录"""
    id: str
    handler: EventHandler
    event_pattern: str  # 如 "state.*", "*.updated"
    filter_fn: Optional[Callable[[AgentEvent], bool]] = None
    
    def matches(self, event: AgentEvent) -> bool:
        """判断事件是否匹配此订阅"""
        if not event.event_type.matches(self.event_pattern):
            return False
        if self.filter_fn and not self.filter_fn(event):
            return False
        return True


# ============================================================
# 事件总线
# ============================================================

class EventBus:
    """
    规范化事件总线
    
    第一性原理：事件总线是系统的神经系统，必须可靠、有序、可观测
    """
    
    def __init__(self, max_queue_size: int = 10000):
        self._subscriptions: Dict[str, Subscription] = {}
        self._lock = threading.RLock()
        self._event_queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_queue_size)
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._event_count = 0
        self._drop_count = 0
        self._handlers_called = 0
    
    def subscribe(
        self,
        handler: EventHandler,
        event_pattern: str = "*.*",
        filter_fn: Optional[Callable[[AgentEvent], bool]] = None
    ) -> str:
        """
        订阅事件
        
        Args:
            handler: 事件处理器
            event_pattern: 事件类型匹配模式
            filter_fn: 可选的额外过滤函数
        
        Returns:
            订阅ID
        """
        sub_id = str(uuid.uuid4())[:8]
        subscription = Subscription(
            id=sub_id,
            handler=handler,
            event_pattern=event_pattern,
            filter_fn=filter_fn,
        )
        
        with self._lock:
            self._subscriptions[sub_id] = subscription
        
        return sub_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        with self._lock:
            if subscription_id in self._subscriptions:
                del self._subscriptions[subscription_id]
                return True
            return False
    
    def publish(
        self,
        event: AgentEvent,
        mode: DeliveryMode = DeliveryMode.ASYNC
    ) -> List[Any]:
        """
        发布事件
        
        Args:
            event: 要发布的事件
            mode: 投递模式
        
        Returns:
            同步模式下返回所有处理器的结果
        """
        if mode == DeliveryMode.SYNC:
            return self._publish_sync(event)
        elif mode == DeliveryMode.ASYNC:
            return self._publish_async(event)
        else:
            return self._publish_broadcast(event)
    
    def _get_matching_handlers(self, event: AgentEvent) -> List[Tuple[int, EventHandler]]:
        """获取匹配的事件处理器，按优先级排序"""
        handlers = []
        with self._lock:
            for sub in self._subscriptions.values():
                if sub.matches(event):
                    handlers.append((sub.handler.get_priority(), sub.handler))
        
        handlers.sort(key=lambda x: x[0])
        return handlers
    
    def _publish_sync(self, event: AgentEvent) -> List[Any]:
        """同步发布"""
        results = []
        handlers = self._get_matching_handlers(event)
        
        for _, handler in handlers:
            try:
                handler.handle(event)
                results.append(None)
                self._handlers_called += 1
            except Exception as e:
                results.append(e)
        
        self._event_count += 1
        return results
    
    def _publish_async(self, event: AgentEvent) -> List[Any]:
        """异步发布（入队列）"""
        try:
            # 优先级队列使用 (priority, seq, event) 格式
            self._event_queue.put_nowait((event.priority.value, self._event_count, event))
            self._event_count += 1
            return []
        except queue.Full:
            self._drop_count += 1
            return [Exception("Event queue full")]
    
    def _publish_broadcast(self, event: AgentEvent) -> List[Any]:
        """广播发布（异步，不保证顺序）"""
        return self._publish_async(event)
    
    def start(self) -> None:
        """启动异步处理线程"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_events, daemon=True)
        self._worker_thread.start()
    
    def stop(self) -> None:
        """停止异步处理线程"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
    
    def _process_events(self) -> None:
        """事件处理循环"""
        while self._running:
            try:
                _, _, event = self._event_queue.get(timeout=0.1)
                handlers = self._get_matching_handlers(event)
                
                for _, handler in handlers:
                    try:
                        handler.handle(event)
                        self._handlers_called += 1
                    except Exception:
                        # 异步模式下错误不传播
                        pass
                
                self._event_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        """获取事件总线统计"""
        return {
            "subscriptions": len(self._subscriptions),
            "events_published": self._event_count,
            "events_dropped": self._drop_count,
            "handlers_called": self._handlers_called,
            "queue_size": self._event_queue.qsize(),
            "running": self._running,
        }
    
    def clear(self) -> None:
        """清除所有订阅"""
        with self._lock:
            self._subscriptions.clear()


# ============================================================
# 便捷的事件处理器实现
# ============================================================

class FunctionEventHandler(EventHandler):
    """基于函数的事件处理器"""
    
    def __init__(
        self,
        handler_fn: Callable[[AgentEvent], None],
        event_pattern: str = "*.*",
        priority: int = 100
    ):
        self._handler_fn = handler_fn
        self._event_pattern = event_pattern
        self._priority = priority
    
    def can_handle(self, event_type: EventType) -> bool:
        return event_type.matches(self._event_pattern)
    
    def handle(self, event: AgentEvent) -> None:
        self._handler_fn(event)
    
    def get_priority(self) -> int:
        return self._priority


class FilteringEventHandler(EventHandler):
    """带过滤条件的事件处理器"""
    
    def __init__(
        self,
        handler_fn: Callable[[AgentEvent], None],
        event_pattern: str = "*.*",
        filter_fn: Optional[Callable[[AgentEvent], bool]] = None,
        priority: int = 100
    ):
        self._handler_fn = handler_fn
        self._event_pattern = event_pattern
        self._filter_fn = filter_fn
        self._priority = priority
    
    def can_handle(self, event_type: EventType) -> bool:
        return event_type.matches(self._event_pattern)
    
    def handle(self, event: AgentEvent) -> None:
        if self._filter_fn is None or self._filter_fn(event):
            self._handler_fn(event)
    
    def get_priority(self) -> int:
        return self._priority


# ============================================================
# 事件构建器
# ============================================================

class EventBuilder:
    """
    事件构建器
    
    提供流畅的API构建事件
    """
    
    def __init__(self, event_type: EventType):
        self._event_type = event_type
        self._payload: Dict[str, Any] = {}
        self._source = "unknown"
        self._priority = EventPriority.NORMAL
        self._correlation_id: Optional[str] = None
        self._causation_id: Optional[str] = None
    
    def with_payload(self, **kwargs) -> 'EventBuilder':
        self._payload.update(kwargs)
        return self
    
    def from_source(self, source: str) -> 'EventBuilder':
        self._source = source
        return self
    
    def with_priority(self, priority: EventPriority) -> 'EventBuilder':
        self._priority = priority
        return self
    
    def with_correlation(self, correlation_id: str) -> 'EventBuilder':
        self._correlation_id = correlation_id
        return self
    
    def caused_by(self, causation_id: str) -> 'EventBuilder':
        self._causation_id = causation_id
        return self
    
    def build(self) -> AgentEvent:
        return AgentEvent(
            event_type=self._event_type,
            payload=self._payload,
            source=self._source,
            priority=self._priority,
            correlation_id=self._correlation_id,
            causation_id=self._causation_id,
        )
