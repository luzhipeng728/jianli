"""简历解析与问答助手 - 后端应用主模块"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import knowledge, chat, resume

app = FastAPI(
    title="简历解析与问答助手",
    version="0.1.0",
)

# NOTE: POC 临时配置，生产环境需通过环境变量限制允许的源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(knowledge.router)
app.include_router(chat.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """健康检查端点"""
    return {"status": "ok"}
