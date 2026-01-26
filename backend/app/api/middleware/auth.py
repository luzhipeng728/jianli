"""JWT认证中间件"""
import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.config import get_settings

security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """Token载荷"""
    sub: str  # 用户ID
    exp: datetime
    iat: datetime
    role: str = "user"


class User(BaseModel):
    """用户信息"""
    user_id: str
    username: str
    role: str = "user"


# 模拟用户数据库（POC用，生产环境应使用真实数据库）
MOCK_USERS = {
    "admin": {
        "user_id": "1",
        "username": "admin",
        "password": "admin123",  # 生产环境必须加密
        "role": "admin"
    },
    "user": {
        "user_id": "2",
        "username": "user",
        "password": "user123",
        "role": "user"
    }
}


def create_access_token(user_id: str, role: str = "user", expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_expire_minutes)

    now = datetime.utcnow()
    expire = now + expires_delta

    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "role": role
    }

    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token


def decode_token(token: str) -> Optional[TokenPayload]:
    """解码令牌"""
    settings = get_settings()

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "令牌已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "无效的令牌")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """获取当前用户（可选认证）"""
    if not credentials:
        return None

    token_payload = decode_token(credentials.credentials)

    # 从模拟数据库获取用户
    for username, user_data in MOCK_USERS.items():
        if user_data["user_id"] == token_payload.sub:
            return User(
                user_id=user_data["user_id"],
                username=username,
                role=user_data["role"]
            )

    return None


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> User:
    """强制认证"""
    token_payload = decode_token(credentials.credentials)

    for username, user_data in MOCK_USERS.items():
        if user_data["user_id"] == token_payload.sub:
            return User(
                user_id=user_data["user_id"],
                username=username,
                role=user_data["role"]
            )

    raise HTTPException(401, "用户不存在")


async def require_admin(user: User = Depends(require_auth)) -> User:
    """要求管理员权限"""
    if user.role != "admin":
        raise HTTPException(403, "需要管理员权限")
    return user


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """验证用户"""
    user = MOCK_USERS.get(username)
    if user and user["password"] == password:
        return user
    return None
