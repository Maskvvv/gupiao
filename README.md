# 股票数据分析与推荐系统 📈

面向 A 股/美股的数据抓取、技术面分析、AI 解读与推荐，以及可视化前端。采用流式推荐系统架构，支持异步任务处理和实时进度跟踪。

## 功能特性
- **多数据源**：akshare（A股）/ yfinance（美股）
- **增强分析**：技术指标打分 + AI 解读 + 融合分（EnhancedAnalyzer）
- **流式推荐系统**：异步任务处理，实时进度跟踪，支持关键词选股和全市场扫描
- **数据库支持**：SQLite / MySQL（SQLAlchemy）
- **现代化前端**：React + Vite + Ant Design + React Query
- **AI 集成**：支持 OpenAI、DeepSeek、Google Gemini 多种 AI 服务

## 快速开始

### 1. 安装依赖
```bash
# Python 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend-web && npm install
```

### 2. 配置环境
复制 `.env.example` 为 `.env`，按需填写：
- **AI 配置**：DEFAULT_AI_PROVIDER / OPENAI_* / DEEPSEEK_* / GEMINI_*
- **数据源**：STOCK_DATA_SOURCE（默认 akshare）
- **数据库**：DATABASE_URL（默认 sqlite:///./a_stock_analysis.db）
- **服务配置**：HOST / PORT / DEBUG 等

### 3. 启动服务

#### 后端服务（推荐使用脚本）
```powershell
# Windows PowerShell（推荐）
./run_backend.ps1

# 或手动启动
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端服务
```powershell
# Windows PowerShell（推荐）
./run_frontend.ps1

# 或手动启动
cd frontend-web
npm run dev
```

### 4. 访问应用
- **前端界面**：http://localhost:5173
- **API 文档**：http://localhost:8000/docs
- **健康检查**：http://localhost:8000/health

## 主要功能模块

### 🔍 智能选股系统
- **关键词选股**：基于关键词筛选相关股票并进行 AI 分析
- **全市场扫描**：从全市场候选股票中筛选优质标的
- **自定义推荐**：手动选择股票进行分析和推荐

### 📊 技术分析引擎
- **多维度评分**：技术指标、趋势分析、支撑阻力位
- **AI 深度解读**：结合市场数据进行智能分析
- **融合评分系统**：技术分析与 AI 分析的智能融合

### 📈 实时任务系统
- **异步处理**：长耗时分析任务异步执行
- **实时进度**：任务执行进度实时跟踪
- **结果持久化**：分析结果自动保存到数据库

### 🎯 自选股管理
- **股票收藏**：添加/删除自选股票
- **批量分析**：一键分析所有自选股票
- **历史记录**：查看股票历史分析结果

## 核心 API 接口

### 基础接口
- `GET /health` - 健康检查
- `GET /config/ai` - AI 配置信息
- `POST /api/ai` - AI 咨询服务

### 股票分析
- `POST /api/analyze` - 多股票分析与推荐
- `POST /api/recommend/market` - 全市场推荐（同步）
- `POST /api/recommend/market/start` - 全市场推荐（异步）

### 关键词选股
- `POST /api/recommend/keyword/start` - 启动关键词选股任务
- `GET /api/recommend/keyword/status/{task_id}` - 查询任务状态
- `GET /api/recommend/keyword/result/{task_id}` - 获取任务结果

### 异步任务管理
- `POST /api/recommend/start` - 启动推荐任务
- `GET /api/recommend/status/{task_id}` - 查询任务状态
- `GET /api/recommend/result/{task_id}` - 获取任务结果

### 自选股管理
- `POST /api/watchlist/add` - 添加自选股
- `DELETE /api/watchlist/remove/{symbol}` - 删除自选股
- `GET /api/watchlist/list` - 获取自选股列表
- `POST /api/watchlist/analyze` - 分析自选股（同步）
- `POST /api/watchlist/analyze/batch/start` - 批量分析（异步）
- `GET /api/watchlist/history/{symbol}` - 股票历史分析

## 数据库架构

### 流式推荐系统表结构
- **recommendation_tasks** - 推荐任务主表
- **recommendation_results** - 推荐结果表
- **task_progress** - 任务进度记录
- **task_schedules** - 任务调度配置
- **system_metrics** - 系统性能指标

### 基础功能表
- **watchlist** - 自选股列表
- **analysis_records** - 分析记录表

## 技术栈

### 后端技术
- **框架**：FastAPI + Uvicorn
- **数据库**：SQLAlchemy + SQLite/MySQL
- **数据分析**：pandas, numpy, scipy
- **AI 集成**：OpenAI, DeepSeek, Google Gemini
- **数据源**：akshare（A股）, yfinance（美股）

### 前端技术
- **框架**：React 18 + TypeScript
- **构建工具**：Vite 5
- **UI 组件**：Ant Design
- **状态管理**：@tanstack/react-query
- **开发工具**：ESLint + Prettier

## 项目结构

```
gupiao/
├── backend/                    # 后端服务
│   ├── main.py                # FastAPI 应用入口
│   ├── routes.py              # 主要业务路由
│   ├── routes_streaming.py    # 流式推荐路由
│   ├── routes_analysis_logs.py # 分析日志路由
│   ├── models/                # 数据模型
│   │   ├── streaming_models.py # 流式推荐模型
│   │   └── ...
│   ├── services/              # 业务服务
│   │   ├── ai_router.py       # AI 服务路由
│   │   ├── enhanced_analyzer.py # 增强分析器
│   │   ├── streaming_recommender.py # 流式推荐引擎
│   │   └── ...
│   └── ...
├── frontend-web/              # 前端应用
│   ├── src/
│   │   ├── features/          # 功能模块
│   │   │   ├── recommend/    # 推荐功能
│   │   │   ├── watchlist/    # 自选股功能
│   │   │   └── ...
│   │   ├── api/              # API 接口
│   │   ├── components/       # 通用组件
│   │   └── ...
│   ├── package.json
│   └── ...
├── db_init_mysql.sql          # MySQL 数据库初始化脚本
├── db_init_streaming_mysql.sql # 流式系统数据库脚本
├── requirements.txt           # Python 依赖
├── run_backend.ps1           # 后端启动脚本
├── run_frontend.ps1          # 前端启动脚本
└── README.md
```

## 环境变量配置

### AI 服务配置
```env
DEFAULT_AI_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1
DEEPSEEK_API_KEY=your_deepseek_key
GEMINI_API_KEY=your_gemini_key
```

### 数据源配置
```env
STOCK_DATA_SOURCE=akshare
UPDATE_INTERVAL=3600
CACHE_EXPIRY=1800
```

### 数据库配置
```env
# SQLite（默认）
DATABASE_URL=sqlite:///./a_stock_analysis.db

# MySQL
# DATABASE_URL=mysql+pymysql://user:password@localhost:3306/gupiao?charset=utf8mb4
```

### 应用配置
```env
HOST=0.0.0.0
PORT=8000
DEBUG=true
DEFAULT_ANALYSIS_PERIOD=1y
RISK_FREE_RATE=0.03
MARKET_BENCHMARK=000300.SH
```

## 开发指南

### 运行测试
```bash
# 简易联调测试
python test_market_api.py

# 设置测试后端地址
BACKEND_URL=http://localhost:8000 python test_market_api.py
```

### 数据库迁移
```bash
# 初始化流式推荐系统数据库
python backend/init_db.py

# MySQL 数据库初始化
mysql -u root -p < db_init_mysql.sql
```

### 代码规范
- 遵循 PEP 8 编码规范
- 使用 TypeScript 进行前端开发
- 提交前运行代码格式化和检查
- 编写必要的单元测试

## 更新日志

### v2.0.0 - 流式推荐系统
- ✨ 全新的流式推荐系统架构
- 🚀 异步任务处理和实时进度跟踪
- 📊 增强的数据库模型和性能优化
- 🎯 关键词选股和智能筛选功能
- 🔧 移除旧的推荐历史功能，采用新的任务管理系统
- 💡 改进的用户界面和交互体验

## 许可证

MIT License

## 贡献指南

欢迎提交 Issue 和 Pull Request！请确保：
1. 遵循项目的代码规范
2. 添加必要的测试用例
3. 更新相关文档
4. 提供清晰的提交信息

---

💡 **提示**：完整的 API 接口文档请访问 `http://localhost:8000/docs`