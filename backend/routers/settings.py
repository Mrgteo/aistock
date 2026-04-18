"""
系统设置路由 - 提供设置相关的API接口
"""
import os
import sqlite3
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.responses import success_response, error_response

router = APIRouter(prefix="/api/settings", tags=["系统设置"])

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "stock_trade.db")


def get_db_connection():
    """获取数据库连接（使用连接池）"""
    from backend.utils.db_pool import get_db_pool
    pool = get_db_pool(DB_PATH, pool_size=5)
    return pool.get_connection()


class SettingsItem(BaseModel):
    key: str
    value: Any
    type: str = "string"


@router.get("/llm")
async def get_llm_settings():
    """获取LLM配置"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 从数据库获取设置
        settings_keys = [
            'deepseek_api_key', 'deepseek_base_url', 'default_model',
            'embedding_mode', 'dashscope_api_key', 'embedding_model', 'embedding_dim'
        ]

        result = {}
        for key in settings_keys:
            cursor.execute("SELECT value, type FROM system_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                if row['type'] == 'number':
                    result[key] = int(row['value'])
                else:
                    result[key] = row['value']

        return success_response(data={"config": result}, message="获取LLM配置成功")

    except Exception as e:
        return error_response(error=str(e), message="获取配置失败")


@router.post("/llm")
async def save_llm_settings(settings: Dict[str, Any]):
    """保存LLM配置"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        settings_keys = [
            'deepseek_api_key', 'deepseek_base_url', 'default_model',
            'embedding_mode', 'dashscope_api_key', 'embedding_model', 'embedding_dim'
        ]

        for key, value in settings.items():
            if key in settings_keys:
                value_type = 'number' if isinstance(value, int) else 'string'
                cursor.execute("""
                    INSERT OR REPLACE INTO system_settings (key, value, type, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (key, str(value), value_type))

        conn.commit()

        return success_response(message="LLM配置已保存")

    except Exception as e:
        return error_response(error=str(e), message="保存配置失败")


@router.post("/llm/test")
async def test_llm_connection():
    """测试LLM连接"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_settings WHERE key = 'deepseek_api_key'")
        row = cursor.fetchone()
        api_key = row['value'] if row else None

        cursor.execute("SELECT value FROM system_settings WHERE key = 'deepseek_base_url'")
        row = cursor.fetchone()
        base_url = row['value'] if row else "https://api.deepseek.com/v1"

        if not api_key:
            return error_response(error="API Key未配置", message="连接失败")

        # 测试API连接
        from backend.utils.http_client import get_http_client
        http_client = get_http_client()
        try:
            response = await http_client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "Hi"}]},
                timeout=10
            )
            if "choices" in response:
                return success_response(message="LLM连接成功")
            else:
                return error_response(error=str(response), message="连接失败")
        except Exception as e:
            return error_response(error=str(e), message="连接失败")

    except Exception as e:
        return error_response(error=str(e), message="连接异常")


@router.post("/llm/embedding/test")
async def test_embedding_connection():
    """测试Embedding连接"""
    try:
        import dashscope
        from dashscope import TextEmbedding

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_settings WHERE key = 'dashscope_api_key'")
        row = cursor.fetchone()
        api_key = row['value'] if row else None
        conn.close()

        if not api_key:
            return error_response(error="API Key未配置", message="连接失败")

        dashscope.api_key = api_key
        response = TextEmbedding.call(
            model="text-embedding-v4",
            input="测试文本"
        )

        if response.status_code == 200:
            return success_response(message="Embedding服务连接成功")
        else:
            return error_response(error=f"连接失败: {response.code}", message="连接失败")

    except Exception as e:
        return error_response(error=str(e), message="连接异常")


@router.get("/ocr")
async def get_ocr_settings():
    """获取OCR配置"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        settings_keys = [
            'paddleocr_api_url', 'paddleocr_access_token', 'paddleocr_timeout'
        ]

        result = {}
        for key in settings_keys:
            cursor.execute("SELECT value, type FROM system_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                if row['type'] == 'number':
                    result[key] = int(row['value'])
                else:
                    result[key] = row['value']

        conn.close()
        return {"success": True, "config": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/ocr")
async def save_ocr_settings(settings: Dict[str, Any]):
    """保存OCR配置"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        settings_keys = [
            'paddleocr_api_url', 'paddleocr_access_token', 'paddleocr_timeout'
        ]

        for key, value in settings.items():
            if key in settings_keys:
                value_type = 'number' if isinstance(value, int) else 'string'
                cursor.execute("""
                    INSERT OR REPLACE INTO system_settings (key, value, type, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (key, str(value), value_type))

        conn.commit()

        return success_response(message="OCR配置已保存")

    except Exception as e:
        return error_response(error=str(e), message="保存OCR配置失败")


@router.post("/ocr/test")
async def test_ocr_connection():
    """测试OCR连接"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_settings WHERE key = 'paddleocr_access_token'")
        row = cursor.fetchone()
        access_token = row['value'] if row else None

        if not access_token:
            return error_response(error="Access Token未配置", message="连接失败")

        return success_response(message="OCR配置验证成功（实际连接测试需要文件上传）")

    except Exception as e:
        return error_response(error=str(e), message="连接异常")


@router.get("/rerank")
async def get_rerank_settings():
    """获取Rerank配置"""
    try:
        from backend.core.config import settings
        return success_response(
            data={
                "config": {
                    "rerank_model": os.getenv("RERANK_MODEL", "gte-rerank"),
                    "rerank_api_key": settings.DASHSCOPE_API_KEY[:10] + "..." if settings.DASHSCOPE_API_KEY else None
                }
            },
            message="获取Rerank配置成功"
        )
    except Exception as e:
        return error_response(error=str(e), message="获取配置失败")


@router.get("/all")
async def get_all_settings():
    """获取所有系统设置"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value, type FROM system_settings")
        rows = cursor.fetchall()

        settings_dict = {}
        for row in rows:
            if row['type'] == 'number':
                settings_dict[row['key']] = int(row['value'])
            else:
                settings_dict[row['key']] = row['value']

        # 从.env补充未保存的设置
        env_settings_dict = {
            "rerank_model": os.getenv("RERANK_MODEL", "gte-rerank"),
            "chroma_persist_dir": os.getenv("CHROMA_PERSIST_DIR", "./database/chroma"),
            "mongodb_db": os.getenv("MONGODB_DB", "stock_trade_reports"),
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        }

        for key, value in env_settings_dict.items():
            if key not in settings_dict:
                settings_dict[key] = value

        return success_response(data={"settings": settings_dict}, message="获取所有设置成功")

    except Exception as e:
        return error_response(error=str(e), message="获取配置失败")


# ========== 数据源配置 ==========

@router.get("/datasource")
async def get_datasource_settings():
    """获取数据源配置"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        settings_keys = [
            'tushare_token', 'akshare_enabled', 'stockapi_key'
        ]

        result = {}
        for key in settings_keys:
            cursor.execute("SELECT value, type FROM system_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                if row['type'] == 'number':
                    result[key] = int(row['value'])
                elif row['type'] == 'boolean':
                    result[key] = row['value'] == 'true'
                else:
                    result[key] = row['value']

        return success_response(data={"config": result}, message="获取数据源配置成功")

    except Exception as e:
        return error_response(error=str(e), message="获取配置失败")


@router.post("/datasource")
async def save_datasource_settings(settings: Dict[str, Any]):
    """保存数据源配置"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        settings_keys = [
            'tushare_token', 'akshare_enabled', 'stockapi_key'
        ]

        for key, value in settings.items():
            if key in settings_keys:
                if key == 'akshare_enabled':
                    value = 'true' if value else 'false'
                    value_type = 'boolean'
                elif isinstance(value, bool):
                    value = 'true' if value else 'false'
                    value_type = 'boolean'
                elif isinstance(value, int):
                    value = str(value)
                    value_type = 'number'
                else:
                    value_type = 'string'

                cursor.execute("""
                    INSERT OR REPLACE INTO system_settings (key, value, type, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (key, str(value), value_type))

        conn.commit()

        return success_response(message="数据源配置已保存")

    except Exception as e:
        return error_response(error=str(e), message="保存配置失败")


@router.get("/database")
async def get_database_settings():
    """获取数据库配置"""
    try:
        # 从环境变量获取（这些是系统级配置）
        return success_response(
            data={
                "config": {
                    "mongodb_url": os.getenv("MONGODB_URL", "mongodb://localhost:27017"),
                    "mongodb_db": os.getenv("MONGODB_DB", "stock_trade_reports"),
                    "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                    "chroma_persist_dir": os.getenv("CHROMA_PERSIST_DIR", "./database/chroma")
                }
            },
            message="获取数据库配置成功"
        )
    except Exception as e:
        return error_response(error=str(e), message="获取配置失败")


# ========== 缓存管理 ==========

@router.get("/cache/status")
async def get_cache_status():
    """获取缓存状态"""
    try:
        from backend.services.redis_service import get_redis_service
        from backend.services.chroma_service import get_chroma_service

        status = {
            "redis": {"connected": False, "keys": 0},
            "chroma": {"connected": False, "knowledge_chunks": 0, "report_chunks": 0}
        }

        # Redis状态
        try:
            redis = get_redis_service()
            redis_stats = redis.get_stats()
            status["redis"]["connected"] = redis_stats.get("connected", False)
            status["redis"]["keys"] = redis_stats.get("keys", 0)
            status["redis"]["used_memory"] = redis_stats.get("used_memory", "unknown")
        except Exception as e:
            status["redis"]["error"] = str(e)

        # Chroma状态
        try:
            chroma = get_chroma_service()
            if chroma.is_connected:
                status["chroma"]["connected"] = True
                kb_stats = chroma.get_collection_stats("knowledge_chunks")
                report_stats = chroma.get_collection_stats("report_chunks")
                status["chroma"]["knowledge_chunks"] = kb_stats.get("entities", 0)
                status["chroma"]["report_chunks"] = report_stats.get("entities", 0)
        except Exception as e:
            status["chroma"]["error"] = str(e)

        return success_response(data={"status": status}, message="获取缓存状态成功")

    except Exception as e:
        return error_response(error=str(e), message="获取缓存状态失败")


@router.post("/cache/clear")
async def clear_redis_cache():
    """清理Redis缓存"""
    try:
        from backend.services.redis_service import get_redis_service

        redis = get_redis_service()
        try:
            # 使用Redis FLUSHDB 清空当前数据库
            redis.client.flushdb()
            return success_response(message="Redis缓存已清理")
        except Exception as e:
            return error_response(error=str(e), message="清理Redis缓存失败")

    except Exception as e:
        return error_response(error=str(e), message="清理Redis缓存失败")


@router.post("/cache/clear-chroma")
async def clear_chroma_cache():
    """清理Chroma向量缓存"""
    try:
        from backend.services.chroma_service import get_chroma_service

        chroma = get_chroma_service()
        if chroma.is_connected:
            # 清理knowledge_chunks
            try:
                chroma.reset_collection("knowledge_chunks")
            except:
                pass
            # 清理report_chunks
            try:
                chroma.reset_collection("report_chunks")
            except:
                pass
            return success_response(message="Chroma缓存已清理")
        else:
            return error_response(error="Chroma未连接", message="清理失败")

    except Exception as e:
        return error_response(error=str(e), message="清理Chroma缓存失败")
