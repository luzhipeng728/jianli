"""Qwen-Omni HTTP API 服务

使用 HTTP API 而非 WebSocket 调用 Qwen-Omni 模型。
优势：
- 无 VAD 问题，用户可以任意停顿思考
- 无连接超时问题
- 单次录音最长 20 分钟
"""

import os
import json
import base64
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import httpx

@dataclass
class OmniResponse:
    """Omni API 响应"""
    text: str  # AI 回复文本
    audio_base64: Optional[str] = None  # AI 回复音频 (base64)
    audio_format: str = "wav"


class OmniHttpService:
    """Qwen-Omni HTTP API 服务"""

    # API 配置
    API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    MODEL = "qwen-omni-turbo"  # 使用 turbo 版本，响应更快

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY not configured")

    async def chat_with_audio(
        self,
        audio_base64: str,
        audio_format: str = "wav",
        system_prompt: str = "",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        voice: str = "Cherry",
        enable_audio_output: bool = True,
    ) -> OmniResponse:
        """发送音频并获取 AI 回复

        Args:
            audio_base64: 用户音频的 base64 编码
            audio_format: 音频格式 (wav, mp3, pcm 等)
            system_prompt: 系统提示词
            conversation_history: 对话历史
            voice: AI 回复的音色
            enable_audio_output: 是否生成语音回复

        Returns:
            OmniResponse: 包含文本和音频的响应
        """
        # 构建消息
        messages = []

        # 系统提示
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        # 对话历史
        if conversation_history:
            messages.extend(conversation_history)

        # 用户音频输入
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": f"data:audio/{audio_format};base64,{audio_base64}",
                        "format": audio_format
                    }
                }
            ]
        })

        # 构建请求体
        request_body = {
            "model": self.MODEL,
            "messages": messages,
            "stream": True,  # Qwen-Omni 只支持流式输出
            "stream_options": {"include_usage": True}
        }

        # 如果需要音频输出
        if enable_audio_output:
            request_body["modalities"] = ["text", "audio"]
            request_body["audio"] = {
                "voice": voice,
                "format": "wav"
            }
        else:
            request_body["modalities"] = ["text"]

        # 发送请求
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        text_response = ""
        audio_chunks = []

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                self.API_URL,
                headers=headers,
                json=request_body
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"API error {response.status_code}: {error_text.decode()}")

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:]  # 去掉 "data: " 前缀
                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)

                        if "choices" in data and len(data["choices"]) > 0:
                            choice = data["choices"][0]
                            delta = choice.get("delta", {})

                            # 文本内容
                            if "content" in delta and delta["content"]:
                                text_response += delta["content"]

                            # 音频内容
                            if "audio" in delta:
                                audio_data = delta["audio"]
                                if "data" in audio_data and audio_data["data"]:
                                    audio_chunks.append(audio_data["data"])

                    except json.JSONDecodeError:
                        continue

        # 合并音频
        audio_base64_response = None
        if audio_chunks:
            audio_base64_response = "".join(audio_chunks)

        return OmniResponse(
            text=text_response,
            audio_base64=audio_base64_response,
            audio_format="wav"
        )

    async def text_to_speech(
        self,
        text: str,
        voice: str = "Cherry"
    ) -> Optional[str]:
        """文本转语音

        Args:
            text: 要转换的文本
            voice: 音色

        Returns:
            音频的 base64 编码
        """
        messages = [
            {
                "role": "user",
                "content": text
            }
        ]

        request_body = {
            "model": self.MODEL,
            "messages": messages,
            "modalities": ["text", "audio"],
            "audio": {
                "voice": voice,
                "format": "wav"
            },
            "stream": True,
            "stream_options": {"include_usage": True}
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        audio_chunks = []

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                self.API_URL,
                headers=headers,
                json=request_body
            ) as response:
                if response.status_code != 200:
                    return None

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            if "audio" in delta and "data" in delta["audio"]:
                                audio_chunks.append(delta["audio"]["data"])
                    except json.JSONDecodeError:
                        continue

        if audio_chunks:
            return "".join(audio_chunks)
        return None


# 全局服务实例
_omni_http_service: Optional[OmniHttpService] = None

def get_omni_http_service() -> OmniHttpService:
    """获取 Omni HTTP 服务实例"""
    global _omni_http_service
    if _omni_http_service is None:
        _omni_http_service = OmniHttpService()
    return _omni_http_service
