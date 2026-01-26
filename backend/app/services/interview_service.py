import uuid
from datetime import datetime
from typing import Optional
from app.services.es_client import ESClient
from app.models.interview import (
    InterviewSession,
    InterviewStatus,
    WrittenTest,
    VoiceInterview,
    Evaluation
)
from app.models.jd import JobDescription
from app.models.resume import ResumeData

INTERVIEW_INDEX = "interviews"


class InterviewService:
    def __init__(self):
        self.es_client = ESClient()
        self._ensure_index()

    def _ensure_index(self):
        """确保索引存在"""
        index_body = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "token": {"type": "keyword"},
                    "resume_id": {"type": "keyword"},
                    "jd_id": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "started_at": {"type": "date"},
                    "completed_at": {"type": "date"},
                    "cancelled_at": {"type": "date"},
                    "cancelled_reason": {"type": "text"},
                    "written_test": {"type": "object", "enabled": True},
                    "voice_interview": {"type": "object", "enabled": True},
                    "evaluation": {"type": "object", "enabled": True}
                }
            }
        }
        self.es_client.create_index(INTERVIEW_INDEX, index_body)

    def create_session(self, resume_id: str, jd_id: str) -> InterviewSession:
        """创建面试会话并生成唯一token"""
        session_id = str(uuid.uuid4())
        token = str(uuid.uuid4())

        session = InterviewSession(
            id=session_id,
            token=token,
            resume_id=resume_id,
            jd_id=jd_id,
            status=InterviewStatus.PENDING,
            created_at=datetime.now()
        )

        # 保存到ES
        doc = session.model_dump(mode="json")
        self.es_client.index_document(INTERVIEW_INDEX, session_id, doc)

        return session

    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        """根据ID获取面试会话"""
        try:
            result = self.es_client.get_document(INTERVIEW_INDEX, session_id)
            return InterviewSession(**result["_source"])
        except Exception:
            return None

    def get_by_token(self, token: str) -> Optional[InterviewSession]:
        """根据token获取面试会话（候选人端使用）"""
        try:
            query = {
                "query": {
                    "term": {"token": token}
                },
                "size": 1
            }
            result = self.es_client.search(INTERVIEW_INDEX, query)
            hits = result["hits"]["hits"]
            if hits:
                return InterviewSession(**hits[0]["_source"])
            return None
        except Exception:
            return None

    def update_status(self, session_id: str, status: InterviewStatus) -> bool:
        """更新面试状态（根据ES文档ID）"""
        session = self.get_session(session_id)
        if not session:
            return False

        session.status = status

        # 更新时间戳
        if status == InterviewStatus.WRITTEN_TEST and not session.started_at:
            session.started_at = datetime.now()
        elif status == InterviewStatus.COMPLETED and not session.completed_at:
            session.completed_at = datetime.now()

        doc = session.model_dump(mode="json")
        self.es_client.index_document(INTERVIEW_INDEX, session_id, doc)
        return True

    def update_status_by_token(self, token: str, status: InterviewStatus) -> bool:
        """更新面试状态（根据token/session_id）"""
        session = self.get_by_token(token)
        if not session:
            return False

        session.status = status

        # 更新时间戳
        if status == InterviewStatus.WRITTEN_TEST and not session.started_at:
            session.started_at = datetime.now()
        elif status == InterviewStatus.COMPLETED and not session.completed_at:
            session.completed_at = datetime.now()

        doc = session.model_dump(mode="json")
        # 使用session.id作为ES文档ID
        self.es_client.index_document(INTERVIEW_INDEX, session.id, doc)
        return True

    def save_written_test(self, session_id: str, written_test: WrittenTest) -> bool:
        """保存笔试结果"""
        session = self.get_session(session_id)
        if not session:
            return False

        session.written_test = written_test

        # 如果笔试完成，自动更新状态
        if written_test.completed_at and session.status == InterviewStatus.PENDING:
            session.status = InterviewStatus.WRITTEN_TEST
            if not session.started_at:
                session.started_at = datetime.now()

        doc = session.model_dump(mode="json")
        self.es_client.index_document(INTERVIEW_INDEX, session_id, doc)
        return True

    def save_voice_interview(self, session_id: str, voice_interview: VoiceInterview) -> bool:
        """保存语音面试记录"""
        session = self.get_session(session_id)
        if not session:
            return False

        session.voice_interview = voice_interview

        # 如果语音面试结束，更新状态
        if voice_interview.ended_at:
            session.status = InterviewStatus.VOICE_INTERVIEW

        doc = session.model_dump(mode="json")
        self.es_client.index_document(INTERVIEW_INDEX, session_id, doc)
        return True

    def save_evaluation(self, session_id: str, evaluation: Evaluation) -> bool:
        """保存评估报告"""
        session = self.get_session(session_id)
        if not session:
            return False

        evaluation.generated_at = datetime.now()
        session.evaluation = evaluation

        # 有评估报告，标记为完成
        session.status = InterviewStatus.COMPLETED
        if not session.completed_at:
            session.completed_at = datetime.now()

        doc = session.model_dump(mode="json")
        self.es_client.index_document(INTERVIEW_INDEX, session_id, doc)
        return True

    def list_sessions(
        self,
        page: int = 1,
        size: int = 20,
        status_filter: Optional[InterviewStatus] = None
    ) -> dict:
        """获取面试会话列表"""
        query_body = {"match_all": {}}

        if status_filter:
            query_body = {"term": {"status": status_filter.value}}

        query = {
            "query": query_body,
            "from": (page - 1) * size,
            "size": size,
            "sort": [{"created_at": "desc"}]
        }

        result = self.es_client.search(INTERVIEW_INDEX, query)
        total = result["hits"]["total"]["value"] if isinstance(result["hits"]["total"], dict) else result["hits"]["total"]
        data = [InterviewSession(**hit["_source"]) for hit in result["hits"]["hits"]]

        return {
            "data": data,
            "total": total,
            "page": page,
            "size": size
        }

    def cancel_session(self, session_id: str, reason: str = "") -> bool:
        """取消面试"""
        session = self.get_session(session_id)
        if not session:
            return False

        session.status = InterviewStatus.CANCELLED
        session.cancelled_at = datetime.now()
        session.cancelled_reason = reason

        doc = session.model_dump(mode="json")
        self.es_client.index_document(INTERVIEW_INDEX, session_id, doc)
        return True

    def delete_session(self, session_id: str) -> bool:
        """删除面试会话"""
        try:
            self.es_client.delete_document(INTERVIEW_INDEX, session_id)
            return True
        except Exception:
            return False

    async def generate_evaluation_report(
        self,
        session_id: str,
        jd: JobDescription,
        resume: ResumeData
    ) -> Optional[Evaluation]:
        """生成评估报告并保存到会话中"""
        from app.agents.evaluation_agent import evaluation_agent

        session = self.get_session(session_id)
        if not session:
            return None

        # 调用评估Agent生成报告
        evaluation = await evaluation_agent.generate_evaluation(
            session=session,
            jd=jd,
            resume=resume
        )

        # 保存评估报告
        self.save_evaluation(session_id, evaluation)

        return evaluation
