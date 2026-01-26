"""语音面试 HTTP API 路由

使用 HTTP API 替代 WebSocket，解决 VAD 和超时问题。
用户录制完整音频后一次性发送，AI 回复完整响应。
"""

import json
import base64
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.omni_http_service import get_omni_http_service, OmniHttpService
from app.services.interview_service import InterviewService
from app.services.interview_state import get_interview_state_manager
from app.services.jd_service import JDService
from app.services.resume_parser import ResumeParser
from app.agents.controller_agent import ControllerAgent

router = APIRouter()

# 服务实例
interview_service = InterviewService()
jd_service = JDService()
resume_parser = ResumeParser()


class StartInterviewRequest(BaseModel):
    """开始面试请求"""
    pass


class StartInterviewResponse(BaseModel):
    """开始面试响应"""
    session_id: str
    welcome_text: str
    welcome_audio: Optional[str] = None  # base64 wav
    audio_format: str = "wav"


class SendAudioRequest(BaseModel):
    """发送音频请求"""
    session_id: str
    audio: str  # base64 编码的音频
    audio_format: str = "wav"  # wav, mp3, webm 等


class SendAudioResponse(BaseModel):
    """发送音频响应"""
    user_transcript: str  # 用户说的内容（转录）
    ai_text: str  # AI 回复文本
    ai_audio: Optional[str] = None  # AI 回复音频 (base64)
    audio_format: str = "wav"
    is_interview_complete: bool = False


class EndInterviewRequest(BaseModel):
    """结束面试请求"""
    session_id: str


class EndInterviewResponse(BaseModel):
    """结束面试响应"""
    summary: str
    duration_seconds: int


# 存储面试会话状态
interview_sessions: dict = {}


class InterviewSession:
    """面试会话状态"""

    def __init__(self, session_id: str, resume_summary: str, job_info: str):
        self.session_id = session_id
        self.resume_summary = resume_summary
        self.job_info = job_info
        self.conversation_history: List[dict] = []
        self.start_time = datetime.now()
        self.controller = ControllerAgent(session_id=session_id)
        self.controller.start_time = self.start_time

    def get_system_prompt(self) -> str:
        """构建面试官系统提示"""
        return f"""你是一位专业的AI面试官，正在进行一场真实的求职面试。

## 候选人简历
{self.resume_summary}

## 招聘岗位
{self.job_info}

## 面试要求
1. 用专业、友好的语气进行面试
2. 根据简历和岗位要求提出针对性问题
3. 深入追问以了解候选人的真实能力
4. 每次只问一个问题，等待候选人回答
5. 注意倾听，适当给予反馈
6. 用中文进行面试

请开始面试。"""

    def add_user_message(self, text: str):
        """添加用户消息"""
        self.conversation_history.append({
            "role": "user",
            "content": text
        })

    def add_assistant_message(self, text: str):
        """添加助手消息"""
        self.conversation_history.append({
            "role": "assistant",
            "content": text
        })

    def get_conversation_for_api(self) -> List[dict]:
        """获取适合 API 调用的对话历史（纯文本格式）"""
        return self.conversation_history.copy()


def build_resume_summary(resume) -> str:
    """从简历数据构建面试官需要的摘要"""
    if not resume:
        return "候选人简历信息暂不可用"

    parts = []

    if resume.basic_info:
        info = resume.basic_info
        basic = []
        if info.name:
            basic.append(f"姓名: {info.name}")
        if info.age:
            basic.append(f"年龄: {info.age}岁")
        if basic:
            parts.append("【基本信息】" + ", ".join(basic))

    if resume.education:
        edu_list = []
        for edu in resume.education[:2]:
            edu_str = f"{edu.school}"
            if edu.degree:
                edu_str += f" {edu.degree}"
            if edu.major:
                edu_str += f" {edu.major}"
            edu_list.append(edu_str)
        if edu_list:
            parts.append("【教育背景】" + "; ".join(edu_list))

    if resume.experience:
        exp_list = []
        for exp in resume.experience[:3]:
            exp_str = f"{exp.company} - {exp.title}"
            if exp.start_date and exp.end_date:
                exp_str += f" ({exp.start_date}至{exp.end_date})"
            if exp.duties:
                duties_short = exp.duties[:100] + "..." if len(exp.duties) > 100 else exp.duties
                exp_str += f": {duties_short}"
            exp_list.append(exp_str)
        if exp_list:
            parts.append("【工作经历】\n" + "\n".join(exp_list))

    if resume.skills:
        skills = []
        if resume.skills.hard_skills:
            skills.extend(resume.skills.hard_skills[:10])
        if skills:
            parts.append("【技术技能】" + ", ".join(skills))

    return "\n\n".join(parts) if parts else "候选人简历信息暂不可用"


def build_job_info(jd) -> str:
    """从JD数据构建岗位信息"""
    if not jd:
        return "岗位信息暂不可用"

    parts = [f"职位: {jd.title}"]

    if jd.department:
        parts.append(f"部门: {jd.department}")

    if jd.requirements:
        parts.append(f"要求: {jd.requirements[:500]}")

    if jd.required_skills:
        parts.append(f"技能要求: {', '.join(jd.required_skills[:10])}")

    return "\n".join(parts)


@router.post("/start/{token}", response_model=StartInterviewResponse)
async def start_interview(token: str):
    """开始语音面试

    创建面试会话，返回 AI 面试官的开场白。
    """
    # 验证 token 并获取面试信息
    interview = interview_service.get_by_token(token)
    if not interview:
        raise HTTPException(status_code=404, detail="面试不存在或已过期")

    session_id = str(interview.id)

    # 获取简历和 JD 信息
    resume = resume_parser.get_resume(interview.resume_id)
    jd = jd_service.get(interview.jd_id) if interview.jd_id else None

    resume_summary = build_resume_summary(resume)
    job_info = build_job_info(jd)

    # 创建会话
    session = InterviewSession(
        session_id=session_id,
        resume_summary=resume_summary,
        job_info=job_info
    )
    interview_sessions[session_id] = session

    # 生成开场白
    omni_service = get_omni_http_service()

    welcome_prompt = "请用语音问候候选人，做一个简短的自我介绍，然后请候选人做自我介绍。"

    try:
        # 使用文本生成开场白音频
        messages = [
            {"role": "system", "content": session.get_system_prompt()},
            {"role": "user", "content": welcome_prompt}
        ]

        # 调用 API 生成开场白
        import httpx

        request_body = {
            "model": "qwen-omni-turbo",
            "messages": messages,
            "modalities": ["text", "audio"],
            "audio": {"voice": "Cherry", "format": "wav"},
            "stream": True,
            "stream_options": {"include_usage": True}
        }

        headers = {
            "Authorization": f"Bearer {omni_service.api_key}",
            "Content-Type": "application/json"
        }

        welcome_text = ""
        audio_chunks = []

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                omni_service.API_URL,
                headers=headers,
                json=request_body
            ) as response:
                if response.status_code != 200:
                    error = await response.aread()
                    print(f"[VoiceInterview] Welcome API error: {error.decode()}")
                    raise HTTPException(status_code=500, detail="生成开场白失败")

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                welcome_text += delta["content"]
                            if "audio" in delta and "data" in delta["audio"]:
                                audio_chunks.append(delta["audio"]["data"])
                    except:
                        continue

        welcome_audio = "".join(audio_chunks) if audio_chunks else None

        # 记录开场白到对话历史
        session.add_assistant_message(welcome_text)

        print(f"[VoiceInterview] Session {session_id} started with welcome: {welcome_text[:50]}...")

        return StartInterviewResponse(
            session_id=session_id,
            welcome_text=welcome_text,
            welcome_audio=welcome_audio,
            audio_format="wav"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[VoiceInterview] Start error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-audio", response_model=SendAudioResponse)
async def send_audio(request: SendAudioRequest):
    """发送用户音频，获取 AI 回复

    用户录制完成后调用此接口，发送完整音频。
    """
    session = interview_sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="面试会话不存在")

    omni_service = get_omni_http_service()

    try:
        # 调用 Omni API 处理音频
        response = await omni_service.chat_with_audio(
            audio_base64=request.audio,
            audio_format=request.audio_format,
            system_prompt=session.get_system_prompt(),
            conversation_history=session.get_conversation_for_api(),
            voice="Cherry",
            enable_audio_output=True
        )

        # 从响应中提取用户转录（Omni API 会自动转录）
        # 注意：Omni API 的响应包含 AI 的回复，用户的转录需要单独处理
        # 这里我们假设用户说的内容已经被 AI 理解并回复了
        user_transcript = "[用户语音输入]"  # 暂时用占位符

        # 记录对话
        session.add_user_message(user_transcript)
        session.add_assistant_message(response.text)

        # 检查是否需要结束面试（通过 Controller Agent）
        is_complete = False
        if session.controller:
            # 简单检查：对话超过 10 轮或时间超过 15 分钟
            duration = (datetime.now() - session.start_time).total_seconds()
            rounds = len([m for m in session.conversation_history if m["role"] == "user"])
            if rounds >= 10 or duration > 900:
                is_complete = True

        print(f"[VoiceInterview] AI response: {response.text[:50]}...")

        return SendAudioResponse(
            user_transcript=user_transcript,
            ai_text=response.text,
            ai_audio=response.audio_base64,
            audio_format="wav",
            is_interview_complete=is_complete
        )

    except Exception as e:
        print(f"[VoiceInterview] Send audio error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/end", response_model=EndInterviewResponse)
async def end_interview(request: EndInterviewRequest):
    """结束面试"""
    session = interview_sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="面试会话不存在")

    duration = int((datetime.now() - session.start_time).total_seconds())

    # 生成面试总结
    summary = f"面试已完成，共进行了 {len(session.conversation_history) // 2} 轮对话。"

    # 清理会话
    del interview_sessions[request.session_id]

    return EndInterviewResponse(
        summary=summary,
        duration_seconds=duration
    )
