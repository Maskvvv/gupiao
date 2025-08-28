"""
数据库迁移脚本：在原有数据库中添加流式推荐系统的新表
将新的流式任务管理表添加到现有的 a_stock_analysis.db 数据库中
"""
import os
import sys
from sqlalchemy import inspect, text

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from backend.models.streaming_models import (
    create_tables, 
    engine,
    RecommendationTask,
    RecommendationResult,
    TaskProgress,
    TaskSchedule,
    SystemMetrics,
    SessionLocal,
    Base
)

def check_existing_tables():
    """检查现有表结构"""
    print("🔍 检查现有数据库表...")
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    print(f"📋 现有表列表 ({len(existing_tables)} 个):")
    for table in existing_tables:
        print(f"  - {table}")
    
    return existing_tables

def check_new_tables():
    """检查需要添加的新表"""
    new_tables = [
        'recommendation_tasks',
        'recommendation_results', 
        'task_progress',
        'task_schedules',
        'system_metrics'
    ]
    
    print(f"\n📝 需要添加的新表 ({len(new_tables)} 个):")
    for table in new_tables:
        print(f"  - {table}")
    
    return new_tables

def migrate_tables():
    """执行表迁移"""
    print("\n🚀 开始数据库表迁移...")
    
    try:
        # 获取现有表
        existing_tables = check_existing_tables()
        new_tables = check_new_tables()
        
        # 检查是否有表冲突
        conflicts = set(existing_tables).intersection(set(new_tables))
        if conflicts:
            print(f"\n⚠️  发现表名冲突: {list(conflicts)}")
            response = input("是否继续并覆盖现有表? (y/N): ")
            if response.lower() != 'y':
                print("❌ 迁移已取消")
                return False
        
        # 创建新表
        print("\n📝 创建流式推荐系统表...")
        create_tables()
        
        # 验证新表是否创建成功
        print("\n🔍 验证新表创建状态...")
        inspector = inspect(engine)
        updated_tables = inspector.get_table_names()
        
        newly_created = []
        for table in new_tables:
            if table in updated_tables:
                print(f"  ✅ {table}")
                newly_created.append(table)
            else:
                print(f"  ❌ {table} - 创建失败")
        
        if len(newly_created) == len(new_tables):
            print(f"\n✅ 成功创建 {len(newly_created)} 个新表")
            return True
        else:
            print(f"\n⚠️  部分表创建失败: {len(newly_created)}/{len(new_tables)}")
            return False
            
    except Exception as e:
        print(f"\n❌ 表迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def initialize_default_data():
    """初始化默认数据"""
    print("\n📊 初始化默认数据...")
    
    try:
        with SessionLocal() as db:
            # 检查是否已有调度任务
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
                print(f"  📋 已存在 {existing_schedules} 个调度任务，跳过初始化")
                
    except Exception as e:
        print(f"  ❌ 初始化默认数据失败: {e}")
        return False
    
    return True

def test_database_connection():
    """测试数据库连接"""
    print("\n🔗 测试数据库连接...")
    
    try:
        with SessionLocal() as db:
            # 测试基本查询
            task_count = db.query(RecommendationTask).count()
            print(f"  ✅ 推荐任务表连接正常，当前任务数: {task_count}")
            
            schedule_count = db.query(TaskSchedule).count()
            print(f"  ✅ 调度任务表连接正常，当前调度数: {schedule_count}")
            
        return True
        
    except Exception as e:
        print(f"  ❌ 数据库连接测试失败: {e}")
        return False

def print_summary():
    """打印迁移总结"""
    print("\n" + "="*60)
    print("📋 流式推荐系统数据库迁移总结")
    print("="*60)
    print("✅ 已添加的表:")
    print("   • recommendation_tasks    - 推荐任务主表")
    print("   • recommendation_results  - 推荐结果表") 
    print("   • task_progress          - 任务进度日志表")
    print("   • task_schedules         - 任务调度配置表")
    print("   • system_metrics         - 系统指标表")
    print()
    print("🔗 数据库配置:")
    print(f"   • URL: {engine.url}")
    print(f"   • 驱动: {engine.url.get_backend_name()}")
    print()
    print("🎯 下一步:")
    print("   1. 启动后端服务: uvicorn backend.main:app --reload")
    print("   2. 启动前端服务: cd frontend-web && npm run dev")
    print("   3. 访问任务管理界面: http://localhost:5173/tasks")
    print("="*60)

def main():
    """主迁移函数"""
    print("🚀 开始流式推荐系统数据库迁移...")
    print(f"🔗 目标数据库: {engine.url}")
    
    # 步骤1: 迁移表结构
    if not migrate_tables():
        print("❌ 表迁移失败，终止进程")
        sys.exit(1)
    
    # 步骤2: 初始化默认数据
    if not initialize_default_data():
        print("⚠️  默认数据初始化失败，但表迁移成功")
    
    # 步骤3: 测试数据库连接
    if not test_database_connection():
        print("⚠️  数据库连接测试失败，请检查配置")
    
    # 步骤4: 打印总结
    print_summary()
    
    print("\n✅ 流式推荐系统数据库迁移完成！")

if __name__ == "__main__":
    main()