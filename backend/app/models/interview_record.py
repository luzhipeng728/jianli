from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.interview_phase import InterviewPhase, PHASE_CONFIGS, get_next_phase
from app.models.dialogue import DialogueEntry, DialogueRole, PhaseTransition

class InterviewRecordStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class EvaluationDimension(BaseModel):
    name: str
    score: int  # 1-10
    weight: float
    feedback: str

class EvaluationReport(BaseModel):
    overall_score: int  # 1-100
    recommendation: str  # "strongly_recommend" | "recommend" | "neutral" | "not_recommend"
    dimensions: List[EvaluationDimension] = []
    highlights: List[str] = []
    concerns: List[str] = []
    summary: str = ""
    generated_at: datetime = Field(default_factory=datetime.now)

class InterviewRecord(BaseModel):
    """Complete interview record for storage and replay"""
    session_id: str
    resume_id: str
    jd_id: str

    # State
    status: InterviewRecordStatus = InterviewRecordStatus.NOT_STARTED
    current_phase: InterviewPhase = InterviewPhase.OPENING
    current_round: int = 0  # Round within current phase

    # Dialogue history
    dialogues: List[DialogueEntry] = Field(default_factory=list)
    phase_transitions: List[PhaseTransition] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Evaluation
    evaluation: Optional[EvaluationReport] = None

    # HR features
    hr_watchers: List[str] = Field(default_factory=list)
    hr_interventions: List[Dict[str, Any]] = Field(default_factory=list)

    # Audio storage
    audio_dir: Optional[str] = None

    def add_dialogue(
        self,
        role: str,
        content: str,
        audio_path: Optional[str] = None,
        duration_seconds: Optional[float] = None
    ) -> DialogueEntry:
        """Add a dialogue entry"""
        entry = DialogueEntry(
            role=DialogueRole(role),
            content=content,
            phase=self.current_phase.value,
            round_number=self.current_round,
            audio_path=audio_path,
            duration_seconds=duration_seconds
        )
        self.dialogues.append(entry)
        return entry

    def advance_round(self) -> bool:
        """Advance to next round, returns True if phase should change"""
        self.current_round += 1
        max_rounds = PHASE_CONFIGS[self.current_phase].max_rounds
        return self.current_round >= max_rounds

    def advance_phase(self, reason: str = "max_rounds_reached") -> bool:
        """Advance to next phase, returns False if interview should end"""
        next_phase = get_next_phase(self.current_phase)
        if next_phase is None:
            return False

        self.phase_transitions.append(PhaseTransition(
            from_phase=self.current_phase.value,
            to_phase=next_phase.value,
            reason=reason
        ))
        self.current_phase = next_phase
        self.current_round = 0
        return True

    def can_advance_phase_early(self) -> bool:
        """Check if LLM can decide to advance phase early"""
        min_rounds = PHASE_CONFIGS[self.current_phase].min_rounds
        return self.current_round >= min_rounds

    def get_phase_dialogues(self, phase: InterviewPhase) -> List[DialogueEntry]:
        """Get all dialogues for a specific phase"""
        return [d for d in self.dialogues if d.phase == phase.value]

    def get_total_duration(self) -> float:
        """Get total interview duration in seconds"""
        return sum(d.duration_seconds or 0 for d in self.dialogues)
