"""
分析日志API端点
提供分析过程日志的查看和管理功能
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from backend.services.analysis_logger import AnalysisLogViewer

# 创建路由器
analysis_logs_router = APIRouter(prefix="/api/v2/analysis-logs", tags=["分析日志"])

class AnalysisLogResponse(BaseModel):
    """分析日志响应模型"""
    id: int
    log_type: str
    stock_symbol: Optional[str]
    timestamp: str
    log_level: str
    log_message: str
    log_details: Optional[Dict[str, Any]]
    
    # AI相关字段
    ai_request_prompt: Optional[str]
    ai_response_content: Optional[str]
    ai_response_tokens: Optional[int]
    ai_processing_time_ms: Optional[int]
    ai_provider: Optional[str]
    
    # 技术分析字段
    technical_indicators: Optional[Dict[str, Any]]
    technical_score: Optional[float]
    technical_signals: Optional[Dict[str, Any]]
    
    # 融合评分字段
    fusion_components: Optional[Dict[str, Any]]
    fusion_weights: Optional[Dict[str, Any]]
    final_score: Optional[float]
    
    # 性能监控字段
    memory_usage_mb: Optional[float]
    cpu_time_ms: Optional[int]

class LogStatsResponse(BaseModel):
    """日志统计响应模型"""
    task_id: str
    total_logs: int
    error_count: int
    warning_count: int
    ai_analysis_count: int
    technical_analysis_count: int
    avg_ai_time_ms: Optional[float]
    total_tokens: Optional[int]
    first_log_time: Optional[str]
    last_log_time: Optional[str]

@analysis_logs_router.get("/tasks/{task_id}/logs", response_model=List[AnalysisLogResponse])
async def get_task_analysis_logs(
    task_id: str,
    log_types: Optional[List[str]] = Query(None, description="日志类型过滤"),
    log_level: str = Query("info", description="最低日志级别"),
    include_debug: bool = Query(False, description="是否包含调试日志")
):
    """
    获取指定任务的分析日志
    
    - **task_id**: 任务ID
    - **log_types**: 日志类型过滤，可选值：ai_screening, technical_analysis, ai_analysis, fusion_score, error, performance
    - **log_level**: 最低日志级别，可选值：debug, info, warning, error
    - **include_debug**: 是否包含调试日志
    """
    try:
        logs = AnalysisLogViewer.get_task_logs(
            task_id=task_id,
            log_types=log_types,
            log_level=log_level,
            include_debug=include_debug
        )
        
        return [AnalysisLogResponse(**log) for log in logs]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分析日志失败: {str(e)}")

@analysis_logs_router.get("/tasks/{task_id}/logs/stats", response_model=LogStatsResponse)
async def get_task_log_statistics(task_id: str):
    """
    获取指定任务的日志统计信息
    
    - **task_id**: 任务ID
    """
    try:
        stats = AnalysisLogViewer.get_log_statistics(task_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail="未找到任务日志统计信息")
        
        return LogStatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志统计失败: {str(e)}")

@analysis_logs_router.get("/tasks/{task_id}/logs/ai-screening")
async def get_ai_screening_logs(task_id: str):
    """
    获取AI股票筛选专项日志
    
    - **task_id**: 任务ID
    """
    try:
        logs = AnalysisLogViewer.get_task_logs(
            task_id=task_id,
            log_types=['ai_screening'],
            log_level='debug',
            include_debug=True
        )
        
        # 整理AI筛选日志
        screening_logs = {
            'start_time': None,
            'end_time': None,
            'ai_requests': [],
            'fallback_events': [],
            'errors': [],
            'summary': {
                'total_processing_time_ms': 0,
                'total_tokens': 0,
                'stocks_recommended': 0
            }
        }
        
        for log in logs:
            if log['log_level'] == 'info' and 'AI股票筛选开始' in log['log_message']:
                screening_logs['start_time'] = log['timestamp']
            elif log['ai_request_prompt']:
                screening_logs['ai_requests'].append({
                    'timestamp': log['timestamp'],
                    'prompt': log['ai_request_prompt'],
                    'response': log['ai_response_content'],
                    'processing_time_ms': log['ai_processing_time_ms'],
                    'tokens': log['ai_response_tokens']
                })
                if log['ai_processing_time_ms']:
                    screening_logs['summary']['total_processing_time_ms'] += log['ai_processing_time_ms']
                if log['ai_response_tokens']:
                    screening_logs['summary']['total_tokens'] += log['ai_response_tokens']
            elif 'AI筛选降级' in log['log_message']:
                screening_logs['fallback_events'].append({
                    'timestamp': log['timestamp'],
                    'reason': log['log_message'],
                    'details': log['log_details']
                })
            elif log['log_level'] == 'error':
                screening_logs['errors'].append({
                    'timestamp': log['timestamp'],
                    'error_message': log['log_message'],
                    'details': log['log_details']
                })
        
        if logs:
            screening_logs['end_time'] = logs[-1]['timestamp']
            if logs[-1]['log_details'] and 'stocks_count' in logs[-1]['log_details']:
                screening_logs['summary']['stocks_recommended'] = logs[-1]['log_details']['stocks_count']
        
        return screening_logs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取AI筛选日志失败: {str(e)}")

@analysis_logs_router.get("/tasks/{task_id}/logs/performance")
async def get_performance_logs(task_id: str):
    """
    获取性能监控日志
    
    - **task_id**: 任务ID
    """
    try:
        logs = AnalysisLogViewer.get_task_logs(
            task_id=task_id,
            log_types=['performance', 'ai_analysis', 'technical_analysis'],
            log_level='info'
        )
        
        performance_data = {
            'ai_performance': {
                'total_calls': 0,
                'total_time_ms': 0,
                'avg_time_ms': 0,
                'total_tokens': 0,
                'avg_tokens_per_call': 0
            },
            'technical_performance': {
                'total_analyses': 0,
                'avg_score': 0
            },
            'timeline': []
        }
        
        ai_times = []
        ai_token_counts = []
        tech_scores = []
        
        for log in logs:
            if log['ai_processing_time_ms']:
                ai_times.append(log['ai_processing_time_ms'])
                performance_data['ai_performance']['total_calls'] += 1
                performance_data['ai_performance']['total_time_ms'] += log['ai_processing_time_ms']
            
            if log['ai_response_tokens']:
                ai_token_counts.append(log['ai_response_tokens'])
                performance_data['ai_performance']['total_tokens'] += log['ai_response_tokens']
            
            if log['technical_score'] is not None:
                tech_scores.append(log['technical_score'])
                performance_data['technical_performance']['total_analyses'] += 1
            
            performance_data['timeline'].append({
                'timestamp': log['timestamp'],
                'log_type': log['log_type'],
                'stock_symbol': log['stock_symbol'],
                'processing_time_ms': log['ai_processing_time_ms'] or log['cpu_time_ms'],
                'memory_mb': log['memory_usage_mb']
            })
        
        # 计算平均值
        if ai_times:
            performance_data['ai_performance']['avg_time_ms'] = sum(ai_times) / len(ai_times)
        if ai_token_counts:
            performance_data['ai_performance']['avg_tokens_per_call'] = sum(ai_token_counts) / len(ai_token_counts)
        if tech_scores:
            performance_data['technical_performance']['avg_score'] = sum(tech_scores) / len(tech_scores)
        
        return performance_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取性能日志失败: {str(e)}")

@analysis_logs_router.get("/tasks/{task_id}/logs/stock/{symbol}")
async def get_stock_analysis_logs(task_id: str, symbol: str):
    """
    获取特定股票的分析日志
    
    - **task_id**: 任务ID
    - **symbol**: 股票代码
    """
    try:
        logs = AnalysisLogViewer.get_task_logs(
            task_id=task_id,
            log_level='debug',
            include_debug=True
        )
        
        # 过滤特定股票的日志
        stock_logs = [log for log in logs if log.get('stock_symbol') == symbol]
        
        if not stock_logs:
            raise HTTPException(status_code=404, detail=f"未找到股票 {symbol} 的分析日志")
        
        # 整理股票分析过程
        analysis_process = {
            'stock_symbol': symbol,
            'technical_analysis': None,
            'ai_analysis': {
                'start_time': None,
                'end_time': None,
                'chunks': [],
                'final_result': None
            },
            'fusion_score': None,
            'errors': []
        }
        
        for log in stock_logs:
            if log['log_type'] == 'technical_analysis':
                analysis_process['technical_analysis'] = {
                    'timestamp': log['timestamp'],
                    'score': log['technical_score'],
                    'indicators': log['technical_indicators'],
                    'signals': log['technical_signals']
                }
            elif log['log_type'] == 'ai_analysis':
                if '开始AI深度分析' in log['log_message']:
                    analysis_process['ai_analysis']['start_time'] = log['timestamp']
                elif 'AI分析流式数据' in log['log_message']:
                    analysis_process['ai_analysis']['chunks'].append({
                        'timestamp': log['timestamp'],
                        'chunk_content': log['log_details'].get('chunk_content', '') if log['log_details'] else ''
                    })
                elif 'AI深度分析完成' in log['log_message']:
                    analysis_process['ai_analysis']['end_time'] = log['timestamp']
                    analysis_process['ai_analysis']['final_result'] = {
                        'content': log['ai_response_content'],
                        'processing_time_ms': log['ai_processing_time_ms'],
                        'tokens': log['ai_response_tokens']
                    }
            elif log['log_type'] == 'fusion_score':
                analysis_process['fusion_score'] = {
                    'timestamp': log['timestamp'],
                    'components': log['fusion_components'],
                    'weights': log['fusion_weights'],
                    'final_score': log['final_score']
                }
            elif log['log_level'] == 'error':
                analysis_process['errors'].append({
                    'timestamp': log['timestamp'],
                    'error_message': log['log_message'],
                    'details': log['log_details']
                })
        
        return analysis_process
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票分析日志失败: {str(e)}")