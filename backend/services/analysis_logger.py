"""
分析过程日志记录器
用于记录推荐系统分析过程的详细日志，支持用户查看分析细节
"""
import json
import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy import text
from backend.models.streaming_models import SessionLocal, now_bj
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalysisLogger:
    """分析过程日志记录器"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.session_start_time = time.time()
        
    def _insert_log(self, log_type: str, log_level: str = 'info', **kwargs):
        """插入日志记录到数据库"""
        try:
            with SessionLocal() as db:
                log_data = {
                    'task_id': self.task_id,
                    'log_type': log_type,
                    'timestamp': now_bj(),
                    'log_level': log_level,
                    **kwargs
                }
                
                # 构建SQL插入语句
                columns = ', '.join(log_data.keys())
                placeholders = ', '.join([f':{key}' for key in log_data.keys()])
                
                sql = f"""
                INSERT INTO analysis_logs ({columns}) 
                VALUES ({placeholders})
                """
                
                db.execute(text(sql), log_data)
                db.commit()
                
        except Exception as e:
            logger.error(f"❌ 插入分析日志失败: {e}")
    
    def log_task_start(self, task_params: Dict[str, Any]):
        """记录任务开始"""
        self._insert_log(
            log_type='task_start',
            log_level='info',
            log_message=f'推荐任务开始执行: {self.task_id}',
            log_details=json.dumps(task_params, ensure_ascii=False, indent=2)
        )
    
    def log_ai_screening_start(self, keyword: str, max_candidates: int):
        """记录AI股票筛选开始"""
        self._insert_log(
            log_type='ai_screening',
            log_level='info',
            log_message=f'开始AI股票筛选: 关键词="{keyword}", 目标数量={max_candidates}',
            log_details=json.dumps({
                'keyword': keyword,
                'max_candidates': max_candidates,
                'stage': 'start'
            }, ensure_ascii=False)
        )
    
    def log_ai_screening_request(self, prompt: str, provider: str = 'openai'):
        """记录AI筛选请求"""
        start_time = time.time()
        
        self._insert_log(
            log_type='ai_screening',
            log_level='debug',
            log_message='发送AI股票筛选请求',
            ai_request_prompt=prompt,
            ai_provider=provider,
            log_details=json.dumps({
                'request_time': start_time,
                'prompt_length': len(prompt)
            }, ensure_ascii=False)
        )
        
        return start_time  # 返回开始时间用于计算耗时
    
    def log_ai_screening_response(self, response: str, provider: str, start_time: float, 
                                 recommended_stocks: List[str]):
        """记录AI筛选响应"""
        processing_time = int((time.time() - start_time) * 1000)
        
        self._insert_log(
            log_type='ai_screening',
            log_level='info',
            log_message=f'AI股票筛选完成: 筛选出{len(recommended_stocks)}只股票',
            ai_response_content=response,
            ai_provider=provider,
            ai_processing_time_ms=processing_time,
            ai_response_tokens=len(response.split()) if response else 0,
            log_details=json.dumps({
                'recommended_stocks': recommended_stocks,
                'processing_time_ms': processing_time,
                'stocks_count': len(recommended_stocks)
            }, ensure_ascii=False)
        )
    
    def log_ai_screening_fallback(self, reason: str, fallback_stocks: List[str]):
        """记录AI筛选降级策略"""
        self._insert_log(
            log_type='ai_screening',
            log_level='warning',
            log_message=f'AI筛选降级: {reason}',
            log_details=json.dumps({
                'fallback_reason': reason,
                'fallback_stocks': fallback_stocks,
                'fallback_count': len(fallback_stocks)
            }, ensure_ascii=False)
        )
    
    def log_technical_analysis_start(self, symbol: str):
        """记录技术分析开始"""
        self._insert_log(
            log_type='technical_analysis',
            log_level='info',
            stock_symbol=symbol,
            log_message=f'开始技术分析: {symbol}'
        )
    
    def log_technical_analysis_complete(self, symbol: str, technical_result: Dict[str, Any]):
        """记录技术分析完成"""
        tech_score = technical_result.get('score', 0)
        
        self._insert_log(
            log_type='technical_analysis',
            log_level='info',
            stock_symbol=symbol,
            log_message=f'技术分析完成: {symbol}, 技术分={tech_score:.2f}',
            technical_score=tech_score,
            technical_indicators=json.dumps(technical_result, ensure_ascii=False, default=str),
            technical_signals=json.dumps({
                'buy_signals': technical_result.get('buy_signals', []),
                'sell_signals': technical_result.get('sell_signals', []),
                'trend': technical_result.get('trend', 'unknown')
            }, ensure_ascii=False)
        )
    
    def log_ai_analysis_start(self, symbol: str, prompt: str):
        """记录AI深度分析开始"""
        start_time = time.time()
        
        self._insert_log(
            log_type='ai_analysis',
            log_level='info',
            stock_symbol=symbol,
            log_message=f'开始AI深度分析: {symbol}',
            ai_request_prompt=prompt,
            log_details=json.dumps({
                'analysis_start_time': start_time,
                'prompt_length': len(prompt)
            }, ensure_ascii=False)
        )
        
        return start_time
    
    def log_ai_analysis_chunk(self, symbol: str, chunk: str, accumulated_content: str):
        """记录AI分析流式数据块"""
        self._insert_log(
            log_type='ai_analysis',
            log_level='debug',
            stock_symbol=symbol,
            log_message=f'AI分析流式数据: {symbol} (长度: {len(chunk)}字符)',
            log_details=json.dumps({
                'chunk_length': len(chunk),
                'accumulated_length': len(accumulated_content),
                'chunk_content': chunk[:200]  # 只记录前200个字符
            }, ensure_ascii=False)
        )
    
    def log_ai_analysis_complete(self, symbol: str, ai_content: str, ai_scores: Dict[str, Any], 
                                start_time: float, provider: str = 'openai'):
        """记录AI分析完成"""
        processing_time = int((time.time() - start_time) * 1000)
        confidence = ai_scores.get('confidence', 0)
        
        self._insert_log(
            log_type='ai_analysis',
            log_level='info',
            stock_symbol=symbol,
            log_message=f'AI深度分析完成: {symbol}, 信心度={confidence:.2f}',
            ai_response_content=ai_content,
            ai_provider=provider,
            ai_processing_time_ms=processing_time,
            ai_response_tokens=len(ai_content.split()) if ai_content else 0,
            log_details=json.dumps({
                'ai_scores': ai_scores,
                'processing_time_ms': processing_time,
                'content_length': len(ai_content)
            }, ensure_ascii=False)
        )
    
    def log_fusion_score_calculation(self, symbol: str, tech_score: float, ai_score: float, 
                                   fusion_score: float, weights: Dict[str, float]):
        """记录融合评分计算"""
        self._insert_log(
            log_type='fusion_score',
            log_level='info',
            stock_symbol=symbol,
            log_message=f'融合评分计算: {symbol}, 最终分数={fusion_score:.2f}',
            final_score=fusion_score,
            fusion_components=json.dumps({
                'technical_score': tech_score,
                'ai_score': ai_score,
                'fusion_score': fusion_score
            }, ensure_ascii=False),
            fusion_weights=json.dumps(weights, ensure_ascii=False),
            log_details=json.dumps({
                'calculation_method': 'weighted_average',
                'tech_weight': weights.get('technical', 0.4),
                'ai_weight': weights.get('ai_confidence', 0.6)
            }, ensure_ascii=False)
        )
    
    def log_error(self, error_type: str, error_message: str, symbol: str = None, 
                  error_details: Dict[str, Any] = None):
        """记录错误"""
        self._insert_log(
            log_type='error',
            log_level='error',
            stock_symbol=symbol,
            log_message=f'{error_type}: {error_message}',
            log_details=json.dumps({
                'error_type': error_type,
                'error_details': error_details or {},
                'traceback': traceback.format_exc()
            }, ensure_ascii=False, default=str)
        )
    
    def log_performance_metrics(self, operation: str, duration_ms: int, 
                              memory_mb: Optional[float] = None, additional_metrics: Dict[str, Any] = None):
        """记录性能指标"""
        self._insert_log(
            log_type='performance',
            log_level='debug',
            log_message=f'性能指标: {operation} 耗时 {duration_ms}ms',
            cpu_time_ms=duration_ms,
            memory_usage_mb=memory_mb,
            log_details=json.dumps({
                'operation': operation,
                'duration_ms': duration_ms,
                'memory_mb': memory_mb,
                'additional_metrics': additional_metrics or {}
            }, ensure_ascii=False)
        )
    
    def log_task_complete(self, total_processed: int, successful_count: int, 
                         final_recommendations: int, total_duration_s: float):
        """记录任务完成"""
        self._insert_log(
            log_type='task_complete',
            log_level='info',
            log_message=f'推荐任务完成: 处理{total_processed}只股票, 成功{successful_count}只, 推荐{final_recommendations}只',
            log_details=json.dumps({
                'total_processed': total_processed,
                'successful_count': successful_count,
                'final_recommendations': final_recommendations,
                'total_duration_seconds': total_duration_s,
                'success_rate': successful_count / total_processed if total_processed > 0 else 0
            }, ensure_ascii=False)
        )

class AnalysisLogViewer:
    """分析日志查看器"""
    
    @staticmethod
    def get_task_logs(task_id: str, log_types: Optional[List[str]] = None, 
                     log_level: str = 'info', include_debug: bool = False) -> List[Dict[str, Any]]:
        """获取任务的分析日志"""
        try:
            with SessionLocal() as db:
                # 构建查询条件
                conditions = ["task_id = :task_id"]
                params = {'task_id': task_id}
                
                if log_types:
                    placeholders = ', '.join([f':log_type_{i}' for i in range(len(log_types))])
                    conditions.append(f"log_type IN ({placeholders})")
                    for i, log_type in enumerate(log_types):
                        params[f'log_type_{i}'] = log_type
                
                # 日志级别过滤
                level_priority = {'debug': 0, 'info': 1, 'warning': 2, 'error': 3}
                min_priority = level_priority.get(log_level, 1)
                
                if not include_debug and min_priority == 0:
                    min_priority = 1
                
                level_conditions = []
                for level, priority in level_priority.items():
                    if priority >= min_priority:
                        level_conditions.append(f"'{level}'")
                
                if level_conditions:
                    conditions.append(f"log_level IN ({', '.join(level_conditions)})")
                
                where_clause = " AND ".join(conditions)
                
                sql = f"""
                SELECT 
                    id, log_type, stock_symbol, timestamp, log_level, log_message, log_details,
                    ai_request_prompt, ai_response_content, ai_response_tokens, ai_processing_time_ms, ai_provider,
                    technical_indicators, technical_score, technical_signals,
                    fusion_components, fusion_weights, final_score,
                    memory_usage_mb, cpu_time_ms
                FROM analysis_logs 
                WHERE {where_clause}
                ORDER BY timestamp ASC
                """
                
                result = db.execute(text(sql), params)
                
                logs = []
                for row in result:
                    log_dict = dict(row._mapping)
                    
                    # 解析JSON字段
                    json_fields = ['log_details', 'technical_indicators', 'technical_signals', 
                                  'fusion_components', 'fusion_weights']
                    for field in json_fields:
                        if log_dict.get(field):
                            try:
                                log_dict[field] = json.loads(log_dict[field])
                            except json.JSONDecodeError:
                                pass
                    
                    logs.append(log_dict)
                
                return logs
                
        except Exception as e:
            logger.error(f"❌ 获取分析日志失败: {e}")
            return []
    
    @staticmethod
    def get_log_statistics(task_id: str) -> Dict[str, Any]:
        """获取日志统计信息"""
        try:
            with SessionLocal() as db:
                sql = """
                SELECT * FROM log_stats_view WHERE task_id = :task_id
                """
                
                result = db.execute(text(sql), {'task_id': task_id})
                row = result.fetchone()
                
                if row:
                    return dict(row._mapping)
                else:
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ 获取日志统计失败: {e}")
            return {}