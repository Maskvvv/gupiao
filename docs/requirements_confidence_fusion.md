# 评分与AI信心融合 功能 需求设计文档

版本：v1.0  
作者：Trae AI 助手  
状态：已确认（包含你的最新决定）

一、背景与目标
- 背景：推荐结果中，AI 会输出“信心 y/10”的文本，目前未结构化存储，无法与技术分进行融合展示。
- 目标：
  1) 后端解析“信心 y/10”为独立数值字段并保存；
  2) 新增“融合分”字段，并在前端并排展示“技术分 / AI信心 / 融合分”，提供提示说明。

二、范围
- 后端：解析、存储、API输出；
- 前端：列表/卡片展示，数值格式化与 Tooltip 提示；
- 数据：本迭代不做历史数据回填，保证对旧数据不产生副作用（空值安全、回退策略生效）；
- 架构演进：通用表方案本迭代不实施，待第一阶段完成后再评估。

三、决议与约定（包含你的最新确认）
- 技术分范围：0~10（如现有实现不同，融合前归一化到 0~10）；
- AI信心：解析自“y/10”，y ∈ [0,10]，支持小数；
- 融合权重：α=0.4（技术分权重），(1-α)=0.6（AI权重），可通过配置覆盖；
- 显示与精度：技术分/AI信心/融合分均保留两位小数；
- 展示约定：AI 信心显示为“7.50”，范围在 Tooltip 说明为“0~10”；
- 行为建议：操作建议依据融合分（fusion_score）计算；若 ai_confidence 为空则等价于依据技术分；
- 历史数据“信心”来源字段不存在时：ai_confidence 为空（null），不做构造；
- 当 ai_confidence 为空时：最终融合分以技术分为准（fusion_score=tech_score）。

四、数据模型与字段
- 新增字段（表：recommendation_items 与 analysis_records）：
  - recommendation_items：新增 ai_confidence DECIMAL(4,1) NULL、ai_confidence_raw VARCHAR(255) NULL、fusion_score DECIMAL(5,2) NULL
  - analysis_records：新增 ai_confidence DECIMAL(4,1) NULL、ai_confidence_raw VARCHAR(255) NULL、fusion_score DECIMAL(5,2) NULL
  - 注：recommendations 为会话主表，不新增上述字段（如需会话级汇总，另行设计聚合字段）
- 写入规则：
  - 解析成功：写入 ai_confidence 与 ai_confidence_raw；
  - 解析失败或不存在来源字段：均保持 ai_confidence 为空（raw 也为空）；
  - fusion_score 由融合规则计算并写入。

五、解析规则（后端）
- 支持的文本变体：
  - “信心 7/10”“信心: 7/10”“Confidence 7/10”“Confidence: 7/10”
  - 容忍空格/换行/中英文大小写/全角半角符号；支持小数（如 8.5/10）。
- 多匹配时取第一个匹配，并记录 ai_confidence_raw；
- 数值校验：y 超界则截到边界并记 warn 日志；
- 解析失败：ai_confidence=null、ai_confidence_raw=null，记 debug 日志；
- 解析逻辑封装为独立方法，并提供单元测试（整型/小数/变体/多匹配/异常文本）。

六、融合分计算规则（后端）
- 默认：fusion_score = round( tech_score*α + ai_confidence*(1-α), 2 )；
- 当 ai_confidence=null：fusion_score = round(tech_score, 2)（两位小数），并记录“无AI信心，回退技术分”；
- 当 tech_score=null：fusion_score=null，并记告警日志；
- 输出范围限制：最终 fusion_score ∈ [0,10]；
- α 通过配置或环境变量覆盖，默认 0.4；
- 计算逻辑封装为独立方法，并提供单元测试（边界/空值/不同α/四舍五入到两位）。

七、历史数据回填（暂缓至下一阶段）
- 本迭代不进行回填任务开发与执行；
- 兼容要求：
  - 旧记录 ai_confidence 与 fusion_score 默认为空；
  - 融合策略对空值回退为技术分，保证不影响功能与展示；
  - 日志无需统计回填，仅确保服务稳定与API兼容。
- 若历史数据中不存在“信心”来源字段或内容：保持 ai_confidence=null，不做构造；fusion_score 以技术分为准；
- 回填具备幂等性：已有 ai_confidence 的记录不重复覆盖（除非开启强制覆写开关）；
- 分页批量执行并输出统计日志（总数/成功/失败/跳过）；
- 回滚策略：仅新增字段写入，原有业务字段不改，过程可重试。

八、API 合同（后端）
- 在推荐查询/详情接口新增字段：
  - ai_confidence: number|null（0~10，保留两位小数）
  - fusion_score: number|null（0~10，保留两位小数）
- 兼容性：仅新增字段，旧消费者不受影响；
- 如需按 fusion_score 排序，另行开关（默认关闭）。

九、前端展示（React）
- 展示位置：推荐历史页面，建议在同一行并排展示三项：
  - 技术分 / AI信心 / 融合分：示例 7.80 / 7.50 / 7.62；
- Tooltip 提示：
  - 技术分：技术面量化评分（0~10）；
  - AI信心：大模型自信程度（0~10）；
  - 融合分：按权重融合技术分与AI信心（默认技术分权重 0.4）；
- 空值展示：
  - ai_confidence=null 显示“-”；
  - fusion_score=null 显示“-”；
- 数值格式：
  - 技术分：保留两位小数；
  - AI信心：保留两位小数（展示不含“/10”，在 Tooltip 描述范围 0~10）；
  - 融合分：保留两位小数；
- 样式与现有视觉风格一致，移动端与桌面端均不溢出；
- 若有导出/打印，随之导出；若无则忽略。

十、日志与监控（后端）
- 解析失败或越界：warn，包含记录ID与原始片段；
- 回填任务：开始/结束/耗时/结果计数聚合日志；
- 服务启动时打印一次融合权重配置值（info）。

十一、测试与验收
- 后端单测：
  - 解析：整型/小数/中英文/多匹配/异常字符串（如“信心十/10”解析失败）；
  - 融合：α=0.4、边界（0/10）、空值回退（ai=null→fusion=tech）、四舍五入保留两位；
- 集成测试：
  - 新增记录写入字段正确；
  - API 返回包含新增字段，空值语义正确；
- 前端：
  - 展示正确，空值不异常；
  - Tooltip 文案与显示时机正确；
  - 不同数值长度不致布局错位。
- 验收示例：
  - “信心 8/10” + 技术分=7.50（α=0.4）→ ai=8.00，fusion=7.80；
  - “Confidence 7.5/10” → ai=7.50；
  - “信心 十/10” → ai=null，fusion=技术分（两位小数）；
  - 缺少技术分 → fusion=null。

十二、实施建议与位置
- 后端（Python）：
  - 解析/融合逻辑：backend/services/enhanced_analyzer.py 或 analyzer.py；
  - 路由输出：backend/routes_recommends.py；
  - 数据库变更：参考 db_init_mysql.sql 的风格新增 ALTER 语句；
  - 操作建议：沿用既有阈值/规则，但以 fusion_score 为输入依据（ai 缺失等价于技术分）。
- 前端（React + Vite）：
  - 页面：frontend-web/src/features/recommend/pages/RecommendHistoryPage.tsx；
  - 如有公共评分组件，统一封装复用。

十三、部署顺序
1) 数据库加列
2) 后端上线解析/融合能力
3) 前端上线展示（空值安全）
4) 如需开启“按融合分排序”，再行开关

十四、变更记录
- v1.0：确认“历史数据无信心来源字段时保持空值，融合分以技术分为准”的最终策略，并固化到规则中。

十五、To Do List（不可再分的原子任务）

后端 Backend
- 数据库与配置
  - [x] 在 recommendation_items 表新增 ai_confidence DECIMAL(4,2) NULL
  - [x] 在 recommendation_items 表新增 ai_confidence_raw VARCHAR(255) NULL
  - [x] 在 recommendation_items 表新增 fusion_score DECIMAL(4,2) NULL
  - [x] 在 analysis_records 表新增 ai_confidence DECIMAL(4,2) NULL
  - [x] 在 analysis_records 表新增 ai_confidence_raw VARCHAR(255) NULL
  - [x] 在 analysis_records 表新增 fusion_score DECIMAL(4,2) NULL
  - [ ] 本地/测试环境执行变更脚本并验证新增列读取/写入
  - [x] 支持环境变量 CONF_FUSION_ALPHA（默认 0.4），服务启动打印一次配置值

- 解析逻辑（AI信心）
  - [x] 在 backend/services/enhanced_analyzer.py 实现 parse_ai_confidence(text) -> (value: float|None, raw: str|None)
  - [x] 正则覆盖：中/英“信心|confidence”、冒号/空格、大小写、全角/半角、带小数、换行、多个匹配取第一个
  - [ ] 边界处理：超界截断至 [0,10]，warn 日志记录记录ID与原始片段
  - [x] 失败处理：返回 (None, None)，debug 日志
  - [x] 单元测试：整型/小数/中英文/多匹配/异常文本（如“信心十/10”）

- 融合逻辑（最终分）
  - [x] 在 backend/services/enhanced_analyzer.py 实现 compute_fusion_score(tech_score: float|None, ai_confidence: float|None, alpha: float=0.4) -> float|None
  - [x] 规则：ai=null → fusion=tech（四舍五入两位小数，info 日志“无AI信心，回退技术分”）
  - [x] 规则：tech=null → fusion=null（warn 日志）
  - [x] 规则：范围裁剪 [0,10]；四舍五入两位小数
  - [x] 单元测试：边界/空值/不同 α/两位小数一致性

- API 输出
  - [x] 在 backend/routes_recommends.py 的查询/详情接口新增字段 ai_confidence、fusion_score
  - [x] 保持向下兼容（仅新增，不移除旧字段）
  - [ ] 更新接口文档注释（范围 0~10 与两位小数语义）

- 操作建议
  - [ ] 将现有 action 计算改为依据 fusion_score（ai 缺失场景与技术分一致）
  - [ ] 单元测试：阈值触发在融合分输入下的正确性

前端 Frontend
- 展示与交互
  - [x] 修改 frontend-web/src/features/recommend/pages/RecommendHistoryPage.tsx：同一行并排展示“技术分 / AI信心 / 融合分”（两位小数）
  - [x] 为三项添加 Tooltip：技术分(0~10) / AI信心(0~10) / 融合分(默认 α=0.4)
  - [x] 数值格式：统一保留两位小数；ai_confidence 为空显示“-”；fusion_score 为空显示“-”
  - [x] 视觉与响应式：对齐现有风格，移动端不溢出
  - [x] 可选：支持按融合分排序（默认关闭，受后端开关控制）
  - [x] 自选股（Watchlist）页面：删除综合评分列，新增“融合分”独立一列；“技术分/AI信心”通过该列 Hover 的 Tooltip 展示（两位小数，空值显示“-”）

- 前端测试
  - [ ] 不同数据长度与空值下布局不抖动
  - [ ] Tooltip 文案与显示时机正确

日志与监控
  - [ ] 解析失败或越界：warn，含记录ID与原始片段
  - [x] 无AI回退技术分：info 日志

测试与验收
  - [x] 后端单测：解析/融合覆盖上述用例
  - [ ] 集成测试：新增记录写入、API 返回新增字段
  - [ ] 前端：渲染正确、Tooltip 正确、空值与布局正确
  - [ ] 验收用例：
    - [ ] “信心 8/10” + 技术分=7.50 → ai=8.00，fusion=7.80（α=0.4）
    - [ ] “Confidence 7.5/10” → ai=7.50
    - [ ] “信心 十/10” → ai=null，fusion=技术分（两位小数）
    - [ ] 缺少技术分 → fusion=null

阶段二（后续规划，不在本迭代）
- 历史数据回填
  - [ ] 分页解析历史记录、幂等与统计日志、只写新增列
- 合并通用表方案评估与迁移
  - [ ] 评估并设计 stock_analysis_records，规划数据迁移与双写策略
- 目标：统一“个股分析记录”为一张通用表 stock_analysis_records，既可关联推荐会话（rec_id），也可独立记录（rec_id 为空）。
- 建议字段：
  - id（PK）、rec_id（INT NULL，FK→recommendations.id）、symbol（VARCHAR(16) NOT NULL）、name（VARCHAR(64) NULL）
  - tech_score（DOUBLE NULL）、action（VARCHAR(16) NULL）、reason_brief（TEXT）、ai_advice（TEXT）
  - ai_confidence（DECIMAL(4,1) NULL）、ai_confidence_raw（VARCHAR(255) NULL）、fusion_score（DECIMAL(5,2) NULL）
  - created_at（DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP）
- 优点：查询口径统一、复用业务逻辑、简化回填/展示；
- 风险：迁移成本高、历史代码改动广、索引与权限需重新评估；
- 迁移方案（分阶段）：
  1) 新建 stock_analysis_records 表并补齐索引；
  2) 数据迁移：从 recommendation_items 与 analysis_records 写入新表；rec_id 对应；name 缺失时可结合 watchlist 或在线补充（可选）；
  3) 代码切换：新增统一 ORM（StockAnalysisRecord），routes_recommends 详情接口按 rec_id 查询新表；
  4) 双写观察：过渡期同时写旧表与新表（可选）；
  5) 切换只读/归档：稳定后停写旧表，保留只读或归档；
- 当前建议：为降低风险，现阶段按两张表直接加列实现；待功能稳定、查询诉求明确后，再评估是否推进合表。