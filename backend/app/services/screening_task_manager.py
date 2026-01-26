"""AI筛选任务管理器 - 基于Redis的异步任务队列"""
import uuid
import json
import asyncio
import base64
from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from app.config import get_settings


class ScreeningStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class ResumeScreeningTask(BaseModel):
    """单个简历筛选任务"""
    resume_id: str
    resume_name: str  # 候选人姓名
    status: ScreeningStatus = ScreeningStatus.PENDING
    status_detail: str = ""  # 详细状态：读取简历、AI评分中、保存结果
    progress: int = 0
    match_score: Optional[int] = None
    skill_score: Optional[int] = None
    experience_score: Optional[int] = None
    education_score: Optional[int] = None
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ScreeningBatch(BaseModel):
    """筛选批量任务"""
    batch_id: str
    jd_id: str
    jd_title: str
    total_resumes: int
    completed: int = 0
    failed: int = 0
    skipped: int = 0  # 已有分数的跳过数量
    status: ScreeningStatus = ScreeningStatus.PENDING
    min_score: int = 0  # 最低匹配分数过滤
    resumes: list[ResumeScreeningTask] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def progress(self) -> int:
        if self.total_resumes == 0:
            return 0
        return int((self.completed + self.failed + self.skipped) / self.total_resumes * 100)

    @property
    def processing_count(self) -> int:
        return sum(1 for r in self.resumes if r.status == ScreeningStatus.PROCESSING)


class ScreeningTaskManager:
    """筛选任务管理器"""
    BATCH_TTL = 86400 * 7  # 批量任务保留7天
    MATCH_TTL = 86400 * 30  # 匹配结果保留30天
    LOCK_TTL = 10  # 锁超时时间（秒）

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

    def _batch_lock_key(self, batch_id: str) -> str:
        """批量任务锁的key"""
        return f"lock:screening:{batch_id}"

    @asynccontextmanager
    async def batch_lock(self, batch_id: str, timeout: float = 5.0):
        """分布式锁 - 防止并发更新批量任务"""
        redis = await self.get_redis()
        lock_key = self._batch_lock_key(batch_id)
        lock_value = str(uuid.uuid4())

        # 尝试获取锁，带重试
        acquired = False
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            acquired = await redis.set(lock_key, lock_value, nx=True, ex=self.LOCK_TTL)
            if acquired:
                break
            await asyncio.sleep(0.05)  # 50ms重试间隔

        if not acquired:
            # 超时后强制获取锁（防止死锁）
            await redis.set(lock_key, lock_value, ex=self.LOCK_TTL)
            acquired = True

        try:
            yield acquired
        finally:
            # 只删除自己的锁
            current = await redis.get(lock_key)
            if current == lock_value:
                await redis.delete(lock_key)

    def _batch_key(self, batch_id: str) -> str:
        return f"screening:{batch_id}"

    def _queue_key(self) -> str:
        return "screening:queue"

    def _active_batches_key(self) -> str:
        return "screening:active"

    def _match_key(self, jd_id: str, resume_id: str) -> str:
        """JD-简历匹配结果的key"""
        return f"match:{jd_id}:{resume_id}"

    def _jd_matches_key(self, jd_id: str) -> str:
        """JD下所有匹配结果的集合key"""
        return f"jd_matches:{jd_id}"

    async def create_batch(
        self,
        jd_id: str,
        jd_title: str,
        resumes: list[dict],
        min_score: int = 0
    ) -> ScreeningBatch:
        """创建筛选批量任务"""
        batch_id = str(uuid.uuid4())

        # 检查哪些简历已经有匹配分数
        redis = await self.get_redis()
        resume_tasks = []
        skipped = 0

        for resume in resumes:
            resume_id = resume["id"]
            # 检查是否已有匹配结果
            existing = await self.get_match_result(jd_id, resume_id)
            if existing:
                # 已有结果，跳过
                skipped += 1
                resume_tasks.append(ResumeScreeningTask(
                    resume_id=resume_id,
                    resume_name=resume.get("name", "未知"),
                    status=ScreeningStatus.SUCCESS,
                    progress=100,
                    match_score=existing.get("match_score"),
                    skill_score=existing.get("skill_score"),
                    experience_score=existing.get("experience_score"),
                    education_score=existing.get("education_score"),
                    matched_skills=existing.get("matched_skills", []),
                    missing_skills=existing.get("missing_skills", []),
                    highlights=existing.get("highlights", []),
                    concerns=existing.get("concerns", []),
                ))
            else:
                resume_tasks.append(ResumeScreeningTask(
                    resume_id=resume_id,
                    resume_name=resume.get("name", "未知"),
                    status=ScreeningStatus.QUEUED
                ))

        batch = ScreeningBatch(
            batch_id=batch_id,
            jd_id=jd_id,
            jd_title=jd_title,
            total_resumes=len(resumes),
            completed=skipped,  # 已有分数的算完成
            skipped=skipped,
            status=ScreeningStatus.QUEUED,
            min_score=min_score,
            resumes=resume_tasks
        )

        # 存储批量任务
        await redis.set(
            self._batch_key(batch_id),
            batch.model_dump_json(),
            ex=self.BATCH_TTL
        )

        # 添加到活跃任务集合
        await redis.sadd(self._active_batches_key(), batch_id)

        return batch

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

    async def get_batch(self, batch_id: str) -> Optional[ScreeningBatch]:
        """获取批量任务状态"""
        redis = await self.get_redis()
        data = await redis.get(self._batch_key(batch_id))
        if data:
            return ScreeningBatch.model_validate_json(data)
        return None

    async def get_active_batch_for_jd(self, jd_id: str) -> Optional[ScreeningBatch]:
        """获取JD的活跃筛选任务"""
        redis = await self.get_redis()
        batch_ids = await redis.smembers(self._active_batches_key())

        for batch_id in batch_ids:
            batch = await self.get_batch(batch_id)
            if batch and batch.jd_id == jd_id:
                if batch.status in [ScreeningStatus.PENDING, ScreeningStatus.QUEUED, ScreeningStatus.PROCESSING]:
                    return batch
        return None

    async def update_batch(self, batch: ScreeningBatch):
        """更新批量任务"""
        batch.updated_at = datetime.now()
        redis = await self.get_redis()
        await redis.set(
            self._batch_key(batch.batch_id),
            batch.model_dump_json(),
            ex=self.BATCH_TTL
        )

    async def update_resume_status(
        self,
        batch_id: str,
        resume_id: str,
        status: ScreeningStatus,
        progress: int = 0,
        match_result: dict = None,
        error: str = None,
        status_detail: str = None
    ):
        """更新单个简历筛选状态（使用分布式锁防止并发冲突）"""
        # 先保存匹配结果（这个操作是幂等的，不需要锁）
        if match_result:
            batch = await self.get_batch(batch_id)
            if batch:
                await self.save_match_result(batch.jd_id, resume_id, match_result)

        # 使用分布式锁更新批量任务状态
        async with self.batch_lock(batch_id):
            batch = await self.get_batch(batch_id)
            if not batch:
                return

            for task in batch.resumes:
                if task.resume_id == resume_id:
                    task.status = status
                    task.progress = progress
                    task.updated_at = datetime.now()

                    if status_detail:
                        task.status_detail = status_detail

                    if error:
                        task.error = error

                    if match_result:
                        task.match_score = match_result.get("match_score")
                        task.skill_score = match_result.get("skill_score")
                        task.experience_score = match_result.get("experience_score")
                        task.education_score = match_result.get("education_score")
                        task.matched_skills = match_result.get("matched_skills", [])
                        task.missing_skills = match_result.get("missing_skills", [])
                        task.highlights = match_result.get("highlights", [])
                        task.concerns = match_result.get("concerns", [])

                    # 更新统计
                    if status == ScreeningStatus.SUCCESS:
                        batch.completed = sum(1 for r in batch.resumes if r.status == ScreeningStatus.SUCCESS)
                    elif status == ScreeningStatus.FAILED:
                        batch.failed = sum(1 for r in batch.resumes if r.status == ScreeningStatus.FAILED)

                    # 更新整体状态
                    if batch.completed + batch.failed + batch.skipped >= batch.total_resumes:
                        batch.status = ScreeningStatus.SUCCESS if batch.failed == 0 else ScreeningStatus.FAILED
                    else:
                        batch.status = ScreeningStatus.PROCESSING

                    break

            await self.update_batch(batch)

    async def save_match_result(self, jd_id: str, resume_id: str, result: dict):
        """保存JD-简历匹配结果"""
        redis = await self.get_redis()
        key = self._match_key(jd_id, resume_id)

        # 添加时间戳
        result["jd_id"] = jd_id
        result["resume_id"] = resume_id
        result["created_at"] = datetime.now().isoformat()

        await redis.set(key, json.dumps(result), ex=self.MATCH_TTL)

        # 添加到JD的匹配集合
        await redis.sadd(self._jd_matches_key(jd_id), resume_id)

    async def get_match_result(self, jd_id: str, resume_id: str) -> Optional[dict]:
        """获取JD-简历匹配结果"""
        redis = await self.get_redis()
        data = await redis.get(self._match_key(jd_id, resume_id))
        if data:
            return json.loads(data)
        return None

    async def get_jd_all_matches(self, jd_id: str, min_score: int = 0) -> list[dict]:
        """获取JD的所有匹配结果"""
        redis = await self.get_redis()
        resume_ids = await redis.smembers(self._jd_matches_key(jd_id))

        results = []
        for resume_id in resume_ids:
            result = await self.get_match_result(jd_id, resume_id)
            if result and result.get("match_score", 0) >= min_score:
                results.append(result)

        # 按分数排序
        results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return results

    async def delete_batch(self, batch_id: str) -> bool:
        """删除批量任务"""
        redis = await self.get_redis()
        await redis.delete(self._batch_key(batch_id))
        await redis.srem(self._active_batches_key(), batch_id)
        return True


# 全局任务管理器实例
screening_task_manager = ScreeningTaskManager()
