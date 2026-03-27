"""
系统配置管理
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """系统配置"""

    # 应用基础配置
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8017
    APP_NAME: str = "股票交易辅助系统"
    VERSION: str = "1.0.0"

    # JWT认证配置
    JWT_SECRET: str = "stock-trade-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # DeepSeek API配置
    DEEPSEEK_API_KEY: str = "sk-8cb3bfe75b94480a8005a87362306526"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEFAULT_MODEL_NAME: str = "deepseek-chat"

    # 数据库配置 (SQLite)
    DB_PATH: str = "stock_trade.db"

    # 文件上传配置
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # CORS配置
    ALLOWED_ORIGINS: list = ["*"]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings
