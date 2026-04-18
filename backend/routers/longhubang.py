"""
龙虎榜分析路由
龙虎榜深度分析、历史报告、数据统计 API
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import logging
import os

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.longhubang_engine import LonghubangEngine

router = APIRouter(prefix="/api/longhubang", tags=["龙虎榜分析"])
logger = logging.getLogger(__name__)

# 任务状态存储（生产环境建议使用Redis）
_task_status = {}


class AnalysisRequest(BaseModel):
    """分析请求模型"""
    date: Optional[str] = None  # 指定日期，格式YYYY-MM-DD
    days: int = 1  # 分析最近天数


class ReportDetailRequest(BaseModel):
    """报告详情请求模型"""
    report_id: int


# ========== 龙虎榜深度分析 ==========

@router.post("/analyze")
async def run_analysis(req: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    启动龙虎榜综合分析
    这是一个异步任务，会在后台运行
    """
    task_id = f"lhb_{id(req)}"

    # 在后台运行分析
    async def run_analysis_async():
        try:
            _task_status[task_id] = {"status": "running", "progress": 0}

            engine = LonghubangEngine()
            result = engine.run_comprehensive_analysis(date=req.date, days=req.days)

            _task_status[task_id] = {
                "status": "completed" if result.get("success") else "failed",
                "progress": 100,
                "result": result,
                "error": result.get("error")
            }
        except Exception as e:
            logger.exception(f"龙虎榜分析任务失败: {e}")
            _task_status[task_id] = {"status": "failed", "progress": 0, "error": str(e)}

    background_tasks.add_task(run_analysis_async)

    return {
        "success": True,
        "task_id": task_id,
        "message": "分析任务已启动，请在稍后查询结果"
    }


@router.get("/analyze/sync")
async def run_analysis_sync(date: Optional[str] = None, days: int = 1):
    """
    同步执行龙虎榜分析（阻塞直到完成）
    适用于小数据量或测试场景
    """
    try:
        logger.info(f"[龙虎榜] 开始同步分析... date={date}, days={days}")
        engine = LonghubangEngine()
        result = engine.run_comprehensive_analysis(date=date, days=days)
        return result
    except Exception as e:
        logger.exception(f"龙虎榜分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/status/{task_id}")
async def get_analysis_status(task_id: str):
    """查询分析任务状态"""
    status = _task_status.get(task_id)
    if not status:
        return {"status": "not_found", "message": "任务不存在或已过期"}
    return status


@router.get("/analyze/result/{task_id}")
async def get_analysis_result(task_id: str):
    """获取分析结果"""
    status = _task_status.get(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    if status.get("status") == "running":
        return {"status": "running", "progress": status.get("progress", 0)}

    if status.get("status") == "failed":
        return {"status": "failed", "error": status.get("error")}

    return {"status": "completed", "result": status.get("result")}


# ========== 历史报告 ==========

@router.get("/reports")
async def get_historical_reports(limit: int = 10):
    """获取历史分析报告列表"""
    try:
        engine = LonghubangEngine()
        reports_df = engine.get_historical_reports(limit=limit)

        if reports_df.empty:
            return {"success": True, "reports": [], "total": 0}

        # 转换为字典列表
        reports = []
        for _, row in reports_df.iterrows():
            reports.append({
                "id": row.get("id"),
                "analysis_date": row.get("analysis_date"),
                "data_date_range": row.get("data_date_range"),
                "summary": row.get("summary"),
                "created_at": row.get("created_at")
            })

        return {"success": True, "reports": reports, "total": len(reports)}
    except Exception as e:
        logger.exception(f"获取历史报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_id}")
async def get_report_detail(report_id: int):
    """获取报告详情"""
    try:
        engine = LonghubangEngine()
        report = engine.get_report_detail(report_id)

        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        return {"success": True, "report": report}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取报告详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reports/{report_id}")
async def delete_report(report_id: int):
    """删除分析报告"""
    try:
        engine = LonghubangEngine()
        success = engine.database.delete_analysis_report(report_id)

        if not success:
            raise HTTPException(status_code=404, detail="报告不存在或删除失败")

        return {"success": True, "message": "报告已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"删除报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 数据统计 ==========

@router.get("/statistics")
async def get_statistics():
    """获取数据库统计信息"""
    try:
        engine = LonghubangEngine()
        stats = engine.get_statistics()
        return {"success": True, "statistics": stats}
    except Exception as e:
        logger.exception(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top/youzi")
async def get_top_youzi(start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 20):
    """获取活跃游资排名"""
    try:
        engine = LonghubangEngine()
        df = engine.get_top_youzi(start_date, end_date, limit)

        if df.empty:
            return {"success": True, "data": [], "total": 0}

        data = []
        for _, row in df.iterrows():
            data.append({
                "游资名称": row.get("youzi_name"),
                "交易次数": row.get("trade_count"),
                "总买入": row.get("total_buy", 0),
                "总卖出": row.get("total_sell", 0),
                "净流入": row.get("total_net_inflow", 0)
            })

        return {"success": True, "data": data, "total": len(data)}
    except Exception as e:
        logger.exception(f"获取游资排名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top/stocks")
async def get_top_stocks(start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 20):
    """获取热门股票排名"""
    try:
        engine = LonghubangEngine()
        df = engine.get_top_stocks(start_date, end_date, limit)

        if df.empty:
            return {"success": True, "data": [], "total": 0}

        data = []
        for _, row in df.iterrows():
            data.append({
                "股票代码": row.get("stock_code"),
                "股票名称": row.get("stock_name"),
                "游资席位数": row.get("youzi_count"),
                "总买入": row.get("total_buy", 0),
                "总卖出": row.get("total_sell", 0),
                "净流入": row.get("total_net_inflow", 0),
                "概念": row.get("all_concepts", "")
            })

        return {"success": True, "data": data, "total": len(data)}
    except Exception as e:
        logger.exception(f"获取股票排名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data")
async def get_longhubang_data(start_date: Optional[str] = None, end_date: Optional[str] = None, stock_code: Optional[str] = None):
    """查询龙虎榜原始数据"""
    try:
        engine = LonghubangEngine()
        df = engine.database.get_longhubang_data(start_date, end_date, stock_code)

        if df.empty:
            return {"success": True, "data": [], "total": 0}

        data = []
        for _, row in df.iterrows():
            data.append({
                "日期": row.get("date"),
                "股票代码": row.get("stock_code"),
                "股票名称": row.get("stock_name"),
                "游资名称": row.get("youzi_name"),
                "营业部": row.get("yingye_bu"),
                "榜单类型": row.get("list_type"),
                "买入金额": row.get("buy_amount", 0),
                "卖出金额": row.get("sell_amount", 0),
                "净流入金额": row.get("net_inflow", 0),
                "概念": row.get("concepts")
            })

        return {"success": True, "data": data, "total": len(data)}
    except Exception as e:
        logger.exception(f"查询龙虎榜数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 评分排名 ==========

@router.get("/scoring/ranking")
async def get_scoring_ranking(date: Optional[str] = None, days: int = 5):
    """获取股票AI评分排名"""
    try:
        engine = LonghubangEngine()

        # 获取数据
        if date:
            result = engine.data_fetcher.get_longhubang_data(date)
            data_list = result.get('data', []) if result else []
        else:
            data_list = engine.data_fetcher.get_recent_days_data(days)

        if not data_list:
            return {"success": True, "data": [], "total": 0, "summary": None}

        # 执行评分
        scoring_df = engine.scoring.score_all_stocks(data_list)

        if scoring_df.empty:
            return {"success": True, "data": [], "total": 0, "summary": None}

        # 生成数据概览
        summary = engine.data_fetcher.analyze_data_summary(data_list)

        data = []
        for _, row in scoring_df.iterrows():
            data.append({
                "排名": row.get("排名"),
                "排名_display": row.get("排名_display"),
                "股票名称": row.get("股票名称"),
                "股票代码": row.get("股票代码"),
                "综合评分": row.get("综合评分"),
                "资金含金量": row.get("资金含金量"),
                "净买入额": row.get("净买入额"),
                "卖出压力": row.get("卖出压力"),
                "机构共振": row.get("机构共振"),
                "加分项": row.get("加分项"),
                "顶级游资": row.get("顶级游资"),
                "买方数": row.get("买方数"),
                "机构参与": row.get("机构参与"),
                "净流入": row.get("净流入")
            })

        return {
            "success": True,
            "data": data,
            "total": len(data),
            "summary": {
                "total_records": summary.get('total_records', 0),
                "total_stocks": summary.get('total_stocks', 0),
                "total_youzi": summary.get('total_youzi', 0),
                "total_net_inflow": summary.get('total_net_inflow', 0)
            }
        }
    except Exception as e:
        logger.exception(f"获取评分排名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scoring/explanation")
async def get_score_explanation():
    """获取评分维度说明"""
    try:
        engine = LonghubangEngine()
        explanation = engine.scoring.get_score_explanation()
        return {"success": True, "explanation": explanation}
    except Exception as e:
        logger.exception(f"获取评分说明失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
