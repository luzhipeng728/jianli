"""CosyVoice 流式语音合成服务

使用阿里云 DashScope CosyVoice 实现流式 TTS。
参考文档: https://help.aliyun.com/zh/model-studio/cosyvoice-websocket-api
"""

import os
import asyncio
import json
from typing import Optional, Callable, Any, AsyncGenerator
from dataclasses import dataclass
import logging

import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


class CosyVoiceTTSSession:
    """CosyVoice 流式语音合成会话

    支持流式输出，低延迟。
    """

    # WebSocket 地址
    WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference/"
    MODEL = "cosyvoice-v1"

    # 支持的音色
    VOICES = {
        "longxiaochun": "龙小淳 - 温柔女声",
        "longxiaoxia": "龙小夏 - 活泼女声",
        "longyue": "龙悦 - 知性女声",
        "longwan": "龙婉 - 甜美女声",
        "longcheng": "龙城 - 成熟男声",
        "longhua": "龙华 - 沉稳男声",
        "longjing": "龙京 - 新闻男声",
        "longfei": "龙飞 - 活力男声",
        "loongstella": "Stella - 英文女声",
        "loongbella": "Bella - 英文女声",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice: str = "longxiaochun",
        on_audio: Optional[Callable[[bytes], Any]] = None,
        on_complete: Optional[Callable[[], Any]] = None,
        on_error: Optional[Callable[[str], Any]] = None,
        sample_rate: int = 24000,
    ):
        """初始化 TTS 会话

        Args:
            api_key: DashScope API Key
            voice: 音色名称
            on_audio: 音频回调 (audio_bytes)
            on_complete: 完成回调
            on_error: 错误回调
            sample_rate: 采样率 (8000, 16000, 22050, 24000, 44100, 48000)
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY not configured")

        self.voice = voice
        self.on_audio = on_audio
        self.on_complete = on_complete
        self.on_error = on_error
        self.sample_rate = sample_rate

        self._ws: Optional[WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._is_connected = False
        self._task_id: Optional[str] = None

    async def connect(self) -> bool:
        """建立 WebSocket 连接"""
        try:
            print(f"[TTS] Connecting to CosyVoice...")

            self._ws = await websockets.connect(
                self.WS_URL,
                additional_headers={
                    "Authorization": f"Bearer {self.api_key}",
                },
                ping_interval=20,
                ping_timeout=10,
            )

            # 发送启动任务请求
            start_task = {
                "header": {
                    "action": "run-task",
                    "task_id": f"tts-{id(self)}",
                    "streaming": "duplex"
                },
                "payload": {
                    "model": self.MODEL,
                    "task_group": "audio",
                    "task": "tts",
                    "function": "SpeechSynthesizer",
                    "parameters": {
                        "voice": self.voice,
                        "format": "pcm",
                        "sample_rate": self.sample_rate,
                        "rate": 1.0,  # 语速
                        "pitch": 1.0,  # 音调
                    },
                    "input": {}
                }
            }

            await self._ws.send(json.dumps(start_task))
            print(f"[TTS] Sent start task request")

            # 等待任务启动确认
            response = await self._ws.recv()
            data = json.loads(response)

            if data.get("header", {}).get("event") == "task-started":
                self._task_id = data["header"].get("task_id")
                self._is_connected = True
                print(f"[TTS] Task started: {self._task_id}")

                # 启动接收循环
                self._receive_task = asyncio.create_task(self._receive_loop())
                return True
            else:
                error = data.get("header", {}).get("error_message", "Unknown error")
                print(f"[TTS] Failed to start task: {error}")
                if self.on_error:
                    self.on_error(error)
                return False

        except Exception as e:
            print(f"[TTS] Connection error: {e}")
            import traceback
            traceback.print_exc()
            if self.on_error:
                self.on_error(str(e))
            return False

    async def _receive_loop(self):
        """接收消息循环"""
        if not self._ws:
            return

        try:
            async for message in self._ws:
                if isinstance(message, bytes):
                    # 二进制音频数据
                    if self.on_audio:
                        self.on_audio(message)
                else:
                    # JSON 消息
                    await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed as e:
            print(f"[TTS] Connection closed: {e}")
        except Exception as e:
            print(f"[TTS] Receive error: {e}")
            if self.on_error:
                self.on_error(str(e))
        finally:
            self._is_connected = False

    async def _handle_message(self, message: str):
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            event = data.get("header", {}).get("event", "")

            if event == "result-generated":
                # 合成进度
                pass

            elif event == "task-finished":
                print(f"[TTS] Task finished")
                if self.on_complete:
                    self.on_complete()
                self._is_connected = False

            elif event == "task-failed":
                error = data.get("header", {}).get("error_message", "Unknown error")
                print(f"[TTS] Task failed: {error}")
                if self.on_error:
                    self.on_error(error)
                self._is_connected = False

        except Exception as e:
            print(f"[TTS] Handle message error: {e}")

    async def synthesize(self, text: str) -> bool:
        """发送文本进行合成

        Args:
            text: 要合成的文本

        Returns:
            bool: 是否发送成功
        """
        if not self._ws or not self._is_connected:
            return False

        try:
            # 发送文本
            text_msg = {
                "header": {
                    "action": "continue-task",
                    "task_id": self._task_id,
                    "streaming": "duplex"
                },
                "payload": {
                    "input": {
                        "text": text
                    }
                }
            }
            await self._ws.send(json.dumps(text_msg))
            return True
        except Exception as e:
            print(f"[TTS] Synthesize error: {e}")
            return False

    async def finish(self):
        """结束合成，获取剩余音频"""
        if not self._ws or not self._is_connected:
            return

        try:
            # 发送结束信号
            finish_msg = {
                "header": {
                    "action": "finish-task",
                    "task_id": self._task_id,
                    "streaming": "duplex"
                },
                "payload": {
                    "input": {}
                }
            }
            await self._ws.send(json.dumps(finish_msg))
            print(f"[TTS] Sent finish signal")
        except Exception as e:
            print(f"[TTS] Finish error: {e}")

    async def close(self):
        """关闭连接"""
        self._is_connected = False

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

        print(f"[TTS] Session closed")


async def synthesize_text(text: str, voice: str = "longxiaochun") -> AsyncGenerator[bytes, None]:
    """简单的文本转语音函数

    Args:
        text: 要合成的文本
        voice: 音色

    Yields:
        bytes: PCM 音频数据块
    """
    audio_queue = asyncio.Queue()
    is_complete = asyncio.Event()

    def on_audio(data: bytes):
        audio_queue.put_nowait(data)

    def on_complete():
        is_complete.set()

    session = CosyVoiceTTSSession(
        voice=voice,
        on_audio=on_audio,
        on_complete=on_complete,
    )

    if not await session.connect():
        return

    await session.synthesize(text)
    await session.finish()

    # 等待音频数据
    while not is_complete.is_set() or not audio_queue.empty():
        try:
            data = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
            yield data
        except asyncio.TimeoutError:
            continue

    await session.close()
