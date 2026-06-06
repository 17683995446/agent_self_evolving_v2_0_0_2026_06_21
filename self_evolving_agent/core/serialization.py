"""
自驱永续进化Agent系统 — 消息序列化协议
阶段20：消息序列化协议

第一性原理：信息必须在不同模块间无损传递，序列化是信息跨越边界的必要手段

支持格式：
1. JSON：人类可读，便于调试
2. Binary：高效紧凑，适用于高频通信

版本兼容：
- 消息包含版本号
- 支持向前兼容（忽略未知字段）
- 支持向后兼容（提供默认值）
"""

import json
import struct
from typing import Dict, Any, Optional, Union, List
from enum import Enum, auto
from dataclasses import dataclass

from .interfaces import AgentMessage, MessageType, MessagePriority


class SerializationFormat(Enum):
    """序列化格式"""
    JSON = auto()
    BINARY = auto()


@dataclass
class SerializedMessage:
    """序列化后的消息"""
    format: SerializationFormat
    data: Union[str, bytes]
    version: str = "1.0.0"
    size: int = 0


class JSONSerializer:
    """
    JSON序列化器

    特点：
    - 人类可读
    - 跨语言兼容
    - 便于调试
    """

    @staticmethod
    def serialize(message: AgentMessage) -> str:
        """序列化为JSON字符串"""
        data = {
            "version": message.version,
            "msg_id": message.msg_id,
            "msg_type": message.msg_type.name,
            "source": message.source,
            "target": message.target,
            "payload": message.payload,
            "timestamp": message.timestamp.isoformat(),
            "priority": message.priority.name,
        }
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    @staticmethod
    def deserialize(data: str) -> Optional[AgentMessage]:
        """从JSON字符串反序列化"""
        try:
            obj = json.loads(data)
            return JSONSerializer._dict_to_message(obj)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise SerializationError(f"JSON deserialization failed: {e}")

    @staticmethod
    def _dict_to_message(obj: Dict[str, Any]) -> AgentMessage:
        """字典转消息"""
        from datetime import datetime

        # 处理版本兼容
        version = obj.get("version", "1.0.0")

        # 解析消息类型（兼容旧版本）
        msg_type_name = obj.get("msg_type", "SYSTEM_EVENT")
        try:
            msg_type = MessageType[msg_type_name]
        except KeyError:
            # 未知类型，使用默认值
            msg_type = MessageType.SYSTEM_EVENT

        # 解析优先级（兼容旧版本）
        priority_name = obj.get("priority", "NORMAL")
        try:
            priority = MessagePriority[priority_name]
        except KeyError:
            priority = MessagePriority.NORMAL

        # 解析时间戳
        timestamp_str = obj.get("timestamp")
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()

        return AgentMessage(
            msg_id=obj.get("msg_id", ""),
            msg_type=msg_type,
            source=obj.get("source", ""),
            target=obj.get("target"),
            payload=obj.get("payload", {}),
            timestamp=timestamp,
            priority=priority,
            version=version,
        )


class BinarySerializer:
    """
    二进制序列化器

    特点：
    - 高效紧凑
    - 适用于高频通信
    - 固定头部 + 变长载荷

    格式：
    [版本(4)][类型(4)][优先级(4)][源长度(4)][目标长度(4)][载荷长度(4)][时间戳(8)]
    [源模块][目标模块][载荷数据]
    """

    HEADER_FORMAT = "!IIIIIId"  # 网络字节序
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    VERSION = 1

    @staticmethod
    def serialize(message: AgentMessage) -> bytes:
        """序列化为二进制"""
        # 编码字符串
        source_bytes = message.source.encode('utf-8')
        target_bytes = message.target.encode('utf-8') if message.target else b''
        payload_bytes = json.dumps(message.payload, ensure_ascii=False).encode('utf-8')

        # 构建头部
        header = struct.pack(
            BinarySerializer.HEADER_FORMAT,
            BinarySerializer.VERSION,
            message.msg_type.value,
            message.priority.value,
            len(source_bytes),
            len(target_bytes),
            len(payload_bytes),
            message.timestamp.timestamp(),
        )

        # 组合
        return header + source_bytes + target_bytes + payload_bytes

    @staticmethod
    def deserialize(data: bytes) -> Optional[AgentMessage]:
        """从二进制反序列化"""
        try:
            if len(data) < BinarySerializer.HEADER_SIZE:
                raise SerializationError("Data too short for header")

            # 解析头部
            header = struct.unpack(
                BinarySerializer.HEADER_FORMAT,
                data[:BinarySerializer.HEADER_SIZE]
            )
            version, msg_type_val, priority_val, source_len, target_len, payload_len, timestamp_val = header

            # 检查版本
            if version != BinarySerializer.VERSION:
                raise SerializationError(f"Version mismatch: expected {BinarySerializer.VERSION}, got {version}")

            # 解析数据
            offset = BinarySerializer.HEADER_SIZE
            source = data[offset:offset + source_len].decode('utf-8')
            offset += source_len

            target = data[offset:offset + target_len].decode('utf-8') if target_len > 0 else None
            offset += target_len

            payload = json.loads(data[offset:offset + payload_len].decode('utf-8'))

            from datetime import datetime
            return AgentMessage(
                msg_type=MessageType(msg_type_val),
                source=source,
                target=target,
                payload=payload,
                timestamp=datetime.fromtimestamp(timestamp_val),
                priority=MessagePriority(priority_val),
                version=str(version),
            )
        except (struct.error, KeyError, ValueError, json.JSONDecodeError) as e:
            raise SerializationError(f"Binary deserialization failed: {e}")


class SerializationError(Exception):
    """序列化错误"""
    pass


class MessageSerializer:
    """
    统一消息序列化器

    根据配置自动选择序列化格式
    """

    def __init__(self, default_format: SerializationFormat = SerializationFormat.JSON):
        self.default_format = default_format
        self._json_serializer = JSONSerializer()
        self._binary_serializer = BinarySerializer()

    def serialize(self, message: AgentMessage,
                  format: SerializationFormat = None) -> SerializedMessage:
        """序列化消息"""
        fmt = format or self.default_format

        if fmt == SerializationFormat.JSON:
            data = self._json_serializer.serialize(message)
            return SerializedMessage(
                format=fmt,
                data=data,
                version=message.version,
                size=len(data.encode('utf-8')),
            )
        elif fmt == SerializationFormat.BINARY:
            data = self._binary_serializer.serialize(message)
            return SerializedMessage(
                format=fmt,
                data=data,
                version=message.version,
                size=len(data),
            )
        else:
            raise SerializationError(f"Unknown format: {fmt}")

    def deserialize(self, serialized: SerializedMessage) -> Optional[AgentMessage]:
        """反序列化消息"""
        if serialized.format == SerializationFormat.JSON:
            return self._json_serializer.deserialize(serialized.data)
        elif serialized.format == SerializationFormat.BINARY:
            return self._binary_serializer.deserialize(serialized.data)
        else:
            raise SerializationError(f"Unknown format: {serialized.format}")

    def serialize_batch(self, messages: List[AgentMessage],
                        format: SerializationFormat = None) -> SerializedMessage:
        """批量序列化"""
        fmt = format or self.default_format

        if fmt == SerializationFormat.JSON:
            data = json.dumps([
                json.loads(self._json_serializer.serialize(m))
                for m in messages
            ], ensure_ascii=False)
            return SerializedMessage(
                format=fmt,
                data=data,
                size=len(data.encode('utf-8')),
            )
        else:
            # 二进制批量：先写数量，再依次写每条消息
            result = struct.pack("!I", len(messages))
            for msg in messages:
                msg_bytes = self._binary_serializer.serialize(msg)
                result += struct.pack("!I", len(msg_bytes)) + msg_bytes
            return SerializedMessage(
                format=fmt,
                data=result,
                size=len(result),
            )

    def get_stats(self) -> Dict[str, Any]:
        """获取序列化器统计"""
        return {
            "default_format": self.default_format.name,
            "supported_formats": [f.name for f in SerializationFormat],
        }
