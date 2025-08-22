from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from .services.data_fetcher import DataFetcher
from .services.analyzer import basic_analysis
from .services.ai_router import AIRouter, AIRequest
from .services.enhanced_analyzer import EnhancedAnalyzer

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# 新增：持久化相关
import json
# 补充：异步任务与任务ID依赖
import threading
import uuid

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

# 自选股票表
class Watchlist(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(16), unique=True, index=True, nullable=False)
    name = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

# 股票分析记录表
class AnalysisRecord(Base):
    __tablename__ = "analysis_records"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(16), index=True, nullable=False)
    score = Column(Float)
    action = Column(String(16))
    reason_brief = Column(Text)
    ai_advice = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

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
    # AI参数
    provider: Optional[str] = None
    temperature: Optional[float] = None
    api_key: Optional[str] = None

class KeywordRecommendationRequest(BaseModel):
    keyword: str
    period: str = "1y"
    max_candidates: int = 5
    weights: Optional[Dict[str, float]] = None
    exclude_st: bool = True
    min_market_cap: Optional[float] = None
    # AI参数
    provider: Optional[str] = None
    temperature: Optional[float] = None
    api_key: Optional[str] = None

# 新增：自选相关请求模型
class WatchlistAddRequest(BaseModel):
    symbol: str

class WatchlistBatchAnalyzeRequest(BaseModel):
    symbols: Optional[List[str]] = None
    period: str = "1y"
    weights: Optional[Dict[str, float]] = None
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
            weights=req.weights,
            ai_params={
                "provider": req.provider,
                "temperature": req.temperature,
                "api_key": req.api_key,
            },
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

# 新增：持久化相关
PROGRESS_STORE: Dict[str, Dict[str, Any]] = {}

@router.post("/recommend/start")
def recommend_start(req: RecommendationRequest):
    """启动手动推荐任务，返回task_id用于查询进度与结果"""
    task_id = uuid.uuid4().hex
    PROGRESS_STORE[task_id] = {"status": "running", "done": 0, "total": 0, "error": None}

    def worker(req_obj: RecommendationRequest, task: str):
        analyzer = EnhancedAnalyzer()
        fetcher = DataFetcher()
        try:
            # 进度回调：更新完成数和总数
            def on_progress(done: int, total: int):
                PROGRESS_STORE[task].update({"done": done, "total": total})
            
            # 使用bulk_analyze批量分析输入的股票列表
            analyses = analyzer.bulk_analyze(
                symbols=req_obj.symbols,
                period=req_obj.period,
                weights=req_obj.weights,
                ai_params={
                    "provider": req_obj.provider,
                    "temperature": req_obj.temperature,
                    "api_key": req_obj.api_key,
                },
                progress_callback=on_progress,
            )
            
            # 构造候选并持久化（复用现有逻辑）
            candidates = []
            for analysis in analyses:
                if analysis.get("valid"):
                    symbol = analysis.get("symbol")
                    info = fetcher.get_stock_info(symbol)
                    stock_name = (info.get('股票简称') if info else None) or f"股票{symbol}"
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
            
            candidates.sort(key=lambda x: x["评分"], reverse=True)
            desired = 10 if len(candidates) >= 10 else (5 if len(candidates) >= 5 else len(candidates))
            top_list = candidates[:desired]
            top_n = len(top_list)

            rec_id = None
            if top_list:
                with SessionLocal() as db:
                    rec = Recommendation(
                        created_at=datetime.utcnow(),
                        period=req_obj.period,
                        total_candidates=len(candidates),
                        top_n=top_n,
                        weights_config=json.dumps(req_obj.weights) if req.weights else None,
                        recommend_type="manual"
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
            
            for it in top_list:
                it.pop("_ai_advice", None)
            
            PROGRESS_STORE[task].update({
                "status": "done",
                "result": {
                    "recommendations": top_list,
                    "rec_id": rec_id,
                }
            })
        except Exception as e:
            PROGRESS_STORE[task].update({"status": "error", "error": str(e)})

    threading.Thread(target=worker, args=(req, task_id), daemon=True).start()
    return {"task_id": task_id}

@router.get("/recommend/status/{task_id}")
def recommend_status(task_id: str):
    info = PROGRESS_STORE.get(task_id)
    if not info:
        return {"status": "not_found"}
    done = info.get("done", 0)
    total = info.get("total", 0) or 1
    percent = int(done * 100 / total) if total else 0
    return {"status": info.get("status"), "done": done, "total": total, "percent": percent}

@router.get("/recommend/result/{task_id}")
def recommend_result(task_id: str):
    info = PROGRESS_STORE.get(task_id)
    if not info:
        return {"status": "not_found"}
    if info.get("status") == "done":
        return info.get("result", {})
    if info.get("status") == "error":
        return {"error": info.get("error")}
    return {"status": info.get("status")}

@router.post("/recommend/market/start")
def recommend_market_start(req: MarketRecommendationRequest):
    """启动全市场自动推荐任务，返回task_id用于查询进度与结果"""
    task_id = uuid.uuid4().hex
    PROGRESS_STORE[task_id] = {"status": "running", "done": 0, "total": 0, "error": None}

    def worker(req_obj: MarketRecommendationRequest, task: str):
        analyzer = EnhancedAnalyzer()
        fetcher = DataFetcher()
        try:
            # 进度回调：更新完成数和总数
            def on_progress(done: int, total: int):
                PROGRESS_STORE[task].update({"done": done, "total": total})
            analyses = analyzer.auto_screen_market(
                max_candidates=req.max_candidates,
                weights=req.weights,
                ai_params={
                    "provider": req.provider,
                    "temperature": req.temperature,
                    "api_key": req.api_key,
                },
                progress_callback=on_progress,
            )
            # 构造候选并持久化（复用现有逻辑）
            candidates = []
            for analysis in analyses:
                if analysis.get("valid"):
                    symbol = analysis.get("symbol")
                    info = fetcher.get_stock_info(symbol)
                    stock_name = (info.get('股票简称') if info else None) or f"股票{symbol}"
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
            candidates.sort(key=lambda x: x["评分"], reverse=True)
            desired = 10 if len(candidates) >= 10 else (5 if len(candidates) >= 5 else len(candidates))
            top_list = candidates[:desired]
            top_n = len(top_list)

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
            for it in top_list:
                it.pop("_ai_advice", None)
            PROGRESS_STORE[task].update({
                "status": "done",
                "result": {
                    "recommendations": top_list,
                    "rec_id": rec_id,
                    "total_screened": len(candidates),
                    "weights_used": req.weights or analyzer.default_weights,
                }
            })
        except Exception as e:
            PROGRESS_STORE[task].update({"status": "error", "error": str(e)})

    threading.Thread(target=worker, args=(req, task_id), daemon=True).start()
    return {"task_id": task_id}

@router.get("/recommend/market/status/{task_id}")
def recommend_market_status(task_id: str):
    info = PROGRESS_STORE.get(task_id)
    if not info:
        return {"status": "not_found"}
    done = info.get("done", 0)
    total = info.get("total", 0) or 1
    percent = int(done * 100 / total) if total else 0
    return {"status": info.get("status"), "done": done, "total": total, "percent": percent}

@router.get("/recommend/market/result/{task_id}")
def recommend_market_result(task_id: str):
    info = PROGRESS_STORE.get(task_id, {})
    if not info:
        return {"status": "not_found"}
    if info.get("status") == "done":
        return info.get("result", {})
    elif info.get("status") == "error":
        return {"error": info.get("error")}
    else:
        return {"status": info.get("status")}

# 关键词推荐异步任务接口
@router.post("/recommend/keyword/start")
def recommend_keyword_start(req: KeywordRecommendationRequest):
    task_id = str(uuid.uuid4())
    PROGRESS_STORE[task_id] = {
        "status": "running",
        "done": 0,
        "total": 0,
        "percent": 0
    }
    
    def worker(req_obj, task):
        try:
            analyzer = EnhancedAnalyzer()
            fetcher = DataFetcher()
            ai_params = {
                "provider": req_obj.provider,
                "temperature": req_obj.temperature,
                "api_key": req_obj.api_key
            }
            
            def progress_callback(done, total):
                percent = int((done / total) * 100) if total > 0 else 0
                PROGRESS_STORE[task].update({
                    "done": done,
                    "total": total,
                    "percent": percent
                })
            
            # 调用关键词筛选方法（返回的是分析结果列表，每项包含 symbol、score、action、ai_advice 等）
            analyses = analyzer.keyword_screen_market(
                keyword=req_obj.keyword,
                period=req_obj.period,
                max_candidates=req_obj.max_candidates,
                weights=req_obj.weights,
                exclude_st=req_obj.exclude_st,
                min_market_cap=req_obj.min_market_cap,
                progress_callback=progress_callback,
                ai_params=ai_params
            )
            
            # 将分析结果映射为统一的候选结构（中文字段），以便前端展示与持久化
            candidates = []
            for analysis in analyses:
                if analysis.get("valid"):
                    symbol = analysis.get("symbol")
                    info = fetcher.get_stock_info(symbol)
                    stock_name = (info.get('股票简称') if info else None) or f"股票{symbol}"
                    ai_text = (analysis.get("ai_advice") or "").strip()
                    brief = (ai_text.split("\n")[0].strip("。 .") + "。") if ai_text else (analysis.get("action_reason", "无详细理由").split("。")[0] + "。")
                    candidates.append({
                        "股票代码": symbol,
                        "股票名称": stock_name,
                        "评分": round(analysis.get("score", 0.0), 2),
                        "建议动作": analysis.get("action"),
                        "理由简述": brief,
                        "_ai_advice": ai_text,
                    })
            
            # 排序与Top-N（默认返回5只，可通过max_candidates配置）
            candidates.sort(key=lambda x: x["评分"], reverse=True)
            desired = int(req_obj.max_candidates or 5)
            top_list = candidates[:desired]
            filtered_count = len(candidates)
            
            # 保存推荐结果
            rec_id = None
            if top_list:
                with SessionLocal() as db:
                    rec = Recommendation(
                        created_at=datetime.utcnow(),
                        period=req_obj.period,
                        total_candidates=filtered_count,
                        top_n=len(top_list),
                        weights_config=json.dumps(req_obj.weights) if req_obj.weights else None,
                        recommend_type="keyword"
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
            
            # 清理内部字段
            for it in top_list:
                it.pop("_ai_advice", None)
            
            PROGRESS_STORE[task].update({
                "status": "done",
                "result": {
                    "recommendations": top_list,
                    "rec_id": rec_id,
                    "filtered_count": filtered_count
                }
            })
        except Exception as e:
            PROGRESS_STORE[task].update({"status": "error", "error": str(e)})
    
    threading.Thread(target=worker, args=(req, task_id), daemon=True).start()
    return {"task_id": task_id}

@router.get("/recommend/keyword/status/{task_id}")
def recommend_keyword_status(task_id: str):
    info = PROGRESS_STORE.get(task_id, {})
    if not info:
        return {"status": "not_found"}
    return {
        "status": info.get("status"),
        "done": info.get("done", 0),
        "total": info.get("total", 0),
        "percent": info.get("percent", 0)
    }

@router.get("/recommend/keyword/result/{task_id}")
def recommend_keyword_result(task_id: str):
    info = PROGRESS_STORE.get(task_id, {})
    if not info:
        return {"status": "not_found"}
    if info.get("status") == "done":
        return info.get("result", {})
    elif info.get("status") == "error":
        return {"error": info.get("error")}
    else:
        return {"status": info.get("status")}

# =================== 自选股票功能 ===================
@router.post("/watchlist/add")
def watchlist_add(req: WatchlistAddRequest):
    symbol = (req.symbol or "").strip()
    if not symbol:
        return {"error": "股票代码不能为空"}
    fetcher = DataFetcher()
    info = fetcher.get_stock_info(symbol)
    name = (info.get('股票简称') if info else None) or f"股票{symbol}"
    with SessionLocal() as db:
        # 若已存在则直接返回
        exists = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
        if exists:
            return {"ok": True, "symbol": symbol, "name": exists.name}
        item = Watchlist(symbol=symbol, name=name)
        db.add(item)
        db.commit()
        return {"ok": True, "symbol": symbol, "name": name}

@router.delete("/watchlist/remove/{symbol}")
def watchlist_remove(symbol: str):
    symbol = (symbol or "").strip()
    with SessionLocal() as db:
        row = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
        if not row:
            return {"ok": True, "removed": False}
        db.delete(row)
        db.commit()
        return {"ok": True, "removed": True}

@router.get("/watchlist/list")
def watchlist_list():
    results = []
    with SessionLocal() as db:
        wl = db.query(Watchlist).order_by(Watchlist.created_at.desc()).all()
        for it in wl:
            last = db.query(AnalysisRecord).filter(AnalysisRecord.symbol == it.symbol).order_by(AnalysisRecord.created_at.desc()).first()
            results.append({
                "股票代码": it.symbol,
                "股票名称": it.name,
                "综合评分": round(float(last.score), 2) if last and last.score is not None else None,
                "操作建议": last.action if last else None,
                "分析理由摘要": (last.reason_brief or "").split("。")[0] + "。" if last and last.reason_brief else None,
                "最近分析时间": last.created_at.strftime("%Y-%m-%d %H:%M:%S") if last else None
            })
    return {"items": results}

@router.post("/watchlist/analyze")
def watchlist_analyze(req: WatchlistBatchAnalyzeRequest):
    # 单股分析：当symbols为单只或未传时，要求用户传一只
    symbols = (req.symbols or [])
    if len(symbols) != 1:
        return {"error": "请仅传入一只股票进行单股分析"}
    symbol = symbols[0]
    fetcher = DataFetcher()
    df = fetcher.get_stock_data(symbol, period=req.period)
    if df is None:
        return {"error": f"无法获取{symbol}历史数据"}
    df_compatible = df.reset_index()
    df_compatible.columns = [c.lower() for c in df_compatible.columns]
    analyzer = EnhancedAnalyzer()
    ai_params = {"provider": req.provider, "temperature": req.temperature, "api_key": req.api_key}
    analysis = analyzer.analyze_with_ai(symbol, df_compatible, weights=req.weights, ai_params=ai_params)
    # 持久化分析记录
    if analysis.get("valid", True):
        reason = analysis.get("action_reason") or (analysis.get("ai_advice") or "").split("\n")[0]
        with SessionLocal() as db:
            db.add(AnalysisRecord(
                symbol=symbol,
                score=float(analysis.get("score", 0.0)) if analysis.get("score") is not None else None,
                action=analysis.get("action"),
                reason_brief=reason,
                ai_advice=analysis.get("ai_advice")
            ))
            db.commit()
    return {"symbol": symbol, "analysis": analysis}

@router.post("/watchlist/analyze/batch/start")
def watchlist_analyze_batch_start(req: WatchlistBatchAnalyzeRequest):
    task_id = str(uuid.uuid4())
    PROGRESS_STORE[task_id] = {"status": "running", "done": 0, "total": 0, "percent": 0}

    def worker(req_obj, task):
        try:
            fetcher = DataFetcher()
            analyzer = EnhancedAnalyzer()
            ai_params = {"provider": req_obj.provider, "temperature": req_obj.temperature, "api_key": req_obj.api_key}
            with SessionLocal() as db:
                if req_obj.symbols:
                    syms = [s.strip() for s in req_obj.symbols if s and s.strip()]
                else:
                    syms = [w.symbol for w in db.query(Watchlist).all()]
            total = len(syms)
            PROGRESS_STORE[task].update({"total": total})
            results = []
            done = 0
            for s in syms:
                df = fetcher.get_stock_data(s, period=req_obj.period)
                if df is None:
                    results.append({"股票代码": s, "错误": "无法获取数据"})
                    done += 1
                    PROGRESS_STORE[task].update({"done": done, "percent": int(done*100/max(total,1))})
                    continue
                df_compatible = df.reset_index()
                df_compatible.columns = [c.lower() for c in df_compatible.columns]
                analysis = analyzer.analyze_with_ai(s, df_compatible, weights=req_obj.weights, ai_params=ai_params)
                # 持久化
                if analysis.get("valid", True):
                    reason = analysis.get("action_reason") or (analysis.get("ai_advice") or "").split("\n")[0]
                    with SessionLocal() as db:
                        db.add(AnalysisRecord(
                            symbol=s,
                            score=float(analysis.get("score", 0.0)) if analysis.get("score") is not None else None,
                            action=analysis.get("action"),
                            reason_brief=reason,
                            ai_advice=analysis.get("ai_advice")
                        ))
                        db.commit()
                # 输出结构（中文字段）
                fetcher_local = DataFetcher()
                info = fetcher_local.get_stock_info(s)
                stock_name = (info.get('股票简称') if info else None) or f"股票{s}"
                results.append({
                    "股票代码": s,
                    "股票名称": stock_name,
                    "评分": round(float(analysis.get("score", 0.0)), 2) if analysis.get("score") is not None else None,
                    "建议动作": analysis.get("action"),
                    "理由简述": (analysis.get("action_reason") or (analysis.get("ai_advice") or "").split("\n")[0] or "").strip()
                })
                done += 1
                PROGRESS_STORE[task].update({"done": done, "percent": int(done*100/max(total,1))})
            PROGRESS_STORE[task].update({"status": "done", "result": {"items": results}})
        except Exception as e:
            PROGRESS_STORE[task].update({"status": "error", "error": str(e)})

    threading.Thread(target=worker, args=(req, task_id), daemon=True).start()
    return {"task_id": task_id}

@router.get("/watchlist/analyze/batch/status/{task_id}")
def watchlist_analyze_batch_status(task_id: str):
    info = PROGRESS_STORE.get(task_id, {})
    if not info:
        return {"status": "not_found"}
    return {"status": info.get("status"), "done": info.get("done", 0), "total": info.get("total", 0), "percent": info.get("percent", 0)}

@router.get("/watchlist/analyze/batch/result/{task_id}")
def watchlist_analyze_batch_result(task_id: str):
    info = PROGRESS_STORE.get(task_id, {})
    if not info:
        return {"status": "not_found"}
    if info.get("status") == "done":
        return info.get("result", {})
    elif info.get("status") == "error":
        return {"error": info.get("error")}
    else:
        return {"status": info.get("status")}
# =================== 自选股票功能 END ===================

# 新增：个股分析历史查询
@router.get("/watchlist/history/{symbol}")
def watchlist_history(symbol: str, page: int = 1, page_size: int = 20):
    symbol = (symbol or "").strip()
    if not symbol:
        return {"error": "股票代码不能为空"}
    # 分页参数边界
    page = 1 if not isinstance(page, int) or page < 1 else page
    page_size = 20 if not isinstance(page_size, int) or page_size < 1 else min(page_size, 200)
    with SessionLocal() as db:
        q = db.query(AnalysisRecord).filter(AnalysisRecord.symbol == symbol).order_by(AnalysisRecord.created_at.desc())
        total = q.count()
        recs = q.offset((page - 1) * page_size).limit(page_size).all()
        items = []
        for r in recs:
            items.append({
                "时间": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
                "综合评分": round(float(r.score), 2) if r.score is not None else None,
                "操作建议": r.action,
                "分析理由摘要": r.reason_brief,
                "AI详细分析": r.ai_advice,
            })
    return {
        "symbol": symbol,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }