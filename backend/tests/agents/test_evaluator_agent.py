# backend/tests/agents/test_evaluator_agent.py
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.evaluator_agent import EvaluatorAgent
from app.models.interview_record import InterviewRecord, EvaluationReport

@pytest.fixture
def agent():
    return EvaluatorAgent()

@pytest.fixture
def sample_record():
    record = InterviewRecord(
        session_id="test-123",
        resume_id="resume-456",
        jd_id="jd-789"
    )
    record.add_dialogue(role="interviewer", content="请介绍一下你自己")
    record.add_dialogue(role="candidate", content="我是张三，有5年Python开发经验...")
    record.add_dialogue(role="interviewer", content="说说你最有挑战的项目")
    record.add_dialogue(role="candidate", content="我们做了一个高并发系统...")
    return record

@pytest.mark.asyncio
async def test_generate_evaluation(agent, sample_record):
    mock_response = '''{
        "overall_score": 75,
        "recommendation": "recommend",
        "dimensions": [
            {"name": "技术能力", "score": 8, "weight": 0.4, "feedback": "扎实的Python基础"}
        ],
        "highlights": ["有高并发经验"],
        "concerns": ["需要了解更多系统设计"],
        "summary": "候选人整体表现良好"
    }'''

    with patch.object(agent.llm, 'chat_async', new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = mock_response

        report = await agent.evaluate(
            record=sample_record,
            job_info="高级后端工程师"
        )

        assert isinstance(report, EvaluationReport)
        assert report.overall_score == 75
        assert report.recommendation == "recommend"
        assert len(report.dimensions) == 1
        assert report.dimensions[0].name == "技术能力"
        assert report.dimensions[0].score == 8
        assert len(report.highlights) == 1
        assert len(report.concerns) == 1
        assert report.summary == "候选人整体表现良好"

@pytest.mark.asyncio
async def test_evaluation_with_json_markdown(agent, sample_record):
    """Test handling of JSON response wrapped in markdown code blocks"""
    mock_response = '''```json
    {
        "overall_score": 85,
        "recommendation": "strongly_recommend",
        "dimensions": [
            {"name": "技术能力", "score": 9, "weight": 0.3, "feedback": "优秀"}
        ],
        "highlights": ["技术扎实"],
        "concerns": [],
        "summary": "强烈推荐"
    }
    ```'''

    with patch.object(agent.llm, 'chat_async', new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = mock_response

        report = await agent.evaluate(
            record=sample_record,
            job_info="高级后端工程师"
        )

        assert report.overall_score == 85
        assert report.recommendation == "strongly_recommend"

@pytest.mark.asyncio
async def test_evaluation_with_invalid_json(agent, sample_record):
    """Test fallback behavior when JSON parsing fails"""
    mock_response = "This is not valid JSON"

    with patch.object(agent.llm, 'chat_async', new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = mock_response

        report = await agent.evaluate(
            record=sample_record,
            job_info="高级后端工程师"
        )

        assert isinstance(report, EvaluationReport)
        assert report.overall_score == 0
        assert report.recommendation == "neutral"
        assert "评估生成失败" in report.summary

@pytest.mark.asyncio
async def test_evaluation_multiple_dimensions(agent, sample_record):
    """Test evaluation with multiple dimensions"""
    mock_response = '''{
        "overall_score": 80,
        "recommendation": "recommend",
        "dimensions": [
            {"name": "技术能力", "score": 8, "weight": 0.3, "feedback": "扎实的Python基础"},
            {"name": "项目经验", "score": 7, "weight": 0.25, "feedback": "有相关项目经验"},
            {"name": "沟通表达", "score": 9, "weight": 0.15, "feedback": "表达清晰"},
            {"name": "学习能力", "score": 8, "weight": 0.15, "feedback": "学习态度好"},
            {"name": "文化匹配", "score": 8, "weight": 0.15, "feedback": "团队协作能力强"}
        ],
        "highlights": ["技术扎实", "沟通能力强"],
        "concerns": ["项目规模有待提升"],
        "summary": "综合表现优秀，推荐录用"
    }'''

    with patch.object(agent.llm, 'chat_async', new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = mock_response

        report = await agent.evaluate(
            record=sample_record,
            job_info="高级后端工程师"
        )

        assert report.overall_score == 80
        assert len(report.dimensions) == 5
        assert all(d.score >= 1 and d.score <= 10 for d in report.dimensions)
        assert sum(d.weight for d in report.dimensions) == 1.0
