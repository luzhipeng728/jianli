"""
HR Interview Replay REST API

This module provides REST endpoints for HR personnel to replay, review,
and manage completed interviews. It supports:
- Listing and filtering interview records
- Retrieving full interview data with audio
- Accessing phase-specific dialogues
- Viewing evaluation reports
- Serving audio files
- Highlighting important dialogues with notes
- Deleting interview records
"""

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse
from typing import List, Optional
from pathlib import Path

from app.services.interview_storage import get_interview_storage
from app.models.interview_record import InterviewRecord, EvaluationReport
from app.models.dialogue import DialogueEntry
from app.models.interview_phase import InterviewPhase

router = APIRouter(
    prefix="/api/interviews",
    tags=["interview-replay"],
)

storage = get_interview_storage()


@router.get("", response_model=List[dict])
async def list_interviews(
    status: Optional[str] = Query(None, description="Filter by status: not_started, in_progress, completed, etc."),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip")
) -> List[dict]:
    """
    List all interview records with pagination and optional status filtering.

    Returns a summary of each interview including:
    - Session ID and basic metadata
    - Status and timestamps
    - Total duration
    - Evaluation score (if available)
    """
    records = storage.list_records(limit=limit, offset=offset, status=status)

    # Return summary data
    return [
        {
            "session_id": record.session_id,
            "resume_id": record.resume_id,
            "jd_id": record.jd_id,
            "status": record.status.value,
            "current_phase": record.current_phase.value,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            "total_duration": record.get_total_duration(),
            "dialogue_count": len(record.dialogues),
            "evaluation_score": record.evaluation.overall_score if record.evaluation else None,
            "evaluation_recommendation": record.evaluation.recommendation if record.evaluation else None,
        }
        for record in records
    ]


@router.get("/{session_id}", response_model=dict)
async def get_interview(session_id: str) -> dict:
    """
    Get complete interview record for a specific session.

    Returns:
    - Full interview record with all metadata
    - All dialogues across all phases
    - Phase transitions
    - Evaluation report
    - Audio URLs for playback
    """
    record = storage.load_record(session_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview record not found: {session_id}"
        )

    # Convert to dict and add audio URLs
    data = record.model_dump(mode="json")

    # Replace audio paths with URLs for frontend
    for dialogue in data["dialogues"]:
        if dialogue.get("audio_path"):
            dialogue["audio_url"] = storage.get_audio_url(dialogue["audio_path"])

    return data


@router.get("/{session_id}/dialogues", response_model=List[dict])
async def get_dialogues(
    session_id: str,
    phase: Optional[str] = Query(None, description="Filter by phase: opening, technical, behavioral, etc.")
) -> List[dict]:
    """
    Get dialogues for a specific interview, optionally filtered by phase.

    Each dialogue includes:
    - Content and metadata
    - Audio URL for playback
    - Highlighting status and HR notes
    """
    record = storage.load_record(session_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview record not found: {session_id}"
        )

    # Filter by phase if requested
    if phase:
        try:
            phase_enum = InterviewPhase(phase)
            dialogues = record.get_phase_dialogues(phase_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid phase: {phase}"
            )
    else:
        dialogues = record.dialogues

    # Convert to dict and add audio URLs
    result = []
    for dialogue in dialogues:
        dialogue_dict = dialogue.model_dump(mode="json")
        if dialogue.audio_path:
            dialogue_dict["audio_url"] = storage.get_audio_url(dialogue.audio_path)
        result.append(dialogue_dict)

    return result


@router.get("/{session_id}/evaluation", response_model=dict)
async def get_evaluation(session_id: str) -> dict:
    """
    Get evaluation report for a specific interview.

    Returns comprehensive evaluation including:
    - Overall score and recommendation
    - Dimensional scores with weights
    - Highlights and concerns
    - Summary feedback
    """
    record = storage.load_record(session_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview record not found: {session_id}"
        )

    if not record.evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No evaluation available for interview: {session_id}"
        )

    return record.evaluation.model_dump(mode="json")


@router.get("/{session_id}/audio/{filename}")
async def get_audio(session_id: str, filename: str) -> FileResponse:
    """
    Serve audio file for playback.

    Audio files are stored in: /data/interviews/{session_id}/audio/{filename}
    Supports formats: .wav, .mp3, .pcm
    """
    # Construct audio path
    session_dir = storage.base_dir / session_id
    audio_path = session_dir / "audio" / filename

    # Security check: ensure path is within session directory
    try:
        audio_path = audio_path.resolve()
        session_dir = session_dir.resolve()
        if not str(audio_path).startswith(str(session_dir)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )

    # Check file exists
    if not audio_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file not found: {filename}"
        )

    # Determine media type based on extension
    media_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".pcm": "audio/pcm",
    }
    media_type = media_types.get(audio_path.suffix.lower(), "application/octet-stream")

    return FileResponse(
        path=str(audio_path),
        media_type=media_type,
        filename=filename
    )


@router.post("/{session_id}/highlight")
async def highlight_dialogue(
    session_id: str,
    dialogue_id: str = Query(..., description="ID of the dialogue to highlight"),
    notes: Optional[str] = Query(None, description="HR notes for this dialogue")
) -> dict:
    """
    Mark a dialogue as highlighted and optionally add HR notes.

    This allows HR personnel to flag important moments in the interview
    for later review or discussion.
    """
    record = storage.load_record(session_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview record not found: {session_id}"
        )

    # Find the dialogue
    dialogue = None
    for d in record.dialogues:
        if d.id == dialogue_id:
            dialogue = d
            break

    if not dialogue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dialogue not found: {dialogue_id}"
        )

    # Update highlighting
    dialogue.is_highlighted = True
    if notes:
        dialogue.hr_notes = notes

    # Save updated record
    storage.save_record(record)

    return {
        "success": True,
        "dialogue_id": dialogue_id,
        "is_highlighted": dialogue.is_highlighted,
        "hr_notes": dialogue.hr_notes
    }


@router.delete("/{session_id}")
async def delete_interview(session_id: str) -> dict:
    """
    Delete an interview record and all associated files (including audio).

    Warning: This operation is irreversible!
    """
    success = storage.delete_record(session_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview record not found: {session_id}"
        )

    return {
        "success": True,
        "session_id": session_id,
        "message": "Interview record deleted successfully"
    }
