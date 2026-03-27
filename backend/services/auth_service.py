"""
认证服务 - JWT Token管理
"""

import time
from datetime import datetime, timedelta
from typing import Optional
import jwt
from pydantic import BaseModel

# JWT配置
JWT_SECRET = "stock-trade-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class TokenData(BaseModel):
    sub: str
    exp: int


class AuthService:
    """认证服务类"""

    @staticmethod
    def create_access_token(sub: str, expires_delta: int = None) -> str:
        """创建访问令牌"""
        if expires_delta:
            expire = datetime.utcnow() + timedelta(seconds=expires_delta)
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {"sub": sub, "exp": expire}
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token

    @staticmethod
    def verify_token(token: str) -> Optional[TokenData]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            token_data = TokenData(sub=payload.get("sub"), exp=int(payload.get("exp", time.time())))

            # 检查是否过期
            current_time = int(time.time())
            if token_data.exp < current_time:
                return None

            return token_data

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception:
            return None

    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return AuthService.hash_password(plain_password) == hashed_password


auth_service = AuthService()
