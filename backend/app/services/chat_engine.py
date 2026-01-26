import uuid
import time
import json
from datetime import datetime
from typing import AsyncGenerator
from app.services.llm_client import LLMClient
from app.services.es_client import ESClient
from app.models.chat import ChatMessage, ChatSession, StreamChunk

RESUME_INDEX = "resumes"
CHAT_STATS_INDEX = "chat_stats"

SYSTEM_PROMPT = """你是一个智能简历问答助手，专门帮助HR和招聘人员查询和筛选候选人。

你有以下能力：
1. 根据技能、经验、学历等条件搜索合适的候选人
2. 分析候选人的背景和匹配度
3. 对比多个候选人的优劣势
4. 回答关于简历库中候选人的问题

## 回复规则
1. 系统已经自动搜索并展示了候选人卡片，你只需要提供分析和建议
2. 不要重复列出候选人的基本信息（姓名、技能等），卡片已经展示了
3. 重点分析：为什么这些候选人匹配、各自的优势、推荐理由
4. 如果需要对比，直接用文字描述对比结果
5. 回复要简洁有价值，不要冗长

请基于提供的候选人信息进行专业分析，给出有价值的建议。
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

    def _save_chat_record(self, session_id: str, user_message: str, assistant_message: str, response_time_ms: int):
        """保存聊天记录到 Elasticsearch"""
        try:
            record_id = str(uuid.uuid4())
            doc = {
                "session_id": session_id,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "response_time_ms": response_time_ms,
                "created_at": datetime.now().isoformat()
            }
            self.es_client.index_document(CHAT_STATS_INDEX, record_id, doc)
        except Exception as e:
            print(f"Save chat record error: {e}")

    async def _search_resumes(self, query: str, top_k: int = 10, jd_id: str = None) -> list[dict]:
        """从简历库搜索候选人（混合搜索：关键词 + 向量），可按JD筛选"""
        results = []

        # 构建JD筛选条件
        jd_filter = None
        screened_resume_ids = None

        if jd_id:
            # 首先检查是否有AI筛选结果
            try:
                from app.services.screening_task_manager import screening_task_manager
                matches = await screening_task_manager.get_jd_all_matches(jd_id, min_score=0)
                if matches:
                    # 使用AI筛选结果中的简历ID
                    screened_resume_ids = [m["resume_id"] for m in matches]
                    jd_filter = {
                        "terms": {"id": screened_resume_ids}
                    }
            except Exception as e:
                print(f"Get screening results error: {e}")

            # 如果没有AI筛选结果，回退到旧的nested查询
            if not screened_resume_ids:
                jd_filter = {
                    "nested": {
                        "path": "recommended_jds",
                        "query": {
                            "term": {"recommended_jds.jd_id": jd_id}
                        }
                    }
                }

        # 1. 先尝试向量搜索
        try:
            query_embedding = await self.llm_client.get_embedding(query, text_type="query")
            if query_embedding:
                vector_query = {
                    "knn": {
                        "field": "embedding",
                        "query_vector": query_embedding,
                        "k": top_k,
                        "num_candidates": top_k * 2,
                        "filter": jd_filter
                    } if jd_filter else {
                        "field": "embedding",
                        "query_vector": query_embedding,
                        "k": top_k,
                        "num_candidates": top_k * 2
                    },
                    "_source": True
                }
                vector_result = self.es_client.search(RESUME_INDEX, vector_query)
                for hit in vector_result["hits"]["hits"]:
                    hit["_source"]["_search_type"] = "vector"
                    hit["_source"]["_score"] = hit.get("_score", 0)
                    results.append(hit["_source"])
        except Exception as e:
            print(f"Vector search error: {e}")

        # 2. 关键词搜索
        try:
            if jd_filter:
                keyword_query = {
                    "query": {
                        "bool": {
                            "must": {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["raw_text^1", "skills.hard_skills^3", "basic_info.name^2"],
                                    "type": "best_fields"
                                }
                            },
                            "filter": jd_filter
                        }
                    },
                    "size": top_k
                }
            else:
                keyword_query = {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["raw_text^1", "skills.hard_skills^3", "basic_info.name^2"],
                            "type": "best_fields"
                        }
                    },
                    "size": top_k
                }
            keyword_result = self.es_client.search(RESUME_INDEX, keyword_query)
            for hit in keyword_result["hits"]["hits"]:
                # 避免重复
                source = hit["_source"]
                if not any(r.get("id") == source.get("id") for r in results):
                    source["_search_type"] = "keyword"
                    source["_score"] = hit.get("_score", 0)
                    results.append(source)
        except Exception as e:
            print(f"Keyword search error: {e}")

        return results[:top_k]

    def _resume_to_card(self, resume: dict, query: str) -> dict:
        """将简历转换为卡片数据"""
        basic = resume.get("basic_info", {})
        skills = resume.get("skills", {})
        education = resume.get("education", [])
        experience = resume.get("experience", [])

        # 计算匹配度（简单版本：基于搜索分数）
        score = resume.get("_score", 0)
        match_score = min(95, max(60, int(70 + score * 5))) if score else 75

        # 获取最近的工作
        latest_exp = experience[0] if experience else {}

        # 获取最高学历
        edu_str = ""
        if education:
            edu = education[0]
            edu_str = f"{edu.get('school', '')} - {edu.get('degree', '')} - {edu.get('major', '')}"

        # 计算工作年限
        exp_years = 0
        for exp in experience:
            start = exp.get("start_date", "")
            end = exp.get("end_date", "至今")
            try:
                start_year = int(start.split(".")[0]) if start else 0
                end_year = 2025 if "至今" in end else int(end.split(".")[0]) if end else 0
                if start_year and end_year:
                    exp_years += end_year - start_year
            except:
                pass

        # 生成亮点（基于查询关键词匹配）
        highlights = []
        query_lower = query.lower()
        hard_skills = skills.get("hard_skills", [])

        # 技能匹配亮点
        matched_skills = [s for s in hard_skills if s.lower() in query_lower or query_lower in s.lower()]
        if matched_skills:
            highlights.append(f"精通 {', '.join(matched_skills[:3])}")

        # 经验亮点
        if exp_years >= 5:
            highlights.append(f"拥有 {exp_years} 年相关工作经验")

        # 公司亮点
        if latest_exp.get("company"):
            highlights.append(f"曾在 {latest_exp.get('company')} 担任 {latest_exp.get('title', '开发')}")

        return {
            "id": resume.get("id", ""),
            "resume_id": resume.get("id", ""),
            "name": basic.get("name", "未知"),
            "title": latest_exp.get("title", "开发工程师"),
            "company": latest_exp.get("company", ""),
            "experience_years": exp_years or None,
            "skills": hard_skills[:8],
            "education": edu_str,
            "match_score": match_score,
            "highlights": highlights[:3]
        }

    def _format_resume_for_context(self, resume: dict) -> str:
        """将简历格式化为上下文文本"""
        basic = resume.get("basic_info", {})
        name = basic.get("name", "未知")
        phone = basic.get("phone", "")
        email = basic.get("email", "")
        gender = basic.get("gender", "")
        age = basic.get("age", "")

        # 技能
        skills = resume.get("skills", {})
        hard_skills = ", ".join(skills.get("hard_skills", [])[:10])
        soft_skills = ", ".join(skills.get("soft_skills", [])[:5])

        # 工作经历
        experiences = resume.get("experience", [])
        exp_text = ""
        for exp in experiences[:3]:  # 最近3份工作
            company = exp.get("company", "")
            title = exp.get("title", "")
            start = exp.get("start_date", "")
            end = exp.get("end_date", "")
            duties = exp.get("duties", "")[:200]
            exp_text += f"  - {company} | {title} ({start} - {end})\n    {duties}\n"

        # 教育背景
        education = resume.get("education", [])
        edu_text = ""
        for edu in education[:2]:
            school = edu.get("school", "")
            degree = edu.get("degree", "")
            major = edu.get("major", "")
            edu_text += f"  - {school} | {degree} | {major}\n"

        return f"""
【候选人：{name}】
基本信息：{gender} {f'{age}岁' if age else ''} | {phone} | {email}
技术技能：{hard_skills}
软技能：{soft_skills}
工作经历：
{exp_text}
教育背景：
{edu_text}
"""

    def _parse_card(self, card_text: str) -> dict | None:
        """解析卡片内容"""
        import re
        try:
            # 提取卡片类型
            type_match = re.search(r'<card type="([^"]+)">', card_text)
            if not type_match:
                return None

            card_type = type_match.group(1)

            # 提取JSON内容
            content_match = re.search(r'<card type="[^"]+">(.+?)</card>', card_text, re.DOTALL)
            if not content_match:
                return None

            json_str = content_match.group(1).strip()
            # 移除可能的 markdown 代码块标记
            json_str = re.sub(r'^```\w*\n?', '', json_str)
            json_str = re.sub(r'\n?```$', '', json_str)
            json_str = json_str.strip()

            data = json.loads(json_str)
            return {"type": card_type, "data": data}
        except Exception as e:
            print(f"Card parse error: {e}")
            return None

    async def _build_context(self, query: str, history: list[ChatMessage]) -> str:
        """构建RAG上下文"""
        # 从简历库搜索候选人
        resumes = await self._search_resumes(query)
        return await self._build_context_from_resumes(resumes, query, history)

    async def _build_context_from_resumes(self, resumes: list[dict], query: str, history: list[ChatMessage]) -> str:
        """从已搜索的简历构建上下文"""
        context_parts = []

        # 添加简历搜索结果
        if resumes:
            context_parts.append(f"=== 简历库搜索结果（共找到 {len(resumes)} 位候选人，卡片已展示给用户）===\n")
            for resume in resumes[:5]:  # 只给LLM前5个详细信息
                context_parts.append(self._format_resume_for_context(resume))
        else:
            context_parts.append("=== 简历库中未找到匹配的候选人 ===")

        # 添加历史对话（最近5轮）
        recent_history = history[-10:]
        if recent_history:
            context_parts.append("\n=== 历史对话 ===")
            for msg in recent_history:
                role = "用户" if msg.role == "user" else "助手"
                context_parts.append(f"{role}: {msg.content[:300]}")

        context_parts.append(f"\n用户问题：{query}")
        context_parts.append("\n请基于以上候选人信息进行分析，给出专业建议。注意：候选人卡片已经展示给用户了，不需要重复列出基本信息。")

        return "\n".join(context_parts)

    async def chat_stream(
        self,
        session_id: str | None,
        message: str,
        show_thinking: bool = False,
        jd_id: str = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式问答 - 先展示卡片，再流式分析"""
        start_time = time.time()
        first_token_time = None

        # 获取或创建会话
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
        else:
            session = self.create_session()

        # 添加用户消息
        session.messages.append(ChatMessage(role="user", content=message))

        # 思考过程
        if show_thinking:
            yield StreamChunk(type="thinking", content="正在搜索候选人...")

        # 1. 先搜索简历（可按JD筛选）
        resumes = await self._search_resumes(message, jd_id=jd_id)

        # 2. 立即发送候选人卡片（如果有搜索结果）
        if resumes:
            cards_data = [self._resume_to_card(r, message) for r in resumes[:5]]
            # 过滤掉无效卡片
            cards_data = [c for c in cards_data if c.get("name") and c.get("name") != "未知"]
            if cards_data:
                yield StreamChunk(type="card", card_type="candidates", data=cards_data)

        # 3. 构建上下文
        context = await self._build_context_from_resumes(resumes, message, session.messages[:-1])

        # 4. 流式生成分析文本
        full_response = ""
        async for chunk in self.llm_client.chat_stream(context, SYSTEM_PROMPT):
            if first_token_time is None:
                first_token_time = time.time()
            full_response += chunk
            yield StreamChunk(type="text", content=chunk)

        # 添加助手回复到历史
        session.messages.append(ChatMessage(role="assistant", content=full_response))

        # 完成
        end_time = time.time()
        total_ms = int((end_time - start_time) * 1000)
        metrics = {
            "first_token_ms": int((first_token_time - start_time) * 1000) if first_token_time else 0,
            "total_ms": total_ms,
            "session_id": session.id
        }

        # 持久化聊天记录到 ES
        self._save_chat_record(session.id, message, full_response, total_ms)

        yield StreamChunk(type="done", metrics=metrics)
