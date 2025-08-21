from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Optional
from .services.data_fetcher import DataFetcher
from .services.analyzer import basic_analysis
from .services.ai_router import AIRouter, AIRequest
from .services.enhanced_analyzer import EnhancedAnalyzer

# 新增：持久化相关
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
# 补充：缺失的json导入，避免在持久化weights_config时 NameError
import json

router = APIRouter()

# ---------- 数据库初始化与模型 ----------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./a_stock_analysis.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    period = Column(String(20))
    total_candidates = Column(Integer, default=0)
    top_n = Column(Integer, default=0)
    # 新增：权重配置与推荐类型存储
    weights_config = Column(Text)  # JSON格式存储权重配置
    recommend_type = Column(String(20), default="manual")  # manual/market_wide
    items = relationship("RecommendationItem", back_populates="rec", cascade="all, delete-orphan")

class RecommendationItem(Base):
    __tablename__ = "recommendation_items"
    id = Column(Integer, primary_key=True, index=True)
    rec_id = Column(Integer, ForeignKey("recommendations.id"), index=True)
    symbol = Column(String(16), index=True)
    name = Column(String(64))
    score = Column(Float)
    action = Column(String(16))
    reason_brief = Column(Text)
    ai_advice = Column(Text)
    rec = relationship("Recommendation", back_populates="items")

# 确保表存在（幂等）
Base.metadata.create_all(engine)

# 轻量级迁移：如果是SQLite，尝试添加缺失列
try:
    if engine.url.get_backend_name() == "sqlite":
        with engine.begin() as conn:
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(recommendations)")).fetchall()}
            if "weights_config" not in cols:
                conn.execute(text("ALTER TABLE recommendations ADD COLUMN weights_config TEXT"))
            if "recommend_type" not in cols:
                conn.execute(text("ALTER TABLE recommendations ADD COLUMN recommend_type VARCHAR(20) DEFAULT 'manual'"))
except Exception as _e:
    # 迁移失败不阻塞主流程，但会在首次插入时报错提示
    pass

class RecommendationRequest(BaseModel):
    symbols: List[str]
    period: str = "1y"
    # 新增：权重配置
    weights: Optional[Dict[str, float]] = None
    # 新增：AI配置
    provider: Optional[str] = None
    temperature: Optional[float] = None
    api_key: Optional[str] = None

class MarketRecommendationRequest(BaseModel):
    period: str = "1y"
    max_candidates: int = 50
    weights: Optional[Dict[str, float]] = None
    exclude_st: bool = True
    min_market_cap: Optional[float] = None
    # 新增：AI配置
    provider: Optional[str] = None
    temperature: Optional[float] = None
    api_key: Optional[str] = None

@router.post("/analyze")
def analyze_symbol(req: RecommendationRequest):
    analyzer = EnhancedAnalyzer()
    results = []
    for s in req.symbols:
        df = DataFetcher().get_stock_data(s, period=req.period)
        if df is not None:
            # 转换列名为兼容格式
            df_compatible = df.reset_index()
            df_compatible.columns = [col.lower() for col in df_compatible.columns]
            analysis = analyzer.analyze_with_ai(
                s,
                df_compatible,
                weights=req.weights,
                ai_params={"provider": req.provider, "temperature": req.temperature, "api_key": req.api_key},
            )
            results.append({"symbol": s, **analysis})
        else:
            results.append({"symbol": s, "valid": False, "reason": "无法获取数据"})
    return {"results": results}

@router.post("/recommend")
def recommend_symbols(req: RecommendationRequest):
    fetcher = DataFetcher()
    analyzer = EnhancedAnalyzer()
    candidates = []
    for s in req.symbols:
        df = fetcher.get_stock_data(s, period=req.period)
        if df is not None:
            # 转换列名为兼容格式
            df_compatible = df.reset_index()
            df_compatible.columns = [col.lower() for col in df_compatible.columns]
            # 使用AI综合分析（包含技术面+情绪/宏观+事件）
            analysis = analyzer.analyze_with_ai(
                s,
                df_compatible,
                weights=req.weights,
                ai_params={"provider": req.provider, "temperature": req.temperature, "api_key": req.api_key},
            )
            if analysis.get("valid"):
                # 获取股票名称（尽量友好降级）
                info = fetcher.get_stock_info(s)
                stock_name = (info.get('股票简称') if info else None) or f"股票{s}"
                # 生成理由简述：优先取AI解读第一句，否则取技术理由第一句
                ai_text = (analysis.get("ai_advice") or "").strip()
                brief = (ai_text.split("\n")[0].strip("。.") + "。") if ai_text else (analysis.get("action_reason", "无详细理由").split("。")[0] + "。")
                candidates.append({
                    "股票代码": s,
                    "股票名称": stock_name,
                    "评分": round(analysis.get("score", 0.0), 2),
                    "建议动作": analysis.get("action"),
                    "理由简述": brief,
                    "_ai_advice": ai_text,  # 内部字段，便于持久化
                })

    # 如果 symbols 为空，尝试调用全市场筛选逻辑作为后备
    if not candidates and not req.symbols:
        analyses = analyzer.auto_screen_market(
            max_candidates=req.max_candidates if hasattr(req, 'max_candidates') else 50,
            weights=req.weights,
            ai_params={"provider": req.provider, "temperature": req.temperature, "api_key": req.api_key},
        )
        for analysis in analyses:
            if analysis.get("valid"):
                s = analysis.get("symbol")
                info = fetcher.get_stock_info(s)
                stock_name = (info.get('股票简称') if info else None) or f"股票{s}"
                ai_text = (analysis.get("ai_advice") or "").strip()
                brief = (ai_text.split("\n")[0].strip("。.") + "。") if ai_text else (analysis.get("action_reason", "无详细理由").split("。")[0] + "。")
                candidates.append({
                    "股票代码": s,
                    "股票名称": stock_name,
                    "评分": round(analysis.get("score", 0.0), 2),
                    "建议动作": analysis.get("action"),
                    "理由简述": brief,
                    "_ai_advice": ai_text,
                })

    # 排序并选取5-10只
    candidates.sort(key=lambda x: x["评分"], reverse=True)
    # 需求为尽量推荐5-10只；若候选不足5只，则返回实际可用数量
    desired = 10 if len(candidates) >= 10 else (5 if len(candidates) >= 5 else len(candidates))
    top_list = candidates[:desired]
    top_n = len(top_list)

    # 持久化本次推荐
    rec_id = None
    if top_list:
        with SessionLocal() as db:
            rec = Recommendation(
                created_at=datetime.utcnow(),
                period=req.period,
                total_candidates=len(candidates),
                top_n=top_n,
                weights_config=json.dumps(req.weights) if req.weights else None,
                recommend_type="manual"
            )
            db.add(rec)
            db.flush()  # 获取rec.id
            # 批量写入明细
            for item in top_list:
                db.add(RecommendationItem(
                    rec_id=rec.id,
                    symbol=item["股票代码"],
                    name=item["股票名称"],
                    score=item["评分"],
                    action=item["建议动作"],
                    reason_brief=item["理由简述"],
                    ai_advice=item.get("_ai_advice")
                ))
            db.commit()
            rec_id = rec.id

    # 输出给前端时不暴露内部字段
    for it in top_list:
        it.pop("_ai_advice", None)
    return {"recommendations": top_list, "rec_id": rec_id}

@router.post("/recommend/market")
def recommend_market_wide(req: MarketRecommendationRequest):
    """全市场自动候选池推荐"""
    analyzer = EnhancedAnalyzer()
    fetcher = DataFetcher()
    
    try:
        # 使用增强分析器的全市场筛选功能
        analyses = analyzer.auto_screen_market(
            max_candidates=req.max_candidates,
            weights=req.weights
        )
        
        candidates = []
        for analysis in analyses:
            if analysis.get("valid"):
                symbol = analysis.get("symbol")
                # 获取股票名称
                info = fetcher.get_stock_info(symbol)
                stock_name = (info.get('股票简称') if info else None) or f"股票{symbol}"
                # 生成理由简述
                ai_text = (analysis.get("ai_advice") or "").strip()
                brief = (ai_text.split("\n")[0].strip("。.") + "。") if ai_text else (analysis.get("action_reason", "无详细理由").split("。")[0] + "。")
                candidates.append({
                    "股票代码": symbol,
                    "股票名称": stock_name,
                    "评分": round(analysis.get("score", 0.0), 2),
                    "建议动作": analysis.get("action"),
                    "理由简述": brief,
                    "_ai_advice": ai_text,
                })
        
        # 排序并选取top 5-10
        candidates.sort(key=lambda x: x["评分"], reverse=True)
        desired = 10 if len(candidates) >= 10 else (5 if len(candidates) >= 5 else len(candidates))
        top_list = candidates[:desired]
        top_n = len(top_list)
        
        # 持久化
        rec_id = None
        if top_list:
            with SessionLocal() as db:
                rec = Recommendation(
                    created_at=datetime.utcnow(),
                    period=req.period,
                    total_candidates=len(candidates),
                    top_n=top_n,
                    weights_config=json.dumps(req.weights) if req.weights else None,
                    recommend_type="market_wide"
                )
                db.add(rec)
                db.flush()
                
                for item in top_list:
                    db.add(RecommendationItem(
                        rec_id=rec.id,
                        symbol=item["股票代码"],
                        name=item["股票名称"],
                        score=item["评分"],
                        action=item["建议动作"],
                        reason_brief=item["理由简述"],
                        ai_advice=item.get("_ai_advice")
                    ))
                db.commit()
                rec_id = rec.id
        
        # 移除内部字段
        for it in top_list:
            it.pop("_ai_advice", None)
            
        return {
            "recommendations": top_list, 
            "rec_id": rec_id,
            "total_screened": len(candidates),
            "weights_used": req.weights or analyzer.default_weights
        }
        
    except Exception as e:
        return {"error": f"全市场推荐失败: {str(e)}", "recommendations": []}

from fastapi import Body

@router.post("/ai")
def ai_suggest(
    prompt: str = Body(..., embed=True),
    provider: str = Body(None),
    temperature: float = Body(None),
    api_key: str = Body(None),
):
    router = AIRouter()
    return {"content": router.complete(AIRequest(prompt=prompt, provider=provider, temperature=temperature, api_key=api_key))}