"""
维度分析服务 - 使用LLM对简历进行多维度分析
支持动态维度配置，可扩展的分析维度
"""
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from app.services.llm_client import LLMClient
from app.services.dimension_service import get_dimension_service


@dataclass
class DimensionScore:
    """单个维度评分"""
    name: str  # 维度名称
    score: int  # 评分 0-100
    level: str  # 等级：优秀/良好/一般/不足
    highlights: List[str] = field(default_factory=list)  # 亮点
    concerns: List[str] = field(default_factory=list)  # 问题


@dataclass
class DimensionAnalysisResult:
    """维度分析结果"""
    resume_id: str
    dimensions: List[DimensionScore]  # 各维度评分
    overall_score: int  # 总体评分
    summary: str  # 综合评估
    recommendations: List[str]  # 建议
    analysis_source: str = "AI多维度分析"  # 分析来源


class DimensionAnalyzer:
    """维度分析器"""

    def __init__(self):
        self.llm_client = LLMClient()
        self.dimension_service = get_dimension_service()

    async def analyze_resume(
        self,
        resume_data: dict,
        analysis_type: str = "screening",
        jd_data: Optional[dict] = None
    ) -> DimensionAnalysisResult:
        """
        对简历进行多维度分析

        Args:
            resume_data: 简历数据（ResumeData的字典形式）
            analysis_type: 分析类型（screening/evaluation/parsing）
            jd_data: 岗位数据（可选，用于岗位匹配分析）

        Returns:
            DimensionAnalysisResult: 分析结果
        """
        # 获取启用的维度配置
        if analysis_type == "screening":
            dimensions = self.dimension_service.get_screening_prompts()
        elif analysis_type == "evaluation":
            dimensions = self.dimension_service.get_evaluation_dimensions()
        elif analysis_type == "parsing":
            dimensions = self.dimension_service.get_parsing_prompts()
        else:
            dimensions = []

        if not dimensions:
            # 如果没有配置维度，使用默认维度
            dimensions = self._get_default_dimensions(analysis_type)

        # 构建分析prompt
        prompt = self._build_analysis_prompt(
            resume_data, dimensions, jd_data, analysis_type
        )

        # 调用LLM进行分析
        result_text = await self.llm_client.chat(prompt)

        # 解析结果
        return self._parse_analysis_result(
            result_text, resume_data.get("id", ""), dimensions
        )

    def _get_default_dimensions(self, analysis_type: str) -> List[dict]:
        """获取默认维度配置"""
        if analysis_type == "screening":
            return [
                {"name": "技能匹配", "weight": 0.40, "description": "技术技能与岗位要求的匹配程度", "prompt_hint": "评估硬技能和软技能的匹配度"},
                {"name": "工作经验", "weight": 0.30, "description": "工作年限和相关经验的匹配程度", "prompt_hint": "评估工作年限、行业经验、相关项目经验"},
                {"name": "教育背景", "weight": 0.15, "description": "学历和专业背景的匹配程度", "prompt_hint": "评估学历层次、毕业院校、专业背景"},
                {"name": "求职意向", "weight": 0.15, "description": "求职意向与岗位的匹配程度", "prompt_hint": "评估期望职位、期望薪资、工作地点匹配度"},
            ]
        elif analysis_type == "evaluation":
            return [
                {"name": "专业能力", "weight": 0.30, "description": "技术深度、问题解决能力"},
                {"name": "沟通表达", "weight": 0.20, "description": "表达清晰度、逻辑性"},
                {"name": "逻辑思维", "weight": 0.20, "description": "分析问题、推理能力"},
                {"name": "学习能力", "weight": 0.15, "description": "知识广度、学习态度"},
                {"name": "岗位匹配度", "weight": 0.15, "description": "经验匹配、意愿度"},
            ]
        else:
            return [
                {"name": "学历真实性", "description": "检测学历造假风险"},
                {"name": "经历一致性", "description": "检查工作经历的时间线一致性"},
                {"name": "信息完整性", "description": "检查关键信息是否完整"},
            ]

    def _build_analysis_prompt(
        self,
        resume_data: dict,
        dimensions: List[dict],
        jd_data: Optional[dict],
        analysis_type: str
    ) -> str:
        """构建分析prompt"""
        # 提取简历关键信息
        basic_info = resume_data.get("basic_info", {})
        education = resume_data.get("education", [])
        experience = resume_data.get("experience", [])
        skills = resume_data.get("skills", {})
        warnings = resume_data.get("education_warnings", [])

        # 构建简历摘要
        education_text = "; ".join([
            f"{e.get('school', '')} {e.get('degree', '')} {e.get('major', '')}"
            for e in education[:3]
        ]) if education else "未提供"

        experience_text = "; ".join([
            f"{e.get('company', '')} {e.get('title', '')}({e.get('start_date', '')}-{e.get('end_date', '至今')})"
            for e in experience[:3]
        ]) if experience else "无"

        skills_text = ", ".join(skills.get("hard_skills", [])[:15]) if skills else "无"
        soft_skills_text = ", ".join(skills.get("soft_skills", [])[:10]) if skills else "无"

        # 构建维度描述
        dimension_descriptions = "\n".join([
            f"- {d['name']}: {d.get('description', '')}。提示: {d.get('prompt_hint', d.get('description', ''))}"
            for d in dimensions
        ])

        # 构建JD信息（如果提供）
        jd_section = ""
        if jd_data:
            jd_section = f"""
## 岗位要求（用于匹配分析）
- 岗位名称: {jd_data.get('title', '')}
- 岗位描述: {jd_data.get('description', '')[:300] if jd_data.get('description') else '无'}
- 必需技能: {', '.join(jd_data.get('required_skills', [])[:10]) if jd_data.get('required_skills') else '无'}
- 加分技能: {', '.join(jd_data.get('preferred_skills', [])[:5]) if jd_data.get('preferred_skills') else '无'}
"""

        # 分析类型特定说明
        analysis_instruction = {
            "screening": "请根据岗位要求，分析候选人在各维度的匹配程度",
            "evaluation": "请从专业角度评估候选人在各维度的能力水平",
            "parsing": "请检查简历在各维度是否存在问题或风险"
        }.get(analysis_type, "请分析候选人的简历")

        prompt = f"""你是一个专业的HR分析师，请对以下简历进行多维度分析。

{analysis_instruction}，每个维度给出0-100的评分、等级判定、亮点和问题。

## 分析维度
{dimension_descriptions}

{jd_section}

## 简历信息
- 姓名: {basic_info.get('name', '未知')}
- 年龄: {basic_info.get('age', '未知')}
- 联系方式: {basic_info.get('phone', '')} / {basic_info.get('email', '')}

### 教育背景
{education_text}

### 工作经历
{experience_text}

### 技能
- 硬技能: {skills_text}
- 软技能: {soft_skills_text}

### 学历风险警告
{len(warnings)} 个警告需要关注

## 输出要求
请返回JSON格式（不要用```json包裹）：
{{
  "dimensions": [
    {{
      "name": "维度名称",
      "score": 0-100的分数,
      "level": "优秀(90+) / 良好(75-89) / 一般(60-74) / 不足(<60)",
      "highlights": ["亮点1", "亮点2"],
      "concerns": ["问题1", "问题2"]
    }}
  ],
  "overall_score": 0-100的总体评分,
  "summary": "一句话综合评估",
  "recommendations": ["建议1", "建议2"]
}}

只返回JSON，不要其他内容。"""
        return prompt

    def _parse_analysis_result(
        self,
        result_text: str,
        resume_id: str,
        dimensions: List[dict]
    ) -> DimensionAnalysisResult:
        """解析LLM返回的分析结果"""
        try:
            # 提取JSON
            result_text = result_text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]

            data = json.loads(result_text)

            # 解析各维度评分
            dimension_scores = []
            for dim_data in data.get("dimensions", []):
                # 找到对应的维度配置获取权重
                dim_config = next(
                    (d for d in dimensions if d["name"] == dim_data.get("name")),
                    None
                )

                dimension_scores.append(DimensionScore(
                    name=dim_data.get("name", "未知维度"),
                    score=int(dim_data.get("score", 50)),
                    level=dim_data.get("level", "一般"),
                    highlights=dim_data.get("highlights", []),
                    concerns=dim_data.get("concerns", [])
                ))

            # 如果LLM没有返回所有维度，补充默认值
            analyzed_names = {d.name for d in dimension_scores}
            for dim_config in dimensions:
                if dim_config["name"] not in analyzed_names:
                    dimension_scores.append(DimensionScore(
                        name=dim_config["name"],
                        score=50,
                        level="一般",
                        highlights=[],
                        concerns=["LLM未返回该维度的分析"]
                    ))

            return DimensionAnalysisResult(
                resume_id=resume_id,
                dimensions=dimension_scores,
                overall_score=int(data.get("overall_score", 50)),
                summary=data.get("summary", ""),
                recommendations=data.get("recommendations", [])
            )

        except Exception as e:
            print(f"[DimensionAnalyzer] 解析分析结果失败: {e}")
            # 返回默认结果
            return DimensionAnalysisResult(
                resume_id=resume_id,
                dimensions=[
                    DimensionScore(
                        name=d["name"],
                        score=50,
                        level="一般",
                        highlights=[],
                        concerns=["分析失败，请重试"]
                    )
                    for d in dimensions
                ],
                overall_score=50,
                summary="分析服务暂时不可用",
                recommendations=["请稍后重试"]
            )

    def calculate_weighted_score(self, result: DimensionAnalysisResult) -> int:
        """根据维度权重计算加权总分"""
        dimensions = self.dimension_service.list(dim_type="screening", enabled_only=True)
        weights = {d.name: d.weight for d in dimensions}

        weighted_sum = 0
        total_weight = 0

        for dim_score in result.dimensions:
            weight = weights.get(dim_score.name, 0.25)
            weighted_sum += dim_score.score * weight
            total_weight += weight

        return int(weighted_sum / total_weight) if total_weight > 0 else result.overall_score


# 全局分析器实例
dimension_analyzer = DimensionAnalyzer()


async def analyze_resume_dimensions(
    resume_data: dict,
    analysis_type: str = "screening",
    jd_data: Optional[dict] = None
) -> DimensionAnalysisResult:
    """便捷函数：分析简历维度"""
    return await dimension_analyzer.analyze_resume(resume_data, analysis_type, jd_data)
