"""WebSocket 消息类型定义"""
from pydantic import BaseModel
from typing import Optional, Literal

class ClientMessage(BaseModel):
    """客户端发送的消息"""
    type: Literal["audio", "control", "ping", "audio_end"]
    audio: Optional[str] = None  # base64 编码的音频数据
    action: Optional[Literal["start", "stop", "pause", "resume"]] = None

class ServerMessage(BaseModel):
    """服务器发送的消息"""
    type: Literal["transcript", "audio", "status", "question", "end", "error", "pong"]
    text: Optional[str] = None  # 转录文本或问题文本
    is_final: Optional[bool] = None  # 转录是否完成
    audio: Optional[str] = None  # base64 编码的音频数据
    status: Optional[str] = None  # 状态：listening, processing, speaking, stopped
    question: Optional[str] = None  # 面试问题
    reason: Optional[str] = None  # 结束原因
    evaluation_ready: Optional[bool] = None  # 评估是否就绪
    message: Optional[str] = None  # 错误消息
