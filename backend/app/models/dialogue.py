from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DialogueRole(str, Enum):
    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"
    SYSTEM = "system"  # For phase transitions, etc.

class DialogueEntry(BaseModel):
    """A single dialogue entry in the interview"""
    id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S%f"))
    role: DialogueRole
    content: str
    phase: str
    round_number: int
    audio_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    # For HR annotations
    is_highlighted: bool = False
    hr_notes: Optional[str] = None

class PhaseTransition(BaseModel):
    """Record of phase transitions"""
    from_phase: str
    to_phase: str
    reason: str  # "max_rounds_reached" | "llm_decision" | "hr_intervention"
    timestamp: datetime = Field(default_factory=datetime.now)
