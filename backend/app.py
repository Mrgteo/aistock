"""
股票交易辅助系统 - FastAPI主应用
"""

import os
import sys
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.core.config import settings
from backend.routers import auth, stock, analysis, review, market, report_analysis, history, screener

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="股票交易辅助系统 - AI智能分析、选股、复盘"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
# 注意：路由内部已定义 prefix 的不再重复添加
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(stock.router, prefix="/api", tags=["股票数据"])
app.include_router(analysis.router, prefix="/api", tags=["股票分析"])
app.include_router(review.router, tags=["交易复盘"])       # 内部 prefix="/api/review"
app.include_router(market.router, prefix="/api/market", tags=["市场数据"])
app.include_router(report_analysis.router, tags=["研报分析"])  # 内部 prefix="/api/report"
app.include_router(history.router, tags=["历史记录"])        # 内部 prefix="/api/history"
app.include_router(screener.router, tags=["股票筛选"])       # 内部 prefix="/api/screener"

# 静态文件服务
cur_dir = os.path.dirname(os.path.abspath(__file__))
upload_path = os.path.join(cur_dir, "uploads")
data_path = os.path.join(cur_dir, "data")

if not os.path.exists(upload_path):
    os.makedirs(upload_path)
if not os.path.exists(data_path):
    os.makedirs(data_path)

app.mount("/uploads", StaticFiles(directory=upload_path), name="uploads")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
