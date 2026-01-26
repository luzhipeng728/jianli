import asyncio
import dashscope
from dashscope import Generation, TextEmbedding
from typing import AsyncGenerator, Callable, Any, Optional
from dataclasses import dataclass
from app.config import get_settings


@dataclass
class QueueTask:
    """队列任务"""
    task_id: str
    func: Callable
    args: tuple
    kwargs: dict
    future: asyncio.Future
    retry_count: int = 0
    max_retries: int = 10


class AsyncRequestQueue:
    """异步请求队列 - 控制并发数量，自动重试"""

    def __init__(self, name: str, max_concurrent: int = 5, max_retries: int = 10):
        self.name = name
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self._queue: asyncio.Queue[QueueTask] = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._task_counter = 0
        self._active_count = 0
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def start(self):
        """启动队列工作器"""
        if self._running:
            return
        self._running = True
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        print(f"[Queue:{self.name}] 启动，最大并发: {self.max_concurrent}")

    async def stop(self):
        """停止队列"""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        self._workers.clear()
        print(f"[Queue:{self.name}] 已停止")

    async def submit(self, func: Callable, *args, **kwargs) -> Any:
        """提交任务到队列并等待结果"""
        if not self._running:
            await self.start()

        self._task_counter += 1
        task_id = f"{self.name}-{self._task_counter}"

        loop = asyncio.get_event_loop()
        future = loop.create_future()

        task = QueueTask(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            future=future,
            max_retries=self.max_retries
        )

        # 使用信号量控制并发
        async with self._semaphore:
            self._active_count += 1
            try:
                result = await self._execute_task(task)
                return result
            finally:
                self._active_count -= 1

    async def _execute_task(self, task: QueueTask) -> Any:
        """执行单个任务，支持重试"""
        last_error = None

        for attempt in range(task.max_retries):
            try:
                # 执行任务
                if asyncio.iscoroutinefunction(task.func):
                    result = await task.func(*task.args, **task.kwargs)
                else:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, lambda: task.func(*task.args, **task.kwargs))

                return result

            except Exception as e:
                last_error = e
                error_str = str(e)

                # 判断是否是限流错误
                is_rate_limit = "429" in error_str or "rate" in error_str.lower()

                if attempt < task.max_retries - 1:
                    # 计算等待时间：限流错误递增等待，其他错误固定等待
                    if is_rate_limit:
                        wait_time = 2 * (attempt + 1)  # 2, 4, 6, 8...
                        print(f"[Queue:{self.name}] 任务 {task.task_id} 限流，等待 {wait_time}s 后重试 ({attempt + 1}/{task.max_retries})")
                    else:
                        wait_time = 1
                        print(f"[Queue:{self.name}] 任务 {task.task_id} 错误: {error_str}，重试 ({attempt + 1}/{task.max_retries})")

                    await asyncio.sleep(wait_time)
                else:
                    print(f"[Queue:{self.name}] 任务 {task.task_id} 重试 {task.max_retries} 次后失败: {error_str}")

        raise last_error if last_error else Exception("任务执行失败")

    @property
    def pending_count(self) -> int:
        """等待中的任务数"""
        return self._queue.qsize()

    @property
    def active_count(self) -> int:
        """正在执行的任务数"""
        return self._active_count


# 全局队列实例
_embedding_queue: Optional[AsyncRequestQueue] = None
_llm_queue: Optional[AsyncRequestQueue] = None


def get_embedding_queue() -> AsyncRequestQueue:
    """获取 embedding 队列（懒加载）"""
    global _embedding_queue
    if _embedding_queue is None:
        _embedding_queue = AsyncRequestQueue("embedding", max_concurrent=5, max_retries=10)
    return _embedding_queue


def get_llm_queue() -> AsyncRequestQueue:
    """获取 LLM 队列（懒加载）"""
    global _llm_queue
    if _llm_queue is None:
        _llm_queue = AsyncRequestQueue("llm", max_concurrent=10, max_retries=10)
    return _llm_queue


class LLMClient:
    # 主模型和备用模型
    PRIMARY_MODEL = "qwen-plus"
    FALLBACK_MODEL = "qwen-turbo"  # 429时切换到更快的模型
    STREAM_TIMEOUT = 120  # 流式调用超时时间（秒）
    MAX_RETRIES = 10  # 最大重试次数

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.dashscope_api_key
        dashscope.api_key = self.api_key
        self.model = self.PRIMARY_MODEL
        self._use_fallback = False  # 是否使用备用模型

    def _get_current_model(self) -> str:
        """获取当前使用的模型"""
        return self.FALLBACK_MODEL if self._use_fallback else self.PRIMARY_MODEL

    def _switch_to_fallback(self):
        """切换到备用模型"""
        if not self._use_fallback:
            self._use_fallback = True
            print(f"[LLM] 429限流，切换到备用模型: {self.FALLBACK_MODEL}")

    def _reset_to_primary(self):
        """重置为主模型"""
        self._use_fallback = False

    async def chat(self, prompt: str, system_prompt: str = "") -> str:
        """异步对话 - 在线程池中执行同步API调用，支持429自动切换模型"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        loop = asyncio.get_event_loop()
        current_model = self._get_current_model()

        def sync_call(model: str):
            response = Generation.call(
                model=model,
                messages=messages,
                result_format="message",
            )
            return response

        # 第一次尝试
        response = await loop.run_in_executor(None, lambda: sync_call(current_model))

        # 如果429限流，切换模型重试
        if response.status_code == 429:
            self._switch_to_fallback()
            fallback_model = self._get_current_model()
            response = await loop.run_in_executor(None, lambda: sync_call(fallback_model))

        if response.status_code == 200:
            return response.output.choices[0].message.content
        return ""

    async def chat_async(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7
    ) -> str:
        """异步对话 - 支持完整的消息列表格式"""
        loop = asyncio.get_event_loop()

        def sync_call():
            response = Generation.call(
                model=self.model,
                messages=messages,
                result_format="message",
                temperature=temperature,
            )
            if response.status_code == 200:
                return response.output.choices[0].message.content
            return ""

        return await loop.run_in_executor(None, sync_call)

    async def chat_stream(
        self, prompt: str, system_prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        """流式对话 - 真正的异步流式输出"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async for chunk in self.chat_stream_messages(messages):
            yield chunk

    async def chat_stream_messages(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        model: str = None
    ) -> AsyncGenerator[str, None]:
        """流式对话 - 支持完整的消息列表格式，429自动切换模型，支持重试"""
        loop = asyncio.get_event_loop()

        for attempt in range(self.MAX_RETRIES):
            queue: asyncio.Queue[str | None | dict] = asyncio.Queue()
            use_model = model or self._get_current_model()
            has_output = False

            def stream_worker(target_model: str):
                """在线程中运行同步的流式API"""
                try:
                    responses = Generation.call(
                        model=target_model,
                        messages=messages,
                        result_format="message",
                        stream=True,
                        incremental_output=True,
                        temperature=temperature,
                    )

                    for response in responses:
                        if response.status_code == 200:
                            content = response.output.choices[0].message.content
                            if content:
                                asyncio.run_coroutine_threadsafe(
                                    queue.put(content), loop
                                )
                        elif response.status_code == 429:
                            asyncio.run_coroutine_threadsafe(
                                queue.put({"error": 429}), loop
                            )
                            return
                except Exception as e:
                    print(f"[LLM] Stream error: {e}")
                    asyncio.run_coroutine_threadsafe(
                        queue.put({"error": "exception", "msg": str(e)}), loop
                    )
                finally:
                    asyncio.run_coroutine_threadsafe(queue.put(None), loop)

            loop.run_in_executor(None, lambda m=use_model: stream_worker(m))

            try:
                while True:
                    try:
                        chunk = await asyncio.wait_for(queue.get(), timeout=self.STREAM_TIMEOUT)
                    except asyncio.TimeoutError:
                        if has_output:
                            # 已有输出但超时，可能是正常结束
                            break
                        raise

                    if chunk is None:
                        return  # 正常结束
                    if isinstance(chunk, dict):
                        if chunk.get("error") == 429:
                            print(f"[LLM] 429限流，切换模型重试 {attempt + 1}/{self.MAX_RETRIES}")
                            self._switch_to_fallback()
                            break  # 跳出内层循环，重试
                        elif chunk.get("error") == "exception":
                            print(f"[LLM] 异常，重试 {attempt + 1}/{self.MAX_RETRIES}")
                            break
                    else:
                        has_output = True
                        yield chunk

                if has_output:
                    return  # 有输出就算成功

            except asyncio.TimeoutError:
                print(f"[LLM] 流式调用超时，重试 {attempt + 1}/{self.MAX_RETRIES}")

            if attempt < self.MAX_RETRIES - 1:
                wait_time = 2 * (attempt + 1)  # 递增等待: 2秒, 4秒, 6秒...
                print(f"[LLM] 等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)

        raise TimeoutError(f"LLM调用重试 {self.MAX_RETRIES} 次后失败")

    async def ocr(self, image_data: bytes, filename: str = "image.png") -> str:
        """使用Qwen-VL-OCR进行图片文字识别

        支持两种方式：
        1. 传入图片URL
        2. 传入图片二进制数据（会先转为base64）
        """
        import base64
        from dashscope import MultiModalConversation

        loop = asyncio.get_event_loop()

        def sync_ocr():
            # 将图片转为 base64 data URL
            ext = filename.split('.')[-1].lower()
            mime_map = {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'webp': 'webp', 'bmp': 'bmp'}
            mime_type = mime_map.get(ext, 'png')
            b64_data = base64.b64encode(image_data).decode('utf-8')
            image_url = f"data:image/{mime_type};base64,{b64_data}"

            messages = [{
                "role": "user",
                "content": [
                    {
                        "image": image_url,
                        "min_pixels": 28 * 28 * 4,
                        "max_pixels": 28 * 28 * 8192,
                    },
                    {"text": "请识别图片中的所有文字内容，保持原有格式和布局。"}
                ]
            }]

            response = MultiModalConversation.call(
                api_key=self.api_key,
                model="qwen-vl-ocr-latest",
                messages=messages,
            )

            if response.status_code == 200:
                # 提取文字内容
                content = response.output.choices[0].message.content
                if isinstance(content, list):
                    # 可能返回的是列表格式
                    text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
                    return "\n".join(text_parts)
                return content
            else:
                print(f"OCR error: {response.code} - {response.message}")
                return ""

        return await loop.run_in_executor(None, sync_ocr)

    async def get_embedding(self, text: str, text_type: str = "document", max_retries: int = 10) -> list[float]:
        """获取文本向量 (使用 text-embedding-v3)，通过队列控制并发

        Args:
            text: 要向量化的文本
            text_type: 'document' 用于存储, 'query' 用于搜索
            max_retries: 最大重试次数
        Returns:
            1024维向量
        """
        api_key = self.api_key
        truncated_text = text[:8000]

        def sync_embedding():
            response = TextEmbedding.call(
                api_key=api_key,
                model="text-embedding-v3",
                input=[truncated_text],
                dimension=1024,
                text_type=text_type,
            )
            if response.status_code == 200:
                return response.output["embeddings"][0]["embedding"]
            elif response.status_code == 429:
                raise Exception("429_RATE_LIMIT")
            else:
                raise Exception(f"Embedding error: {response.code} - {response.message}")

        # 使用队列提交任务
        queue = get_embedding_queue()
        try:
            result = await asyncio.wait_for(
                queue.submit(sync_embedding),
                timeout=60  # 总超时60秒（包含重试时间）
            )
            return result if result else []
        except asyncio.TimeoutError:
            print(f"[LLM] Embedding 队列超时")
            return []
        except Exception as e:
            print(f"[LLM] Embedding 最终失败: {e}")
            return []

    async def get_embeddings_batch(self, texts: list[str], text_type: str = "document") -> list[list[float]]:
        """批量获取文本向量，通过队列控制并发"""
        api_key = self.api_key
        truncated = [t[:8000] for t in texts]

        def sync_batch():
            response = TextEmbedding.call(
                api_key=api_key,
                model="text-embedding-v3",
                input=truncated,
                dimension=1024,
                text_type=text_type,
            )
            if response.status_code == 200:
                return [e["embedding"] for e in response.output["embeddings"]]
            elif response.status_code == 429:
                raise Exception("429_RATE_LIMIT")
            else:
                raise Exception(f"Batch embedding error: {response.code} - {response.message}")

        # 使用队列提交任务
        queue = get_embedding_queue()
        try:
            result = await asyncio.wait_for(
                queue.submit(sync_batch),
                timeout=120  # 批量操作超时更长
            )
            return result if result else []
        except asyncio.TimeoutError:
            print(f"[LLM] Batch embedding 队列超时")
            return []
        except Exception as e:
            print(f"[LLM] Batch embedding 最终失败: {e}")
            return []
