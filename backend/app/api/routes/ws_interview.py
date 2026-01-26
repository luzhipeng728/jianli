"""WebSocket 语音面试路由"""
import json
import asyncio
import base64
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException
from app.services.interview_service import InterviewService
from app.services.interview_state import get_interview_state_manager
from app.services.voice_service import get_voice_service, ASRResult
from app.models.ws_messages import ClientMessage, ServerMessage

router = APIRouter()

# 全局连接管理器
class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}  # token -> websocket
        self.heartbeat_tasks: dict[str, asyncio.Task] = {}  # token -> heartbeat task
        self.audio_buffers: dict[str, list[bytes]] = {}  # token -> audio chunks

    async def connect(self, token: str, websocket: WebSocket):
        """接受新连接"""
        await websocket.accept()
        self.active_connections[token] = websocket
        self.audio_buffers[token] = []  # 初始化音频缓冲
        # 启动心跳任务
        self.heartbeat_tasks[token] = asyncio.create_task(
            self._heartbeat_loop(token, websocket)
        )

    def disconnect(self, token: str):
        """断开连接"""
        # 取消心跳任务
        if token in self.heartbeat_tasks:
            self.heartbeat_tasks[token].cancel()
            del self.heartbeat_tasks[token]

        # 移除连接
        if token in self.active_connections:
            del self.active_connections[token]

        # 清理音频缓冲
        if token in self.audio_buffers:
            del self.audio_buffers[token]

    def add_audio_chunk(self, token: str, audio_bytes: bytes):
        """添加音频块到缓冲"""
        if token in self.audio_buffers:
            self.audio_buffers[token].append(audio_bytes)

    def get_and_clear_audio(self, token: str) -> bytes:
        """获取并清空音频缓冲"""
        if token in self.audio_buffers:
            chunks = self.audio_buffers[token]
            self.audio_buffers[token] = []
            return b''.join(chunks)
        return b''

    async def send_message(self, token: str, message: dict):
        """发送消息到客户端"""
        if token in self.active_connections:
            try:
                await self.active_connections[token].send_json(message)
            except Exception as e:
                print(f"[WebSocket] Failed to send message to {token}: {e}")
                self.disconnect(token)

    async def _heartbeat_loop(self, token: str, websocket: WebSocket):
        """心跳循环 - 每30秒发送一次ping"""
        try:
            while True:
                await asyncio.sleep(30)
                if token in self.active_connections:
                    try:
                        # 发送心跳消息
                        await websocket.send_json({"type": "ping"})
                    except Exception:
                        # 心跳失败，断开连接
                        self.disconnect(token)
                        break
                else:
                    break
        except asyncio.CancelledError:
            # 任务被取消，正常退出
            pass

# 全局连接管理器实例
manager = ConnectionManager()

# 面试服务实例
interview_service = InterviewService()


@router.websocket("/ws/interview/{token}")
async def interview_websocket(websocket: WebSocket, token: str):
    """
    语音面试 WebSocket 端点

    客户端消息格式:
    - {"type": "audio", "audio": "base64_data"}  # 发送音频
    - {"type": "control", "action": "start"}     # 开始面试
    - {"type": "control", "action": "stop"}      # 停止面试
    - {"type": "control", "action": "pause"}     # 暂停
    - {"type": "control", "action": "resume"}    # 恢复
    - {"type": "ping"}                           # 心跳响应

    服务器消息格式:
    - {"type": "transcript", "text": "...", "is_final": true}  # ASR转录结果
    - {"type": "audio", "audio": "base64_data"}                # TTS音频
    - {"type": "status", "status": "listening|processing|speaking|stopped"}
    - {"type": "question", "text": "..."}                      # 面试官问题
    - {"type": "end", "reason": "...", "evaluation_ready": true}
    - {"type": "error", "message": "..."}
    - {"type": "pong"}                                         # 心跳响应
    """

    # 1. 验证 token
    session = interview_service.get_by_token(token)
    if not session:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # 2. 检查面试状态
    if session.status not in ["voice", "written_test", "pending"]:
        await websocket.close(code=4002, reason="Interview not in progress")
        return

    # 3. 建立连接
    await manager.connect(token, websocket)

    # 4. 获取状态管理器
    state_manager = get_interview_state_manager()
    session_id = session.id

    # 5. 初始化面试会话（如果不存在）
    context = await state_manager.get_session(session_id)
    if not context:
        try:
            await state_manager.create_session(
                session_id=session_id,
                candidate_id=session.resume_id,
                resume_id=session.resume_id,
                job_position=getattr(session, "position", "未指定职位"),
                config={}
            )
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "message": f"Failed to initialize session: {str(e)}"
            })
            manager.disconnect(token)
            return

    # 6. 发送欢迎消息
    await websocket.send_json({
        "type": "status",
        "status": "connected"
    })

    try:
        # 7. 消息处理循环
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)

                # 验证消息格式
                try:
                    client_msg = ClientMessage(**message_data)
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Invalid message format: {str(e)}"
                    })
                    continue

                # 处理不同类型的消息
                if client_msg.type == "audio":
                    # 处理音频数据
                    await handle_audio_message(
                        websocket, token, session_id, client_msg, state_manager
                    )

                elif client_msg.type == "control":
                    # 处理控制指令
                    await handle_control_message(
                        websocket, token, session_id, client_msg, state_manager
                    )

                elif client_msg.type == "audio_end":
                    # 音频结束信号 - 处理累积的音频数据
                    await handle_audio_end(
                        websocket, token, session_id, state_manager
                    )

                elif client_msg.type == "ping":
                    # 响应心跳
                    await websocket.send_json({"type": "pong"})

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Error processing message: {str(e)}"
                })

    except WebSocketDisconnect:
        # 正常断开
        print(f"[WebSocket] Client {token} disconnected")
    except Exception as e:
        # 异常断开
        print(f"[WebSocket] Error for client {token}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass
    finally:
        # 清理连接
        manager.disconnect(token)


async def generate_interviewer_response(
    session_id: str,
    candidate_message: str,
    context: dict,
    state_manager
) -> str:
    """生成面试官回复

    Args:
        session_id: 会话ID
        candidate_message: 候选人的回答
        context: 会话上下文
        state_manager: 状态管理器

    Returns:
        面试官的回复文本

    TODO: 集成完整的面试官 Agent 逻辑，包括：
    - 根据简历内容提问
    - 评估候选人回答
    - 根据对话历史动态调整问题
    - 多轮面试流程控制
    """
    from app.services.llm_client import LLMClient

    # 获取对话历史
    conversation_history = context.get("conversation_history", [])

    # 构建对话上下文
    messages = []

    # 系统提示
    system_prompt = """你是一位专业的技术面试官。你的职责是：
1. 根据候选人的简历背景，提出针对性的技术问题
2. 评估候选人的回答质量和技术深度
3. 引导面试流程，逐步深入考察候选人的能力
4. 保持专业、友好的面试氛围

请根据对话历史，给出下一个面试问题或回应。每次只问一个问题，问题要简洁明确。"""

    messages.append({"role": "system", "content": system_prompt})

    # 添加历史对话
    for conv in conversation_history[-10:]:  # 只保留最近10轮对话
        role = "assistant" if conv["role"] == "interviewer" else "user"
        messages.append({"role": role, "content": conv["content"]})

    # 添加当前候选人回答
    messages.append({"role": "user", "content": candidate_message})

    # 调用 LLM 生成回复
    llm_client = LLMClient()
    try:
        response = await llm_client.chat_async(messages, temperature=0.8)
        return response if response else "感谢你的回答。请继续。"
    except Exception as e:
        print(f"[Interviewer] LLM error: {e}")
        # 使用默认回复
        return "非常好。让我们继续下一个问题。"


async def handle_audio_message(
    websocket: WebSocket,
    token: str,
    session_id: str,
    message: ClientMessage,
    state_manager
):
    """处理音频消息 - 缓冲音频数据，等待 audio_end 信号后处理"""
    if not message.audio:
        return  # 静默忽略空音频

    try:
        # 解码并缓冲音频数据
        audio_bytes = base64.b64decode(message.audio)
        manager.add_audio_chunk(token, audio_bytes)
    except Exception as e:
        print(f"[Audio] Error buffering audio: {e}")


async def handle_audio_end(
    websocket: WebSocket,
    token: str,
    session_id: str,
    state_manager
):
    """处理音频结束信号 - 处理累积的音频数据进行 ASR 和生成回复"""
    # 设置状态为处理中
    await websocket.send_json({
        "type": "status",
        "status": "processing"
    })

    try:
        # 1. 获取累积的音频数据
        audio_bytes = manager.get_and_clear_audio(token)

        if not audio_bytes:
            await websocket.send_json({
                "type": "status",
                "status": "listening"
            })
            return

        # 2. 使用阿里云 ASR 进行语音识别
        voice_service = get_voice_service()

        # 创建音频流生成器
        async def audio_stream_generator():
            """生成音频流"""
            yield audio_bytes

        # 执行 ASR，获取转录结果
        final_transcript = ""
        async for result in voice_service.speech_to_text_stream(audio_stream_generator()):
            # 发送实时转录结果
            await websocket.send_json({
                "type": "transcript",
                "text": result.text,
                "is_final": result.is_final
            })

            # 保存完整转录文本
            if result.is_final:
                final_transcript = result.text

        # 如果没有识别到有效文本，提示用户
        if not final_transcript or not final_transcript.strip():
            await websocket.send_json({
                "type": "status",
                "status": "listening"
            })
            return

        # 3. 将转录文本记录到会话历史
        await state_manager.add_conversation(
            session_id,
            role="candidate",
            content=final_transcript
        )

        # 4. 调用面试官 Agent 生成回复
        context = await state_manager.get_session(session_id)
        interviewer_response = await generate_interviewer_response(
            session_id, final_transcript, context, state_manager
        )

        # 5. 发送问题文本
        await websocket.send_json({
            "type": "question",
            "text": interviewer_response
        })

        # 记录面试官回复
        await state_manager.add_conversation(
            session_id,
            role="interviewer",
            content=interviewer_response
        )

        # 6. 使用阿里云 TTS 生成语音
        await websocket.send_json({
            "type": "status",
            "status": "speaking"
        })

        # 流式发送 TTS 音频
        async for audio_b64 in voice_service.text_to_speech_base64(
            interviewer_response,
            voice="zhitian_emo",
            language="Chinese"
        ):
            await websocket.send_json({
                "type": "audio",
                "audio": audio_b64
            })

        # 7. 恢复为监听状态
        await websocket.send_json({
            "type": "status",
            "status": "listening"
        })

    except Exception as e:
        # 发送错误消息
        await websocket.send_json({
            "type": "error",
            "message": f"Error processing audio: {str(e)}"
        })

        # 恢复为监听状态
        await websocket.send_json({
            "type": "status",
            "status": "listening"
        })


async def handle_control_message(
    websocket: WebSocket,
    token: str,
    session_id: str,
    message: ClientMessage,
    state_manager
):
    """处理控制消息"""
    action = message.action

    if action == "start":
        # 开始面试
        welcome_text = "你好，欢迎参加本次面试。请先简单介绍一下你自己。"

        # 发送第一个问题（文本）
        await websocket.send_json({
            "type": "question",
            "text": welcome_text
        })

        # 记录到会话历史
        await state_manager.add_conversation(
            session_id,
            role="interviewer",
            content=welcome_text
        )

        # 发送 TTS 语音
        await websocket.send_json({
            "type": "status",
            "status": "speaking"
        })

        voice_service = get_voice_service()
        try:
            async for audio_b64 in voice_service.text_to_speech_base64(
                welcome_text,
                voice="zhitian_emo",
                language="Chinese"
            ):
                await websocket.send_json({
                    "type": "audio",
                    "audio": audio_b64
                })
        except Exception as e:
            print(f"[TTS] Error generating welcome audio: {e}")

        # 切换到监听状态
        await websocket.send_json({
            "type": "status",
            "status": "listening"
        })

    elif action == "stop":
        # 停止面试
        await websocket.send_json({
            "type": "status",
            "status": "stopped"
        })

        await websocket.send_json({
            "type": "end",
            "reason": "User stopped the interview",
            "evaluation_ready": False
        })

        # 更新会话状态
        await state_manager.update_session(
            session_id,
            {"end_time": None}
        )

    elif action == "pause":
        # 暂停面试
        await websocket.send_json({
            "type": "status",
            "status": "paused"
        })

    elif action == "resume":
        # 恢复面试
        await websocket.send_json({
            "type": "status",
            "status": "listening"
        })

    else:
        await websocket.send_json({
            "type": "error",
            "message": f"Unknown action: {action}"
        })


@router.get("/ws/interview/{token}/status")
async def get_interview_status(token: str):
    """获取面试会话状态 (HTTP接口，用于检查连接)"""
    session = interview_service.get_by_token(token)
    if not session:
        return {"error": "Invalid token"}, 404

    is_connected = token in manager.active_connections

    return {
        "session_id": session.id,
        "status": session.status,
        "connected": is_connected
    }
