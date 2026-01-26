"""面试状态管理模块

管理面试会话的生命周期、Agent上下文和控场指令队列
"""

from typing import Optional, Any, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from app.services.redis_client import get_redis_client


class InterviewPhase(str, Enum):
    """面试阶段"""
    PREPARING = "preparing"  # 准备中
    INTRO = "intro"  # 自我介绍
    TECHNICAL = "technical"  # 技术问答
    BEHAVIORAL = "behavioral"  # 行为面试
    QA = "qa"  # 候选人提问
    CLOSING = "closing"  # 结束阶段
    COMPLETED = "completed"  # 已完成


class CommandType(str, Enum):
    """控场指令类型"""
    PHASE_CHANGE = "phase_change"  # 阶段切换
    INTERRUPT = "interrupt"  # 中断
    HINT = "hint"  # 提示
    TIME_WARNING = "time_warning"  # 时间警告
    END_INTERVIEW = "end_interview"  # 结束面试


class InterviewContext(BaseModel):
    """面试会话上下文"""
    session_id: str = Field(..., description="会话ID")
    candidate_id: str = Field(..., description="候选人ID")
    resume_id: str = Field(..., description="简历ID")
    job_position: str = Field(..., description="应聘岗位")

    # 面试状态
    current_phase: InterviewPhase = Field(
        default=InterviewPhase.PREPARING,
        description="当前阶段"
    )
    start_time: Optional[datetime] = Field(default=None, description="开始时间")
    end_time: Optional[datetime] = Field(default=None, description="结束时间")

    # Agent 上下文
    interviewer_context: dict = Field(
        default_factory=dict,
        description="面试官Agent上下文"
    )
    evaluator_context: dict = Field(
        default_factory=dict,
        description="评估员Agent上下文"
    )

    # 面试数据
    conversation_history: list[dict] = Field(
        default_factory=list,
        description="对话历史"
    )
    candidate_answers: list[dict] = Field(
        default_factory=list,
        description="候选人回答记录"
    )
    evaluation_notes: list[dict] = Field(
        default_factory=list,
        description="评估笔记"
    )

    # 配置
    config: dict = Field(
        default_factory=dict,
        description="面试配置"
    )


class ControlCommand(BaseModel):
    """控场指令"""
    command_type: CommandType = Field(..., description="指令类型")
    payload: dict = Field(default_factory=dict, description="指令数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    priority: int = Field(default=0, description="优先级（数字越大优先级越高）")


class AgentState(BaseModel):
    """Agent状态"""
    agent_id: str = Field(..., description="Agent ID")
    agent_type: Literal["interviewer", "evaluator"] = Field(..., description="Agent类型")
    status: Literal["idle", "thinking", "speaking", "listening"] = Field(
        default="idle",
        description="当前状态"
    )
    current_task: Optional[str] = Field(default=None, description="当前任务")
    memory: dict = Field(default_factory=dict, description="短期记忆")
    metadata: dict = Field(default_factory=dict, description="元数据")


class InterviewStateManager:
    """面试状态管理器"""

    def __init__(self):
        self.redis = None

    async def _get_redis(self):
        """延迟初始化 Redis 客户端"""
        if self.redis is None:
            self.redis = await get_redis_client()
        return self.redis

    # ==================== 会话上下文管理 ====================

    async def create_session(
        self,
        session_id: str,
        candidate_id: str,
        resume_id: str,
        job_position: str,
        config: Optional[dict] = None,
        ttl: int = 7200,  # 默认2小时
    ) -> InterviewContext:
        """创建面试会话

        Args:
            session_id: 会话ID
            candidate_id: 候选人ID
            resume_id: 简历ID
            job_position: 应聘岗位
            config: 面试配置
            ttl: 会话过期时间（秒）
        """
        redis = await self._get_redis()

        context = InterviewContext(
            session_id=session_id,
            candidate_id=candidate_id,
            resume_id=resume_id,
            job_position=job_position,
            start_time=datetime.now(),
            config=config or {},
        )

        await redis.set_interview_context(
            session_id,
            context.model_dump(mode="json"),
            ttl=ttl
        )

        return context

    async def get_session(self, session_id: str) -> Optional[InterviewContext]:
        """获取面试会话"""
        redis = await self._get_redis()
        data = await redis.get_interview_context(session_id)
        if data is None:
            return None
        return InterviewContext(**data)

    async def update_session(
        self,
        session_id: str,
        updates: dict,
        ttl: Optional[int] = None
    ) -> bool:
        """更新面试会话

        Args:
            session_id: 会话ID
            updates: 要更新的字段
            ttl: 新的过期时间（秒），None表示保持原有
        """
        redis = await self._get_redis()

        # 获取现有上下文
        context = await self.get_session(session_id)
        if context is None:
            return False

        # 更新字段
        context_dict = context.model_dump(mode="json")
        context_dict.update(updates)

        # 保存更新后的上下文
        if ttl is None:
            # 获取剩余TTL
            ttl = await redis.ttl(f"interview:context:{session_id}")
            if ttl < 0:
                ttl = 3600  # 默认1小时

        await redis.set_interview_context(session_id, context_dict, ttl=ttl)
        return True

    async def delete_session(self, session_id: str) -> bool:
        """删除面试会话"""
        redis = await self._get_redis()
        count = await redis.delete_interview_context(session_id)
        return count > 0

    async def change_phase(
        self,
        session_id: str,
        new_phase: InterviewPhase
    ) -> bool:
        """切换面试阶段"""
        return await self.update_session(
            session_id,
            {"current_phase": new_phase}
        )

    async def add_conversation(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """添加对话记录

        Args:
            session_id: 会话ID
            role: 角色（interviewer/candidate）
            content: 对话内容
            metadata: 元数据
        """
        context = await self.get_session(session_id)
        if context is None:
            return False

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        context.conversation_history.append(message)

        return await self.update_session(
            session_id,
            {"conversation_history": context.conversation_history}
        )

    async def add_evaluation_note(
        self,
        session_id: str,
        category: str,
        score: float,
        note: str
    ) -> bool:
        """添加评估笔记

        Args:
            session_id: 会话ID
            category: 评估类别（如：技术能力、沟通能力等）
            score: 评分
            note: 评估说明
        """
        context = await self.get_session(session_id)
        if context is None:
            return False

        evaluation = {
            "category": category,
            "score": score,
            "note": note,
            "timestamp": datetime.now().isoformat()
        }

        context.evaluation_notes.append(evaluation)

        return await self.update_session(
            session_id,
            {"evaluation_notes": context.evaluation_notes}
        )

    # ==================== Agent 状态管理 ====================

    async def set_agent_state(
        self,
        session_id: str,
        agent_state: AgentState,
        ttl: int = 3600
    ) -> bool:
        """设置 Agent 状态"""
        redis = await self._get_redis()
        return await redis.set_agent_state(
            session_id,
            agent_state.agent_id,
            agent_state.model_dump(mode="json"),
            ttl=ttl
        )

    async def get_agent_state(
        self,
        session_id: str,
        agent_id: str
    ) -> Optional[AgentState]:
        """获取 Agent 状态"""
        redis = await self._get_redis()
        data = await redis.get_agent_state(session_id, agent_id)
        if data is None:
            return None
        return AgentState(**data)

    async def update_agent_status(
        self,
        session_id: str,
        agent_id: str,
        status: Literal["idle", "thinking", "speaking", "listening"],
        current_task: Optional[str] = None
    ) -> bool:
        """更新 Agent 状态"""
        agent_state = await self.get_agent_state(session_id, agent_id)
        if agent_state is None:
            return False

        agent_state.status = status
        if current_task is not None:
            agent_state.current_task = current_task

        return await self.set_agent_state(session_id, agent_state)

    async def delete_agent_state(
        self,
        session_id: str,
        agent_id: str
    ) -> bool:
        """删除 Agent 状态"""
        redis = await self._get_redis()
        count = await redis.delete_agent_state(session_id, agent_id)
        return count > 0

    # ==================== 控场指令队列 ====================

    async def push_command(
        self,
        session_id: str,
        command: ControlCommand
    ) -> int:
        """推送控场指令"""
        redis = await self._get_redis()
        command_dict = command.model_dump(mode="json")
        return await redis.push_control_command(session_id, command_dict)

    async def pop_command(self, session_id: str) -> Optional[ControlCommand]:
        """弹出控场指令"""
        redis = await self._get_redis()
        data = await redis.pop_control_command(session_id)
        if data is None:
            return None
        return ControlCommand(**data)

    async def get_command_count(self, session_id: str) -> int:
        """获取指令队列长度"""
        redis = await self._get_redis()
        return await redis.get_command_queue_length(session_id)

    async def clear_commands(self, session_id: str) -> bool:
        """清空指令队列"""
        redis = await self._get_redis()
        count = await redis.clear_command_queue(session_id)
        return count > 0

    async def push_phase_change_command(
        self,
        session_id: str,
        new_phase: InterviewPhase,
        reason: Optional[str] = None
    ) -> int:
        """推送阶段切换指令"""
        command = ControlCommand(
            command_type=CommandType.PHASE_CHANGE,
            payload={
                "new_phase": new_phase,
                "reason": reason
            },
            priority=5
        )
        return await self.push_command(session_id, command)

    async def push_interrupt_command(
        self,
        session_id: str,
        reason: str,
        action: Optional[str] = None
    ) -> int:
        """推送中断指令"""
        command = ControlCommand(
            command_type=CommandType.INTERRUPT,
            payload={
                "reason": reason,
                "action": action
            },
            priority=10  # 中断优先级最高
        )
        return await self.push_command(session_id, command)

    async def push_hint_command(
        self,
        session_id: str,
        hint_text: str,
        target_agent: Optional[str] = None
    ) -> int:
        """推送提示指令"""
        command = ControlCommand(
            command_type=CommandType.HINT,
            payload={
                "hint_text": hint_text,
                "target_agent": target_agent
            },
            priority=3
        )
        return await self.push_command(session_id, command)

    async def push_end_interview_command(
        self,
        session_id: str,
        reason: Optional[str] = None
    ) -> int:
        """推送结束面试指令"""
        command = ControlCommand(
            command_type=CommandType.END_INTERVIEW,
            payload={
                "reason": reason
            },
            priority=8
        )
        return await self.push_command(session_id, command)


# 全局单例
_state_manager = InterviewStateManager()


def get_interview_state_manager() -> InterviewStateManager:
    """获取面试状态管理器实例"""
    return _state_manager
