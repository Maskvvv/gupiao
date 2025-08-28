---
trigger: always_on
alwaysApply: true
---

# gupiao 项目开发规范

## 🚀 项目启动规则 (强制执行)

### 后端项目启动
- **必须使用脚本**: `./run_backend.ps1`
- 脚本功能: 自动设置 PYTHONPATH 环境变量并启动 FastAPI 服务器
- 端口: 8000

### 前端项目启动
- **必须使用脚本**: `./run_frontend.ps1`
- 脚本功能: 自动检查依赖、安装依赖、启动 Vite 开发服务器
- 端口: 5173

### ❌ 严格禁止的启动方式
- `uvicorn backend.main:app --reload`
- `cd frontend-web && npm run dev`
- `python -m backend.main`
- 任何其他非脚本启动方式

**原因**: 确保环境变量设置、统一开发环境、避免路径依赖问题

## 📝 Python 编码规范

### 🏗️ 项目结构组织规范 (强制执行)

#### 标准项目目录结构
```
gupiao/                     # 项目根目录
├── .env                   # 环境变量配置
├── .gitignore            # Git忽略文件
├── requirements.txt      # Python依赖
├── README.md            # 项目说明文档
├── run_backend.ps1      # 后端启动脚本
├── run_frontend.ps1     # 前端启动脚本
├── backend/             # 后端代码目录
│   ├── __init__.py
│   ├── main.py          # FastAPI应用入口
│   ├── routes/          # 路由模块
│   │   ├── __init__.py
│   │   ├── api.py       # API路由
│   │   └── health.py    # 健康检查路由
│   ├── services/        # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── stock_service.py
│   │   ├── ai_service.py
│   │   └── analysis_service.py
│   ├── models/          # 数据模型
│   │   ├── __init__.py
│   │   ├── database.py  # 数据库连接
│   │   ├── schemas.py   # Pydantic模型
│   │   └── entities.py  # SQLAlchemy实体
│   ├── core/            # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py    # 配置管理
│   │   ├── security.py  # 安全相关
│   │   └── database.py  # 数据库配置
│   ├── utils/           # 工具函数
│   │   ├── __init__.py
│   │   ├── helpers.py   # 通用工具
│   │   └── validators.py # 数据验证
│   └── dependencies/    # FastAPI依赖注入
│       ├── __init__.py
│       └── auth.py      # 认证依赖
├── tests/               # 测试代码目录 (强制要求)
│   ├── __init__.py
│   ├── conftest.py      # pytest配置
│   ├── unit/            # 单元测试
│   │   ├── __init__.py
│   │   ├── test_services/
│   │   ├── test_models/
│   │   └── test_utils/
│   ├── integration/     # 集成测试
│   │   ├── __init__.py
│   │   └── test_api/
│   └── fixtures/        # 测试数据
│       └── test_data.json
├── docs/                # 文档目录
│   ├── api_docs.md
│   └── project_rules.md
└── frontend-web/        # 前端代码目录
    ├── src/
    ├── public/
    └── package.json
```

#### ❌ 严格禁止的代码组织方式
- **禁止在项目根目录放置业务逻辑代码**
- **禁止测试代码与业务代码混放**
- **禁止在业务模块中放置测试文件**
- **禁止使用中文文件名或目录名**
- **禁止创建没有 `__init__.py` 的包目录**

### 🔧 模块拆分规范

#### 按功能拆分模块
- **routes/**: 所有HTTP路由处理器，按功能模块分文件
- **services/**: 业务逻辑层，核心功能实现
- **models/**: 数据模型层，包含数据库实体和API模型
- **core/**: 核心配置和基础设施代码
- **utils/**: 可复用的工具函数
- **dependencies/**: FastAPI依赖注入相关代码

#### 模块命名规范
- 使用小写字母和下划线: `stock_service.py`
- 避免使用缩写: `authentication.py` 而不是 `auth.py`
- 功能明确的命名: `stock_analysis_service.py`
- 测试文件前缀 `test_`: `test_stock_service.py`

#### 导入规范
```python
# 1. 标准库导入
import os
import sys
from datetime import datetime
from typing import List, Optional

# 2. 第三方库导入
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 3. 本地应用导入
from backend.core.config import settings
from backend.models.schemas import StockData
from backend.services.stock_service import StockService
```

### 🧪 测试代码组织规范 (强制执行)

#### 测试目录结构要求
- **必须创建独立的 `tests/` 目录**
- **测试目录必须在项目根目录下**
- **测试文件必须以 `test_` 开头**
- **测试目录结构必须镜像业务代码结构**

#### 测试文件组织
```
tests/
├── __init__.py              # 必须包含
├── conftest.py             # pytest全局配置
├── unit/                   # 单元测试
│   ├── __init__.py
│   ├── test_services/      # 服务层测试
│   │   ├── __init__.py
│   │   ├── test_stock_service.py
│   │   └── test_ai_service.py
│   ├── test_models/        # 模型层测试
│   │   ├── __init__.py
│   │   └── test_schemas.py
│   └── test_utils/         # 工具函数测试
│       ├── __init__.py
│       └── test_helpers.py
├── integration/            # 集成测试
│   ├── __init__.py
│   └── test_api/
│       ├── __init__.py
│       ├── test_stock_routes.py
│       └── test_health_routes.py
└── fixtures/               # 测试数据
    ├── __init__.py
    ├── stock_data.json
    └── mock_responses.py
```

#### 测试代码编写规范
```python
# test_stock_service.py
import pytest
from unittest.mock import Mock, patch
from backend.services.stock_service import StockService
from backend.models.schemas import StockData

class TestStockService:
    """股票服务测试类"""
    
    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.stock_service = StockService()
    
    def test_get_stock_data_success(self):
        """测试获取股票数据成功场景"""
        # Given
        symbol = "000001"
        expected_data = StockData(symbol=symbol, price=10.5)
        
        # When
        with patch('akshare.stock_zh_a_hist') as mock_ak:
            mock_ak.return_value = pd.DataFrame({...})
            result = self.stock_service.get_stock_data(symbol)
        
        # Then
        assert result.symbol == symbol
        assert isinstance(result.price, float)
        mock_ak.assert_called_once_with(symbol)
    
    def test_get_stock_data_failure(self):
        """测试获取股票数据失败场景"""
        # Given
        invalid_symbol = "INVALID"
        
        # When & Then
        with pytest.raises(ValueError):
            self.stock_service.get_stock_data(invalid_symbol)
```

#### pytest配置文件 (conftest.py)
```python
import pytest
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(scope="session")
def test_app():
    """测试应用实例"""
    from backend.main import app
    return app

@pytest.fixture
def mock_database():
    """模拟数据库连接"""
    # 测试数据库配置
    pass
```

### 代码质量要求
- 使用 `black` 进行代码格式化
- 使用 `flake8` 进行代码风格检查
- 使用 `pytest` 进行单元测试
- 遵循 PEP 8 编码规范
- 必须使用类型注解 (Type Hints)

### 文档规范
- 复杂函数必须编写 docstring
- 使用有意义的变量和函数命名
- 关键业务逻辑添加注释
- 每个模块必须包含模块级docstring

### 配置文件管理
```python
# backend/core/config.py
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """应用配置"""
    
    # 数据库配置
    database_url: str = "sqlite:///./app.db"
    
    # API配置
    api_title: str = "Stock Analysis API"
    api_version: str = "1.0.0"
    
    # AI服务配置
    openai_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

**重要提醒**: 严格按照上述结构组织代码，违反结构规范的代码不允许提交！

## 🗄️ 数据库规范

### 技术栈
- ORM: SQLAlchemy
- 支持数据库: SQLite (默认) / MySQL
- 配置方式: 环境变量 `DATABASE_URL`

### 开发规范
- 数据库变更需要提供迁移脚本
- 保持向后兼容性
- 测试环境和生产环境分离

## 🌐 API 开发规范

### 接口设计
- 所有业务接口使用 `/api` 前缀
- 遵循 RESTful 设计风格
- 正确使用 HTTP 状态码
- 统一错误响应格式

### 异步处理
- 长耗时操作必须使用异步任务模式
- 提供任务状态查询接口
- 实现任务结果获取机制

## 🔒 安全规范

### 敏感信息管理
- API 密钥存储在 `.env` 文件中
- 禁止在代码中硬编码敏感信息
- 生产环境必须关闭 DEBUG 模式

### 输入验证
- 使用 Pydantic 进行严格输入验证
- 防止 SQL 注入和安全漏洞
- 对用户输入进行过滤和转义

## 🏗️ 技术栈信息

### 后端技术栈
- Framework: FastAPI
- Server: Uvicorn
- Database: SQLAlchemy + SQLite/MySQL
- Data Analysis: pandas, numpy, scipy
- AI Integration: OpenAI, DeepSeek, Google Gemini
- Data Sources: akshare (A股), yfinance (美股)

### 前端技术栈
- Framework: React 18
- Build Tool: Vite 5
- UI Library: Ant Design
- State Management: @tanstack/react-query
- Language: TypeScript

### 开发工具
- Python 3.8+
- Node.js + npm
- 代码编辑器: Qoder IDE

## 📋 开发流程规范

### 代码提交前检查
1. 运行代码格式化: `black .`
2. 运行代码检查: `flake8`
3. 运行单元测试: `pytest`
4. 确保所有测试通过

### 新功能开发
1. 创建功能分支
2. 编写功能代码
3. 编写单元测试
4. 更新文档
5. 代码审查
6. 合并到主分支

**重要提醒**: 所有代码修改都必须严格遵循以上规范，特别是项目启动规则不可违背！