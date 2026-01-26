"""批量任务管理器 - 基于Redis的异步任务队列"""
import uuid
import json
import asyncio
import base64
from datetime import datetime
from typing import Optional, AsyncGenerator
from enum import Enum
from pydantic import BaseModel, Field
import redis.asyncio as aioredis
from app.config import get_settings


class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"  # 已入队，等待处理
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class FileTask(BaseModel):
    """单个文件任务"""
    file_id: str
    file_name: str
    status: TaskStatus = TaskStatus.PENDING
    status_detail: str = ""  # 详细状态：提取文本、OCR识别、LLM解析、创建向量、保存数据
    progress: int = 0
    result: Optional[dict] = None
    error: Optional[str] = None
    retry_count: int = 0
    llm_output: str = ""  # LLM输出内容
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class BatchTask(BaseModel):
    """批量任务"""
    batch_id: str
    total_files: int
    completed: int = 0
    failed: int = 0
    status: TaskStatus = TaskStatus.PENDING
    files: list[FileTask] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def progress(self) -> int:
        if self.total_files == 0:
            return 0
        return int((self.completed + self.failed) / self.total_files * 100)

    @property
    def success_count(self) -> int:
        return self.completed

    @property
    def processing_count(self) -> int:
        return sum(1 for f in self.files if f.status == TaskStatus.PROCESSING)


class TaskManager:
    """任务管理器"""
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # 重试延迟（秒）
    BATCH_TTL = 86400 * 7  # 批量任务保留7天
    FILE_TTL = 86400  # 文件内容保留24小时（防止处理中断后无法恢复）

    def __init__(self):
        settings = get_settings()
        self.redis_url = f"redis://{settings.redis_host}:{settings.redis_port}"
        self._redis: Optional[aioredis.Redis] = None

    async def get_redis(self) -> aioredis.Redis:
        """获取Redis连接"""
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis

    async def close(self):
        """关闭Redis连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _batch_key(self, batch_id: str) -> str:
        return f"batch:{batch_id}"

    def _file_content_key(self, batch_id: str, file_id: str) -> str:
        return f"file_content:{batch_id}:{file_id}"

    def _queue_key(self) -> str:
        return "batch:queue"

    def _active_batches_key(self) -> str:
        return "batch:active"

    async def create_batch(self, file_names: list[str]) -> BatchTask:
        """创建批量任务"""
        batch_id = str(uuid.uuid4())
        files = [
            FileTask(
                file_id=str(uuid.uuid4()),
                file_name=name,
                status=TaskStatus.QUEUED
            )
            for name in file_names
        ]

        batch = BatchTask(
            batch_id=batch_id,
            total_files=len(file_names),
            status=TaskStatus.QUEUED,
            files=files
        )

        redis = await self.get_redis()

        # 存储批量任务
        await redis.set(
            self._batch_key(batch_id),
            batch.model_dump_json(),
            ex=self.BATCH_TTL
        )

        # 添加到活跃任务集合
        await redis.sadd(self._active_batches_key(), batch_id)

        return batch

    async def store_file_content(self, batch_id: str, file_id: str, content: bytes):
        """存储文件内容到Redis"""
        redis = await self.get_redis()
        # Base64编码存储
        encoded = base64.b64encode(content).decode('utf-8')
        await redis.set(
            self._file_content_key(batch_id, file_id),
            encoded,
            ex=self.FILE_TTL
        )

    async def get_file_content(self, batch_id: str, file_id: str) -> Optional[bytes]:
        """获取文件内容"""
        redis = await self.get_redis()
        data = await redis.get(self._file_content_key(batch_id, file_id))
        if data:
            return base64.b64decode(data)
        return None

    async def delete_file_content(self, batch_id: str, file_id: str):
        """删除文件内容"""
        redis = await self.get_redis()
        await redis.delete(self._file_content_key(batch_id, file_id))

    async def enqueue_batch(self, batch_id: str):
        """将批量任务加入处理队列"""
        redis = await self.get_redis()
        await redis.lpush(self._queue_key(), batch_id)

    async def dequeue_batch(self, timeout: int = 5) -> Optional[str]:
        """从队列取出批量任务"""
        redis = await self.get_redis()
        result = await redis.brpop(self._queue_key(), timeout=timeout)
        if result:
            return result[1]
        return None

    async def get_batch(self, batch_id: str) -> Optional[BatchTask]:
        """获取批量任务状态"""
        redis = await self.get_redis()
        data = await redis.get(self._batch_key(batch_id))
        if data:
            return BatchTask.model_validate_json(data)
        return None

    async def get_all_batches(self) -> list[BatchTask]:
        """获取所有活跃的批量任务"""
        redis = await self.get_redis()
        batch_ids = await redis.smembers(self._active_batches_key())

        batches = []
        for batch_id in batch_ids:
            batch = await self.get_batch(batch_id)
            if batch:
                batches.append(batch)
            else:
                # 清理已过期的batch_id
                await redis.srem(self._active_batches_key(), batch_id)

        # 按创建时间倒序排列
        batches.sort(key=lambda b: b.created_at, reverse=True)
        return batches

    async def update_batch(self, batch: BatchTask):
        """更新批量任务"""
        batch.updated_at = datetime.now()
        redis = await self.get_redis()
        await redis.set(
            self._batch_key(batch.batch_id),
            batch.model_dump_json(),
            ex=self.BATCH_TTL
        )

    async def update_file_status(
        self,
        batch_id: str,
        file_id: str,
        status: TaskStatus,
        progress: int = 0,
        result: dict = None,
        error: str = None,
        llm_output: str = None,
        status_detail: str = None
    ):
        """更新单个文件任务状态"""
        batch = await self.get_batch(batch_id)
        if not batch:
            return

        for file_task in batch.files:
            if file_task.file_id == file_id:
                file_task.status = status
                file_task.progress = progress
                file_task.updated_at = datetime.now()

                if status_detail:
                    file_task.status_detail = status_detail
                if result:
                    file_task.result = result
                if error:
                    file_task.error = error
                if llm_output:
                    file_task.llm_output = llm_output

                # 更新统计
                if status == TaskStatus.SUCCESS:
                    batch.completed = sum(1 for f in batch.files if f.status == TaskStatus.SUCCESS)
                    # 删除已处理的文件内容
                    await self.delete_file_content(batch_id, file_id)
                elif status == TaskStatus.FAILED:
                    batch.failed = sum(1 for f in batch.files if f.status == TaskStatus.FAILED)

                # 更新整体状态
                if batch.completed + batch.failed >= batch.total_files:
                    batch.status = TaskStatus.SUCCESS if batch.failed == 0 else TaskStatus.FAILED
                else:
                    batch.status = TaskStatus.PROCESSING

                break

        await self.update_batch(batch)

    async def append_llm_output(self, batch_id: str, file_id: str, chunk: str):
        """追加LLM输出"""
        batch = await self.get_batch(batch_id)
        if not batch:
            return

        for file_task in batch.files:
            if file_task.file_id == file_id:
                file_task.llm_output += chunk
                file_task.updated_at = datetime.now()
                break

        await self.update_batch(batch)

    async def retry_file(self, batch_id: str, file_id: str) -> bool:
        """重试失败的文件"""
        batch = await self.get_batch(batch_id)
        if not batch:
            return False

        for file_task in batch.files:
            if file_task.file_id == file_id:
                if file_task.retry_count >= self.MAX_RETRIES:
                    return False

                file_task.status = TaskStatus.RETRYING
                file_task.retry_count += 1
                file_task.error = None
                file_task.llm_output = ""
                file_task.updated_at = datetime.now()

                # 减少失败计数
                batch.failed = max(0, batch.failed - 1)
                batch.status = TaskStatus.PROCESSING

                await self.update_batch(batch)
                return True

        return False

    async def retry_all_failed(self, batch_id: str) -> int:
        """重试所有失败的文件"""
        batch = await self.get_batch(batch_id)
        if not batch:
            return 0

        retry_count = 0
        for file_task in batch.files:
            if file_task.status == TaskStatus.FAILED and file_task.retry_count < self.MAX_RETRIES:
                file_task.status = TaskStatus.RETRYING
                file_task.retry_count += 1
                file_task.error = None
                file_task.llm_output = ""
                file_task.updated_at = datetime.now()
                retry_count += 1

        if retry_count > 0:
            batch.failed = max(0, batch.failed - retry_count)
            batch.status = TaskStatus.PROCESSING
            await self.update_batch(batch)

            # 重新入队
            await self.enqueue_batch(batch_id)

        return retry_count

    async def delete_batch(self, batch_id: str) -> bool:
        """删除批量任务"""
        redis = await self.get_redis()

        # 获取批量任务以删除文件内容
        batch = await self.get_batch(batch_id)
        if batch:
            for file_task in batch.files:
                await self.delete_file_content(batch_id, file_task.file_id)

        # 删除批量任务
        await redis.delete(self._batch_key(batch_id))
        # 从活跃列表中移除
        await redis.srem(self._active_batches_key(), batch_id)
        return True


# 全局任务管理器实例
task_manager = TaskManager()
