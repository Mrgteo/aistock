"""
定制量化策略路由
提供5种选股策略的API接口：主力选股、低价擒牛、小市值、净利增长、低估值
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from backend.services.custom_strategy_engine import get_custom_strategy_engine

router = APIRouter(prefix="/api/custom_strategy", tags=["定制量化策略"])

# ========== 请求模型 ==========

class MainForceReq(BaseModel):
    """主力选股请求"""
    start_date: Optional[str] = None  # 格式: "2025年10月1日"
    days_ago: int = 90
    min_market_cap: float = 0
    max_market_cap: float = 500
    top_n: int = 20


class LowPriceBullReq(BaseModel):
    """低价擒牛请求"""
    top_n: int = 5


class SmallCapReq(BaseModel):
    """小市值策略请求"""
    top_n: int = 5


class ProfitGrowthReq(BaseModel):
    """净利增长请求"""
    top_n: int = 5


class ValueStockReq(BaseModel):
    """低估值策略请求"""
    top_n: int = 10


class AllStrategiesReq(BaseModel):
    """全部策略请求"""
    main_force_top_n: int = 20
    low_price_top_n: int = 5
    small_cap_top_n: int = 5
    profit_growth_top_n: int = 5
    value_top_n: int = 10
    days_ago: int = 90


# ========== 策略描述 ==========

STRATEGY_DESCRIPTIONS = {
    "main_force": {
        "name": "主力选股",
        "icon": "💰",
        "description": "跟踪主力资金净流入，筛选大资金关注的股票",
        "conditions": ["主力资金净流入排名", "市值筛选", "区间涨跌幅计算"],
        "params": ["时间范围", "市值区间", "返回数量"]
    },
    "low_price_bull": {
        "name": "低价擒牛",
        "icon": "🐂",
        "description": "低价+高成长，寻找估值洼地中的爆发股",
        "conditions": ["股价 < 10元", "净利润增长 ≥ 100%", "非ST/科创/创业"],
        "params": ["返回数量"]
    },
    "small_cap": {
        "name": "小市值策略",
        "icon": "🚀",
        "description": "小市值+高成长，寻找未来潜力黑马",
        "conditions": ["总市值 ≤ 50亿", "营收增长 ≥ 10%", "净利增长 ≥ 100%"],
        "params": ["返回数量"]
    },
    "profit_growth": {
        "name": "净利增长",
        "icon": "📈",
        "description": "聚焦净利润持续增长的优质企业",
        "conditions": ["净利润增长 ≥ 10%", "深圳A股", "非ST/科创/创业"],
        "params": ["返回数量"]
    },
    "value": {
        "name": "低估值策略",
        "icon": "💎",
        "description": "价值投资，寻找被低估的优质股票",
        "conditions": ["市盈率 ≤ 20", "市净率 ≤ 1.5", "股息率 ≥ 1%", "资产负债率 ≤ 30%"],
        "params": ["返回数量"]
    }
}


# ========== API 端点 ==========

@router.get("/strategies")
async def get_strategy_descriptions():
    """获取所有策略描述"""
    return {"success": True, "strategies": STRATEGY_DESCRIPTIONS}


@router.post("/main_force")
async def run_main_force_strategy(req: MainForceReq):
    """执行主力资金选股"""
    engine = get_custom_strategy_engine()
    result = engine.run_main_force(
        start_date=req.start_date,
        days_ago=req.days_ago,
        min_market_cap=req.min_market_cap,
        max_market_cap=req.max_market_cap,
        top_n=req.top_n
    )
    return result


@router.post("/low_price_bull")
async def run_low_price_bull_strategy(req: LowPriceBullReq):
    """执行低价擒牛选股"""
    engine = get_custom_strategy_engine()
    result = engine.run_low_price_bull(top_n=req.top_n)
    return result


@router.post("/small_cap")
async def run_small_cap_strategy(req: SmallCapReq):
    """执行小市值策略选股"""
    engine = get_custom_strategy_engine()
    result = engine.run_small_cap(top_n=req.top_n)
    return result


@router.post("/profit_growth")
async def run_profit_growth_strategy(req: ProfitGrowthReq):
    """执行净利增长选股"""
    engine = get_custom_strategy_engine()
    result = engine.run_profit_growth(top_n=req.top_n)
    return result


@router.post("/value_stock")
async def run_value_stock_strategy(req: ValueStockReq):
    """执行低估值选股"""
    engine = get_custom_strategy_engine()
    result = engine.run_value_stock(top_n=req.top_n)
    return result


@router.post("/all")
async def run_all_strategies(req: AllStrategiesReq):
    """执行全部5种策略"""
    engine = get_custom_strategy_engine()
    result = engine.run_all_strategies(
        main_force_top_n=req.main_force_top_n,
        low_price_top_n=req.low_price_top_n,
        small_cap_top_n=req.small_cap_top_n,
        profit_growth_top_n=req.profit_growth_top_n,
        value_top_n=req.value_top_n,
        days_ago=req.days_ago
    )
    result["timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return result


@router.get("/columns/{strategy}")
async def get_strategy_columns(strategy: str):
    """
    获取指定策略返回的数据列信息
    用于前端表格渲染
    """
    column_map = {
        "main_force": [
            {"key": "股票代码", "label": "代码", "width": 90},
            {"key": "股票简称", "label": "名称", "width": 100},
            {"key": "主力资金净流入", "label": "主力净流入", "width": 120},
            {"key": "区间涨跌幅", "label": "区间涨跌幅", "width": 100},
            {"key": "总市值", "label": "总市值", "width": 100},
            {"key": "所属同花顺行业", "label": "行业", "width": 120},
            {"key": "市盈率", "label": "市盈率", "width": 80},
            {"key": "市净率", "label": "市净率", "width": 80},
        ],
        "low_price_bull": [
            {"key": "股票代码", "label": "代码", "width": 90},
            {"key": "股票简称", "label": "名称", "width": 100},
            {"key": "股价", "label": "股价", "width": 80},
            {"key": "净利润增长率", "label": "净利增长", "width": 100},
            {"key": "成交额", "label": "成交额", "width": 120},
        ],
        "small_cap": [
            {"key": "股票代码", "label": "代码", "width": 90},
            {"key": "股票简称", "label": "名称", "width": 100},
            {"key": "总市值", "label": "总市值", "width": 100},
            {"key": "营收增长率", "label": "营收增长", "width": 100},
            {"key": "净利润增长率", "label": "净利增长", "width": 100},
        ],
        "profit_growth": [
            {"key": "股票代码", "label": "代码", "width": 90},
            {"key": "股票简称", "label": "名称", "width": 100},
            {"key": "净利润增长率", "label": "净利增长", "width": 100},
            {"key": "成交额", "label": "成交额", "width": 120},
        ],
        "value": [
            {"key": "股票代码", "label": "代码", "width": 90},
            {"key": "股票简称", "label": "名称", "width": 100},
            {"key": "市盈率", "label": "市盈率", "width": 80},
            {"key": "市净率", "label": "市净率", "width": 80},
            {"key": "股息率", "label": "股息率", "width": 80},
            {"key": "资产负债率", "label": "资产负债率", "width": 100},
            {"key": "流通市值", "label": "流通市值", "width": 120},
        ]
    }

    if strategy not in column_map:
        raise HTTPException(status_code=404, detail=f"策略 {strategy} 不存在")

    return {"success": True, "columns": column_map[strategy]}
