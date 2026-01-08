import pytest
import os
import tempfile
import shutil
from app.services.interview_storage import InterviewStorage
from app.models.interview_record import InterviewRecord

@pytest.fixture
def storage():
    # Use temp directory for tests
    temp_dir = tempfile.mkdtemp()
    s = InterviewStorage(base_dir=temp_dir)
    yield s
    shutil.rmtree(temp_dir)

def test_save_and_load_record(storage):
    record = InterviewRecord(
        session_id="test-123",
        resume_id="resume-456",
        jd_id="jd-789"
    )
    record.add_dialogue(role="interviewer", content="你好")

    storage.save_record(record)

    loaded = storage.load_record("test-123")
    assert loaded is not None
    assert loaded.session_id == "test-123"
    assert len(loaded.dialogues) == 1

def test_save_audio(storage):
    audio_data = b"fake audio data"
    path = storage.save_audio(
        session_id="test-123",
        round_number=1,
        role="candidate",
        audio_data=audio_data
    )
    assert os.path.exists(path)
    assert "test-123" in path

def test_list_records(storage):
    for i in range(3):
        record = InterviewRecord(
            session_id=f"test-{i}",
            resume_id="resume-456",
            jd_id="jd-789"
        )
        storage.save_record(record)

    records = storage.list_records()
    assert len(records) == 3
