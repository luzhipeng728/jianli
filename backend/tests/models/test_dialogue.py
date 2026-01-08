import pytest
from datetime import datetime
from app.models.dialogue import DialogueEntry, DialogueRole

def test_dialogue_entry_creation():
    entry = DialogueEntry(
        role=DialogueRole.INTERVIEWER,
        content="请介绍一下你自己",
        phase="self_intro",
        round_number=1
    )
    assert entry.role == DialogueRole.INTERVIEWER
    assert entry.content == "请介绍一下你自己"
    assert entry.audio_path is None
    assert entry.timestamp is not None

def test_dialogue_entry_with_audio():
    entry = DialogueEntry(
        role=DialogueRole.CANDIDATE,
        content="我是张三...",
        phase="self_intro",
        round_number=1,
        audio_path="/data/interviews/123/round_1_candidate.wav",
        duration_seconds=45.5
    )
    assert entry.audio_path == "/data/interviews/123/round_1_candidate.wav"
    assert entry.duration_seconds == 45.5
