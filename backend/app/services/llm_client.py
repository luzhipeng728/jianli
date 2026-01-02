import dashscope
from dashscope import Generation
from typing import AsyncGenerator
from app.config import get_settings

class LLMClient:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.dashscope_api_key
        dashscope.api_key = self.api_key
        self.model = "qwen-max"  # 或 qwen3-32b

    async def chat(self, prompt: str, system_prompt: str = "") -> str:
        """同步对话"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = Generation.call(
            model=self.model,
            messages=messages,
            result_format="message",
        )

        if response.status_code == 200:
            return response.output.choices[0].message.content
        return ""

    async def chat_stream(
        self, prompt: str, system_prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        responses = Generation.call(
            model=self.model,
            messages=messages,
            result_format="message",
            stream=True,
            incremental_output=True,
        )

        for response in responses:
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                if content:
                    yield content

    async def ocr(self, image_url: str) -> str:
        """使用Qwen-VL-OCR进行图片文字识别"""
        messages = [{
            "role": "user",
            "content": [
                {"image": image_url},
                {"text": "请识别图片中的所有文字内容，保持原有格式。"}
            ]
        }]

        response = Generation.call(
            model="qwen-vl-ocr",
            messages=messages,
        )

        if response.status_code == 200:
            return response.output.choices[0].message.content
        return ""
