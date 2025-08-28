"""
流式推荐系统数据库初始化脚本（修改为使用原有数据库）
直接在backend目录下运行
"""
import os
import sys

# 不再强制设置数据库URL，使用项目默认配置

# 导入模型
from models.streaming_models import (
    create_tables, 
    DatabaseMigrator, 
    engine,
    RecommendationTask,
    RecommendationResult,
    TaskProgress,
    TaskSchedule,
    SystemMetrics,
    SessionLocal
)

def main():
    """主初始化函数"""
    print("🚀 开始初始化流式推荐系统数据库...")
    
    try:
        # 1. 创建新表
        print("\n📝 步骤1: 创建数据库表...")
        create_tables()
        
        # 2. 验证表是否创建成功
        print("\n🔍 步骤2: 验证表结构...")
        verify_tables()
        
        # 3. 初始化默认数据
        print("\n📊 步骤3: 初始化默认数据...")
        initialize_default_data()
        
        print("\n✅ 流式推荐系统数据库初始化完成！")
        print_summary()
        
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def verify_tables():
    """验证表是否正确创建"""
    from sqlalchemy import inspect
    
    inspector = inspect(engine)
    required_tables = [
        'recommendation_tasks',
        'recommendation_results', 
        'task_progress',
        'task_schedules',
        'system_metrics'
    ]
    
    existing_tables = inspector.get_table_names()
    
    for table_name in required_tables:
        if table_name in existing_tables:
            print(f"  ✅ {table_name}")
            # 验证关键列
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            print(f"     📋 列数: {len(columns)}")
        else:
            print(f"  ❌ {table_name} - 表未找到!")
            raise Exception(f"Required table {table_name} not created")

def initialize_default_data():
    """初始化默认数据"""
    with SessionLocal() as db:
        try:
            # 初始化默认任务调度配置
            existing_schedules = db.query(TaskSchedule).count()
            if existing_schedules == 0:
                default_schedules = [
                    TaskSchedule(
                        schedule_name="daily_market_scan",
                        task_type="market",
                        cron_expression="0 9 * * 1-5",  # 工作日上午9点
                        is_enabled=False,  # 默认禁用
                        schedule_params='{"period": "1y", "max_candidates": 50}',
                        max_concurrent_tasks=1,
                        timeout_seconds=3600
                    ),
                    TaskSchedule(
                        schedule_name="weekend_full_analysis",
                        task_type="market",
                        cron_expression="0 10 * * 6",  # 周六上午10点
                        is_enabled=False,  # 默认禁用
                        schedule_params='{"period": "1y", "max_candidates": 200}',
                        max_concurrent_tasks=1,
                        timeout_seconds=7200
                    )
                ]
                
                for schedule in default_schedules:
                    db.add(schedule)
                
                db.commit()
                print(f"  ✅ 创建了 {len(default_schedules)} 个默认调度任务")
            else:
                print(f"  📋 已存在 {existing_schedules} 个调度任务")
                
        except Exception as e:
            print(f"  ❌ 初始化默认数据失败: {e}")
            db.rollback()

def print_summary():
    """打印初始化总结"""
    print("\n" + "="*60)
    print("📋 流式推荐系统数据库初始化总结")
    print("="*60)
    print("✅ 核心表:")
    print("   • recommendation_tasks    - 推荐任务主表")
    print("   • recommendation_results  - 推荐结果表") 
    print("   • task_progress          - 任务进度日志表")
    print("   • task_schedules         - 任务调度配置表")
    print("   • system_metrics         - 系统指标表")
    print()
    print("🔗 数据库连接:")
    print(f"   • URL: {engine.url}")
    print(f"   • 驱动: {engine.url.get_backend_name()}")
    print()
    print("🎯 下一步:")
    print("   1. 启动流式推荐引擎")
    print("   2. 配置任务调度器")
    print("   3. 部署前端Dashboard")
    print("="*60)

if __name__ == "__main__":
    main()