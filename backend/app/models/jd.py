from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class InterviewConfig(BaseModel):
    written_question_count: int = 5
    voice_max_duration: int = 30  # 分钟
    focus_areas: list[str] = Field(default_factory=list)
    difficulty: str = "medium"  # easy/medium/hard

class JobDescription(BaseModel):
    id: str = ""
    title: str
    department: str = ""
    description: str
    requirements: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    interview_config: InterviewConfig = Field(default_factory=InterviewConfig)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

class JDCreateRequest(BaseModel):
    title: str
    department: str = ""
    description: str
    requirements: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    interview_config: Optional[InterviewConfig] = None

class JDUpdateRequest(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[list[str]] = None
    required_skills: Optional[list[str]] = None
    preferred_skills: Optional[list[str]] = None
    interview_config: Optional[InterviewConfig] = None
