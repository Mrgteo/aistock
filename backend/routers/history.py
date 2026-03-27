"""
股票分析历史记录路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any

from backend.routers.analysis_db import db

router = APIRouter(prefix="/api/history", tags=["历史记录"])


class RecordDeleteReq(BaseModel):
    record_id: int


class RecordSearchReq(BaseModel):
    keyword: str


# 获取历史记录列表
@router.get("/records")
async def get_records(limit: int = 50, offset: int = 0):
    """获取历史分析记录列表"""
    records = db.get_all_records(limit=limit, offset=offset)
    total = db.get_record_count()
    return {
        "success": True,
        "total": total,
        "records": records
    }


# 搜索历史记录
@router.get("/search")
async def search_records(keyword: str, limit: int = 50):
    """搜索历史记录"""
    if not keyword:
        return {"success": True, "records": []}

    records = db.search_records(keyword=keyword, limit=limit)
    return {
        "success": True,
        "records": records
    }


# 获取单条记录详情
@router.get("/record/{record_id}")
async def get_record(record_id: int):
    """获取历史记录详情"""
    record = db.get_record_by_id(record_id)

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    return {
        "success": True,
        "record": record
    }


# 删除单条记录
@router.post("/delete")
async def delete_record(req: RecordDeleteReq):
    """删除历史记录"""
    success = db.delete_record(req.record_id)

    if not success:
        raise HTTPException(status_code=404, detail="记录不存在或删除失败")

    return {"success": True, "message": "记录已删除"}


# 获取记录总数
@router.get("/count")
async def get_record_count():
    """获取历史记录总数"""
    count = db.get_record_count()
    return {"success": True, "count": count}


# 删除所有记录
@router.post("/delete_all")
async def delete_all_records():
    """删除所有历史记录"""
    count = db.delete_all_records()
    return {"success": True, "deleted": count, "message": f"已删除 {count} 条记录"}
