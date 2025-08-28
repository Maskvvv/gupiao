"""
流式推荐引擎辅助方法
包含分析、评分和数据库操作等工具方法
"""
import json
import logging
import os
from typing import Dict, Any, List, Optional
from backend.models.streaming_models import (
    RecommendationTask, RecommendationResult, TaskProgress, SessionLocal, now_bj
)
from .confidence_fusion import extract_confidence_and_fusion

# 从环境变量获取投资建议阈值配置
BUY_THRESHOLD = float(os.getenv("BUY_THRESHOLD", "7.0"))
HOLD_THRESHOLD = float(os.getenv("HOLD_THRESHOLD", "4.0"))

# 初始化时打印配置值
print(f"[CONFIG] BUY_THRESHOLD = {BUY_THRESHOLD}")
print(f"[CONFIG] HOLD_THRESHOLD = {HOLD_THRESHOLD}")

logger = logging.getLogger(__name__)

class StreamingEngineUtils:
    """流式引擎工具类"""
    
    def _build_analysis_prompt(self, symbol: str, technical_analysis: dict, 
                              stock_data, weights: dict, context_keyword: str = None) -> str:
        """构建AI分析提示词"""
        closes = stock_data.get("close") if stock_data is not None else None
        last_close = float(closes.iloc[-1]) if closes is not None and len(closes) > 0 else None
        
        # 计算价格变化
        pct = lambda n: (float(closes.iloc[-1]) / float(closes.iloc[-n]) - 1.0) * 100 if closes is not None and len(closes) >= n else None
        chg_5 = pct(5)
        chg_20 = pct(20)
        chg_60 = pct(60)
        
        # 技术指标
        ma20 = technical_analysis.get('ma20')
        ma60 = technical_analysis.get('ma60')
        rsi14 = technical_analysis.get('rsi14')
        macd = technical_analysis.get('macd')
        signal = technical_analysis.get('signal')
        score = technical_analysis.get('score')
        action = technical_analysis.get('action')
        
        fmt = lambda v, d: (f"{v:.2f}" if isinstance(v, (int, float)) else d)
        
        lines = [
            f"请对A股股票 {symbol} 进行多维度投资分析，并给出结论。",
            ""
        ]
        
        if context_keyword:
            lines.extend([
                f"【关键词背景】此股票通过关键词 '{context_keyword}' 筛选得出，请重点分析其与该关键词的相关性。",
                ""
            ])
        
        lines.extend([
            "【分析权重配置】",
            f"- 技术面权重: {weights.get('technical', 0.4)*100:.0f}%",
            f"- 宏观情绪权重: {weights.get('macro_sentiment', 0.35)*100:.0f}%", 
            f"- 新闻事件权重: {weights.get('news_events', 0.25)*100:.0f}%",
            "",
            "【已知技术指标】",
            f"- MA20: {fmt(ma20, 'N/A')}  |  MA60: {fmt(ma60, 'N/A')}",
            f"- RSI(14): {fmt(rsi14, 'N/A')}  |  MACD: {fmt(macd, 'N/A')}  |  Signal: {fmt(signal, 'N/A')}",
            f"- 技术评分: {fmt(score, 'N/A')}  |  技术面建议: {action or 'N/A'}",
            "",
            "【价格表现】",
            f"- 最新收盘价: {fmt(last_close, 'N/A')}",
            f"- 近5/20/60日涨跌幅(%): {fmt(chg_5, 'N/A')} / {fmt(chg_20, 'N/A')} / {fmt(chg_60, 'N/A')}",
            "",
            "请按以下结构输出：",
            "1) 技术面分析：结合均线趋势、动量指标",
            "2) 市场情绪/宏观分析：市场波动、政策影响",
            "3) 新闻/事件分析：公司公告、行业动态",
            "4) 风险点：主要风险因素",
            "5) 最终建议：买入/持有/卖出（信心0-10）",
            "",
            "格式要求：",
            "- 第一行：摘要 | 建议：xxx（信心y/10）| 理由",
            "- 正文：控制在200字以内",
            "- 最后一行：最终建议：xxx（信心y/10）| 理由：...",
        ])
        
        return "\n".join(lines)
    
    def _extract_ai_scores(self, ai_analysis: str) -> dict:
        """从AI分析中提取分数和信心度"""
        try:
            temp_analysis = {"ai_advice": ai_analysis}
            result = extract_confidence_and_fusion(temp_analysis, ai_analysis)
            return {
                'confidence': result.get('ai_confidence', 0),
                'reasoning': ai_analysis
            }
        except Exception as e:
            logger.warning(f"提取AI分数失败: {e}")
            return {'confidence': 0, 'reasoning': ai_analysis}
    
    def _calculate_fusion_score(self, technical_score: float, ai_confidence: float, weights: dict) -> float:
        """计算融合分数（技术分 + AI信心度的加权平均）"""
        # 从权重配置中获取技术分权重，如果没有ai_confidence权重，则用(1-technical)作为AI权重
        tech_weight = weights.get('technical', 0.6)
        ai_weight = weights.get('ai_confidence')
        
        # 如果没有明确的ai_confidence权重，使用(1-technical)作为AI权重
        if ai_weight is None:
            ai_weight = 1.0 - tech_weight
        
        # 确保权重在合理范围内
        tech_weight = max(0.0, min(1.0, tech_weight))
        ai_weight = max(0.0, min(1.0, ai_weight))
        
        # 标准化分数到0-10范围
        # 技术分从0-1范围映射到0-10范围（用于融合分计算）
        technical_normalized = max(0, min(10, technical_score * 10.0))
        # AI信心度已经是0-10范围
        ai_normalized = max(0, min(10, ai_confidence))
        
        fusion_score = technical_normalized * tech_weight + ai_normalized * ai_weight
        
        # 添加调试日志
        logger.debug(f"融合分计算: 技术分{technical_score:.3f}(标准化{technical_normalized:.1f}) * {tech_weight:.2f} + AI信心{ai_confidence:.1f} * {ai_weight:.2f} = {fusion_score:.2f}")
        
        return max(0, min(10, fusion_score))
    
    def _determine_action(self, fusion_score: float) -> str:
        """根据融合分数确定投资建议"""
        if fusion_score >= BUY_THRESHOLD:
            return "buy"
        elif fusion_score >= HOLD_THRESHOLD:
            return "hold"
        else:
            return "sell"
    
    def _generate_summary(self, technical_analysis: dict, ai_scores: dict) -> str:
        """生成股票分析摘要"""
        action = technical_analysis.get('action', 'unknown')
        tech_score = technical_analysis.get('score', 0)
        ai_confidence = ai_scores.get('confidence', 0)
        
        # 技术分保持原始0-1范围显示（用于摘要）
        tech_score_display = tech_score if tech_score is not None else 0
        
        return f"技术面{action}信号(评分{tech_score_display:.2f})，AI信心度{ai_confidence:.1f}/10"
    
    def _extract_key_factors(self, ai_analysis: str) -> list:
        """从AI分析中提取关键因子"""
        factors = []
        if "技术面" in ai_analysis:
            factors.append("技术面分析")
        if "市场情绪" in ai_analysis or "宏观" in ai_analysis:
            factors.append("市场情绪")
        if "新闻" in ai_analysis or "事件" in ai_analysis:
            factors.append("新闻事件")
        if "风险" in ai_analysis:
            factors.append("风险评估")
        return factors
    
    def _get_stock_name(self, symbol: str) -> str:
        """获取股票名称"""
        try:
            import akshare as ak
            stock_info = ak.stock_info_a_code_name()
            code_name_map = dict(zip(stock_info['code'], stock_info['name']))
            return code_name_map.get(symbol, f"股票{symbol}")
        except:
            return f"股票{symbol}"
    
    # 数据库操作方法
    async def _get_task(self, task_id: str) -> Optional[RecommendationTask]:
        """获取任务信息"""
        with SessionLocal() as db:
            return db.query(RecommendationTask).filter(RecommendationTask.id == task_id).first()
    
    async def _update_task_status(self, task_id: str, status: str, **kwargs):
        """更新任务状态"""
        with SessionLocal() as db:
            task = db.query(RecommendationTask).filter(RecommendationTask.id == task_id).first()
            if task:
                task.status = status
                task.updated_at = now_bj()
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                db.commit()
    
    async def _update_task_total_symbols(self, task_id: str, total: int):
        """更新任务总股票数"""
        with SessionLocal() as db:
            task = db.query(RecommendationTask).filter(RecommendationTask.id == task_id).first()
            if task:
                task.total_symbols = total
                task.updated_at = now_bj()
                db.commit()
    
    async def _update_task_current_symbol(self, task_id: str, symbol: str):
        """更新当前处理股票"""
        with SessionLocal() as db:
            task = db.query(RecommendationTask).filter(RecommendationTask.id == task_id).first()
            if task:
                task.current_symbol = symbol
                task.updated_at = now_bj()
                db.commit()
    
    async def _update_task_progress(self, task_id: str, progress: float, completed: int):
        """更新任务进度"""
        with SessionLocal() as db:
            task = db.query(RecommendationTask).filter(RecommendationTask.id == task_id).first()
            if task:
                task.progress_percent = progress
                task.completed_symbols = completed
                task.updated_at = now_bj()
                db.commit()
    
    async def _increment_successful_count(self, task_id: str):
        """增加成功计数"""
        with SessionLocal() as db:
            task = db.query(RecommendationTask).filter(RecommendationTask.id == task_id).first()
            if task:
                task.successful_count += 1
                task.updated_at = now_bj()
                db.commit()
    
    async def _increment_failed_count(self, task_id: str):
        """增加失败计数"""
        with SessionLocal() as db:
            task = db.query(RecommendationTask).filter(RecommendationTask.id == task_id).first()
            if task:
                task.failed_count += 1
                task.updated_at = now_bj()
                db.commit()
    
    async def _finalize_task(self, task_id: str):
        """完成任务"""
        with SessionLocal() as db:
            task = db.query(RecommendationTask).filter(RecommendationTask.id == task_id).first()
            if task:
                task.status = 'completed'
                task.completed_at = now_bj()
                task.progress_percent = 100.0
                
                # 计算执行时间
                if task.started_at:
                    execution_time = (task.completed_at - task.started_at).total_seconds()
                    task.execution_time_seconds = execution_time
                
                # 统计最终推荐数
                final_count = db.query(RecommendationResult).filter(
                    RecommendationResult.task_id == task_id,
                    RecommendationResult.is_recommended == True
                ).count()
                task.final_recommendations = final_count
                
                task.updated_at = now_bj()
                db.commit()
    
    async def _handle_task_error(self, task_id: str, error_message: str):
        """处理任务错误"""
        with SessionLocal() as db:
            task = db.query(RecommendationTask).filter(RecommendationTask.id == task_id).first()
            if task:
                task.status = 'failed'
                task.error_message = error_message
                task.updated_at = now_bj()
                db.commit()
    
    async def _rank_and_select_recommendations(self, task_id: str, results: List[dict], max_count: int = None) -> List[dict]:
        """排序并选择推荐结果"""
        if not results:
            return []
        
        # 按融合分数排序
        sorted_results = sorted(results, key=lambda x: x.get('final_score', 0), reverse=True)
        
        # 如果没有指定最大数量，取前50%
        if max_count is None:
            max_count = max(1, len(sorted_results) // 2)
        
        # 标记推荐股票
        for i, result in enumerate(sorted_results):
            result['rank_in_task'] = i + 1
            result['is_recommended'] = i < max_count
            if result['is_recommended']:
                result['recommendation_reason'] = f"综合评分排名第{i+1}，融合分数{result['final_score']:.2f}"
        
        return sorted_results
    
    async def _save_task_results(self, task_id: str, results: List[dict]):
        """保存任务结果到数据库"""
        with SessionLocal() as db:
            for result in results:
                db_result = RecommendationResult(
                    task_id=task_id,
                    symbol=result['symbol'],
                    name=result.get('name'),
                    technical_score=result.get('technical_score'),
                    ai_score=result.get('ai_score'),
                    fusion_score=result.get('fusion_score'),
                    final_score=result.get('final_score'),
                    action=result.get('action'),
                    ai_analysis=result.get('ai_analysis'),
                    ai_confidence=result.get('ai_confidence'),
                    ai_reasoning=result.get('ai_reasoning'),
                    technical_indicators=result.get('technical_indicators'),
                    summary=result.get('summary'),
                    key_factors=result.get('key_factors'),
                    rank_in_task=result.get('rank_in_task'),
                    is_recommended=result.get('is_recommended', False),
                    recommendation_reason=result.get('recommendation_reason'),
                    current_price=result.get('current_price'),
                    analyzed_at=result.get('analyzed_at', now_bj())
                )
                db.add(db_result)
            
            db.commit()
            logger.info(f"✅ 保存了 {len(results)} 个分析结果到数据库")