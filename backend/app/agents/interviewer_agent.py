"""面试官智能体 - 负责进行语音面试"""

from app.services.llm_client import LLMClient
from app.services.interview_state import get_interview_state_manager, CommandType
from app.models.jd import JobDescription
from app.models.resume import ResumeData
from typing import AsyncGenerator, Optional
import json


class InterviewerAgent:
    """面试官智能体

    职责：
    - 根据JD+简历生成系统提示词
    - 进行语音面试提问
    - 根据回答进行追问/深挖
    - 评估候选人表现
    - 接收控场Agent的引导指令
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.llm = LLMClient()
        self.state_manager = get_interview_state_manager()
        self.conversation_history: list[dict] = []
        self.agent_id = f"interviewer_{session_id}"

    def build_system_prompt(self, jd: JobDescription, resume: ResumeData) -> str:
        """构建面试官系统提示词

        Args:
            jd: 职位描述
            resume: 简历数据

        Returns:
            系统提示词字符串
        """
        # 安全地获取简历信息
        candidate_name = resume.basic_info.name or "候选人"
        skills = ', '.join(resume.skills.hard_skills[:10]) if resume.skills.hard_skills else "待评估"

        recent_company = resume.experience[0].company if resume.experience else "无"
        recent_title = resume.experience[0].title if resume.experience else ""
        recent_work = f"{recent_company} - {recent_title}" if recent_company != "无" else "无"

        school = resume.education[0].school if resume.education else "无"
        major = resume.education[0].major if resume.education else ""
        education_info = f"{school} - {major}" if school != "无" else "无"

        # 获取面试配置
        focus_areas = jd.interview_config.focus_areas if jd.interview_config.focus_areas else ["综合能力"]
        required_skills = jd.required_skills if jd.required_skills else []

        return f"""你是一位专业、友好的面试官，正在面试 {candidate_name}，应聘 {jd.title} 岗位。

## 候选人简历摘要
- 姓名：{candidate_name}
- 技能：{skills}
- 最近工作：{recent_work}
- 教育背景：{education_info}

## 岗位要求
- 岗位：{jd.title}
- 必需技能：{', '.join(required_skills)}
- 重点考察：{', '.join(focus_areas)}

## 面试指导
1. 每次只问一个问题，等待回答后再继续
2. 根据回答适当追问，深入了解候选人能力
3. 保持专业、友好的面试氛围
4. 如果候选人回答不清楚，可以引导或换个方式问
5. 注意控制面试节奏，不要问太多重复的问题

## 面试流程
1. 先简单自我介绍，让候选人放松
2. 围绕工作经验提问
3. 技术/专业能力考察
4. 软技能考察
5. 让候选人提问

请用自然、口语化的方式提问，就像真实面试一样。"""

    async def get_directives(self) -> list[str]:
        """获取控场指令并转换为文本提示

        Returns:
            指令文本列表
        """
        directives = []

        # 检查指令队列
        command_count = await self.state_manager.get_command_count(self.session_id)

        for _ in range(command_count):
            command = await self.state_manager.pop_command(self.session_id)
            if not command:
                break

            # 根据指令类型生成提示文本
            if command.command_type == CommandType.PHASE_CHANGE:
                new_phase = command.payload.get("new_phase")
                reason = command.payload.get("reason", "")
                directives.append(
                    f"[阶段切换] 请开始进入 {new_phase} 阶段。{reason}"
                )

            elif command.command_type == CommandType.INTERRUPT:
                reason = command.payload.get("reason", "")
                action = command.payload.get("action", "")
                directives.append(
                    f"[中断提示] {reason} 建议：{action}"
                )

            elif command.command_type == CommandType.HINT:
                hint_text = command.payload.get("hint_text", "")
                directives.append(f"[提示] {hint_text}")

            elif command.command_type == CommandType.TIME_WARNING:
                directives.append("[时间提醒] 请注意时间，准备进入下一环节")

            elif command.command_type == CommandType.END_INTERVIEW:
                reason = command.payload.get("reason", "")
                directives.append(f"[结束面试] {reason} 请礼貌地结束面试。")

        return directives

    async def ask_question(
        self,
        jd: JobDescription,
        resume: ResumeData,
        candidate_response: Optional[str] = None
    ) -> str:
        """生成下一个面试问题

        Args:
            jd: 职位描述
            resume: 简历数据
            candidate_response: 候选人的回答（如果有）

        Returns:
            面试官的问题
        """
        # 更新 Agent 状态为思考中
        await self.state_manager.update_agent_status(
            self.session_id,
            self.agent_id,
            "thinking",
            "生成面试问题"
        )

        # 获取控场指令
        directives = await self.get_directives()
        directive_text = ""
        if directives:
            directive_text = f"\n\n## 控场指令（请参考）\n" + "\n".join(directives)

        system_prompt = self.build_system_prompt(jd, resume) + directive_text

        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]

        if not self.conversation_history:
            # 首次提问
            messages.append({
                "role": "user",
                "content": "请开始面试，先做自我介绍并提出第一个问题。"
            })
        else:
            # 继续对话
            messages.extend(self.conversation_history)
            if candidate_response:
                messages.append({"role": "user", "content": candidate_response})

        # 调用 LLM（使用 chat_async 方法支持完整消息列表）
        response = await self.llm.chat_async(
            messages=messages,
            temperature=0.7
        )

        # 更新对话历史
        if candidate_response:
            self.conversation_history.append({"role": "user", "content": candidate_response})
        self.conversation_history.append({"role": "assistant", "content": response})

        # 保存上下文到 InterviewStateManager
        await self.save_context()

        # 更新会话的对话历史
        if candidate_response:
            await self.state_manager.add_conversation(
                self.session_id,
                "candidate",
                candidate_response
            )
        await self.state_manager.add_conversation(
            self.session_id,
            "interviewer",
            response
        )

        # 更新 Agent 状态为说话中
        await self.state_manager.update_agent_status(
            self.session_id,
            self.agent_id,
            "speaking",
            "提问候选人"
        )

        return response

    async def ask_question_stream(
        self,
        jd: JobDescription,
        resume: ResumeData,
        candidate_response: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """流式生成面试问题

        Args:
            jd: 职位描述
            resume: 简历数据
            candidate_response: 候选人的回答（如果有）

        Yields:
            问题文本的流式片段
        """
        # 更新 Agent 状态为思考中
        await self.state_manager.update_agent_status(
            self.session_id,
            self.agent_id,
            "thinking",
            "生成面试问题"
        )

        # 获取控场指令
        directives = await self.get_directives()
        directive_text = ""
        if directives:
            directive_text = f"\n\n## 控场指令（请参考）\n" + "\n".join(directives)

        system_prompt = self.build_system_prompt(jd, resume) + directive_text

        # 构建消息
        if not self.conversation_history:
            # 首次提问
            prompt = "请开始面试，先做自我介绍并提出第一个问题。"
        else:
            # 继续对话 - 使用候选人的回答作为 prompt
            prompt = candidate_response if candidate_response else "请继续提问。"

        # 更新 Agent 状态为说话中
        await self.state_manager.update_agent_status(
            self.session_id,
            self.agent_id,
            "speaking",
            "提问候选人"
        )

        # 流式输出
        full_response = ""
        async for chunk in self.llm.chat_stream(
            prompt=prompt,
            system_prompt=system_prompt
        ):
            full_response += chunk
            yield chunk

        # 更新对话历史
        if candidate_response:
            self.conversation_history.append({"role": "user", "content": candidate_response})
        self.conversation_history.append({"role": "assistant", "content": full_response})

        # 保存上下文
        await self.save_context()

        # 更新会话的对话历史
        if candidate_response:
            await self.state_manager.add_conversation(
                self.session_id,
                "candidate",
                candidate_response
            )
        await self.state_manager.add_conversation(
            self.session_id,
            "interviewer",
            full_response
        )

    async def save_context(self):
        """保存 Agent 上下文到 Redis"""
        context = await self.state_manager.get_session(self.session_id)
        if context:
            # 更新面试官上下文
            context.interviewer_context = {
                "conversation_history": self.conversation_history,
                "question_count": len([m for m in self.conversation_history if m["role"] == "assistant"]),
                "last_update": str(context.start_time)
            }

            await self.state_manager.update_session(
                self.session_id,
                {"interviewer_context": context.interviewer_context}
            )

    async def load_context(self):
        """从 Redis 加载 Agent 上下文"""
        context = await self.state_manager.get_session(self.session_id)
        if context and context.interviewer_context:
            self.conversation_history = context.interviewer_context.get(
                "conversation_history",
                []
            )

    def get_conversation_history(self) -> list[dict]:
        """获取对话历史

        Returns:
            对话历史列表
        """
        return self.conversation_history

    async def reset(self):
        """重置面试官状态"""
        self.conversation_history = []
        await self.save_context()
