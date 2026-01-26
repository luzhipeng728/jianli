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
        """Save interview record to JSON file"""
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
        format: str = "wav",
        phase: str = None
    ) -> str:
        """Save audio file

        Args:
            session_id: Interview session ID
            round_number: Round number within the phase
            role: 'candidate' or 'interviewer'
            audio_data: Audio bytes
            format: Audio format (wav, mp3, etc.)
            phase: Interview phase (opening, self_intro, etc.) - used to avoid filename collisions
        """
        session_dir = self._get_session_dir(session_id)
        audio_dir = session_dir / "audio"
        audio_dir.mkdir(exist_ok=True)

        # Include phase in filename to avoid overwriting
        if phase:
            filename = f"{phase}_round_{round_number}_{role}.{format}"
        else:
            filename = f"round_{round_number}_{role}.{format}"
        path = audio_dir / filename

        with open(path, "wb") as f:
            f.write(audio_data)

        return f"audio/{filename}"  # Return relative path

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

    def get_audio_url(self, audio_path: str, session_id: str = None) -> str:
        """Convert local path to API URL for frontend

        Args:
            audio_path: Can be relative (audio/filename.wav) or absolute path
            session_id: Required for relative paths
        """
        path = Path(audio_path)
        filename = path.name

        # For relative paths like "audio/filename.wav", use provided session_id
        if session_id and not audio_path.startswith("/"):
            return f"/api/interviews/{session_id}/audio/{filename}"

        # For absolute paths, extract session_id from path
        extracted_session_id = path.parent.parent.name
        return f"/api/interviews/{extracted_session_id}/audio/{filename}"


# Global instance
_storage: Optional[InterviewStorage] = None

def get_interview_storage() -> InterviewStorage:
    global _storage
    if _storage is None:
        _storage = InterviewStorage()
    return _storage
