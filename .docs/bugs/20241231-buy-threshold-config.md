# BUG修复文档：将买入阈值改为可配置环境变量

## 标题
将action为buy的逻辑从固定阈值6.5改为可配置的融合分≥7，并支持环境变量配置

## 问题描述
原代码中买入建议的阈值硬编码为6.5，用户希望将其改为7.0，并且做成可配置的环境变量，以便灵活调整投资建议的阈值。

## 重现步骤
1. 查看 `backend/services/streaming_engine_utils.py` 中的 `_determine_action` 方法
2. 发现买入阈值硬编码为 `fusion_score >= 6.5`
3. 持有阈值硬编码为 `fusion_score >= 4.0`

## 原因分析
- 投资建议阈值硬编码在代码中，缺乏灵活性
- 无法根据市场环境或用户需求动态调整阈值
- 不符合配置化管理的最佳实践

## 解决方案

### 1. 添加环境变量配置
在 `.env.example` 文件中添加新的配置项：
```env
# 投资建议阈值配置
BUY_THRESHOLD=7.0  # 买入建议的融合分数阈值（0-10分制），≥此分数推荐买入
HOLD_THRESHOLD=4.0  # 持有建议的融合分数阈值（0-10分制），≥此分数且<买入阈值推荐持有
```

### 2. 修改代码实现
在 `backend/services/streaming_engine_utils.py` 中：
- 导入 `os` 模块
- 添加环境变量读取逻辑
- 修改 `_determine_action` 方法使用配置变量

```python
# 从环境变量获取投资建议阈值配置
BUY_THRESHOLD = float(os.getenv("BUY_THRESHOLD", "7.0"))
HOLD_THRESHOLD = float(os.getenv("HOLD_THRESHOLD", "4.0"))

def _determine_action(self, fusion_score: float) -> str:
    """根据融合分数确定投资建议"""
    if fusion_score >= BUY_THRESHOLD:
        return "buy"
    elif fusion_score >= HOLD_THRESHOLD:
        return "hold"
    else:
        return "sell"
```

## 修复后验证步骤
1. 重启后端服务
2. 检查启动日志中是否显示正确的配置值：
   - `[CONFIG] BUY_THRESHOLD = 7.0`
   - `[CONFIG] HOLD_THRESHOLD = 4.0`
3. 测试股票分析功能，验证融合分≥7时显示"buy"建议
4. 测试融合分在4-7之间时显示"hold"建议
5. 测试融合分<4时显示"sell"建议

## 影响范围
- **影响模块**：流式推荐系统的投资建议逻辑
- **影响功能**：所有股票分析结果的action字段
- **向后兼容性**：完全兼容，提供默认值
- **配置要求**：用户可选择在.env文件中自定义阈值

## 关联文件
- `.env.example` - 添加新的环境变量配置项
- `backend/services/streaming_engine_utils.py` - 修改投资建议逻辑

## 测试结果
✅ 后端服务成功启动并加载配置
✅ 配置值正确显示在启动日志中
✅ 代码修改符合现有架构模式

## 备注
- 默认买入阈值从6.5提升到7.0，提高了买入建议的标准
- 配置采用浮点数类型，支持小数点精度调整
- 遵循了项目中其他环境变量的命名和使用模式