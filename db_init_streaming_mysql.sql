-- 流式推荐系统 MySQL 数据库初始化脚本
-- 用于创建新的流式任务管理表结构
-- 兼容：MySQL 8.0+，字符集使用 utf8mb4，存储引擎 InnoDB

START TRANSACTION;

-- 可选：创建并选择数据库（按需启用并修改库名）
-- CREATE DATABASE IF NOT EXISTS `gupiao_streaming` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE `gupiao_streaming`;

-- 推荐任务主表（取代原有的 recommendations 表）
CREATE TABLE IF NOT EXISTS `recommendation_tasks` (
  `id` VARCHAR(32) NOT NULL COMMENT '任务UUID',
  `task_type` VARCHAR(20) NOT NULL COMMENT '任务类型：ai/keyword/market',
  `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '任务状态：pending/running/completed/failed/cancelled',
  `priority` INT NOT NULL DEFAULT 5 COMMENT '优先级 1-10',
  
  -- 时间戳
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `started_at` DATETIME NULL COMMENT '开始时间',
  `completed_at` DATETIME NULL COMMENT '完成时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  -- 任务参数 (JSON)
  `request_params` TEXT NULL COMMENT '原始请求参数(JSON)',
  `ai_config` TEXT NULL COMMENT 'AI相关配置(JSON)',
  `filter_config` TEXT NULL COMMENT '筛选配置(JSON)',
  `weights_config` TEXT NULL COMMENT '权重配置(JSON)',
  
  -- 执行状态
  `total_symbols` INT NOT NULL DEFAULT 0 COMMENT '总处理股票数',
  `completed_symbols` INT NOT NULL DEFAULT 0 COMMENT '已完成股票数',
  `current_symbol` VARCHAR(16) NULL COMMENT '当前处理股票',
  `current_phase` VARCHAR(32) NULL COMMENT '当前阶段',
  `progress_percent` DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '进度百分比',
  
  -- 结果统计
  `successful_count` INT NOT NULL DEFAULT 0 COMMENT '成功分析数',
  `failed_count` INT NOT NULL DEFAULT 0 COMMENT '失败分析数',
  `final_recommendations` INT NOT NULL DEFAULT 0 COMMENT '最终推荐数',
  
  -- 错误处理
  `error_message` TEXT NULL COMMENT '错误消息',
  `error_details` TEXT NULL COMMENT '详细错误信息(JSON)',
  `retry_count` INT NOT NULL DEFAULT 0 COMMENT '重试次数',
  `max_retries` INT NOT NULL DEFAULT 3 COMMENT '最大重试次数',
  
  -- 性能指标
  `total_tokens_used` INT NOT NULL DEFAULT 0 COMMENT 'AI Token消耗',
  `total_api_calls` INT NOT NULL DEFAULT 0 COMMENT 'API调用次数',
  `execution_time_seconds` DECIMAL(10,3) NULL COMMENT '执行时间（秒）',
  
  PRIMARY KEY (`id`),
  KEY `idx_recommendation_tasks_created_at` (`created_at`),
  KEY `idx_recommendation_tasks_status` (`status`),
  KEY `idx_recommendation_tasks_type` (`task_type`),
  KEY `idx_recommendation_tasks_updated_at` (`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='推荐任务主表';

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
  `is_recommended` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否被推荐',
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
  `event_type` VARCHAR(20) NULL COMMENT '事件类型：start/progress/ai_chunk/symbol_complete/phase_change/complete/error',
  `symbol` VARCHAR(16) NULL COMMENT '当前处理的股票',
  `phase` VARCHAR(32) NULL COMMENT '当前阶段',
  `progress_data` TEXT NULL COMMENT '进度数据(JSON)',
  
  -- AI流式数据
  `ai_chunk_content` TEXT NULL COMMENT 'AI流式返回的数据块',
  `ai_chunk_sequence` INT NULL COMMENT 'AI数据块序号',
  `accumulated_content` TEXT NULL COMMENT '累积的AI内容',
  
  -- 状态和消息
  `status` VARCHAR(20) NULL COMMENT '状态',
  `message` TEXT NULL COMMENT '消息内容',
  
  -- 性能数据
  `processing_time_ms` INT NULL COMMENT '处理时间（毫秒）',
  `memory_usage_mb` DECIMAL(8,2) NULL COMMENT '内存使用（MB）',
  
  PRIMARY KEY (`id`),
  KEY `idx_task_progress_task_id` (`task_id`),
  KEY `idx_task_progress_timestamp` (`timestamp`),
  KEY `idx_task_progress_event_type` (`event_type`),
  CONSTRAINT `fk_task_progress_task_id` 
    FOREIGN KEY (`task_id`) REFERENCES `recommendation_tasks` (`id`) 
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务进度记录表';

-- 任务调度配置表
CREATE TABLE IF NOT EXISTS `task_schedules` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `schedule_name` VARCHAR(64) NOT NULL UNIQUE COMMENT '调度名称',
  `task_type` VARCHAR(20) NOT NULL COMMENT '任务类型',
  `cron_expression` VARCHAR(32) NOT NULL COMMENT 'Cron表达式',
  `is_enabled` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
  
  -- 调度参数
  `schedule_params` TEXT NULL COMMENT '调度参数(JSON)',
  `max_concurrent_tasks` INT NOT NULL DEFAULT 1 COMMENT '最大并发任务数',
  `timeout_seconds` INT NOT NULL DEFAULT 3600 COMMENT '超时时间',
  
  -- 状态信息
  `last_run_time` DATETIME NULL COMMENT '上次运行时间',
  `next_run_time` DATETIME NULL COMMENT '下次运行时间',
  `last_task_id` VARCHAR(32) NULL COMMENT '最后一次创建的任务ID',
  `success_count` INT NOT NULL DEFAULT 0 COMMENT '成功次数',
  `failure_count` INT NOT NULL DEFAULT 0 COMMENT '失败次数',
  
  -- 时间戳
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_schedules_name` (`schedule_name`),
  KEY `idx_task_schedules_enabled` (`is_enabled`),
  KEY `idx_task_schedules_next_run` (`next_run_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务调度配置表';

-- 系统性能指标表
CREATE TABLE IF NOT EXISTS `system_metrics` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `metric_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '指标时间',
  
  -- 任务统计
  `pending_tasks` INT NOT NULL DEFAULT 0 COMMENT '等待任务数',
  `running_tasks` INT NOT NULL DEFAULT 0 COMMENT '运行任务数',
  `completed_tasks_today` INT NOT NULL DEFAULT 0 COMMENT '今日完成任务数',
  `failed_tasks_today` INT NOT NULL DEFAULT 0 COMMENT '今日失败任务数',
  
  -- 系统资源
  `cpu_usage_percent` DECIMAL(5,2) NULL COMMENT 'CPU使用率',
  `memory_usage_percent` DECIMAL(5,2) NULL COMMENT '内存使用率',
  `disk_usage_percent` DECIMAL(5,2) NULL COMMENT '磁盘使用率',
  
  -- API调用统计
  `openai_calls_today` INT NOT NULL DEFAULT 0 COMMENT '今日OpenAI调用数',
  `deepseek_calls_today` INT NOT NULL DEFAULT 0 COMMENT '今日DeepSeek调用数',
  `gemini_calls_today` INT NOT NULL DEFAULT 0 COMMENT '今日Gemini调用数',
  `total_tokens_today` INT NOT NULL DEFAULT 0 COMMENT '今日总Token消耗',
  
  -- 错误统计
  `api_errors_today` INT NOT NULL DEFAULT 0 COMMENT '今日API错误数',
  `system_errors_today` INT NOT NULL DEFAULT 0 COMMENT '今日系统错误数',
  
  -- 性能指标
  `avg_task_execution_time` DECIMAL(8,3) NULL COMMENT '平均任务执行时间（秒）',
  `avg_symbol_analysis_time` DECIMAL(8,3) NULL COMMENT '平均单股分析时间（秒）',
  
  PRIMARY KEY (`id`),
  KEY `idx_system_metrics_time` (`metric_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统性能指标表';

-- 插入默认调度任务配置
INSERT IGNORE INTO `task_schedules` 
(`schedule_name`, `task_type`, `cron_expression`, `is_enabled`, `schedule_params`, `max_concurrent_tasks`, `timeout_seconds`)
VALUES 
('daily_market_scan', 'market', '0 9 * * 1-5', FALSE, '{"period": "1y", "max_candidates": 50}', 1, 3600),
('weekend_full_analysis', 'market', '0 10 * * 6', FALSE, '{"period": "1y", "max_candidates": 200}', 1, 7200);

COMMIT;

-- 显示创建的表
SELECT 
  TABLE_NAME as '表名',
  TABLE_COMMENT as '说明',
  TABLE_ROWS as '行数'
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME IN ('recommendation_tasks', 'recommendation_results', 'task_progress', 'task_schedules', 'system_metrics')
ORDER BY TABLE_NAME;