from typing import Dict, Any, List
import pandas as pd
import numpy as np
from .analyzer import basic_analysis
from .ai_router import AIRouter, AIRequest
from .confidence_fusion import extract_confidence_and_fusion

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
            # 新增：强制第一行输出多维摘要，便于前端“理由简述”直接使用
            "输出格式要求：",
            "- 第一行：多维摘要：技术面要点；宏观/情绪要点；新闻/事件要点 | 建议：买入/持有/卖出（信心y/10）| 一句话理由",
            "- 正文：按上述结构展开，总字数控制在250字以内，语言专业精炼",
            "- 最后一行：最终建议：xxx（信心y/10）| 理由：...",
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
            # 提取 AI 信心并计算融合分
            tech_analysis = extract_confidence_and_fusion(tech_analysis, ai_advice)
        except Exception as e:
            ai_msg = f"AI分析暂时不可用: {str(e)}"
            tech_analysis["ai_advice"] = ai_msg
            tech_analysis["weights_used"] = weights or self.default_weights
            # 即便AI异常，也尝试基于已有信息计算融合分（将回退到技术分）
            tech_analysis = extract_confidence_and_fusion(tech_analysis, ai_msg)
            
        return tech_analysis
    
    def bulk_analyze(self, symbols: List[str], period: str = "1y", weights: Dict[str, float] = None, ai_params: Dict[str, Any] = None, progress_callback=None) -> List[Dict[str, Any]]:
        """批量分析多只股票（支持权重配置）
        progress_callback: 可选回调，形如 lambda done, total: ...，用于上报进度
        """
        from .data_fetcher import DataFetcher
        
        fetcher = DataFetcher()
        results = []
        total = len(symbols)
        
        for idx, symbol in enumerate(symbols):
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
            finally:
                # 上报进度
                try:
                    progress_callback and progress_callback(idx + 1, total)
                except Exception:
                    pass
        
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
    
    def auto_screen_market(self, max_candidates: int = 50, weights: Dict[str, float] = None, exclude_st: bool = True, min_market_cap: float = None, board: str = None, ai_params: Dict[str, Any] = None, progress_callback=None) -> List[Dict[str, Any]]:
        """
        全市场自动筛选候选股票
        
        Args:
            max_candidates: 最大候选股票数量
            weights: 多维度权重配置
            ai_params: AI参数
            progress_callback: 进度上报回调（done, total）
        
        Returns:
            筛选出的候选股票分析结果
        """
        market_stocks = self.get_market_stocks(exclude_st=exclude_st, min_market_cap=min_market_cap, board=board)
        
        if not market_stocks:
            return []
        
        # 为了演示，这里随机采样一部分股票进行分析（实际可根据预筛选条件优化）
        import random
        sample_size = min(max_candidates * 3, len(market_stocks))  # 采样3倍候选数量
        sampled_stocks = random.sample(market_stocks, sample_size)
        
        # 批量分析（带进度回调）
        analyses = self.bulk_analyze(sampled_stocks, weights=weights, ai_params=ai_params, progress_callback=progress_callback)
        
        # 筛选有效结果并按评分排序
        valid_analyses = [a for a in analyses if a.get("valid") and a.get("score", 0) > 0.4]
        valid_analyses.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return valid_analyses[:max_candidates]
    
    def keyword_screen_market(self, keyword: str, period: str = "1y", max_candidates: int = 50, 
                             weights: Dict[str, float] = None, exclude_st: bool = True, 
                             min_market_cap: float = None, board: str = None, ai_params: Dict[str, Any] = None, 
                             progress_callback=None) -> List[Dict[str, Any]]:
        """
        基于关键词的AI智能股票筛选
        
        Args:
            keyword: 筛选关键词（如"稳定币"、"新能源"等）
            period: 分析周期
            max_candidates: 最大候选股票数量
            weights: 多维度权重配置
            exclude_st: 是否排除ST股票
            min_market_cap: 最小市值要求
            ai_params: AI参数
            progress_callback: 进度上报回调（done, total）
        
        Returns:
            筛选出的相关股票分析结果
        """
        # 获取全市场股票池
        market_stocks = self.get_market_stocks(exclude_st=exclude_st, min_market_cap=min_market_cap, board=board)
        
        if not market_stocks:
            return []
        
        # 第一阶段：AI关键词筛选
        if progress_callback:
            progress_callback(0, 2)  # 两个主要阶段
        
        filtered_stocks = self._ai_keyword_filter(market_stocks, keyword, ai_params)
        
        if progress_callback:
            progress_callback(1, 2)
        
        if not filtered_stocks:
            if progress_callback:
                progress_callback(2, 2)
            return []
        
        # 第二阶段：对筛选出的股票进行详细分析
        # 限制分析数量以控制耗时
        analysis_limit = min(len(filtered_stocks), max_candidates * 2)
        stocks_to_analyze = filtered_stocks[:analysis_limit]
        
        # 创建新的进度回调，映射到第二阶段
        def analysis_progress_callback(done, total):
            if progress_callback:
                # 第二阶段占总进度的一半：映射为 [1, 2] / 总计 2 个阶段
                overall_done = 1 + (done / max(total, 1))
                progress_callback(min(round(overall_done, 2), 2), 2)
        
        analyses = self.bulk_analyze(
            stocks_to_analyze, 
            period=period,
            weights=weights, 
            ai_params=ai_params, 
            progress_callback=analysis_progress_callback
        )
        
        # 筛选有效结果并按评分排序
        valid_analyses = [a for a in analyses if a.get("valid") and a.get("score", 0) > 0.3]
        valid_analyses.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        if progress_callback:
            progress_callback(2, 2)
        
        return valid_analyses[:max_candidates]
    
    def _ai_keyword_filter(self, stocks: List[str], keyword: str, ai_params: Dict[str, Any] = None) -> List[str]:
        """
        使用AI根据关键词筛选相关股票
        
        Args:
            stocks: 股票代码列表
            keyword: 筛选关键词
            ai_params: AI参数
        
        Returns:
            筛选出的相关股票代码列表
        """
        print(f"[DEBUG] AI关键词筛选开始，关键词: {keyword}, 股票数量: {len(stocks)}")
        
        # 构建AI筛选提示词
        prompt = self._build_keyword_filter_prompt(stocks, keyword)
        print(f"[DEBUG] 提示词长度: {len(prompt)} 字符")
        
        try:
            ai_request = AIRequest(
                prompt=prompt,
                provider=ai_params.get("provider") if ai_params else None,
                temperature=ai_params.get("temperature", 0.3) if ai_params else 0.3,
                api_key=ai_params.get("api_key") if ai_params else None
            )
            
            print(f"[DEBUG] 调用AI接口，提供商: {ai_request.provider}")
            response = self.ai.complete(ai_request)
            print(f"[DEBUG] AI响应: {response[:200]}..." if len(response) > 200 else f"[DEBUG] AI响应: {response}")
            
            # 解析AI返回的股票代码
            filtered_stocks = self._parse_ai_filter_response(response, stocks)
            print(f"[DEBUG] AI筛选结果: {len(filtered_stocks)} 只股票 - {filtered_stocks[:10]}")
            
            if not filtered_stocks:
                print(f"[DEBUG] AI筛选结果为空，使用降级策略")
                return self._fallback_keyword_filter(stocks, keyword)
            
            return filtered_stocks
            
        except Exception as e:
            print(f"[DEBUG] AI关键词筛选失败: {e}")
            # 降级策略：简单的字符串匹配筛选
            fallback_result = self._fallback_keyword_filter(stocks, keyword)
            print(f"[DEBUG] 降级策略结果: {len(fallback_result)} 只股票")
            return fallback_result
    
    def _build_keyword_filter_prompt(self, stocks: List[str], keyword: str) -> str:
        """
        构建关键词筛选的AI提示词
        """
        # 获取股票代码和名称信息
        try:
            import akshare as ak
            stock_info = ak.stock_info_a_code_name()
            code_name_map = dict(zip(stock_info['code'], stock_info['name']))
        except:
            code_name_map = {}
        
        # 限制股票数量以避免提示词过长
        stock_sample = stocks[:100] if len(stocks) > 100 else stocks
        
        # 构建股票代码和名称的列表
        stock_info_list = []
        for code in stock_sample:
            name = code_name_map.get(code, "未知")
            stock_info_list.append(f"{code}({name})")
        
        stocks_str = ", ".join(stock_info_list)
        
        prompt = f"""请根据关键词"{keyword}"从以下A股股票中筛选出最相关的股票。

关键词：{keyword}

股票列表（代码(名称)）：
{stocks_str}

请分析每个股票对应的公司业务是否与关键词"{keyword}"相关，并返回最相关的股票代码。

要求：
1. 只返回6位数字的股票代码，用逗号分隔
2. 按相关性从高到低排序
3. 最多返回20个股票代码
4. 重点考虑公司的主营业务、产品服务、行业分类等因素
5. 如果没有高度相关的股票，可以选择部分相关的

示例格式：000001,000002,300750

请直接返回股票代码，不要包含其他解释文字："""
        
        return prompt
    
    def _parse_ai_filter_response(self, response: str, original_stocks: List[str]) -> List[str]:
        """
        解析AI筛选响应，提取有效的股票代码
        """
        if not response:
            return []
        
        # 提取股票代码
        import re
        # 匹配6位数字的股票代码
        stock_pattern = r'\b\d{6}\b'
        found_codes = re.findall(stock_pattern, response)
        
        # 验证股票代码是否在原始列表中
        valid_codes = [code for code in found_codes if code in original_stocks]
        
        # 去重并保持顺序
        seen = set()
        filtered_codes = []
        for code in valid_codes:
            if code not in seen:
                seen.add(code)
                filtered_codes.append(code)
        
        return filtered_codes

    def get_market_stocks(self, exclude_st: bool = True, min_market_cap: float = None, board: str = None) -> List[str]:
        """
        获取全市场A股股票代码列表，并可选过滤：
        - exclude_st: 是否排除 ST/*ST 股票（通过名称包含“ST”判断）
        - min_market_cap: 最小总市值（单位：亿元）。当无法解析市值时跳过该过滤。
        
        返回：6位股票代码列表
        """
        try:
            import akshare as ak
            import pandas as pd  # 保证本地命名空间有 pd
        except Exception:
            # akshare 不可用时直接返回空
            return []

        codes: List[str] = []
        try:
            # 优先使用行情快照（含总市值、名称等）
            spot = ak.stock_zh_a_spot_em()
            if spot is not None and not spot.empty:
                df = spot.copy()
                # 标准列名（东财接口通常为：代码、名称、总市值、流通市值 等）
                code_col = "代码" if "代码" in df.columns else ("code" if "code" in df.columns else None)
                name_col = "名称" if "名称" in df.columns else ("name" if "name" in df.columns else None)
                mcap_col = None
                for c in ["总市值", "总市值(元)", "总市值(万元)", "总市值(亿)", "market_cap", "总市值-最新"]:
                    if c in df.columns:
                        mcap_col = c
                        break
                if code_col is None:
                    raise ValueError("缺少代码列")

                # 过滤 ST
                if exclude_st and name_col is not None:
                    df = df[~df[name_col].astype(str).str.contains("ST", case=False, na=False)]

                # 过滤市值
                def parse_to_yi(v) -> float:
                    """将各种格式的总市值转换为“亿元”为单位的浮点值。失败返回 None。"""
                    if v is None:
                        return None
                    try:
                        # 数字直接按“元”处理
                        if isinstance(v, (int, float)):
                            # 如果值很大，默认认为以“元”为单位，转为“亿”
                            return float(v) / 1e8
                        s = str(v)
                        # 处理常见带单位的字符串
                        if "万亿" in s:
                            import re
                            num = float(re.sub(r"[^0-9\.]", "", s))
                            return num * 10000.0
                        if "亿" in s:
                            import re
                            num = float(re.sub(r"[^0-9\.]", "", s))
                            return num
                        # 可能是纯数字字符串（单位元）
                        f = float(s)
                        return f / 1e8
                    except Exception:
                        return None

                if mcap_col is not None and min_market_cap is not None:
                    parsed = df[mcap_col].map(parse_to_yi)
                    df = df[parsed.notna() & (parsed >= float(min_market_cap))]

                # 板块过滤
                if board:
                    prefixes = (
                        ['300'] if board == 'gem' else
                        ['688'] if board == 'star' else
                        ['000','001','002','003','004','600','601','603','605'] if board == 'main' else
                        []
                    )
                    if prefixes:
                        df = df[df[code_col].astype(str).str.startswith(tuple(prefixes))]

                codes = [str(c).zfill(6) for c in df[code_col].astype(str).tolist() if str(c).isdigit()]
                # 去重保持顺序
                seen = set()
                codes = [c for c in codes if not (c in seen or seen.add(c))]
                return codes
        except Exception as _:
            # 回退到基础代码-名称接口
            pass

        # Fallback：仅获取代码与名称（不支持市值过滤）
        try:
            stock_info = ak.stock_info_a_code_name()
            if stock_info is not None and not stock_info.empty:
                df2 = stock_info.copy()
                code_col = "code" if "code" in df2.columns else ("代码" if "代码" in df2.columns else None)
                name_col = "name" if "name" in df2.columns else ("名称" if "名称" in df2.columns else None)
                if code_col is None:
                    return []
                if exclude_st and name_col is not None:
                    df2 = df2[~df2[name_col].astype(str).str.contains("ST", case=False, na=False)]
                # 板块过滤
                if board:
                    prefixes = (
                        ['300'] if board == 'gem' else
                        ['688'] if board == 'star' else
                        ['000','001','002','003','004','600','601','603','605'] if board == 'main' else
                        []
                    )
                    if prefixes:
                        df2 = df2[df2[code_col].astype(str).str.startswith(tuple(prefixes))]

                codes = [str(c).zfill(6) for c in df2[code_col].astype(str).tolist() if str(c).isdigit()]
                # 去重
                seen = set()
                codes = [c for c in codes if not (c in seen or seen.add(c))]
                return codes
        except Exception:
            return []

        return codes