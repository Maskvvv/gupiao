-- db_init_mysql.sql
-- 目的：初始化本项目在 MySQL 下的数据库表结构，对应后端 SQLAlchemy 模型。
-- 兼容：MySQL 8.0+，字符集使用 utf8mb4，存储引擎 InnoDB。
-- 提示：当前代码默认使用 SQLite，若要切换到 MySQL，请在 .env 中配置 DATABASE_URL（见文末说明）。

START TRANSACTION;

-- 可选：创建并选择数据库（按需启用并修改库名）
-- CREATE DATABASE IF NOT EXISTS `gupiao` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE `gupiao`;

-- 推荐记录主表（对应模型：Recommendation）
-- 用于存放一次候选筛选/推荐任务的概要信息
CREATE TABLE IF NOT EXISTS `recommendations` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  `period` VARCHAR(20) NULL COMMENT '分析周期，如 1y/6mo/3mo',
  `total_candidates` INT NOT NULL DEFAULT 0 COMMENT '候选股票总数',
  `top_n` INT NOT NULL DEFAULT 0 COMMENT '入选Top数量',
  `weights_config` TEXT NULL COMMENT '多维度权重配置(JSON 字符串)',
  `recommend_type` VARCHAR(20) NOT NULL DEFAULT 'manual' COMMENT '推荐类型：manual/market_wide/keyword',
  PRIMARY KEY (`id`),
  KEY `idx_recommendations_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='推荐记录主表';

-- 推荐明细表（对应模型：RecommendationItem）
-- 用于存放某次推荐的具体股票条目
CREATE TABLE IF NOT EXISTS `recommendation_items` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `rec_id` INT NOT NULL COMMENT '外键：关联 recommendations.id',
  `symbol` VARCHAR(16) NOT NULL COMMENT '股票代码（带交易所后缀或内部格式）',
  `name` VARCHAR(64) NULL COMMENT '股票名称',
  `score` DOUBLE NULL COMMENT '技术评分（0-1）',
  `action` VARCHAR(16) NULL COMMENT '建议动作：buy/hold/sell',
  `reason_brief` TEXT NULL COMMENT '理由简述（通常取 AI 文本首行）',
  `ai_advice` TEXT NULL COMMENT 'AI 生成的详细分析文本',
  PRIMARY KEY (`id`),
  KEY `idx_rec_items_rec_id` (`rec_id`),
  KEY `idx_rec_items_symbol` (`symbol`),
  CONSTRAINT `fk_rec_items_rec_id` FOREIGN KEY (`rec_id`) REFERENCES `recommendations` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='推荐明细表';

-- 自选股表（对应模型：Watchlist）
-- 用户维护的自选股票列表
CREATE TABLE IF NOT EXISTS `watchlist` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `symbol` VARCHAR(16) NOT NULL COMMENT '股票代码，唯一',
  `name` VARCHAR(64) NULL COMMENT '股票名称',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '加入时间（UTC）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_watchlist_symbol` (`symbol`),
  KEY `idx_watchlist_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='自选股票列表';

-- 分析记录表（对应模型：AnalysisRecord）
-- 用于批量或单次分析时记录每只股票的分析结果
CREATE TABLE IF NOT EXISTS `analysis_records` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `symbol` VARCHAR(16) NOT NULL COMMENT '股票代码',
  `score` DOUBLE NULL COMMENT '技术评分（0-1）',
  `action` VARCHAR(16) NULL COMMENT '建议动作：buy/hold/sell',
  `reason_brief` TEXT NULL COMMENT '理由简述（通常取 AI 文本首行）',
  `ai_advice` TEXT NULL COMMENT 'AI 生成的详细分析文本',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间（UTC）',
  PRIMARY KEY (`id`),
  KEY `idx_analysis_symbol` (`symbol`),
  KEY `idx_analysis_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='个股分析记录表';

-- 可选：为按 (rec_id, score DESC) 的查询加速，建立复合索引（与业务排序匹配）
-- 注意：MySQL 8.0 开始支持降序索引，但大多数情况下普通索引同样可用；按需开启。
-- CREATE INDEX `idx_rec_items_rec_id_score` ON `recommendation_items` (`rec_id`, `score` DESC);

COMMIT;

-- 使用说明：
-- 1) 在 MySQL 中（可选）先创建数据库并切换：
--    CREATE DATABASE IF NOT EXISTS gupiao DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; USE gupiao;
-- 2) 执行本 SQL 文件，创建所需表与索引。
-- 3) 在项目根目录的 .env 中配置 DATABASE_URL 指向 MySQL，例如：
--    DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/gupiao?charset=utf8mb4
-- 4) 若需回滚，可按依赖顺序删除表：
--    DROP TABLE IF EXISTS `recommendation_items`;  -- 先删子表（含外键）
--    DROP TABLE IF EXISTS `recommendations`;
--    DROP TABLE IF EXISTS `watchlist`;
--    DROP TABLE IF EXISTS `analysis_records`;