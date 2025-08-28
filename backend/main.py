from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import atexit
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="股票分析与推荐 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 集成模块路由
from backend.routes import router as api_router
from backend.routes_streaming import streaming_router as streaming_api_router
from backend.routes_analysis_logs import analysis_logs_router
from backend.services.performance_scheduler import performance_scheduler
from backend.services.sse_manager import sse_manager
from backend.services.ai_router_bridge import unified_ai_router

app.include_router(api_router, prefix="/api")
app.include_router(streaming_api_router)  # 已包含 /api/v2 前缀
app.include_router(analysis_logs_router)  # 分析日志API

# 启动性能调度器
@app.on_event("startup")
async def startup_event():
    """App启动时的初始化"""
    # 启动性能缓存定时任务
    performance_scheduler.start()
    print("[系统] 性能缓存调度器已启动")
    
    # 初始化流式推荐系统
    print("[系统] 流式推荐系统已初始化")
    print("[系统] AI路由器桥接已加载")
    
    # 启动SSE连接清理任务
    import asyncio
    asyncio.create_task(cleanup_sse_connections())
    print("[系统] SSE连接清理任务已启动")

@app.on_event("shutdown")
async def shutdown_event():
    """App关闭时的清理工作"""
    # 停止性能缓存定时任务
    performance_scheduler.stop()
    print("[系统] 性能缓存调度器已停止")
    
    # 清理SSE连接
    await sse_manager.cleanup_dead_connections()
    print("[系统] SSE连接已清理")

# SSE连接清理任务
async def cleanup_sse_connections():
    """定期清理死连接"""
    import asyncio
    while True:
        try:
            await sse_manager.cleanup_dead_connections()
            await asyncio.sleep(60)  # 每分钟清理一次
        except Exception as e:
            print(f"[错误] SSE清理任务异常: {e}")

# 注册程序退出时的清理函数
def cleanup():
    performance_scheduler.stop()

atexit.register(cleanup)

class StockQuery(BaseModel):
    symbol: str
    period: Optional[str] = "1y"

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/config/ai")
def get_ai_config():
    return {
        "default_provider": os.getenv("DEFAULT_AI_PROVIDER", "deepseek"),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "deepseek_model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-pro"),
    }

@app.get("/stocks/recommendations")
def get_recommendations(limit: int = Query(10, ge=1, le=50)):
    # TODO: 调用分析引擎与AI模型生成推荐
    return {"recommendations": [], "limit": limit}

@app.post("/stocks/analyze")
def analyze_stock(query: StockQuery):
    # TODO: 调用数据获取与分析逻辑返回买入建议
    return {"symbol": query.symbol.upper(), "period": query.period, "recommend": "hold", "confidence": 0.5}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8000)))