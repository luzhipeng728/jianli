# backend/app/agents/evaluator_agent.py
"""Evaluator Agent - generates post-interview evaluation report"""

import json
from typing import Optional
from app.services.llm_client import LLMClient
from app.models.interview_record import InterviewRecord, EvaluationReport, EvaluationDimension

class EvaluatorAgent:
    """Generates comprehensive evaluation after interview ends"""

    def __init__(self):
        self.llm = LLMClient()

    def _build_evaluation_prompt(
        self,
        record: InterviewRecord,
        job_info: str
    ) -> str:
        """Build prompt for evaluation"""

        # Format dialogue for analysis
        dialogue_text = ""
        for d in record.dialogues:
            role_label = "面试官" if d.role.value == "interviewer" else "候选人"
            dialogue_text += f"\n[{d.phase}] {role_label}: {d.content}"

        return f"""你是一位资深的面试评估专家。请根据以下面试记录，生成全面的评估报告。

## 岗位信息
{job_info}

## 面试记录
{dialogue_text}

## 面试时长
总轮次: {len([d for d in record.dialogues if d.role.value == 'candidate'])}
阶段: {', '.join(set(d.phase for d in record.dialogues))}

## 评估要求
请从以下维度评估候选人（每项1-10分）：
1. 技术能力 (权重0.3) - 专业技能、技术深度
2. 项目经验 (权重0.25) - 项目复杂度、个人贡献
3. 沟通表达 (权重0.15) - 表达清晰度、逻辑性
4. 学习能力 (权重0.15) - 学习态度、成长潜力
5. 文化匹配 (权重0.15) - 价值观、团队协作

## 输出格式 (JSON)
{{
    "overall_score": 总分(1-100),
    "recommendation": "strongly_recommend|recommend|neutral|not_recommend",
    "dimensions": [
        {{"name": "技术能力", "score": 分数, "weight": 0.3, "feedback": "评语"}},
        ...
    ],
    "highlights": ["亮点1", "亮点2"],
    "concerns": ["顾虑1", "顾虑2"],
    "summary": "总结评语（100字以内）"
}}

请只返回JSON，不要其他内容。"""

    async def evaluate(
        self,
        record: InterviewRecord,
        job_info: str
    ) -> EvaluationReport:
        """Generate evaluation report

        Args:
            record: Complete interview record
            job_info: Job description info

        Returns:
            EvaluationReport
        """
        prompt = self._build_evaluation_prompt(record, job_info)

        messages = [
            {"role": "system", "content": "你是专业的面试评估专家，请严格按照JSON格式输出评估报告。"},
            {"role": "user", "content": prompt}
        ]

        response = await self.llm.chat_async(
            messages=messages,
            temperature=0.3  # Lower temperature for consistent evaluation
        )

        # Parse JSON response
        try:
            # Clean up response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response.strip())

            # Convert dimensions
            dimensions = []
            for dim in data.get("dimensions", []):
                dimensions.append(EvaluationDimension(
                    name=dim["name"],
                    score=dim["score"],
                    weight=dim["weight"],
                    feedback=dim.get("feedback", "")
                ))

            report = EvaluationReport(
                overall_score=data.get("overall_score", 0),
                recommendation=data.get("recommendation", "neutral"),
                dimensions=dimensions,
                highlights=data.get("highlights", []),
                concerns=data.get("concerns", []),
                summary=data.get("summary", "")
            )

            return report

        except json.JSONDecodeError as e:
            # Return default report on parse error
            print(f"Evaluation parse error: {e}, response: {response[:200]}")
            return EvaluationReport(
                overall_score=0,
                recommendation="neutral",
                summary="评估生成失败，请人工评估"
            )
