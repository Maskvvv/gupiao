"""
流式推荐系统API端点
提供任务创建、状态查询、流式获取等功能
"""
import uuid
from fastapi import APIRouter, HTTPException, Request, Query, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging
import uuid

# 导入服务组件
from backend.services.task_manager import task_manager
from backend.services.sse_manager import sse_manager, sse_handler

logger = logging.getLogger(__name__)

# 创建路由器
streaming_router = APIRouter(prefix="/api/v2", tags=["streaming-recommendations"])

# ===== 请求模型 =====

class AIRecommendationRequest(BaseModel):
    """AI推荐请求"""
    symbols: List[str]
    period: str = "1y"
    weights: Optional[Dict[str, float]] = None
    ai_config: Optional[Dict[str, Any]] = None
    priority: int = 5

class KeywordRecommendationRequest(BaseModel):
    """关键词推荐请求"""
    keyword: str
    period: str = "1y"
    max_candidates: int = 5
    weights: Optional[Dict[str, float]] = None
    filter_config: Optional[Dict[str, Any]] = None
    ai_config: Optional[Dict[str, Any]] = None
    priority: int = 5

class MarketRecommendationRequest(BaseModel):
    """全市场推荐请求"""
    period: str = "1y"
    max_candidates: int = 50
    weights: Optional[Dict[str, float]] = None
    filter_config: Optional[Dict[str, Any]] = None
    ai_config: Optional[Dict[str, Any]] = None
    priority: int = 5

class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str
    stream_url: str
    status: str
    message: str

# ===== 任务创建端点 =====

@streaming_router.post("/recommend/ai", response_model=TaskResponse)
async def create_ai_recommendation_task(request: AIRecommendationRequest):
    """创建AI推荐任务"""
    try:
        task_id = await task_manager.create_ai_recommendation_task(
            symbols=request.symbols,
            period=request.period,
            weights=request.weights,
            ai_config=request.ai_config,
            priority=request.priority
        )
        
        stream_url = f"/api/v2/stream/{task_id}"
        
        return TaskResponse(
            task_id=task_id,
            stream_url=stream_url,
            status="pending",
            message=f"AI推荐任务已创建，分析 {len(request.symbols)} 只股票"
        )
        
    except Exception as e:
        logger.error(f"❌ 创建AI推荐任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

@streaming_router.post("/recommend/keyword", response_model=TaskResponse)
async def create_keyword_recommendation_task(request: KeywordRecommendationRequest):
    """创建关键词推荐任务"""
    try:
        task_id = await task_manager.create_keyword_recommendation_task(
            keyword=request.keyword,
            period=request.period,
            max_candidates=request.max_candidates,
            weights=request.weights,
            filter_config=request.filter_config,
            ai_config=request.ai_config,
            priority=request.priority
        )
        
        stream_url = f"/api/v2/stream/{task_id}"
        
        return TaskResponse(
            task_id=task_id,
            stream_url=stream_url,
            status="pending",
            message=f"关键词推荐任务已创建，关键词: {request.keyword}"
        )
        
    except Exception as e:
        logger.error(f"❌ 创建关键词推荐任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

@streaming_router.post("/recommend/market", response_model=TaskResponse)
async def create_market_recommendation_task(request: MarketRecommendationRequest):
    """创建全市场推荐任务"""
    try:
        task_id = await task_manager.create_market_recommendation_task(
            period=request.period,
            max_candidates=request.max_candidates,
            weights=request.weights,
            filter_config=request.filter_config,
            ai_config=request.ai_config,
            priority=request.priority
        )
        
        stream_url = f"/api/v2/stream/{task_id}"
        
        return TaskResponse(
            task_id=task_id,
            stream_url=stream_url,
            status="pending",
            message=f"全市场推荐任务已创建，最大候选数: {request.max_candidates}"
        )
        
    except Exception as e:
        logger.error(f"❌ 创建全市场推荐任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

# ===== 任务管理端点 =====

@streaming_router.post("/tasks/{task_id}/start")
async def start_task(task_id: str = Path(..., description="任务ID")):
    """启动任务执行"""
    try:
        success = await task_manager.start_task(task_id)
        if success:
            return {"message": "任务已启动", "task_id": task_id}
        else:
            raise HTTPException(status_code=400, detail="任务启动失败")
    except Exception as e:
        logger.error(f"❌ 启动任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动任务失败: {str(e)}")

@streaming_router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str = Path(..., description="任务ID")):
    """取消任务"""
    try:
        success = await task_manager.cancel_task(task_id)
        if success:
            return {"message": "任务已取消", "task_id": task_id}
        else:
            raise HTTPException(status_code=400, detail="任务取消失败")
    except Exception as e:
        logger.error(f"❌ 取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")

@streaming_router.post("/tasks/{task_id}/retry")
async def retry_task(task_id: str = Path(..., description="任务ID")):
    """重试任务"""
    try:
        success = await task_manager.retry_task(task_id)
        if success:
            return {"message": "任务已重置为待执行状态", "task_id": task_id}
        else:
            raise HTTPException(status_code=400, detail="任务重试失败")
    except Exception as e:
        logger.error(f"❌ 重试任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"重试任务失败: {str(e)}")

# ===== 查询端点 =====

@streaming_router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str = Path(..., description="任务ID")):
    """获取任务状态"""
    try:
        status = await task_manager.get_task_status(task_id)
        if status is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")

@streaming_router.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(None, description="任务状态过滤"),
    task_type: Optional[str] = Query(None, description="任务类型过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """获取任务列表"""
    try:
        return await task_manager.list_tasks(
            status=status,
            task_type=task_type,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"❌ 获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")

@streaming_router.get("/tasks/{task_id}/results")
async def get_task_results(
    task_id: str = Path(..., description="任务ID"),
    recommended_only: bool = Query(False, description="仅返回推荐结果"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制")
):
    """获取任务结果"""
    try:
        results = await task_manager.get_task_results(
            task_id=task_id,
            recommended_only=recommended_only,
            limit=limit
        )
        return {"task_id": task_id, "results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"❌ 获取任务结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务结果失败: {str(e)}")

@streaming_router.get("/tasks/{task_id}/progress")
async def get_task_progress(
    task_id: str = Path(..., description="任务ID"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制")
):
    """获取任务执行进度记录"""
    try:
        progress = await task_manager.get_task_progress(
            task_id=task_id,
            limit=limit
        )
        return {"task_id": task_id, "progress": progress, "count": len(progress)}
    except Exception as e:
        logger.error(f"❌ 获取任务进度失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务进度失败: {str(e)}")

# ===== 流式端点 =====

@streaming_router.get("/stream/{task_id}")
async def stream_task_progress(
    request: Request,
    task_id: str = Path(..., description="任务ID"),
    client_id: Optional[str] = Query(None, description="客户端ID")
):
    """流式获取任务进度"""
    # 生成客户端ID（如果未提供）
    if not client_id:
        client_id = str(uuid.uuid4())
    
    try:
        # 验证任务是否存在
        task_status = await task_manager.get_task_status(task_id)
        if task_status is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 创建SSE流
        return await sse_handler.create_event_stream(task_id, client_id, request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建流式连接失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建流式连接失败: {str(e)}")

@streaming_router.get("/tasks/{task_id}/stream")
async def stream_task_progress_standard(
    request: Request,
    task_id: str = Path(..., description="任务ID"),
    client_id: Optional[str] = Query(None, description="客户端ID")
):
    """流式获取任务进度（标准路径）"""
    # 直接调用原有的处理方法
    return await stream_task_progress(request, task_id, client_id)

# ===== 一键启动端点 =====

@streaming_router.post("/recommend/ai/start", response_model=TaskResponse)
async def create_and_start_ai_recommendation(request: AIRecommendationRequest):
    """创建并立即启动AI推荐任务"""
    try:
        # 创建任务
        task_id = await task_manager.create_ai_recommendation_task(
            symbols=request.symbols,
            period=request.period,
            weights=request.weights,
            ai_config=request.ai_config,
            priority=request.priority
        )
        
        # 立即启动任务
        success = await task_manager.start_task(task_id)
        if not success:
            raise HTTPException(status_code=500, detail="任务创建成功但启动失败")
        
        stream_url = f"/api/v2/stream/{task_id}"
        
        return TaskResponse(
            task_id=task_id,
            stream_url=stream_url,
            status="running",
            message=f"AI推荐任务已创建并启动，分析 {len(request.symbols)} 只股票"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建并启动AI推荐任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建并启动任务失败: {str(e)}")

@streaming_router.post("/recommend/keyword/start", response_model=TaskResponse)
async def create_and_start_keyword_recommendation(request: KeywordRecommendationRequest):
    """创建并立即启动关键词推荐任务"""
    try:
        # 创建任务
        task_id = await task_manager.create_keyword_recommendation_task(
            keyword=request.keyword,
            period=request.period,
            max_candidates=request.max_candidates,
            weights=request.weights,
            filter_config=request.filter_config,
            ai_config=request.ai_config,
            priority=request.priority
        )
        
        # 立即启动任务
        success = await task_manager.start_task(task_id)
        if not success:
            raise HTTPException(status_code=500, detail="任务创建成功但启动失败")
        
        stream_url = f"/api/v2/stream/{task_id}"
        
        return TaskResponse(
            task_id=task_id,
            stream_url=stream_url,
            status="running",
            message=f"关键词推荐任务已创建并启动，关键词: {request.keyword}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建并启动关键词推荐任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建并启动任务失败: {str(e)}")

# ===== 系统状态端点 =====

@streaming_router.get("/system/status")
async def get_system_status():
    """获取系统状态"""
    try:
        running_count = task_manager.get_running_task_count()
        running_tasks = task_manager.get_running_task_ids()
        connection_counts = sse_manager.get_task_connection_counts()
        
        return {
            "running_tasks": running_count,
            "running_task_ids": running_tasks,
            "total_connections": sse_manager.get_connection_count(),
            "task_connections": connection_counts,
            "max_concurrent_tasks": task_manager.max_concurrent_tasks,
            "system_health": "healthy"
        }
    except Exception as e:
        logger.error(f"❌ 获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")

# ===== 兼容性端点 =====

@streaming_router.post("/legacy/analyze")
async def legacy_analyze_compatibility(request: AIRecommendationRequest):
    """兼容原有分析接口"""
    try:
        # 创建并启动任务
        response = await create_and_start_ai_recommendation(request)
        
        # 返回兼容格式
        return {
            "task_id": response.task_id,
            "stream_url": response.stream_url,
            "status": "started",
            "symbols": request.symbols,
            "message": "任务已启动，请使用stream_url获取实时进度"
        }
        
    except Exception as e:
        logger.error(f"❌ 兼容性分析接口失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")