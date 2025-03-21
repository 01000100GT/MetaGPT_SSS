from pydantic import BaseModel, Field
from datetime import datetime
from pydantic import field_validator
from enum import Enum
from typing import Set, Optional, Dict, Any, Union, List
import uuid


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"           # 文本消息
    COMMAND = "command"     # 命令消息
    RESULT = "result"       # 结果消息
    ERROR = "error"         # 错误消息
    SYSTEM = "system"       # 系统消息
    ACTION = "action"       # 动作消息
    CUSTOM = "custom"       # 自定义消息


class MessagePriority(int, Enum):
    """消息优先级枚举"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class Message(BaseModel):
    """增强版消息类"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    context: Any = Field(default=None, description="消息内容")
    type: MessageType = Field(default=MessageType.TEXT, description="消息类型")
    sent_from: Optional[str] = Field(default=None, description="发送者")
    sent_to: Optional[List[str]] = Field(
        default_factory=list, description="接收者列表")
    cause_by: Optional[str] = Field(default=None, description="触发原因")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="时间戳")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    priority: MessagePriority = Field(
        default=MessagePriority.NORMAL, description="优先级")

    def add_metadata(self, key: str, value: Any) -> None:
        """添加元数据"""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self.metadata.get(key, default)

    def is_from(self, sender: str) -> bool:
        """检查消息是否来自特定发送者"""
        return self.sent_from == sender

    def is_caused_by(self, action: str) -> bool:
        """检查消息是否由特定动作触发"""
        return self.cause_by == action

    def is_type(self, msg_type: Union[MessageType, str]) -> bool:
        """检查消息类型"""
        if isinstance(msg_type, str):
            try:
                msg_type = MessageType(msg_type)
            except ValueError:
                return False
        return self.type == msg_type

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "context": self.context,
            "type": self.type.value,
            "sent_from": self.sent_from,
            "sent_to": self.sent_to,
            "cause_by": self.cause_by,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "priority": self.priority.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建消息"""
        # 处理时间戳
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        # 处理枚举类型
        if "type" in data and isinstance(data["type"], str):
            data["type"] = MessageType(data["type"])

        if "priority" in data and isinstance(data["priority"], int):
            data["priority"] = MessagePriority(data["priority"])

        return cls(**data)
