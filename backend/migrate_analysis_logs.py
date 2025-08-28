#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加分析过程日志持久化功能
为推荐系统添加详细的分析过程日志记录表
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean, JSON
from backend.models.streaming_models import engine, SessionLocal, now_bj

def add_analysis_log_tables():
    """添加分析过程日志相关表"""
    
    # 创建详细分析日志表
    create_analysis_logs_table = """
    CREATE TABLE IF NOT EXISTS analysis_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id VARCHAR(32) NOT NULL,
        log_type VARCHAR(32) NOT NULL,  -- 'ai_screening', 'technical_analysis', 'ai_analysis', 'fusion_score', 'error'
        stock_symbol VARCHAR(16),
        timestamp DATETIME NOT NULL,
        
        -- 日志内容
        log_level VARCHAR(16) DEFAULT 'info',  -- 'debug', 'info', 'warning', 'error'
        log_message TEXT,
        log_details TEXT,  -- JSON格式的详细信息
        
        -- AI相关日志
        ai_request_prompt TEXT,
        ai_response_content TEXT,
        ai_response_tokens INTEGER,
        ai_processing_time_ms INTEGER,
        ai_provider VARCHAR(32),
        
        -- 技术分析日志
        technical_indicators TEXT,  -- JSON格式
        technical_score FLOAT,
        technical_signals TEXT,  -- JSON格式
        
        -- 融合评分日志
        fusion_components TEXT,  -- JSON格式，包含各个评分组件
        fusion_weights TEXT,  -- JSON格式，评分权重
        final_score FLOAT,
        
        -- 性能监控
        memory_usage_mb FLOAT,
        cpu_time_ms INTEGER,
        
        -- 索引字段
        FOREIGN KEY (task_id) REFERENCES recommendation_tasks(id) ON DELETE CASCADE
    );
    """
    
    # 创建用户日志查看配置表
    create_log_viewer_config_table = """
    CREATE TABLE IF NOT EXISTS log_viewer_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id VARCHAR(64),  -- 用户标识，如果有用户系统的话
        task_id VARCHAR(32) NOT NULL,
        
        -- 查看配置
        show_ai_details BOOLEAN DEFAULT true,
        show_technical_details BOOLEAN DEFAULT true,
        show_performance_metrics BOOLEAN DEFAULT false,
        show_debug_logs BOOLEAN DEFAULT false,
        
        -- 过滤设置
        log_level_filter VARCHAR(16) DEFAULT 'info',  -- 最低显示级别
        log_type_filter TEXT,  -- JSON数组，要显示的日志类型
        
        -- 时间戳
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (task_id) REFERENCES recommendation_tasks(id) ON DELETE CASCADE
    );
    """
    
    # 创建日志统计视图
    create_log_stats_view = """
    CREATE VIEW IF NOT EXISTS log_stats_view AS
    SELECT 
        task_id,
        COUNT(*) as total_logs,
        SUM(CASE WHEN log_level = 'error' THEN 1 ELSE 0 END) as error_count,
        SUM(CASE WHEN log_level = 'warning' THEN 1 ELSE 0 END) as warning_count,
        SUM(CASE WHEN log_type = 'ai_analysis' THEN 1 ELSE 0 END) as ai_analysis_count,
        SUM(CASE WHEN log_type = 'technical_analysis' THEN 1 ELSE 0 END) as technical_analysis_count,
        AVG(ai_processing_time_ms) as avg_ai_time_ms,
        SUM(ai_response_tokens) as total_tokens,
        MIN(timestamp) as first_log_time,
        MAX(timestamp) as last_log_time
    FROM analysis_logs 
    GROUP BY task_id;
    """
    
    # 为性能优化添加索引
    create_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_analysis_logs_task_id ON analysis_logs(task_id);",
        "CREATE INDEX IF NOT EXISTS idx_analysis_logs_timestamp ON analysis_logs(timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_analysis_logs_log_type ON analysis_logs(log_type);",
        "CREATE INDEX IF NOT EXISTS idx_analysis_logs_stock_symbol ON analysis_logs(stock_symbol);",
        "CREATE INDEX IF NOT EXISTS idx_analysis_logs_log_level ON analysis_logs(log_level);",
    ]
    
    with SessionLocal() as db:
        try:
            # 创建表
            db.execute(text(create_analysis_logs_table))
            print("✅ 创建 analysis_logs 表成功")
            
            db.execute(text(create_log_viewer_config_table))
            print("✅ 创建 log_viewer_configs 表成功")
            
            db.execute(text(create_log_stats_view))
            print("✅ 创建 log_stats_view 视图成功")
            
            # 创建索引
            for index_sql in create_indexes:
                db.execute(text(index_sql))
                print(f"✅ 创建索引成功: {index_sql.split('ON')[1].split('(')[0].strip()}")
            
            db.commit()
            print("✅ 分析日志表结构创建完成")
            
        except Exception as e:
            db.rollback()
            print(f"❌ 创建分析日志表失败: {e}")
            raise

def verify_log_tables():
    """验证日志表创建成功"""
    with SessionLocal() as db:
        try:
            # 检查表是否存在
            tables_to_check = ['analysis_logs', 'log_viewer_configs']
            
            for table_name in tables_to_check:
                result = db.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';"))
                if result.fetchone():
                    print(f"✅ 表 {table_name} 存在")
                else:
                    print(f"❌ 表 {table_name} 不存在")
            
            # 检查视图
            result = db.execute(text("SELECT name FROM sqlite_master WHERE type='view' AND name='log_stats_view';"))
            if result.fetchone():
                print("✅ 视图 log_stats_view 存在")
            else:
                print("❌ 视图 log_stats_view 不存在")
            
            # 测试插入和查询
            test_log_sql = """
            INSERT INTO analysis_logs (
                task_id, log_type, stock_symbol, timestamp, log_level, 
                log_message, log_details
            ) VALUES (
                'test_task_123', 'ai_screening', '000001', datetime('now'), 'info',
                '测试日志消息', '{"test": "data"}'
            );
            """
            
            db.execute(text(test_log_sql))
            
            # 查询测试数据
            test_query = "SELECT * FROM analysis_logs WHERE task_id = 'test_task_123';"
            result = db.execute(text(test_query))
            test_data = result.fetchone()
            
            if test_data:
                print("✅ 日志表插入和查询测试成功")
                # 清理测试数据
                db.execute(text("DELETE FROM analysis_logs WHERE task_id = 'test_task_123';"))
            else:
                print("❌ 日志表测试失败")
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            print(f"❌ 验证日志表失败: {e}")

if __name__ == "__main__":
    print("开始创建分析日志表...")
    add_analysis_log_tables()
    
    print("\n验证日志表创建结果...")
    verify_log_tables()
    
    print("\n✅ 分析过程日志持久化数据库准备完成")