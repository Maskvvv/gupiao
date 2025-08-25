# 股票数据分析与推荐系统 📈

面向 A 股/美股的数据抓取、技术面分析、AI 解读与推荐，以及可视化前端。

## 功能特性
- 多数据源：akshare / yfinance
- 增强分析：技术指标打分 + AI 解读 + 融合分（EnhancedAnalyzer）
- 推荐历史持久化：SQLite / MySQL（SQLAlchemy）
- 异步任务：长耗时推荐/批量分析提供任务查询
- 前端：React + Vite + Ant Design + React Query

## 快速开始
1) 安装依赖
- Python: `pip install -r requirements.txt`
- 前端: `cd frontend-web && npm i`

2) 配置环境
- 复制 `.env.example` 为 `.env`，按需填写：
  - DEFAULT_AI_PROVIDER / OPENAI_* / DEEPSEEK_* / GEMINI_*
  - STOCK_DATA_SOURCE（默认 akshare）
  - DATABASE_URL（默认 sqlite:///./a_stock_analysis.db）
  - HOST / PORT / DEBUG 等

3) 启动后端（Windows PowerShell）
- `./run_backend.ps1`
- 或手动：`uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
- 健康检查：`http://localhost:8000/health`
- API 文档：`http://localhost:8000/docs`

4) 启动前端（开发模式）
- `cd frontend-web`
- `npm run dev` → `http://localhost:5173`
- 已配置代理：`/api -> http://localhost:8000`
- 生产预览：`npm run build && npm run preview`（默认 5174）

## 主要 API（简要）
说明：后端将业务路由挂载在 `/api` 前缀下，少量基础路由无前缀（如 `/health`, `/config/ai`）。完整入参/出参请见 Swagger 文档。

通用说明：period 默认 `1y`；部分接口支持 AI 配置（provider/temperature/api_key）与权重 `weights`。

- GET `/health`（无前缀）：健康检查
- GET `/config/ai`（无前缀）：返回默认模型配置
- POST `/api/ai`：AI 咨询，Body: `{ "prompt": "...", "provider"?, "temperature"?, "api_key"? }`
- POST `/api/analyze`：多股票分析与推荐（技术+AI 融合）
  - Body: `{ symbols: string[], period?: string, weights?: object, provider?, temperature?, api_key? }`
- POST `/api/recommend/market`：全市场候选筛选并推荐（同步）
  - Body: `{ period?: string, max_candidates?: number, weights?: object, exclude_st?: boolean, min_market_cap?: number, board?: string, provider?, temperature?, api_key? }`
- 异步任务：
  - POST `/api/recommend/start` → GET `/api/recommend/status/{task_id}` → GET `/api/recommend/result/{task_id}`
  - POST `/api/recommend/market/start`（全市场异步）
  - 关键词选股：POST `/api/recommend/keyword/start`，并配套 `status/result`
- 自选股（Watchlist）：
  - POST `/api/watchlist/add`、DELETE `/api/watchlist/remove/{symbol}`、GET `/api/watchlist/list`
  - 单次批量分析：POST `/api/watchlist/analyze`
  - 异步批量分析：POST `/api/watchlist/analyze/batch/start` + `status/result`
  - 历史：GET `/api/watchlist/history/{symbol}`
- 推荐历史：
  - GET `/api/recommendations/history`
  - GET `/api/recommendations/{rec_id}/details`
  - DELETE `/api/recommendations/{rec_id}`

## 运行测试
- 简易联调脚本：`python test_market_api.py`
  - 可设置环境变量 `BACKEND_URL`（默认 `http://localhost:8000`）。

## 环境变量（摘录）
- 模型：`DEFAULT_AI_PROVIDER`、`OPENAI_*`、`DEEPSEEK_*`、`GEMINI_*`
- 数据源：`STOCK_DATA_SOURCE=akshare|yfinance`、`UPDATE_INTERVAL`、`CACHE_EXPIRY`
- 数据库：`DATABASE_URL`（SQLite/MySQL）
- 应用：`HOST`、`PORT`、`DEBUG`
- 分析：`DEFAULT_ANALYSIS_PERIOD`、`RISK_FREE_RATE`、`MARKET_BENCHMARK`、`DEFAULT_STOCKS`

## 技术栈
- 后端：FastAPI, SQLAlchemy, Pydantic
- 前端：React 18, Vite 5, Ant Design, @tanstack/react-query
- 数据&分析：pandas, numpy, akshare, yfinance
- AI：OpenAI / DeepSeek / Gemini（见 `backend/services/ai_router.py`）

## 项目结构（简要）
```
gupiao/
├── backend/              # FastAPI 后端与业务逻辑
│   ├── main.py           # 应用入口（/health, /config/ai 等）
│   ├── routes.py         # 业务 API（挂载到 /api）
│   ├── routes_recommends.py # 推荐历史查询/删除
│   └── services/         # 数据抓取、分析与AI集成
└── frontend-web/         # React + Vite 前端
```

提示：完整接口与字段约束以 `http://localhost:8000/docs` 为准。