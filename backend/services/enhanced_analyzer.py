from typing import Dict, Any, List
import pandas as pd
import numpy as np
from .analyzer import basic_analysis
from .ai_router import AIRouter, AIRequest

class EnhancedAnalyzer:
    """增强版分析器，集成AI建议与多维度权重配置"""
    
    def __init__(self):
        self.ai = AIRouter()
        # 默认权重配置：技术面40%，宏观情绪35%，新闻事件25%
        self.default_weights = {
            "technical": 0.4,
            "macro_sentiment": 0.35,
            "news_events": 0.25
        }
    
    def _build_prompt_multi_dim(self, symbol: str, tech: Dict[str, Any], df: pd.DataFrame, weights: Dict[str, float] = None) -> str:
        """
        构建多维度AI分析提示词：支持权重配置的技术面、市场情绪/宏观、新闻/事件
        """
        if weights is None:
            weights = self.default_weights
        
        # 安全计算近期变动，尽量避免数据不足导致报错
        closes = df.get("close") if isinstance(df, pd.DataFrame) else None
        last_close = float(closes.iloc[-1]) if closes is not None and len(closes) > 0 else None
        pct = lambda n: (float(closes.iloc[-1]) / float(closes.iloc[-n]) - 1.0) * 100 if closes is not None and len(closes) >= n else None
        chg_5 = pct(5)
        chg_20 = pct(20)
        chg_60 = pct(60)
        
        # 尽量提供更完整的技术上下文
        ma20 = tech.get('ma20')
        ma60 = tech.get('ma60')
        rsi14 = tech.get('rsi14')
        macd = tech.get('macd')
        signal = tech.get('signal')
        score = tech.get('score')
        action = tech.get('action')
        
        # 统一格式，避免None在字符串中产生歧义
        fmt = lambda v, d: (f"{v:.2f}" if isinstance(v, (int, float)) else d)
        
        lines = [
            f"请对A股股票 {symbol} 进行多维度投资分析，并给出结论。",
            "",
            "【分析权重配置】",
            f"- 技术面权重: {weights['technical']*100:.0f}%",
            f"- 宏观情绪权重: {weights['macro_sentiment']*100:.0f}%", 
            f"- 新闻事件权重: {weights['news_events']*100:.0f}%",
            "",
            "【已知技术指标】",
            f"- MA20: {fmt(ma20, 'N/A')}  |  MA60: {fmt(ma60, 'N/A')}",
            f"- RSI(14): {fmt(rsi14, 'N/A')}  |  MACD: {fmt(macd, 'N/A')}  |  Signal: {fmt(signal, 'N/A')}",
            f"- 技术评分: {fmt(score, 'N/A')}  |  技术面建议: {action or 'N/A'}",
            "",
            "【价格表现（辅助参考）】",
            f"- 最新收盘价: {fmt(last_close, 'N/A')}",
            f"- 近5/20/60日涨跌幅(%): {fmt(chg_5, 'N/A')} / {fmt(chg_20, 'N/A')} / {fmt(chg_60, 'N/A')}",
            "",
            "请按以下结构输出，并根据权重配置侧重分析对应维度：",
            f"1) 技术面分析（权重{weights['technical']*100:.0f}%）：结合均线趋势、动量(RSI/MACD)与可能的形态信号",
            f"2) 市场情绪/宏观分析（权重{weights['macro_sentiment']*100:.0f}%）：综合市场波动、流动性、政策取向、经济数据与行业景气度",
            f"3) 新闻/事件分析（权重{weights['news_events']*100:.0f}%）：从公司公告、行业政策与突发事件角度评估影响",
            "4) 风险点：罗列2-3条主要风险",
            "5) 最终建议：根据权重配置综合各维度，明确给出【买入/持有/卖出】并给出信心(0-10)与一句话理由",
            "",
            '请用简洁、专业的中文输出，总字数控制在250字以内。最后一行以“最终建议：xxx（信心y/10）| 理由：...”格式收束。',
        ]
        return "\n".join(lines)
    
    def analyze_with_ai(self, symbol: str, df: pd.DataFrame, weights: Dict[str, float] = None, ai_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """结合技术分析和AI分析给出综合建议（支持多维度权重配置）"""
        if df.empty:
            return {"valid": False, "reason": "无数据"}
            
        # 基础技术分析
        tech_analysis = basic_analysis(df)
        
        if not tech_analysis.get("valid"):
            return tech_analysis
            
        # 构建多维度AI分析提示（支持权重配置）
        prompt = self._build_prompt_multi_dim(symbol, tech_analysis, df, weights)
        
        try:
            req = AIRequest(
                prompt=prompt,
                provider=(ai_params or {}).get("provider"),
                temperature=(ai_params or {}).get("temperature"),
                api_key=(ai_params or {}).get("api_key"),
            )
            ai_advice = self.ai.complete(req)
            tech_analysis["ai_advice"] = ai_advice
            # 记录使用的权重配置
            tech_analysis["weights_used"] = weights or self.default_weights
        except Exception as e:
            tech_analysis["ai_advice"] = f"AI分析暂时不可用: {str(e)}"
            tech_analysis["weights_used"] = weights or self.default_weights
            
        return tech_analysis
    
    def bulk_analyze(self, symbols: List[str], period: str = "1y", weights: Dict[str, float] = None, ai_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """批量分析多只股票（支持权重配置）"""
        from .data_fetcher import DataFetcher
        
        fetcher = DataFetcher()
        results = []
        
        for symbol in symbols:
            try:
                df = fetcher.get_stock_data(symbol, period=period)
                if df is not None:
                    # 转换列名为兼容格式
                    df_compatible = df.reset_index()
                    df_compatible.columns = [col.lower() for col in df_compatible.columns]
                    analysis = self.analyze_with_ai(symbol, df_compatible, weights, ai_params)
                    analysis["symbol"] = symbol
                    results.append(analysis)
                else:
                    results.append({
                        "symbol": symbol,
                        "valid": False,
                        "reason": "无法获取数据"
                    })
            except Exception as e:
                results.append({
                    "symbol": symbol,
                    "valid": False,
                    "reason": f"分析失败: {str(e)}"
                })
                
        return results
    
    def generate_market_report(self, symbols: List[str], weights: Dict[str, float] = None) -> str:
        """生成市场总体报告（支持权重配置）"""
        analyses = self.bulk_analyze(symbols, weights=weights)
        valid_analyses = [a for a in analyses if a.get("valid")]
        
        if not valid_analyses:
            return "市场数据不足，无法生成报告"
            
        # 统计信息
        buy_count = sum(1 for a in valid_analyses if a.get("action") == "buy")
        hold_count = sum(1 for a in valid_analyses if a.get("action") == "hold")
        sell_count = sum(1 for a in valid_analyses if a.get("action") == "sell")
        avg_score = np.mean([a.get("score", 0) for a in valid_analyses])
        
        used_weights = weights or self.default_weights
        weights_desc = f"技术面{used_weights['technical']*100:.0f}%，宏观{used_weights['macro_sentiment']*100:.0f}%，事件{used_weights['news_events']*100:.0f}%"
        
        # AI生成报告
        prompt = f"""
        基于以下市场统计数据生成简要市场报告：
        - 分析股票数: {len(valid_analyses)}
        - 买入信号: {buy_count}只
        - 持有信号: {hold_count}只  
        - 卖出信号: {sell_count}只
        - 平均技术评分: {avg_score:.2f}
        - 权重配置: {weights_desc}
        
        请分析当前市场情绪和趋势，给出投资建议。控制在200字以内。
        """
        
        try:
            return self.ai.complete(AIRequest(prompt=prompt))
        except Exception:
            return f"当前市场统计（{weights_desc}）：买入{buy_count}，持有{hold_count}，卖出{sell_count}，平均评分{avg_score:.2f}"

    def get_market_stocks(self, exclude_st: bool = True, min_market_cap: float = None) -> List[str]:
        """
        获取A股市场股票列表（用于全市场筛选）
        
        Args:
            exclude_st: 是否排除ST股票
            min_market_cap: 最小市值筛选（亿元）
            
        Returns:
            股票代码列表
        """
        try:
            import akshare as ak
            
            # 获取A股基本信息
            stock_info = ak.stock_info_a_code_name()
            
            if stock_info is None or stock_info.empty:
                return []
            
            codes = stock_info['code'].tolist()
            
            # 排除ST股票
            if exclude_st:
                names = stock_info['name'].tolist()
                codes = [code for code, name in zip(codes, names) 
                        if not any(keyword in name for keyword in ['ST', '*ST', 'PT'])]
            
            # 市值筛选（如果需要的话，这里简化处理）
            if min_market_cap:
                # 这里可以进一步集成市值数据筛选，暂时返回所有代码
                pass
            
            # 返回前1000只，避免全量处理性能问题
            return codes[:1000]
            
        except Exception as e:
            print(f"获取市场股票列表失败: {e}")
            # 返回一些主要指数成分股作为fallback
            return [
                "000001", "000002", "000858", "002415", "002594", "300015", "300122",
                "600000", "600036", "600519", "600887", "601318", "601398", "601888"
            ]
            
    def auto_screen_market(self, max_candidates: int = 50, weights: Dict[str, float] = None, ai_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        全市场自动筛选候选股票
        
        Args:
            max_candidates: 最大候选股票数量
            weights: 多维度权重配置
            
        Returns:
            筛选出的候选股票分析结果
        """
        market_stocks = self.get_market_stocks()
        
        if not market_stocks:
            return []
        
        # 为了演示，这里随机采样一部分股票进行分析（实际可根据预筛选条件优化）
        import random
        sample_size = min(max_candidates * 3, len(market_stocks))  # 采样3倍候选数量
        sampled_stocks = random.sample(market_stocks, sample_size)
        
        # 批量分析
        analyses = self.bulk_analyze(sampled_stocks, weights=weights, ai_params=ai_params)
        
        # 筛选有效结果并按评分排序
        valid_analyses = [a for a in analyses if a.get("valid") and a.get("score", 0) > 0.4]
        valid_analyses.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return valid_analyses[:max_candidates]