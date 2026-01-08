"""Structured Voice Interview WebSocket with 7-Phase State Machine

Integrates:
- InterviewStateMachine (7-phase interview flow)
- InterviewStorage (record and audio persistence)
- UnifiedInterviewerAgent (phase-aware questioning)
- EvaluatorAgent (post-interview evaluation)
- VoiceService (ASR + TTS via Alibaba Cloud)

WebSocket Endpoints:
- /ws/structured-interview/{session_id} - Main interview endpoint
- /ws/hr-monitor/{session_id} - HR monitoring endpoint
"""

import json
import asyncio
import base64
import struct
import wave
import io
from datetime import datetime
from typing import Optional, Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from app.services.interview_state_machine import InterviewStateMachine
from app.services.interview_storage import get_interview_storage
from app.agents.unified_interviewer_agent import UnifiedInterviewerAgent
from app.agents.evaluator_agent import EvaluatorAgent
from app.services.voice_service import get_voice_service, ASRResult, TTSChunk
from app.models.interview_phase import InterviewPhase, PHASE_CONFIGS
from app.models.interview_record import InterviewRecordStatus

router = APIRouter()

# Global session manager
active_sessions: Dict[str, "StructuredInterviewSession"] = {}


class StructuredInterviewSession:
    """Manages a single structured interview session"""

    def __init__(
        self,
        session_id: str,
        websocket: WebSocket,
        resume_id: str,
        jd_id: str,
        resume_summary: str,
        job_info: str
    ):
        self.session_id = session_id
        self.websocket = websocket
        self.resume_id = resume_id
        self.jd_id = jd_id
        self.resume_summary = resume_summary
        self.job_info = job_info

        # Core components
        self.state_machine = InterviewStateMachine(
            session_id=session_id,
            resume_id=resume_id,
            jd_id=jd_id,
            audio_dir=f"/data/interviews/{session_id}"
        )
        self.storage = get_interview_storage()
        self.interviewer = UnifiedInterviewerAgent(
            session_id=session_id,
            resume_summary=resume_summary,
            job_info=job_info
        )
        self.evaluator = EvaluatorAgent()
        self.voice_service = get_voice_service()

        # Audio buffers
        self.audio_buffer: list[bytes] = []
        self.is_processing = False

        # HR watchers
        self.hr_watchers: Set[WebSocket] = set()

        # Lock for thread safety
        self.lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the interview"""
        async with self.lock:
            # Start state machine
            self.state_machine.start()

            # Save initial record
            self.storage.save_record(self.state_machine.record)

            # Send phase start
            await self._send_phase_start()

            # Generate opening message
            await self._generate_and_send_response()

    async def _send_phase_start(self) -> None:
        """Notify frontend of phase change"""
        config = self.state_machine.get_current_phase_config()
        await self._send_message({
            "type": "phase_start",
            "phase": config["phase"],
            "description": config["description"],
            "round": config["current_round"],
            "min_rounds": config["min_rounds"],
            "max_rounds": config["max_rounds"]
        })

        # Broadcast to HR
        await self._broadcast_to_hr({
            "type": "phase_change",
            "session_id": self.session_id,
            "phase": config["phase"],
            "description": config["description"]
        })

    async def _generate_and_send_response(self) -> None:
        """Generate interviewer response and send with audio"""
        record = self.state_machine.record
        phase = record.current_phase
        round_number = record.current_round

        # Build conversation history for agent
        conversation_history = [
            {"role": d.role.value, "content": d.content}
            for d in record.dialogues
        ]

        # Check if can advance early
        can_advance = self.state_machine.can_advance_early()

        # Generate response
        response_text = await self.interviewer.generate_response(
            phase=phase,
            round_number=round_number,
            conversation_history=conversation_history,
            can_advance_early=can_advance
        )

        # Check for advance signal
        response_text, should_advance = self.interviewer.check_advance_signal(response_text)

        # Send text
        await self._send_message({
            "type": "interviewer_text",
            "text": response_text
        })

        # Synthesize and send audio
        await self._synthesize_and_send_audio(response_text)

        # Note: We'll add the interviewer dialogue when we process the user's response
        # This is stored temporarily for the next turn
        self._pending_interviewer_text = response_text
        self._should_advance = should_advance

    async def _synthesize_and_send_audio(self, text: str) -> None:
        """Synthesize text to speech and send to frontend"""
        await self._send_message({
            "type": "status",
            "status": "speaking"
        })

        try:
            # Stream TTS audio
            async for audio_b64 in self.voice_service.text_to_speech_base64(
                text=text,
                voice="zhitian_emo",
                language="Chinese"
            ):
                await self._send_message({
                    "type": "audio",
                    "audio": audio_b64
                })

            # Done speaking
            await self._send_message({
                "type": "status",
                "status": "listening"
            })

        except Exception as e:
            print(f"[TTS Error] {e}")
            await self._send_message({
                "type": "error",
                "message": f"TTS error: {str(e)}"
            })
            await self._send_message({
                "type": "status",
                "status": "listening"
            })

    async def handle_audio(self, audio_b64: str) -> None:
        """Handle audio chunk from frontend"""
        if self.is_processing:
            return  # Drop audio if still processing

        try:
            audio_bytes = base64.b64decode(audio_b64)
            self.audio_buffer.append(audio_bytes)
        except Exception as e:
            print(f"[Audio Buffer Error] {e}")

    async def handle_commit(self) -> None:
        """Handle user finished speaking - process accumulated audio"""
        if self.is_processing:
            return  # Already processing

        async with self.lock:
            self.is_processing = True

            try:
                # Get audio
                if not self.audio_buffer:
                    await self._send_message({
                        "type": "status",
                        "status": "listening"
                    })
                    return

                audio_data = b''.join(self.audio_buffer)
                self.audio_buffer.clear()

                # Set status
                await self._send_message({
                    "type": "status",
                    "status": "processing"
                })

                # ASR - transcribe audio
                transcript = await self._transcribe_audio(audio_data)

                if not transcript or not transcript.strip():
                    await self._send_message({
                        "type": "status",
                        "status": "listening"
                    })
                    return

                # Send transcript to frontend
                await self._send_message({
                    "type": "transcript",
                    "text": transcript,
                    "is_final": True
                })

                # Save audio
                audio_path = await self._save_audio(audio_data, "candidate")

                # Process the turn
                await self._process_turn(transcript, audio_path)

            finally:
                self.is_processing = False

    async def _transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio using ASR"""
        # Create audio stream
        async def audio_stream():
            yield audio_data

        # Run ASR
        final_text = ""
        try:
            async for result in self.voice_service.speech_to_text_stream(audio_stream()):
                # Send partial results
                if not result.is_final:
                    await self._send_message({
                        "type": "transcript",
                        "text": result.text,
                        "is_final": False
                    })
                else:
                    final_text = result.text

        except Exception as e:
            print(f"[ASR Error] {e}")
            return ""

        return final_text

    async def _save_audio(self, audio_data: bytes, role: str) -> str:
        """Save audio file and return path"""
        record = self.state_machine.record
        round_number = record.current_round

        # Convert PCM to WAV
        wav_data = self._pcm_to_wav(audio_data)

        # Save
        audio_path = self.storage.save_audio(
            session_id=self.session_id,
            round_number=round_number,
            role=role,
            audio_data=wav_data,
            format="wav"
        )

        return audio_path

    def _pcm_to_wav(self, pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
        """Convert PCM to WAV format"""
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
        return buffer.getvalue()

    async def _process_turn(self, candidate_text: str, candidate_audio: str) -> None:
        """Process a complete dialogue turn"""
        # Get pending interviewer text
        interviewer_text = getattr(self, "_pending_interviewer_text", "")
        should_advance = getattr(self, "_should_advance", False)

        # Calculate audio durations (approximate)
        candidate_duration = len(candidate_text) * 0.5  # Rough estimate
        interviewer_duration = len(interviewer_text) * 0.5

        # Save interviewer audio (from previous TTS)
        interviewer_audio = None  # We could save TTS output if needed

        # Process turn in state machine
        result = self.state_machine.process_turn(
            interviewer_text=interviewer_text,
            candidate_text=candidate_text,
            interviewer_audio=interviewer_audio,
            candidate_audio=candidate_audio,
            interviewer_duration=interviewer_duration,
            candidate_duration=candidate_duration,
            should_advance=should_advance
        )

        # Save record
        self.storage.save_record(self.state_machine.record)

        # Broadcast to HR
        await self._broadcast_to_hr({
            "type": "dialogue",
            "session_id": self.session_id,
            "interviewer": interviewer_text,
            "candidate": candidate_text,
            "phase": self.state_machine.record.current_phase.value,
            "round": self.state_machine.record.current_round
        })

        # Handle phase change or end
        if result["interview_ended"]:
            await self._end_interview()
        elif result["phase_changed"]:
            await self._send_phase_start()
            await self._generate_and_send_response()
        else:
            # Continue in same phase
            await self._generate_and_send_response()

    async def _end_interview(self) -> None:
        """End interview and generate evaluation"""
        await self._send_message({
            "type": "status",
            "status": "evaluating"
        })

        # Generate evaluation
        try:
            record = self.state_machine.record
            evaluation = await self.evaluator.evaluate(record, self.job_info)

            # Save evaluation to record
            record.evaluation = evaluation
            self.storage.save_record(record)

            # Send evaluation to frontend
            await self._send_message({
                "type": "interview_end",
                "evaluation": evaluation.model_dump(mode="json")
            })

            # Broadcast to HR
            await self._broadcast_to_hr({
                "type": "interview_complete",
                "session_id": self.session_id,
                "evaluation": evaluation.model_dump(mode="json")
            })

        except Exception as e:
            print(f"[Evaluation Error] {e}")
            await self._send_message({
                "type": "interview_end",
                "error": f"Evaluation failed: {str(e)}"
            })

    async def handle_hr_intervention(self, command: str, data: dict) -> None:
        """Handle HR intervention commands"""
        async with self.lock:
            if command == "force_advance":
                # Force advance to next phase
                continued = self.state_machine.force_advance_phase(reason="hr_intervention")

                # Save
                self.storage.save_record(self.state_machine.record)

                # Notify
                if not continued:
                    await self._end_interview()
                else:
                    await self._send_phase_start()
                    await self._generate_and_send_response()

            elif command == "force_end":
                # Force end interview
                reason = data.get("reason", "hr_intervention")
                self.state_machine.force_end(reason)

                # Save
                self.storage.save_record(self.state_machine.record)

                # End
                await self._end_interview()

            elif command == "inject_question":
                # Inject a custom question
                question = data.get("question", "")
                if question:
                    # Override pending interviewer text
                    self._pending_interviewer_text = question
                    self._should_advance = False

                    # Send it
                    await self._send_message({
                        "type": "interviewer_text",
                        "text": question
                    })
                    await self._synthesize_and_send_audio(question)

            else:
                print(f"[HR] Unknown command: {command}")

    def add_hr_watcher(self, websocket: WebSocket) -> None:
        """Add HR watcher"""
        self.hr_watchers.add(websocket)

    def remove_hr_watcher(self, websocket: WebSocket) -> None:
        """Remove HR watcher"""
        self.hr_watchers.discard(websocket)

    async def _broadcast_to_hr(self, message: dict) -> None:
        """Broadcast message to all HR watchers"""
        disconnected = []
        for ws in self.hr_watchers:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        # Remove disconnected watchers
        for ws in disconnected:
            self.hr_watchers.discard(ws)

    async def _send_message(self, message: dict) -> None:
        """Send message to candidate websocket"""
        try:
            await self.websocket.send_json(message)
        except Exception as e:
            print(f"[WebSocket Send Error] {e}")

    async def close(self) -> None:
        """Cleanup session"""
        # Close all HR connections
        for ws in list(self.hr_watchers):
            try:
                await ws.close()
            except Exception:
                pass
        self.hr_watchers.clear()

        # Remove from active sessions
        if self.session_id in active_sessions:
            del active_sessions[self.session_id]


@router.websocket("/ws/structured-interview/{session_id}")
async def structured_interview_websocket(websocket: WebSocket, session_id: str):
    """Main structured interview WebSocket endpoint

    Client message types:
    - {"type": "init", "resume_id": "...", "jd_id": "...", "resume_summary": "...", "job_info": "..."}
    - {"type": "audio", "audio": "base64_pcm_data"}
    - {"type": "commit"}  # User finished speaking
    - {"type": "ping"}

    Server message types:
    - {"type": "phase_start", "phase": "...", "description": "...", ...}
    - {"type": "interviewer_text", "text": "..."}
    - {"type": "audio", "audio": "base64_audio"}
    - {"type": "transcript", "text": "...", "is_final": bool}
    - {"type": "status", "status": "listening|processing|speaking|evaluating"}
    - {"type": "interview_end", "evaluation": {...}}
    - {"type": "error", "message": "..."}
    - {"type": "pong"}
    """

    await websocket.accept()

    session: Optional[StructuredInterviewSession] = None

    try:
        # Wait for init message
        init_data = await websocket.receive_text()
        init_msg = json.loads(init_data)

        if init_msg.get("type") != "init":
            await websocket.send_json({
                "type": "error",
                "message": "First message must be 'init'"
            })
            await websocket.close()
            return

        # Extract init params
        resume_id = init_msg.get("resume_id")
        jd_id = init_msg.get("jd_id")
        resume_summary = init_msg.get("resume_summary", "")
        job_info = init_msg.get("job_info", "")

        if not resume_id or not jd_id:
            await websocket.send_json({
                "type": "error",
                "message": "resume_id and jd_id are required"
            })
            await websocket.close()
            return

        # Create session
        session = StructuredInterviewSession(
            session_id=session_id,
            websocket=websocket,
            resume_id=resume_id,
            jd_id=jd_id,
            resume_summary=resume_summary,
            job_info=job_info
        )

        # Register session
        active_sessions[session_id] = session

        # Start interview
        await session.start()

        # Message loop
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            msg_type = msg.get("type")

            if msg_type == "audio":
                audio_b64 = msg.get("audio", "")
                await session.handle_audio(audio_b64)

            elif msg_type == "commit":
                await session.handle_commit()

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })

    except WebSocketDisconnect:
        print(f"[Interview] Client disconnected: {session_id}")
    except Exception as e:
        print(f"[Interview Error] {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass
    finally:
        if session:
            await session.close()


@router.websocket("/ws/hr-monitor/{session_id}")
async def hr_monitor_websocket(websocket: WebSocket, session_id: str):
    """HR monitoring WebSocket endpoint

    Client message types:
    - {"type": "subscribe"}
    - {"type": "intervention", "command": "force_advance|force_end|inject_question", "data": {...}}
    - {"type": "ping"}

    Server message types:
    - {"type": "phase_change", "session_id": "...", "phase": "...", ...}
    - {"type": "dialogue", "session_id": "...", "interviewer": "...", "candidate": "...", ...}
    - {"type": "interview_complete", "session_id": "...", "evaluation": {...}}
    - {"type": "error", "message": "..."}
    - {"type": "pong"}
    """

    await websocket.accept()

    # Find session
    session = active_sessions.get(session_id)
    if not session:
        await websocket.send_json({
            "type": "error",
            "message": f"Session {session_id} not found or not active"
        })
        await websocket.close()
        return

    # Register as watcher
    session.add_hr_watcher(websocket)

    try:
        # Send initial state
        await websocket.send_json({
            "type": "subscribed",
            "session_id": session_id,
            "current_phase": session.state_machine.record.current_phase.value,
            "current_round": session.state_machine.record.current_round,
            "status": session.state_machine.record.status.value
        })

        # Message loop
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            msg_type = msg.get("type")

            if msg_type == "intervention":
                command = msg.get("command")
                data = msg.get("data", {})
                await session.handle_hr_intervention(command, data)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })

    except WebSocketDisconnect:
        print(f"[HR Monitor] HR disconnected from {session_id}")
    except Exception as e:
        print(f"[HR Monitor Error] {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass
    finally:
        session.remove_hr_watcher(websocket)


@router.get("/api/structured-interview/sessions")
async def list_active_sessions():
    """List all active interview sessions"""
    sessions = []
    for sid, session in active_sessions.items():
        sessions.append({
            "session_id": sid,
            "resume_id": session.resume_id,
            "jd_id": session.jd_id,
            "current_phase": session.state_machine.record.current_phase.value,
            "current_round": session.state_machine.record.current_round,
            "status": session.state_machine.record.status.value,
            "hr_watchers": len(session.hr_watchers)
        })
    return {"sessions": sessions}
