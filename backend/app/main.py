"""简历解析与问答助手 - 后端应用主模块"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import knowledge, chat, resume, batch, auth, jd, interview, ws_interview, ws_omni_interview, voice_interview, ws_voice_interview, ws_structured_interview
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.config import get_settings
from app.services.background_worker import background_worker
from app.services.redis_client import get_redis_client

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("[App] 正在启动后台任务处理器...")
    await background_worker.start()

    print("[App] 正在初始化 Redis 连接...")
    redis = await get_redis_client()
    print("[App] Redis 连接初始化完成")

    yield

    # 关闭时
    print("[App] 正在停止后台任务处理器...")
    await background_worker.stop()

    print("[App] 正在关闭 Redis 连接...")
    await redis.close()
    print("[App] Redis 连接已关闭")


app = FastAPI(
    title="简历解析与问答助手",
    version="0.1.0",
    lifespan=lifespan,
)

# 限流中间件（生产环境启用）
app.add_middleware(RateLimitMiddleware, enabled=not settings.debug)

# NOTE: POC 临时配置，生产环境需通过环境变量限制允许的源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(auth.router)
app.include_router(knowledge.router)
app.include_router(chat.router)
app.include_router(resume.router)
app.include_router(batch.router)
app.include_router(jd.router)
app.include_router(interview.router)
app.include_router(ws_interview.router)  # WebSocket 语音面试 (旧版)
app.include_router(ws_omni_interview.router)  # Omni Realtime 语音面试 (WebSocket)
app.include_router(voice_interview.router, prefix="/api/voice-interview", tags=["voice-interview"])  # HTTP 语音面试
app.include_router(ws_voice_interview.router)  # ASR+LLM+TTS 分离架构语音面试 (推荐，无60秒限制)
app.include_router(ws_structured_interview.router, tags=["structured-interview"])  # 7-Phase Structured Interview with State Machine


@app.get("/health")
async def health_check() -> dict[str, str]:
    """健康检查端点"""
    return {"status": "ok"}
