"""Omni Realtime 语音面试 WebSocket 路由

使用 Qwen-Omni Realtime 实现端到端实时语音对话：
- 实时语音输入 (内置 VAD)
- 端到端语音理解和生成
- 多智能体协同 (面试官 + 控场)
"""

import json
import asyncio
import base64
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.omni_realtime_service import (
    OmniRealtimeSession,
    ConversationState,
    get_omni_service
)
from app.services.interview_service import InterviewService
from app.services.interview_state import get_interview_state_manager
from app.agents.controller_agent import ControllerAgent
from app.services.jd_service import JDService
from app.services.resume_parser import ResumeParser

router = APIRouter()

# 服务实例
interview_service = InterviewService()
jd_service = JDService()
resume_parser = ResumeParser()


def build_resume_summary(resume) -> str:
    """从简历数据构建面试官需要的摘要"""
    if not resume:
        return "候选人简历信息暂不可用"

    parts = []

    # 基本信息
    if resume.basic_info:
        info = resume.basic_info
        basic = []
        if info.name:
            basic.append(f"姓名: {info.name}")
        if info.age:
            basic.append(f"年龄: {info.age}岁")
        if basic:
            parts.append("【基本信息】" + ", ".join(basic))

    # 教育背景
    if resume.education:
        edu_list = []
        for edu in resume.education[:2]:  # 最多2条
            edu_str = f"{edu.school}"
            if edu.degree:
                edu_str += f" {edu.degree}"
            if edu.major:
                edu_str += f" {edu.major}"
            edu_list.append(edu_str)
        if edu_list:
            parts.append("【教育背景】" + "; ".join(edu_list))

    # 工作经历
    if resume.experience:
        exp_list = []
        for exp in resume.experience[:3]:  # 最多3条
            exp_str = f"{exp.company} - {exp.title}"
            if exp.start_date and exp.end_date:
                exp_str += f" ({exp.start_date}至{exp.end_date})"
            if exp.duties:
                # 截取职责描述的前100字
                duties_short = exp.duties[:100] + "..." if len(exp.duties) > 100 else exp.duties
                exp_str += f": {duties_short}"
            exp_list.append(exp_str)
        if exp_list:
            parts.append("【工作经历】\n" + "\n".join(exp_list))

    # 技能
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

    if jd.description:
        # 截取描述的前200字
        desc_short = jd.description[:200] + "..." if len(jd.description) > 200 else jd.description
        parts.append(f"职位描述: {desc_short}")

    if jd.requirements:
        reqs = jd.requirements[:5]  # 最多5条
        parts.append("岗位要求:\n- " + "\n- ".join(reqs))

    if jd.required_skills:
        parts.append(f"必需技能: {', '.join(jd.required_skills[:8])}")

    if jd.preferred_skills:
        parts.append(f"加分技能: {', '.join(jd.preferred_skills[:5])}")

    if jd.interview_config and jd.interview_config.focus_areas:
        parts.append(f"面试重点考察: {', '.join(jd.interview_config.focus_areas)}")

    return "\n".join(parts)


class InterviewSession:
    """面试会话管理"""

    def __init__(
        self,
        token: str,
        websocket: WebSocket,
        session_id: str,
        resume_summary: str,
        job_info: str,
        jd=None,  # JD对象，用于控场智能体
    ):
        self.token = token
        self.websocket = websocket
        self.session_id = session_id
        self.resume_summary = resume_summary
        self.job_info = job_info
        self.jd = jd  # 保存JD对象供控场智能体使用

        # Omni 会话
        self.omni_session: Optional[OmniRealtimeSession] = None

        # 控场智能体
        self.controller: Optional[ControllerAgent] = None

        # 状态
        self.state_manager = get_interview_state_manager()
        self.conversation_history: list[dict] = []
        self.is_active = False

    def _build_interviewer_prompt(self) -> str:
        """构建面试官系统提示词"""
        return f"""你是一位专业的技术面试官。

## 语言要求【重要】
- 必须全程使用中文进行面试
- 不允许使用英文，即使候选人用英文也要用中文回复
- 使用自然的中文口语表达

## 你的角色
- 你正在进行一场语音面试
- 保持专业、友好、有耐心
- 用自然的口语化表达，不要太正式
- 每次只问一个问题，等待候选人回答

## 职位信息
{self.job_info}

## 候选人背景
{self.resume_summary}

## 面试流程
1. 首先用中文问候候选人，请他做自我介绍
2. 根据简历背景提出针对性的技术问题
3. 深入追问以评估技术深度
4. 适时进行行为面试（STAR法则）
5. 给候选人提问机会

## 注意事项
- 问题要简洁明确，适合语音交流
- 如果候选人回答不清楚，换种方式追问
- 关注候选人的思考过程，不只是答案
- 保持对话流畅自然
- 记住：全程只用中文！

## 当前对话
请用中文给出下一个自然的回应或问题。
"""

    async def start(self) -> bool:
        """启动面试会话"""
        try:
            print(f"[Interview] Starting session {self.session_id}")

            # 获取 Omni 服务
            omni_service = get_omni_service()
            print(f"[Interview] Got Omni service")

            # 创建 Omni 会话 (使用 Cherry 女声)
            self.omni_session = await omni_service.create_session(
                session_id=self.session_id,
                system_prompt=self._build_interviewer_prompt(),
                voice="Cherry",
                on_transcript=self._on_transcript,
                on_response_text=self._on_response_text,
                on_response_audio=self._on_response_audio,
                on_state_change=self._on_state_change,
                on_error=self._on_error,
            )
            print(f"[Interview] Created Omni session")

            # 连接 Omni API
            print(f"[Interview] Connecting to Omni API...")
            if not await self.omni_session.connect():
                print(f"[Interview] Omni connection failed")
                return False
            print(f"[Interview] Omni connected successfully")

            # 创建控场智能体
            self.controller = ControllerAgent(session_id=self.session_id)
            self.controller.start_time = datetime.now()
            print(f"[Interview] Controller agent initialized")

            self.is_active = True

            # 发送欢迎消息
            print(f"[Interview] Sending welcome message...")
            await self._send_welcome()
            print(f"[Interview] Session started successfully")

            return True

        except Exception as e:
            import traceback
            print(f"[Interview] Start error: {e}")
            traceback.print_exc()
            await self._send_error(str(e))
            return False

    async def _send_welcome(self):
        """发送欢迎消息 (触发AI说话)"""
        # 发送开场白请求
        await self.omni_session.send_text(
            "面试开始了，请用语音问候候选人并请他/她做自我介绍。"
        )

    def _on_transcript(self, text: str, is_final: bool):
        """收到转录结果"""
        asyncio.create_task(self._async_on_transcript(text, is_final))

    async def _async_on_transcript(self, text: str, is_final: bool):
        """异步处理转录结果"""
        if not self.is_active:
            return
        # 发送给前端
        try:
            await self.websocket.send_json({
                "type": "transcript",
                "text": text,
                "is_final": is_final
            })
        except Exception:
            return  # WebSocket may be closed

        # 如果是最终结果，记录到历史
        if is_final and text.strip():
            self.conversation_history.append({
                "role": "candidate",
                "content": text
            })

            # 保存到状态管理器
            await self.state_manager.add_conversation(
                self.session_id,
                role="candidate",
                content=text
            )

            # 通知控场智能体
            if self.controller:
                asyncio.create_task(
                    self._check_controller()
                )

    def _on_response_text(self, text: str):
        """收到响应文本"""
        asyncio.create_task(self._async_on_response_text(text))

    async def _async_on_response_text(self, text: str):
        """异步处理响应文本"""
        if not self.is_active:
            return
        # 发送给前端 (增量文本)
        try:
            await self.websocket.send_json({
                "type": "response_text",
                "text": text
            })
        except Exception:
            pass  # WebSocket may be closed

    def _on_response_audio(self, audio_bytes: bytes):
        """收到响应音频"""
        asyncio.create_task(self._async_on_response_audio(audio_bytes))

    async def _async_on_response_audio(self, audio_bytes: bytes):
        """异步处理响应音频"""
        if not self.is_active:
            return
        # 编码并发送给前端
        try:
            audio_b64 = base64.b64encode(audio_bytes).decode('ascii')
            await self.websocket.send_json({
                "type": "audio",
                "audio": audio_b64
            })
        except Exception:
            pass  # WebSocket may be closed

    def _on_state_change(self, state: ConversationState):
        """状态变化"""
        asyncio.create_task(self._async_on_state_change(state))

    async def _async_on_state_change(self, state: ConversationState):
        """异步处理状态变化"""
        if not self.is_active:
            return

        status_map = {
            ConversationState.LISTENING: "listening",
            ConversationState.THINKING: "processing",
            ConversationState.SPEAKING: "speaking",
            ConversationState.IDLE: "idle",
            ConversationState.CLOSED: "stopped",
        }

        try:
            await self.websocket.send_json({
                "type": "status",
                "status": status_map.get(state, "unknown")
            })
        except Exception:
            pass  # WebSocket may be closed

        # 如果是说话结束，记录响应到历史
        if state == ConversationState.LISTENING:
            # TODO: 获取完整响应文本并记录
            pass

    def _on_error(self, error: str):
        """错误回调"""
        asyncio.create_task(self._send_error(error))

    async def _send_error(self, error: str):
        """发送错误消息"""
        if not self.is_active:
            return
        try:
            await self.websocket.send_json({
                "type": "error",
                "message": error
            })
        except Exception:
            pass  # WebSocket may be closed

    async def _check_controller(self):
        """检查控场智能体的决策"""
        if not self.controller or not self.jd:
            return

        try:
            # 使用已加载的 JD 信息进行分析
            decision = await self.controller.analyze(self.jd, self.conversation_history)
            print(f"[Controller] Analyzed: should_guide={decision.should_guide}, covered={decision.covered_topics}")

            # 如果有引导指令，注入到 Omni 会话
            if decision.should_guide and decision.directive:
                if self.omni_session:
                    await self.omni_session.inject_context(decision.directive)
                print(f"[Controller] Injected: {decision.directive}")

            # 如果建议结束
            if decision.should_end:
                await self._end_interview(decision.end_reason)

        except Exception as e:
            print(f"[Controller] Check error: {e}")

    _audio_count = 0  # 音频计数器
    _error_sent = False  # 是否已发送错误消息

    async def handle_audio(self, audio_b64: str):
        """处理前端发来的音频"""
        if not self.omni_session or not self.is_active:
            return

        try:
            audio_bytes = base64.b64decode(audio_b64)

            # 每100帧打印一次调试信息
            self._audio_count += 1
            if self._audio_count % 100 == 1:
                print(f"[Interview] Audio frame #{self._audio_count}: {len(audio_bytes)} bytes")

            success = await self.omni_session.send_audio(audio_bytes)

            # 如果发送失败(连接已关闭)，只发送一次错误消息
            if not success and not self._error_sent:
                self._error_sent = True
                print("[Interview] Audio send failed - connection closed")
                await self._send_error("语音连接已断开，请刷新页面重试")
        except Exception as e:
            print(f"[Interview] Audio error: {e}")

    async def handle_control(self, action: str):
        """处理控制指令"""
        if action == "stop":
            await self._end_interview("用户主动结束")
        elif action == "interrupt":
            if self.omni_session:
                await self.omni_session.cancel_response()
        elif action == "commit":
            # 用户手动提交音频（说完了）
            if self.omni_session:
                print("[Interview] User committed audio - triggering response")
                await self.omni_session.commit_audio()

    async def _end_interview(self, reason: str):
        """结束面试"""
        self.is_active = False

        # 通知前端
        try:
            await self.websocket.send_json({
                "type": "end",
                "reason": reason,
                "evaluation_ready": False
            })
        except Exception:
            pass  # WebSocket may be closed

        # 停止控场
        if self.controller:
            self.controller.stop()

        # 关闭 Omni 会话
        if self.omni_session:
            await self.omni_session.close()

    async def close(self):
        """清理资源"""
        self.is_active = False

        if self.controller:
            self.controller.stop()

        if self.omni_session:
            await self.omni_session.close()


# 活跃会话管理
active_sessions: dict[str, InterviewSession] = {}


@router.websocket("/ws/omni-interview/{token}")
async def omni_interview_websocket(websocket: WebSocket, token: str):
    """Omni Realtime 语音面试 WebSocket 端点

    使用 Qwen-Omni Realtime 实现端到端实时语音对话。

    客户端消息:
    - {"type": "audio", "audio": "base64_data"}  # 音频数据
    - {"type": "control", "action": "stop|interrupt"}

    服务器消息:
    - {"type": "transcript", "text": "...", "is_final": bool}
    - {"type": "response_text", "text": "..."}
    - {"type": "audio", "audio": "base64_data"}
    - {"type": "status", "status": "listening|processing|speaking"}
    - {"type": "end", "reason": "...", "evaluation_ready": bool}
    - {"type": "error", "message": "..."}
    """

    # 1. 验证 token
    session_data = interview_service.get_by_token(token)
    if not session_data:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # 2. 检查状态
    if session_data.status not in ["voice", "pending"]:
        await websocket.close(code=4002, reason="Interview not in voice stage")
        return

    # 3. 接受连接
    await websocket.accept()

    # 4. 准备面试信息 - 获取真实简历和JD数据
    resume_summary = "候选人简历信息暂不可用"
    job_info = "岗位信息暂不可用"
    jd = None

    # 获取简历信息
    if session_data.resume_id:
        try:
            resume = resume_parser.get_resume(session_data.resume_id)
            if resume:
                resume_summary = build_resume_summary(resume)
                print(f"[Omni Interview] Loaded resume for: {resume.basic_info.name if resume.basic_info else 'Unknown'}")
        except Exception as e:
            print(f"[Omni Interview] Failed to load resume: {e}")

    # 获取JD信息
    if session_data.jd_id:
        try:
            jd = jd_service.get(session_data.jd_id)
            if jd:
                job_info = build_job_info(jd)
                print(f"[Omni Interview] Loaded JD: {jd.title}")
        except Exception as e:
            print(f"[Omni Interview] Failed to load JD: {e}")

    # 5. 创建面试会话
    interview_session = InterviewSession(
        token=token,
        websocket=websocket,
        session_id=session_data.id,
        resume_summary=resume_summary,
        job_info=job_info,
        jd=jd,  # 传入JD对象供控场智能体使用
    )

    active_sessions[token] = interview_session

    try:
        # 6. 启动面试
        if not await interview_session.start():
            await websocket.close(code=4003, reason="Failed to start interview")
            return

        # 7. 消息处理循环
        while interview_session.is_active:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                msg_type = message.get("type", "")

                if msg_type == "audio":
                    audio = message.get("audio", "")
                    if audio:
                        await interview_session.handle_audio(audio)

                elif msg_type == "control":
                    action = message.get("action", "")
                    await interview_session.handle_control(action)

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })

    except WebSocketDisconnect:
        print(f"[Omni Interview] Client {token} disconnected")

    except Exception as e:
        print(f"[Omni Interview] Error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass

    finally:
        # 清理
        await interview_session.close()
        if token in active_sessions:
            del active_sessions[token]
