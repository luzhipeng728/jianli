"""Qwen-Omni HTTP 客户端

使用 Qwen-Omni 模型直接理解音频，效果比 ASR + LLM 更好。
支持流式输出文本和音频。

参考文档:
- https://help.aliyun.com/zh/model-studio/qwen-omni
- https://www.alibabacloud.com/help/en/model-studio/qwen-omni
"""

import os
import json
import base64
import asyncio
import httpx
from typing import AsyncGenerator, Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class OmniResponse:
    """Omni 响应数据"""
    text: str = ""
    audio_base64: str = ""
    is_complete: bool = False


class QwenOmniClient:
    """Qwen-Omni HTTP 客户端

    直接发送音频给 Qwen-Omni，获得更好的理解效果。
    支持流式输出文本和音频。
    """

    # OpenAI 兼容 API 端点
    API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    # 支持的模型
    MODELS = {
        "qwen-omni-turbo": "qwen-omni-turbo",  # 较快
        "qwen-omni-turbo-latest": "qwen-omni-turbo-latest",
        "qwen3-omni-flash": "qwen3-omni-flash",  # 最新flash
    }

    # 支持的音色
    VOICES = {
        "Cherry": "温柔女声",
        "Serena": "知性女声",
        "Ethan": "沉稳男声",
        "Chelsie": "活泼女声",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen-omni-turbo",
        voice: str = "Cherry",
    ):
        """初始化客户端

        Args:
            api_key: DashScope API Key
            model: 模型名称
            voice: 音色名称
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY not configured")

        self.model = model
        self.voice = voice

    async def chat_with_audio(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
        system_prompt: str = "",
        history: list[dict] = None,
        output_audio: bool = True,
    ) -> AsyncGenerator[OmniResponse, None]:
        """发送音频进行对话（流式）

        Args:
            audio_data: 音频二进制数据
            audio_format: 音频格式 (wav, mp3, etc.)
            system_prompt: 系统提示词
            history: 对话历史
            output_audio: 是否输出音频

        Yields:
            OmniResponse: 流式响应（文本和音频）
        """
        # 编码音频为 base64
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')

        # 构建消息
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        # 添加历史消息
        if history:
            for msg in history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

        # 添加当前音频消息
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": f"data:;base64,{audio_b64}",
                        "format": audio_format
                    }
                }
            ]
        })

        # 构建请求体
        request_body = {
            "model": self.model,
            "messages": messages,
            "stream": True,  # 必须流式
            "stream_options": {"include_usage": True},
        }

        # 如果需要音频输出
        if output_audio:
            request_body["modalities"] = ["text", "audio"]
            request_body["audio"] = {
                "voice": self.voice,
                "format": "wav"
            }
        else:
            request_body["modalities"] = ["text"]

        # 发送请求
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                self.API_URL,
                headers=headers,
                json=request_body,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"[OmniClient] API error: {response.status_code} - {error_text}")
                    return

                # 解析 SSE 流
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        yield OmniResponse(is_complete=True)
                        break

                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])

                        if not choices:
                            # 可能是 usage 信息或其他非内容消息
                            continue

                        choice = choices[0]
                        delta = choice.get("delta", {})

                        response_obj = OmniResponse()

                        # 提取文本
                        if "content" in delta:
                            response_obj.text = delta["content"] or ""

                        # 提取音频
                        if "audio" in delta:
                            audio_delta = delta["audio"]
                            if "data" in audio_delta:
                                response_obj.audio_base64 = audio_delta["data"]

                        if response_obj.text or response_obj.audio_base64:
                            yield response_obj

                    except json.JSONDecodeError as e:
                        print(f"[OmniClient] JSON parse error: {e}")
                        continue
                    except Exception as e:
                        print(f"[OmniClient] Parse error: {e}, data: {data_str[:200]}")
                        continue

    async def chat_with_audio_text_only(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
        system_prompt: str = "",
        history: list[dict] = None,
    ) -> AsyncGenerator[str, None]:
        """发送音频，只获取文本回复（流式）

        Args:
            audio_data: 音频二进制数据
            audio_format: 音频格式
            system_prompt: 系统提示词
            history: 对话历史

        Yields:
            str: 文本片段
        """
        async for response in self.chat_with_audio(
            audio_data=audio_data,
            audio_format=audio_format,
            system_prompt=system_prompt,
            history=history,
            output_audio=False,
        ):
            if response.text:
                yield response.text


# 全局实例
_omni_client: Optional[QwenOmniClient] = None


def get_omni_client() -> QwenOmniClient:
    """获取 Qwen-Omni 客户端实例"""
    global _omni_client
    if _omni_client is None:
        _omni_client = QwenOmniClient()
    return _omni_client
