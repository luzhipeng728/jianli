"""AI筛选后台 Worker - 支持最高10并发"""
import asyncio
from typing import Optional
from app.services.screening_task_manager import (
    ScreeningTaskManager, ScreeningStatus, screening_task_manager
)
from app.services.job_matcher import JobMatcher, JobRequirement
from app.services.es_client import ESClient
from app.models.resume import ResumeData


class ScreeningWorker:
    """AI筛选后台 Worker"""

    MAX_CONCURRENCY = 10  # 最大并发数
    QUEUE_CHECK_INTERVAL = 2  # 队列检查间隔（秒）
    PROCESS_TIMEOUT = 60  # 单个简历处理超时（秒）

    def __init__(self):
        self.task_manager = screening_task_manager
        self.job_matcher = JobMatcher()
        self.es_client = ESClient()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENCY)
        self._active_tasks: dict[str, asyncio.Task] = {}

    async def start(self):
        """启动 Worker"""
        if self._running:
            return
        self._running = True

        # 恢复卡住的任务
        await self._recover_stuck_tasks()

        self._worker_task = asyncio.create_task(self._run_loop())
        print(f"[ScreeningWorker] AI筛选处理器已启动，最大并发: {self.MAX_CONCURRENCY}")

    async def _recover_stuck_tasks(self):
        """恢复未完成的任务"""
        redis = await self.task_manager.get_redis()
        batch_ids = await redis.smembers(self.task_manager._active_batches_key())
        recovered = 0

        for batch_id in batch_ids:
            batch = await self.task_manager.get_batch(batch_id)
            if not batch:
                continue

            # 检查是否有未完成的简历
            pending_resumes = [r for r in batch.resumes
                              if r.status in [ScreeningStatus.PROCESSING, ScreeningStatus.QUEUED, ScreeningStatus.PENDING]]

            if pending_resumes and batch.status != ScreeningStatus.SUCCESS:
                # 重置 processing 状态为 queued
                for task in batch.resumes:
                    if task.status == ScreeningStatus.PROCESSING:
                        task.status = ScreeningStatus.QUEUED
                        task.progress = 0
                        recovered += 1

                batch.status = ScreeningStatus.PROCESSING
                await self.task_manager.update_batch(batch)
                await self.task_manager.enqueue_batch(batch.batch_id)
                print(f"[ScreeningWorker] 恢复批次 {batch.batch_id[:8]}...，{len(pending_resumes)} 个待处理简历")

        if recovered > 0:
            print(f"[ScreeningWorker] 重置了 {recovered} 个 processing 状态的任务")

    async def stop(self):
        """停止 Worker"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        # 取消所有活跃任务
        for task in self._active_tasks.values():
            task.cancel()
        print("[ScreeningWorker] AI筛选处理器已停止")

    async def _run_loop(self):
        """主循环 - 监听队列并处理任务"""
        while self._running:
            try:
                batch_id = await self.task_manager.dequeue_batch(timeout=self.QUEUE_CHECK_INTERVAL)
                if batch_id:
                    asyncio.create_task(self._process_batch(batch_id))
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ScreeningWorker] 队列处理错误: {e}")
                await asyncio.sleep(1)

    async def _process_batch(self, batch_id: str):
        """处理筛选批量任务"""
        batch = await self.task_manager.get_batch(batch_id)
        if not batch:
            print(f"[ScreeningWorker] 批量任务 {batch_id} 不存在")
            return

        print(f"[ScreeningWorker] 开始AI筛选任务 {batch_id}，JD: {batch.jd_title}，共 {batch.total_resumes} 份简历")

        # 更新状态为处理中
        batch.status = ScreeningStatus.PROCESSING
        await self.task_manager.update_batch(batch)

        # 获取JD信息
        from app.services.jd_service import JDService
        jd_service = JDService()
        jd = jd_service.get(batch.jd_id)
        if not jd:
            print(f"[ScreeningWorker] JD {batch.jd_id} 不存在")
            batch.status = ScreeningStatus.FAILED
            await self.task_manager.update_batch(batch)
            return

        job_req = JobRequirement(
            title=jd.title,
            description=jd.description,
            required_skills=jd.required_skills,
            preferred_skills=jd.preferred_skills,
        )

        # 创建所有简历处理任务
        tasks = []
        for resume_task in batch.resumes:
            if resume_task.status in [ScreeningStatus.QUEUED, ScreeningStatus.PENDING]:
                task = asyncio.create_task(
                    self._process_resume_with_semaphore(
                        batch_id, resume_task.resume_id, resume_task.resume_name, job_req
                    )
                )
                tasks.append(task)
                self._active_tasks[resume_task.resume_id] = task

        # 等待所有任务完成
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # 清理活跃任务
        for resume_task in batch.resumes:
            self._active_tasks.pop(resume_task.resume_id, None)

        # 获取最终状态
        batch = await self.task_manager.get_batch(batch_id)
        print(f"[ScreeningWorker] AI筛选任务 {batch_id} 完成: {batch.completed} 成功, {batch.failed} 失败")

    async def _process_resume_with_semaphore(
        self,
        batch_id: str,
        resume_id: str,
        resume_name: str,
        job_req: JobRequirement
    ):
        """使用信号量控制并发处理单个简历"""
        async with self._semaphore:
            try:
                await asyncio.wait_for(
                    self._process_resume(batch_id, resume_id, resume_name, job_req),
                    timeout=self.PROCESS_TIMEOUT
                )
            except asyncio.TimeoutError:
                print(f"[ScreeningWorker] 简历处理超时: {resume_name}")
                await self.task_manager.update_resume_status(
                    batch_id, resume_id,
                    ScreeningStatus.FAILED,
                    error=f"处理超时 ({self.PROCESS_TIMEOUT}秒)"
                )

    async def _process_resume(
        self,
        batch_id: str,
        resume_id: str,
        resume_name: str,
        job_req: JobRequirement
    ):
        """处理单个简历 - 使用AI智能匹配"""
        print(f"[ScreeningWorker] 开始分析简历: {resume_name}")

        # 更新状态为处理中 - 读取简历
        await self.task_manager.update_resume_status(
            batch_id, resume_id,
            ScreeningStatus.PROCESSING,
            progress=10,
            status_detail="读取简历数据"
        )

        try:
            # 从ES获取简历数据
            result = self.es_client.get_document("resumes", resume_id)
            source = result["_source"]

            # 更新进度 - 解析数据
            await self.task_manager.update_resume_status(
                batch_id, resume_id,
                ScreeningStatus.PROCESSING,
                progress=20,
                status_detail="解析简历内容"
            )

            # 构建ResumeData用于匹配
            resume_data = ResumeData.model_validate(source)

            # 更新进度 - AI分析中
            await self.task_manager.update_resume_status(
                batch_id, resume_id,
                ScreeningStatus.PROCESSING,
                progress=40,
                status_detail="AI智能评分中"
            )

            # 使用AI智能匹配（而非规则匹配）
            match_result = await self.job_matcher.smart_match(resume_data, job_req)

            # 更新进度 - 保存结果
            await self.task_manager.update_resume_status(
                batch_id, resume_id,
                ScreeningStatus.PROCESSING,
                progress=90,
                status_detail="保存评分结果"
            )

            # 构建结果
            result_data = {
                "resume_id": resume_id,
                "resume_name": resume_name,
                "match_score": match_result.overall_score,
                "skill_score": match_result.skill_score,
                "experience_score": match_result.experience_score,
                "education_score": match_result.education_score,
                "intention_score": match_result.intention_score,
                "matched_skills": match_result.matched_skills,
                "missing_skills": match_result.missing_skills,
                "highlights": match_result.highlights,
                "concerns": match_result.concerns,
            }

            # 更新为成功
            await self.task_manager.update_resume_status(
                batch_id, resume_id,
                ScreeningStatus.SUCCESS,
                progress=100,
                match_result=result_data
            )

            print(f"[ScreeningWorker] 简历分析完成: {resume_name} -> 匹配度 {match_result.overall_score}%")

        except Exception as e:
            error_msg = str(e)
            print(f"[ScreeningWorker] 简历分析失败: {resume_name} - {error_msg}")
            await self.task_manager.update_resume_status(
                batch_id, resume_id,
                ScreeningStatus.FAILED,
                error=error_msg
            )


# 全局 Worker 实例
screening_worker = ScreeningWorker()
