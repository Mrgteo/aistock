"""
认证路由 - 用户登录、注册、Token管理
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from backend.services.auth_service import auth_service
from backend.services.user_service import user_service
from backend.models.user import UserCreate, UserUpdate, UserPreferences

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    preferences: Optional[UserPreferences] = None


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    """获取当前用户信息"""
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization.split(" ", 1)[1]
    token_data = auth_service.verify_token(token)

    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await user_service.get_user_by_username(token_data.sub)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive")

    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "preferences": user.preferences.model_dump() if user.preferences else {}
    }


@router.post("/login")
async def login(payload: LoginRequest):
    """用户登录"""
    user = await user_service.authenticate_user(payload.username, payload.password)

    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = auth_service.create_access_token(sub=user.username)
    refresh_token = auth_service.create_access_token(sub=user.username, expires_delta=60*60*24*7)

    return {
        "success": True,
        "data": {
            "access_token": token,
            "refresh_token": refresh_token,
            "expires_in": 60 * 60,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "preferences": user.preferences.model_dump() if user.preferences else {}
            }
        },
        "message": "登录成功"
    }


@router.post("/register")
async def register(payload: UserCreate):
    """用户注册"""
    user = await user_service.create_user(payload)

    if not user:
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")

    return {
        "success": True,
        "data": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email
        },
        "message": "注册成功"
    }


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "success": True,
        "data": user,
        "message": "获取用户信息成功"
    }


@router.put("/me")
async def update_me(
    payload: UserUpdate,
    user: dict = Depends(get_current_user)
):
    """更新当前用户信息"""
    updated_user = await user_service.update_user(user["username"], payload)

    if not updated_user:
        raise HTTPException(status_code=400, detail="更新失败")

    return {
        "success": True,
        "data": {
            "id": str(updated_user.id),
            "username": updated_user.username,
            "email": updated_user.email,
            "preferences": updated_user.preferences.model_dump()
        },
        "message": "用户信息更新成功"
    }


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    user: dict = Depends(get_current_user)
):
    """修改密码"""
    success = await user_service.change_password(
        user["username"],
        payload.old_password,
        payload.new_password
    )

    if not success:
        raise HTTPException(status_code=400, detail="旧密码错误")

    return {
        "success": True,
        "data": {},
        "message": "密码修改成功"
    }


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """用户登出"""
    return {
        "success": True,
        "data": {},
        "message": "登出成功"
    }


@router.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 100,
    user: dict = Depends(get_current_user)
):
    """获取用户列表（管理员操作）"""
    if not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="权限不足")

    users = await user_service.list_users(skip=skip, limit=limit)

    return {
        "success": True,
        "data": {
            "users": [
                {
                    "id": str(u.id),
                    "username": u.username,
                    "email": u.email,
                    "is_admin": u.is_admin,
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat() if u.created_at else None
                }
                for u in users
            ],
            "total": len(users)
        },
        "message": "获取用户列表成功"
    }
