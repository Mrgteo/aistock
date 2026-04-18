"""
交易复盘路由
"""

import os
import time
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel

from backend.routers.auth import get_current_user

router = APIRouter(prefix="/api/review", tags=["交易复盘"])

# 获取当前路径，用来存文件
cur_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(os.path.dirname(cur_dir), "data")
upload_path = os.path.join(os.path.dirname(cur_dir), "uploads")

# 如果没有文件夹就建一个
if not os.path.exists(data_path):
    os.makedirs(data_path)
if not os.path.exists(upload_path):
    os.makedirs(upload_path)


class Trade(BaseModel):
    id: str
    symbol: str
    direction: str
    plan_entry: float
    plan_sl: float
    plan_tp: float
    position: float = 0
    actual_entry: float
    actual_exit: float
    stop_loss_reason: str = ""
    followup_evaluation: str = ""
    reason: str
    order_type: str = "计划单"
    ai_review: str = ""


class ReviewReq(BaseModel):
    reflections: str
    plans: str
    trades: list[Trade]
    images: list = []


@router.post("/ai_analyze")
async def ai_review(t: Trade):
    """AI复盘分析"""
    import re
    from backend.core.config import settings
    from backend.routers.stock import get_code_type

    # 获取股票代码
    try:
        code, market = get_code_type(t.symbol)
        stock_code = code
    except:
        stock_code = t.symbol
        code = t.symbol

    # 获取实时价格和名称（使用Sina API）
    current_price = 0
    stock_name = t.symbol  # 默认使用用户输入的标的作为名称

    try:
        # 根据市场确定Sina代码前缀
        if ".SS" in code or market == "A股-上交所":
            sina_code = f"sh{code.replace('.SS', '')}"
        else:
            sina_code = f"sz{code.replace('.SZ', '')}"

        # 获取实时数据
        import requests as req
        headers = {"Referer": "http://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}
        res = req.get(f"https://hq.sinajs.cn/list={sina_code}", headers=headers, timeout=10)

        if res.status_code == 200 and res.text:
            text = res.text
            # 解析: var hq_str_xxx="name,open,prev_close,current,high,low,..."
            match = re.search(r'"([^"]+)"', text)
            if match:
                parts = match.group(1).split(',')
                if len(parts) > 3:
                    stock_name = parts[0]  # 名称
                    current_price = float(parts[3])  # 当前价格
    except Exception as e:
        print(f"获取实时数据失败: {e}")

    # 计算盈亏（用实时价格计算）
    pnl = 0
    if t.actual_entry > 0 and current_price > 0:
        pnl = (current_price - t.actual_entry) / t.actual_entry * 100
        if t.direction == "short":
            pnl = -pnl

    # 计算偏离度（计划入场价 vs 实际入场价）
    dev = 0
    if t.plan_entry > 0 and t.actual_entry > 0:
        dev = (t.actual_entry - t.plan_entry) / t.plan_entry * 100

    s = "【交易复盘分析】\n"
    s += f"标的: {stock_name}（{stock_code}） 方向: {'做多' if t.direction == 'long' else '做空'} 交割单属性: {t.order_type}\n"
    s += f"仓位: {t.position}成（{t.position * 10}%） 当前价: {current_price:.2f}\n"
    s += f"计划入场: {t.plan_entry:.2f} 计划止损: {t.plan_sl:.2f} 计划目标: {t.plan_tp:.2f}\n"
    s += f"实际入场: {t.actual_entry:.2f} 实际出场: {t.actual_exit:.2f}\n"
    s += f"入场理由: {t.reason}\n"
    s += f"止盈止损理由: {t.stop_loss_reason}\n"
    s += f"后续评估: {t.followup_evaluation}\n"
    s += f"当前盈亏: {pnl:.2f}% 偏离度: {dev:.2f}%\n"
    s += "请根据以上信息进行综合复盘分析，包括：交易计划执行情况、止盈止损执行合理性、仓位管理、入场时机选择、情绪控制（" + t.order_type + "）、存在的问题及改进建议。"

    data = {
        "model": settings.DEFAULT_MODEL_NAME,
        "messages": [{"role": "user", "content": s}],
        "stream": False
    }

    api_key = settings.DEEPSEEK_API_KEY or "sk-8cb3bfe75b94480a8005a87362306526"
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(
            settings.DEEPSEEK_BASE_URL + "/chat/completions",
            json=data,
            headers=headers,
            timeout=120
        )
        if r.status_code != 200:
            err_detail = r.text
            raise Exception(f"API返回错误 {r.status_code}: {err_detail[:200]}")
        ans = r.json()["choices"][0]["message"]["content"]
        return {"reply": ans, "pnl": pnl, "deviation": dev}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import requests


@router.get("/{date_str}")
async def get_review(date_str: str):
    """获取复盘数据"""
    path = data_path + "/" + date_str + ".json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.loads(f.read())
    else:
        return {"reflections": "", "plans": "", "trades": [], "images": []}


@router.post("/{date_str}")
async def save_review(date_str: str, req: ReviewReq):
    """保存复盘数据"""
    path = data_path + "/" + date_str + ".json"
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(req.model_dump(), ensure_ascii=False, indent=2))
    return {"msg": "ok"}


@router.post("/upload/{date_str}")
async def upload_image(date_str: str, file: UploadFile = File(...)):
    """上传复盘图片"""
    name = str(int(time.time())) + "_" + file.filename
    path = upload_path + "/" + name

    with open(path, "wb") as f:
        f.write(file.file.read())

    return {"url": "/uploads/" + name}
