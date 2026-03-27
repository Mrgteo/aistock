"""
股票筛选路由 - 同花顺问财自然语言选股
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.services.stock_screener import get_screener

router = APIRouter(prefix="/api/screener", tags=["股票筛选"])


class StockScreenReq(BaseModel):
    """股票筛选请求"""
    query: str  # 问财格式查询条件，如 "换手率大于3%"
    page_size: int = 50


class StockInfoReq(BaseModel):
    """股票信息查询请求"""
    code: str  # 股票代码


@router.get("/hot_strategies")
async def get_hot_strategies():
    """
    获取热门选股策略列表

    这些是常用的问财查询条件，可以直接用于筛选
    """
    screener = get_screener()
    strategies = screener.hot_strategies()
    return {"success": True, "data": strategies}


@router.post("/stock")
async def screen_stock(req: StockScreenReq):
    """
    股票条件筛选（同花顺问财自然语言）

    支持的查询语法示例：
    - MACD金叉
    - KDJ金叉
    - 换手率大于5%
    - 量比大于2
    - 涨幅大于5%
    - 跌幅大于3%
    - 市盈率小于30
    - 市净率小于3
    - 流通市值小于50亿
    - 股价小于10元
    - RSI低于30
    - RSI超买70
    - 创历史新高
    - 创历史新低
    - 10日内有涨停
    - 突破年线
    - 5日均线上穿10日均线
    - 今日低开高走
    - 今日放量上涨
    - 涨停股

    可以组合多个条件，用逗号或空格分隔
    """
    screener = get_screener()
    result = screener.screen(req.query, req.page_size)

    if result.get("code") == -1:
        raise HTTPException(status_code=500, detail=result.get("message"))

    return {
        "success": True,
        "query": req.query,
        "count": result.get("data", {}).get("count", 0),
        "columns": result.get("data", {}).get("columns", []),
        "rows": result.get("data", {}).get("rows", [])
    }


@router.get("/stock/{code}")
async def get_stock_info(code: str):
    """
    获取单只股票详细信息

    Args:
        code: 股票代码，如 600519
    """
    screener = get_screener()
    result = screener.get_stock_info(code)

    if result.get("code") == -1:
        raise HTTPException(status_code=500, detail=result.get("message"))

    return {
        "success": True,
        "data": result.get("data", {})
    }
