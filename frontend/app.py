import os
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import time

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="分析与推荐", layout="wide")

st.title("分析与推荐")

# 侧边栏设置
with st.sidebar:
    st.header("基础设置")
    backend_url = st.text_input("后端地址", value=BACKEND_URL)
    default_symbols = st.text_input("A股代码（逗号分隔）", value="000001, 000002, 300750, 600036")
    period = st.selectbox("历史周期", ["6mo", "1y", "2y", "5y"], index=1)
    
    st.divider()
    
    # AI配置面板
    st.header("🤖 AI配置面板")
    
    # 获取默认配置
    try:
        config_resp = requests.get(f"{backend_url}/config/ai", timeout=10)
        ai_config = config_resp.json() if config_resp.status_code == 200 else {}
    except:
        ai_config = {}
    
    # AI模型选择
    provider_options = ["deepseek", "openai", "gemini"]
    default_provider = ai_config.get("default_provider", "deepseek")
    ai_provider = st.selectbox("AI模型", provider_options, 
                               index=provider_options.index(default_provider) if default_provider in provider_options else 0)
    
    # 温度设置
    temperature = st.slider("温度(Temperature)", min_value=0.0, max_value=2.0, value=0.3, step=0.1,
                           help="控制AI回答的随机性，值越高越随机")
    
    # API密钥配置
    api_key = st.text_input(f"{ai_provider.upper()} API密钥", type="password", 
                           help="留空则使用服务器配置的密钥")
    
    # 自定义提示词
    custom_prompt = st.text_area("自定义提示词前缀", 
                                placeholder="请根据A股市场特点分析以下数据...",
                                help="将添加到AI分析请求前")
    
    st.divider()
    st.subheader("⚖️ 多维度权重设置")
    # 权重滑块，保证总和≈1
    col1, col2, col3 = st.columns(3)
    with col1:
        w_tech = st.slider("技术面", 0.0, 1.0, 0.4, 0.05)
    with col2:
        w_macro = st.slider("宏观情绪", 0.0, 1.0, 0.35, 0.05)
    with col3:
        w_news = st.slider("新闻事件", 0.0, 1.0, 0.25, 0.05)
    total_w = w_tech + w_macro + w_news
    if abs(total_w - 1.0) > 0.01:
        st.caption(f"当前总权重：{total_w:.2f}（建议≈1.00）")
    weights = {"technical": float(w_tech), "macro_sentiment": float(w_macro), "news_events": float(w_news)}

    # 实时显示区域
    st.divider()
    st.subheader("💡 AI解读结果")
    ai_result_container = st.container()
    
    # 存储AI配置到session state
    st.session_state.ai_config = {
        "provider": ai_provider,
        "temperature": temperature,
        "api_key": api_key if api_key else None,
        "custom_prompt": custom_prompt
    }
    st.session_state.weights = weights

# Tabs
rec_tab, single_tab, history_tab = st.tabs(["🧠 AI推荐", "🔍 单股分析", "🗂 推荐历史"])

# 帮助方法：渲染动作标签
ACTION_COLORS = {
    "buy": "#16a34a",   # 绿色
    "hold": "#f59e0b",  # 黄色
    "sell": "#dc2626"   # 红色
}

get_action_badge = lambda action: f"<span style='background:{ACTION_COLORS.get(action, '#64748b')};color:#fff;padding:2px 8px;border-radius:12px;font-size:12px'>{action or 'N/A'}</span>"

with rec_tab:
    st.subheader("根据行情推荐可购买股票")
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        gen_manual = st.button("生成推荐（使用输入列表）")
    with c2:
        topn = st.slider("Top N", min_value=5, max_value=50, value=10, step=5,
                         help="控制本次全市场筛选返回的候选数量，值越大耗时越久")
    with c3:
        gen_market = st.button("全市场自动推荐（AI精排）")
    
    # 关键词筛选功能
    st.divider()
    st.subheader("🔍 关键词智能筛选")
    keyword_col1, keyword_col2 = st.columns([3, 1])
    with keyword_col1:
        keyword = st.text_input("输入关键词进行智能筛选", 
                               placeholder="例如：稳定币、新能源、医药、芯片等",
                               help="AI将根据关键词从A股市场中筛选相关股票，然后进行精排推荐")
    with keyword_col2:
        gen_keyword = st.button("🚀 关键词推荐", type="primary")

    if gen_manual:
        symbols = [s.strip() for s in default_symbols.split(",") if s.strip()]
        if not symbols:
            st.warning("请先输入股票代码")
        else:
            try:
                payload = {"symbols": symbols, "period": period, "weights": st.session_state.weights}
                cfg = st.session_state.get("ai_config", {})
                payload.update({k: cfg.get(k) for k in ("provider", "temperature", "api_key")})
                
                # 启动异步任务
                r = requests.post(f"{backend_url}/api/recommend/start", json=payload, timeout=30)
                if r.status_code != 200:
                    st.error(f"启动任务失败: {r.text}")
                else:
                    task_id = r.json().get("task_id")
                    if not task_id:
                        st.error("未获得任务ID")
                    else:
                        prog = st.progress(0, text="正在分析股票...")
                        status_area = st.empty()
                        
                        # 轮询任务状态
                        while True:
                            s = requests.get(f"{backend_url}/api/recommend/status/{task_id}", timeout=10)
                            sj = s.json()
                            if sj.get("status") == "not_found":
                                status_area.warning("任务不存在或已过期")
                                break
                            percent = int(sj.get("percent", 0))
                            done = sj.get("done", 0)
                            total = sj.get("total", 0)
                            prog.progress(min(max(percent, 0), 100), text=f"进度 {done}/{total}（{percent}%）")
                            if sj.get("status") in ("done", "error"):
                                break
                            time.sleep(0.6)
                        
                        # 获取结果
                        res = requests.get(f"{backend_url}/api/recommend/result/{task_id}", timeout=30)
                        data = res.json()
                        if data.get("error"):
                            st.error(f"任务失败: {data.get('error')}")
                        else:
                            recs = data.get("recommendations", [])
                            rec_id = data.get("rec_id")
                            if rec_id:
                                st.success(f"已保存推荐批次，ID: {rec_id}")
                            if not recs:
                                st.info("未返回推荐结果")
                            else:
                                df_rec = pd.DataFrame(recs)
                                st.dataframe(df_rec, use_container_width=True)
            except Exception as e:
                st.error(f"请求失败: {e}")

    if gen_market:
        try:
            payload = {"period": period, "max_candidates": int(topn), "weights": st.session_state.weights}
            cfg = st.session_state.get("ai_config", {})
            payload.update({k: cfg.get(k) for k in ("provider", "temperature", "api_key")})
            # 1) 启动后台任务
            r = requests.post(f"{backend_url}/api/recommend/market/start", json=payload, timeout=30)
            if r.status_code != 200:
                st.error(f"启动任务失败: {r.text}")
            else:
                task_id = r.json().get("task_id")
                if not task_id:
                    st.error("未获得任务ID")
                else:
                    prog = st.progress(0, text="正在分析候选股票...")
                    status_area = st.empty()
                    # 2) 轮询进度
                    while True:
                        s = requests.get(f"{backend_url}/api/recommend/market/status/{task_id}", timeout=10)
                        sj = s.json()
                        if sj.get("status") == "not_found":
                            status_area.warning("任务不存在或已过期")
                            break
                        percent = int(sj.get("percent", 0))
                        done = sj.get("done", 0)
                        total = sj.get("total", 0)
                        prog.progress(min(max(percent, 0), 100), text=f"进度 {done}/{total}（{percent}%）")
                        if sj.get("status") in ("done", "error"):
                            break
                        time.sleep(0.6)
                    # 3) 拉取结果
                    res = requests.get(f"{backend_url}/api/recommend/market/result/{task_id}", timeout=30)
                    data = res.json()
                    if data.get("error"):
                        st.error(f"任务失败: {data.get('error')}")
                    else:
                        recs = data.get("recommendations", [])
                        rec_id = data.get("rec_id")
                        if rec_id:
                            st.success(f"已保存推荐批次，ID: {rec_id}")
                        if not recs:
                            st.info("未返回推荐结果")
                        else:
                            df_rec = pd.DataFrame(recs)
                            st.dataframe(df_rec, use_container_width=True)
        except Exception as e:
            st.error(f"请求失败: {e}")

    if gen_keyword:
        if not keyword.strip():
            st.warning("请先输入关键词")
        else:
            try:
                payload = {
                    "keyword": keyword.strip(),
                    "period": period, 
                    "max_candidates": int(topn), 
                    "weights": st.session_state.weights
                }
                cfg = st.session_state.get("ai_config", {})
                payload.update({k: cfg.get(k) for k in ("provider", "temperature", "api_key")})
                
                # 启动关键词筛选任务
                r = requests.post(f"{backend_url}/api/recommend/keyword/start", json=payload, timeout=30)
                if r.status_code != 200:
                    st.error(f"启动任务失败: {r.text}")
                else:
                    task_id = r.json().get("task_id")
                    if not task_id:
                        st.error("未获得任务ID")
                    else:
                        prog = st.progress(0, text=f"正在根据关键词'{keyword}'筛选股票...")
                        status_area = st.empty()
                        
                        # 轮询任务状态
                        while True:
                            s = requests.get(f"{backend_url}/api/recommend/keyword/status/{task_id}", timeout=10)
                            sj = s.json()
                            if sj.get("status") == "not_found":
                                status_area.warning("任务不存在或已过期")
                                break
                            percent = int(sj.get("percent", 0))
                            done = sj.get("done", 0)
                            total = sj.get("total", 0)
                            prog.progress(min(max(percent, 0), 100), text=f"关键词筛选进度 {done}/{total}（{percent}%）")
                            if sj.get("status") in ("done", "error"):
                                break
                            time.sleep(0.6)
                        
                        # 获取结果
                        res = requests.get(f"{backend_url}/api/recommend/keyword/result/{task_id}", timeout=30)
                        data = res.json()
                        if data.get("error"):
                            st.error(f"任务失败: {data.get('error')}")
                        else:
                            recs = data.get("recommendations", [])
                            rec_id = data.get("rec_id")
                            filtered_count = data.get("filtered_count", 0)
                            if rec_id:
                                st.success(f"已保存推荐批次，ID: {rec_id}")
                            if filtered_count > 0:
                                st.info(f"🎯 根据关键词'{keyword}'筛选出 {filtered_count} 只相关股票")
                            if not recs:
                                st.info("未返回推荐结果")
                            else:
                                df_rec = pd.DataFrame(recs)
                                st.dataframe(df_rec, use_container_width=True)
            except Exception as e:
                st.error(f"请求失败: {e}")
with single_tab:
    st.subheader("单股分析")
    symbol = st.text_input("股票代码", value="000001")
    if st.button("分析该股票"):
        if not symbol.strip():
            st.warning("请输入股票代码")
        else:
            try:
                payload = {"symbols": [symbol.strip()], "period": period, "weights": st.session_state.weights}
                cfg = st.session_state.get("ai_config", {})
                payload.update({k: cfg.get(k) for k in ("provider", "temperature", "api_key")})
                resp = requests.post(f"{backend_url}/api/analyze", json=payload, timeout=180)
                data = resp.json()
                results = data.get("results", [])
                if not results:
                    st.info("未返回分析结果")
                else:
                    r = results[0]
                    st.write("动作建议:", unsafe_allow_html=True)
                    st.markdown(get_action_badge(r.get('action')), unsafe_allow_html=True)
                    st.write(f"评分: {r.get('score')}")
                    reason = r.get("action_reason")
                    with st.expander("📌 理由详解", expanded=True):
                        st.write(reason or "(暂无理由详解)")
                    with st.container():
                        st.subheader("AI解读")
                        st.write(r.get("ai_advice") or "(无AI解读)")
            except Exception as e:
                st.error(f"请求失败: {e}")
with history_tab:
    st.subheader("历史推荐记录")
    try:
        page = st.number_input("页码", value=1, min_value=1, step=1)
        page_size = st.slider("每页数量", 5, 50, 10)
        start_date = st.date_input("开始日期", value=None)
        end_date = st.date_input("结束日期", value=None)
        params = {
            "page": int(page),
            "page_size": int(page_size)
        }
        if start_date:
            params["start_date"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["end_date"] = end_date.strftime("%Y-%m-%d")
        hist_resp = requests.get(f"{backend_url}/api/recommendations/history", params=params, timeout=30)
        hist = hist_resp.json()
        if hist.get("records"):
            df_hist = pd.DataFrame(hist["records"])
            st.dataframe(df_hist, use_container_width=True)
            selected_id = st.number_input("查看详情ID", value=int(df_hist.iloc[0]["id"]) if not df_hist.empty else 0)
            if st.button("查看详情") and selected_id:
                d_resp = requests.get(f"{backend_url}/api/recommendations/{int(selected_id)}/details", timeout=30)
                d = d_resp.json()
                items = d.get("items", [])
                if items:
                    for item in items:
                        with st.expander(f"{item.get('股票名称')}（{item.get('股票代码')}） - 评分 {item.get('评分')}"):
                            st.markdown(get_action_badge(item.get("建议动作")), unsafe_allow_html=True)
                            st.write("理由简述：", item.get("理由简述"))
                            st.write("AI详细分析：")
                            st.write(item.get("AI详细分析") or "无AI分析")
                else:
                    st.info("该记录暂无明细或已删除")
        else:
            st.caption("暂无历史记录")
    except Exception as e:
        st.error(f"加载历史失败: {e}")