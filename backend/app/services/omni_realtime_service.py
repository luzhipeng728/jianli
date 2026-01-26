"""Qwen-Omni Realtime 端到端实时语音对话服务

使用 qwen3-omni-flash-realtime 模型实现:
- 实时语音输入 (内置 VAD)
- 端到端语音理解
- 实时语音输出
- 支持自定义系统提示

参考文档:
- https://help.aliyun.com/zh/model-studio/realtime
"""

import os
import json
import asyncio
import base64
import logging
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    """对话状态"""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    CLOSED = "closed"


@dataclass
class OmniEvent:
    """Omni 事件"""
    type: str
    data: dict = field(default_factory=dict)


class OmniRealtimeSession:
    """Qwen-Omni Realtime 会话

    管理与 Qwen-Omni Realtime API 的 WebSocket 连接，
    支持实时双向语音对话。
    """

    # API 配置
    WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
    MODEL = "qwen3-omni-flash-realtime"

    # 支持的音色列表 (49种)
    VOICES = [
        "zhitian_emo", "zhichu_emo", "zhida_emo", "zhixiaobai", "zhixiaoxia",
        "zhiyan_emo", "loongstella", "loongbella", "longjielidou", "longlibra",
        "longshu", "longshuo", "longxiaochun", "longxiaoxia", "longhua",
        "longwan", "longcheng", "longfei", "longjing", "longyue",
        # ... 更多音色
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        system_prompt: str = "",
        voice: str = "zhitian_emo",
        on_transcript: Optional[Callable[[str, bool], Any]] = None,
        on_response_text: Optional[Callable[[str], Any]] = None,
        on_response_audio: Optional[Callable[[bytes], Any]] = None,
        on_state_change: Optional[Callable[[ConversationState], Any]] = None,
        on_error: Optional[Callable[[str], Any]] = None,
    ):
        """初始化 Omni Realtime 会话

        Args:
            api_key: DashScope API Key
            system_prompt: 系统提示词 (定义 AI 人设)
            voice: 语音音色
            on_transcript: 转录回调 (text, is_final)
            on_response_text: 响应文本回调
            on_response_audio: 响应音频回调 (PCM bytes)
            on_state_change: 状态变化回调
            on_error: 错误回调
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY not configured")

        self.system_prompt = system_prompt
        self.voice = voice

        # 回调函数
        self.on_transcript = on_transcript
        self.on_response_text = on_response_text
        self.on_response_audio = on_response_audio
        self.on_state_change = on_state_change
        self.on_error = on_error

        # 内部状态
        self._ws: Optional[WebSocketClientProtocol] = None
        self._state = ConversationState.IDLE
        self._receive_task: Optional[asyncio.Task] = None
        self._conversation_id: Optional[str] = None
        self._should_reconnect = True  # 是否应该自动重连
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5

        # 音频配置
        self.input_sample_rate = 16000   # 输入: 16kHz
        self.output_sample_rate = 24000  # 输出: 24kHz

    @property
    def state(self) -> ConversationState:
        return self._state

    def _set_state(self, new_state: ConversationState):
        """更新状态并触发回调"""
        if self._state != new_state:
            self._state = new_state
            if self.on_state_change:
                try:
                    self.on_state_change(new_state)
                except Exception as e:
                    logger.error(f"[Omni] State callback error: {e}")

    async def connect(self) -> bool:
        """建立 WebSocket 连接

        Returns:
            bool: 连接是否成功
        """
        try:
            # 构建连接 URL
            url = f"{self.WS_URL}?model={self.MODEL}"
            print(f"[Omni] Connecting to {url}")

            # 连接 WebSocket
            self._ws = await websockets.connect(
                url,
                additional_headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "X-DashScope-DataInspection": "enable",
                    "OpenAI-Beta": "realtime=v1",  # 可能需要的头
                },
                ping_interval=20,
                ping_timeout=10,
            )

            print(f"[Omni] WebSocket connected to {self.MODEL}")

            # 发送会话配置
            print("[Omni] Sending session config...")
            await self._send_session_update()
            print("[Omni] Session config sent")

            # 启动接收任务
            print("[Omni] Starting receive loop...")
            self._receive_task = asyncio.create_task(self._receive_loop())

            self._set_state(ConversationState.LISTENING)
            print("[Omni] Connection established successfully")
            return True

        except Exception as e:
            print(f"[Omni] Connection failed: {e}")
            import traceback
            traceback.print_exc()
            if self.on_error:
                self.on_error(f"Connection failed: {e}")
            return False

    async def _send_session_update(self):
        """发送会话配置"""
        if not self._ws:
            return

        # 会话配置 - 禁用服务端VAD，改为手动模式
        # 用户说完后手动点击发送按钮，调用 commit_audio()
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": self.system_prompt,
                "voice": self.voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": None,  # 禁用VAD，改为手动模式
                "temperature": 0.8,
                "max_response_output_tokens": 4096,
            }
        }

        await self._ws.send(json.dumps(session_config))
        logger.info("[Omni] Session configured with manual mode (VAD disabled)")

    async def _receive_loop(self):
        """接收消息循环"""
        if not self._ws:
            print("[Omni] No WebSocket in receive loop")
            return

        print("[Omni] Starting receive loop")
        try:
            async for message in self._ws:
                # 重置重连计数
                self._reconnect_attempts = 0
                print(f"[Omni] Received message: {message[:200] if len(message) > 200 else message}")
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed as e:
            print(f"[Omni] Connection closed: {e}")
            # 尝试自动重连
            if self._should_reconnect:
                await self._try_reconnect()
                return
        except Exception as e:
            print(f"[Omni] Receive error: {e}")
            import traceback
            traceback.print_exc()
            if self.on_error:
                self.on_error(str(e))
            # 尝试自动重连
            if self._should_reconnect:
                await self._try_reconnect()
                return
        finally:
            if not self._should_reconnect:
                print("[Omni] Receive loop ended, setting state to CLOSED")
                self._set_state(ConversationState.CLOSED)

    async def _try_reconnect(self):
        """尝试自动重连"""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            print(f"[Omni] Max reconnect attempts ({self._max_reconnect_attempts}) reached, giving up")
            self._set_state(ConversationState.CLOSED)
            if self.on_error:
                self.on_error("连接已断开，请刷新页面重试")
            return

        self._reconnect_attempts += 1
        wait_time = min(2 ** self._reconnect_attempts, 10)  # 指数退避，最多等10秒
        print(f"[Omni] Attempting reconnect #{self._reconnect_attempts} in {wait_time}s...")

        await asyncio.sleep(wait_time)

        try:
            # 关闭旧连接
            if self._ws:
                try:
                    await self._ws.close()
                except:
                    pass
                self._ws = None

            # 重新连接
            url = f"{self.WS_URL}?model={self.MODEL}"
            print(f"[Omni] Reconnecting to {url}")

            self._ws = await websockets.connect(
                url,
                additional_headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "X-DashScope-DataInspection": "enable",
                    "OpenAI-Beta": "realtime=v1",
                },
                ping_interval=20,
                ping_timeout=10,
            )

            print(f"[Omni] Reconnected successfully")

            # 重新发送会话配置
            await self._send_session_update()

            # 重启接收循环
            self._receive_task = asyncio.create_task(self._receive_loop())

            self._set_state(ConversationState.LISTENING)
            print("[Omni] Session restored after reconnection")

        except Exception as e:
            print(f"[Omni] Reconnect failed: {e}")
            # 继续尝试重连
            await self._try_reconnect()

    async def _handle_message(self, message: str):
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            event_type = data.get("type", "")

            # 会话创建成功
            if event_type == "session.created":
                self._conversation_id = data.get("session", {}).get("id")
                print(f"[Omni] Session created: {self._conversation_id}")
                logger.info(f"[Omni] Session created: {self._conversation_id}")

            # 会话更新确认
            elif event_type == "session.updated":
                print(f"[Omni] Session updated successfully")

            # 输入音频缓冲区已提交
            elif event_type == "input_audio_buffer.committed":
                print(f"[Omni] Audio buffer committed")

            # 输入音频缓冲区语音开始
            elif event_type == "input_audio_buffer.speech_started":
                print(f"[Omni] Speech detected - VAD triggered")

            # 输入音频缓冲区语音结束
            elif event_type == "input_audio_buffer.speech_stopped":
                print(f"[Omni] Speech ended - VAD detected silence")

            # 输入音频转录 (实时)
            elif event_type == "conversation.item.input_audio_transcription.delta":
                text = data.get("delta", "")
                if text and self.on_transcript:
                    self.on_transcript(text, False)

            # 输入音频转录 (完成)
            elif event_type == "conversation.item.input_audio_transcription.completed":
                text = data.get("transcript", "")
                if text and self.on_transcript:
                    self.on_transcript(text, True)

            # 响应开始
            elif event_type == "response.created":
                self._set_state(ConversationState.THINKING)

            # 响应文本 (增量)
            elif event_type == "response.text.delta":
                text = data.get("delta", "")
                if text and self.on_response_text:
                    self.on_response_text(text)

            # 响应音频转录 (增量) - 用于显示AI说的内容
            elif event_type == "response.audio_transcript.delta":
                text = data.get("delta", "")
                if text and self.on_response_text:
                    self.on_response_text(text)

            # 响应音频 (增量)
            elif event_type == "response.audio.delta":
                audio_b64 = data.get("delta", "")
                if audio_b64:
                    self._set_state(ConversationState.SPEAKING)
                    if self.on_response_audio:
                        audio_bytes = base64.b64decode(audio_b64)
                        self.on_response_audio(audio_bytes)

            # 响应完成
            elif event_type == "response.done":
                self._set_state(ConversationState.LISTENING)

            # 错误
            elif event_type == "error":
                error_msg = data.get("error", {}).get("message", "Unknown error")
                logger.error(f"[Omni] Server error: {error_msg}")
                if self.on_error:
                    self.on_error(error_msg)

        except Exception as e:
            logger.error(f"[Omni] Message handling error: {e}")

    async def send_audio(self, audio_data: bytes) -> bool:
        """发送音频数据

        Args:
            audio_data: PCM 音频数据 (16kHz, 16bit, mono)

        Returns:
            bool: 是否发送成功
        """
        if not self._ws:
            logger.warning("[Omni] Cannot send audio: WebSocket is None")
            return False

        if self._state == ConversationState.CLOSED:
            logger.warning("[Omni] Cannot send audio: Session is closed")
            return False

        try:
            # 检查WebSocket连接状态
            if self._ws.close_code is not None:
                logger.warning(f"[Omni] WebSocket is closed (code: {self._ws.close_code}), cannot send audio")
                self._set_state(ConversationState.CLOSED)
                return False

            # 编码为 base64
            audio_b64 = base64.b64encode(audio_data).decode('ascii')

            # 发送音频
            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_b64
            }
            await self._ws.send(json.dumps(message))
            return True

        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"[Omni] Send audio failed - connection closed: {e}")
            self._set_state(ConversationState.CLOSED)
            if self.on_error:
                self.on_error(f"Connection closed: {e}")
            return False
        except Exception as e:
            logger.error(f"[Omni] Send audio error: {e}")
            return False

    async def commit_audio(self):
        """提交音频缓冲区并触发AI响应

        手动模式下，用户说完话后调用此方法
        """
        if not self._ws:
            print("[Omni] Cannot commit: WebSocket is None")
            return

        if self._ws.close_code is not None:
            print(f"[Omni] Cannot commit: WebSocket is closed")
            return

        try:
            # 1. 提交音频缓冲区
            commit_msg = {"type": "input_audio_buffer.commit"}
            await self._ws.send(json.dumps(commit_msg))
            print("[Omni] Audio buffer committed")

            # 2. 触发响应生成
            response_msg = {"type": "response.create"}
            await self._ws.send(json.dumps(response_msg))
            print("[Omni] Response generation triggered")

        except Exception as e:
            logger.error(f"[Omni] Commit audio error: {e}")
            print(f"[Omni] Commit audio error: {e}")

    async def cancel_response(self):
        """取消当前响应 (打断)"""
        if not self._ws:
            return

        try:
            message = {"type": "response.cancel"}
            await self._ws.send(json.dumps(message))
        except Exception as e:
            logger.error(f"[Omni] Cancel response error: {e}")

    async def send_text(self, text: str):
        """发送文本消息

        Args:
            text: 要发送的文本
        """
        if not self._ws:
            return

        try:
            # 添加文本消息
            message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": text
                        }
                    ]
                }
            }
            await self._ws.send(json.dumps(message))

            # 触发响应
            await self._ws.send(json.dumps({"type": "response.create"}))

        except Exception as e:
            logger.error(f"[Omni] Send text error: {e}")

    async def inject_context(self, context: str):
        """注入上下文 (用于控场 Agent 提供提示)

        这会作为系统消息注入到对话中，但不触发响应。

        Args:
            context: 上下文信息 (对用户不可见)
        """
        if not self._ws:
            return

        try:
            message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"[控场提示] {context}"
                        }
                    ]
                }
            }
            await self._ws.send(json.dumps(message))
            logger.info(f"[Omni] Injected context: {context[:50]}...")

        except Exception as e:
            logger.error(f"[Omni] Inject context error: {e}")

    async def close(self):
        """关闭连接"""
        # 禁用自动重连
        self._should_reconnect = False
        self._set_state(ConversationState.CLOSED)

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._ws:
            try:
                await self._ws.close()
            except:
                pass
            self._ws = None

        logger.info("[Omni] Session closed")


class OmniRealtimeService:
    """Omni Realtime 服务管理器

    管理多个 Omni 会话，提供会话创建和管理功能。
    """

    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self._sessions: dict[str, OmniRealtimeSession] = {}

    async def create_session(
        self,
        session_id: str,
        system_prompt: str,
        voice: str = "zhitian_emo",
        **callbacks
    ) -> OmniRealtimeSession:
        """创建新的 Omni 会话

        Args:
            session_id: 会话 ID
            system_prompt: 系统提示词
            voice: 语音音色
            **callbacks: 回调函数

        Returns:
            OmniRealtimeSession: 会话实例
        """
        # 关闭已存在的会话
        if session_id in self._sessions:
            await self._sessions[session_id].close()

        # 创建新会话
        session = OmniRealtimeSession(
            api_key=self.api_key,
            system_prompt=system_prompt,
            voice=voice,
            **callbacks
        )

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[OmniRealtimeSession]:
        """获取会话"""
        return self._sessions.get(session_id)

    async def close_session(self, session_id: str):
        """关闭会话"""
        if session_id in self._sessions:
            await self._sessions[session_id].close()
            del self._sessions[session_id]

    async def close_all(self):
        """关闭所有会话"""
        for session in self._sessions.values():
            await session.close()
        self._sessions.clear()


# 全局单例
_omni_service: Optional[OmniRealtimeService] = None


def get_omni_service() -> OmniRealtimeService:
    """获取 Omni Realtime 服务单例"""
    global _omni_service
    if _omni_service is None:
        _omni_service = OmniRealtimeService()
    return _omni_service
