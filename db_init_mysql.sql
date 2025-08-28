-- db_init_mysql.sql
-- 目的：初始化本项目在 MySQL 下的数据库表结构，对应后端 SQLAlchemy 模型。
-- 兼容：MySQL 8.0+，字符集使用 utf8mb4，存储引擎 InnoDB。
-- 提示：当前代码默认使用 SQLite，若要切换到 MySQL，请在 .env 中配置 DATABASE_URL（见文末说明）。
-- 更新：已移除旧的推荐历史表结构，采用新的流式推荐系统架构

START TRANSACTION;

-- 可选：创建并选择数据库（按需启用并修改库名）
-- CREATE DATABASE IF NOT EXISTS `gupiao` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE `gupiao`;

-- 流式推荐任务主表
CREATE TABLE IF NOT EXISTS `recommendation_tasks` (
  `id` VARCHAR(32) NOT NULL COMMENT '任务ID（UUID格式）',
  `task_type` VARCHAR(20) NOT NULL COMMENT '任务类型：keyword/market/manual',
  `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '任务状态：pending/running/completed/failed/cancelled',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `started_at` DATETIME NULL COMMENT '开始时间',
  `completed_at` DATETIME NULL COMMENT '完成时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  -- 任务参数
  `keyword` VARCHAR(100) NULL COMMENT '关键词（keyword类型任务）',
  `period` VARCHAR(20) NULL COMMENT '分析周期：1y/6mo/3mo',
  `max_candidates` INT NULL COMMENT '最大候选数量',
  `weights_config` TEXT NULL COMMENT '权重配置(JSON)',
  `ai_config` TEXT NULL COMMENT 'AI配置(JSON)',
  `filter_config` TEXT NULL COMMENT '筛选配置(JSON)',
  
  -- 执行结果统计
  `total_screened` INT NULL COMMENT '筛选的股票总数',
  `total_analyzed` INT NULL COMMENT '分析的股票总数',
  `total_recommended` INT NULL COMMENT '推荐的股票总数',
  `error_message` TEXT NULL COMMENT '错误信息',
  
  PRIMARY KEY (`id`),
  KEY `idx_recommendation_tasks_status` (`status`),
  KEY `idx_recommendation_tasks_type` (`task_type`),
  KEY `idx_recommendation_tasks_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='流式推荐任务表';

-- 推荐结果表（取代原有的 recommendation_items 表）
CREATE TABLE IF NOT EXISTS `recommendation_results` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` VARCHAR(32) NOT NULL COMMENT '关联任务ID',
  
  -- 股票信息
  `symbol` VARCHAR(16) NOT NULL COMMENT '股票代码',
  `name` VARCHAR(64) NULL COMMENT '股票名称',
  `market` VARCHAR(16) NULL COMMENT '市场：A/US/HK',
  
  -- 分析结果
  `technical_score` DECIMAL(4,2) NULL COMMENT '技术分数',
  `ai_score` DECIMAL(4,2) NULL COMMENT 'AI分数',
  `fusion_score` DECIMAL(4,2) NULL COMMENT '融合分数',
  `final_score` DECIMAL(4,2) NULL COMMENT '最终分数',
  `action` VARCHAR(16) NULL COMMENT '建议动作：buy/hold/sell',
  
  -- AI分析内容
  `ai_analysis` TEXT NULL COMMENT 'AI完整分析',
  `ai_confidence` DECIMAL(4,2) NULL COMMENT 'AI信心度',
  `ai_reasoning` TEXT NULL COMMENT 'AI推理过程',
  `ai_risk_assessment` TEXT NULL COMMENT 'AI风险评估',
  
  -- 技术分析内容
  `technical_indicators` TEXT NULL COMMENT '技术指标详情(JSON)',
  `support_resistance` TEXT NULL COMMENT '支撑阻力位(JSON)',
  `trend_analysis` TEXT NULL COMMENT '趋势分析(JSON)',
  
  -- 摘要信息
  `summary` TEXT NULL COMMENT '简要描述',
  `key_factors` TEXT NULL COMMENT '关键因子(JSON)',
  `risk_factors` TEXT NULL COMMENT '风险因子(JSON)',
  
  -- 排序和筛选
  `rank_in_task` INT NULL COMMENT '在任务中的排名',
  `is_recommended` BOOLEAN DEFAULT FALSE COMMENT '是否被推荐',
  `recommendation_reason` TEXT NULL COMMENT '推荐理由',
  
  -- 市场数据快照
  `current_price` DECIMAL(10,4) NULL COMMENT '分析时价格',
  `price_change_pct` DECIMAL(8,4) NULL COMMENT '价格变化百分比',
  `volume` BIGINT NULL COMMENT '成交量',
  `market_cap` DECIMAL(15,2) NULL COMMENT '市值',
  
  -- 时间戳
  `analyzed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '分析时间',
  `data_date` DATETIME NULL COMMENT '数据日期',
  
  PRIMARY KEY (`id`),
  KEY `idx_recommendation_results_task_id` (`task_id`),
  KEY `idx_recommendation_results_symbol` (`symbol`),
  KEY `idx_recommendation_results_rank` (`rank_in_task`),
  KEY `idx_recommendation_results_score` (`final_score`),
  KEY `idx_recommendation_results_analyzed_at` (`analyzed_at`),
  CONSTRAINT `fk_recommendation_results_task_id` 
    FOREIGN KEY (`task_id`) REFERENCES `recommendation_tasks` (`id`) 
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='推荐结果表';

-- 任务进度记录表
CREATE TABLE IF NOT EXISTS `task_progress` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` VARCHAR(32) NOT NULL COMMENT '关联任务ID',
  `timestamp` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '时间戳',
  
  -- 进度信息
  `phase` VARCHAR(20) NOT NULL COMMENT '阶段：screening/analyzing/completed',
  `current_step` VARCHAR(50) NULL COMMENT '当前步骤描述',
  `progress_percent` DECIMAL(5,2) NULL COMMENT '进度百分比',
  `processed_count` INT NULL COMMENT '已处理数量',
  `total_count` INT NULL COMMENT '总数量',
  
  -- 性能指标
  `processing_speed` DECIMAL(8,2) NULL COMMENT '处理速度（个/秒）',
  `estimated_remaining_time` INT NULL COMMENT '预估剩余时间（秒）',
  
  -- 状态信息
  `status_message` TEXT NULL COMMENT '状态消息',
  `error_count` INT DEFAULT 0 COMMENT '错误计数',
  `warning_count` INT DEFAULT 0 COMMENT '警告计数',
  
  PRIMARY KEY (`id`),
  KEY `idx_task_progress_task_id` (`task_id`),
  KEY `idx_task_progress_timestamp` (`timestamp`),
  CONSTRAINT `fk_task_progress_task_id` 
    FOREIGN KEY (`task_id`) REFERENCES `recommendation_tasks` (`id`) 
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务进度记录表';

-- 任务调度配置表
CREATE TABLE IF NOT EXISTS `task_schedules` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `schedule_name` VARCHAR(50) NOT NULL COMMENT '调度名称',
  `task_type` VARCHAR(20) NOT NULL COMMENT '任务类型',
  `cron_expression` VARCHAR(50) NOT NULL COMMENT 'Cron表达式',
  `is_enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `last_run_at` DATETIME NULL COMMENT '上次运行时间',
  `next_run_at` DATETIME NULL COMMENT '下次运行时间',
  
  -- 调度参数
  `schedule_params` TEXT NULL COMMENT '调度参数(JSON)',
  `max_concurrent_tasks` INT DEFAULT 1 COMMENT '最大并发任务数',
  `timeout_seconds` INT DEFAULT 3600 COMMENT '超时时间（秒）',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_schedules_name` (`schedule_name`),
  KEY `idx_task_schedules_enabled` (`is_enabled`),
  KEY `idx_task_schedules_next_run` (`next_run_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务调度配置表';

-- 系统指标表
CREATE TABLE IF NOT EXISTS `system_metrics` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `timestamp` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '时间戳',
  `metric_type` VARCHAR(30) NOT NULL COMMENT '指标类型',
  `metric_name` VARCHAR(50) NOT NULL COMMENT '指标名称',
  `metric_value` DECIMAL(15,4) NULL COMMENT '指标值',
  `metric_unit` VARCHAR(20) NULL COMMENT '指标单位',
  `tags` TEXT NULL COMMENT '标签(JSON)',
  
  PRIMARY KEY (`id`),
  KEY `idx_system_metrics_timestamp` (`timestamp`),
  KEY `idx_system_metrics_type_name` (`metric_type`, `metric_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统指标表';

-- 自选股表（保留原有功能）
CREATE TABLE IF NOT EXISTS `watchlist` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `symbol` VARCHAR(16) NOT NULL COMMENT '股票代码，唯一',
  `name` VARCHAR(64) NULL COMMENT '股票名称',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '加入时间（北京时间/UTC+8）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_watchlist_symbol` (`symbol`),
  KEY `idx_watchlist_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='自选股票列表';

-- 分析记录表（保留原有功能）
CREATE TABLE IF NOT EXISTS `analysis_records` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `symbol` VARCHAR(16) NOT NULL COMMENT '股票代码',
  `score` DOUBLE NULL COMMENT '技术评分（0-1）',
  `action` VARCHAR(16) NULL COMMENT '建议动作：buy/hold/sell',
  `reason_brief` TEXT NULL COMMENT '理由简述（通常取 AI 文本首行）',
  `ai_advice` TEXT NULL COMMENT 'AI 生成的详细分析文本',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间（北京时间/UTC+8）',
  PRIMARY KEY (`id`),
  KEY `idx_analysis_symbol` (`symbol`),
  KEY `idx_analysis_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='个股分析记录表';

-- 插入默认调度任务
INSERT IGNORE INTO `task_schedules` 
(`schedule_name`, `task_type`, `cron_expression`, `is_enabled`, `schedule_params`, `max_concurrent_tasks`, `timeout_seconds`)
VALUES 
('daily_market_scan', 'market', '0 9 * * 1-5', FALSE, '{"period": "1y", "max_candidates": 50}', 1, 3600),
('weekend_full_analysis', 'market', '0 10 * * 6', FALSE, '{"period": "1y", "max_candidates": 200}', 1, 7200);

COMMIT;

-- 使用说明：
-- 1) 在 MySQL 中（可选）先创建数据库并切换：
--    CREATE DATABASE IF NOT EXISTS gupiao DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; USE gupiao;
-- 2) 执行本 SQL 文件，创建所需表与索引。
-- 3) 在项目根目录的 .env 中配置 DATABASE_URL 指向 MySQL，例如：
--    DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/gupiao?charset=utf8mb4
-- 4) 新架构说明：
--    - 采用流式推荐系统，支持异步任务处理
--    - recommendation_tasks: 任务管理主表
--    - recommendation_results: 推荐结果表（替代原 recommendation_items）
--    - task_progress: 任务进度跟踪
--    - task_schedules: 定时任务配置
--    - system_metrics: 系统性能监控
-- 5) 若需回滚，可按依赖顺序删除表：
--    DROP TABLE IF EXISTS `recommendation_results`;
--    DROP TABLE IF EXISTS `task_progress`;
--    DROP TABLE IF EXISTS `system_metrics`;
--    DROP TABLE IF EXISTS `task_schedules`;
--    DROP TABLE IF EXISTS `recommendation_tasks`;
--    DROP TABLE IF EXISTS `watchlist`;
--    DROP TABLE IF EXISTS `analysis_records`;