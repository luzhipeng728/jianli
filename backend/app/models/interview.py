from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class InterviewStatus(str, Enum):
    PENDING = "pending"
    WRITTEN_TEST = "written_test"
    VOICE_INTERVIEW = "voice"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class QuestionType(str, Enum):
    SINGLE = "single"
    MULTIPLE = "multiple"
    JUDGMENT = "judgment"

class Question(BaseModel):
    id: str
    type: QuestionType
    content: str
    options: list[str]
    correct_answer: str | list[str]
    explanation: str = ""
    points: int = 10

class Answer(BaseModel):
    question_id: str
    answer: str | list[str]
    is_correct: bool
    time_spent: int = 0
    ai_evaluation: str = ""  # AI对错题的解析（为什么正确答案是对的）

class WrittenTest(BaseModel):
    questions: list[Question] = Field(default_factory=list)
    answers: list[Answer] = Field(default_factory=list)
    score: float = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class TranscriptMessage(BaseModel):
    role: str  # interviewer/candidate
    content: str
    audio_url: Optional[str] = None
    timestamp: datetime
    duration: float = 0

class VoiceInterview(BaseModel):
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration: int = 0
    transcript: list[TranscriptMessage] = Field(default_factory=list)
    audio_url: Optional[str] = None
    end_reason: str = ""

class DimensionScore(BaseModel):
    name: str
    score: int
    weight: float
    analysis: str = ""

class Evaluation(BaseModel):
    overall_score: int = 0
    recommendation: str = ""  # strongly_recommend/recommend/neutral/not_recommend
    dimensions: list[DimensionScore] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    summary: str = ""
    detailed_analysis: str = ""
    generated_at: Optional[datetime] = None

class InterviewSession(BaseModel):
    id: str
    token: str
    resume_id: str
    jd_id: str
    status: InterviewStatus = InterviewStatus.PENDING
    written_test: Optional[WrittenTest] = None
    voice_interview: Optional[VoiceInterview] = None
    evaluation: Optional[Evaluation] = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None
