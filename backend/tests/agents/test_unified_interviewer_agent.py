import pytest
from unittest.mock import AsyncMock, patch
from app.agents.unified_interviewer_agent import UnifiedInterviewerAgent
from app.models.interview_phase import InterviewPhase

@pytest.fixture
def agent():
    return UnifiedInterviewerAgent(
        session_id="test-123",
        resume_summary="张三，5年Python开发经验",
        job_info="高级后端工程师，要求Python、FastAPI"
    )

@pytest.mark.asyncio
async def test_generate_opening(agent):
    with patch.object(agent.llm, 'chat_async', new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "你好，我是今天的面试官。"

        response = await agent.generate_response(
            phase=InterviewPhase.OPENING,
            round_number=0,
            conversation_history=[]
        )

        assert "面试官" in mock_chat.call_args[1]["messages"][0]["content"]
        assert response == "你好，我是今天的面试官。"

@pytest.mark.asyncio
async def test_phase_specific_prompts(agent):
    with patch.object(agent.llm, 'chat_async', new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "请介绍一个你做过的项目"

        await agent.generate_response(
            phase=InterviewPhase.PROJECT_DEEP,
            round_number=1,
            conversation_history=[
                {"role": "assistant", "content": "请做自我介绍"},
                {"role": "user", "content": "我是张三..."}
            ]
        )

        # Check that phase hint is in system prompt
        system_prompt = mock_chat.call_args[1]["messages"][0]["content"]
        assert "项目" in system_prompt or "深入" in system_prompt
