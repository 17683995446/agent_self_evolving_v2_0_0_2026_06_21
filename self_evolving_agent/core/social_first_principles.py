"""
阶段79: 社交第一性原理化

第一性原理:
1. 信息交换加速进化：单个Agent的学习速度有限
2. 协作产生规模效应：1+1 > 2
3. 社交必须基于信息共享，而非指令传递

设计原则:
- AgentIdentity: Agent身份
- Message: Agent间消息
- SocialFirstPrinciplesEngine: 社交引擎
- 支持知识共享、协作任务、群体学习
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class MessageType(Enum):
    """消息类型"""
    KNOWLEDGE_SHARE = "knowledge_share"    # 知识共享
    TASK_COLLABORATION = "task_collab"     # 任务协作
    ERROR_REPORT = "error_report"          # 错误报告
    QUERY = "query"                        # 查询请求
    RESPONSE = "response"                  # 查询响应


@dataclass
class AgentIdentity:
    """Agent身份"""
    agent_id: str
    capabilities: List[str] = field(default_factory=list)
    trust_score: float = 0.5              # 信任分数 [0,1]
    last_seen: float = field(default_factory=time.time)


@dataclass
class InterAgentMessage:
    """Agent间消息"""
    message_id: str
    sender_id: str
    receiver_id: str                      # "*" 表示广播
    message_type: MessageType
    payload: Any
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 社交第一性原理引擎
# ============================================================

class SocialFirstPrinciplesEngine:
    """
    社交第一性原理引擎

    核心原则：多Agent协作基于信息共享

    第一性原理推导:
    1. 单个Agent的知识有限
    2. 信息交换扩展知识边界
    3. 信任决定信息质量权重
    4. 协作任务需要能力互补
    5. 群体学习 > 个体学习
    """

    def __init__(self, engine_id: str = "social_engine"):
        self.engine_id = engine_id
        self._peers: Dict[str, AgentIdentity] = {}
        self._inbox: List[InterAgentMessage] = []
        self._outbox: List[InterAgentMessage] = []
        self._shared_knowledge: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._cycle_count = 0

    def register_peer(self, agent_id: str, capabilities: List[str] = None) -> AgentIdentity:
        """注册对等Agent"""
        peer = AgentIdentity(
            agent_id=agent_id,
            capabilities=capabilities or [],
        )
        with self._lock:
            self._peers[agent_id] = peer
        return peer

    def update_trust(self, agent_id: str, delta: float) -> None:
        """更新信任分数"""
        with self._lock:
            peer = self._peers.get(agent_id)
            if peer:
                peer.trust_score = max(0.0, min(1.0, peer.trust_score + delta))
                peer.last_seen = time.time()

    def send_message(
        self,
        sender_id: str,
        receiver_id: str,
        message_type: MessageType,
        payload: Any,
    ) -> InterAgentMessage:
        """发送消息"""
        msg = InterAgentMessage(
            message_id=f"msg_{int(time.time() * 1000)}_{self._cycle_count}",
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            payload=payload,
        )
        with self._lock:
            self._outbox.append(msg)
            self._cycle_count += 1
        return msg

    def broadcast(
        self,
        sender_id: str,
        message_type: MessageType,
        payload: Any,
    ) -> InterAgentMessage:
        """广播消息"""
        return self.send_message(sender_id, "*", message_type, payload)

    def receive_messages(self, agent_id: str) -> List[InterAgentMessage]:
        """接收发给指定Agent的消息"""
        with self._lock:
            messages = [
                msg for msg in self._inbox
                if msg.receiver_id == agent_id or msg.receiver_id == "*"
            ]
            # 从inbox移除已接收的消息
            self._inbox = [
                msg for msg in self._inbox
                if msg.receiver_id != agent_id and msg.receiver_id != "*"
            ]
        return messages

    def share_knowledge(self, agent_id: str, key: str, value: Any) -> None:
        """
        共享知识

        第一性原理：知识共享加速群体进化
        """
        with self._lock:
            if key not in self._shared_knowledge:
                self._shared_knowledge[key] = {}
            self._shared_knowledge[key][agent_id] = {
                "value": value,
                "timestamp": time.time(),
            }

    def query_knowledge(self, key: str) -> Dict[str, Any]:
        """
        查询知识

        返回所有Agent对该知识的贡献，按信任度加权
        """
        with self._lock:
            entries = self._shared_knowledge.get(key, {})
            result = {}
            for agent_id, data in entries.items():
                peer = self._peers.get(agent_id)
                trust = peer.trust_score if peer else 0.5
                result[agent_id] = {
                    "value": data["value"],
                    "trust": trust,
                    "weighted_value": data["value"] * trust if isinstance(data["value"], (int, float)) else data["value"],
                }
            return result

    def find_collaborators(self, required_capability: str) -> List[AgentIdentity]:
        """
        寻找协作者

        第一性原理：协作需要能力互补
        """
        with self._lock:
            return [
                peer for peer in self._peers.values()
                if required_capability in peer.capabilities
            ]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "engine_id": self.engine_id,
                "peers_count": len(self._peers),
                "inbox_size": len(self._inbox),
                "outbox_size": len(self._outbox),
                "shared_knowledge_topics": len(self._shared_knowledge),
                "cycle_count": self._cycle_count,
                "avg_trust": sum(p.trust_score for p in self._peers.values()) / len(self._peers) if self._peers else 0,
            }

    def clear(self) -> None:
        """清除"""
        with self._lock:
            self._inbox.clear()
            self._outbox.clear()
            self._shared_knowledge.clear()


# ============================================================
# 便捷函数
# ============================================================

def create_social_engine(engine_id: str = "social_engine") -> SocialFirstPrinciplesEngine:
    """创建社交引擎"""
    return SocialFirstPrinciplesEngine(engine_id=engine_id)


def create_agent_identity(agent_id: str, capabilities: List[str] = None) -> AgentIdentity:
    """创建Agent身份"""
    return AgentIdentity(agent_id=agent_id, capabilities=capabilities or [])
