# 流式 AI 改造需求文档

1. 项目概述
- 项目名称：流式 AI 响应与进度推送改造
- 目标：将当前所有涉及 AI 调用的关键路径支持“流式”返回（逐步输出/渐进显示），降低等待感、提升交互体验，并在必要处保留非流式回退能力。
- 背景：现有系统使用同步阻塞式 AI 调用，前端需等待完整结果，用户体验上存在空窗；部分长耗时分析（如全市场推荐/关键词筛选）需要更明确的进度反馈；后端已采用 FastAPI，具备实现 StreamingResponse/SSE 的基础能力。

2. 用户角色
- 普通用户（前端用户）：关注快速得到可读的 AI 分析内容，期望边生成边显示，减少等待焦虑。
- 投研用户（专业用户）：关注长耗时任务进度（%）、关键阶段节点信息，以及最终结果的完整性与可信度。
- 前端开发者：需要易于对接的流式 API（ReadableStream 或 SSE），以及清晰的 chunk 边界与事件语义。
- 后端开发者：需要统一的 AI 流式适配层，便于切换不同 Provider（OpenAI/DeepSeek/Gemini），并具备良好的日志与错误处理机制。
- 运维/DevOps：需要可观测性（日志/指标）、配置化开关、异常回退策略，保障线上稳定性。
- 测试工程师：需要可自动化验证的流式接口与非流式回退路径的测试用例与验收标准。

3. 功能模块
- 模块A：AI 流式适配层（Provider Adapter）
- 模块B：后端 API 路由流式化（StreamingResponse/SSE）
- 模块C：长耗时任务进度推送（SSE，可选）
- 模块D：前端流式消费与渐进式渲染
- 模块E：配置开关、回退与兼容策略
- 模块F：日志与可观测性（DEBUG/INFO/ERROR + 关键打点）
- 模块G：测试与验收（后端/前端）

4. 原子需求清单（User Stories）

模块A：AI 流式适配层
- FUNC-001 作为一个后端开发者，我想要在 <mcfile name="ai_router.py" path="backend/services/ai_router.py"></mcfile> 中新增统一的流式接口（如 stream_complete(req) -> 生成器yield chunk），以便于不同 Provider 输出以一致方式被上层消费。
- FUNC-002 作为一个后端开发者，我想要在流式接口中支持 OpenAI Chat Completions 的流式参数，并将模型增量内容按文本块输出，以便前端实时显示。
- FUNC-003 作为一个后端开发者，我想要在流式接口中支持 DeepSeek Chat Completions 的流式参数，处理服务端分块（含增量/结束标记），以便对齐 OpenAI 的输出语义。
- FUNC-004 作为一个后端开发者，我想要在流式接口中支持 Gemini 的流式生成（若不支持则自动回退为非流式），以便统一 Provider 行为并保证兼容性。
- FUNC-005 作为一个后端开发者，我想要在流式过程中聚合完整文本副本（shadow buffer），以便流式结束后进行“AI 信心值解析与融合分计算”，不影响既有逻辑。
- FUNC-006 作为一个后端开发者，我想要在 Provider 不支持流式或发生错误时自动回退到非流式 complete(req)，以便保证服务可用性。
- FUNC-007 作为一个后端开发者，我想要统一定义流式 chunk 的结构（至少包含 type、data、delta、provider、model、ts），以便前后端约定清晰。
- FUNC-008 作为一个后端开发者，我想要在流式接口中输出“开始/结束/错误”三类控制事件（type=start/end/error），以便前端可正确处理生命周期。

模块B：后端 API 路由流式化
- FUNC-009 作为一个前端开发者，我想要一个新的 POST /ai/stream 接口，返回 StreamingResponse（text/event-stream 或 text/plain chunked），以便在前端即时渲染 AI 输出。
- FUNC-010 作为一个前端开发者，我想要 /ai/stream 支持请求体参数：prompt、provider、model、temperature、api_key、stream=true，以便灵活配置模型与开关。
- FUNC-011 作为一个后端开发者，我想要在 <mcfile name="routes.py" path="backend/routes.py"></mcfile> 中对现有 /ai 同步接口保留不变，并新增 /ai/stream（不破坏兼容），以便平滑迁移。
- FUNC-012 作为一个后端开发者，我想要在 /ai/stream 中逐块输出 AI 文本增量（delta），并在最后输出一个包含完整文本与聚合指标（ai_confidence、fusion_score）的完结块，以便前端既能实时显示又能拿到最终指标。
- FUNC-013 作为一个后端开发者，我想要在 /ai/stream 中输出必要的心跳/注释行（例如每10秒）以保持连接存活，以便提升稳定性。

模块C：长耗时任务进度推送（可选增强）
- FUNC-014 作为一个投研用户，我想要在“全市场推荐/关键词筛选”等接口中获得进度推送（SSE：progress 事件），以便在等待期间获知大致耗时与阶段。
- FUNC-015 作为一个后端开发者，我想要为现有任务型接口（如 recommend_keyword_start / 任务查询）新增 /progress/stream SSE 渠道，以便以事件的形式发送进度、关键里程碑与告警信息。
- FUNC-016 作为一个后端开发者，我想要在 EnhancedAnalyzer 内部调用 AI 时（如 analyze_with_ai、_ai_keyword_filter）能够触发可选的“AI 文本流片段”中继到路由层（若该 API 选择流式返回），以便统一用户体验。

模块D：前端流式消费与渐进式渲染
- FUNC-017 作为一个前端开发者，我想要在前端新增通用的流式消费工具（基于 fetch ReadableStream 或 EventSource），以便便捷复用到多个页面。
- FUNC-018 作为一个普通用户，我想要在“AI 一键解读”页面看到文字逐步出现的效果，并且在末尾看到“信心分与融合分”，以便快速获取结论与可信度。
- FUNC-019 作为一个投研用户，我想要当流式连接异常中断时，前端能显式展示错误提示，并提供“重试/回退为完整加载”的选项，以便不中断工作流。
- FUNC-020 作为一个前端开发者，我想要在列表/弹窗等 UI 容器中支持“加载中骨架 + 流式文本 + 最终指标回填”的交互模式，以便提升一致性与观感。

模块E：配置开关、回退与兼容
- FUNC-021 作为一个运维，我想要在环境变量中新增默认流式开关 DEFAULT_STREAMING=true|false 与 Provider 级能力声明（如 GEMINI_STREAM_SUPPORTED=true|false），以便按需调整行为。
- FUNC-022 作为一个后端开发者，我想要在每个路由允许 query/body 中覆盖 stream=true|false，以便在特定场景下临时关闭流式（如自动化测试）。
- FUNC-023 作为一个后端开发者，我想要在流式超时/错误时自动降级到非流式并记录日志，以便保障 SLA。
- FUNC-024 作为一个测试工程师，我想要确保非流式接口的行为与返回格式不被破坏，以便既有前端与脚本持续可用。

模块F：日志与可观测性
- FUNC-025 作为一个后端开发者，我想要在 Provider 适配层输出 DEBUG/INFO 日志（包含 provider、model、温度、首包耗时、总耗时、chunk 数量），以便后续性能优化与排障。
- FUNC-026 作为一个运维，我想要在错误事件中记录异常类型、HTTP 状态、Provider错误码、失败位置（start/delta/end），以便快速定位问题源头。
- FUNC-027 作为一个后端开发者，我想要在流式路由中对关键步骤（接收请求、调用适配层、首包产出、完成/错误）打印结构化日志，避免泄漏密钥信息，以便安全与可维护性。

模块G：测试与验收
- FUNC-028 作为一个测试工程师，我想要为 /ai/stream 编写集成测试，验证增量文本顺序、完结块结构、异常回退逻辑，以便保障核心体验。
- FUNC-029 作为一个测试工程师，我想要为 Provider 适配层编写单元测试（模拟流式/非流式响应），以便确保多 Provider 行为一致。
- FUNC-030 作为一个测试工程师，我想要为前端流式消费工具编写最小 e2e 测试（可使用 mock server），以便验证渐进渲染与异常处理。
- FUNC-031 作为一个测试工程师，我想要验证在流式路径下，ai_confidence 与 fusion_score 的计算与非流式保持一致（最终完整文本作为输入），以便保证业务一致性。

范围内关键文件与影响面
- 后端核心适配：<mcfile name="ai_router.py" path="backend/services/ai_router.py"></mcfile>
- 后端路由：<mcfile name="routes.py" path="backend/routes.py"></mcfile>（新增 /ai/stream 与可选进度 SSE 路由）
- 分析器内部调用：<mcfile name="enhanced_analyzer.py" path="backend/services/enhanced_analyzer.py"></mcfile>（内部 AI 调用点保持接口兼容，必要时打通可选的流式回调）
- 前端对接：frontend-web/src 下新增流式消费工具与 UI 渐进渲染逻辑

非功能性要求
- 性能：首包时间较同步方案显著改善（目标 < 1.2s，在网络与 Provider 正常情况下）；长文本持续输出不阻塞主循环。
- 稳定性：连接异常可自动重连（前端可配置），后端在 Provider 失败时快速回退非流式；提供心跳维持连接。
- 安全：不在日志/返回中泄漏任何密钥；对错误信息进行适度脱敏。
- 兼容：不破坏现有同步接口与返回格式；新增接口以 /ai/stream 命名，路径清晰。
- 可维护性：适配层面向接口编程，Provider 新增仅需最小改动；日志打点一致。

交付验收标准（示例）
- /ai/stream：
  - 返回首包 < 1.2s；
  - 持续输出 delta 文本片段，结束时输出 end 事件包含 full_text、ai_confidence、fusion_score；
  - 错误时输出 error 事件并回退到非流式（可配置），HTTP 状态码合理；
  - 日志包含首包时间/总时长/chunk 数。
- 任务进度 SSE（若纳入本期）：
  - progress 事件频率合适（不低于 1Hz，且不高于 5Hz），包含 done/total；
  - 断线可重连，不重复推进计数。
- 前端：
  - 渐进渲染稳定，无明显闪烁；
  - 异常提示清晰，支持重试；
  - 最终指标（信心/融合分）与非流式一致。

里程碑与优先级（建议）
- M1（核心）：模块A、B、D 的最小可用闭环（/ai/stream + 前端渐进渲染 + 适配OpenAI/DeepSeek）
- M2（增强）：模块E、F 完成配置化与日志完善；
- M3（可选）：模块C 任务进度 SSE、模块G 全量测试覆盖与文档。

备注
- 若 Gemini 当前 SDK 流式能力受限，则在本期标记不支持（自动回退），在配置中显式记录能力声明，避免前端误判。
- 流式实现建议采用 StreamingResponse（text/event-stream 或 chunked text/plain），并与前端约定统一事件格式。