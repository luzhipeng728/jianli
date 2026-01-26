"""
分析维度模型

支持三种类型的维度：
1. screening - 简历筛选匹配维度（技能、经验、教育等）
2. evaluation - 面试评估维度（专业能力、沟通表达等）
3. parsing - 简历解析关注点（警告类型、重点提取等）
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class AnalysisDimension(BaseModel):
    """分析维度"""
    id: str = ""
    name: str  # 维度名称
    type: Literal["screening", "evaluation", "parsing"] = "screening"  # 维度类型
    weight: float = 0.0  # 权重（0-1，screening和evaluation使用）
    description: str = ""  # 维度描述
    prompt_hint: str = ""  # 给LLM的提示词
    is_default: bool = False  # 是否为系统默认维度
    is_enabled: bool = True  # 是否启用
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class DimensionCreateRequest(BaseModel):
    """创建维度请求"""
    name: str
    type: Literal["screening", "evaluation", "parsing"] = "screening"
    weight: float = 0.0
    description: str = ""
    prompt_hint: str = ""


class DimensionUpdateRequest(BaseModel):
    """更新维度请求"""
    name: Optional[str] = None
    weight: Optional[float] = None
    description: Optional[str] = None
    prompt_hint: Optional[str] = None
    is_enabled: Optional[bool] = None


# 默认的筛选维度
DEFAULT_SCREENING_DIMENSIONS = [
    {
        "name": "技能匹配",
        "type": "screening",
        "weight": 0.40,
        "description": "技术技能与岗位要求的匹配程度",
        "prompt_hint": "评估候选人的硬技能和软技能与岗位要求的匹配度，重点关注核心技术栈的匹配",
        "is_default": True
    },
    {
        "name": "工作经验",
        "type": "screening",
        "weight": 0.30,
        "description": "工作年限和相关经验的匹配程度",
        "prompt_hint": "评估候选人的工作年限、行业经验、相关项目经验是否符合岗位需求",
        "is_default": True
    },
    {
        "name": "教育背景",
        "type": "screening",
        "weight": 0.15,
        "description": "学历和专业背景的匹配程度",
        "prompt_hint": "评估候选人的学历层次、毕业院校、专业背景是否符合岗位要求",
        "is_default": True
    },
    {
        "name": "求职意向",
        "type": "screening",
        "weight": 0.15,
        "description": "求职意向与岗位的匹配程度",
        "prompt_hint": "评估候选人的期望职位、期望薪资、工作地点等是否与岗位匹配",
        "is_default": True
    }
]

# 默认的面试评估维度
DEFAULT_EVALUATION_DIMENSIONS = [
    {
        "name": "专业能力",
        "type": "evaluation",
        "weight": 0.30,
        "description": "技术深度、问题解决能力",
        "prompt_hint": "评估候选人在专业领域的深度和广度，以及解决实际问题的能力",
        "is_default": True
    },
    {
        "name": "沟通表达",
        "type": "evaluation",
        "weight": 0.20,
        "description": "表达清晰度、逻辑性",
        "prompt_hint": "评估候选人的语言表达能力、沟通技巧和逻辑思维",
        "is_default": True
    },
    {
        "name": "逻辑思维",
        "type": "evaluation",
        "weight": 0.20,
        "description": "分析问题、推理能力",
        "prompt_hint": "评估候选人分析和解决复杂问题的能力，以及逻辑推理能力",
        "is_default": True
    },
    {
        "name": "学习能力",
        "type": "evaluation",
        "weight": 0.15,
        "description": "知识广度、学习态度",
        "prompt_hint": "评估候选人的学习能力、对新技术的适应能力和求知欲",
        "is_default": True
    },
    {
        "name": "岗位匹配度",
        "type": "evaluation",
        "weight": 0.15,
        "description": "经验匹配、意愿度",
        "prompt_hint": "评估候选人的经验和能力与岗位需求的匹配程度，以及入职意愿",
        "is_default": True
    }
]

# 默认的简历解析关注点
DEFAULT_PARSING_DIMENSIONS = [
    {
        "name": "学历真实性",
        "type": "parsing",
        "weight": 0.0,
        "description": "检测学历造假风险",
        "prompt_hint": "检查是否存在野鸡大学、假学历、学历夸大等问题",
        "is_default": True
    },
    {
        "name": "经历一致性",
        "type": "parsing",
        "weight": 0.0,
        "description": "检查工作经历的时间线一致性",
        "prompt_hint": "检查工作经历是否有时间重叠、时间空白、经历夸大等问题",
        "is_default": True
    },
    {
        "name": "信息完整性",
        "type": "parsing",
        "weight": 0.0,
        "description": "检查关键信息是否完整",
        "prompt_hint": "检查联系方式、工作经历、教育背景等关键信息是否完整",
        "is_default": True
    }
]
