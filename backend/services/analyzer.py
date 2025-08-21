from typing import Dict, Any
import pandas as pd
import numpy as np

# 一些基础技术指标计算，控制在简洁范围

def moving_average(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=max(1, window // 2)).mean()

def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    roll_up = up.rolling(window).mean()
    roll_down = down.rolling(window).mean()
    rs = np.where(roll_down == 0, 0, roll_up / roll_down)
    rsi_values = 100 - (100 / (1 + rs))
    # 确保返回 pandas.Series 而不是 numpy.ndarray
    return pd.Series(rsi_values, index=series.index)

def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})

def basic_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty or "close" not in df.columns:
        return {"valid": False, "reason": "无数据或缺少收盘价"}
    close = df["close"]
    ma20 = moving_average(close, 20)
    ma60 = moving_average(close, 60)
    rsi14 = rsi(close, 14)
    macd_df = macd(close)

    last = len(close) - 1
    trend_up = ma20.iloc[last] > ma60.iloc[last]
    rsi_ok = 40 <= rsi14.iloc[last] <= 70
    macd_ok = macd_df["macd"].iloc[last] > macd_df["signal"].iloc[last]

    score_parts = [
        0.4 if trend_up else 0.0,
        0.3 if rsi_ok else 0.0,
        0.3 if macd_ok else 0.0,
    ]
    # 连续型评分，提升区分度
    clamp = lambda x, a, b: max(a, min(b, x))
    sigmoid = lambda z: 1.0 / (1.0 + np.exp(-z))
    ma20_cur = float(ma20.iloc[last]); ma60_cur = float(ma60.iloc[last])
    rsi_cur = float(rsi14.iloc[last]); macd_cur = float(macd_df["macd"].iloc[last]); signal_cur = float(macd_df["signal"].iloc[last])
    den = ma60_cur if abs(ma60_cur) > 1e-6 else 1e-6
    diff_pct = (ma20_cur - ma60_cur) / den
    trend_comp = clamp((diff_pct + 0.01) / 0.06, 0.0, 1.0)
    rsi_comp = clamp(1.0 - abs(rsi_cur - 50.0) / 30.0, 0.0, 1.0)
    macd_comp = sigmoid((macd_cur - signal_cur) * 8.0)
    score = float(0.45 * trend_comp + 0.30 * rsi_comp + 0.25 * macd_comp)
    action = "buy" if score >= 0.70 else ("hold" if score >= 0.50 else "sell")
    
    # 生成详细的动作建议理由
    def generate_action_reason(action: str, trend_up: bool, rsi_ok: bool, macd_ok: bool, 
                              ma20_val: float, ma60_val: float, rsi_val: float, macd_val: float, signal_val: float) -> str:
        reasons = []
        
        # 趋势分析
        if trend_up:
            reasons.append(f"短期均线MA20({ma20_val:.2f})高于长期均线MA60({ma60_val:.2f})，显示上升趋势")
        else:
            reasons.append(f"短期均线MA20({ma20_val:.2f})低于长期均线MA60({ma60_val:.2f})，显示下降趋势")
        
        # RSI分析
        if rsi_val < 30:
            reasons.append(f"RSI({rsi_val:.1f})处于超卖区间，可能反弹")
        elif rsi_val > 70:
            reasons.append(f"RSI({rsi_val:.1f})处于超买区间，存在回调风险")
        elif rsi_ok:
            reasons.append(f"RSI({rsi_val:.1f})处于健康区间，动能适中")
        else:
            reasons.append(f"RSI({rsi_val:.1f})偏离正常区间")
        
        # MACD分析
        if macd_ok:
            reasons.append(f"MACD({macd_val:.4f})高于信号线({signal_val:.4f})，动量向好")
        else:
            reasons.append(f"MACD({macd_val:.4f})低于信号线({signal_val:.4f})，动量偏弱")
        
        # 根据动作给出建议
        if action == "buy":
            conclusion = "综合技术指标显示积极信号，建议买入"
        elif action == "sell":
            conclusion = "多项技术指标显示风险，建议卖出"
        else:
            conclusion = "技术指标混合，建议持有观望"
        
        return f"{conclusion}。{' '.join(reasons)}"
    
    ma20_val = float(ma20.iloc[last])
    ma60_val = float(ma60.iloc[last])
    rsi_val = float(rsi14.iloc[last])
    macd_val = float(macd_df["macd"].iloc[last])
    signal_val = float(macd_df["signal"].iloc[last])
    
    action_reason = generate_action_reason(action, trend_up, rsi_ok, macd_ok, 
                                         ma20_val, ma60_val, rsi_val, macd_val, signal_val)

    return {
        "valid": True,
        "ma20": ma20_val,
        "ma60": ma60_val,
        "rsi14": rsi_val,
        "macd": macd_val,
        "signal": signal_val,
        "score": score,
        "action": action,
        "action_reason": action_reason,
    }