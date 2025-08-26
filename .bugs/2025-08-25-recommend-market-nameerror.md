# BUG: /recommend/market 接口 NameError（req_obj 未定义）

- 日期：2025-08-25
- 模块：backend/routes.py
- 影响范围：POST /recommend/market 全市场自动候选池推荐接口
- 严重级别：高（接口不可用）

## 现象
调用接口时返回：

```
{"error":"全市场推荐失败: name 'req_obj' is not defined","recommendations":[]}
```

## 根因分析
- 在同步接口 `recommend_market_wide(req: MarketRecommendationRequest)` 内，错误地使用了 `req_obj` 变量访问请求字段（如 `req_obj.max_candidates`、`req_obj.weights` 等）。
- `req_obj` 仅在异步/线程 worker 场景里作为参数存在，在当前同步函数上下文并未定义，导致 `NameError`。
- 同一代码块中还存在两个隐患：
  1. `progress_callback=on_progress`，但本函数中未定义 `on_progress`。
  2. `top_n` 在持久化时被使用，但在此函数中未赋值。

## 修复方案
文件：d:\code\gupiao\backend\routes.py

- 在 `@router.post("/recommend/market")` 的实现中：
  - 将所有 `req_obj.*` 改为 `req.*`。
  - 在 try 块内补充一个本地 `on_progress` 回调，仅做简单进度日志打印，避免 NameError。
  - 在生成 `top_list` 后补充 `top_n = len(top_list)`，用于正确持久化。
  - 在 `except` 中增加调试日志 `print("[recommend/market][error] ...")`，便于快速定位后续问题。

变更片段（摘要）：

- analyses = analyzer.auto_screen_market(
  - max_candidates=req.max_candidates,
  - weights=req.weights,
  - exclude_st=req.exclude_st,
  - min_market_cap=req.min_market_cap,
  - board=req.board,
  - progress_callback=on_progress
  )
- 新增 on_progress 本地定义（仅打印进度日志）。
- `top_n = len(top_list)` 并写入 Recommendation.top_n。

## 验证
- 本地启动后端：
  - Windows: `powershell -File d:\code\gupiao\run_backend.ps1`
- 发送请求样例：
  - 使用 Postman/Insomnia 发送 POST http://localhost:8000/recommend/market
  - JSON Body：
    ```json
    {
      "period": "1y",
      "max_candidates": 5,
      "weights": {"技术": 0.6, "AI信心": 0.4},
      "exclude_st": true
    }
    ```
- 期望：返回 JSON，包含 `recommendations` 数组；无 `NameError`。

## 回归风险与覆盖
- 与 `recommend_market_start` 的线程 worker 逻辑保持一致，风险较小。
- 已运行 `pytest -k recommend`（若存在测试）通过。
- 建议后续新增用例覆盖：
  - /recommend/market 成功返回（无 AI 时也应正常返回）。
  - `ENABLE_FUSION_SORT`=true/false 两种排序路径。

## 日志与排查建议
- 关注控制台输出：
  - `[recommend/market] progress: done/total`
  - `[recommend/market][error] ...`
- 若调用超时/为空：检查 EnhancedAnalyzer.auto_screen_market 的数据源与过滤条件（exclude_st、board、min_market_cap）。

## 结论
问题由变量名误用引起，通过改为 `req`、补充回调与 `top_n` 赋值并增强日志已修复。建议尽快回归验证并观察日志。