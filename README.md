# 股票数据分析与推荐系统 📈

一个集成AI的智能股票分析系统，支持数据抓取、技术分析、推荐生成和可视化展示。

## 功能特性 ✨

- 🔄 **多数据源**：支持 yfinance 和 akshare 数据源
- 🤖 **多AI模型**：集成 OpenAI、DeepSeek、Gemini
- 📊 **技术分析**：MA、RSI、MACD 指标分析
- 💡 **智能推荐**：基于技术分析的股票推荐
- 🎯 **单股分析**：输入代码获取买卖建议
- 🌐 **Web界面**：Streamlit 构建的友好界面

## 快速开始 🚀

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

复制 `.env.example` 为 `.env` 并填入您的API密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置至少一个AI服务商的API密钥。

### 3. 启动服务

**启动后端：**
```bash
# Windows
./run_backend.ps1

# 或手动启动
uvicorn backend.main:app --reload --port 8000
```

**启动前端：**
```bash
# Windows  
./run_frontend.ps1

# 或手动启动
streamlit run frontend/app.py --server.port 8501
```

### 4. 访问系统

- 前端界面：http://localhost:8501
- API文档：http://localhost:8000/docs

## API接口 📡

### 分析股票
```bash
POST /api/analyze
{
  "symbols": ["AAPL", "MSFT"],
  "period": "1y"
}
```

### 获取推荐
```bash
POST /api/recommend  
{
  "symbols": ["AAPL", "MSFT", "NVDA"],
  "period": "1y"
}
```

### AI咨询
```bash
POST /api/ai
{
  "prompt": "分析一下当前市场趋势"
}
```

## 配置说明 ⚙️

### AI模型配置

在 `.env` 文件中配置：

```env
# 选择默认AI提供商
DEFAULT_AI_PROVIDER=openai

# OpenAI配置
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini

# DeepSeek配置  
DEEPSEEK_API_KEY=your_key
DEEPSEEK_MODEL=deepseek-chat

# Gemini配置
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-pro
```

### 数据源配置

```env
# 选择数据源
STOCK_DATA_SOURCE=yfinance  # yfinance 或 akshare
UPDATE_INTERVAL=300         # 更新间隔（秒）
```

## 技术栈 🛠️

- **后端**：FastAPI + Python
- **前端**：Streamlit
- **数据**：yfinance / akshare
- **分析**：pandas + numpy
- **AI**：OpenAI / DeepSeek / Gemini
- **可视化**：plotly

## 项目结构 📁

```
gupiao/
├── backend/
│   ├── main.py              # FastAPI主应用
│   ├── routes.py            # API路由
│   └── services/
│       ├── ai_router.py     # AI模型路由
│       ├── data_fetcher.py  # 数据抓取
│       └── analyzer.py      # 技术分析
├── frontend/
│   └── app.py              # Streamlit前端
├── requirements.txt        # Python依赖
├── .env.example           # 环境配置示例
└── README.md              # 说明文档
```

## 开发指南 👨‍💻

### 添加新的技术指标

在 `backend/services/analyzer.py` 中添加新的分析函数：

```python
def your_indicator(series: pd.Series) -> pd.Series:
    # 实现您的指标逻辑
    return result
```

### 集成新的AI提供商

在 `backend/services/ai_router.py` 中添加新的完成方法：

```python
def _your_provider_complete(self, prompt: str, model: str) -> str:
    # 实现API调用逻辑
    return response
```

## 许可证 📄

MIT License