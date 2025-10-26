from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import time, hashlib

class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, object]

class AgentMessage(BaseModel):
    message_id: str
    conversation_id: str
    sender: str
    receiver: str
    timestamp: str
    performative: str
    schema_version: str
    ttl: Optional[int] = 60
    idempotency_key: Optional[str] = None
    in_reply_to: Optional[str] = None
    reply_to: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    content: Dict[str, object]
