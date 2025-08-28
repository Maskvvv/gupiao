# 自选股重新分析后历史记录不显示问题

## 问题标题
自选股票重新分析后，在历史分析中看不到历史记录

## 重现步骤
1. 在自选股页面选择一只股票
2. 点击"更多" -> "重新分析"
3. 等待分析完成
4. 点击"更多" -> "历史"
5. 发现历史记录中没有显示刚才的分析结果

## 日志摘录
```
✅ 自选股 000001 分析结果已保存到AnalysisRecord
```

## 原因分析
在 `streaming_engine_core.py` 的 `_save_watchlist_analysis_result` 方法中，保存分析结果到 `AnalysisRecord` 表时存在字段映射错误：

1. **字段名不匹配**：
   - 保存时使用了 `technical_score`、`ai_score`、`final_score` 等字段
   - 但 `AnalysisRecord` 模型中实际字段名是 `score`
   - 历史查询接口使用 `r.score` 查询，导致查询结果为空

2. **字段映射错误**：
   - `ai_analysis` 应该映射到 `ai_advice` 字段
   - `summary` 应该映射到 `reason_brief` 字段
   - `analyzed_at` 应该映射到 `created_at` 字段

3. **数据库表结构与代码不一致**：
   - `AnalysisRecord` 模型定义的字段与保存逻辑使用的字段不匹配

## 解决方案
修改 `backend/services/streaming_engine_core.py` 文件中的 `_save_watchlist_analysis_result` 方法：

```python
# 修复前
analysis_record = AnalysisRecord(
    symbol=symbol,
    technical_score=analysis_result.get('technical_score'),
    ai_score=analysis_result.get('ai_score'),
    fusion_score=analysis_result.get('fusion_score'),
    final_score=analysis_result.get('final_score'),
    action=analysis_result.get('action'),
    ai_analysis=analysis_result.get('ai_analysis'),
    ai_confidence=analysis_result.get('ai_confidence'),
    ai_reasoning=analysis_result.get('ai_reasoning'),
    summary=analysis_result.get('summary'),
    analyzed_at=analysis_result.get('analyzed_at', now_bj())
)

# 修复后
analysis_record = AnalysisRecord(
    symbol=symbol,
    score=analysis_result.get('final_score'),  # 修复：使用final_score作为score字段
    action=analysis_result.get('action'),
    reason_brief=analysis_result.get('summary'),  # 修复：使用summary作为reason_brief
    ai_advice=analysis_result.get('ai_analysis'),  # 修复：使用ai_analysis作为ai_advice
    ai_confidence=analysis_result.get('ai_confidence'),
    fusion_score=analysis_result.get('fusion_score'),
    created_at=analysis_result.get('analyzed_at', now_bj())  # 修复：使用created_at而不是analyzed_at
)
```

## 修复后验证步骤
1. 重启后端服务
2. 执行自选股重新分析：
   ```bash
   Invoke-WebRequest -Uri "http://localhost:8000/api/v2/watchlist/reanalyze/start" -Method POST -ContentType "application/json" -Body '{"symbol": "000001", "period": "1y"}'
   ```
3. 等待任务完成
4. 查询历史记录：
   ```bash
   Invoke-WebRequest -Uri "http://localhost:8000/api/watchlist/history/000001" -Method GET
   ```
5. 确认返回结果包含最新的分析记录
6. 在前端页面验证历史记录正常显示

## 影响范围
- **影响功能**：自选股重新分析功能的历史记录显示
- **影响用户**：所有使用自选股重新分析功能的用户
- **数据影响**：修复前的分析记录可能存在字段为空的情况，但不影响数据完整性

## 关联 Commit/PR
- 修复字段映射问题的代码变更
- 文件：`backend/services/streaming_engine_core.py`
- 方法：`_save_watchlist_analysis_result`

## 预防措施
1. **代码审查**：确保数据库模型字段与业务逻辑代码保持一致
2. **单元测试**：为数据保存和查询逻辑添加单元测试
3. **集成测试**：添加端到端测试验证完整的分析流程
4. **文档更新**：更新数据库表结构文档，明确字段用途和映射关系

## 修复时间
2025-08-28 17:50:00

## 修复状态
✅ 已修复并验证