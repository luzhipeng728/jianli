"""认证API"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.api.middleware.auth import (
    authenticate_user,
    create_access_token,
    require_auth,
    User
)

router = APIRouter(prefix="/api/auth", tags=["认证"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserInfoResponse(BaseModel):
    user_id: str
    username: str
    role: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """用户登录

    POC测试账号:
    - admin / admin123 (管理员)
    - user / user123 (普通用户)
    """
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(401, "用户名或密码错误")

    token = create_access_token(user["user_id"], user["role"])

    return LoginResponse(
        access_token=token,
        user={
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"]
        }
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(user: User = Depends(require_auth)):
    """获取当前用户信息"""
    return UserInfoResponse(
        user_id=user.user_id,
        username=user.username,
        role=user.role
    )


@router.post("/refresh")
async def refresh_token(user: User = Depends(require_auth)):
    """刷新令牌"""
    new_token = create_access_token(user.user_id, user.role)
    return {"access_token": new_token, "token_type": "bearer"}
