"""
流式推荐引擎核心组件 - 第一部分
取代原有的EnhancedAnalyzer，支持流式处理和任务管理
"""
import asyncio
import json
import uuid
import time
import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, AsyncGenerator
import logging

# 导入相关组件
from .streaming_ai_router import StreamingAIRouter, StreamingAIRequest, progress_manager
from .analyzer import basic_analysis
from .data_fetcher import DataFetcher
from .confidence_fusion import extract_confidence_and_fusion
from .analysis_logger import AnalysisLogger, AnalysisLogViewer

# 导入数据库模型
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.models.streaming_models import (
    RecommendationTask, RecommendationResult, TaskProgress, SessionLocal, now_bj
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StreamingRecommendationEngine:
    """流式推荐引擎 - 系统核心（取代原有的EnhancedAnalyzer）"""
    
    def __init__(self):
        self.ai_router = StreamingAIRouter()
        self.data_fetcher = DataFetcher()
        self.progress_manager = progress_manager
        
        # 默认权重配置
        self.default_weights = {
            "technical": 0.6,
            "ai_confidence": 0.4,
            "macro_sentiment": 0.35,
            "news_events": 0.25
        }
    
    async def execute_recommendation_task(self, task_id: str):
        """执行推荐任务的主方法"""
        # 初始化分析日志记录器
        analysis_logger = AnalysisLogger(task_id)
        
        # 注册进度回调，确保进度能正确保存到数据库
        async def progress_callback(progress_data: Dict[str, Any]):
            """进度回调函数，将进度保存到数据库"""
            try:
                from .sse_manager import sse_manager
                event_type = progress_data.get('type', 'progress')
                await sse_manager.broadcast_to_task(task_id, event_type, progress_data)
                logger.debug(f"✅ 进度回调成功: {event_type} - {progress_data.get('symbol', '')}")
            except Exception as e:
                logger.error(f"❌ 进度回调失败: {e}")
        
        # 注册回调
        self.progress_manager.register_callback(task_id, progress_callback)
        
        task = await self._get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        try:
            await self._update_task_status(task_id, 'running', started_at=now_bj())
            
            # 记录任务开始
            request_params = json.loads(task.request_params or '{}')
            analysis_logger.log_task_start({
                'task_type': task.task_type,
                'request_params': request_params,
                'ai_config': json.loads(task.ai_config or '{}'),
                'filter_config': json.loads(task.filter_config or '{}'),
                'weights_config': json.loads(task.weights_config or '{}')
            })
            
            # 根据任务类型调用不同的处理方法
            if task.task_type == 'ai':
                await self._process_ai_recommendation(task, analysis_logger)
            elif task.task_type == 'keyword':
                await self._process_keyword_recommendation(task, analysis_logger)
            elif task.task_type == 'market':
                await self._process_market_recommendation(task, analysis_logger)
            elif task.task_type == 'watchlist_batch':
                await self._process_watchlist_batch(task, analysis_logger)
            elif task.task_type == 'watchlist_reanalyze':
                await self._process_watchlist_reanalyze(task, analysis_logger)
            else:
                analysis_logger.log_error('unknown_task_type', f'Unknown task type: {task.task_type}')
                raise ValueError(f"Unknown task type: {task.task_type}")
                
            await self._finalize_task(task_id)
            logger.info(f"✅ 任务 {task_id} 执行完成")
            
        except Exception as e:
            analysis_logger.log_error('task_execution_error', str(e))
            await self._handle_task_error(task_id, str(e))
            logger.error(f"❌ 任务 {task_id} 执行失败: {e}")
            raise
        finally:
            # 任务结束时注销回调
            self.progress_manager.unregister_callback(task_id)
    
    async def _process_ai_recommendation(self, task: RecommendationTask, analysis_logger: AnalysisLogger):
        """处理AI推荐任务（手动输入股票代码）"""
        request_params = json.loads(task.request_params)
        symbols = request_params.get('symbols', [])
        
        await self._update_task_total_symbols(task.id, len(symbols))
        logger.info(f"🎯 开始AI推荐任务: {len(symbols)} 只股票")
        
        results = []
        for i, symbol in enumerate(symbols):
            # 更新当前处理状态
            await self.progress_manager.update_current_symbol(task.id, symbol)
            await self._update_task_current_symbol(task.id, symbol)
            
            # 获取股票数据
            stock_data = self.data_fetcher.get_stock_data(
                symbol, 
                period=request_params.get('period', '1y')
            )
            
            if stock_data is None or stock_data.empty:
                await self.progress_manager.record_symbol_failed(task.id, symbol, "数据获取失败")
                await self._increment_failed_count(task.id)
                continue
            
            # 流式分析股票
            analysis_result = await self._stream_analyze_symbol(
                task.id, symbol, stock_data, 
                ai_config=json.loads(task.ai_config or '{}'),
                weights=json.loads(task.weights_config or '{}'),
                analysis_logger=analysis_logger
            )
            
            if analysis_result:
                results.append(analysis_result)
                await self.progress_manager.record_symbol_completed(task.id, symbol)
                await self._increment_successful_count(task.id)
            
            # 更新进度
            progress = (i + 1) / len(symbols) * 100
            await self.progress_manager.update_progress(task.id, progress)
            await self._update_task_progress(task.id, progress, i + 1)
        
        # 排序和生成最终推荐
        final_recommendations = await self._rank_and_select_recommendations(task.id, results)
        await self._save_task_results(task.id, final_recommendations)
        
        return final_recommendations
    
    async def _process_keyword_recommendation(self, task: RecommendationTask, analysis_logger: AnalysisLogger):
        """处理关键词推荐任务"""
        request_params = json.loads(task.request_params)
        keyword = request_params.get('keyword')
        max_candidates = request_params.get('max_candidates', 5)
        
        # 在最开始记录开始时间
        task_start_time = time.time()
        
        # 更新任务详情信息
        await self._update_task_details(task, keyword, request_params)
        
        # 阶段1: 关键词筛选股票
        await self.progress_manager.update_phase(task.id, 'screening')
        analysis_logger.log_ai_screening_start(keyword, max_candidates)
        
        filter_config = json.loads(task.filter_config or '{}')
        # 使用更大的候选数进行初步筛选，通常是最终推荐数的3-4倍
        screening_candidates = max(max_candidates * 3, 20)
        
        candidate_symbols = await self._get_ai_recommended_stocks(
            keyword=keyword,
            max_candidates=screening_candidates,
            exclude_st=filter_config.get('exclude_st', True),
            board=filter_config.get('board'),
            analysis_logger=analysis_logger
        )
        
        logger.info(f"📊 筛选出 {len(candidate_symbols)} 只候选股票")
        
        # 存储候选股票信息
        await self._store_candidate_stocks_info(task.id, candidate_symbols, keyword)
        
        await self._update_task_total_symbols(task.id, len(candidate_symbols))
        await self.progress_manager.update_phase(task.id, 'analyzing')
        
        # 获取AI配置和权重配置
        ai_config = json.loads(task.ai_config or '{}')
        weights_config = json.loads(task.weights_config or '{}')
        
        # 阶段2: 并行流式分析筛选结果
        results = []
        
        # 优化：小批量并行处理，避免资源耗尽
        batch_size = min(3, len(candidate_symbols))  # 最多3个并行
        
        for batch_start in range(0, len(candidate_symbols), batch_size):
            batch_symbols = candidate_symbols[batch_start:batch_start + batch_size]
            
            # 创建并行任务
            tasks = []
            for symbol in batch_symbols:
                coroutine_task = self._analyze_single_stock_async(
                    task.id, symbol, request_params, ai_config, weights_config, keyword, analysis_logger
                )
                tasks.append(coroutine_task)
            
            # 并行执行当前批次
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理批次结果
            for i, result in enumerate(batch_results):
                symbol = batch_symbols[i]
                current_index = batch_start + i
                
                if isinstance(result, Exception):
                    logger.error(f"⚠️ 分析股票 {symbol} 失败: {result}")
                    await self.progress_manager.record_symbol_failed(task.id, symbol, str(result))
                    await self._increment_failed_count(task.id)
                elif result:
                    results.append(result)
                    await self.progress_manager.record_symbol_completed(task.id, symbol)
                    await self._increment_successful_count(task.id)
                else:
                    await self.progress_manager.record_symbol_failed(task.id, symbol, "分析结果为空")
                    await self._increment_failed_count(task.id)
                
                # 更新进度
                progress = (current_index + 1) / len(candidate_symbols) * 100
                await self.progress_manager.update_progress(task.id, progress)
                await self._update_task_progress(task.id, progress, current_index + 1)
        
        # 生成最终推荐，使用用户指定的max_candidates
        final_recommendations = await self._rank_and_select_recommendations(
            task.id,
            results, 
            max_count=max_candidates
        )
        await self._save_task_results(task.id, final_recommendations)
        
        # 记录任务完成
        total_duration = time.time() - task_start_time
        if analysis_logger:
            analysis_logger.log_task_complete(
                len(candidate_symbols), len(results), len(final_recommendations), total_duration
            )
        
        logger.info(f"✨ 关键词推荐完成: {len(final_recommendations)} 只推荐股票 (用户设置: {max_candidates})")
        
        return final_recommendations
    
    async def _get_ai_recommended_stocks(self, keyword: str, max_candidates: int = 20,
                                       exclude_st: bool = True, board: str = None, 
                                       analysis_logger: AnalysisLogger = None) -> List[str]:
        """使用AI获取与关键词相关的股票池（纯AI驱动，无降级策略）"""
        
        try:
            import akshare as ak
            
            logger.info(f"🔍 开始AI智能筛选与 '{keyword}' 相关的{max_candidates}只股票")
            
            # 获取所有A股股票列表
            stock_info = ak.stock_info_a_code_name()
            
            # 基本筛选
            filtered_stocks = stock_info.copy()
            
            # 排除ST股票
            if exclude_st:
                filtered_stocks = filtered_stocks[~filtered_stocks['name'].str.contains(r'ST|\*ST|退', na=False)]
            
            # 板块筛选
            if board and board != 'all':
                if board == 'main':
                    filtered_stocks = filtered_stocks[
                        filtered_stocks['code'].str.startswith(('600', '601', '603', '605', '000', '001', '002'))
                    ]
                elif board == 'gem':
                    filtered_stocks = filtered_stocks[filtered_stocks['code'].str.startswith('300')]
                elif board == 'star':
                    filtered_stocks = filtered_stocks[filtered_stocks['code'].str.startswith('688')]
            
            # 构建股票候选集（扩大到500只，提供AI更多选择）
            available_stocks = filtered_stocks.head(500)
            
            # 优化的AI提示词 - 更加精准和专业
            stock_options = "\n".join([
                f"{row['code']} {row['name']}" 
                for _, row in available_stocks.iterrows()
            ])
            
            prompt = f"""作为专业的A股投资分析师，请根据关键词"{keyword}"从以下股票池中精选出{max_candidates}只最相关的优质股票。

**筛选标准（按重要性排序）：**
1. **核心业务匹配度**：公司主营业务与关键词的直接相关性
2. **行业地位与竞争优势**：在相关领域的市场地位和技术实力
3. **成长潜力与趋势**：未来发展前景和成长性
4. **财务健康度**：经营稳定性和盈利能力
5. **投资价值**：当前估值水平和投资机会

**输出要求：**
- 只返回股票代码，每行一个
- 不要包含任何其他文字或解释
- 代码格式为6位数字（如：000001）
- 请从最相关的开始排列

**可选股票池：**
{stock_options}

**请返回{max_candidates}个股票代码：**"""
            
            # 记录AI请求
            if analysis_logger:
                ai_start_time = analysis_logger.log_ai_screening_request(prompt, 'deepseek')
            
            # 使用DeepSeek流式调用
            ai_response = await self._call_deepseek_stream(prompt, analysis_logger)
            
            # 解析AI返回的股票代码
            recommended_codes = self._parse_stock_codes(ai_response, available_stocks, max_candidates)
            
            # 记录AI筛选结果
            if analysis_logger:
                analysis_logger.log_ai_screening_response(
                    ai_response, 'deepseek', ai_start_time if 'ai_start_time' in locals() else time.time(),
                    recommended_codes
                )
            
            if not recommended_codes:
                error_msg = f"AI筛选失败：未获取到与关键词'{keyword}'相关的有效股票代码"
                logger.error(f"❌ {error_msg}")
                if analysis_logger:
                    analysis_logger.log_error('ai_screening_empty_result', error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"✨ AI筛选成功：{len(recommended_codes)}只与'{keyword}'相关的股票 -> {recommended_codes}")
            
            return recommended_codes
            
        except Exception as e:
            error_msg = f"AI股票筛选失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            if analysis_logger:
                analysis_logger.log_error('ai_screening_error', error_msg, error_details={'keyword': keyword})
            raise Exception(error_msg) from e
    
    async def _call_deepseek_stream(self, prompt: str, analysis_logger: AnalysisLogger = None) -> str:
        """使用DeepSeek流式调用"""
        ai_response = ""
        start_time = time.time()
        
        try:
            logger.info("🔄 开始流式AI请求 - Provider: deepseek")
            
            # 使用DeepSeek流式调用
            async for chunk in self.ai_router.stream_complete(
                prompt=prompt,
                provider='deepseek',
                model='deepseek-chat',
                temperature=0.1  # 使用较低温度确保精确性
            ):
                ai_response += chunk
                
            ai_call_time = time.time() - start_time
            logger.info(f"🕰️ AI调用耗时: {ai_call_time:.2f}秒")
            
            return ai_response
            
        except Exception as e:
            error_msg = f"DeepSeek流式调用失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e
    
    def _parse_stock_codes(self, ai_response: str, available_stocks, max_candidates: int) -> List[str]:
        """解析AI返回的股票代码"""
        recommended_codes = []
        
        if not ai_response.strip():
            return recommended_codes
            
        lines = ai_response.strip().split('\n')
        for line in lines:
            # 清理和验证股票代码
            code = line.strip()
            # 提取6位数字代码
            import re
            code_match = re.search(r'\b(\d{6})\b', code)
            if code_match:
                code = code_match.group(1)
                # 验证代码是否在候选列表中
                if code in available_stocks['code'].values:
                    if code not in recommended_codes:  # 避免重复
                        recommended_codes.append(code)
                        if len(recommended_codes) >= max_candidates:
                            break
                            
        return recommended_codes

    async def _analyze_single_stock_async(self, task_id: str, symbol: str, request_params: dict, 
                                         ai_config: dict, weights_config: dict, context_keyword: str = None,
                                         analysis_logger: AnalysisLogger = None):
        """异步分析单个股票（用于并行处理）"""
        try:
            await self.progress_manager.update_current_symbol(task_id, symbol)
            await self._update_task_current_symbol(task_id, symbol)
            
            # 获取股票数据
            stock_data = self.data_fetcher.get_stock_data(
                symbol, 
                period=request_params.get('period', '1y')
            )
            
            if stock_data is None or stock_data.empty:
                logger.warning(f"⚠️ 股票 {symbol} 数据获取失败")
                return None
            
            # 流式分析股票
            analysis_result = await self._stream_analyze_symbol(
                task_id, symbol, stock_data,
                ai_config=ai_config,
                weights=weights_config,
                context_keyword=context_keyword,
                analysis_logger=analysis_logger
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"⚠️ 异步分析股票 {symbol} 失败: {e}")
            raise e
    
    
    async def _process_market_recommendation(self, task: RecommendationTask, analysis_logger: AnalysisLogger):
        """处理全市场推荐任务"""
        request_params = json.loads(task.request_params)
        max_candidates = request_params.get('max_candidates', 50)
        
        logger.info(f"🌍 开始全市场推荐任务: 最大候选数 {max_candidates}")
        
        # 阶段1: 全市场股票筛选
        await self.progress_manager.update_phase(task.id, 'screening')
        
        filter_config = json.loads(task.filter_config or '{}')
        candidate_symbols = await self._screen_market_stocks(
            max_candidates=max_candidates,
            exclude_st=filter_config.get('exclude_st', True),
            min_market_cap=filter_config.get('min_market_cap'),
            board=filter_config.get('board')
        )
        
        logger.info(f"📊 全市场筛选出 {len(candidate_symbols)} 只候选股票")
        
        await self._update_task_total_symbols(task.id, len(candidate_symbols))
        await self.progress_manager.update_phase(task.id, 'analyzing')
        
        # 阶段2: 流式分析筛选结果
        results = []
        for i, symbol in enumerate(candidate_symbols):
            await self.progress_manager.update_current_symbol(task.id, symbol)
            await self._update_task_current_symbol(task.id, symbol)
            
            stock_data = self.data_fetcher.get_stock_data(
                symbol, 
                period=request_params.get('period', '1y')
            )
            
            if stock_data is not None and not stock_data.empty:
                analysis_result = await self._stream_analyze_symbol(
                    task.id, symbol, stock_data,
                    ai_config=json.loads(task.ai_config or '{}'),
                    weights=json.loads(task.weights_config or '{}')
                )
                
                if analysis_result:
                    results.append(analysis_result)
                    await self.progress_manager.record_symbol_completed(task.id, symbol)
                    await self._increment_successful_count(task.id)
            else:
                await self.progress_manager.record_symbol_failed(task.id, symbol, "数据获取失败")
                await self._increment_failed_count(task.id)
            
            progress = (i + 1) / len(candidate_symbols) * 100
            await self.progress_manager.update_progress(task.id, progress)
            await self._update_task_progress(task.id, progress, i + 1)
        
        # 生成最终推荐
        final_recommendations = await self._rank_and_select_recommendations(
            task.id,
            results, 
            max_count=max_candidates // 4  # 取前25%作为最终推荐
        )
        await self._save_task_results(task.id, final_recommendations)
        
        logger.info(f"✨ 全市场推荐完成: {len(final_recommendations)} 只推荐股票")
        
        return final_recommendations
    
    async def _screen_market_stocks(self, max_candidates: int = 50, exclude_st: bool = True,
                                   min_market_cap: float = None, board: str = None) -> List[str]:
        """筛选全市场股票"""
        try:
            import akshare as ak
            
            # 获取所有A股股票列表
            stock_info = ak.stock_info_a_code_name()
            
            # 基本筛选
            filtered_stocks = stock_info.copy()
            
            # 排除ST股票
            if exclude_st:
                filtered_stocks = filtered_stocks[~filtered_stocks['name'].str.contains(r'ST|\*ST|退', na=False)]
            
            # 板块筛选
            if board and board != 'all':
                if board == 'main':
                    # 主板：600开头的上海主板，000开头的深圳主板
                    filtered_stocks = filtered_stocks[
                        filtered_stocks['code'].str.startswith(('600', '601', '603', '605', '000', '001', '002'))
                    ]
                elif board == 'gem':
                    # 创业板：300开头
                    filtered_stocks = filtered_stocks[filtered_stocks['code'].str.startswith('300')]
                elif board == 'star':
                    # 科创板：688开头
                    filtered_stocks = filtered_stocks[filtered_stocks['code'].str.startswith('688')]
            
            # 随机采样（保证市场代表性）
            if len(filtered_stocks) > max_candidates:
                # 按市值排序（如果有数据），取前50%的大市值股票
                # 然后随机采样
                sampled = filtered_stocks.sample(n=max_candidates, random_state=42)
            else:
                sampled = filtered_stocks
            
            result_symbols = sampled['code'].tolist()
            
            logger.info(f"🌍 全市场筛选结果: {len(result_symbols)} 只股票")
            
            return result_symbols
            
        except Exception as e:
            logger.error(f"⚠️ 全市场筛选失败: {e}")
            # 退化策略：返回一些代表性股票
            default_stocks = [
                '000001', '000002', '000858', '000876', '000725',  # 深圳主板
                '600000', '600036', '600519', '600887', '600028',  # 上海主板
                '300015', '300059', '300124', '300142', '300454',  # 创业板
                '688008', '688036', '688111', '688169', '688981'   # 科创板
            ]
            return default_stocks[:max_candidates]
    
    async def _stream_analyze_symbol(self, task_id: str, symbol: str, stock_data: pd.DataFrame, 
                                   ai_config: dict, weights: dict, context_keyword: str = None,
                                   analysis_logger: AnalysisLogger = None):
        """流式分析单个股票（核心方法）"""
        try:
            # 转换列名为兼容格式
            if not isinstance(stock_data.index, pd.DatetimeIndex):
                stock_data = stock_data.reset_index()
            stock_data.columns = [col.lower() for col in stock_data.columns]
            
            # 技术分析
            if analysis_logger:
                analysis_logger.log_technical_analysis_start(symbol)
                
            technical_analysis = basic_analysis(stock_data)
            if not technical_analysis.get("valid"):
                if analysis_logger:
                    analysis_logger.log_error('technical_analysis_invalid', f'技术分析无效: {symbol}')
                return None
                
            # 检查技术分是否有效
            tech_score = technical_analysis.get('score')
            if tech_score is None:
                if analysis_logger:
                    analysis_logger.log_error('technical_score_null', f'技术分为空: {symbol}')
                logger.warning(f"技术分为空，跳过股票 {symbol}")
                return None
            
            if analysis_logger:
                analysis_logger.log_technical_analysis_complete(symbol, technical_analysis)
            
            # 构建 AI 提示词
            prompt = self._build_analysis_prompt(
                symbol, technical_analysis, stock_data, 
                weights or self.default_weights, context_keyword
            )
            
            # 流式AI分析
            ai_chunks = []
            ai_analysis = ""
            
            await self.progress_manager.record_ai_analysis_start(task_id, symbol)
            
            # 记录AI分析开始
            ai_start_time = None
            if analysis_logger:
                ai_start_time = analysis_logger.log_ai_analysis_start(symbol, prompt)
            
            async for chunk in self.ai_router.stream_complete(
                prompt=prompt,
                provider=ai_config.get('provider'),
                temperature=ai_config.get('temperature'),
                api_key=ai_config.get('api_key')
            ):
                ai_chunks.append(chunk)
                ai_analysis += chunk
                
                # 实时推送AI内容
                await self.progress_manager.push_ai_chunk(
                    task_id, symbol, chunk, ai_analysis
                )
                
                # 记录AI流式数据块
                if analysis_logger:
                    analysis_logger.log_ai_analysis_chunk(symbol, chunk, ai_analysis)
            
            # 处理AI分析结果
            ai_scores = self._extract_ai_scores(ai_analysis)
            
            # 记录AI分析完成
            if analysis_logger and ai_start_time:
                analysis_logger.log_ai_analysis_complete(
                    symbol, ai_analysis, ai_scores, ai_start_time, 
                    ai_config.get('provider', 'openai')
                )
            
            # 计算融合分数，处理空值情况
            fusion_score = self._calculate_fusion_score(
                tech_score,  # 使用已经检查过的tech_score
                ai_scores.get('confidence', 0),
                weights or self.default_weights
            )
            
            # 记录融合评分计算
            if analysis_logger:
                analysis_logger.log_fusion_score_calculation(
                    symbol, tech_score, ai_scores.get('confidence', 0), 
                    fusion_score, weights or self.default_weights
                )
            
            # 如果融合分计算失败，跳过该股票
            if fusion_score is None:
                if analysis_logger:
                    analysis_logger.log_error('fusion_score_calculation_failed', f'融合分计算失败: {symbol}')
                logger.warning(f"融合分计算失败，跳过股票 {symbol}")
                return None
            
            # 获取股票名称
            stock_name = self._get_stock_name(symbol)
            
            result = {
                'symbol': symbol,
                'name': stock_name,
                'technical_score': tech_score * 10,  # 转换为0-10范围用于持久化
                'ai_score': ai_scores.get('confidence', 0),
                'fusion_score': fusion_score,
                'final_score': fusion_score,
                'action': self._determine_action(fusion_score),
                'ai_analysis': ai_analysis,
                'ai_confidence': ai_scores.get('confidence'),
                'ai_reasoning': ai_scores.get('reasoning'),
                'summary': self._generate_summary(technical_analysis, ai_scores),
                'key_factors': json.dumps(self._extract_key_factors(ai_analysis)),
                'technical_indicators': json.dumps(technical_analysis),
                'current_price': stock_data['close'].iloc[-1] if 'close' in stock_data.columns else None,
                'analyzed_at': now_bj()
            }
            
            await self.progress_manager.record_symbol_analysis_complete(task_id, symbol, result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 分析股票 {symbol} 失败: {e}")
            if analysis_logger:
                analysis_logger.log_error('stock_analysis_error', str(e), symbol)
            await self.progress_manager.record_symbol_failed(task_id, symbol, str(e))
            return None
    
    async def _update_task_details(self, task: RecommendationTask, keyword: str, request_params: dict):
        """更新任务详情信息"""
        with SessionLocal() as db:
            try:
                db_task = db.query(RecommendationTask).filter(RecommendationTask.id == task.id).first()
                if db_task:
                    # 用户输入摘要
                    user_summary_parts = []
                    if task.task_type == 'keyword':
                        user_summary_parts.append(f"关键词: {keyword}")
                    elif task.task_type == 'market':
                        user_summary_parts.append("全市场推荐")
                    
                    max_candidates = request_params.get('max_candidates', '未设置')
                    user_summary_parts.append(f"最大候选数: {max_candidates}")
                    
                    period = request_params.get('period', '1y')
                    user_summary_parts.append(f"分析周期: {period}")
                    
                    db_task.user_input_summary = " | ".join(user_summary_parts)
                    
                    # 筛选条件摘要
                    filter_config = json.loads(task.filter_config or '{}')
                    filter_summary_parts = []
                    if filter_config.get('exclude_st'):
                        filter_summary_parts.append("排除ST股票")
                    
                    board = filter_config.get('board')
                    if board and board != 'all':
                        board_names = {'main': '主板', 'gem': '创业板', 'star': '科创板'}
                        filter_summary_parts.append(f"板块: {board_names.get(board, board)}")
                    
                    min_market_cap = filter_config.get('min_market_cap')
                    if min_market_cap:
                        filter_summary_parts.append(f"最小市值: {min_market_cap}亿")
                    
                    db_task.filter_summary = " | ".join(filter_summary_parts) if filter_summary_parts else "无特殊筛选条件"
                    
                    # 执行策略说明
                    if task.task_type == 'keyword':
                        db_task.execution_strategy = "AI智能筛选股票池 → 技术分析 → AI深度分析 → 融合评分 → 排序推荐"
                    else:
                        db_task.execution_strategy = "市场随机采样 → 技术分析 → AI深度分析 → 融合评分 → 排序推荐"
                    
                    db.commit()
                    logger.info(f"✅ 任务 {task.id} 详情信息已更新")
                    
            except Exception as e:
                db.rollback()
                logger.error(f"❌ 更新任务详情失败: {e}")

    async def _store_candidate_stocks_info(self, task_id: str, candidate_symbols: List[str], keyword: str = None):
        """存储候选股票信息"""
        with SessionLocal() as db:
            try:
                db_task = db.query(RecommendationTask).filter(RecommendationTask.id == task_id).first()
                if db_task:
                    # 获取股票名称信息
                    import akshare as ak
                    try:
                        stock_info = ak.stock_info_a_code_name()
                        code_name_map = dict(zip(stock_info['code'], stock_info['name']))
                    except:
                        code_name_map = {}
                    
                    # 构建候选股票信息
                    candidate_info = []
                    for i, symbol in enumerate(candidate_symbols, 1):
                        stock_name = code_name_map.get(symbol, f"股票{symbol}")
                        candidate_info.append({
                            "rank": i,
                            "code": symbol,
                            "name": stock_name,
                            "selected_by": "AI推荐" if keyword else "市场筛选"
                        })
                    
                    # 存储为JSON格式
                    candidate_summary = {
                        "total_count": len(candidate_symbols),
                        "selection_method": f"AI关键词筛选: {keyword}" if keyword else "全市场随机采样",
                        "candidates": candidate_info
                    }
                    
                    db_task.candidate_stocks_info = json.dumps(candidate_summary, ensure_ascii=False, indent=2)
                    db.commit()
                    logger.info(f"✅ 候选股票信息已存储到任务 {task_id}")
                    
            except Exception as e:
                db.rollback()
                logger.error(f"❌ 存储候选股票信息失败: {e}")
    
    async def _process_watchlist_batch(self, task: RecommendationTask, analysis_logger: AnalysisLogger):
        """处理自选股票批量分析任务"""
        request_params = json.loads(task.request_params)
        symbols = request_params.get('symbols')
        
        # 如果没有指定股票列表，获取所有自选股
        if not symbols:
            symbols = await self._get_all_watchlist_symbols()
            if not symbols:
                error_msg = "自选股列表为空，无法执行批量分析"
                logger.error(f"❌ {error_msg}")
                analysis_logger.log_error('empty_watchlist', error_msg)
                raise ValueError(error_msg)
        
        await self._update_task_total_symbols(task.id, len(symbols))
        logger.info(f"🎯 开始自选股票批量分析任务: {len(symbols)} 只股票")
        
        # 记录任务详情
        await self._update_watchlist_task_details(task, symbols, 'batch')
        
        results = []
        for i, symbol in enumerate(symbols):
            # 更新当前处理状态
            await self.progress_manager.update_current_symbol(task.id, symbol)
            await self._update_task_current_symbol(task.id, symbol)
            
            # 获取股票数据
            stock_data = self.data_fetcher.get_stock_data(
                symbol, 
                period=request_params.get('period', '1y')
            )
            
            if stock_data is None or stock_data.empty:
                await self.progress_manager.record_symbol_failed(task.id, symbol, "数据获取失败")
                await self._increment_failed_count(task.id)
                continue
            
            # 流式分析股票
            analysis_result = await self._stream_analyze_symbol(
                task.id, symbol, stock_data, 
                ai_config=json.loads(task.ai_config or '{}'),
                weights=json.loads(task.weights_config or '{}'),
                analysis_logger=analysis_logger
            )
            
            if analysis_result:
                results.append(analysis_result)
                await self.progress_manager.record_symbol_completed(task.id, symbol)
                await self._increment_successful_count(task.id)
                
                # 保存分析结果到自选股分析记录
                await self._save_watchlist_analysis_result(symbol, analysis_result)
            
            # 更新进度
            progress = (i + 1) / len(symbols) * 100
            await self.progress_manager.update_progress(task.id, progress)
            await self._update_task_progress(task.id, progress, i + 1)
        
        # 排序和生成最终推荐
        final_recommendations = await self._rank_and_select_recommendations(task.id, results)
        await self._save_task_results(task.id, final_recommendations)
        
        logger.info(f"✨ 自选股票批量分析完成: {len(final_recommendations)} 只股票")
        
        return final_recommendations
    
    async def _process_watchlist_reanalyze(self, task: RecommendationTask, analysis_logger: AnalysisLogger):
        """处理自选股票单股重新分析任务"""
        logger.info(f"🔍 开始处理自选股重新分析任务: {task.id}")
        request_params = json.loads(task.request_params)
        symbol = request_params.get('symbol')
        logger.info(f"📊 解析请求参数 - 股票代码: {symbol}, 周期: {request_params.get('period', '1y')}")
        
        if not symbol:
            error_msg = "股票代码不能为空"
            logger.error(f"❌ {error_msg}")
            analysis_logger.log_error('missing_symbol', error_msg)
            raise ValueError(error_msg)
        
        # 验证股票是否在自选股列表中
        logger.info(f"🔍 验证股票 {symbol} 是否在自选股列表中...")
        watchlist_symbols = await self._get_all_watchlist_symbols()
        logger.info(f"📋 自选股列表: {watchlist_symbols}")
        
        if symbol not in watchlist_symbols:
            error_msg = f"股票 {symbol} 不在自选股列表中，当前自选股: {watchlist_symbols}"
            logger.error(f"❌ {error_msg}")
            analysis_logger.log_error('symbol_not_in_watchlist', error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"✅ 股票 {symbol} 验证通过，开始分析...")
        
        await self._update_task_total_symbols(task.id, 1)
        logger.info(f"🎯 开始自选股票重新分析任务: {symbol}")
        
        # 记录任务详情
        await self._update_watchlist_task_details(task, [symbol], 'reanalyze')
        
        # 更新当前处理状态
        await self.progress_manager.update_current_symbol(task.id, symbol)
        await self._update_task_current_symbol(task.id, symbol)
        
        # 获取股票数据
        stock_data = self.data_fetcher.get_stock_data(
            symbol, 
            period=request_params.get('period', '1y')
        )
        
        if stock_data is None or stock_data.empty:
            error_msg = f"股票 {symbol} 数据获取失败"
            await self.progress_manager.record_symbol_failed(task.id, symbol, error_msg)
            await self._increment_failed_count(task.id)
            analysis_logger.log_error('data_fetch_failed', error_msg)
            raise ValueError(error_msg)
        
        # 流式分析股票
        analysis_result = await self._stream_analyze_symbol(
            task.id, symbol, stock_data, 
            ai_config=json.loads(task.ai_config or '{}'),
            weights=json.loads(task.weights_config or '{}'),
            analysis_logger=analysis_logger
        )
        
        if analysis_result:
            await self.progress_manager.record_symbol_completed(task.id, symbol)
            await self._increment_successful_count(task.id)
            
            # 保存分析结果到自选股分析记录
            await self._save_watchlist_analysis_result(symbol, analysis_result)
            
            # 更新进度为100%
            await self.progress_manager.update_progress(task.id, 100.0)
            await self._update_task_progress(task.id, 100.0, 1)
            
            # 保存任务结果
            await self._save_task_results(task.id, [analysis_result])
            
            logger.info(f"✨ 自选股票重新分析完成: {symbol}")
            
            return [analysis_result]
        else:
            error_msg = f"股票 {symbol} 分析失败"
            await self.progress_manager.record_symbol_failed(task.id, symbol, error_msg)
            await self._increment_failed_count(task.id)
            analysis_logger.log_error('analysis_failed', error_msg)
            raise ValueError(error_msg)
    
    async def _get_all_watchlist_symbols(self) -> List[str]:
        """获取所有自选股票代码"""
        try:
            logger.info("🔍 开始获取自选股列表...")
            # 导入自选股相关模型（从routes.py导入）
            from backend.routes import Watchlist, SessionLocal as WatchlistSessionLocal
            logger.info("✅ 成功导入Watchlist模型和SessionLocal")
            
            with WatchlistSessionLocal() as db:
                logger.info("🔗 数据库连接已建立")
                watchlist_items = db.query(Watchlist).all()
                logger.info(f"📊 查询到 {len(watchlist_items)} 条自选股记录")
                
                symbols = [item.symbol for item in watchlist_items]
                logger.info(f"📋 获取自选股列表: {len(symbols)} 只股票 - {symbols}")
                return symbols
                
        except Exception as e:
            logger.error(f"❌ 获取自选股列表失败: {e}")
            logger.error(f"❌ 错误详情: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
            return []
    
    async def _save_watchlist_analysis_result(self, symbol: str, analysis_result: dict):
        """保存自选股分析结果到AnalysisRecord表"""
        try:
            # 导入分析记录模型（从routes.py导入）
            from backend.routes import AnalysisRecord, SessionLocal as WatchlistSessionLocal
            
            with WatchlistSessionLocal() as db:
                # 创建新的分析记录
                analysis_record = AnalysisRecord(
                    symbol=symbol,
                    score=analysis_result.get('final_score'),  # 修复：使用final_score作为score字段
                    action=analysis_result.get('action'),
                    reason_brief=analysis_result.get('summary'),  # 修复：使用summary作为reason_brief
                    ai_advice=analysis_result.get('ai_analysis'),  # 修复：使用ai_analysis作为ai_advice
                    ai_confidence=analysis_result.get('ai_confidence'),
                    fusion_score=analysis_result.get('fusion_score'),
                    created_at=analysis_result.get('analyzed_at', now_bj())  # 修复：使用created_at而不是analyzed_at
                )
                
                db.add(analysis_record)
                db.commit()
                
                logger.info(f"✅ 自选股 {symbol} 分析结果已保存到AnalysisRecord")
                
        except Exception as e:
            logger.error(f"❌ 保存自选股 {symbol} 分析结果失败: {e}")
    
    async def _update_watchlist_task_details(self, task: RecommendationTask, symbols: List[str], task_subtype: str):
        """更新自选股任务详情信息"""
        with SessionLocal() as db:
            try:
                db_task = db.query(RecommendationTask).filter(RecommendationTask.id == task.id).first()
                if db_task:
                    # 用户输入摘要
                    if task_subtype == 'batch':
                        if len(symbols) == await self._get_watchlist_total_count():
                            db_task.user_input_summary = f"自选股批量分析 | 全部自选股 ({len(symbols)}只)"
                        else:
                            db_task.user_input_summary = f"自选股批量分析 | 指定股票 ({len(symbols)}只): {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}"
                    else:  # reanalyze
                        db_task.user_input_summary = f"自选股重新分析 | 股票代码: {symbols[0]}"
                    
                    # 筛选条件摘要
                    db_task.filter_summary = "自选股票池 | 无额外筛选条件"
                    
                    # 执行策略说明
                    if task_subtype == 'batch':
                        db_task.execution_strategy = "获取自选股列表 → 技术分析 → AI深度分析 → 融合评分 → 更新分析记录"
                    else:
                        db_task.execution_strategy = "验证自选股 → 技术分析 → AI深度分析 → 融合评分 → 更新分析记录"
                    
                    db.commit()
                    logger.info(f"✅ 自选股任务 {task.id} 详情信息已更新")
                    
            except Exception as e:
                db.rollback()
                logger.error(f"❌ 更新自选股任务详情失败: {e}")
    
    async def _get_watchlist_total_count(self) -> int:
        """获取自选股总数"""
        try:
            # 导入自选股相关模型（从routes.py导入）
            from backend.routes import Watchlist, SessionLocal as WatchlistSessionLocal
            
            with WatchlistSessionLocal() as db:
                count = db.query(Watchlist).count()
                return count
                
        except Exception as e:
            logger.error(f"❌ 获取自选股总数失败: {e}")
            return 0
