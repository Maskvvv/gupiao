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
    default_symbols = st.text_input("代码（逗号分隔）", value="000001, 000002, 300750, 600036")
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
rec_tab, single_tab, history_tab, watchlist_tab = st.tabs(["🧠 AI推荐", "🔍 单股分析", "🗂 推荐历史", "⭐ 自选股票"])

# 帮助方法：渲染动作标签
ACTION_COLORS = {
    "buy": "#16a34a",   # 绿色
    "hold": "#f59e0b",  # 黄色
    "sell": "#dc2626"   # 红色
}

get_action_badge = lambda action: f"<span style='background:{ACTION_COLORS.get(action, '#64748b')};color:#fff;padding:2px 8px;border-radius:12px;font-size:12px'>{action or 'N/A'}</span>"

# 帮助方法：渲染个股历史（上移到首次调用之前，防止未定义）
def render_stock_history(symbol: str, backend_url: str):
    """渲染指定股票的历史分析记录（带分页控件）。"""
    try:
        cc1, cc2 = st.columns([1, 2])
        page = cc1.number_input("页码", min_value=1, value=1, step=1, key=f"hist_page_{symbol}")
        page_size = cc2.slider("每页数量", 5, 50, 10, key=f"hist_page_size_{symbol}")
        params = {"page": int(page), "page_size": int(page_size)}
        resp = requests.get(f"{backend_url}/api/watchlist/history/{symbol}", params=params, timeout=30)
        data = resp.json() if resp.status_code == 200 else {"error": resp.text}
        if data.get("error"):
            st.error(f"获取历史失败：{data.get('error')}")
            return
        items = data.get("items", []) or []
        if not items:
            st.info("暂无分析历史记录")
            return
        df_hist = pd.DataFrame(items)
        st.dataframe(df_hist, use_container_width=True)
        with st.expander("展开每条历史详情", expanded=False):
            for idx, it in enumerate(items):
                # 顶部概览行（时间/分数/动作）
                st.markdown(
                    f"- {it.get('时间')} | 评分: {it.get('综合评分')} | 动作: "
                    + get_action_badge(it.get('操作建议')),
                    unsafe_allow_html=True,
                )
                # 摘要
                brief = it.get("分析理由摘要") or "(无摘要)"
                st.caption(brief)
                # 详细AI分析
                detail = it.get("AI详细分析")
                if detail:
                    with st.expander(f"AI详细分析 - 第{idx+1}条", expanded=False):
                        st.write(detail)
    except Exception as e:
        st.error(f"请求失败：{e}")

with rec_tab:
    st.subheader("根据行情推荐")
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
                                with st.expander("对这些股票进行操作", expanded=False):
                                    for i, item in enumerate(recs):
                                        sym = (item.get("股票代码") or item.get("symbol") or "").strip()
                                        name = (item.get("股票名称") or item.get("name") or sym)
                                        c1, c2, c3 = st.columns([2, 3, 1])
                                        c1.write(sym)
                                        c2.write(name)
                                        if c3.button("加入自选", key=f"manual_add_wl_{sym}_{i}"):
                                            try:
                                                r2 = requests.post(f"{backend_url}/api/watchlist/add", json={"symbol": sym}, timeout=15)
                                                j2 = r2.json() if r2.status_code == 200 else {"error": r2.text}
                                                if j2.get("ok"):
                                                    st.success(f"已加入自选：{sym}")
                                                else:
                                                    st.error(f"添加失败：{j2.get('error') or r2.text}")
                                            except Exception as e2:
                                                st.error(f"请求失败：{e2}")
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
                            with st.expander("对这些股票进行操作", expanded=False):
                                for i, item in enumerate(recs):
                                    sym = (item.get("股票代码") or item.get("symbol") or "").strip()
                                    name = (item.get("股票名称") or item.get("name") or sym)
                                    c1, c2, c3 = st.columns([2, 3, 1])
                                    c1.write(sym)
                                    c2.write(name)
                                    if c3.button("加入自选", key=f"market_add_wl_{sym}_{i}"):
                                        try:
                                            r2 = requests.post(f"{backend_url}/api/watchlist/add", json={"symbol": sym}, timeout=15)
                                            j2 = r2.json() if r2.status_code == 200 else {"error": r2.text}
                                            if j2.get("ok"):
                                                st.success(f"已加入自选：{sym}")
                                            else:
                                                st.error(f"添加失败：{j2.get('error') or r2.text}")
                                        except Exception as e2:
                                            st.error(f"请求失败：{e2}")
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
    csa1, csa2 = st.columns([1,1])
    if csa1.button("分析该股票"):
        if not symbol.strip():
            st.warning("请输入股票代码")
        else:
            try:
                payload = {"symbols": [symbol.strip()], "period": period, "weights": st.session_state.weights}
                cfg = st.session_state.get("ai_config", {})
                payload.update({k: cfg.get(k) for k in ("provider", "temperature", "api_key")})
                resp = requests.post(f"{backend_url}/api/watchlist/analyze", json=payload, timeout=180)
                data = resp.json()
                if data.get("error"):
                    st.error(f"任务失败: {data.get('error')}")
                else:
                    r = data.get("analysis", {})
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
    if csa2.button("加入自选"):
        if not symbol.strip():
            st.warning("请输入股票代码")
        else:
            try:
                ar = requests.post(f"{backend_url}/api/watchlist/add", json={"symbol": symbol.strip()}, timeout=15)
                aj = ar.json() if ar.status_code == 200 else {"error": ar.text}
                if aj.get("ok"):
                    st.success(f"已加入自选：{symbol.strip()}")
                else:
                    st.error(f"添加失败：{aj.get('error') or ar.text}")
            except Exception as e:
                st.error(f"请求失败：{e}")
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
with watchlist_tab:
    st.subheader("自选股票")
    # 添加入口
    add_sym = st.text_input("添加股票代码到自选", value="", placeholder="例如：600036、000001")
    c_add1, c_add2 = st.columns([1,3])
    if c_add1.button("加入自选", key="wl_add_input_btn"):
        s_add = (add_sym or "").strip()
        if not s_add:
            st.warning("请输入股票代码")
        else:
            try:
                r = requests.post(f"{backend_url}/api/watchlist/add", json={"symbol": s_add}, timeout=15)
                j = r.json() if r.status_code == 200 else {"error": r.text}
                if j.get("ok"):
                    st.success(f"已加入自选：{s_add}")
                else:
                    st.error(f"添加失败：{j.get('error') or r.text}")
            except Exception as e:
                st.error(f"请求失败：{e}")
    st.divider()
    # 列表展示
    try:
        lst_resp = requests.get(f"{backend_url}/api/watchlist/list", timeout=30)
        lst = lst_resp.json() if lst_resp.status_code == 200 else {"items": []}
        items = lst.get("items", [])
        if not items:
            st.info("暂无自选股票，快去添加吧～ ✨")
        else:
            df_wl = pd.DataFrame(items)
            st.dataframe(df_wl, use_container_width=True)
            # 个股操作
            st.subheader("个股操作")
            for i, it in enumerate(items):
                sym = it.get("股票代码")
                name = it.get("股票名称")
                c1, c2, c3, c4, c5 = st.columns([2,3,1,1,1])
                c1.write(sym)
                c2.write(name)
                if c3.button("分析", key=f"wl_analyze_{sym}_{i}"):
                    try:
                        payload = {"symbols": [sym], "period": period, "weights": st.session_state.weights}
                        cfg = st.session_state.get("ai_config", {})
                        payload.update({k: cfg.get(k) for k in ("provider", "temperature", "api_key")})
                        r3 = requests.post(f"{backend_url}/api/watchlist/analyze", json=payload, timeout=180)
                        j3 = r3.json()
                        if j3.get("error"):
                            st.error(f"分析失败：{j3.get('error')}")
                        else:
                            st.success(f"分析完成并已保存：{sym}")
                    except Exception as e:
                        st.error(f"请求失败：{e}")
                
                # 历史查看按钮与展示
                hist_state_key = f"show_hist_{sym}"
                if c5.button("历史", key=f"wl_history_{sym}_{i}"):
                    st.session_state[hist_state_key] = not st.session_state.get(hist_state_key, False)
                if st.session_state.get(hist_state_key, False):
                    with st.expander(f"{sym} 历史分析", expanded=True):
                        render_stock_history(sym, backend_url)
                
                if c4.button("移除", key=f"wl_remove_{sym}_{i}"):
                    try:
                        rr = requests.delete(f"{backend_url}/api/watchlist/remove/{sym}", timeout=15)
                        rj = rr.json() if rr.status_code == 200 else {"error": rr.text}
                        if rj.get("ok"):
                            st.success(f"已移除：{sym}")
                            # 同时清理历史显示状态
                            st.session_state.pop(hist_state_key, None)
                        else:
                            st.error(f"移除失败：{rj.get('error') or rr.text}")
                    except Exception as e:
                        st.error(f"请求失败：{e}")
            st.divider()
            # 批量操作
            st.subheader("批量分析")
            all_syms = [it.get("股票代码") for it in items]
            selected_syms = st.multiselect("选择需要批量分析的股票", options=all_syms, default=[])
            if st.button("开始批量分析", type="primary", key="wl_batch_start"):
                if not selected_syms:
                    st.warning("请至少选择一只股票")
                else:
                    try:
                        payload = {"symbols": selected_syms, "period": period, "weights": st.session_state.weights}
                        cfg = st.session_state.get("ai_config", {})
                        payload.update({k: cfg.get(k) for k in ("provider", "temperature", "api_key")})
                        r = requests.post(f"{backend_url}/api/watchlist/analyze/batch/start", json=payload, timeout=30)
                        if r.status_code != 200:
                            st.error(f"启动任务失败: {r.text}")
                        else:
                            task_id = r.json().get("task_id")
                            if not task_id:
                                st.error("未获得任务ID")
                            else:
                                prog = st.progress(0, text="正在批量分析...")
                                status_area = st.empty()
                                while True:
                                    s = requests.get(f"{backend_url}/api/watchlist/analyze/batch/status/{task_id}", timeout=15)
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
                                res = requests.get(f"{backend_url}/api/watchlist/analyze/batch/result/{task_id}", timeout=60)
                                data = res.json()
                                if data.get("error"):
                                    st.error(f"任务失败: {data.get('error')}")
                                else:
                                    items_res = data.get("items", [])
                                    if not items_res:
                                        st.info("未返回结果")
                                    else:
                                        st.success("批量分析完成，结果已持久化保存")
                                        st.dataframe(pd.DataFrame(items_res), use_container_width=True)
                    except Exception as e:
                        st.error(f"请求失败：{e}")
    except Exception as e:
        st.error(f"加载自选列表失败：{e}")

# 帮助方法：渲染个股历史
def render_stock_history(symbol: str, backend_url: str):
    """渲染指定股票的历史分析记录（带分页控件）。"""
    try:
        cc1, cc2 = st.columns([1, 2])
        page = cc1.number_input("页码", min_value=1, value=1, step=1, key=f"hist_page_{symbol}")
        page_size = cc2.slider("每页数量", 5, 50, 10, key=f"hist_page_size_{symbol}")
        params = {"page": int(page), "page_size": int(page_size)}
        resp = requests.get(f"{backend_url}/api/watchlist/history/{symbol}", params=params, timeout=30)
        data = resp.json() if resp.status_code == 200 else {"error": resp.text}
        if data.get("error"):
            st.error(f"获取历史失败：{data.get('error')}")
            return
        items = data.get("items", []) or []
        if not items:
            st.info("暂无分析历史记录")
            return
        df_hist = pd.DataFrame(items)
        st.dataframe(df_hist, use_container_width=True)
        with st.expander("展开每条历史详情", expanded=False):
            for idx, it in enumerate(items):
                # 顶部概览行（时间/分数/动作）
                st.markdown(
                    f"- {it.get('时间')} | 评分: {it.get('综合评分')} | 动作: "
                    + get_action_badge(it.get('操作建议')),
                    unsafe_allow_html=True,
                )
                # 摘要
                brief = it.get("分析理由摘要") or "(无摘要)"
                st.caption(brief)
                # 详细AI分析
                detail = it.get("AI详细分析")
                if detail:
                    with st.expander(f"AI详细分析 - 第{idx+1}条", expanded=False):
                        st.write(detail)
    except Exception as e:
        st.error(f"请求失败：{e}")