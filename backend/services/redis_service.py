"""
Redis 服务 - 缓存和会话管理
"""
import os
import json
from typing import Optional, Any
from datetime import timedelta
import redis

class RedisService:
    """Redis服务类，处理缓存和会话管理"""

    def __init__(self, connection_url: str = None):
        self.connection_url = connection_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client: Optional[redis.Redis] = None
        self._parse_connection_url()

    def _parse_connection_url(self):
        """解析Redis连接URL"""
        # redis://host:port/db
        url = self.connection_url.replace("redis://", "")
        parts = url.split("/")
        host_port = parts[0].split(":")
        self.host = host_port[0] if len(host_port) > 0 else "localhost"
        self.port = int(host_port[1]) if len(host_port) > 1 else 6379
        self.db = int(parts[1]) if len(parts) > 1 else 0

    def connect(self) -> "RedisService":
        """建立Redis连接"""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # 验证连接
            try:
                self._client.ping()
            except redis.ConnectionError as e:
                raise Exception(f"Redis连接失败: {e}")
            print(f"[Redis] 已连接到 {self.host}:{self.port}/{self.db}")
        return self

    def disconnect(self):
        """关闭Redis连接"""
        if self._client:
            self._client.close()
            self._client = None
            print("[Redis] 连接已关闭")

    @property
    def client(self) -> redis.Redis:
        """获取Redis客户端实例"""
        if self._client is None:
            self.connect()
        return self._client

    # ========== 基础操作 ==========

    def get(self, key: str) -> Optional[str]:
        """获取值"""
        try:
            return self.client.get(key)
        except Exception as e:
            print(f"[Redis] GET失败 {key}: {e}")
            return None

    def set(self, key: str, value: str, expire: int = None) -> bool:
        """设置值"""
        try:
            if expire:
                return self.client.setex(key, expire, value)
            else:
                return self.client.set(key, value)
        except Exception as e:
            print(f"[Redis] SET失败 {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除键"""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            print(f"[Redis] DELETE失败 {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return bool(self.client.exists(key))
        except Exception:
            return False

    def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        try:
            return bool(self.client.expire(key, seconds))
        except Exception:
            return False

    # ========== JSON操作 ==========

    def get_json(self, key: str) -> Optional[Any]:
        """获取JSON格式的值"""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    def set_json(self, key: str, value: Any, expire: int = None) -> bool:
        """设置JSON格式的值"""
        try:
            json_str = json.dumps(value, ensure_ascii=False)
            return self.set(key, json_str, expire)
        except (TypeError, json.JSONEncodeError) as e:
            print(f"[Redis] JSON编码失败: {e}")
            return False

    # ========== 哈希操作 ==========

    def hget(self, name: str, key: str) -> Optional[str]:
        """获取哈希字段值"""
        try:
            return self.client.hget(name, key)
        except Exception:
            return None

    def hset(self, name: str, key: str, value: str) -> bool:
        """设置哈希字段值"""
        try:
            return bool(self.client.hset(name, key, value))
        except Exception:
            return False

    def hgetall(self, name: str) -> dict:
        """获取哈希所有字段"""
        try:
            return self.client.hgetall(name)
        except Exception:
            return {}

    def hdel(self, name: str, *keys: str) -> bool:
        """删除哈希字段"""
        try:
            return bool(self.client.hdel(name, *keys))
        except Exception:
            return False

    # ========== 缓存业务方法 ==========

    def cache_report_analysis(self, report_id: str, query: str,
                             result: dict, expire: int = 3600) -> bool:
        """
        缓存报告分析结果

        Args:
            report_id: 报告ID
            query: 查询内容
            result: 分析结果
            expire: 过期时间(秒)，默认1小时
        """
        key = f"report:analysis:{report_id}:{hash(query)}"
        return self.set_json(key, result, expire)

    def get_cached_analysis(self, report_id: str, query: str) -> Optional[dict]:
        """获取缓存的分析结果"""
        key = f"report:analysis:{report_id}:{hash(query)}"
        return self.get_json(key)

    def cache_embedding(self, text_hash: str, embedding: list, expire: int = 86400) -> bool:
        """
        缓存文本嵌入结果

        Args:
            text_hash: 文本哈希
            embedding: 嵌入向量
            expire: 过期时间(秒)，默认24小时
        """
        key = f"embedding:{text_hash}"
        return self.set_json(key, embedding, expire)

    def get_cached_embedding(self, text_hash: str) -> Optional[list]:
        """获取缓存的嵌入向量"""
        key = f"embedding:{text_hash}"
        return self.get_json(key)

    def cache_search_results(self, query: str, collection: str,
                             results: list, expire: int = 1800) -> bool:
        """缓存搜索结果"""
        key = f"search:{collection}:{hash(query)}"
        return self.set_json(key, results, expire)

    def get_cached_search(self, query: str, collection: str) -> Optional[list]:
        """获取缓存的搜索结果"""
        key = f"search:{collection}:{hash(query)}"
        return self.get_json(key)

    # ========== 会话管理 ==========

    def create_session(self, session_id: str, data: dict,
                       expire: int = 3600) -> bool:
        """
        创建用户会话

        Args:
            session_id: 会话ID
            data: 会话数据
            expire: 过期时间(秒)，默认1小时
        """
        key = f"session:{session_id}"
        return self.set_json(key, data, expire)

    def get_session(self, session_id: str) -> Optional[dict]:
        """获取会话数据"""
        key = f"session:{session_id}"
        return self.get_json(key)

    def update_session(self, session_id: str, data: dict) -> bool:
        """更新会话数据"""
        key = f"session:{session_id}"
        # 获取当前TTL
        ttl = self.client.ttl(key)
        if ttl > 0:
            return self.set_json(key, data, ttl)
        return False

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        key = f"session:{session_id}"
        return self.delete(key)

    # ========== 分布式锁 ==========

    def acquire_lock(self, lock_name: str, timeout: int = 10) -> Optional[str]:
        """
        获取分布式锁

        Args:
            lock_name: 锁名称
            timeout: 锁超时时间(秒)

        Returns:
            锁标识符或None
        """
        lock_key = f"lock:{lock_name}"
        import uuid
        lock_value = str(uuid.uuid4())

        if self.client.set(lock_key, lock_value, nx=True, ex=timeout):
            return lock_value
        return None

    def release_lock(self, lock_name: str, lock_value: str) -> bool:
        """释放分布式锁"""
        lock_key = f"lock:{lock_name}"

        # 使用Lua脚本确保原子性
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        try:
            result = self.client.eval(script, 1, lock_key, lock_value)
            return bool(result)
        except Exception:
            return False

    # ========== 统计和方法 ==========

    def increment(self, key: str, amount: int = 1) -> int:
        """递增计数"""
        try:
            return self.client.incrby(key, amount)
        except Exception:
            return 0

    def get_stats(self) -> dict:
        """获取Redis状态信息"""
        try:
            info = self.client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "keys": self.client.dbsize(),
                "uptime_days": info.get("uptime_days", 0)
            }
        except Exception:
            return {"connected": False}

    # ========== 解析进度管理 ==========

    def set_parse_progress(self, kb_id: str, progress: dict, expire: int = 3600) -> bool:
        """
        设置知识库解析进度

        Args:
            kb_id: 知识库ID
            progress: 进度信息 {"stage": "extracting|chunking|vectorizing|indexing", "progress": 0-100, "message": ""}
            expire: 过期时间(秒)，默认1小时
        """
        key = f"kb:progress:{kb_id}"
        return self.set_json(key, progress, expire)

    def get_parse_progress(self, kb_id: str) -> Optional[dict]:
        """获取知识库解析进度"""
        key = f"kb:progress:{kb_id}"
        return self.get_json(key)

    def delete_parse_progress(self, kb_id: str) -> bool:
        """删除知识库解析进度"""
        key = f"kb:progress:{kb_id}"
        return self.delete(key)


# 单例模式全局实例
_redis_service: Optional[RedisService] = None

def get_redis_service() -> RedisService:
    """获取Redis服务单例"""
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService().connect()
    return _redis_service
