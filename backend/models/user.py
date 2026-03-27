"""
用户数据模型
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr


class UserPreferences(BaseModel):
    """用户偏好设置"""
    default_market: str = "A股"
    default_depth: str = "3"
    auto_refresh: bool = True
    refresh_interval: int = 30
    ui_theme: str = "light"
    language: str = "zh-CN"
    notifications_enabled: bool = True


class User(BaseModel):
    """用户模型"""
    id: Optional[str] = Field(default=None, alias="_id")
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    daily_quota: int = 1000
    concurrent_limit: int = 3
    total_analyses: int = 0
    successful_analyses: int = 0
    failed_analyses: int = 0

    class Config:
        populate_by_name = True


class UserCreate(BaseModel):
    """创建用户请求模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=6, max_length=100)


class UserUpdate(BaseModel):
    """更新用户请求模型"""
    email: Optional[str] = None
    preferences: Optional[UserPreferences] = None


class UserResponse(BaseModel):
    """用户响应模型"""
    id: str
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    preferences: UserPreferences


class TokenData(BaseModel):
    """Token数据"""
    sub: str
    exp: int


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
