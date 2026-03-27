"""
用户服务 - 基于SQLite的用户管理
"""

import sqlite3
import hashlib
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager

from backend.models.user import User, UserCreate, UserUpdate, UserPreferences


DB_PATH = "stock_trade.db"


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    """数据库上下文管理器"""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """初始化数据库表"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                is_verified INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                preferences TEXT DEFAULT '{}',
                daily_quota INTEGER DEFAULT 1000,
                concurrent_limit INTEGER DEFAULT 3,
                total_analyses INTEGER DEFAULT 0,
                successful_analyses INTEGER DEFAULT 0,
                failed_analyses INTEGER DEFAULT 0
            )
        """)
        conn.commit()

        # 创建默认管理员用户
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            admin_password = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute("""
                INSERT INTO users (username, email, hashed_password, is_admin, is_verified, preferences)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("admin", "admin@stocktrade.local", admin_password, 1, 1, '{"ui_theme": "light", "language": "zh-CN"}'))
            conn.commit()
            print("默认管理员用户已创建: admin / admin123")


class UserService:
    """用户服务类"""

    def __init__(self):
        init_db()

    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        """将数据库行转换为用户对象"""
        preferences = {}
        if row["preferences"]:
            import json
            try:
                preferences = json.loads(row["preferences"])
            except:
                preferences = {}

        return User(
            id=str(row["id"]),
            username=row["username"],
            email=row["email"],
            hashed_password=row["hashed_password"],
            is_active=bool(row["is_active"]),
            is_verified=bool(row["is_verified"]),
            is_admin=bool(row["is_admin"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.utcnow(),
            last_login=datetime.fromisoformat(row["last_login"]) if row["last_login"] else None,
            preferences=UserPreferences(**preferences),
            daily_quota=row["daily_quota"],
            concurrent_limit=row["concurrent_limit"],
            total_analyses=row["total_analyses"],
            successful_analyses=row["successful_analyses"],
            failed_analyses=row["failed_analyses"]
        )

    async def create_user(self, user_data: UserCreate) -> Optional[User]:
        """创建用户"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()

                # 检查用户名是否存在
                cursor.execute("SELECT id FROM users WHERE username = ?", (user_data.username,))
                if cursor.fetchone():
                    return None

                # 检查邮箱是否存在
                cursor.execute("SELECT id FROM users WHERE email = ?", (user_data.email,))
                if cursor.fetchone():
                    return None

                # 创建用户
                hashed_password = self.hash_password(user_data.password)
                import json
                default_prefs = json.dumps({
                    "default_market": "A股",
                    "default_depth": "3",
                    "auto_refresh": True,
                    "refresh_interval": 30,
                    "ui_theme": "light",
                    "language": "zh-CN",
                    "notifications_enabled": True
                })

                cursor.execute("""
                    INSERT INTO users (username, email, hashed_password, preferences)
                    VALUES (?, ?, ?, ?)
                """, (user_data.username, user_data.email, hashed_password, default_prefs))
                conn.commit()

                user_id = cursor.lastrowid
                return await self.get_user_by_id(str(user_id))

        except Exception as e:
            print(f"创建用户失败: {e}")
            return None

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """用户认证"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()

                if not row:
                    return None

                hashed_password = self.hash_password(password)
                if row["hashed_password"] != hashed_password:
                    return None

                if not row["is_active"]:
                    return None

                # 更新最后登录时间
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE username = ?",
                    (datetime.utcnow().isoformat(), username)
                )
                conn.commit()

                return self._row_to_user(row)

        except Exception as e:
            print(f"用户认证失败: {e}")
            return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_user(row)
                return None
        except Exception as e:
            print(f"获取用户失败: {e}")
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据用户ID获取用户"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_user(row)
                return None
        except Exception as e:
            print(f"获取用户失败: {e}")
            return None

    async def update_user(self, username: str, user_data: UserUpdate) -> Optional[User]:
        """更新用户信息"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                update_fields = []
                params = []

                if user_data.email:
                    update_fields.append("email = ?")
                    params.append(user_data.email)

                if user_data.preferences:
                    import json
                    update_fields.append("preferences = ?")
                    params.append(json.dumps(user_data.preferences.model_dump()))

                if update_fields:
                    update_fields.append("updated_at = ?")
                    params.append(datetime.utcnow().isoformat())
                    params.append(username)

                    cursor.execute(
                        f"UPDATE users SET {', '.join(update_fields)} WHERE username = ?",
                        params
                    )
                    conn.commit()

                return await self.get_user_by_username(username)

        except Exception as e:
            print(f"更新用户失败: {e}")
            return None

    async def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        try:
            user = await self.authenticate_user(username, old_password)
            if not user:
                return False

            new_hashed = self.hash_password(new_password)
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET hashed_password = ?, updated_at = ? WHERE username = ?",
                    (new_hashed, datetime.utcnow().isoformat(), username)
                )
                conn.commit()
            return True

        except Exception as e:
            print(f"修改密码失败: {e}")
            return False

    async def reset_password(self, username: str, new_password: str) -> bool:
        """重置密码（管理员操作）"""
        try:
            new_hashed = self.hash_password(new_password)
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET hashed_password = ?, updated_at = ? WHERE username = ?",
                    (new_hashed, datetime.utcnow().isoformat(), username)
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"重置密码失败: {e}")
            return False

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """获取用户列表"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users LIMIT ? OFFSET ?", (limit, skip))
                rows = cursor.fetchall()
                return [self._row_to_user(row) for row in rows]
        except Exception as e:
            print(f"获取用户列表失败: {e}")
            return []


user_service = UserService()
