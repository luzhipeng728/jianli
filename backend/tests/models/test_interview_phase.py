import pytest
from app.models.interview_phase import InterviewPhase, PhaseConfig, PHASE_CONFIGS

def test_interview_phases_exist():
    """All 7 phases should be defined"""
    assert len(InterviewPhase) == 7
    assert InterviewPhase.OPENING.value == "opening"
    assert InterviewPhase.SELF_INTRO.value == "self_intro"
    assert InterviewPhase.PROJECT_DEEP.value == "project_deep"
    assert InterviewPhase.TECH_ASSESS.value == "tech_assess"
    assert InterviewPhase.BEHAVIORAL.value == "behavioral"
    assert InterviewPhase.QA.value == "qa"
    assert InterviewPhase.CLOSING.value == "closing"

def test_phase_configs_have_round_limits():
    """Each phase should have min/max round limits"""
    assert PHASE_CONFIGS[InterviewPhase.OPENING].min_rounds == 1
    assert PHASE_CONFIGS[InterviewPhase.OPENING].max_rounds == 1
    assert PHASE_CONFIGS[InterviewPhase.PROJECT_DEEP].min_rounds == 3
    assert PHASE_CONFIGS[InterviewPhase.PROJECT_DEEP].max_rounds == 5

def test_phase_order():
    """Phases should have correct order"""
    assert PHASE_CONFIGS[InterviewPhase.OPENING].order == 1
    assert PHASE_CONFIGS[InterviewPhase.CLOSING].order == 7
