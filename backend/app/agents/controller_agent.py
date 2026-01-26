"""控场智能体 - 异步监控面试进度，静默引导面试官"""

from app.services.llm_client import LLMClient
from app.services.interview_state import InterviewStateManager, InterviewPhase, CommandType
from app.models.jd import JobDescription
import asyncio
import json
from datetime import datetime
from typing import Optional, Callable
from pydantic import BaseModel


class ControllerDecision(BaseModel):
    """控场决策模型"""
    should_guide: bool = False
    directive: str = ""
    should_end: bool = False
    end_reason: str = ""
    covered_topics: list[str] = []


class ControllerAgent:
    """控场智能体

    核心功能：
    - 异步监控对话质量和进度
    - 生成话题引导指令（静默发给面试官Agent）
    - 判断面试是否可以结束
    - 监控异常情况（超时、跑题等）
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.llm = LLMClient()
        self.state_manager = InterviewStateManager()
        self.start_time: Optional[datetime] = None
        self.max_duration = 30 * 60  # 30分钟最大时长
        self.is_running = False

    async def analyze(
        self,
        jd: JobDescription,
        conversation_history: list[dict]
    ) -> ControllerDecision:
        """分析当前面试状态，返回决策

        Args:
            jd: 岗位描述
            conversation_history: 对话历史

        Returns:
            ControllerDecision: 控场决策
        """

        elapsed_minutes = 0
        if self.start_time:
            elapsed_minutes = (datetime.now() - self.start_time).seconds // 60

        question_count = len([m for m in conversation_history if m.get("role") == "assistant"])

        system_prompt = """你是面试控场助手，负责监控面试进度和质量。
你的指令只发给面试官，候选人不会看到。

## 你的任务
1. 分析当前面试进度和质量
2. 判断是否需要引导面试官调整方向
3. 判断面试是否可以结束

## 输出格式（JSON）
{
  "should_guide": true/false,
  "directive": "引导指令内容（如需要）",
  "should_end": true/false,
  "end_reason": "结束原因（如需要）",
  "covered_topics": ["已覆盖的话题"]
}

## 结束条件
- 已充分考察候选人能力（至少5个问题）
- 候选人明确表示需要结束
- 面试时间过长（超过25分钟建议结束）

## 引导时机
- 话题偏离岗位要求
- 某个方向问太多，需要转换
- 候选人回答不清楚，建议换种方式问"""

        user_prompt = f"""## 岗位重点
- 岗位：{jd.title}
- 重点考察：{', '.join(jd.interview_config.focus_areas) if jd.interview_config.focus_areas else '综合能力'}
- 必需技能：{', '.join(jd.required_skills[:5]) if jd.required_skills else '无'}

## 当前进度
- 已进行时间：{elapsed_minutes} 分钟
- 已问问题数：{question_count}

## 对话历史
{json.dumps(conversation_history[-10:], ensure_ascii=False, indent=2)}

请分析并返回JSON决策："""

        try:
            response = await self.llm.chat_async(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )

            # 提取JSON
            response_text = response.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            data = json.loads(response_text.strip())
            return ControllerDecision(**data)
        except Exception as e:
            print(f"Controller analyze error: {e}")
            return ControllerDecision()

    async def push_directive(self, directive: str) -> None:
        """发送引导指令给面试官

        Args:
            directive: 引导指令内容
        """
        try:
            await self.state_manager.push_hint_command(
                session_id=self.session_id,
                hint_text=directive,
                target_agent="interviewer"
            )
        except Exception as e:
            print(f"Push directive error: {e}")

    async def set_should_end(self, should_end: bool, reason: str = "") -> None:
        """设置面试结束标志

        Args:
            should_end: 是否应该结束
            reason: 结束原因
        """
        try:
            if should_end:
                await self.state_manager.push_end_interview_command(
                    session_id=self.session_id,
                    reason=reason
                )
                # 更新会话阶段
                await self.state_manager.change_phase(
                    session_id=self.session_id,
                    new_phase=InterviewPhase.CLOSING
                )
        except Exception as e:
            print(f"Set should end error: {e}")

    async def get_context(self) -> Optional[dict]:
        """获取当前会话上下文

        Returns:
            会话上下文字典，如果会话不存在则返回None
        """
        try:
            context = await self.state_manager.get_session(self.session_id)
            if context is None:
                return None
            return context.model_dump()
        except Exception as e:
            print(f"Get context error: {e}")
            return None

    async def run_loop(
        self,
        jd: JobDescription,
        on_end_callback: Optional[Callable[[str], None]] = None
    ):
        """异步监控循环，定期分析并发送指令

        Args:
            jd: 岗位描述
            on_end_callback: 面试结束时的回调函数
        """
        self.is_running = True
        self.start_time = datetime.now()

        while self.is_running:
            try:
                # 获取当前上下文
                context = await self.get_context()
                if not context:
                    await asyncio.sleep(5)
                    continue

                conversation_history = context.get("conversation_history", [])

                # 分析
                decision = await self.analyze(jd, conversation_history)

                # 发送引导指令
                if decision.should_guide and decision.directive:
                    await self.push_directive(decision.directive)
                    print(f"[Controller] 发送引导指令: {decision.directive}")

                # 检查是否结束
                if decision.should_end:
                    await self.set_should_end(True, decision.end_reason)
                    print(f"[Controller] 面试结束: {decision.end_reason}")
                    if on_end_callback:
                        if asyncio.iscoroutinefunction(on_end_callback):
                            await on_end_callback(decision.end_reason)
                        else:
                            on_end_callback(decision.end_reason)
                    break

                # 检查最大时长
                if self.start_time:
                    elapsed = (datetime.now() - self.start_time).seconds
                    if elapsed > self.max_duration:
                        await self.set_should_end(True, "面试时间已达上限")
                        print("[Controller] 面试时间已达上限")
                        if on_end_callback:
                            if asyncio.iscoroutinefunction(on_end_callback):
                                await on_end_callback("面试时间已达上限")
                            else:
                                on_end_callback("面试时间已达上限")
                        break

                # 每10秒分析一次
                await asyncio.sleep(10)

            except Exception as e:
                print(f"[Controller] Error: {e}")
                await asyncio.sleep(5)

    def stop(self):
        """停止监控循环"""
        self.is_running = False
        print("[Controller] 停止监控")
