import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.services.chat_engine import ChatEngine
from app.models.chat import ChatRequest, ChatSession, KnowledgeItem

router = APIRouter(prefix="/api/chat", tags=["智能问答"])

engine = ChatEngine()

@router.post("/session")
async def create_session() -> ChatSession:
    """创建新会话"""
    return engine.create_session()

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    if not engine.delete_session(session_id):
        raise HTTPException(404, "会话不存在")
    return {"status": "deleted"}

@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """获取对话历史"""
    session = engine.get_session(session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    return {"messages": session.messages}

@router.post("/message")
async def chat_message(request: ChatRequest):
    """发送消息（SSE流式响应）"""

    async def generate():
        async for chunk in engine.chat_stream(
            request.session_id,
            request.message,
            request.show_thinking,
            request.jd_id
        ):
            data = chunk.model_dump_json()
            yield f"data: {data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
