from fastapi import APIRouter, Query
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from .routes import SessionLocal, Recommendation, RecommendationItem

rec_router = APIRouter()

@rec_router.get("/recommendations/history")
def get_recommendation_history(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    recommend_type: Optional[str] = Query(None, description="推荐类型 manual/market_wide/keyword")
):
    """查询推荐历史记录"""
    with SessionLocal() as db:
        query = db.query(Recommendation)
        
        # 日期过滤
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(Recommendation.created_at >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                query = query.filter(Recommendation.created_at < end_dt)
            except ValueError:
                pass
        
        # 类型过滤
        if recommend_type:
            query = query.filter(Recommendation.recommend_type == recommend_type)
        
        # 分页
        total = query.count()
        records = query.order_by(Recommendation.created_at.desc())\
                      .offset((page - 1) * page_size)\
                      .limit(page_size)\
                      .all()
        
        # 格式化返回
        result = []
        for rec in records:
            result.append({
                "id": rec.id,
                "created_at": rec.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "period": rec.period,
                "total_candidates": rec.total_candidates,
                "top_n": rec.top_n,
                "recommend_type": getattr(rec, "recommend_type", None),
                "status": "done",
                "summary": f"从{rec.total_candidates}只候选股票中推荐{rec.top_n}只"
            })
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "records": result
        }

@rec_router.get("/recommendations/{rec_id}/details")
def get_recommendation_details(rec_id: int):
    """查询推荐详情（包含具体股票列表）"""
    with SessionLocal() as db:
        rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
        if not rec:
            return {"error": "推荐记录不存在"}
        
        items = db.query(RecommendationItem)\
                  .filter(RecommendationItem.rec_id == rec_id)\
                  .order_by(RecommendationItem.score.desc())\
                  .all()
        
        return {
            "id": rec.id,
            "created_at": rec.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "period": rec.period,
            "total_candidates": rec.total_candidates,
            "items": [{
                "股票代码": item.symbol,
                "股票名称": item.name,
                "评分": item.score,
                "建议动作": item.action,
                "理由简述": item.reason_brief,
                "AI详细分析": item.ai_advice or "无AI分析",
                "AI信心": (round(float(item.ai_confidence), 2) if item.ai_confidence is not None else None),
                "AI信心原文": item.ai_confidence_raw,
                "融合分": (round(float(item.fusion_score), 2) if item.fusion_score is not None else None),
            } for item in items]
         }

@rec_router.delete("/recommendations/{rec_id}")
def delete_recommendation(rec_id: int):
    """删除推荐记录（级联删除明细）"""
    with SessionLocal() as db:
        rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
        if not rec:
            return {"error": "推荐记录不存在"}
        
        db.delete(rec)
        db.commit()
        return {"message": f"推荐记录 {rec_id} 已删除"}