# 自选股重新分析功能缺失方法错误

## 问题描述
自选股重新分析功能不可用，后端报错提示 `TaskManager` 对象没有 `create_watchlist_reanalyze_task` 方法。

## 重现步骤
1. 打开前端自选股页面
2. 点击某只股票的"重新分析"按钮
3. 后端报错：`'TaskManager' object has no attribute 'create_watchlist_reanalyze_task'`

## 错误日志摘录
```
ERROR:backend.routes:❌ 创建单股分析任务失败: 'TaskManager' object has no attribute 'create_watchlist_reanalyze_task'
```

## 原因分析
在 `backend/services/task_manager.py` 文件中，虽然系统设计支持自选股重新分析功能，但缺少了 `create_watchlist_reanalyze_task` 方法的实现。

相关组件状态：
- ✅ `streaming_models.py` 中已定义 `watchlist_reanalyze` 任务类型
- ✅ `streaming_engine_core.py` 中已有 `_process_watchlist_reanalyze` 处理方法
- ✅ `routes_streaming.py` 中已有对应的API接口
- ❌ `task_manager.py` 中缺少 `create_watchlist_reanalyze_task` 方法

## 解决方案
在 `backend/services/task_manager.py` 文件中添加 `create_watchlist_reanalyze_task` 方法：

```python
async def create_watchlist_reanalyze_task(self, symbol: str,
                                        period: str = "1y",
                                        weights: Optional[Dict[str, float]] = None,
                                        ai_config: Optional[Dict[str, Any]] = None,
                                        priority: int = 5) -> str:
    """创建自选股重新分析任务"""
    task_id = str(uuid.uuid4()).replace('-', '')
    
    request_params = {
        'symbols': [symbol],
        'period': period
    }
    
    weights_config = weights or {
        "technical": 0.4,
        "macro_sentiment": 0.35,
        "news_events": 0.25
    }
    
    ai_config = ai_config or {}
    
    # 创建任务记录
    with SessionLocal() as db:
        # 生成用户详情摘要
        user_input_summary = f"重新分析股票: {symbol} | 分析周期: {period}"
        
        weights_str = ', '.join([f'{k}({v})' for k, v in weights_config.items()])
        filter_summary = f'权重配置: {weights_str}'
        
        execution_strategy = "单股重新分析 → 技术分析 → AI深度分析 → 融合评分 → 输出结果"
        
        task = RecommendationTask(
            id=task_id,
            task_type='watchlist_reanalyze',
            status='pending',
            priority=priority,
            request_params=json.dumps(request_params),
            ai_config=json.dumps(ai_config),
            weights_config=json.dumps(weights_config),
            total_symbols=1,
            # 用户详情字段
            user_input_summary=user_input_summary,
            filter_summary=filter_summary,
            execution_strategy=execution_strategy
        )
        db.add(task)
        db.commit()
    
    logger.info(f"✅ 创建自选股重新分析任务: {task_id}, 股票: {symbol}")
    return task_id
```

## 修复后验证步骤
1. 重启后端服务
2. 打开前端自选股页面
3. 点击某只股票的"重新分析"按钮
4. 验证任务创建成功，不再出现方法缺失错误
5. 检查任务执行流程是否正常

## 影响范围
- **功能影响**: 自选股重新分析功能完全不可用
- **用户体验**: 用户无法对单只自选股进行重新分析
- **系统稳定性**: 不影响其他功能，仅限于此特定功能

## 根本原因
在重构自选股分析功能时，虽然设计了完整的任务管理架构，但在实现过程中遗漏了 `TaskManager` 类中关键方法的实现。

## 预防措施
1. **完整性检查**: 在功能重构时，确保所有设计的方法都有对应实现
2. **集成测试**: 增加端到端测试，覆盖完整的用户操作流程
3. **代码审查**: 重构时进行更仔细的代码审查，确保接口一致性
4. **文档同步**: 及时更新API文档和架构文档，避免实现与设计脱节

## 修复时间
- 发现时间: 2025-01-20
- 修复时间: 2025-01-20
- 验证时间: 2025-01-20

## 相关文件
- `backend/services/task_manager.py` (修改)
- `backend/routes.py` (调用方)
- `backend/services/streaming_engine_core.py` (处理逻辑)
- `backend/models/streaming_models.py` (数据模型)
- `backend/routes_streaming.py` (API接口)