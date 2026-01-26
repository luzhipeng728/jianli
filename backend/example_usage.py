"""Redis 和面试状态管理使用示例

本文件展示如何在 FastAPI 路由中使用 Redis 和面试状态管理服务。
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.services.redis_client import get_redis_client, RedisClient
from app.services.interview_state import (
    get_interview_state_manager,
    InterviewStateManager,
    InterviewPhase,
    AgentState,
)

# 创建路由
example_router = APIRouter(prefix="/api/example", tags=["示例"])


# ==================== 数据模型 ====================

class CreateSessionRequest(BaseModel):
    """创建面试会话请求"""
    candidate_id: str
    resume_id: str
    job_position: str
    duration: int = 60  # 分钟


class AddMessageRequest(BaseModel):
    """添加对话消息请求"""
    role: str  # interviewer 或 candidate
    content: str


class AddEvaluationRequest(BaseModel):
    """添加评估笔记请求"""
    category: str
    score: float
    note: str


class ControlCommandRequest(BaseModel):
    """控场指令请求"""
    command_type: str  # phase_change, hint, interrupt, end_interview
    payload: dict


# ==================== Redis 基础操作示例 ====================

@example_router.post("/redis/cache")
async def set_cache(
    key: str,
    value: str,
    ttl: int = 3600,
    redis: RedisClient = Depends(get_redis_client)
):
    """设置缓存值"""
    success = await redis.set(key, value, ex=ttl)
    return {"success": success, "key": key}


@example_router.get("/redis/cache/{key}")
async def get_cache(
    key: str,
    redis: RedisClient = Depends(get_redis_client)
):
    """获取缓存值"""
    value = await redis.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"key": key, "value": value}


@example_router.post("/redis/queue")
async def push_to_queue(
    queue_name: str,
    item: str,
    redis: RedisClient = Depends(get_redis_client)
):
    """推送消息到队列"""
    count = await redis.rpush(queue_name, item)
    return {"queue": queue_name, "length": count}


@example_router.get("/redis/queue/{queue_name}/pop")
async def pop_from_queue(
    queue_name: str,
    redis: RedisClient = Depends(get_redis_client)
):
    """从队列弹出消息"""
    item = await redis.lpop(queue_name)
    if item is None:
        raise HTTPException(status_code=404, detail="Queue is empty")
    return {"queue": queue_name, "item": item}


# ==================== 面试会话管理示例 ====================

@example_router.post("/interview/sessions")
async def create_interview_session(
    request: CreateSessionRequest,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """创建面试会话"""
    # 生成会话ID（实际应用中可能用 UUID）
    import uuid
    session_id = f"interview_{uuid.uuid4().hex[:12]}"

    context = await manager.create_session(
        session_id=session_id,
        candidate_id=request.candidate_id,
        resume_id=request.resume_id,
        job_position=request.job_position,
        config={"duration": request.duration},
        ttl=7200  # 2小时
    )

    return {
        "session_id": context.session_id,
        "candidate_id": context.candidate_id,
        "job_position": context.job_position,
        "current_phase": context.current_phase,
        "start_time": context.start_time
    }


@example_router.get("/interview/sessions/{session_id}")
async def get_interview_session(
    session_id: str,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """获取面试会话详情"""
    context = await manager.get_session(session_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": context.session_id,
        "candidate_id": context.candidate_id,
        "resume_id": context.resume_id,
        "job_position": context.job_position,
        "current_phase": context.current_phase,
        "start_time": context.start_time,
        "end_time": context.end_time,
        "conversation_count": len(context.conversation_history),
        "evaluation_count": len(context.evaluation_notes),
        "config": context.config
    }


@example_router.put("/interview/sessions/{session_id}/phase")
async def change_interview_phase(
    session_id: str,
    phase: InterviewPhase,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """切换面试阶段"""
    success = await manager.change_phase(session_id, phase)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"session_id": session_id, "new_phase": phase}


@example_router.post("/interview/sessions/{session_id}/messages")
async def add_interview_message(
    session_id: str,
    request: AddMessageRequest,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """添加对话消息"""
    success = await manager.add_conversation(
        session_id=session_id,
        role=request.role,
        content=request.content
    )

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"session_id": session_id, "success": True}


@example_router.get("/interview/sessions/{session_id}/messages")
async def get_interview_messages(
    session_id: str,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """获取对话历史"""
    context = await manager.get_session(session_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "messages": context.conversation_history
    }


@example_router.post("/interview/sessions/{session_id}/evaluations")
async def add_evaluation(
    session_id: str,
    request: AddEvaluationRequest,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """添加评估笔记"""
    success = await manager.add_evaluation_note(
        session_id=session_id,
        category=request.category,
        score=request.score,
        note=request.note
    )

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"session_id": session_id, "success": True}


@example_router.get("/interview/sessions/{session_id}/evaluations")
async def get_evaluations(
    session_id: str,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """获取评估笔记"""
    context = await manager.get_session(session_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "evaluations": context.evaluation_notes
    }


@example_router.delete("/interview/sessions/{session_id}")
async def delete_interview_session(
    session_id: str,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """删除面试会话"""
    success = await manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"session_id": session_id, "deleted": True}


# ==================== Agent 状态管理示例 ====================

@example_router.post("/interview/sessions/{session_id}/agents")
async def create_agent(
    session_id: str,
    agent_id: str,
    agent_type: str,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """创建 Agent 状态"""
    agent_state = AgentState(
        agent_id=agent_id,
        agent_type=agent_type,  # interviewer 或 evaluator
        status="idle"
    )

    success = await manager.set_agent_state(session_id, agent_state)
    return {
        "session_id": session_id,
        "agent_id": agent_id,
        "success": success
    }


@example_router.get("/interview/sessions/{session_id}/agents/{agent_id}")
async def get_agent_status(
    session_id: str,
    agent_id: str,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """获取 Agent 状态"""
    state = await manager.get_agent_state(session_id, agent_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "session_id": session_id,
        "agent_id": state.agent_id,
        "agent_type": state.agent_type,
        "status": state.status,
        "current_task": state.current_task,
        "memory": state.memory
    }


@example_router.put("/interview/sessions/{session_id}/agents/{agent_id}/status")
async def update_agent_status(
    session_id: str,
    agent_id: str,
    status: str,
    current_task: Optional[str] = None,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """更新 Agent 状态"""
    success = await manager.update_agent_status(
        session_id=session_id,
        agent_id=agent_id,
        status=status,
        current_task=current_task
    )

    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "session_id": session_id,
        "agent_id": agent_id,
        "status": status
    }


# ==================== 控场指令队列示例 ====================

@example_router.post("/interview/sessions/{session_id}/commands")
async def push_control_command(
    session_id: str,
    request: ControlCommandRequest,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """推送控场指令"""
    if request.command_type == "phase_change":
        count = await manager.push_phase_change_command(
            session_id,
            InterviewPhase(request.payload.get("new_phase")),
            request.payload.get("reason")
        )
    elif request.command_type == "hint":
        count = await manager.push_hint_command(
            session_id,
            request.payload.get("hint_text"),
            request.payload.get("target_agent")
        )
    elif request.command_type == "interrupt":
        count = await manager.push_interrupt_command(
            session_id,
            request.payload.get("reason"),
            request.payload.get("action")
        )
    elif request.command_type == "end_interview":
        count = await manager.push_end_interview_command(
            session_id,
            request.payload.get("reason")
        )
    else:
        raise HTTPException(status_code=400, detail="Unknown command type")

    return {
        "session_id": session_id,
        "command_type": request.command_type,
        "queue_length": count
    }


@example_router.get("/interview/sessions/{session_id}/commands")
async def get_command_queue_status(
    session_id: str,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """获取指令队列状态"""
    count = await manager.get_command_count(session_id)
    return {
        "session_id": session_id,
        "queue_length": count
    }


@example_router.get("/interview/sessions/{session_id}/commands/next")
async def pop_next_command(
    session_id: str,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """弹出下一条指令"""
    command = await manager.pop_command(session_id)
    if command is None:
        raise HTTPException(status_code=404, detail="No commands in queue")

    return {
        "session_id": session_id,
        "command_type": command.command_type,
        "payload": command.payload,
        "timestamp": command.timestamp,
        "priority": command.priority
    }


@example_router.delete("/interview/sessions/{session_id}/commands")
async def clear_command_queue(
    session_id: str,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """清空指令队列"""
    success = await manager.clear_commands(session_id)
    return {
        "session_id": session_id,
        "cleared": success
    }


# ==================== 完整流程示例 ====================

@example_router.post("/interview/demo/complete-flow")
async def demo_complete_interview_flow(
    candidate_id: str,
    resume_id: str,
    job_position: str,
    manager: InterviewStateManager = Depends(get_interview_state_manager)
):
    """演示完整的面试流程"""
    import uuid

    # 1. 创建会话
    session_id = f"demo_{uuid.uuid4().hex[:8]}"
    context = await manager.create_session(
        session_id=session_id,
        candidate_id=candidate_id,
        resume_id=resume_id,
        job_position=job_position,
        config={"duration": 60, "demo": True}
    )

    # 2. 初始化 Agents
    interviewer = AgentState(
        agent_id="interviewer_001",
        agent_type="interviewer",
        status="idle"
    )
    evaluator = AgentState(
        agent_id="evaluator_001",
        agent_type="evaluator",
        status="idle"
    )
    await manager.set_agent_state(session_id, interviewer)
    await manager.set_agent_state(session_id, evaluator)

    # 3. 切换到自我介绍阶段
    await manager.change_phase(session_id, InterviewPhase.INTRO)
    await manager.add_conversation(
        session_id, "interviewer",
        "您好，欢迎参加面试。请先做个自我介绍。"
    )

    # 4. 添加候选人回答
    await manager.add_conversation(
        session_id, "candidate",
        "您好，我是一名有3年经验的Python工程师..."
    )

    # 5. 切换到技术面试阶段
    await manager.change_phase(session_id, InterviewPhase.TECHNICAL)
    await manager.add_conversation(
        session_id, "interviewer",
        "请解释一下Python的GIL是什么？"
    )

    # 6. 添加评估笔记
    await manager.add_evaluation_note(
        session_id,
        category="沟通表达",
        score=8.5,
        note="自我介绍清晰，表达流畅"
    )

    # 7. 推送控场指令
    await manager.push_hint_command(
        session_id,
        "面试进行到30分钟，准备进入下一阶段"
    )

    # 8. 获取完整的会话信息
    final_context = await manager.get_session(session_id)

    return {
        "message": "面试流程演示完成",
        "session_id": session_id,
        "current_phase": final_context.current_phase,
        "conversations": len(final_context.conversation_history),
        "evaluations": len(final_context.evaluation_notes),
        "note": "这是一个演示流程，展示了如何使用面试状态管理服务"
    }


# 在 main.py 中注册路由：
# app.include_router(example_router)
