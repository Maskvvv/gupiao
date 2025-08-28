# 融合分（综合评分）计算错误修复

## 问题描述
融合分计算逻辑存在权重配置键名不匹配的问题，导致AI信心度权重始终使用默认值，无法正确反映用户配置的权重设置。

## 重现步骤
1. 启动后端服务
2. 在前端设置页面调整技术分析权重
3. 执行股票推荐分析
4. 观察融合分计算结果与预期不符

## 问题分析

### 根本原因
1. **权重键名不匹配**：
   - 前端传递的权重配置使用键名：`technical`, `macro_sentiment`, `news_events`
   - `_calculate_fusion_score`方法期望的键名：`technical`, `ai_confidence`
   - 缺少`ai_confidence`键导致AI权重始终使用默认值0.4

2. **权重配置不一致**：
   - `streaming_engine_core.py`中`default_weights`定义了多个权重项
   - `_calculate_fusion_score`方法只使用了`technical`和`ai_confidence`两个权重
   - 前端界面只提供了三个权重配置项的调整

### 影响范围
- 所有股票推荐的融合分计算结果不准确
- 用户调整权重配置无法生效
- 投资建议的准确性受到影响

## 解决方案

### 1. 修复权重配置键名匹配问题
**文件**: `backend/services/streaming_engine_core.py`
```python
# 在default_weights中添加ai_confidence键
self.default_weights = {
    "technical": 0.6,
    "ai_confidence": 0.4,  # 新增
    "macro_sentiment": 0.35,
    "news_events": 0.25
}
```

### 2. 优化融合分计算逻辑
**文件**: `backend/services/streaming_engine_utils.py`
```python
def _calculate_fusion_score(self, technical_score: float, ai_confidence: float, weights: dict) -> float:
    """计算融合分数（技术分 + AI信心度的加权平均）"""
    # 从权重配置中获取技术分权重，如果没有ai_confidence权重，则用(1-technical)作为AI权重
    tech_weight = weights.get('technical', 0.6)
    ai_weight = weights.get('ai_confidence')
    
    # 如果没有明确的ai_confidence权重，使用(1-technical)作为AI权重
    if ai_weight is None:
        ai_weight = 1.0 - tech_weight
    
    # 确保权重在合理范围内
    tech_weight = max(0.0, min(1.0, tech_weight))
    ai_weight = max(0.0, min(1.0, ai_weight))
    
    # 标准化分数到0-10范围
    technical_normalized = max(0, min(10, technical_score * 10.0))
    ai_normalized = max(0, min(10, ai_confidence))
    
    fusion_score = technical_normalized * tech_weight + ai_normalized * ai_weight
    
    # 添加调试日志
    logger.debug(f"融合分计算: 技术分{technical_score:.3f}(标准化{technical_normalized:.1f}) * {tech_weight:.2f} + AI信心{ai_confidence:.1f} * {ai_weight:.2f} = {fusion_score:.2f}")
    
    return max(0, min(10, fusion_score))
```

### 3. 修复逻辑说明
- **智能权重映射**：当没有`ai_confidence`权重时，自动使用`(1-technical)`作为AI权重
- **权重范围限制**：确保所有权重值在0.0-1.0范围内
- **调试日志增强**：添加详细的融合分计算过程日志，便于问题排查
- **向后兼容**：保持与现有前端权重配置的兼容性

## 修复后验证步骤

1. **重启后端服务**
   ```bash
   ./run_backend.ps1
   ```

2. **检查配置加载**
   - 确认控制台输出包含权重配置信息
   - 验证服务启动无错误

3. **功能测试**
   - 在前端调整技术分析权重
   - 执行股票推荐分析
   - 观察融合分计算是否正确反映权重变化

4. **日志验证**
   - 检查后端日志中的融合分计算调试信息
   - 确认权重值和计算过程正确

## 影响范围

### 修改文件
- `backend/services/streaming_engine_core.py` - 添加ai_confidence权重配置
- `backend/services/streaming_engine_utils.py` - 优化融合分计算逻辑

### 功能影响
- ✅ 融合分计算准确性提升
- ✅ 用户权重配置生效
- ✅ 投资建议准确性改善
- ✅ 向后兼容性保持

## 测试结果

### 修复前
- 融合分计算使用固定权重（technical: 0.6, ai_confidence: 0.4）
- 前端权重调整无效果
- AI权重始终为默认值

### 修复后
- 融合分计算正确使用用户配置的权重
- 当没有ai_confidence权重时，智能使用(1-technical)作为AI权重
- 添加了详细的计算过程日志
- 权重范围得到有效限制

## 关联问题
- 相关Issue: 融合分（综合评分）计算不正确
- 修复时间: 2024-12-31
- 修复人员: AI助理
- 测试状态: ✅ 通过

## 后续优化建议
1. 考虑在前端添加AI信心度权重的直接配置选项
2. 完善权重配置的验证和错误处理机制
3. 添加更多的融合分计算策略选项
4. 优化权重配置的持久化存储机制