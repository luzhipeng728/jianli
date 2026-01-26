"""API限流中间件 - 基于Redis的滑动窗口限流"""
import time
from typing import Optional, Callable
from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as aioredis
from app.config import get_settings


class RateLimiter:
    """Redis滑动窗口限流器"""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None

    async def get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int
    ) -> tuple[bool, int, int]:
        """检查请求是否允许

        Args:
            key: 限流键（如 ip:xxx 或 user:xxx）
            limit: 窗口内最大请求数
            window: 窗口大小（秒）

        Returns:
            (是否允许, 剩余次数, 重置时间戳)
        """
        redis = await self.get_redis()
        now = time.time()
        window_start = now - window

        # 使用有序集合实现滑动窗口
        pipe = redis.pipeline()

        # 移除窗口外的请求
        pipe.zremrangebyscore(key, 0, window_start)
        # 获取当前窗口内的请求数
        pipe.zcard(key)
        # 添加当前请求
        pipe.zadd(key, {str(now): now})
        # 设置过期时间
        pipe.expire(key, window)

        results = await pipe.execute()
        current_count = results[1]

        remaining = max(0, limit - current_count - 1)
        reset_time = int(now + window)

        if current_count >= limit:
            return False, 0, reset_time

        return True, remaining, reset_time

    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None


# 限流配置
RATE_LIMITS = {
    # 路径: (限制次数, 时间窗口秒)
    "/api/resume/upload": (10, 60),       # 上传：每分钟10次
    "/api/resume/upload-stream": (10, 60),
    "/api/batch/upload": (5, 60),         # 批量上传：每分钟5次
    "/api/batch/process": (5, 60),
    "/api/chat/message": (30, 60),        # 聊天：每分钟30次
    "/api/auth/login": (5, 60),           # 登录：每分钟5次
    "default": (100, 60),                 # 默认：每分钟100次
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        settings = get_settings()
        self.limiter = RateLimiter(f"redis://{settings.redis_host}:{settings.redis_port}")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)

        # 获取客户端IP
        client_ip = request.client.host if request.client else "unknown"

        # 对于认证用户，使用user_id作为限流key
        # 这里简单使用IP，生产环境可以从token中获取user_id
        rate_key = f"rate:{client_ip}"

        # 获取路径对应的限流配置
        path = request.url.path
        limit_config = RATE_LIMITS.get(path)

        # 检查前缀匹配
        if not limit_config:
            for pattern, config in RATE_LIMITS.items():
                if pattern != "default" and path.startswith(pattern):
                    limit_config = config
                    break

        if not limit_config:
            limit_config = RATE_LIMITS["default"]

        limit, window = limit_config

        try:
            allowed, remaining, reset_time = await self.limiter.is_allowed(
                f"{rate_key}:{path}",
                limit,
                window
            )
        except Exception as e:
            # Redis连接失败时不阻止请求
            print(f"Rate limit error: {e}")
            return await call_next(request)

        # 添加限流响应头
        response = await call_next(request) if allowed else Response(
            content='{"detail": "请求过于频繁，请稍后再试"}',
            status_code=429,
            media_type="application/json"
        )

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


def rate_limit(limit: int = 10, window: int = 60):
    """路由级别的限流装饰器

    用法:
    @router.post("/endpoint")
    @rate_limit(limit=5, window=60)
    async def endpoint():
        pass
    """
    def decorator(func: Callable) -> Callable:
        # 存储限流配置，供中间件使用
        func._rate_limit = (limit, window)
        return func
    return decorator
