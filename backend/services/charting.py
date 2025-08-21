import pandas as pd
import plotly.graph_objects as go
from typing import Optional


def kline_chart(df: pd.DataFrame, title: str = "K线图") -> Optional[dict]:
    if df.empty:
        return None
    cols = [c.lower() for c in df.columns]
    date_col = "date" if "date" in cols else ("datetime" if "datetime" in cols else None)
    if not date_col:
        return None
    fig = go.Figure(data=[go.Candlestick(
        x=df[date_col],
        open=df["open"], high=df["high"], low=df["low"], close=df["close"]
    )])
    fig.update_layout(title=title, xaxis_title="日期", yaxis_title="价格", xaxis_rangeslider_visible=False)
    return fig.to_dict()