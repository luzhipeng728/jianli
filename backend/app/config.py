from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    app_name: str = "简历解析与问答助手"
    debug: bool = False

    # Elasticsearch
    es_host: str = "localhost"
    es_port: int = 9200

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_url: str = "redis://localhost:6379/0"

    # 阿里百炼
    dashscope_api_key: str = ""

    # JWT
    jwt_secret: str = "dev-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 30  # 30天（长期登录，用户不清除token则保持登录状态）

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
