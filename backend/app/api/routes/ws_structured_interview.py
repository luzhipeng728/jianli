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
import os
import httpx
from datetime import datetime
from typing import Optional, Dict, Set, AsyncGenerator
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from app.services.interview_state_machine import InterviewStateMachine
from app.services.interview_storage import get_interview_storage
from app.services.interview_service import InterviewService
from app.models.interview import InterviewStatus
from app.agents.unified_interviewer_agent import UnifiedInterviewerAgent
from app.agents.evaluator_agent import EvaluatorAgent
from app.services.voice_service import get_voice_service, ASRResult, TTSChunk
from app.services.asr_service import ParaformerASRSession
from app.services.jd_analyzer import get_jd_analyzer, InterviewStrategy
from app.models.interview_phase import InterviewPhase, PHASE_CONFIGS
from app.models.interview_record import InterviewRecordStatus


def pcm_to_wav_base64(pcm_base64: str, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> str:
    """将PCM base64转换为WAV base64

    Args:
        pcm_base64: PCM音频的base64编码
        sample_rate: 采样率 (默认16kHz)
        channels: 声道数 (默认单声道)
        sample_width: 采样位宽 (默认2字节/16bit)

    Returns:
        WAV格式的base64编码
    """
    # 解码PCM数据
    pcm_data = base64.b64decode(pcm_base64)

    # 创建WAV文件
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)

    # 获取WAV数据并编码为base64
    wav_data = wav_buffer.getvalue()
    wav_base64 = base64.b64encode(wav_data).decode('utf-8')

    return wav_base64


class QwenOmniTextToAudio:
    """使用 Qwen-Omni 直接生成文本和音频响应"""

    API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, voice: str = "Cherry"):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.voice = voice

    async def generate_with_audio(
        self,
        system_prompt: str,
        messages: list[dict],
        audio_format: str = "mp3"
    ) -> AsyncGenerator[tuple[str, str], None]:
        """生成带音频的响应

        Args:
            system_prompt: 系统提示词
            messages: 对话历史
            audio_format: 音频格式 (mp3, wav)

        Yields:
            tuple[str, str]: (text_chunk, audio_base64_chunk)
        """
        print(f"[Omni] API Key configured: {bool(self.api_key)}, voice: {self.voice}")

        # 使用 qwen3-omni-flash 模型 (支持System Message设定角色)
        # 【重要】关闭思考模式，否则响应会很慢
        request_body = {
            "model": "qwen3-omni-flash",
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages
            ],
            "stream": True,
            "modalities": ["text", "audio"],
            "audio": {
                "voice": self.voice,
                "format": audio_format
            },
            "enable_thinking": False  # 关闭思考模式，加速响应
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        print(f"[Omni] Calling API with modalities: {request_body['modalities']}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                self.API_URL,
                headers=headers,
                json=request_body,
            ) as response:
                print(f"[Omni] Response status: {response.status_code}")
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"[Omni] API error: {response.status_code} - {error_text}")
                    return

                line_count = 0
                async for line in response.aiter_lines():
                    line_count += 1
                    if not line or not line.startswith("data:"):
                        continue

                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        print(f"[Omni] Stream done after {line_count} lines")
                        break

                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if not choices:
                            continue

                        delta = choices[0].get("delta", {})

                        text_chunk = delta.get("content", "") or ""
                        audio_chunk = ""

                        if "audio" in delta and "data" in delta["audio"]:
                            audio_chunk = delta["audio"]["data"]
                            print(f"[Omni] Got audio chunk: {len(audio_chunk)} chars")

                        if text_chunk or audio_chunk:
                            yield (text_chunk, audio_chunk)

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"[Omni] Parse error: {e}")
                        continue

    async def generate_with_audio_input(
        self,
        system_prompt: str,
        messages: list[dict],
        user_audio_b64: str,
        audio_format: str = "mp3"
    ) -> AsyncGenerator[tuple[str, str], None]:
        """生成带音频的响应，接收用户音频输入

        Args:
            system_prompt: 系统提示词
            messages: 对话历史（不包含最新的用户音频）
            user_audio_b64: 用户音频的base64编码（PCM 16kHz）
            audio_format: 输出音频格式 (mp3, wav)

        Yields:
            tuple[str, str]: (text_chunk, audio_base64_chunk)
        """
        print(f"[Omni] Processing audio input, length: {len(user_audio_b64)} chars")
        print(f"[Omni] System prompt (first 500 chars): {system_prompt[:500]}...")
        print(f"[Omni] Previous messages count: {len(messages)}")

        # 【关键修复】将PCM转换为WAV格式
        # qwen3-omni-flash 需要WAV格式的音频输入
        wav_audio_b64 = pcm_to_wav_base64(user_audio_b64, sample_rate=16000)
        print(f"[Omni] Converted PCM to WAV, original: {len(user_audio_b64)} -> wav: {len(wav_audio_b64)} chars")

        # 构建带音频的用户消息 (使用正确的Data URL格式)
        user_audio_message = {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": f"data:;base64,{wav_audio_b64}",
                        "format": "wav"
                    }
                }
            ]
        }

        # 使用 qwen3-omni-flash 模型 (支持System Message设定角色)
        # 【重要】关闭思考模式，否则响应会很慢
        request_body = {
            "model": "qwen3-omni-flash",
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages,
                user_audio_message
            ],
            "stream": True,
            "modalities": ["text", "audio"],
            "audio": {
                "voice": self.voice,
                "format": audio_format
            },
            "enable_thinking": False  # 关闭思考模式，加速响应
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 打印完整的messages结构（不含音频数据）
        debug_messages = []
        for m in request_body["messages"]:
            if m["role"] == "user" and isinstance(m.get("content"), list):
                debug_messages.append({"role": "user", "content": "[AUDIO INPUT]"})
            else:
                debug_messages.append(m)
        print(f"[Omni] Messages structure: {json.dumps(debug_messages, ensure_ascii=False, indent=2)[:1000]}")

        print(f"[Omni] Calling API with audio input")

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                self.API_URL,
                headers=headers,
                json=request_body,
            ) as response:
                print(f"[Omni] Response status: {response.status_code}")
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"[Omni] API error: {response.status_code} - {error_text}")
                    return

                line_count = 0
                audio_chunks = 0
                async for line in response.aiter_lines():
                    line_count += 1
                    if not line or not line.startswith("data:"):
                        continue

                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        print(f"[Omni] Stream done after {line_count} lines, {audio_chunks} audio chunks")
                        break

                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if not choices:
                            continue

                        delta = choices[0].get("delta", {})

                        text_chunk = delta.get("content", "") or ""
                        audio_chunk = ""

                        if "audio" in delta and "data" in delta["audio"]:
                            audio_chunk = delta["audio"]["data"]
                            audio_chunks += 1

                        if text_chunk or audio_chunk:
                            yield (text_chunk, audio_chunk)

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"[Omni] Parse error: {e}")
                        continue


# Global Omni client
_omni_text_to_audio: Optional[QwenOmniTextToAudio] = None

def get_omni_text_to_audio() -> QwenOmniTextToAudio:
    global _omni_text_to_audio
    if _omni_text_to_audio is None:
        _omni_text_to_audio = QwenOmniTextToAudio()
    return _omni_text_to_audio

router = APIRouter()

# Global session manager
active_sessions: Dict[str, "StructuredInterviewSession"] = {}
active_sessions_lock = asyncio.Lock()


class StructuredInterviewSession:
    """Manages a single structured interview session"""

    def __init__(
        self,
        session_id: str,
        websocket: WebSocket,
        resume_id: str,
        jd_id: str,
        resume_summary: str,
        job_info: str,
        position_name: str = "",
        written_test_summary: str = ""
    ):
        self.session_id = session_id
        self.websocket = websocket
        self.resume_id = resume_id
        self.jd_id = jd_id
        self.resume_summary = resume_summary
        self.job_info = job_info
        self.position_name = position_name
        self.written_test_summary = written_test_summary

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
            job_info=job_info,
            written_test_summary=written_test_summary
        )
        self.evaluator = EvaluatorAgent()
        self.voice_service = get_voice_service()
        self.omni_client = get_omni_text_to_audio()  # Qwen-Omni for text+audio
        self.jd_analyzer = get_jd_analyzer()

        # Interview strategy (pre-analyzed)
        self.strategy: Optional[InterviewStrategy] = None

        # Audio buffers
        self.audio_buffer: list[bytes] = []
        self.is_processing = False

        # ASR session for real-time transcription
        self.asr_session: Optional[ParaformerASRSession] = None
        self.current_transcript = ""

        # HR watchers
        self.hr_watchers: Set[WebSocket] = set()

        # Lock for thread safety
        self.lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the interview"""
        async with self.lock:
            print(f"[Interview] start() called for session {self.session_id}")

            # 【关键】先用 Qwen-Plus 分析 JD，生成面试策略
            await self._send_message({
                "type": "status",
                "status": "analyzing"
            })
            print("[Interview] Sent analyzing status to frontend")

            # 定义进度回调，发送分析进度给前端
            async def on_analysis_progress(text: str):
                print(f"[JDAnalyzer] Progress callback: {text[:50]}...")
                await self._send_message({
                    "type": "analysis_progress",
                    "text": text
                })
                print(f"[JDAnalyzer] Sent progress to frontend")

            try:
                print(f"[JDAnalyzer] Starting analysis for position: {self.position_name}")
                print(f"[JDAnalyzer] JD length: {len(self.job_info)}, Resume length: {len(self.resume_summary)}")
                print(f"[JDAnalyzer] API key configured: {bool(self.jd_analyzer.api_key)}")

                self.strategy = await self.jd_analyzer.analyze(
                    jd_text=self.job_info,
                    resume_summary=self.resume_summary,
                    position_name=self.position_name,
                    on_progress=on_analysis_progress
                )
                print(f"[JDAnalyzer] Strategy generated: {len(self.strategy.project_questions)} project questions")
            except Exception as e:
                import traceback
                print(f"[JDAnalyzer] Error: {e}")
                traceback.print_exc()
                await on_analysis_progress(f"⚠️ 分析出错，使用默认策略\n")
                self.strategy = self.jd_analyzer._get_default_strategy(self.position_name)

            # 分析完成，准备开始面试
            await self._send_message({
                "type": "analysis_complete"
            })

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

    async def _send_round_update(self) -> None:
        """Notify frontend of round change within same phase"""
        config = self.state_machine.get_current_phase_config()
        await self._send_message({
            "type": "round_update",
            "phase": config["phase"],
            "description": config["description"],
            "round": config["current_round"],
            "min_rounds": config["min_rounds"],
            "max_rounds": config["max_rounds"]
        })
        print(f"[Round] Updated to round {config['current_round'] + 1}/{config['max_rounds']} in {config['phase']}")

    async def _generate_and_send_response(self) -> None:
        """Generate interviewer response and send with audio using Qwen-Omni"""
        record = self.state_machine.record
        phase = record.current_phase
        round_number = record.current_round

        # Build conversation history for Omni
        messages = []
        for d in record.dialogues:
            messages.append({
                "role": "assistant" if d.role.value == "interviewer" else "user",
                "content": d.content
            })

        # Check if can advance early
        can_advance = self.state_machine.can_advance_early()

        # Build system prompt (from interviewer agent)
        system_prompt = self._build_interviewer_prompt(phase, round_number, can_advance)

        # Add a user message to trigger response if no dialogues yet
        if not messages:
            messages.append({"role": "user", "content": "请开始面试"})

        # Set status to speaking
        await self._send_message({
            "type": "status",
            "status": "speaking"
        })

        try:
            # Stream response with text and audio from Qwen-Omni
            full_text = ""
            audio_chunks_count = 0
            total_audio_size = 0

            async for text_chunk, audio_chunk in self.omni_client.generate_with_audio(
                system_prompt=system_prompt,
                messages=messages,
                audio_format="mp3"
            ):
                # Send text chunk (filter out advance markers before sending)
                if text_chunk:
                    full_text += text_chunk
                    # 过滤掉 [ADVANCE] 等标记后再发送给前端
                    display_chunk = text_chunk
                    for marker in ["[ADVANCE]", "[ADVANCE_PHASE]", "【ADVANCE】", "[advance]"]:
                        display_chunk = display_chunk.replace(marker, "")
                    if display_chunk.strip():
                        await self._send_message({
                            "type": "response_text",
                            "text": display_chunk
                        })

                # Send audio chunk
                if audio_chunk:
                    audio_chunks_count += 1
                    total_audio_size += len(audio_chunk)
                    await self._send_message({
                        "type": "audio",
                        "audio": audio_chunk
                    })

            print(f"[Omni] Audio: {audio_chunks_count} chunks, ~{total_audio_size} bytes (base64)")

            # Check for advance signal in the response
            full_text, should_advance = self.interviewer.check_advance_signal(full_text)

            # Store for next turn
            self._pending_interviewer_text = full_text
            self._should_advance = should_advance

            print(f"[Omni] Generated response: {full_text[:100]}...")

            # Signal that audio stream is complete (frontend will switch to listening after playback)
            await self._send_message({
                "type": "audio_complete"
            })

        except Exception as e:
            print(f"[Omni Error] {e}")
            import traceback
            traceback.print_exc()
            await self._send_message({
                "type": "error",
                "message": f"生成回复失败: {str(e)}"
            })
            # On error, still allow listening
            await self._send_message({
                "type": "audio_complete"
            })

    def _build_interviewer_prompt(self, phase: str, round_number: int, can_advance: bool) -> str:
        """Build system prompt for interviewer based on current phase"""
        phase_str = phase.value if hasattr(phase, 'value') else phase
        phase_config = PHASE_CONFIGS.get(phase) if hasattr(phase, 'value') else None
        max_rounds = phase_config.max_rounds if phase_config else 3

        # 使用预分析的策略生成针对性问题
        strategy = self.strategy
        strategy_hint = ""

        if strategy:
            if phase_str == "opening":
                # 开场使用预生成的开场白
                strategy_hint = f"""
【开场白参考】
{strategy.opening_script}
"""
            elif phase_str == "self_intro":
                strategy_hint = f"""
【关注重点】{strategy.self_intro_focus}
【候选人亮点】{', '.join(strategy.highlights[:3]) if strategy.highlights else '待发现'}
"""
            elif phase_str == "project_deep":
                questions = strategy.project_questions[:5] if strategy.project_questions else []
                # 为每轮指定具体问题，避免重复
                if round_number < len(questions):
                    current_question = questions[round_number]
                    strategy_hint = f"""
【本轮必问问题（第{round_number + 1}轮专用）】
→ {current_question}

【已问过的问题（禁止再问）】
{chr(10).join(f'✗ {questions[i]}' for i in range(round_number)) if round_number > 0 else '（这是第一轮，还没有问过问题）'}

【考察差距点】{', '.join(strategy.gaps[:2]) if strategy.gaps else '无'}
"""
                else:
                    strategy_hint = f"""
【本轮必问问题】
→ 在你做过的项目中，有没有遇到过技术难题？最后是怎么解决的？

【考察差距点】{', '.join(strategy.gaps[:2]) if strategy.gaps else '无'}
【说明】这是本阶段最后一轮，问完等候选人回答后再切换。
"""
            elif phase_str == "tech_assess":
                questions = strategy.tech_questions[:5] if strategy.tech_questions else []
                if round_number < len(questions):
                    current_question = questions[round_number]
                    strategy_hint = f"""
【本轮必问问题（第{round_number + 1}轮专用）】
→ {current_question}

【已问过的问题（禁止再问）】
{chr(10).join(f'✗ {questions[i]}' for i in range(round_number)) if round_number > 0 else '（这是第一轮，还没有问过问题）'}

【岗位核心要求】{', '.join(strategy.core_requirements[:3]) if strategy.core_requirements else '技术能力'}
"""
                else:
                    strategy_hint = f"""
【本轮必问问题】
→ 你觉得自己在技术方面最大的优势是什么？有什么想要提升的地方？

【岗位核心要求】{', '.join(strategy.core_requirements[:3]) if strategy.core_requirements else '技术能力'}
【说明】这是本阶段最后一轮，问完等候选人回答后再切换。
"""
            elif phase_str == "behavioral":
                questions = strategy.behavioral_questions[:3] if strategy.behavioral_questions else []
                if round_number < len(questions):
                    current_question = questions[round_number]
                    strategy_hint = f"""
【本轮必问问题（第{round_number + 1}轮专用）】
→ {current_question}

【已问过的问题（禁止再问）】
{chr(10).join(f'✗ {questions[i]}' for i in range(round_number)) if round_number > 0 else '（这是第一轮，还没有问过问题）'}
"""
                else:
                    strategy_hint = f"""
【本轮必问问题】
→ 在工作中遇到过最大的挑战是什么？你是怎么克服的？

【说明】这是本阶段最后一轮，问完这个问题等候选人回答后再切换。
"""

        # 笔试成绩提示（仅在开场阶段显示）
        written_test_hint = ""
        if phase_str == "opening" and self.written_test_summary:
            written_test_hint = f"（笔试成绩：{self.written_test_summary[:50]}，可简单提一句）"

        # 根据不同阶段生成不同的提示词
        if phase_str == "opening":
            # 开场阶段 - 只问候，最后问"准备好了吗"
            base_prompt = f"""你是{self.position_name or '技术岗位'}的面试官，现在是【开场环节】。

请按以下内容开场：
{strategy_hint}
{written_test_hint}

【你的开场白结构】：
1. 问候："你好，欢迎参加今天的面试。"
2. 自我介绍："我是今天的面试官，来自XX部门。"
3. 说明流程："今天面试大约30分钟，会分为几个环节：自我介绍、项目经验、技术能力、综合素质考察，最后你可以问我一些问题。"
4. 如有笔试成绩可简单提一句
5. 【必须以这句话结尾】："你准备好了吗？准备好我们就开始。"

【绝对禁止】：
- 不要直接让候选人自我介绍（那是下一个环节）
- 不要问技术问题
- 必须以"你准备好了吗？"结尾"""

        elif phase_str == "self_intro":
            # 自我介绍阶段
            if round_number == 0:
                # 第一轮：让候选人介绍自己
                base_prompt = f"""你是面试官，候选人刚才说"准备好了"，现在进入【自我介绍环节】。

【你只需要说】：
"好的，那我们正式开始。首先请你简单介绍一下自己，包括教育背景、工作经历和主要技能。大概2-3分钟就可以。"

【绝对禁止】：不要问技术问题，只是让候选人介绍自己。"""
            else:
                # 第二轮：简短确认，准备进入下一阶段
                base_prompt = f"""你是面试官，候选人刚完成自我介绍。

【你只需要说一句话】（不超过30字）：
"好的，对你的背景有了解了。那我们进入下一个环节。"

【绝对禁止】：
- 不要长篇总结候选人的介绍内容
- 不要评价"很好"、"不错"
- 就一句话，然后加上 [ADVANCE]"""

        elif phase_str == "qa":
            # Q&A阶段 - 让候选人提问
            base_prompt = f"""你是面试官，现在进入【候选人提问环节】。

【过渡语】：
"好的，技术相关的问题就问到这里了。现在进入【反向提问环节】，你有什么想问我的吗？关于公司、团队、岗位或者技术栈的问题都可以。"

【如果候选人问了问题】：简洁回答，然后问"还有其他问题吗？"
【如果候选人说没问题】：说"好的，那我们进入最后的结束环节。"然后加上 [ADVANCE]"""

        elif phase_str == "closing":
            # 结束阶段 - 感谢告别
            base_prompt = f"""你是面试官，现在进入【结束环节】。

【你只需要说】：
"好的，今天的面试就全部结束了。非常感谢你抽时间参加这次面试，后续HR会在一周内和你联系沟通结果。祝你一切顺利，再见！"

【绝对禁止】：不要再问任何问题！"""

        else:
            # 项目深挖/技术评估/行为面试阶段 - 从必问问题中选择
            phase_names = {
                "project_deep": "项目经验深挖",
                "tech_assess": "技术能力评估",
                "behavioral": "综合素质考察"
            }
            phase_purposes = {
                "project_deep": "了解你在实际项目中的技术实践和解决问题的能力",
                "tech_assess": "考察你的技术基础和专业知识掌握程度",
                "behavioral": "了解你的沟通协作、学习能力等软技能"
            }
            phase_name = phase_names.get(phase_str, "面试")
            phase_purpose = phase_purposes.get(phase_str, "评估候选人能力")

            # 第一轮需要过渡语
            if round_number == 0:
                transition = f"""【阶段过渡】：
先说："好的，接下来我们进入【{phase_name}】环节，第1轮（共{max_rounds}轮）。这个环节主要是{phase_purpose}。"
然后再问问题。

"""
            else:
                transition = f"""【当前进度】：{phase_name}环节，第{round_number + 1}轮（共{max_rounds}轮）。

"""

            base_prompt = f"""你是{self.position_name or '技术'}面试官，当前是【{phase_name}】第{round_number + 1}轮（共{max_rounds}轮）。

{transition}{strategy_hint}

【回复格式】：
第一部分：简短回应候选人（1句话，最多20字）
- 候选人说了具体内容 → 简单概括："嗯，你用的是向量检索方案。"
- 候选人说不会/没做过 → "好的，了解。"
- 候选人说得很少 → "嗯，明白。"

第二部分：问→标记的问题
- 用过渡词连接："那接下来"、"另外想问一下"
- 必须问→标记的那个问题，不能自己编

【示例】：
"嗯，你主要用的是RAG方案。那接下来，在Agent开发中你是怎么处理工具调用的？"

【禁止】：
❌ 不要长篇复述候选人说的内容
❌ 不要追问上一个话题的细节
❌ 不要自己编问题"""

        if can_advance:
            base_prompt += """

【关于阶段切换 - 注意！】
- 你仍然必须先问上面→标记的问题！
- 只有在候选人回答后，你才能考虑是否切换
- 如果候选人回答得很充分，下一轮回复时可以在末尾加 [ADVANCE]
- 绝对不能跳过问题直接切换！"""

        return base_prompt

    async def _synthesize_and_send_audio(self, text: str) -> None:
        """Synthesize text to speech and send to frontend (fallback TTS)"""
        await self._send_message({
            "type": "status",
            "status": "speaking"
        })

        try:
            # Stream TTS audio
            async for audio_b64 in self.voice_service.text_to_speech_base64(
                text=text,
                voice="longxiaochun",
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

            # Start ASR session if not started
            if self.asr_session is None:
                await self._start_asr_session()

            # Send audio to ASR for real-time transcription
            if self.asr_session:
                await self.asr_session.send_audio(audio_bytes)

        except Exception as e:
            print(f"[Audio Buffer Error] {e}")

    async def _start_asr_session(self) -> None:
        """Start ASR session for real-time transcription"""
        try:
            self.current_transcript = ""
            self._finalized_sentences = []  # 存储已完成的句子
            self._current_sentence = ""  # 当前正在识别的句子

            def on_transcript(text: str, is_final: bool):
                """ASR callback - send transcript to frontend"""
                if is_final:
                    # 句子完成，添加到已完成列表
                    if text.strip():
                        self._finalized_sentences.append(text.strip())
                    self._current_sentence = ""
                else:
                    # 正在识别的句子
                    self._current_sentence = text

                # 合并所有已完成句子 + 当前句子
                full_text = "".join(self._finalized_sentences)
                if self._current_sentence:
                    full_text += self._current_sentence
                self.current_transcript = full_text

                # Use asyncio to send message from sync callback
                asyncio.create_task(self._send_message({
                    "type": "transcript",
                    "text": full_text,  # 发送完整文本
                    "is_final": is_final
                }))

            def on_error(error: str):
                """ASR error callback"""
                print(f"[ASR Error] {error}")

            self.asr_session = ParaformerASRSession(
                on_transcript=on_transcript,
                on_error=on_error,
                sample_rate=16000
            )

            connected = await self.asr_session.connect()
            if connected:
                print("[ASR] Session started for real-time transcription")
            else:
                print("[ASR] Failed to connect, will use fallback")
                self.asr_session = None

        except Exception as e:
            print(f"[ASR] Failed to start session: {e}")
            self.asr_session = None

    async def _stop_asr_session(self) -> str:
        """Stop ASR session and get final transcript"""
        transcript = self.current_transcript
        if self.asr_session:
            try:
                await self.asr_session.finish()
                await asyncio.sleep(0.5)  # Wait for final result
                transcript = self.current_transcript
                await self.asr_session.close()
            except Exception as e:
                print(f"[ASR] Error stopping session: {e}")
            finally:
                self.asr_session = None
                self.current_transcript = ""
        return transcript

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

                print(f"[Interview] Processing audio: {len(audio_data)} bytes")

                # Stop ASR and get final transcript
                user_transcript = await self._stop_asr_session()
                print(f"[ASR] Final transcript: {user_transcript}")

                # Set status
                await self._send_message({
                    "type": "status",
                    "status": "processing"
                })

                # Save user audio
                audio_path = await self._save_audio(audio_data, "candidate")

                # Convert audio to base64 for Qwen-Omni
                user_audio_b64 = base64.b64encode(audio_data).decode('ascii')

                # Generate response using Qwen-Omni with audio input
                await self._generate_response_with_audio(user_audio_b64, audio_path, user_transcript)

            finally:
                self.is_processing = False

    async def _generate_response_with_audio(self, user_audio_b64: str, audio_path: str, user_transcript: str = "") -> None:
        """Generate interviewer response with user audio input using Qwen-Omni"""
        record = self.state_machine.record

        # 【关键】检查面试是否已经结束，如果结束了就不再生成回复
        if record.status == InterviewRecordStatus.COMPLETED:
            print("[Phase] Interview already completed, ignoring new input")
            return

        # 【关键修复】先保存上一轮对话，这样才能正确判断是否需要推进阶段
        pending_interviewer_text = getattr(self, "_pending_interviewer_text", "")
        candidate_text = user_transcript if user_transcript else "[用户语音输入]"

        if pending_interviewer_text:
            # 保存上一轮的对话到 dialogues
            self.state_machine.record.add_dialogue(
                role="interviewer",
                content=pending_interviewer_text
            )
            self.state_machine.record.add_dialogue(
                role="candidate",
                content=candidate_text,
                audio_path=audio_path  # 保存用户音频路径
            )
            # 推进轮次，检查是否需要切换阶段
            max_reached = self.state_machine.record.advance_round()
            if max_reached:
                continued = self.state_machine.record.advance_phase("max_rounds_reached")
                if continued:
                    print(f"[Phase] Advanced to: {self.state_machine.record.current_phase.value}")
                    # 【关键】通知前端阶段变化
                    await self._send_phase_start()
                # 【关键修复】如果面试结束，立即调用结束逻辑并返回
                else:
                    print("[Phase] Interview completed - all phases done, ending interview...")
                    await self._end_interview()
                    return  # 不再继续生成面试官回复
            else:
                # 【关键修复】轮次增加但阶段未变，也要通知前端更新进度
                await self._send_round_update()

            # 清空 pending，避免重复保存
            self._pending_interviewer_text = ""

        # 现在获取正确的阶段信息
        phase = record.current_phase
        round_number = record.current_round
        print(f"[Phase] Current: {phase.value}, Round: {round_number}")

        # Build conversation history (previous dialogues as text)
        messages = []
        for d in record.dialogues:
            messages.append({
                "role": "assistant" if d.role.value == "interviewer" else "user",
                "content": d.content
            })

        print(f"[Context] Total messages: {len(messages)}")

        # Check if can advance early
        can_advance = self.state_machine.can_advance_early()

        # Build system prompt with CORRECT phase
        system_prompt = self._build_interviewer_prompt(phase, round_number, can_advance)

        # Set status to speaking
        await self._send_message({
            "type": "status",
            "status": "speaking"
        })

        try:
            # Stream response with text and audio from Qwen-Omni
            full_text = ""
            audio_chunks_count = 0
            total_audio_size = 0

            async for text_chunk, audio_chunk in self.omni_client.generate_with_audio_input(
                system_prompt=system_prompt,
                messages=messages,
                user_audio_b64=user_audio_b64,
                audio_format="mp3"
            ):
                # Send text chunk (filter out advance markers before sending)
                if text_chunk:
                    full_text += text_chunk
                    # 过滤掉 [ADVANCE] 等标记后再发送给前端
                    display_chunk = text_chunk
                    for marker in ["[ADVANCE]", "[ADVANCE_PHASE]", "【ADVANCE】", "[advance]"]:
                        display_chunk = display_chunk.replace(marker, "")
                    if display_chunk.strip():
                        await self._send_message({
                            "type": "response_text",
                            "text": display_chunk
                        })

                # Send audio chunk
                if audio_chunk:
                    audio_chunks_count += 1
                    total_audio_size += len(audio_chunk)
                    await self._send_message({
                        "type": "audio",
                        "audio": audio_chunk
                    })

            print(f"[Omni] Audio response: {audio_chunks_count} chunks, ~{total_audio_size} bytes")

            # Check for advance signal in the response
            full_text, should_advance = self.interviewer.check_advance_signal(full_text)

            print(f"[Omni] Interviewer response: {full_text[:100]}...")

            # Signal that audio stream is complete
            await self._send_message({
                "type": "audio_complete"
            })

            # 保存新响应供下一轮使用（对话已在函数开始时保存）
            self._pending_interviewer_text = full_text
            self._should_advance = should_advance

            # 保存记录
            self.storage.save_record(self.state_machine.record)

            # 广播给 HR
            await self._broadcast_to_hr({
                "type": "dialogue",
                "session_id": self.session_id,
                "interviewer": full_text[:200],
                "candidate": user_transcript or "[语音]",
                "phase": self.state_machine.record.current_phase.value,
                "round": self.state_machine.record.current_round
            })

        except Exception as e:
            print(f"[Omni Error] {e}")
            import traceback
            traceback.print_exc()
            await self._send_message({
                "type": "error",
                "message": f"Response generation failed: {str(e)}"
            })
            await self._send_message({
                "type": "status",
                "status": "listening"
            })

    async def _process_turn_with_audio(self, candidate_text: str, candidate_audio: str, interviewer_text: str = "") -> None:
        """Process a complete dialogue turn with audio input"""
        # Use provided interviewer text or fallback to pending
        if not interviewer_text:
            interviewer_text = getattr(self, "_pending_interviewer_text", "")
        should_advance = getattr(self, "_should_advance", False)

        # Calculate audio durations (approximate)
        candidate_duration = 5.0  # Approximate since we have audio
        interviewer_duration = len(interviewer_text) * 0.1

        # Process turn in state machine
        result = self.state_machine.process_turn(
            interviewer_text=interviewer_text,
            candidate_text=candidate_text,
            interviewer_audio=None,
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
            # Don't generate another response - we just sent one

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
        phase = record.current_phase.value  # Include phase to avoid filename collision

        # Convert PCM to WAV
        wav_data = self._pcm_to_wav(audio_data)

        # Save with phase in filename
        audio_path = self.storage.save_audio(
            session_id=self.session_id,
            round_number=round_number,
            role=role,
            audio_data=wav_data,
            format="wav",
            phase=phase
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
        record = self.state_machine.record

        # 【关键】立即设置状态为已完成，防止继续对话
        record.status = InterviewRecordStatus.COMPLETED
        record.completed_at = datetime.now()
        print(f"[Phase] Interview status set to COMPLETED")

        # 【关键】同步更新主面试系统状态（使用token查找）
        try:
            interview_service = InterviewService()
            result = interview_service.update_status_by_token(self.session_id, InterviewStatus.COMPLETED)
            if result:
                print(f"[Phase] Main interview system status updated to COMPLETED")
            else:
                print(f"[Phase] Failed to find interview by token: {self.session_id}")
        except Exception as e:
            print(f"[Phase] Failed to update main interview system: {e}")

        await self._send_message({
            "type": "status",
            "status": "evaluating"
        })

        # Generate evaluation
        try:
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
                        "type": "response_text",
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
        async with active_sessions_lock:
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
        # Wait for init message with timeout
        try:
            init_data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
        except asyncio.TimeoutError:
            await websocket.send_json({
                "type": "error",
                "message": "Timeout waiting for init message"
            })
            await websocket.close()
            return

        try:
            init_msg = json.loads(init_data)
        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid JSON format"
            })
            await websocket.close()
            return

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
        position_name = init_msg.get("position_name", "")
        written_test_summary = init_msg.get("written_test_summary", "")

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
            job_info=job_info,
            position_name=position_name,
            written_test_summary=written_test_summary
        )

        # Register session
        async with active_sessions_lock:
            active_sessions[session_id] = session

        # Start interview
        await session.start()

        # Message loop
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300)
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Timeout waiting for message"
                })
                break

            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                continue

            msg_type = msg.get("type")

            if msg_type == "audio":
                audio_b64 = msg.get("audio", "")
                await session.handle_audio(audio_b64)

            elif msg_type == "commit":
                await session.handle_commit()

            elif msg_type == "stop":
                # User requested to stop interview
                await session._end_interview()
                break

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
    async with active_sessions_lock:
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
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300)
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Timeout waiting for message"
                })
                break

            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                continue

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
    async with active_sessions_lock:
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
