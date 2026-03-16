from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class Education(BaseModel):
    school: str = ""
    degree: str = ""
    major: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    # 学校验证信息（由系统自动验证）
    school_verified: bool = False  # 是否为教育部承认的正规高校
    school_verification_source: str = ""  # 验证数据来源
    school_verification_message: str = ""  # 验证说明（如：精确匹配、模糊匹配等）
    school_level: str = ""  # 办学层次（本科/专科）
    school_department: str = ""  # 主管部门

class Experience(BaseModel):
    company: str = ""
    title: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duties: str = ""

class Skills(BaseModel):
    hard_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)

class JobIntention(BaseModel):
    position: str = ""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    location: str = ""

class Warning(BaseModel):
    type: str  # fake_education, time_conflict, etc.
    message: str

class EducationWarning(BaseModel):
    """学历造假风险警告"""
    risk_level: str = "medium"  # high, medium, low
    type: str  # fake_university, diploma_mill, degree_inflation, timeline_fraud, overseas_fake, info_missing
    message: str

class RecommendedJD(BaseModel):
    jd_id: str
    jd_title: str
    match_score: int
    matched_skills: list[str] = Field(default_factory=list)

class DimensionScore(BaseModel):
    """维度评分"""
    name: str = ""  # 维度名称
    score: int = 50  # 评分 0-100
    level: str = "一般"  # 等级：优秀/良好/一般/不足
    highlights: list[str] = Field(default_factory=list)  # 亮点
    concerns: list[str] = Field(default_factory=list)  # 问题

class DimensionAnalysis(BaseModel):
    """维度分析结果"""
    dimensions: list[DimensionScore] = Field(default_factory=list)
    overall_score: int = 50  # 总体评分
    summary: str = ""  # 综合评估
    recommendations: list[str] = Field(default_factory=list)  # 建议
    analysis_date: Optional[str] = None  # 分析时间

class BasicInfo(BaseModel):
    name: str = ""
    phone: str = ""
    email: str = ""
    age: Optional[int] = None
    gender: str = ""

class ResumeData(BaseModel):
    id: str = ""
    file_name: str = ""
    file_type: str = ""
    raw_text: str = ""
    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    job_intention: JobIntention = Field(default_factory=JobIntention)
    education_warnings: list[EducationWarning] = Field(default_factory=list)  # 学历造假风险（重点）
    warnings: list[Warning] = Field(default_factory=list)
    recommended_jds: list[RecommendedJD] = Field(default_factory=list)  # 推荐的JD列表
    dimension_analysis: Optional[DimensionAnalysis] = None  # 维度分析结果
    match_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ResumeUploadResponse(BaseModel):
    id: str
    status: str
    data: Optional[ResumeData] = None
    error: Optional[str] = None
