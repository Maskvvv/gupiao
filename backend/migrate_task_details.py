#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加任务详情显示字段
为RecommendationTask表添加用于存储筛选条件和输入内容的字段
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, Column, Text, JSON
from backend.models.streaming_models import engine, SessionLocal, RecommendationTask

def add_task_detail_fields():
    """为RecommendationTask表添加详情显示字段"""
    
    migrations = [
        # 添加用户输入信息字段
        """ALTER TABLE recommendation_tasks ADD COLUMN user_input_summary TEXT;""",
        
        # 添加筛选条件展示字段
        """ALTER TABLE recommendation_tasks ADD COLUMN filter_summary TEXT;""",
        
        # 添加AI提示词存储字段（用于用户查看AI是如何理解任务的）
        """ALTER TABLE recommendation_tasks ADD COLUMN ai_prompt_used TEXT;""",
        
        # 添加执行策略说明字段
        """ALTER TABLE recommendation_tasks ADD COLUMN execution_strategy TEXT;""",
        
        # 添加候选股票列表字段（AI推荐的原始股票池）
        """ALTER TABLE recommendation_tasks ADD COLUMN candidate_stocks_info TEXT;""",
    ]
    
    with SessionLocal() as db:
        try:
            for migration_sql in migrations:
                try:
                    db.execute(text(migration_sql))
                    print(f"✅ 执行成功: {migration_sql}")
                except Exception as e:
                    if "already exists" in str(e) or "duplicate column" in str(e).lower():
                        print(f"⚠️ 字段已存在，跳过: {migration_sql}")
                    else:
                        print(f"❌ 执行失败: {migration_sql}, 错误: {e}")
            
            db.commit()
            print("✅ 任务详情字段添加完成")
            
        except Exception as e:
            db.rollback()
            print(f"❌ 迁移失败: {e}")
            raise

def update_existing_tasks():
    """更新现有任务的详情字段"""
    with SessionLocal() as db:
        try:
            # 查询现有任务
            tasks = db.query(RecommendationTask).all()
            
            for task in tasks:
                # 解析现有的配置信息来生成摘要
                import json
                
                try:
                    request_params = json.loads(task.request_params or '{}')
                    filter_config = json.loads(task.filter_config or '{}')
                    
                    # 生成用户输入摘要
                    user_summary_parts = []
                    if task.task_type == 'keyword':
                        keyword = request_params.get('keyword', '未知')
                        user_summary_parts.append(f"关键词: {keyword}")
                    elif task.task_type == 'market':
                        user_summary_parts.append("全市场推荐")
                    
                    max_candidates = request_params.get('max_candidates', '未设置')
                    user_summary_parts.append(f"最大候选数: {max_candidates}")
                    
                    period = request_params.get('period', '1y')
                    user_summary_parts.append(f"分析周期: {period}")
                    
                    task.user_input_summary = " | ".join(user_summary_parts)
                    
                    # 生成筛选条件摘要
                    filter_summary_parts = []
                    if filter_config.get('exclude_st'):
                        filter_summary_parts.append("排除ST股票")
                    
                    board = filter_config.get('board')
                    if board and board != 'all':
                        board_names = {'main': '主板', 'gem': '创业板', 'star': '科创板'}
                        filter_summary_parts.append(f"板块: {board_names.get(board, board)}")
                    
                    min_market_cap = filter_config.get('min_market_cap')
                    if min_market_cap:
                        filter_summary_parts.append(f"最小市值: {min_market_cap}亿")
                    
                    task.filter_summary = " | ".join(filter_summary_parts) if filter_summary_parts else "无特殊筛选条件"
                    
                    # 生成执行策略说明
                    if task.task_type == 'keyword':
                        task.execution_strategy = "AI智能筛选股票池 → 技术分析 → AI深度分析 → 融合评分 → 排序推荐"
                    else:
                        task.execution_strategy = "市场随机采样 → 技术分析 → AI深度分析 → 融合评分 → 排序推荐"
                    
                except Exception as e:
                    print(f"⚠️ 更新任务 {task.id} 详情失败: {e}")
                    continue
            
            db.commit()
            print(f"✅ 更新了 {len(tasks)} 个现有任务的详情信息")
            
        except Exception as e:
            db.rollback()
            print(f"❌ 更新现有任务失败: {e}")

if __name__ == "__main__":
    print("开始添加任务详情字段...")
    add_task_detail_fields()
    
    print("开始更新现有任务详情...")
    update_existing_tasks()
    
    print("✅ 数据库迁移完成")