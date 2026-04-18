"""
统一API响应格式
"""
from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一API响应格式"""
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"key": "value"},
                "message": "操作成功",
                "error": None
            }
        }


def success_response(data: Any = None, message: str = "操作成功") -> dict:
    """成功响应"""
    return {
        "success": True,
        "data": data,
        "message": message,
        "error": None
    }


def error_response(error: str, message: str = "操作失败", data: Any = None) -> dict:
    """错误响应"""
    return {
        "success": False,
        "data": data,
        "message": message,
        "error": error
    }


def paginated_response(
    items: list,
    total: int,
    page: int = 1,
    page_size: int = 20,
    message: str = "获取成功"
) -> dict:
    """分页响应"""
    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size
        },
        "message": message,
        "error": None
    }
