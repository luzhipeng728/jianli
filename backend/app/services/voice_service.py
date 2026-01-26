"""阿里云语音服务封装 - DashScope ASR & TTS

支持:
- 流式语音识别 (ASR) - 使用 Qwen3-ASR-Flash-Realtime
- 流式语音合成 (TTS) - 使用 Qwen3-TTS-Flash

参考文档:
- ASR: https://www.alibabacloud.com/help/en/model-studio/qwen-asr-realtime-python-sdk
- TTS: https://www.alibabacloud.com/help/en/model-studio/qwen-tts
"""

import os
import asyncio
import base64
import logging
from typing import AsyncGenerator, Optional, Callable
from dataclasses import dataclass

import dashscope
from dashscope.audio.qwen_omni import OmniRealtimeConversation, OmniRealtimeCallback

logger = logging.getLogger(__name__)


@dataclass
class ASRResult:
    """语音识别结果"""
    text: str
    is_final: bool
    sentence_id: Optional[str] = None


@dataclass
class TTSChunk:
    """语音合成音频块"""
    audio_data: bytes
    is_final: bool


class ASRCallback(OmniRealtimeCallback):
    """ASR 实时回调处理器"""

    def __init__(self, result_queue: asyncio.Queue):
        """
        初始化回调处理器

        Args:
            result_queue: 异步队列，用于传递识别结果
        """
        self.result_queue = result_queue
        self.loop = asyncio.get_event_loop()

    def on_open(self):
        """连接建立时的回调"""
        logger.info("[ASR] Connection opened")

    def on_event(self, event: dict):
        """接收到事件时的回调

        事件类型:
        - conversation.item.input_audio_transcription.delta: 实时转录片段
        - conversation.item.input_audio_transcription.completed: 转录完成
        - error: 错误事件
        """
        try:
            event_type = event.get("type", "")

            # 实时转录片段
            if event_type == "conversation.item.input_audio_transcription.delta":
                text = event.get("delta", "")
                if text:
                    result = ASRResult(text=text, is_final=False)
                    asyncio.run_coroutine_threadsafe(
                        self.result_queue.put(result), self.loop
                    )

            # 转录完成
            elif event_type == "conversation.item.input_audio_transcription.completed":
                text = event.get("transcript", "")
                if text:
                    result = ASRResult(
                        text=text,
                        is_final=True,
                        sentence_id=event.get("item_id")
                    )
                    asyncio.run_coroutine_threadsafe(
                        self.result_queue.put(result), self.loop
                    )

            # 错误事件
            elif event_type == "error":
                error_msg = event.get("error", {}).get("message", "Unknown error")
                logger.error(f"[ASR] Error: {error_msg}")
                # 发送错误信号
                asyncio.run_coroutine_threadsafe(
                    self.result_queue.put(None), self.loop
                )

        except Exception as e:
            logger.error(f"[ASR] Callback error: {e}")

    def on_close(self):
        """连接关闭时的回调"""
        logger.info("[ASR] Connection closed")
        # 发送结束信号
        asyncio.run_coroutine_threadsafe(
            self.result_queue.put(None), self.loop
        )


class VoiceService:
    """阿里云语音服务封装"""

    def __init__(self):
        """初始化语音服务"""
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            logger.warning("[VoiceService] DASHSCOPE_API_KEY not set - service will not be functional")
        else:
            dashscope.api_key = self.api_key

        # ASR 配置
        self.asr_model = "qwen3-asr-flash-realtime"
        self.asr_endpoint = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"

        # TTS 配置
        self.tts_model = "qwen3-tts-flash"
        self.tts_voice = "zhitian_emo"  # 可选: Dylan, Cherry, zhitian_emo, zhichu_emo 等
        self.tts_sample_rate = 24000

        logger.info("[VoiceService] Initialized with DashScope API")

    async def speech_to_text_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[ASRResult, None]:
        """流式语音识别

        Args:
            audio_stream: 音频流 (PCM 16kHz 16bit 单声道)

        Yields:
            ASRResult: 识别结果，包含文本和是否完成标志

        使用示例:
            async for result in voice_service.speech_to_text_stream(audio_stream):
                print(f"[{'Final' if result.is_final else 'Partial'}] {result.text}")
        """
        if not self.api_key:
            logger.error("[ASR] API key not configured")
            raise ValueError("DASHSCOPE_API_KEY not configured")
        # 创建结果队列
        result_queue: asyncio.Queue = asyncio.Queue()

        # 创建回调处理器
        callback = ASRCallback(result_queue)

        # 创建 ASR 会话
        conversation = OmniRealtimeConversation(
            model=self.asr_model,
            callback=callback,
            url=self.asr_endpoint
        )

        try:
            # 启动音频发送任务
            async def send_audio():
                """发送音频到 ASR"""
                try:
                    async for audio_chunk in audio_stream:
                        # 将音频编码为 base64
                        audio_b64 = base64.b64encode(audio_chunk).decode('ascii')
                        # 发送音频
                        conversation.append_audio(audio_b64)
                        await asyncio.sleep(0.01)  # 防止发送过快

                    # 发送音频结束信号
                    conversation.input_audio_buffer_commit()
                except Exception as e:
                    logger.error(f"[ASR] Error sending audio: {e}")
                    await result_queue.put(None)

            # 启动发送任务
            send_task = asyncio.create_task(send_audio())

            # 从队列中读取识别结果
            while True:
                result = await result_queue.get()

                if result is None:
                    # 结束信号
                    break

                yield result

            # 等待发送任务完成
            await send_task

        except Exception as e:
            logger.error(f"[ASR] Stream error: {e}")
            raise

        finally:
            # 关闭连接
            try:
                conversation.close()
            except Exception:
                pass

    async def text_to_speech_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        language: str = "Chinese"
    ) -> AsyncGenerator[TTSChunk, None]:
        """流式语音合成

        Args:
            text: 要合成的文本
            voice: 语音类型 (默认: longxiaochun for CosyVoice)
                可选: longxiaochun, longxiaoxia, longyue, longwan, longcheng, longhua, longjing, longfei
            language: 语言类型 (Chinese, English, Auto) - 暂未使用

        Yields:
            TTSChunk: 音频块，包含 MP3 音频数据和是否完成标志

        使用示例:
            async for chunk in voice_service.text_to_speech_stream("你好"):
                audio_data = chunk.audio_data  # bytes (MP3)
                # 处理音频数据...
        """
        if not self.api_key:
            logger.error("[TTS] API key not configured")
            raise ValueError("DASHSCOPE_API_KEY not configured")

        if not text or not text.strip():
            logger.warning("[TTS] Empty text provided")
            return

        # 使用 CosyVoice 音色
        cosyvoice_voice = voice if voice and voice.startswith("long") else "longxiaochun"

        loop = asyncio.get_running_loop()

        def tts_worker() -> bytes:
            """在线程中执行同步 TTS API"""
            try:
                from dashscope.audio.tts_v2 import SpeechSynthesizer

                logger.info(f"[TTS] Synthesizing text with CosyVoice: {text[:50]}...")
                synthesizer = SpeechSynthesizer(model='cosyvoice-v1', voice=cosyvoice_voice)
                audio_data = synthesizer.call(text)
                logger.info(f"[TTS] Generated {len(audio_data)} bytes of audio")
                return audio_data
            except Exception as e:
                logger.error(f"[TTS] Worker error: {e}")
                raise

        try:
            # 在线程池中执行同步 TTS
            audio_data = await loop.run_in_executor(None, tts_worker)

            if audio_data:
                # 返回完整的音频数据（MP3格式）
                yield TTSChunk(audio_data=audio_data, is_final=False)

            # 发送结束信号
            yield TTSChunk(audio_data=b"", is_final=True)

        except Exception as e:
            logger.error(f"[TTS] Stream error: {e}")
            raise

    async def text_to_speech_base64(
        self,
        text: str,
        voice: Optional[str] = None,
        language: str = "Chinese"
    ) -> AsyncGenerator[str, None]:
        """流式语音合成 - 返回 base64 编码的音频

        这是为了方便 WebSocket 直接发送而提供的辅助方法

        Args:
            text: 要合成的文本
            voice: 语音类型
            language: 语言类型

        Yields:
            str: base64 编码的音频数据
        """
        async for chunk in self.text_to_speech_stream(text, voice, language):
            if not chunk.is_final and chunk.audio_data:
                # 编码为 base64
                audio_b64 = base64.b64encode(chunk.audio_data).decode('ascii')
                yield audio_b64


# 全局单例
_voice_service: Optional[VoiceService] = None


def get_voice_service() -> VoiceService:
    """获取语音服务单例"""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service


# 导出
voice_service = get_voice_service()
