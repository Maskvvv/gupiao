# BUG 文档 - 自选股重新分析接口错误

## 标题
自选股重新分析功能出现模块导入错误和变量未定义错误

## 重现步骤
1. 启动后端服务 (`./run_backend.ps1`)
2. 启动前端服务 (`./run_frontend.ps1`)
3. 在自选股页面点击某只股票的"重新分析"按钮
4. 观察后端终端日志，可以看到500错误

## 错误日志摘录
```
INFO:     127.0.0.1:62408 - "POST /api/watchlist/analyze HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "D:\code\gupiao\backend\routes.py", line 863, in watchlist_analyze
    from backend.services.streaming_task_manager import task_manager
ModuleNotFoundError: No module named 'backend.services.streaming_task_manager'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  ...
  File "D:\code\gupiao\backend\routes.py", line 898, in watchlist_analyze
    logger.error(f"❌ 创建单股分析任务失败: {e}")
NameError: name 'logger' is not defined
```

## 原因分析
在 `backend/routes.py` 文件的 `watchlist_analyze` 函数中存在两个问题：

### 1. 错误的模块导入路径
- **错误代码**: `from backend.services.streaming_task_manager import task_manager`
- **问题**: 模块名称错误，实际应该是 `task_manager` 而不是 `streaming_task_manager`
- **正确路径**: `from backend.services.task_manager import task_manager`

### 2. 未定义的 logger 变量
- **错误代码**: `logger.error(f"❌ 创建单股分析任务失败: {e}")`
- **问题**: 在异常处理块中使用了未定义的 `logger` 变量
- **根本原因**: 文件顶部没有导入和初始化 logger

## 解决方案

### 修改文件: `backend/routes.py`

#### 1. 修正模块导入路径 (第863行)
```python
# 修改前
from backend.services.streaming_task_manager import task_manager

# 修改后
from backend.services.task_manager import task_manager
```

#### 2. 修复 logger 未定义问题 (第898行)
```python
# 修改前
except Exception as e:
    logger.error(f"❌ 创建单股分析任务失败: {e}")
    return {"error": f"创建分析任务失败: {str(e)}"}

# 修改后
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"❌ 创建单股分析任务失败: {e}")
    return {"error": f"创建分析任务失败: {str(e)}"}
```

## 修复后验证步骤
1. 保存修改后的文件
2. 后端服务会自动重载 (StatReload)
3. 在前端自选股页面测试"重新分析"功能
4. 观察后端日志，确认不再出现500错误
5. 验证任务创建和执行流程正常工作

## 影响范围
- **影响功能**: 自选股单股重新分析功能
- **影响用户**: 所有使用自选股重新分析功能的用户
- **严重程度**: 高（核心功能完全不可用）
- **影响时间**: 从任务管理中心重构后到修复前的时间段

## 根本原因
在将自选股分析功能重构到任务管理中心时，存在以下问题：
1. 模块重命名后未同步更新所有引用
2. 异常处理代码中缺少必要的导入语句
3. 代码审查时未充分测试错误处理路径

## 预防措施
1. **完善的集成测试**: 为所有API端点编写集成测试，包括错误场景
2. **代码审查检查清单**: 重点检查模块导入和变量定义
3. **自动化测试**: 在CI/CD流程中包含API功能测试
4. **错误处理标准化**: 统一错误处理模式，避免重复的导入代码
5. **重构后的回归测试**: 重构后必须进行完整的功能回归测试

## 关联 commit/PR
- 修复自选股重新分析接口的模块导入和logger错误
- 文件: `backend/routes.py`
- 修改内容: 
  - 修正 task_manager 模块导入路径
  - 在异常处理中添加 logger 初始化

## 后续改进建议
1. 在文件顶部统一导入和初始化 logger，避免在异常处理中重复导入
2. 考虑使用装饰器或中间件统一处理API异常和日志记录
3. 建立模块重命名的标准流程，确保所有引用都得到更新