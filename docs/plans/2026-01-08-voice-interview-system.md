# AI Voice Interview System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete AI voice interview system with structured phases, dialogue storage, HR replay, real-time monitoring, and HR intervention capabilities.

**Architecture:**
- 7-phase state machine controls interview flow with hybrid mode (state machine + LLM flexibility)
- InterviewerAgent handles all questioning, EvaluatorAgent generates final report
- Local file storage for audio (`/data/interviews/{session_id}/`)
- WebSocket for real-time interview + HR monitoring, REST API for replay

**Tech Stack:** FastAPI, WebSocket, Qwen-Omni (audio understanding + TTS), Redis (state), JSON files (records), Vue 3 (frontend)

---

## Phase 1: Core Data Models & State Machine

### Task 1.1: Interview Phase Enum and Config

**Files:**
- Create: `backend/app/models/interview_phase.py`
- Test: `backend/tests/models/test_interview_phase.py`

**Step 1: Write the failing test**

```python
# backend/tests/models/test_interview_phase.py
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
```

**Step 2: Run test to verify it fails**

```bash
cd /root/jianli_final/backend && python -m pytest tests/models/test_interview_phase.py -v
```
Expected: FAIL with "No module named 'app.models.interview_phase'"

**Step 3: Write minimal implementation**

```python
# backend/app/models/interview_phase.py
from enum import Enum
from pydantic import BaseModel
from typing import Dict

class InterviewPhase(str, Enum):
    OPENING = "opening"
    SELF_INTRO = "self_intro"
    PROJECT_DEEP = "project_deep"
    TECH_ASSESS = "tech_assess"
    BEHAVIORAL = "behavioral"
    QA = "qa"
    CLOSING = "closing"

class PhaseConfig(BaseModel):
    """Configuration for each interview phase"""
    phase: InterviewPhase
    order: int
    min_rounds: int
    max_rounds: int
    description: str
    prompt_hint: str  # Hint for interviewer agent

PHASE_CONFIGS: Dict[InterviewPhase, PhaseConfig] = {
    InterviewPhase.OPENING: PhaseConfig(
        phase=InterviewPhase.OPENING,
        order=1,
        min_rounds=1,
        max_rounds=1,
        description="开场寒暄",
        prompt_hint="友好问候，让候选人放松"
    ),
    InterviewPhase.SELF_INTRO: PhaseConfig(
        phase=InterviewPhase.SELF_INTRO,
        order=2,
        min_rounds=1,
        max_rounds=2,
        description="自我介绍",
        prompt_hint="请候选人介绍自己，可以适当追问"
    ),
    InterviewPhase.PROJECT_DEEP: PhaseConfig(
        phase=InterviewPhase.PROJECT_DEEP,
        order=3,
        min_rounds=3,
        max_rounds=5,
        description="项目深挖",
        prompt_hint="深入了解候选人的项目经验，追问技术细节和个人贡献"
    ),
    InterviewPhase.TECH_ASSESS: PhaseConfig(
        phase=InterviewPhase.TECH_ASSESS,
        order=4,
        min_rounds=3,
        max_rounds=5,
        description="技术评估",
        prompt_hint="考察岗位相关的技术能力，可以出具体问题"
    ),
    InterviewPhase.BEHAVIORAL: PhaseConfig(
        phase=InterviewPhase.BEHAVIORAL,
        order=5,
        min_rounds=2,
        max_rounds=3,
        description="行为面试",
        prompt_hint="了解候选人的软技能、团队协作、问题解决能力"
    ),
    InterviewPhase.QA: PhaseConfig(
        phase=InterviewPhase.QA,
        order=6,
        min_rounds=1,
        max_rounds=2,
        description="候选人提问",
        prompt_hint="让候选人提问，耐心解答"
    ),
    InterviewPhase.CLOSING: PhaseConfig(
        phase=InterviewPhase.CLOSING,
        order=7,
        min_rounds=1,
        max_rounds=1,
        description="结束语",
        prompt_hint="感谢候选人，说明后续流程"
    ),
}

def get_next_phase(current: InterviewPhase) -> InterviewPhase | None:
    """Get the next phase in order, None if at closing"""
    current_order = PHASE_CONFIGS[current].order
    for phase, config in PHASE_CONFIGS.items():
        if config.order == current_order + 1:
            return phase
    return None
```

**Step 4: Run test to verify it passes**

```bash
cd /root/jianli_final/backend && python -m pytest tests/models/test_interview_phase.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/interview_phase.py backend/tests/models/test_interview_phase.py
git commit -m "feat: add interview phase enum and config"
```

---

### Task 1.2: Dialogue Entry Model

**Files:**
- Create: `backend/app/models/dialogue.py`
- Test: `backend/tests/models/test_dialogue.py`

**Step 1: Write the failing test**

```python
# backend/tests/models/test_dialogue.py
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
```

**Step 2: Run test to verify it fails**

```bash
cd /root/jianli_final/backend && python -m pytest tests/models/test_dialogue.py -v
```
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# backend/app/models/dialogue.py
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
```

**Step 4: Run test to verify it passes**

```bash
cd /root/jianli_final/backend && python -m pytest tests/models/test_dialogue.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/dialogue.py backend/tests/models/test_dialogue.py
git commit -m "feat: add dialogue entry model"
```

---

### Task 1.3: Interview Record Model

**Files:**
- Create: `backend/app/models/interview_record.py`
- Test: `backend/tests/models/test_interview_record.py`

**Step 1: Write the failing test**

```python
# backend/tests/models/test_interview_record.py
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
```

**Step 2: Run test to verify it fails**

```bash
cd /root/jianli_final/backend && python -m pytest tests/models/test_interview_record.py -v
```
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# backend/app/models/interview_record.py
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
    hr_watchers: List[str] = Field(default_factory=list)  # HR user IDs watching live
    hr_interventions: List[Dict[str, Any]] = Field(default_factory=list)

    # Audio storage
    audio_dir: Optional[str] = None  # /data/interviews/{session_id}/

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
```

**Step 4: Run test to verify it passes**

```bash
cd /root/jianli_final/backend && python -m pytest tests/models/test_interview_record.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/interview_record.py backend/tests/models/test_interview_record.py
git commit -m "feat: add interview record model with phase management"
```

---

### Task 1.4: Interview State Machine

**Files:**
- Create: `backend/app/services/interview_state_machine.py`
- Test: `backend/tests/services/test_interview_state_machine.py`

**Step 1: Write the failing test**

```python
# backend/tests/services/test_interview_state_machine.py
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
```

**Step 2: Run test to verify it fails**

```bash
cd /root/jianli_final/backend && python -m pytest tests/services/test_interview_state_machine.py -v
```
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# backend/app/services/interview_state_machine.py
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
        should_advance: bool = False  # LLM decision to advance early
    ) -> Dict[str, Any]:
        """Process a dialogue turn

        Args:
            interviewer_text: What interviewer said
            candidate_text: What candidate said
            interviewer_audio: Path to interviewer audio file
            candidate_audio: Path to candidate audio file
            should_advance: LLM's decision to advance phase early

        Returns:
            Dict with phase_changed, new_phase, interview_ended flags
        """
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
        """Force advance to next phase (for HR intervention)

        Returns:
            False if interview ended (was at closing)
        """
        continued = self.record.advance_phase(reason)
        if not continued:
            self.complete()
        return continued

    def force_end(self, reason: str = "hr_intervention") -> None:
        """Force end the interview"""
        # Add system message
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
```

**Step 4: Run test to verify it passes**

```bash
cd /root/jianli_final/backend && python -m pytest tests/services/test_interview_state_machine.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/interview_state_machine.py backend/tests/services/test_interview_state_machine.py
git commit -m "feat: add interview state machine with hybrid control"
```

---

## Phase 2: Storage Service

### Task 2.1: Interview Storage Service

**Files:**
- Create: `backend/app/services/interview_storage.py`
- Test: `backend/tests/services/test_interview_storage.py`

**Step 1: Write the failing test**

```python
# backend/tests/services/test_interview_storage.py
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
```

**Step 2: Run test to verify it fails**

```bash
cd /root/jianli_final/backend && python -m pytest tests/services/test_interview_storage.py -v
```
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# backend/app/services/interview_storage.py
import os
import json
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from app.models.interview_record import InterviewRecord

class InterviewStorage:
    """Local file storage for interview records and audio"""

    def __init__(self, base_dir: str = "/data/interviews"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_dir(self, session_id: str) -> Path:
        """Get directory for a session"""
        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def _get_record_path(self, session_id: str) -> Path:
        """Get path to record JSON file"""
        return self._get_session_dir(session_id) / "record.json"

    def save_record(self, record: InterviewRecord) -> str:
        """Save interview record to JSON file

        Returns:
            Path to saved file
        """
        path = self._get_record_path(record.session_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record.model_dump(mode="json"), f, ensure_ascii=False, indent=2, default=str)
        return str(path)

    def load_record(self, session_id: str) -> Optional[InterviewRecord]:
        """Load interview record from JSON file"""
        path = self._get_record_path(session_id)
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return InterviewRecord(**data)

    def save_audio(
        self,
        session_id: str,
        round_number: int,
        role: str,
        audio_data: bytes,
        format: str = "wav"
    ) -> str:
        """Save audio file

        Returns:
            Path to saved audio file
        """
        session_dir = self._get_session_dir(session_id)
        audio_dir = session_dir / "audio"
        audio_dir.mkdir(exist_ok=True)

        filename = f"round_{round_number}_{role}.{format}"
        path = audio_dir / filename

        with open(path, "wb") as f:
            f.write(audio_data)

        return str(path)

    def load_audio(self, audio_path: str) -> Optional[bytes]:
        """Load audio file"""
        path = Path(audio_path)
        if not path.exists():
            return None

        with open(path, "rb") as f:
            return f.read()

    def list_records(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[InterviewRecord]:
        """List all interview records"""
        records = []

        for session_dir in sorted(self.base_dir.iterdir(), reverse=True):
            if not session_dir.is_dir():
                continue

            record_path = session_dir / "record.json"
            if not record_path.exists():
                continue

            try:
                with open(record_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                record = InterviewRecord(**data)

                if status and record.status.value != status:
                    continue

                records.append(record)
            except Exception as e:
                print(f"Error loading record from {record_path}: {e}")
                continue

        return records[offset:offset + limit]

    def delete_record(self, session_id: str) -> bool:
        """Delete interview record and all associated files"""
        import shutil
        session_dir = self._get_session_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)
            return True
        return False

    def get_audio_url(self, audio_path: str) -> str:
        """Convert local path to API URL for frontend"""
        # Assumes audio is served via /api/interviews/{session_id}/audio/{filename}
        path = Path(audio_path)
        session_id = path.parent.parent.name
        filename = path.name
        return f"/api/interviews/{session_id}/audio/{filename}"


# Global instance
_storage: Optional[InterviewStorage] = None

def get_interview_storage() -> InterviewStorage:
    global _storage
    if _storage is None:
        _storage = InterviewStorage()
    return _storage
```

**Step 4: Run test to verify it passes**

```bash
cd /root/jianli_final/backend && python -m pytest tests/services/test_interview_storage.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/interview_storage.py backend/tests/services/test_interview_storage.py
git commit -m "feat: add interview storage service for records and audio"
```

---

## Phase 3: Agents

### Task 3.1: Unified Interviewer Agent

**Files:**
- Create: `backend/app/agents/unified_interviewer_agent.py`
- Test: `backend/tests/agents/test_unified_interviewer_agent.py`

**Step 1: Write the failing test**

```python
# backend/tests/agents/test_unified_interviewer_agent.py
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.unified_interviewer_agent import UnifiedInterviewerAgent
from app.models.interview_phase import InterviewPhase

@pytest.fixture
def agent():
    return UnifiedInterviewerAgent(
        session_id="test-123",
        resume_summary="张三，5年Python开发经验",
        job_info="高级后端工程师，要求Python、FastAPI"
    )

@pytest.mark.asyncio
async def test_generate_opening(agent):
    with patch.object(agent.llm, 'chat_async', new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "你好，我是今天的面试官。"

        response = await agent.generate_response(
            phase=InterviewPhase.OPENING,
            round_number=0,
            conversation_history=[]
        )

        assert "面试官" in mock_chat.call_args[1]["messages"][0]["content"]
        assert response == "你好，我是今天的面试官。"

@pytest.mark.asyncio
async def test_phase_specific_prompts(agent):
    with patch.object(agent.llm, 'chat_async', new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "请介绍一个你做过的项目"

        await agent.generate_response(
            phase=InterviewPhase.PROJECT_DEEP,
            round_number=1,
            conversation_history=[
                {"role": "assistant", "content": "请做自我介绍"},
                {"role": "user", "content": "我是张三..."}
            ]
        )

        # Check that phase hint is in system prompt
        system_prompt = mock_chat.call_args[1]["messages"][0]["content"]
        assert "项目" in system_prompt or "深入" in system_prompt
```

**Step 2: Run test to verify it fails**

```bash
cd /root/jianli_final/backend && python -m pytest tests/agents/test_unified_interviewer_agent.py -v
```
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# backend/app/agents/unified_interviewer_agent.py
"""Unified Interviewer Agent - handles all interview phases"""

from typing import List, Dict, Optional, AsyncGenerator
from app.services.llm_client import LLMClient
from app.models.interview_phase import InterviewPhase, PHASE_CONFIGS

class UnifiedInterviewerAgent:
    """Unified interviewer agent that handles all phases

    Adapts questioning style based on current phase.
    """

    def __init__(
        self,
        session_id: str,
        resume_summary: str,
        job_info: str
    ):
        self.session_id = session_id
        self.resume_summary = resume_summary
        self.job_info = job_info
        self.llm = LLMClient()

    def _build_system_prompt(
        self,
        phase: InterviewPhase,
        round_number: int,
        can_advance_early: bool = False
    ) -> str:
        """Build phase-specific system prompt"""

        phase_config = PHASE_CONFIGS[phase]

        base_prompt = f"""你是一位专业的技术面试官，正在进行语音面试。

## 语言要求
- 必须全程使用中文
- 使用自然的口语表达
- 回复简洁，适合语音播放（不超过3句话）

## 候选人背景
{self.resume_summary}

## 岗位信息
{self.job_info}

## 当前阶段
- 阶段：{phase_config.description}
- 当前轮次：{round_number + 1} / {phase_config.max_rounds}
- 阶段指导：{phase_config.prompt_hint}
"""

        # Phase-specific instructions
        phase_instructions = {
            InterviewPhase.OPENING: """
## 本阶段任务
- 友好问候候选人
- 简单介绍自己和面试流程
- 让候选人放松""",

            InterviewPhase.SELF_INTRO: """
## 本阶段任务
- 请候选人做自我介绍
- 可以针对介绍内容简单追问
- 了解候选人的职业经历概况""",

            InterviewPhase.PROJECT_DEEP: """
## 本阶段任务
- 深入了解候选人做过的项目
- 追问技术细节和个人贡献
- 了解候选人解决问题的能力
- 问题要具体，不要泛泛而谈""",

            InterviewPhase.TECH_ASSESS: """
## 本阶段任务
- 考察岗位相关的技术能力
- 可以出具体的技术问题
- 评估候选人的技术深度和广度
- 根据岗位要求重点考察相关技能""",

            InterviewPhase.BEHAVIORAL: """
## 本阶段任务
- 了解候选人的软技能
- 考察团队协作能力
- 了解问题解决和冲突处理方式
- 使用STAR方法提问（情境-任务-行动-结果）""",

            InterviewPhase.QA: """
## 本阶段任务
- 让候选人提问
- 耐心回答候选人的问题
- 介绍公司和团队情况
- 如果候选人没有问题，可以主动介绍一些信息""",

            InterviewPhase.CLOSING: """
## 本阶段任务
- 感谢候选人参与面试
- 说明后续流程和时间安排
- 礼貌结束面试"""
        }

        base_prompt += phase_instructions.get(phase, "")

        if can_advance_early:
            base_prompt += """

## 阶段切换
如果你认为当前阶段已经充分了解候选人，可以在回复末尾加上 [ADVANCE_PHASE] 标记。
但请确保至少完成了最少轮次的提问。"""

        return base_prompt

    async def generate_response(
        self,
        phase: InterviewPhase,
        round_number: int,
        conversation_history: List[Dict[str, str]],
        can_advance_early: bool = False
    ) -> str:
        """Generate interviewer response

        Args:
            phase: Current interview phase
            round_number: Current round within phase
            conversation_history: Previous dialogue
            can_advance_early: Whether LLM can decide to advance phase

        Returns:
            Interviewer's response text
        """
        system_prompt = self._build_system_prompt(phase, round_number, can_advance_early)

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for msg in conversation_history[-20:]:  # Last 20 messages
            role = "assistant" if msg["role"] in ["interviewer", "assistant"] else "user"
            messages.append({"role": role, "content": msg["content"]})

        # If no history, this is the start
        if not conversation_history:
            messages.append({
                "role": "user",
                "content": "请开始面试。"
            })

        response = await self.llm.chat_async(
            messages=messages,
            temperature=0.7
        )

        return response

    async def generate_response_stream(
        self,
        phase: InterviewPhase,
        round_number: int,
        conversation_history: List[Dict[str, str]],
        can_advance_early: bool = False
    ) -> AsyncGenerator[str, None]:
        """Stream generate interviewer response"""
        system_prompt = self._build_system_prompt(phase, round_number, can_advance_early)

        messages = [{"role": "system", "content": system_prompt}]

        for msg in conversation_history[-20:]:
            role = "assistant" if msg["role"] in ["interviewer", "assistant"] else "user"
            messages.append({"role": role, "content": msg["content"]})

        if not conversation_history:
            messages.append({"role": "user", "content": "请开始面试。"})

        async for chunk in self.llm.chat_stream_messages(messages, temperature=0.7):
            yield chunk

    def check_advance_signal(self, response: str) -> tuple[str, bool]:
        """Check if response contains advance phase signal

        Returns:
            (cleaned_response, should_advance)
        """
        if "[ADVANCE_PHASE]" in response:
            return response.replace("[ADVANCE_PHASE]", "").strip(), True
        return response, False
```

**Step 4: Run test to verify it passes**

```bash
cd /root/jianli_final/backend && python -m pytest tests/agents/test_unified_interviewer_agent.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/agents/unified_interviewer_agent.py backend/tests/agents/test_unified_interviewer_agent.py
git commit -m "feat: add unified interviewer agent with phase-specific prompts"
```

---

### Task 3.2: Evaluator Agent

**Files:**
- Create: `backend/app/agents/evaluator_agent.py`
- Test: `backend/tests/agents/test_evaluator_agent.py`

**Step 1: Write the failing test**

```python
# backend/tests/agents/test_evaluator_agent.py
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.evaluator_agent import EvaluatorAgent
from app.models.interview_record import InterviewRecord, EvaluationReport

@pytest.fixture
def agent():
    return EvaluatorAgent()

@pytest.fixture
def sample_record():
    record = InterviewRecord(
        session_id="test-123",
        resume_id="resume-456",
        jd_id="jd-789"
    )
    record.add_dialogue(role="interviewer", content="请介绍一下你自己")
    record.add_dialogue(role="candidate", content="我是张三，有5年Python开发经验...")
    record.add_dialogue(role="interviewer", content="说说你最有挑战的项目")
    record.add_dialogue(role="candidate", content="我们做了一个高并发系统...")
    return record

@pytest.mark.asyncio
async def test_generate_evaluation(agent, sample_record):
    mock_response = '''{
        "overall_score": 75,
        "recommendation": "recommend",
        "dimensions": [
            {"name": "技术能力", "score": 8, "weight": 0.4, "feedback": "扎实的Python基础"}
        ],
        "highlights": ["有高并发经验"],
        "concerns": ["需要了解更多系统设计"],
        "summary": "候选人整体表现良好"
    }'''

    with patch.object(agent.llm, 'chat_async', new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = mock_response

        report = await agent.evaluate(
            record=sample_record,
            job_info="高级后端工程师"
        )

        assert isinstance(report, EvaluationReport)
        assert report.overall_score == 75
        assert report.recommendation == "recommend"
```

**Step 2: Run test to verify it fails**

```bash
cd /root/jianli_final/backend && python -m pytest tests/agents/test_evaluator_agent.py -v
```
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# backend/app/agents/evaluator_agent.py
"""Evaluator Agent - generates post-interview evaluation report"""

import json
from typing import Optional
from app.services.llm_client import LLMClient
from app.models.interview_record import InterviewRecord, EvaluationReport, EvaluationDimension

class EvaluatorAgent:
    """Generates comprehensive evaluation after interview ends"""

    def __init__(self):
        self.llm = LLMClient()

    def _build_evaluation_prompt(
        self,
        record: InterviewRecord,
        job_info: str
    ) -> str:
        """Build prompt for evaluation"""

        # Format dialogue for analysis
        dialogue_text = ""
        for d in record.dialogues:
            role_label = "面试官" if d.role.value == "interviewer" else "候选人"
            dialogue_text += f"\n[{d.phase}] {role_label}: {d.content}"

        return f"""你是一位资深的面试评估专家。请根据以下面试记录，生成全面的评估报告。

## 岗位信息
{job_info}

## 面试记录
{dialogue_text}

## 面试时长
总轮次: {len([d for d in record.dialogues if d.role.value == 'candidate'])}
阶段: {', '.join(set(d.phase for d in record.dialogues))}

## 评估要求
请从以下维度评估候选人（每项1-10分）：
1. 技术能力 (权重0.3) - 专业技能、技术深度
2. 项目经验 (权重0.25) - 项目复杂度、个人贡献
3. 沟通表达 (权重0.15) - 表达清晰度、逻辑性
4. 学习能力 (权重0.15) - 学习态度、成长潜力
5. 文化匹配 (权重0.15) - 价值观、团队协作

## 输出格式 (JSON)
{{
    "overall_score": 总分(1-100),
    "recommendation": "strongly_recommend|recommend|neutral|not_recommend",
    "dimensions": [
        {{"name": "技术能力", "score": 分数, "weight": 0.3, "feedback": "评语"}},
        ...
    ],
    "highlights": ["亮点1", "亮点2"],
    "concerns": ["顾虑1", "顾虑2"],
    "summary": "总结评语（100字以内）"
}}

请只返回JSON，不要其他内容。"""

    async def evaluate(
        self,
        record: InterviewRecord,
        job_info: str
    ) -> EvaluationReport:
        """Generate evaluation report

        Args:
            record: Complete interview record
            job_info: Job description info

        Returns:
            EvaluationReport
        """
        prompt = self._build_evaluation_prompt(record, job_info)

        messages = [
            {"role": "system", "content": "你是专业的面试评估专家，请严格按照JSON格式输出评估报告。"},
            {"role": "user", "content": prompt}
        ]

        response = await self.llm.chat_async(
            messages=messages,
            temperature=0.3  # Lower temperature for consistent evaluation
        )

        # Parse JSON response
        try:
            # Clean up response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response.strip())

            # Convert dimensions
            dimensions = []
            for dim in data.get("dimensions", []):
                dimensions.append(EvaluationDimension(
                    name=dim["name"],
                    score=dim["score"],
                    weight=dim["weight"],
                    feedback=dim.get("feedback", "")
                ))

            report = EvaluationReport(
                overall_score=data.get("overall_score", 0),
                recommendation=data.get("recommendation", "neutral"),
                dimensions=dimensions,
                highlights=data.get("highlights", []),
                concerns=data.get("concerns", []),
                summary=data.get("summary", "")
            )

            return report

        except json.JSONDecodeError as e:
            # Return default report on parse error
            print(f"Evaluation parse error: {e}, response: {response[:200]}")
            return EvaluationReport(
                overall_score=0,
                recommendation="neutral",
                summary="评估生成失败，请人工评估"
            )

    async def evaluate_and_save(
        self,
        record: InterviewRecord,
        job_info: str
    ) -> InterviewRecord:
        """Evaluate and attach report to record

        Returns:
            Updated record with evaluation
        """
        report = await self.evaluate(record, job_info)
        record.evaluation = report
        return record
```

**Step 4: Run test to verify it passes**

```bash
cd /root/jianli_final/backend && python -m pytest tests/agents/test_evaluator_agent.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/agents/evaluator_agent.py backend/tests/agents/test_evaluator_agent.py
git commit -m "feat: add evaluator agent for post-interview assessment"
```

---

## Phase 4: WebSocket Interview Handler

### Task 4.1: Structured Voice Interview WebSocket

**Files:**
- Create: `backend/app/api/routes/ws_structured_interview.py`

**Step 1: Create the WebSocket handler**

This is a larger file, so we'll create it directly (integration tested manually).

```python
# backend/app/api/routes/ws_structured_interview.py
"""Structured Voice Interview WebSocket

Features:
- 7-phase state machine
- Qwen-Omni for audio understanding + response
- Real-time dialogue storage
- HR monitoring support
"""

import json
import asyncio
import base64
import io
import wave
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.asr_service import ParaformerASRSession
from app.services.omni_http_client import QwenOmniClient, get_omni_client
from app.services.interview_storage import get_interview_storage
from app.services.interview_state_machine import InterviewStateMachine
from app.agents.unified_interviewer_agent import UnifiedInterviewerAgent
from app.agents.evaluator_agent import EvaluatorAgent
from app.models.interview_phase import InterviewPhase, PHASE_CONFIGS

router = APIRouter()

# Active sessions for HR monitoring
active_sessions: Dict[str, "StructuredInterviewSession"] = {}


class StructuredInterviewSession:
    """Structured interview session with state machine"""

    def __init__(
        self,
        websocket: WebSocket,
        session_id: str,
        resume_id: str,
        jd_id: str,
        resume_summary: str,
        job_info: str
    ):
        self.websocket = websocket
        self.session_id = session_id

        # State machine
        self.state_machine = InterviewStateMachine(
            session_id=session_id,
            resume_id=resume_id,
            jd_id=jd_id
        )

        # Agents
        self.interviewer = UnifiedInterviewerAgent(
            session_id=session_id,
            resume_summary=resume_summary,
            job_info=job_info
        )
        self.evaluator = EvaluatorAgent()
        self.job_info = job_info

        # Services
        self.storage = get_interview_storage()
        self.omni_client = get_omni_client()
        self.asr_session: Optional[ParaformerASRSession] = None

        # Audio buffer
        self.audio_buffer: List[bytes] = []
        self.current_transcript = ""

        # State
        self.is_active = False
        self.is_speaking = False

        # HR watchers
        self.hr_watchers: List[WebSocket] = []

    async def start(self) -> bool:
        """Start the interview session"""
        try:
            # Initialize ASR
            self.asr_session = ParaformerASRSession(
                on_transcript=self._on_transcript,
                on_error=self._on_asr_error
            )
            if not await self.asr_session.connect():
                return False

            self.is_active = True
            self.state_machine.start()

            # Save initial record
            self.storage.save_record(self.state_machine.record)

            # Send opening message
            await self._send_phase_start()
            await self._generate_and_send_response()

            return True
        except Exception as e:
            print(f"[StructuredInterview] Start error: {e}")
            return False

    async def _send_phase_start(self):
        """Notify frontend of phase start"""
        config = self.state_machine.get_current_phase_config()
        await self._send_message({
            "type": "phase_change",
            "phase": config["phase"],
            "description": config["description"],
            "round": config["current_round"],
            "max_rounds": config["max_rounds"]
        })
        await self._broadcast_to_hr({
            "type": "phase_change",
            "session_id": self.session_id,
            **config
        })

    async def _generate_and_send_response(self):
        """Generate interviewer response using Omni (text + audio)"""
        self.is_speaking = True
        await self._send_status("speaking")

        try:
            record = self.state_machine.record
            phase = record.current_phase
            round_num = record.current_round

            # Build conversation history for agent
            history = [
                {"role": d.role.value, "content": d.content}
                for d in record.dialogues
            ]

            # Generate text response
            can_advance = self.state_machine.can_advance_early()
            response_text = await self.interviewer.generate_response(
                phase=phase,
                round_number=round_num,
                conversation_history=history,
                can_advance_early=can_advance
            )

            # Check for advance signal
            response_text, should_advance = self.interviewer.check_advance_signal(response_text)

            # Send text to frontend
            await self._send_message({
                "type": "response_text",
                "text": response_text
            })

            # Generate audio using Qwen-Omni (text-to-speech mode)
            # For now, we'll use the Omni client with a simple text prompt
            # In production, you might use a dedicated TTS service
            await self._synthesize_and_send_audio(response_text)

            # Add to record
            audio_path = self.storage.save_audio(
                session_id=self.session_id,
                round_number=round_num,
                role="interviewer",
                audio_data=b""  # Would save actual audio
            )

            record.add_dialogue(
                role="interviewer",
                content=response_text,
                audio_path=None  # TTS audio not saved for now
            )

            # Save record
            self.storage.save_record(record)

            # Broadcast to HR
            await self._broadcast_to_hr({
                "type": "dialogue",
                "session_id": self.session_id,
                "role": "interviewer",
                "content": response_text,
                "phase": phase.value,
                "round": round_num
            })

            # Store advance decision for later
            self._pending_advance = should_advance

        except Exception as e:
            print(f"[StructuredInterview] Generate response error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_speaking = False
            await self._send_status("listening")

    async def _synthesize_and_send_audio(self, text: str):
        """Synthesize audio and send to frontend

        Uses Qwen-Omni's text modality to generate audio response
        """
        # For Qwen-Omni, we need to send audio input
        # Since we only have text, we'll use TTS service or skip audio
        # For now, we'll import and use the TTS service
        from app.services.tts_service import CosyVoiceTTSSession

        audio_queue = asyncio.Queue()
        is_complete = asyncio.Event()

        def on_audio(data: bytes):
            audio_queue.put_nowait(data)

        def on_complete():
            is_complete.set()

        tts = CosyVoiceTTSSession(
            voice="longxiaochun",
            sample_rate=24000,
            on_audio=on_audio,
            on_complete=on_complete
        )

        if not await tts.connect():
            print("[StructuredInterview] TTS connect failed")
            return

        await tts.synthesize(text)
        await tts.finish()

        # Send audio chunks
        while not is_complete.is_set() or not audio_queue.empty():
            try:
                audio_data = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                audio_b64 = base64.b64encode(audio_data).decode('ascii')
                await self._send_message({
                    "type": "audio",
                    "audio": audio_b64
                })
            except asyncio.TimeoutError:
                continue

        await tts.close()

    def _on_transcript(self, text: str, is_final: bool):
        """ASR callback"""
        asyncio.create_task(self._handle_transcript(text, is_final))

    async def _handle_transcript(self, text: str, is_final: bool):
        if self.is_speaking:
            return

        self.current_transcript = text
        await self._send_message({
            "type": "transcript",
            "text": text,
            "is_final": is_final
        })

    def _on_asr_error(self, error: str):
        asyncio.create_task(self._send_message({
            "type": "error",
            "message": f"ASR error: {error}"
        }))

    async def handle_audio(self, audio_b64: str):
        """Handle audio from frontend"""
        if self.is_speaking:
            return

        try:
            audio_bytes = base64.b64decode(audio_b64)

            # Send to ASR
            if self.asr_session:
                await self.asr_session.send_audio(audio_bytes)

            # Buffer for Omni
            self.audio_buffer.append(audio_bytes)
        except Exception as e:
            print(f"[StructuredInterview] Audio error: {e}")

    async def handle_commit(self):
        """Handle user commit (finished speaking)"""
        if self.is_speaking or not self.audio_buffer:
            return

        # Get audio and transcript
        audio_data = b''.join(self.audio_buffer)
        candidate_text = self.current_transcript or "(语音输入)"

        self.audio_buffer = []
        self.current_transcript = ""

        await self._send_status("processing")

        # Convert to WAV
        wav_data = self._pcm_to_wav(audio_data)

        # Save candidate audio
        record = self.state_machine.record
        audio_path = self.storage.save_audio(
            session_id=self.session_id,
            round_number=record.current_round,
            role="candidate",
            audio_data=wav_data
        )

        # Add candidate dialogue
        duration = len(audio_data) / (16000 * 2)
        record.add_dialogue(
            role="candidate",
            content=candidate_text,
            audio_path=audio_path,
            duration_seconds=duration
        )

        # Broadcast to HR
        await self._broadcast_to_hr({
            "type": "dialogue",
            "session_id": self.session_id,
            "role": "candidate",
            "content": candidate_text,
            "phase": record.current_phase.value,
            "round": record.current_round,
            "audio_url": self.storage.get_audio_url(audio_path)
        })

        # Process turn in state machine
        should_advance = getattr(self, '_pending_advance', False)
        self._pending_advance = False

        result = self.state_machine.process_turn(
            interviewer_text="",  # Already added
            candidate_text=candidate_text,
            candidate_audio=audio_path,
            candidate_duration=duration,
            should_advance=should_advance
        )

        # Save record
        self.storage.save_record(record)

        # Check if interview ended
        if result["interview_ended"]:
            await self._end_interview("面试流程完成")
            return

        # Check if phase changed
        if result["phase_changed"]:
            await self._send_phase_start()

        # Reconnect ASR
        await self._reconnect_asr()

        # Generate next response using Qwen-Omni with audio
        await self._generate_response_with_audio(wav_data, candidate_text)

    async def _generate_response_with_audio(self, audio_data: bytes, transcript: str):
        """Generate response using Qwen-Omni with audio input"""
        self.is_speaking = True
        await self._send_status("speaking")

        try:
            record = self.state_machine.record
            phase = record.current_phase
            round_num = record.current_round

            # Build system prompt
            phase_config = PHASE_CONFIGS[phase]
            system_prompt = f"""你是专业的技术面试官，正在进行语音面试。

## 语言要求
- 必须全程使用中文
- 回复简洁，不超过3句话

## 当前阶段: {phase_config.description}
## 阶段指导: {phase_config.prompt_hint}
## 轮次: {round_num + 1} / {phase_config.max_rounds}

## 候选人背景
{self.interviewer.resume_summary}

## 岗位信息
{self.interviewer.job_info}
"""

            # Build history
            history = [
                {"role": d.role.value if d.role.value != "candidate" else "user",
                 "content": d.content}
                for d in record.dialogues[:-1]  # Exclude last (candidate just added)
            ]

            # Call Qwen-Omni with audio
            full_response = ""

            async for response in self.omni_client.chat_with_audio(
                audio_data=audio_data,
                audio_format="wav",
                system_prompt=system_prompt,
                history=history,
                output_audio=True
            ):
                if response.is_complete:
                    break

                if response.text:
                    full_response += response.text
                    await self._send_message({
                        "type": "response_text",
                        "text": response.text
                    })

                if response.audio_base64:
                    await self._send_message({
                        "type": "audio",
                        "audio": response.audio_base64
                    })

            # Add interviewer response to record
            record.add_dialogue(
                role="interviewer",
                content=full_response
            )

            # Save
            self.storage.save_record(record)

            # Broadcast to HR
            await self._broadcast_to_hr({
                "type": "dialogue",
                "session_id": self.session_id,
                "role": "interviewer",
                "content": full_response,
                "phase": phase.value,
                "round": round_num
            })

        except Exception as e:
            print(f"[StructuredInterview] Generate with audio error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_speaking = False
            await self._send_status("listening")

    async def _end_interview(self, reason: str):
        """End interview and generate evaluation"""
        await self._send_status("evaluating")

        # Generate evaluation
        record = self.state_machine.record
        record = await self.evaluator.evaluate_and_save(record, self.job_info)

        # Save final record
        self.storage.save_record(record)

        # Send to frontend
        await self._send_message({
            "type": "end",
            "reason": reason,
            "evaluation": record.evaluation.model_dump() if record.evaluation else None
        })

        # Broadcast to HR
        await self._broadcast_to_hr({
            "type": "interview_end",
            "session_id": self.session_id,
            "reason": reason,
            "evaluation": record.evaluation.model_dump() if record.evaluation else None
        })

        self.is_active = False

    async def handle_hr_intervention(self, action: str, data: Dict[str, Any]):
        """Handle HR intervention commands"""
        if action == "force_advance":
            self.state_machine.force_advance_phase("hr_intervention")
            await self._send_phase_start()
            await self._send_message({
                "type": "system",
                "message": "HR已切换到下一阶段"
            })

        elif action == "force_end":
            reason = data.get("reason", "HR结束面试")
            self.state_machine.force_end(reason)
            await self._end_interview(reason)

        elif action == "inject_question":
            question = data.get("question", "")
            if question:
                self.state_machine.record.add_dialogue(
                    role="system",
                    content=f"[HR注入问题] {question}"
                )
                # Generate response for the injected question
                await self._send_message({
                    "type": "response_text",
                    "text": question
                })
                await self._synthesize_and_send_audio(question)

    def add_hr_watcher(self, ws: WebSocket):
        """Add HR watcher"""
        self.hr_watchers.append(ws)
        self.state_machine.record.hr_watchers.append(str(id(ws)))

    def remove_hr_watcher(self, ws: WebSocket):
        """Remove HR watcher"""
        if ws in self.hr_watchers:
            self.hr_watchers.remove(ws)

    async def _broadcast_to_hr(self, message: Dict[str, Any]):
        """Broadcast message to all HR watchers"""
        for ws in self.hr_watchers[:]:
            try:
                await ws.send_json(message)
            except:
                self.hr_watchers.remove(ws)

    async def _send_message(self, message: Dict[str, Any]):
        """Send message to frontend"""
        try:
            await self.websocket.send_json(message)
        except:
            pass

    async def _send_status(self, status: str):
        """Send status update"""
        await self._send_message({"type": "status", "status": status})

    async def _reconnect_asr(self):
        """Reconnect ASR"""
        if self.asr_session:
            await self.asr_session.close()

        self.asr_session = ParaformerASRSession(
            on_transcript=self._on_transcript,
            on_error=self._on_asr_error
        )
        await self.asr_session.connect()

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Convert PCM to WAV"""
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(pcm_data)
        return wav_buffer.getvalue()

    async def close(self):
        """Cleanup"""
        self.is_active = False
        if self.asr_session:
            await self.asr_session.close()


@router.websocket("/ws/structured-interview/{session_id}")
async def structured_interview_ws(websocket: WebSocket, session_id: str):
    """Structured interview WebSocket endpoint"""
    await websocket.accept()

    # Get session data (simplified - in production, verify from database)
    from app.services.interview_service import InterviewService
    from app.services.jd_service import JDService
    from app.services.resume_parser import ResumeParser

    interview_service = InterviewService()
    jd_service = JDService()
    resume_parser = ResumeParser()

    session_data = interview_service.get_by_token(session_id)
    if not session_data:
        await websocket.close(4001, "Invalid session")
        return

    # Load resume and JD
    resume_summary = "候选人信息"
    job_info = "岗位信息"

    if session_data.resume_id:
        resume = resume_parser.get_resume(session_data.resume_id)
        if resume:
            resume_summary = f"{resume.basic_info.name or '候选人'}, 技能: {', '.join(resume.skills.hard_skills[:5]) if resume.skills.hard_skills else '无'}"

    if session_data.jd_id:
        jd = jd_service.get(session_data.jd_id)
        if jd:
            job_info = f"{jd.title}, 要求: {', '.join(jd.required_skills[:5]) if jd.required_skills else '无'}"

    # Create session
    session = StructuredInterviewSession(
        websocket=websocket,
        session_id=session_id,
        resume_id=session_data.resume_id,
        jd_id=session_data.jd_id,
        resume_summary=resume_summary,
        job_info=job_info
    )

    active_sessions[session_id] = session

    try:
        if not await session.start():
            await websocket.close(4003, "Failed to start")
            return

        while session.is_active:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                msg_type = message.get("type", "")

                if msg_type == "audio":
                    await session.handle_audio(message.get("audio", ""))

                elif msg_type == "commit":
                    await session.handle_commit()

                elif msg_type == "stop":
                    await session._end_interview("用户结束")

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        print(f"[StructuredInterview] Client disconnected: {session_id}")

    finally:
        await session.close()
        if session_id in active_sessions:
            del active_sessions[session_id]


@router.websocket("/ws/hr-monitor/{session_id}")
async def hr_monitor_ws(websocket: WebSocket, session_id: str):
    """HR monitoring WebSocket - watch interview in real-time"""
    await websocket.accept()

    session = active_sessions.get(session_id)
    if not session:
        await websocket.close(4004, "Session not found or not active")
        return

    session.add_hr_watcher(websocket)

    # Send current state
    record = session.state_machine.record
    await websocket.send_json({
        "type": "sync",
        "session_id": session_id,
        "phase": record.current_phase.value,
        "round": record.current_round,
        "dialogues": [d.model_dump() for d in record.dialogues],
        "status": record.status.value
    })

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "intervention":
                action = message.get("action")
                await session.handle_hr_intervention(action, message)

            elif message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        session.remove_hr_watcher(websocket)
```

**Step 2: Register the router**

Add to `backend/app/main.py`:

```python
from app.api.routes.ws_structured_interview import router as structured_interview_router
app.include_router(structured_interview_router, tags=["structured-interview"])
```

**Step 3: Commit**

```bash
git add backend/app/api/routes/ws_structured_interview.py
git commit -m "feat: add structured interview WebSocket with state machine"
```

---

## Phase 5: HR Replay API

### Task 5.1: Replay REST API

**Files:**
- Create: `backend/app/api/routes/interview_replay.py`

**Step 1: Create the replay API**

```python
# backend/app/api/routes/interview_replay.py
"""HR Interview Replay API"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional, List
from pathlib import Path

from app.services.interview_storage import get_interview_storage
from app.models.interview_record import InterviewRecord, InterviewRecordStatus

router = APIRouter(prefix="/api/interviews", tags=["interview-replay"])

storage = get_interview_storage()


@router.get("", response_model=List[dict])
async def list_interviews(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """List all interview records"""
    records = storage.list_records(limit=limit, offset=offset, status=status)
    return [
        {
            "session_id": r.session_id,
            "resume_id": r.resume_id,
            "jd_id": r.jd_id,
            "status": r.status.value,
            "current_phase": r.current_phase.value,
            "dialogue_count": len(r.dialogues),
            "duration": r.get_total_duration(),
            "created_at": r.created_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "has_evaluation": r.evaluation is not None,
            "overall_score": r.evaluation.overall_score if r.evaluation else None
        }
        for r in records
    ]


@router.get("/{session_id}")
async def get_interview(session_id: str):
    """Get full interview record"""
    record = storage.load_record(session_id)
    if not record:
        raise HTTPException(404, "Interview not found")

    return record.model_dump()


@router.get("/{session_id}/dialogues")
async def get_dialogues(
    session_id: str,
    phase: Optional[str] = Query(None, description="Filter by phase")
):
    """Get interview dialogues with audio URLs"""
    record = storage.load_record(session_id)
    if not record:
        raise HTTPException(404, "Interview not found")

    dialogues = record.dialogues
    if phase:
        dialogues = [d for d in dialogues if d.phase == phase]

    return [
        {
            **d.model_dump(),
            "audio_url": storage.get_audio_url(d.audio_path) if d.audio_path else None
        }
        for d in dialogues
    ]


@router.get("/{session_id}/evaluation")
async def get_evaluation(session_id: str):
    """Get interview evaluation report"""
    record = storage.load_record(session_id)
    if not record:
        raise HTTPException(404, "Interview not found")

    if not record.evaluation:
        raise HTTPException(404, "Evaluation not available")

    return record.evaluation.model_dump()


@router.get("/{session_id}/audio/{filename}")
async def get_audio(session_id: str, filename: str):
    """Serve audio file"""
    audio_dir = storage.base_dir / session_id / "audio"
    audio_path = audio_dir / filename

    if not audio_path.exists():
        raise HTTPException(404, "Audio not found")

    return FileResponse(
        audio_path,
        media_type="audio/wav",
        filename=filename
    )


@router.post("/{session_id}/highlight")
async def highlight_dialogue(
    session_id: str,
    dialogue_id: str,
    notes: Optional[str] = None
):
    """Mark a dialogue as highlighted (for HR review)"""
    record = storage.load_record(session_id)
    if not record:
        raise HTTPException(404, "Interview not found")

    for d in record.dialogues:
        if d.id == dialogue_id:
            d.is_highlighted = True
            d.hr_notes = notes
            storage.save_record(record)
            return {"success": True}

    raise HTTPException(404, "Dialogue not found")


@router.delete("/{session_id}")
async def delete_interview(session_id: str):
    """Delete interview record"""
    if storage.delete_record(session_id):
        return {"success": True}
    raise HTTPException(404, "Interview not found")
```

**Step 2: Register router in main.py**

```python
from app.api.routes.interview_replay import router as replay_router
app.include_router(replay_router)
```

**Step 3: Commit**

```bash
git add backend/app/api/routes/interview_replay.py
git commit -m "feat: add HR interview replay REST API"
```

---

## Phase 6: Frontend Updates

### Task 6.1: Update Interview Frontend

**Files:**
- Modify: `interview-frontend/src/views/VoiceInterview.vue`

Update WebSocket connection to use new structured endpoint and handle phase changes.

Key changes:
1. Connect to `/ws/structured-interview/{sessionId}`
2. Handle `phase_change` messages
3. Display current phase and progress
4. Add HR control panel (if HR role)

### Task 6.2: Create HR Replay View

**Files:**
- Create: `interview-frontend/src/views/HRReplay.vue`

Features:
1. List all interviews with filters
2. Play back interview with timeline
3. Jump to specific phase/round
4. View evaluation report
5. Highlight important moments

### Task 6.3: Create HR Monitor View

**Files:**
- Create: `interview-frontend/src/views/HRMonitor.vue`

Features:
1. Real-time interview watching
2. Intervention controls (advance phase, end, inject question)
3. Live dialogue display

---

## Testing Checklist

After completing all tasks, verify:

1. [ ] State machine correctly advances through 7 phases
2. [ ] Dialogues are saved with audio files
3. [ ] HR can list and replay interviews
4. [ ] HR can watch live interviews
5. [ ] HR intervention commands work
6. [ ] Evaluation report generates correctly
7. [ ] Audio playback works in replay

---

## Commit Summary

After all tasks:
```bash
git log --oneline -20
```

Should show incremental, atomic commits for each feature.
