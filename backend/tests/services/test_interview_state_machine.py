import pytest
from app.services.interview_state_machine import InterviewStateMachine
from app.models.interview_phase import InterviewPhase
from app.models.interview_record import InterviewRecordStatus

def test_state_machine_initialization():
    sm = InterviewStateMachine(
        session_id="test-123",
        resume_id="resume-456",
        jd_id="jd-789"
    )
    assert sm.record.current_phase == InterviewPhase.OPENING
    assert sm.record.status == InterviewRecordStatus.NOT_STARTED

def test_start_interview():
    sm = InterviewStateMachine(
        session_id="test-123",
        resume_id="resume-456",
        jd_id="jd-789"
    )
    sm.start()
    assert sm.record.status == InterviewRecordStatus.IN_PROGRESS
    assert sm.record.started_at is not None

def test_process_turn_advances_round():
    sm = InterviewStateMachine(
        session_id="test-123",
        resume_id="resume-456",
        jd_id="jd-789"
    )
    sm.start()

    # Opening phase has max 1 round
    result = sm.process_turn(
        interviewer_text="你好，我是面试官",
        candidate_text="你好",
        should_advance=False
    )

    assert result["phase_changed"] == True
    assert sm.record.current_phase == InterviewPhase.SELF_INTRO

def test_llm_can_advance_early():
    sm = InterviewStateMachine(
        session_id="test-123",
        resume_id="resume-456",
        jd_id="jd-789"
    )
    sm.start()
    sm.record.current_phase = InterviewPhase.PROJECT_DEEP
    sm.record.current_round = 3  # min is 3

    assert sm.can_advance_early() == True

    sm.record.current_round = 2  # below min
    assert sm.can_advance_early() == False
