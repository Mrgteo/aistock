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
    actual_entry: float
    actual_exit: float
    reason: str
    emotion: str
    ai_review: str = ""


class ReviewReq(BaseModel):
    reflections: str
    plans: str
    trades: list[Trade]
    images: list = []


@router.post("/ai_analyze")
async def ai_review(t: Trade):
    """AI复盘分析"""
    from backend.core.config import settings

    # 计算盈亏
    pnl = 0
    if t.actual_entry > 0 and t.actual_exit > 0:
        pnl = (t.actual_exit - t.actual_entry) / t.actual_entry * 100
        if t.direction == "short":
            pnl = -pnl

    dev = 0
    if t.plan_entry > 0 and t.actual_entry > 0:
        dev = (t.actual_entry - t.plan_entry) / t.plan_entry * 100

    s = "标的:" + t.symbol + " 方向:" + t.direction + "\n"
    s += "计划进:" + str(t.plan_entry) + " 实际进:" + str(t.actual_entry) + "\n"
    s += "实际出:" + str(t.actual_exit) + " 理由:" + t.reason + "\n"
    s += "请帮我复盘一下，指出优缺点和改进建议。"

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
