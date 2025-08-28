# BUG 文档 - API路径404错误

## 标题
前端自选股页面轮询任务列表时出现404错误

## 重现步骤
1. 启动后端服务 (`./run_backend.ps1`)
2. 启动前端服务 (`./run_frontend.ps1`)
3. 在浏览器中打开自选股页面
4. 观察后端终端日志
5. 可以看到每10秒出现一次 `GET /api/v2/stream/tasks?limit=10 HTTP/1.1" 404 Not Found` 错误

## 日志摘录
```
INFO:     127.0.0.1:xxxx - "GET /api/v2/stream/tasks?limit=10 HTTP/1.1" 404 Not Found
```

## 原因分析
前端API接口路径配置错误：
- **错误路径**: `/api/v2/stream/tasks` 
- **正确路径**: `/api/v2/tasks`

在 `frontend-web/src/api/watchlist.ts` 文件中，任务管理相关的API接口路径包含了多余的 `stream` 前缀，但后端路由配置 (`backend/routes_streaming.py`) 中实际的路径是 `/api/v2/tasks`，不包含 `stream` 前缀。

## 解决方案
修正前端API接口路径，移除多余的 `stream` 前缀：

### 修改文件: `frontend-web/src/api/watchlist.ts`

1. **getTaskList 函数**:
   ```typescript
   // 修改前
   const r = await http.get('/api/v2/stream/tasks', { params })
   // 修改后  
   const r = await http.get('/api/v2/tasks', { params })
   ```

2. **getTaskStatus 函数**:
   ```typescript
   // 修改前
   const r = await http.get(`/api/v2/stream/tasks/${encodeURIComponent(task_id)}/status`)
   // 修改后
   const r = await http.get(`/api/v2/tasks/${encodeURIComponent(task_id)}/status`)
   ```

3. **getTaskResult 函数**:
   ```typescript
   // 修改前
   const r = await http.get(`/api/v2/stream/tasks/${encodeURIComponent(task_id)}/result`)
   // 修改后
   const r = await http.get(`/api/v2/tasks/${encodeURIComponent(task_id)}/results`)
   ```

4. **cancelTask 函数**:
   ```typescript
   // 修改前
   const r = await http.post(`/api/v2/stream/tasks/${encodeURIComponent(task_id)}/cancel`)
   // 修改后
   const r = await http.post(`/api/v2/tasks/${encodeURIComponent(task_id)}/cancel`)
   ```

5. **retryTask 函数**:
   ```typescript
   // 修改前
   const r = await http.post(`/api/v2/stream/tasks/${encodeURIComponent(task_id)}/retry`)
   // 修改后
   const r = await http.post(`/api/v2/tasks/${encodeURIComponent(task_id)}/retry`)
   ```

## 修复后验证步骤
1. 重启后端服务
2. 刷新前端自选股页面
3. 观察后端日志，确认不再出现404错误
4. 验证任务状态显示功能正常工作

## 影响范围
- **影响功能**: 自选股页面的任务状态显示功能
- **影响用户**: 所有使用自选股功能的用户
- **严重程度**: 中等（功能不可用，但不影响核心分析功能）

## 关联 commit/PR
- 修复API路径配置错误
- 文件: `frontend-web/src/api/watchlist.ts`
- 修改内容: 移除任务管理API路径中多余的 `stream` 前缀

## 预防措施
1. 在API接口开发时，确保前后端路径配置一致
2. 添加API路径的集成测试
3. 在代码审查时重点检查API路径配置
4. 考虑使用统一的API路径配置文件