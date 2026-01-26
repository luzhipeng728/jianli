"""Unified Interviewer Agent - handles all interview phases"""

from typing import List, Dict, Optional, AsyncGenerator
from app.services.llm_client import LLMClient
from app.models.interview_phase import InterviewPhase, PHASE_CONFIGS

class UnifiedInterviewerAgent:
    """Unified interviewer agent that handles all phases

    Adapts questioning style based on current phase.
    """

    def __init__(
        self,
        session_id: str,
        resume_summary: str,
        job_info: str,
        written_test_summary: str = ""
    ):
        self.session_id = session_id
        self.resume_summary = resume_summary
        self.job_info = job_info
        self.written_test_summary = written_test_summary
        self.llm = LLMClient()

    def _build_system_prompt(
        self,
        phase: InterviewPhase,
        round_number: int,
        can_advance_early: bool = False
    ) -> str:
        """Build phase-specific system prompt"""

        phase_config = PHASE_CONFIGS[phase]

        # 笔试结果信息（如果有）
        written_test_section = ""
        if self.written_test_summary:
            written_test_section = f"""
## 候选人笔试表现
{self.written_test_summary}
"""

        base_prompt = f"""你是一位专业的技术面试官，正在进行语音面试。

## 语言要求
- 必须全程使用中文
- 使用自然的口语表达
- 回复简洁，适合语音播放（不超过3句话）

## 候选人背景
{self.resume_summary}

## 岗位信息
{self.job_info}
{written_test_section}
## 当前阶段
- 阶段：{phase_config.description}
- 当前轮次：{round_number + 1} / {phase_config.max_rounds}
- 阶段指导：{phase_config.prompt_hint}
"""

        # Phase-specific instructions
        phase_instructions = {
            InterviewPhase.OPENING: """
## 本阶段任务
- 友好问候候选人
- 简单介绍自己和面试流程
- 如果有笔试成绩，先简单评价一下笔试表现（比如"看到你笔试成绩还不错"或"笔试有些题目答错了，待会我们可以聊聊"）
- 让候选人放松""",

            InterviewPhase.SELF_INTRO: """
## 本阶段任务
- 请候选人做自我介绍
- 可以针对介绍内容简单追问
- 了解候选人的职业经历概况""",

            InterviewPhase.PROJECT_DEEP: """
## 本阶段任务
- 深入了解候选人做过的项目
- 追问技术细节和个人贡献
- 了解候选人解决问题的能力
- 问题要具体，不要泛泛而谈""",

            InterviewPhase.TECH_ASSESS: """
## 本阶段任务
- 考察岗位相关的技术能力
- 可以出具体的技术问题
- 评估候选人的技术深度和广度
- 根据岗位要求重点考察相关技能""",

            InterviewPhase.BEHAVIORAL: """
## 本阶段任务
- 了解候选人的软技能
- 考察团队协作能力
- 了解问题解决和冲突处理方式
- 使用STAR方法提问（情境-任务-行动-结果）""",

            InterviewPhase.QA: """
## 本阶段任务
- 让候选人提问
- 耐心回答候选人的问题
- 介绍公司和团队情况
- 如果候选人没有问题，可以主动介绍一些信息""",

            InterviewPhase.CLOSING: """
## 本阶段任务
- 感谢候选人参与面试
- 说明后续流程和时间安排
- 礼貌结束面试"""
        }

        base_prompt += phase_instructions.get(phase, "")

        if can_advance_early:
            base_prompt += """

## 阶段切换
如果你认为当前阶段已经充分了解候选人，可以在回复末尾加上 [ADVANCE_PHASE] 标记。
但请确保至少完成了最少轮次的提问。"""

        return base_prompt

    async def generate_response(
        self,
        phase: InterviewPhase,
        round_number: int,
        conversation_history: List[Dict[str, str]],
        can_advance_early: bool = False
    ) -> str:
        """Generate interviewer response"""
        system_prompt = self._build_system_prompt(phase, round_number, can_advance_early)

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for msg in conversation_history[-20:]:  # Last 20 messages
            role = "assistant" if msg["role"] in ["interviewer", "assistant"] else "user"
            messages.append({"role": role, "content": msg["content"]})

        # If no history, this is the start
        if not conversation_history:
            messages.append({
                "role": "user",
                "content": "请开始面试。"
            })

        response = await self.llm.chat_async(
            messages=messages,
            temperature=0.7
        )

        return response

    async def generate_response_stream(
        self,
        phase: InterviewPhase,
        round_number: int,
        conversation_history: List[Dict[str, str]],
        can_advance_early: bool = False
    ) -> AsyncGenerator[str, None]:
        """Stream generate interviewer response"""
        system_prompt = self._build_system_prompt(phase, round_number, can_advance_early)

        messages = [{"role": "system", "content": system_prompt}]

        for msg in conversation_history[-20:]:
            role = "assistant" if msg["role"] in ["interviewer", "assistant"] else "user"
            messages.append({"role": role, "content": msg["content"]})

        if not conversation_history:
            messages.append({"role": "user", "content": "请开始面试。"})

        async for chunk in self.llm.chat_stream_messages(messages, temperature=0.7):
            yield chunk

    def check_advance_signal(self, response: str) -> tuple[str, bool]:
        """Check if response contains advance phase signal"""
        should_advance = False
        cleaned = response

        # 支持多种标记格式
        advance_markers = ["[ADVANCE_PHASE]", "[ADVANCE]", "【ADVANCE】", "[advance]"]
        for marker in advance_markers:
            if marker in cleaned:
                cleaned = cleaned.replace(marker, "")
                should_advance = True

        return cleaned.strip(), should_advance
