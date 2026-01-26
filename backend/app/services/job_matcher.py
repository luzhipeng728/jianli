"""岗位匹配度算法"""
from typing import Optional
from pydantic import BaseModel
from app.models.resume import ResumeData
from app.services.llm_client import LLMClient
from app.services.dimension_service import get_dimension_service


class JobRequirement(BaseModel):
    """岗位需求"""
    title: str  # 岗位名称
    description: str = ""  # 岗位描述
    required_skills: list[str] = []  # 必需技能
    preferred_skills: list[str] = []  # 优先技能
    min_experience_years: int = 0  # 最低工作年限
    education_level: str = ""  # 学历要求（本科/硕士/博士）
    location: str = ""  # 工作地点


class MatchResult(BaseModel):
    """匹配结果"""
    overall_score: int  # 总体匹配度 0-100
    skill_score: int  # 技能匹配度
    experience_score: int  # 经验匹配度
    education_score: int  # 学历匹配度
    intention_score: int  # 意向匹配度
    matched_skills: list[str]  # 匹配的技能
    missing_skills: list[str]  # 缺失的技能
    highlights: list[str]  # 亮点
    concerns: list[str]  # 顾虑


class JobMatcher:
    """岗位匹配器"""

    # 学历等级映射
    EDUCATION_LEVELS = {
        "博士": 5,
        "博士后": 5,
        "硕士": 4,
        "研究生": 4,
        "本科": 3,
        "学士": 3,
        "大专": 2,
        "专科": 2,
        "高中": 1,
        "中专": 1,
    }

    def __init__(self):
        self.llm_client = LLMClient()

    def match(self, resume: ResumeData, job: JobRequirement) -> MatchResult:
        """计算简历与岗位的匹配度"""

        # 1. 技能匹配度
        skill_score, matched_skills, missing_skills = self._calculate_skill_match(
            resume.skills.hard_skills + resume.skills.soft_skills,
            job.required_skills,
            job.preferred_skills
        )

        # 2. 经验匹配度
        experience_score = self._calculate_experience_match(
            resume.experience,
            job.min_experience_years,
            job.title
        )

        # 3. 学历匹配度
        education_score = self._calculate_education_match(
            resume.education,
            job.education_level
        )

        # 4. 意向匹配度
        intention_score = self._calculate_intention_match(
            resume.job_intention,
            job
        )

        # 5. 计算总分（加权平均）
        # 从维度服务获取权重，如果获取失败则使用默认值
        try:
            dimension_service = get_dimension_service()
            weights = dimension_service.get_screening_weights()
            # 确保有默认值
            if not weights:
                weights = {"skill": 0.40, "experience": 0.30, "education": 0.15, "intention": 0.15}
        except Exception:
            weights = {"skill": 0.40, "experience": 0.30, "education": 0.15, "intention": 0.15}

        overall_score = int(
            skill_score * weights.get("skill", 0.40) +
            experience_score * weights.get("experience", 0.30) +
            education_score * weights.get("education", 0.15) +
            intention_score * weights.get("intention", 0.15)
        )

        # 6. 生成亮点和顾虑
        highlights, concerns = self._generate_insights(
            resume, job, matched_skills, missing_skills,
            skill_score, experience_score, education_score
        )

        return MatchResult(
            overall_score=overall_score,
            skill_score=skill_score,
            experience_score=experience_score,
            education_score=education_score,
            intention_score=intention_score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            highlights=highlights,
            concerns=concerns
        )

    def _calculate_skill_match(
        self,
        resume_skills: list[str],
        required_skills: list[str],
        preferred_skills: list[str]
    ) -> tuple[int, list[str], list[str]]:
        """计算技能匹配度"""
        resume_skills_lower = [s.lower() for s in resume_skills]

        matched = []
        missing = []

        # 必需技能（权重更高）
        required_matched = 0
        for skill in required_skills:
            skill_lower = skill.lower()
            # 模糊匹配
            if any(skill_lower in rs or rs in skill_lower for rs in resume_skills_lower):
                matched.append(skill)
                required_matched += 1
            else:
                missing.append(skill)

        # 优先技能
        preferred_matched = 0
        for skill in preferred_skills:
            skill_lower = skill.lower()
            if any(skill_lower in rs or rs in skill_lower for rs in resume_skills_lower):
                matched.append(skill)
                preferred_matched += 1

        # 计算分数
        if not required_skills and not preferred_skills:
            score = 70  # 无要求时给基础分
        else:
            required_ratio = required_matched / len(required_skills) if required_skills else 1
            preferred_ratio = preferred_matched / len(preferred_skills) if preferred_skills else 1

            # 必需技能占70%，优先技能占30%
            score = int(required_ratio * 70 + preferred_ratio * 30)

        return score, matched, missing

    def _calculate_experience_match(
        self,
        experiences: list,
        min_years: int,
        job_title: str
    ) -> int:
        """计算经验匹配度"""
        if not experiences:
            return 30 if min_years == 0 else 0

        # 计算总工作年限
        total_years = 0
        relevant_years = 0
        job_title_lower = job_title.lower()

        for exp in experiences:
            years = self._calculate_years(exp.start_date, exp.end_date)
            total_years += years

            # 检查是否相关经验
            title_lower = exp.title.lower() if exp.title else ""
            duties_lower = exp.duties.lower() if exp.duties else ""

            if job_title_lower in title_lower or job_title_lower in duties_lower:
                relevant_years += years

        # 计算分数
        if min_years == 0:
            base_score = 70
        else:
            year_ratio = min(1.0, total_years / min_years)
            base_score = int(year_ratio * 80)

        # 相关经验加分
        if relevant_years > 0:
            base_score = min(100, base_score + 20)

        return base_score

    def _calculate_education_match(
        self,
        educations: list,
        required_level: str
    ) -> int:
        """计算学历匹配度"""
        if not educations:
            return 50

        # 获取最高学历
        max_level = 0
        for edu in educations:
            degree = edu.degree or ""
            for level_name, level_value in self.EDUCATION_LEVELS.items():
                if level_name in degree:
                    max_level = max(max_level, level_value)
                    break

        if not required_level:
            return 80  # 无要求时给基础分

        # 获取要求学历等级
        required_level_value = 0
        for level_name, level_value in self.EDUCATION_LEVELS.items():
            if level_name in required_level:
                required_level_value = level_value
                break

        # 计算分数
        if max_level >= required_level_value:
            return 100
        elif max_level == required_level_value - 1:
            return 70
        else:
            return 40

    def _calculate_intention_match(
        self,
        intention,
        job: JobRequirement
    ) -> int:
        """计算求职意向匹配度"""
        score = 70  # 基础分

        # 职位匹配
        if intention.position and job.title:
            if intention.position.lower() in job.title.lower() or job.title.lower() in intention.position.lower():
                score += 15

        # 地点匹配
        if intention.location and job.location:
            if intention.location in job.location or job.location in intention.location:
                score += 15

        return min(100, score)

    def _calculate_years(self, start_date: str, end_date: str) -> int:
        """计算工作年限"""
        try:
            start = start_date or ""
            end = end_date or "至今"

            start_year = int(start.split(".")[0]) if start and start[0].isdigit() else 0
            end_year = 2025 if "至今" in end else (int(end.split(".")[0]) if end and end[0].isdigit() else 0)

            if start_year and end_year:
                return max(0, end_year - start_year)
        except:
            pass
        return 0

    def _generate_insights(
        self,
        resume: ResumeData,
        job: JobRequirement,
        matched_skills: list[str],
        missing_skills: list[str],
        skill_score: int,
        experience_score: int,
        education_score: int
    ) -> tuple[list[str], list[str]]:
        """生成亮点和顾虑"""
        highlights = []
        concerns = []

        # 技能亮点
        if len(matched_skills) >= 3:
            highlights.append(f"技能匹配度高，掌握 {', '.join(matched_skills[:3])} 等核心技能")

        # 经验亮点
        if experience_score >= 80:
            total_years = sum(self._calculate_years(e.start_date, e.end_date) for e in resume.experience)
            if total_years > 0:
                highlights.append(f"拥有 {total_years} 年相关工作经验")

        # 教育亮点
        if education_score >= 90 and resume.education:
            edu = resume.education[0]
            highlights.append(f"{edu.school} {edu.degree} 学历背景")

        # 技能顾虑
        if missing_skills:
            concerns.append(f"缺少关键技能: {', '.join(missing_skills[:3])}")

        # 经验顾虑
        if experience_score < 60:
            concerns.append("工作经验可能不足")

        # 学历顾虑
        if education_score < 60:
            concerns.append("学历可能不满足要求")

        # 风险警告
        if resume.warnings:
            concerns.append(f"简历存在 {len(resume.warnings)} 个风险警告")

        return highlights, concerns

    async def smart_match(
        self,
        resume: ResumeData,
        job_req: JobRequirement
    ) -> MatchResult:
        """使用LLM进行智能匹配分析（中文返回）"""
        # 构建简洁的简历摘要
        skills_text = ', '.join(resume.skills.hard_skills[:10]) if resume.skills.hard_skills else '未提供'
        exp_text = '; '.join([f'{e.company}-{e.title}({e.start_date or ""}~{e.end_date or "至今"})' for e in resume.experience[:3]]) if resume.experience else '无'
        edu_text = f"{resume.education[0].school} {resume.education[0].degree}" if resume.education else '未知'

        # 构建岗位要求摘要
        jd_skills = ', '.join(job_req.required_skills[:8]) if job_req.required_skills else '未指定'
        jd_preferred = ', '.join(job_req.preferred_skills[:5]) if job_req.preferred_skills else '无'

        prompt = f"""你是一个专业的HR助手，请用中文分析候选人与岗位的匹配度。

## 岗位信息
- 岗位: {job_req.title}
- 必需技能: {jd_skills}
- 加分技能: {jd_preferred}
- 岗位描述: {job_req.description[:200] if job_req.description else '无'}

## 候选人信息
- 姓名: {resume.basic_info.name}
- 技能: {skills_text}
- 工作经历: {exp_text}
- 学历: {edu_text}

请快速评估并返回JSON（必须用中文）：
{{
  "overall_score": 0-100的总体匹配分数,
  "skill_score": 0-100的技能匹配分,
  "experience_score": 0-100的经验匹配分,
  "education_score": 0-100的学历匹配分,
  "matched_skills": ["匹配的技能1", "技能2"],
  "missing_skills": ["缺失的关键技能"],
  "highlights": ["亮点（一句话）"],
  "concerns": ["顾虑（一句话）"],
  "reason": "一句话评估理由"
}}

只返回JSON，不要其他内容。"""

        try:
            result = await self.llm_client.chat(prompt)
            # 尝试提取JSON
            import json
            import re
            # 尝试匹配JSON块
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(result.strip())

            return MatchResult(
                overall_score=data.get("overall_score", 50),
                skill_score=data.get("skill_score", 50),
                experience_score=data.get("experience_score", 50),
                education_score=data.get("education_score", 50),
                intention_score=50,
                matched_skills=data.get("matched_skills", []),
                missing_skills=data.get("missing_skills", []),
                highlights=data.get("highlights", []),
                concerns=data.get("concerns", [])
            )
        except Exception as e:
            print(f"[JobMatcher] AI匹配失败，回退到规则匹配: {e}")
            # 回退到规则匹配
            return self.match(resume, job_req)


# 全局匹配器实例
job_matcher = JobMatcher()
