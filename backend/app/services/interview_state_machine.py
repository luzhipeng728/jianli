from datetime import datetime
from typing import Optional, Dict, Any

from app.models.interview_phase import InterviewPhase, PHASE_CONFIGS, get_next_phase
from app.models.interview_record import InterviewRecord, InterviewRecordStatus
from app.models.dialogue import DialogueRole

class InterviewStateMachine:
    """Manages interview flow with hybrid state machine + LLM control"""

    def __init__(
        self,
        session_id: str,
        resume_id: str,
        jd_id: str,
        audio_dir: Optional[str] = None
    ):
        self.record = InterviewRecord(
            session_id=session_id,
            resume_id=resume_id,
            jd_id=jd_id,
            audio_dir=audio_dir or f"/data/interviews/{session_id}"
        )

    def start(self) -> None:
        """Start the interview"""
        self.record.status = InterviewRecordStatus.IN_PROGRESS
        self.record.started_at = datetime.now()

    def pause(self) -> None:
        """Pause the interview (for HR intervention)"""
        self.record.status = InterviewRecordStatus.PAUSED

    def resume(self) -> None:
        """Resume paused interview"""
        self.record.status = InterviewRecordStatus.IN_PROGRESS

    def complete(self) -> None:
        """Mark interview as completed"""
        self.record.status = InterviewRecordStatus.COMPLETED
        self.record.completed_at = datetime.now()

    def cancel(self, reason: str = "") -> None:
        """Cancel the interview"""
        self.record.status = InterviewRecordStatus.CANCELLED
        self.record.completed_at = datetime.now()

    def get_current_phase_config(self) -> Dict[str, Any]:
        """Get current phase configuration"""
        config = PHASE_CONFIGS[self.record.current_phase]
        return {
            "phase": config.phase.value,
            "description": config.description,
            "prompt_hint": config.prompt_hint,
            "current_round": self.record.current_round,
            "min_rounds": config.min_rounds,
            "max_rounds": config.max_rounds,
            "can_advance_early": self.can_advance_early()
        }

    def can_advance_early(self) -> bool:
        """Check if LLM can decide to advance phase early"""
        return self.record.can_advance_phase_early()

    def process_turn(
        self,
        interviewer_text: str,
        candidate_text: str,
        interviewer_audio: Optional[str] = None,
        candidate_audio: Optional[str] = None,
        interviewer_duration: Optional[float] = None,
        candidate_duration: Optional[float] = None,
        should_advance: bool = False
    ) -> Dict[str, Any]:
        """Process a dialogue turn"""
        # Add interviewer dialogue
        self.record.add_dialogue(
            role="interviewer",
            content=interviewer_text,
            audio_path=interviewer_audio,
            duration_seconds=interviewer_duration
        )

        # Add candidate dialogue
        self.record.add_dialogue(
            role="candidate",
            content=candidate_text,
            audio_path=candidate_audio,
            duration_seconds=candidate_duration
        )

        # Advance round
        max_reached = self.record.advance_round()

        # Determine if phase should change
        phase_changed = False
        interview_ended = False
        reason = ""

        if max_reached:
            reason = "max_rounds_reached"
            phase_changed = True
        elif should_advance and self.can_advance_early():
            reason = "llm_decision"
            phase_changed = True

        if phase_changed:
            continued = self.record.advance_phase(reason)
            if not continued:
                interview_ended = True
                self.complete()

        return {
            "phase_changed": phase_changed,
            "new_phase": self.record.current_phase.value,
            "interview_ended": interview_ended,
            "reason": reason
        }

    def force_advance_phase(self, reason: str = "hr_intervention") -> bool:
        """Force advance to next phase (for HR intervention)"""
        continued = self.record.advance_phase(reason)
        if not continued:
            self.complete()
        return continued

    def force_end(self, reason: str = "hr_intervention") -> None:
        """Force end the interview"""
        self.record.add_dialogue(
            role="system",
            content=f"面试结束: {reason}"
        )
        self.complete()

    def get_record(self) -> InterviewRecord:
        """Get the interview record"""
        return self.record

    def load_record(self, record: InterviewRecord) -> None:
        """Load existing record (for resume/replay)"""
        self.record = record
