"""语音面试 WebSocket 路由 (ASR + Qwen-Omni + TTS 架构)

使用 Paraformer ASR (显示文字) + Qwen-Omni (直接理解音频) + CosyVoice TTS 实现语音面试。
没有60秒限制，支持长时间对话。

Qwen-Omni 直接理解音频，效果比 ASR+LLM 更好。
ASR 仅用于前端实时显示用户说的文字。
"""

import json
import asyncio
import base64
import io
import wave
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.asr_service import ParaformerASRSession
from app.services.tts_service import CosyVoiceTTSSession
from app.services.omni_http_client import QwenOmniClient, get_omni_client
from app.services.interview_service import InterviewService
from app.services.jd_service import JDService
from app.services.resume_parser import ResumeParser
from app.agents.controller_agent import ControllerAgent

router = APIRouter()

# 服务实例
interview_service = InterviewService()
jd_service = JDService()
resume_parser = ResumeParser()


def build_resume_summary(resume) -> str:
    """从简历数据构建面试官需要的摘要"""
    if not resume:
        return "候选人简历信息暂不可用"

    parts = []

    if resume.basic_info:
        info = resume.basic_info
        basic = []
        if info.name:
            basic.append(f"姓名: {info.name}")
        if info.age:
            basic.append(f"年龄: {info.age}岁")
        if basic:
            parts.append("【基本信息】" + ", ".join(basic))

    if resume.education:
        edu_list = []
        for edu in resume.education[:2]:
            edu_str = f"{edu.school}"
            if edu.degree:
                edu_str += f" {edu.degree}"
            if edu.major:
                edu_str += f" {edu.major}"
            edu_list.append(edu_str)
        if edu_list:
            parts.append("【教育背景】" + "; ".join(edu_list))

    if resume.experience:
        exp_list = []
        for exp in resume.experience[:3]:
            exp_str = f"{exp.company} - {exp.title}"
            if exp.start_date and exp.end_date:
                exp_str += f" ({exp.start_date}至{exp.end_date})"
            if exp.duties:
                duties_short = exp.duties[:100] + "..." if len(exp.duties) > 100 else exp.duties
                exp_str += f": {duties_short}"
            exp_list.append(exp_str)
        if exp_list:
            parts.append("【工作经历】\n" + "\n".join(exp_list))

    if resume.skills:
        skills = []
        if resume.skills.hard_skills:
            skills.extend(resume.skills.hard_skills[:10])
        if skills:
            parts.append("【技术技能】" + ", ".join(skills))

    return "\n\n".join(parts) if parts else "候选人简历信息暂不可用"


def build_job_info(jd) -> str:
    """从JD数据构建岗位信息"""
    if not jd:
        return "岗位信息暂不可用"

    parts = [f"职位: {jd.title}"]

    if jd.department:
        parts.append(f"部门: {jd.department}")

    if jd.requirements:
        parts.append(f"要求: {jd.requirements[:500]}")

    if jd.required_skills:
        parts.append(f"技能要求: {', '.join(jd.required_skills[:10])}")

    return "\n".join(parts)


class VoiceInterviewSession:
    """语音面试会话 (ASR + Qwen-Omni + TTS)

    ASR 用于前端实时显示文字，Qwen-Omni 直接理解音频。
    """

    def __init__(
        self,
        token: str,
        websocket: WebSocket,
        session_id: str,
        resume_summary: str,
        job_info: str,
        jd=None,
    ):
        self.token = token
        self.websocket = websocket
        self.session_id = session_id
        self.resume_summary = resume_summary
        self.job_info = job_info
        self.jd = jd

        # ASR 会话 (仅用于显示文字)
        self.asr_session: Optional[ParaformerASRSession] = None

        # TTS 会话
        self.tts_session: Optional[CosyVoiceTTSSession] = None

        # Qwen-Omni 客户端 (直接理解音频)
        self.omni_client = get_omni_client()

        # 控场智能体
        self.controller: Optional[ControllerAgent] = None

        # 对话历史
        self.conversation_history: List[dict] = []

        # 当前转录文本 (ASR 用于显示)
        self.current_transcript = ""

        # 音频缓冲区 (收集用户说话的音频)
        self.audio_buffer: List[bytes] = []

        # 状态
        self.is_active = False
        self.is_speaking = False  # AI 是否正在说话

        # 音频计数
        self._audio_count = 0

    def _build_system_prompt(self) -> str:
        """构建面试官系统提示词"""
        return f"""你是一位专业的技术面试官。

## 语言要求【重要】
- 必须全程使用中文进行面试
- 使用自然的中文口语表达
- 回复要简洁，适合语音播放

## 你的角色
- 你正在进行一场语音面试
- 保持专业、友好、有耐心
- 每次只问一个问题，等待候选人回答
- 回复尽量简短，不要超过3句话

## 职位信息
{self.job_info}

## 候选人背景
{self.resume_summary}

## 面试流程
1. 首先问候候选人，请他做自我介绍
2. 根据简历背景提出针对性的技术问题
3. 深入追问以评估技术深度
4. 适时进行行为面试
5. 给候选人提问机会

## 注意事项
- 回复要简洁，适合语音播放
- 保持对话流畅自然
- 全程只用中文！
"""

    async def start(self) -> bool:
        """启动面试会话"""
        try:
            print(f"[VoiceInterview] Starting session {self.session_id}")

            # 创建 ASR 会话
            self.asr_session = ParaformerASRSession(
                on_transcript=self._on_transcript,
                on_error=self._on_asr_error,
            )

            if not await self.asr_session.connect():
                print(f"[VoiceInterview] ASR connection failed")
                return False

            print(f"[VoiceInterview] ASR connected")

            # 创建控场智能体
            self.controller = ControllerAgent(session_id=self.session_id)
            self.controller.start_time = datetime.now()

            self.is_active = True

            # 发送欢迎消息
            await self._send_welcome()

            return True

        except Exception as e:
            print(f"[VoiceInterview] Start error: {e}")
            import traceback
            traceback.print_exc()
            await self._send_error(str(e))
            return False

    async def _send_welcome(self):
        """发送欢迎语音"""
        welcome_text = "你好，我是今天的面试官。很高兴见到你。请先简单做个自我介绍吧。"

        # 添加到对话历史
        self.conversation_history.append({
            "role": "assistant",
            "content": welcome_text
        })

        # 发送状态
        await self._send_status("speaking")

        # 发送文本给前端显示
        try:
            await self.websocket.send_json({
                "type": "response_text",
                "text": welcome_text
            })
        except Exception as e:
            print(f"[VoiceInterview] Send welcome text error: {e}")

        # 使用 TTS 合成语音
        await self._synthesize_and_send(welcome_text)

        # 发送状态
        await self._send_status("listening")

    def _on_transcript(self, text: str, is_final: bool):
        """ASR 转录回调"""
        asyncio.create_task(self._async_on_transcript(text, is_final))

    async def _async_on_transcript(self, text: str, is_final: bool):
        """异步处理转录结果"""
        if not self.is_active or self.is_speaking:
            return

        self.current_transcript = text

        # 发送转录给前端
        try:
            await self.websocket.send_json({
                "type": "transcript",
                "text": text,
                "is_final": is_final
            })
        except:
            pass

    def _on_asr_error(self, error: str):
        """ASR 错误回调"""
        asyncio.create_task(self._send_error(f"语音识别错误: {error}"))

    async def handle_audio(self, audio_b64: str):
        """处理前端发来的音频

        1. 发送给 ASR 用于实时显示文字
        2. 收集到缓冲区供 Qwen-Omni 使用
        """
        if not self.is_active or self.is_speaking:
            return

        try:
            audio_bytes = base64.b64decode(audio_b64)

            self._audio_count += 1
            if self._audio_count % 100 == 1:
                print(f"[VoiceInterview] Audio frame #{self._audio_count}: {len(audio_bytes)} bytes")

            # 发送给 ASR (实时显示文字)
            if self.asr_session:
                await self.asr_session.send_audio(audio_bytes)

            # 收集到缓冲区 (供 Qwen-Omni 使用)
            self.audio_buffer.append(audio_bytes)

        except Exception as e:
            print(f"[VoiceInterview] Audio error: {e}")

    def _pcm_to_wav(self, pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
        """将 PCM 数据转换为 WAV 格式"""
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
        return wav_buffer.getvalue()

    async def handle_commit(self):
        """处理用户提交（说完了）- Qwen-Omni 直接理解音频 + TTS"""
        if not self.is_active or self.is_speaking:
            return

        # 检查是否有音频数据
        if not self.audio_buffer:
            print(f"[VoiceInterview] No audio data collected")
            return

        # 合并音频数据
        audio_data = b''.join(self.audio_buffer)
        audio_duration = len(audio_data) / (16000 * 2)  # 16kHz, 16bit
        print(f"[VoiceInterview] User committed, audio: {len(audio_data)} bytes ({audio_duration:.1f}s), transcript: {self.current_transcript[:50] if self.current_transcript else '(empty)'}...")

        # 清空缓冲区
        self.audio_buffer = []

        # 转换为 WAV 格式
        wav_data = self._pcm_to_wav(audio_data)
        print(f"[VoiceInterview] Converted to WAV: {len(wav_data)} bytes")

        # 保存用户输入文字（ASR 结果，用于显示）
        user_text = self.current_transcript
        self.current_transcript = ""

        # 添加到对话历史（文字版本）
        if user_text:
            self.conversation_history.append({
                "role": "user",
                "content": user_text
            })

        # 发送最终转录
        await self.websocket.send_json({
            "type": "transcript",
            "text": user_text or "(语音输入)",
            "is_final": True
        })

        # 更新状态
        await self._send_status("processing")

        # 重新连接 ASR（清空缓冲区）
        await self._reconnect_asr()

        # 使用 Qwen-Omni 直接理解音频并流式回复
        await self._stream_response_with_audio(wav_data)

        # 更新状态
        await self._send_status("listening")

    async def _stream_response(self, user_text: str):
        """流式生成回复：LLM 流式输出 -> 前端文本 + TTS 流式合成 -> 前端音频"""
        self.is_speaking = True

        try:
            # 先调用控场智能体
            directive = ""
            if self.controller and self.jd:
                try:
                    decision = await self.controller.analyze(
                        jd=self.jd,
                        conversation_history=self.conversation_history
                    )
                    if decision.should_guide:
                        directive = decision.directive
                    if decision.should_end:
                        # 结束面试
                        end_msg = f"好的，今天的面试就到这里。{decision.end_reason}。感谢你的时间，我们会尽快联系你。"
                        await self._send_text_and_audio(end_msg)
                        return
                except Exception as e:
                    print(f"[VoiceInterview] Controller error: {e}")

            # 构建消息
            system_prompt = self._build_system_prompt()
            if directive:
                system_prompt += f"\n\n## 当前控场指令\n{directive}"

            messages = [{"role": "system", "content": system_prompt}]
            for msg in self.conversation_history[-20:]:
                messages.append({
                    "role": msg["role"] if msg["role"] != "candidate" else "user",
                    "content": msg["content"]
                })

            # 更新状态
            await self._send_status("speaking")

            # 创建 TTS 会话
            audio_queue = asyncio.Queue()
            tts_complete = asyncio.Event()

            def on_audio(data: bytes):
                audio_queue.put_nowait(data)

            def on_tts_complete():
                tts_complete.set()

            self.tts_session = CosyVoiceTTSSession(
                voice="longxiaochun",
                sample_rate=24000,
                on_audio=on_audio,
                on_complete=on_tts_complete,
            )

            if not await self.tts_session.connect():
                print(f"[VoiceInterview] TTS connection failed")
                self.is_speaking = False
                return

            # 启动音频发送任务
            audio_send_task = asyncio.create_task(
                self._send_audio_stream(audio_queue, tts_complete)
            )

            # 流式获取 LLM 回复并发送给 TTS
            full_response = ""
            text_buffer = ""
            MIN_TTS_CHUNK = 10  # 最小 TTS 文本块（避免太短的片段）

            async for chunk in self.llm_client.chat_stream_messages(messages):
                if not self.is_active:
                    break

                full_response += chunk
                text_buffer += chunk

                # 发送文本给前端（流式）
                try:
                    await self.websocket.send_json({
                        "type": "response_text",
                        "text": chunk
                    })
                except:
                    pass

                # 当累积足够文本或遇到句子结束符时，发送给 TTS
                if len(text_buffer) >= MIN_TTS_CHUNK or any(p in text_buffer for p in ['。', '！', '？', '，', '；', '.', '!', '?', ',']):
                    if text_buffer.strip():
                        await self.tts_session.synthesize(text_buffer)
                    text_buffer = ""

            # 发送剩余文本给 TTS
            if text_buffer.strip():
                await self.tts_session.synthesize(text_buffer)

            # 结束 TTS
            await self.tts_session.finish()

            # 等待音频发送完成
            await audio_send_task

            # 清理 TTS
            await self.tts_session.close()
            self.tts_session = None

            # 添加到对话历史
            if full_response:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": full_response
                })

        except Exception as e:
            print(f"[VoiceInterview] Stream response error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_speaking = False

    async def _stream_response_with_audio(self, audio_data: bytes):
        """使用 Qwen-Omni 直接理解音频并流式回复（文本+音频）

        Qwen-Omni 可以同时输出文本和音频，不需要额外的 TTS！

        Args:
            audio_data: WAV 格式的音频数据
        """
        self.is_speaking = True

        try:
            # 构建系统提示词
            system_prompt = self._build_system_prompt()

            # 构建历史消息（只传文字版本）
            history = []
            for msg in self.conversation_history[-20:]:
                history.append({
                    "role": msg["role"] if msg["role"] != "candidate" else "user",
                    "content": msg["content"]
                })

            # 更新状态
            await self._send_status("speaking")

            # 调用 Qwen-Omni 直接理解音频并生成音频回复（流式）
            full_response = ""

            print(f"[VoiceInterview] Calling Qwen-Omni with audio ({len(audio_data)} bytes), output_audio=True...")

            async for response in self.omni_client.chat_with_audio(
                audio_data=audio_data,
                audio_format="wav",
                system_prompt=system_prompt,
                history=history,
                output_audio=True,  # 直接使用 Qwen-Omni 的音频输出！
            ):
                if response.is_complete:
                    break

                # 发送文本给前端（流式）
                if response.text:
                    full_response += response.text
                    try:
                        await self.websocket.send_json({
                            "type": "response_text",
                            "text": response.text
                        })
                    except:
                        pass

                # 直接发送 Qwen-Omni 生成的音频给前端
                if response.audio_base64:
                    try:
                        await self.websocket.send_json({
                            "type": "audio",
                            "audio": response.audio_base64
                        })
                    except:
                        pass

            print(f"[VoiceInterview] Qwen-Omni response: {full_response[:100]}...")

            # 添加到对话历史
            if full_response:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": full_response
                })

        except Exception as e:
            print(f"[VoiceInterview] Stream response with audio error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_speaking = False

    async def _send_audio_stream(self, audio_queue: asyncio.Queue, complete_event: asyncio.Event):
        """流式发送音频给前端"""
        while not complete_event.is_set() or not audio_queue.empty():
            try:
                audio_data = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                audio_b64 = base64.b64encode(audio_data).decode('ascii')
                await self.websocket.send_json({
                    "type": "audio",
                    "audio": audio_b64
                })
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[VoiceInterview] Send audio error: {e}")
                break

    async def _send_text_and_audio(self, text: str):
        """发送文本和对应的语音（用于简单的单次消息）"""
        # 发送文本
        await self.websocket.send_json({
            "type": "response_text",
            "text": text
        })

        # 合成并发送语音
        await self._synthesize_and_send(text)

    async def _reconnect_asr(self):
        """重新连接 ASR（清空缓冲区）"""
        if self.asr_session:
            await self.asr_session.close()

        self.asr_session = ParaformerASRSession(
            on_transcript=self._on_transcript,
            on_error=self._on_asr_error,
        )
        await self.asr_session.connect()

    async def _synthesize_and_send(self, text: str):
        """合成语音并发送给前端"""
        self.is_speaking = True

        try:
            # 创建 TTS 会话
            audio_queue = asyncio.Queue()
            is_complete = asyncio.Event()

            def on_audio(data: bytes):
                audio_queue.put_nowait(data)

            def on_complete():
                is_complete.set()

            self.tts_session = CosyVoiceTTSSession(
                voice="longxiaochun",  # 温柔女声
                sample_rate=24000,
                on_audio=on_audio,
                on_complete=on_complete,
            )

            if not await self.tts_session.connect():
                print(f"[VoiceInterview] TTS connection failed")
                return

            # 发送文本进行合成
            await self.tts_session.synthesize(text)
            await self.tts_session.finish()

            # 发送音频给前端
            while not is_complete.is_set() or not audio_queue.empty():
                try:
                    audio_data = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                    audio_b64 = base64.b64encode(audio_data).decode('ascii')
                    await self.websocket.send_json({
                        "type": "audio",
                        "audio": audio_b64
                    })
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"[VoiceInterview] Send audio error: {e}")
                    break

            await self.tts_session.close()
            self.tts_session = None

        except Exception as e:
            print(f"[VoiceInterview] TTS error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_speaking = False

    async def _send_status(self, status: str):
        """发送状态给前端"""
        try:
            await self.websocket.send_json({
                "type": "status",
                "status": status
            })
        except:
            pass

    async def _send_error(self, error: str):
        """发送错误给前端"""
        try:
            await self.websocket.send_json({
                "type": "error",
                "message": error
            })
        except:
            pass

    async def close(self):
        """清理资源"""
        self.is_active = False

        if self.asr_session:
            await self.asr_session.close()

        if self.tts_session:
            await self.tts_session.close()

        if self.controller:
            self.controller.stop()


# 活跃会话
active_sessions: dict[str, VoiceInterviewSession] = {}


@router.websocket("/ws/voice-interview/{token}")
async def voice_interview_websocket(websocket: WebSocket, token: str):
    """语音面试 WebSocket 端点 (ASR + LLM + TTS 分离架构)

    使用 Paraformer ASR + Qwen LLM + CosyVoice TTS。
    没有60秒限制，支持长时间对话。

    客户端消息:
    - {"type": "audio", "audio": "base64_data"}  # 音频数据
    - {"type": "control", "action": "commit|stop"}  # 控制指令

    服务器消息:
    - {"type": "transcript", "text": "...", "is_final": bool}
    - {"type": "response_text", "text": "..."}
    - {"type": "audio", "audio": "base64_data"}
    - {"type": "status", "status": "listening|processing|speaking"}
    - {"type": "end", "reason": "..."}
    - {"type": "error", "message": "..."}
    """

    # 1. 验证 token
    session_data = interview_service.get_by_token(token)
    if not session_data:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # 2. 检查状态
    if session_data.status not in ["voice", "pending"]:
        await websocket.close(code=4002, reason="Interview not in voice stage")
        return

    # 3. 接受连接
    await websocket.accept()

    # 4. 准备面试信息
    resume_summary = "候选人简历信息暂不可用"
    job_info = "岗位信息暂不可用"
    jd = None

    if session_data.resume_id:
        try:
            resume = resume_parser.get_resume(session_data.resume_id)
            if resume:
                resume_summary = build_resume_summary(resume)
        except Exception as e:
            print(f"[VoiceInterview] Failed to load resume: {e}")

    if session_data.jd_id:
        try:
            jd = jd_service.get(session_data.jd_id)
            if jd:
                job_info = build_job_info(jd)
        except Exception as e:
            print(f"[VoiceInterview] Failed to load JD: {e}")

    # 5. 创建会话
    session = VoiceInterviewSession(
        token=token,
        websocket=websocket,
        session_id=session_data.id,
        resume_summary=resume_summary,
        job_info=job_info,
        jd=jd,
    )

    active_sessions[token] = session

    try:
        # 6. 启动面试
        if not await session.start():
            await websocket.close(code=4003, reason="Failed to start interview")
            return

        # 7. 消息处理循环
        while session.is_active:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                msg_type = message.get("type", "")

                if msg_type == "audio":
                    audio = message.get("audio", "")
                    if audio:
                        await session.handle_audio(audio)

                elif msg_type == "control":
                    action = message.get("action", "")
                    if action == "commit":
                        await session.handle_commit()
                    elif action == "stop":
                        session.is_active = False
                        await websocket.send_json({
                            "type": "end",
                            "reason": "用户结束面试"
                        })

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })

    except WebSocketDisconnect:
        print(f"[VoiceInterview] Client {token} disconnected")

    except Exception as e:
        print(f"[VoiceInterview] Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await session.close()
        if token in active_sessions:
            del active_sessions[token]
