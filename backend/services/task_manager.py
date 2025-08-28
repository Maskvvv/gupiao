"""
任务管理器
负责创建、调度和管理流式推荐任务
"""
import asyncio
import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
import threading

# 导入数据库模型
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.models.streaming_models import (
    RecommendationTask, RecommendationResult, TaskProgress, TaskSchedule, SystemMetrics,
    SessionLocal, now_bj
)

# 导入引擎组件
from .streaming_engine_core import StreamingRecommendationEngine
from .streaming_engine_utils import StreamingEngineUtils

logger = logging.getLogger(__name__)

class TaskManager:
    """任务管理器 - 负责任务的创建、调度和生命周期管理"""
    
    def __init__(self, max_concurrent_tasks: int = 3):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.running_tasks = {}  # task_id -> asyncio.Task
        self.task_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_tasks)
        self.engine = None  # 延迟初始化
        
    def get_engine(self):
        """获取引擎实例（延迟初始化）"""
        if self.engine is None:
            # 合并核心引擎和工具类
            class CombinedEngine(StreamingRecommendationEngine, StreamingEngineUtils):
                pass
            self.engine = CombinedEngine()
        return self.engine
    
    async def create_ai_recommendation_task(self, symbols: List[str], 
                                           period: str = "1y",
                                           weights: Optional[Dict[str, float]] = None,
                                           ai_config: Optional[Dict[str, Any]] = None,
                                           priority: int = 5) -> str:
        """创建AI推荐任务"""
        task_id = str(uuid.uuid4()).replace('-', '')
        
        request_params = {
            'symbols': symbols,
            'period': period
        }
        
        weights_config = weights or {
            "technical": 0.4,
            "macro_sentiment": 0.35,
            "news_events": 0.25
        }
        
        ai_config = ai_config or {}
        
        # 创建任务记录
        with SessionLocal() as db:
            # 生成用户详情摘要
            user_input_summary = f"指定股票: {', '.join(symbols[:5])}{'等' if len(symbols) > 5 else ''} | 总数: {len(symbols)} | 分析周期: {period}"
            
            weights_str = ', '.join([f'{k}({v})' for k, v in weights_config.items()])
            filter_summary = f'权重配置: {weights_str}'
            
            execution_strategy = "AI智能分析指定股票 → 技术分析 → AI深度分析 → 融合评分 → 输出推荐"
            
            task = RecommendationTask(
                id=task_id,
                task_type='ai',
                status='pending',
                priority=priority,
                request_params=json.dumps(request_params),
                ai_config=json.dumps(ai_config),
                weights_config=json.dumps(weights_config),
                total_symbols=len(symbols),
                # 用户详情字段
                user_input_summary=user_input_summary,
                filter_summary=filter_summary,
                execution_strategy=execution_strategy
            )
            db.add(task)
            db.commit()
        
        logger.info(f"✅ 创建AI推荐任务: {task_id}, 股票数: {len(symbols)}")
        return task_id
    
    async def create_keyword_recommendation_task(self, keyword: str,
                                               period: str = "1y",
                                               max_candidates: int = 5,
                                               weights: Optional[Dict[str, float]] = None,
                                               filter_config: Optional[Dict[str, Any]] = None,
                                               ai_config: Optional[Dict[str, Any]] = None,
                                               priority: int = 5) -> str:
        """创建关键词推荐任务"""
        task_id = str(uuid.uuid4()).replace('-', '')
        
        request_params = {
            'keyword': keyword,
            'period': period,
            'max_candidates': max_candidates
        }
        
        weights_config = weights or {
            "technical": 0.4,
            "macro_sentiment": 0.35,
            "news_events": 0.25
        }
        
        filter_config = filter_config or {
            'exclude_st': True
        }
        # 注意: max_candidates 已经在 request_params 中存储，不在 filter_config 中重复
        
        ai_config = ai_config or {}
        
        # 创建任务记录
        with SessionLocal() as db:
            # 生成用户详情摘要
            user_input_summary = f"关键词: {keyword} | 最大候选数: {max_candidates} | 分析周期: {period}"
            
            filter_conditions = []
            if filter_config.get('exclude_st'):
                filter_conditions.append('排除ST股票')
            if filter_config.get('min_market_cap'):
                filter_conditions.append(f'最小市值: {filter_config["min_market_cap"]}亿')
            filter_summary = ', '.join(filter_conditions) if filter_conditions else '无特殊筛选条件'
            
            execution_strategy = "AI智能筛选股票池 → 技术分析 → AI深度分析 → 融合评分 → 输出推荐"
            
            task = RecommendationTask(
                id=task_id,
                task_type='keyword',
                status='pending',
                priority=priority,
                request_params=json.dumps(request_params),
                ai_config=json.dumps(ai_config),
                filter_config=json.dumps(filter_config),
                weights_config=json.dumps(weights_config),
                # 用户详情字段
                user_input_summary=user_input_summary,
                filter_summary=filter_summary,
                execution_strategy=execution_strategy
            )
            db.add(task)
            db.commit()
        
        logger.info(f"✅ 创建关键词推荐任务: {task_id}, 关键词: {keyword}")
        return task_id
    
    async def create_market_recommendation_task(self, 
                                              period: str = "1y",
                                              max_candidates: int = 50,
                                              weights: Optional[Dict[str, float]] = None,
                                              filter_config: Optional[Dict[str, Any]] = None,
                                              ai_config: Optional[Dict[str, Any]] = None,
                                              priority: int = 5) -> str:
        """创建全市场推荐任务"""
        task_id = str(uuid.uuid4()).replace('-', '')
        
        request_params = {
            'period': period,
            'max_candidates': max_candidates
        }
        
        weights_config = weights or {
            "technical": 0.4,
            "macro_sentiment": 0.35,
            "news_events": 0.25
        }
        
        filter_config = filter_config or {
            'exclude_st': True,
            'min_market_cap': None,
            'board': None
        }
        
        ai_config = ai_config or {}
        
        # 创建任务记录
        with SessionLocal() as db:
            # 生成用户详情摘要
            user_input_summary = f"全市场智能推荐 | 最大候选数: {max_candidates} | 分析周期: {period}"
            
            filter_conditions = []
            if filter_config.get('exclude_st'):
                filter_conditions.append('排除ST股票')
            if filter_config.get('min_market_cap'):
                filter_conditions.append(f'最小市值: {filter_config["min_market_cap"]}亿')
            if filter_config.get('board'):
                filter_conditions.append(f'板块: {filter_config["board"]}')
            filter_summary = ', '.join(filter_conditions) if filter_conditions else '无特殊筛选条件'
            
            execution_strategy = "全市场股票池筛选 → 技术分析 → AI深度分析 → 融合评分 → 输出推荐"
            
            task = RecommendationTask(
                id=task_id,
                task_type='market',
                status='pending',
                priority=priority,
                request_params=json.dumps(request_params),
                ai_config=json.dumps(ai_config),
                filter_config=json.dumps(filter_config),
                weights_config=json.dumps(weights_config),
                # 用户详情字段
                user_input_summary=user_input_summary,
                filter_summary=filter_summary,
                execution_strategy=execution_strategy
            )
            db.add(task)
            db.commit()
        
        logger.info(f"✅ 创建全市场推荐任务: {task_id}, 最大候选数: {max_candidates}")
        return task_id
    
    async def start_task(self, task_id: str) -> bool:
        """启动任务执行"""
        with self.task_lock:
            if len(self.running_tasks) >= self.max_concurrent_tasks:
                logger.warning(f"⚠️ 任务队列已满，无法启动任务 {task_id}")
                return False
            
            if task_id in self.running_tasks:
                logger.warning(f"⚠️ 任务 {task_id} 已在运行中")
                return False
        
        try:
            # 创建异步任务
            task = asyncio.create_task(self._execute_task(task_id))
            
            with self.task_lock:
                self.running_tasks[task_id] = task
            
            logger.info(f"🚀 启动任务执行: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动任务失败 {task_id}: {e}")
            return False
    
    async def _execute_task(self, task_id: str):
        """执行任务的内部方法"""
        try:
            engine = self.get_engine()
            await engine.execute_recommendation_task(task_id)
            logger.info(f"✅ 任务执行完成: {task_id}")
            
        except Exception as e:
            logger.error(f"❌ 任务执行失败 {task_id}: {e}")
            
        finally:
            # 清理运行任务记录
            with self.task_lock:
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self.task_lock:
            if task_id not in self.running_tasks:
                logger.warning(f"⚠️ 任务 {task_id} 未在运行中")
                return False
            
            task = self.running_tasks[task_id]
            task.cancel()
            del self.running_tasks[task_id]
        
        # 更新数据库状态
        with SessionLocal() as db:
            db_task = db.query(RecommendationTask).filter(RecommendationTask.id == task_id).first()
            if db_task:
                db_task.status = 'cancelled'
                db_task.updated_at = now_bj()
                db.commit()
        
        logger.info(f"🛑 任务已取消: {task_id}")
        return True
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with SessionLocal() as db:
            task = db.query(RecommendationTask).filter(RecommendationTask.id == task_id).first()
            if not task:
                return None
            
            return {
                'id': task.id,
                'task_type': task.task_type,
                'status': task.status,
                'priority': task.priority,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'updated_at': task.updated_at.isoformat() if task.updated_at else None,
                'total_symbols': task.total_symbols,
                'completed_symbols': task.completed_symbols,
                'current_symbol': task.current_symbol,
                'current_phase': task.current_phase,
                'progress_percent': task.progress_percent,
                'successful_count': task.successful_count,
                'failed_count': task.failed_count,
                'final_recommendations': task.final_recommendations,
                'error_message': task.error_message,
                'execution_time_seconds': task.execution_time_seconds,
                'is_running': task_id in self.running_tasks,
                # 用户详情字段（用于任务详情页面显示）
                'user_input_summary': task.user_input_summary,
                'filter_summary': task.filter_summary,
                'ai_prompt_used': task.ai_prompt_used,
                'execution_strategy': task.execution_strategy,
                'candidate_stocks_info': task.candidate_stocks_info
            }
    
    async def list_tasks(self, status: Optional[str] = None, 
                        task_type: Optional[str] = None,
                        limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """获取任务列表"""
        with SessionLocal() as db:
            query = db.query(RecommendationTask)
            
            if status:
                query = query.filter(RecommendationTask.status == status)
            
            if task_type:
                query = query.filter(RecommendationTask.task_type == task_type)
            
            # 总数
            total = query.count()
            
            # 分页查询
            tasks = query.order_by(RecommendationTask.created_at.desc()).offset(offset).limit(limit).all()
            
            # 统计信息
            stats = {
                'total': total,
                'pending': db.query(RecommendationTask).filter(RecommendationTask.status == 'pending').count(),
                'running': db.query(RecommendationTask).filter(RecommendationTask.status == 'running').count(),
                'completed': db.query(RecommendationTask).filter(RecommendationTask.status == 'completed').count(),
                'failed': db.query(RecommendationTask).filter(RecommendationTask.status == 'failed').count(),
                'cancelled': db.query(RecommendationTask).filter(RecommendationTask.status == 'cancelled').count()
            }
            
            task_list = []
            for task in tasks:
                task_list.append({
                    'id': task.id,
                    'task_type': task.task_type,
                    'status': task.status,
                    'priority': task.priority,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'updated_at': task.updated_at.isoformat() if task.updated_at else None,
                    'total_symbols': task.total_symbols,
                    'completed_symbols': task.completed_symbols,
                    'current_symbol': task.current_symbol,
                    'progress_percent': task.progress_percent,
                    'final_recommendations': task.final_recommendations,
                    'execution_time_seconds': task.execution_time_seconds,
                    'is_running': task.id in self.running_tasks,
                    # 用户详情字段（用于任务详情页面显示）
                    'user_input_summary': task.user_input_summary,
                    'filter_summary': task.filter_summary,
                    'ai_prompt_used': task.ai_prompt_used,
                    'execution_strategy': task.execution_strategy,
                    'candidate_stocks_info': task.candidate_stocks_info
                })
            
            return {
                'tasks': task_list,
                'stats': stats,
                'pagination': {
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total
                }
            }
    
    async def get_task_results(self, task_id: str, 
                              recommended_only: bool = False,
                              limit: int = 100) -> List[Dict[str, Any]]:
        """获取任务结果"""
        with SessionLocal() as db:
            query = db.query(RecommendationResult).filter(RecommendationResult.task_id == task_id)
            
            if recommended_only:
                query = query.filter(RecommendationResult.is_recommended == True)
            
            results = query.order_by(RecommendationResult.rank_in_task).limit(limit).all()
            
            result_list = []
            for result in results:
                result_list.append({
                    'id': result.id,
                    'symbol': result.symbol,
                    'name': result.name,
                    'technical_score': result.technical_score,
                    'ai_score': result.ai_score,
                    'fusion_score': result.fusion_score,
                    'final_score': result.final_score,
                    'action': result.action,
                    'ai_analysis': result.ai_analysis,
                    'ai_confidence': result.ai_confidence,
                    'summary': result.summary,
                    'rank_in_task': result.rank_in_task,
                    'is_recommended': result.is_recommended,
                    'recommendation_reason': result.recommendation_reason,
                    'current_price': result.current_price,
                    'analyzed_at': result.analyzed_at.isoformat() if result.analyzed_at else None
                })
            
            return result_list
    
    async def get_task_progress(self, task_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取任务执行进度记录"""
        with SessionLocal() as db:
            query = db.query(TaskProgress).filter(TaskProgress.task_id == task_id)
            
            progress_records = query.order_by(TaskProgress.timestamp.desc()).limit(limit).all()
            
            progress_list = []
            for progress in progress_records:
                progress_list.append({
                    'id': progress.id,
                    'task_id': progress.task_id,
                    'timestamp': progress.timestamp.isoformat() if progress.timestamp else None,
                    'event_type': progress.event_type,
                    'symbol': progress.symbol,
                    'phase': progress.phase,
                    'progress_data': json.loads(progress.progress_data) if progress.progress_data else None,
                    'ai_chunk_content': progress.ai_chunk_content,
                    'accumulated_content': progress.accumulated_content,
                    'status': progress.status,
                    'message': progress.message,
                    'processing_time_ms': progress.processing_time_ms
                })
            
            return progress_list
    
    async def retry_task(self, task_id: str) -> bool:
        """重试失败的任务"""
        with SessionLocal() as db:
            task = db.query(RecommendationTask).filter(RecommendationTask.id == task_id).first()
            if not task:
                return False
            
            if task.status not in ['failed', 'cancelled']:
                logger.warning(f"⚠️ 任务 {task_id} 状态为 {task.status}，无法重试")
                return False
            
            # 重置任务状态
            task.status = 'pending'
            task.started_at = None
            task.completed_at = None
            task.progress_percent = 0.0
            task.completed_symbols = 0
            task.current_symbol = None
            task.current_phase = None
            task.successful_count = 0
            task.failed_count = 0
            task.error_message = None
            task.retry_count += 1
            task.updated_at = now_bj()
            
            # 清理旧的结果
            db.query(RecommendationResult).filter(RecommendationResult.task_id == task_id).delete()
            db.query(TaskProgress).filter(TaskProgress.task_id == task_id).delete()
            
            db.commit()
        
        logger.info(f"🔄 任务已重置为待执行状态: {task_id}")
        return True
    
    def get_running_task_count(self) -> int:
        """获取正在运行的任务数量"""
        with self.task_lock:
            return len(self.running_tasks)
    
    def get_running_task_ids(self) -> List[str]:
        """获取正在运行的任务ID列表"""
        with self.task_lock:
            return list(self.running_tasks.keys())

# 全局任务管理器实例
task_manager = TaskManager()