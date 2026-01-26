from pydantic import BaseModel, Field
from typing import Optional, Literal, Any
from datetime import datetime

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatSession(BaseModel):
    id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    show_thinking: bool = False
    jd_id: Optional[str] = None  # 筛选特定岗位的候选人

class StreamChunk(BaseModel):
    type: Literal["thinking", "text", "card", "done", "error"]
    content: str = ""
    card_type: Optional[str] = None
    data: Optional[Any] = None  # dict for comparison/stats, list for candidates
    metrics: Optional[dict] = None

class KnowledgeItem(BaseModel):
    id: str
    title: str
    content: str
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    source: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
