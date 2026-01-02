import uuid
import time
import json
from typing import AsyncGenerator
from app.services.llm_client import LLMClient
from app.services.es_client import ESClient
from app.models.chat import ChatMessage, ChatSession, StreamChunk

KNOWLEDGE_INDEX = "knowledge_base"

SYSTEM_PROMPT = """你是一个智能问答助手，能够回答用户的问题。
请基于提供的上下文信息回答问题，如果上下文中没有相关信息，请基于你的知识回答。
回答要简洁、准确、有帮助。

当需要展示结构化数据时，可以使用以下卡片格式：
- 表格数据: <card:table>{"headers":["列1","列2"],"rows":[["值1","值2"]]}</card:table>
- 图表数据: <card:chart>{"type":"bar","data":[...]}</card:chart>
"""

class ChatEngine:
    def __init__(self):
        self.llm_client = LLMClient()
        self.es_client = ESClient()
        self.sessions: dict[str, ChatSession] = {}

    def create_session(self) -> ChatSession:
        session = ChatSession(id=str(uuid.uuid4()))
        self.sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> ChatSession | None:
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def _search_knowledge(self, query: str, top_k: int = 3) -> list[dict]:
        """从知识库检索相关内容"""
        try:
            search_query = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "content"],
                        "type": "best_fields"
                    }
                },
                "size": top_k
            }
            result = self.es_client.search(KNOWLEDGE_INDEX, search_query)
            return [hit["_source"] for hit in result["hits"]["hits"]]
        except Exception:
            return []

    def _build_context(self, query: str, history: list[ChatMessage]) -> str:
        """构建RAG上下文"""
        # 检索知识库
        knowledge = self._search_knowledge(query)

        context_parts = []

        # 添加知识库内容
        if knowledge:
            context_parts.append("相关知识：")
            for i, item in enumerate(knowledge, 1):
                context_parts.append(f"{i}. {item.get('title', '')}: {item.get('content', '')[:500]}")

        # 添加历史对话（最近5轮）
        recent_history = history[-10:]  # 最近5轮对话
        if recent_history:
            context_parts.append("\n历史对话：")
            for msg in recent_history:
                role = "用户" if msg.role == "user" else "助手"
                context_parts.append(f"{role}: {msg.content[:200]}")

        return "\n".join(context_parts)

    async def chat_stream(
        self,
        session_id: str | None,
        message: str,
        show_thinking: bool = False
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式问答"""
        start_time = time.time()
        first_token_time = None

        # 获取或创建会话
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
        else:
            session = self.create_session()

        # 添加用户消息
        session.messages.append(ChatMessage(role="user", content=message))

        # 构建上下文
        context = self._build_context(message, session.messages[:-1])

        # 构建完整prompt
        full_prompt = f"{context}\n\n用户问题：{message}"

        # 思考过程
        if show_thinking:
            yield StreamChunk(type="thinking", content="正在分析问题...")

        # 流式生成
        full_response = ""
        async for chunk in self.llm_client.chat_stream(full_prompt, SYSTEM_PROMPT):
            if first_token_time is None:
                first_token_time = time.time()

            full_response += chunk

            # 检测卡片标记
            if "<card:" in chunk:
                # 简化处理，实际需要更复杂的解析
                yield StreamChunk(type="text", content=chunk)
            else:
                yield StreamChunk(type="text", content=chunk)

        # 添加助手回复到历史
        session.messages.append(ChatMessage(role="assistant", content=full_response))

        # 完成
        end_time = time.time()
        metrics = {
            "first_token_ms": int((first_token_time - start_time) * 1000) if first_token_time else 0,
            "total_ms": int((end_time - start_time) * 1000),
            "session_id": session.id
        }
        yield StreamChunk(type="done", metrics=metrics)
