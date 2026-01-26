"""评估报告生成Agent - 根据面试记录生成详细评估报告"""

from app.services.llm_client import LLMClient
from app.models.interview import (
    InterviewSession, Evaluation, DimensionScore,
    WrittenTest, VoiceInterview
)
from app.models.jd import JobDescription
from app.models.resume import ResumeData
from app.services.dimension_service import get_dimension_service
import json

# 默认评估维度（作为后备方案）
DEFAULT_DIMENSIONS = [
    {"name": "专业能力", "weight": 0.30, "description": "技术深度、问题解决能力"},
    {"name": "沟通表达", "weight": 0.20, "description": "表达清晰度、逻辑性"},
    {"name": "逻辑思维", "weight": 0.20, "description": "分析问题、推理能力"},
    {"name": "学习能力", "weight": 0.15, "description": "知识广度、学习态度"},
    {"name": "岗位匹配度", "weight": 0.15, "description": "经验匹配、意愿度"}
]


def _get_evaluation_dimensions() -> list[dict]:
    """获取评估维度（从维度服务或使用默认值）"""
    try:
        dimension_service = get_dimension_service()
        dims = dimension_service.get_evaluation_dimensions()
        if dims:
            return dims
    except Exception:
        pass
    return DEFAULT_DIMENSIONS

class EvaluationAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def generate_evaluation(
        self,
        session: InterviewSession,
        jd: JobDescription,
        resume: ResumeData
    ) -> Evaluation:
        """生成完整评估报告"""

        # 准备笔试信息
        written_info = ""
        if session.written_test:
            wt = session.written_test
            written_info = f"""
## 笔试成绩
- 得分：{wt.score}/100
- 题目数：{len(wt.questions)}
- 正确数：{len([a for a in wt.answers if a.is_correct])}
"""

        # 准备语音面试信息
        voice_info = ""
        if session.voice_interview and session.voice_interview.transcript:
            vi = session.voice_interview
            transcript_text = "\n".join([
                f"{'面试官' if m.role == 'interviewer' else '候选人'}: {m.content}"
                for m in vi.transcript[:50]  # 限制长度
            ])
            voice_info = f"""
## 语音面试记录
- 时长：{vi.duration // 60} 分钟
- 对话轮数：{len(vi.transcript)}

### 对话内容
{transcript_text}
"""

        # 获取评估维度（可配置）
        dimensions = _get_evaluation_dimensions()
        dimensions_text = "\n".join([
            f"{i+1}. {d['name']} ({int(d['weight']*100)}%) - {d['description']}"
            for i, d in enumerate(dimensions)
        ])
        dimensions_example = ", ".join([
            f'{{"name": "{d["name"]}", "score": 80, "weight": {d["weight"]}, "analysis": "分析内容..."}}'
            for d in dimensions[:2]
        ]) + ", ..."

        system_prompt = f"""你是一位资深HR，负责根据面试记录生成专业的评估报告。

## 评估维度
{dimensions_text}

## 输出格式（JSON）
{{
  "overall_score": 75,
  "recommendation": "recommend",  // strongly_recommend/recommend/neutral/not_recommend
  "dimensions": [
    {dimensions_example}
  ],
  "highlights": ["亮点1", "亮点2"],
  "concerns": ["风险点1", "风险点2"],
  "summary": "一句话总结",
  "detailed_analysis": "详细分析（200-300字）"
}}

## 评分标准
- 90-100: 优秀，强烈推荐
- 75-89: 良好，推荐
- 60-74: 一般，待定
- 60以下: 不推荐"""

        user_prompt = f"""请根据以下信息生成评估报告：

## 岗位信息
- 岗位：{jd.title}
- 要求：{', '.join(jd.requirements[:5])}
- 必需技能：{', '.join(jd.required_skills)}

## 候选人信息
- 姓名：{resume.basic_info.name}
- 技能：{', '.join(resume.skills.hard_skills[:10])}
{written_info}
{voice_info}

请生成详细的评估报告（JSON格式）："""

        response = await self.llm.chat_async(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )

        try:
            # 提取JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            data = json.loads(response.strip())

            return Evaluation(
                overall_score=data["overall_score"],
                recommendation=data["recommendation"],
                dimensions=[DimensionScore(**d) for d in data["dimensions"]],
                highlights=data.get("highlights", []),
                concerns=data.get("concerns", []),
                summary=data.get("summary", ""),
                detailed_analysis=data.get("detailed_analysis", "")
            )
        except Exception as e:
            # 返回默认评估
            return Evaluation(
                overall_score=0,
                recommendation="neutral",
                summary=f"评估生成失败: {str(e)}"
            )

evaluation_agent = EvaluationAgent()
