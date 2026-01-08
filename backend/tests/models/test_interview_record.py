import pytest
from app.models.interview_record import InterviewRecord, InterviewRecordStatus
from app.models.interview_phase import InterviewPhase

def test_interview_record_creation():
    record = InterviewRecord(
        session_id="test-123",
        resume_id="resume-456",
        jd_id="jd-789"
    )
    assert record.session_id == "test-123"
    assert record.current_phase == InterviewPhase.OPENING
    assert record.current_round == 0
    assert record.status == InterviewRecordStatus.NOT_STARTED
    assert len(record.dialogues) == 0

def test_add_dialogue():
    record = InterviewRecord(
        session_id="test-123",
        resume_id="resume-456",
        jd_id="jd-789"
    )
    record.add_dialogue(
        role="interviewer",
        content="你好",
        audio_path=None
    )
    assert len(record.dialogues) == 1
    assert record.dialogues[0].content == "你好"
    assert record.dialogues[0].phase == "opening"
