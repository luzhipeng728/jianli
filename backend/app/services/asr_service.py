"""Paraformer 实时语音识别服务

使用阿里云 DashScope Paraformer 实现实时 ASR，支持长时间语音流。
参考文档: https://help.aliyun.com/zh/model-studio/paraformer-real-time-speech-recognition-python-sdk
"""

import os
import asyncio
import json
from typing import Optional, Callable, Any
from dataclasses import dataclass
import logging

import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


@dataclass
class TranscriptResult:
    """转录结果"""
    text: str
    is_final: bool
    sentence_id: int = 0


class ParaformerASRSession:
    """Paraformer 实时语音识别会话

    支持长时间语音流，没有60秒限制。
    """

    # WebSocket 地址
    WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference/"
    MODEL = "paraformer-realtime-v2"

    def __init__(
        self,
        api_key: Optional[str] = None,
        on_transcript: Optional[Callable[[str, bool], Any]] = None,
        on_error: Optional[Callable[[str], Any]] = None,
        sample_rate: int = 16000,
        language: str = "zh",
    ):
        """初始化 ASR 会话

        Args:
            api_key: DashScope API Key
            on_transcript: 转录回调 (text, is_final)
            on_error: 错误回调
            sample_rate: 采样率 (16000 或 8000)
            language: 语言 (zh, en, ja, ko, etc.)
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY not configured")

        self.on_transcript = on_transcript
        self.on_error = on_error
        self.sample_rate = sample_rate
        self.language = language

        self._ws: Optional[WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._is_connected = False
        self._task_id: Optional[str] = None

        # 累积转录文本（用于处理增量）
        self._current_sentence = ""
        self._sentence_id = 0

    async def connect(self) -> bool:
        """建立 WebSocket 连接"""
        try:
            print(f"[ASR] Connecting to Paraformer...")

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
                    "task_id": f"asr-{id(self)}",
                    "streaming": "duplex"
                },
                "payload": {
                    "model": self.MODEL,
                    "task_group": "audio",
                    "task": "asr",
                    "function": "recognition",
                    "parameters": {
                        "format": "pcm",
                        "sample_rate": self.sample_rate,
                        "language_hints": [self.language],
                        "disfluency_removal_enabled": True,  # 语气词过滤
                    },
                    "input": {}
                }
            }

            await self._ws.send(json.dumps(start_task))
            print(f"[ASR] Sent start task request")

            # 等待任务启动确认
            response = await self._ws.recv()
            data = json.loads(response)

            if data.get("header", {}).get("event") == "task-started":
                self._task_id = data["header"].get("task_id")
                self._is_connected = True
                print(f"[ASR] Task started: {self._task_id}")

                # 启动接收循环
                self._receive_task = asyncio.create_task(self._receive_loop())
                return True
            else:
                error = data.get("header", {}).get("error_message", "Unknown error")
                print(f"[ASR] Failed to start task: {error}")
                if self.on_error:
                    self.on_error(error)
                return False

        except Exception as e:
            print(f"[ASR] Connection error: {e}")
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
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed as e:
            print(f"[ASR] Connection closed: {e}")
        except Exception as e:
            print(f"[ASR] Receive error: {e}")
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
                # 处理识别结果
                output = data.get("payload", {}).get("output", {})
                sentence = output.get("sentence", {})

                text = sentence.get("text", "")
                end_time = sentence.get("end_time")
                # 判断句子是否结束：end_time 存在且大于0
                is_end = end_time is not None and end_time > 0

                if text:
                    # 检查是否是最终结果
                    if is_end:
                        self._sentence_id += 1
                        if self.on_transcript:
                            self.on_transcript(text, True)
                        self._current_sentence = ""
                    else:
                        # 增量结果
                        self._current_sentence = text
                        if self.on_transcript:
                            self.on_transcript(text, False)

            elif event == "task-finished":
                print(f"[ASR] Task finished")
                self._is_connected = False

            elif event == "task-failed":
                error = data.get("header", {}).get("error_message", "Unknown error")
                print(f"[ASR] Task failed: {error}")
                if self.on_error:
                    self.on_error(error)
                self._is_connected = False

        except Exception as e:
            print(f"[ASR] Handle message error: {e}")

    async def send_audio(self, audio_data: bytes) -> bool:
        """发送音频数据

        Args:
            audio_data: PCM 音频数据 (16kHz, 16bit, mono)

        Returns:
            bool: 是否发送成功
        """
        if not self._ws or not self._is_connected:
            return False

        try:
            # 发送二进制音频数据
            await self._ws.send(audio_data)
            return True
        except Exception as e:
            print(f"[ASR] Send audio error: {e}")
            return False

    async def finish(self):
        """结束音频输入，获取最终结果"""
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
            print(f"[ASR] Sent finish signal")
        except Exception as e:
            print(f"[ASR] Finish error: {e}")

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

        print(f"[ASR] Session closed")


# 全局服务实例
_asr_service = None


def get_asr_service():
    """获取 ASR 服务实例"""
    global _asr_service
    if _asr_service is None:
        _asr_service = ParaformerASRSession()
    return _asr_service
